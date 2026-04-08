# -*- coding: utf-8 -*-
"""Kurumsal QC butonu v4.

Export UI: sadece "CSV + JSON" veya "Hayır".
Title block skor dışı. BIM form %50 ağırlık. Manuel check UI.
"""
from __future__ import print_function

from pyrevit import forms, revit, script

from qc_engine import evaluate_document
from qc_manual_checks import show_manual_check_ui
from qc_report import export_csv_report, export_json_report, write_central_log
from qc_scoring import compute_bim_form_score, compute_general_score
from qc_standard import get_history_limit, get_standard_summary, load_company_standard
from qc_storage import (
    append_report_history, get_last_report_summary,
    load_project_state, save_project_state,
)
from qc_utils import classify_score, delivery_decision, get_env_username, get_logger, now_str, utext

logger = get_logger()


def _print_result(output, result):
    output.close_others()
    output.set_title(u"Kurumsal Kalite Kontrol v4")

    output.print_md(u"# Kurumsal Çizim Kalite Kontrol")
    output.print_md(u"**Proje:** {0}".format(result['project_name']))
    output.print_md(u"**Dosya:** {0}".format(result['document_title']))
    output.print_md(u"**Disiplin:** {0}".format(result['discipline_name']))
    output.print_md(u"**Rapor ID:** {0}".format(result['report_id']))

    gsd = result.get('general_score_data', {})
    output.print_md(u"---")
    output.print_md(u"## Genel Skor: {0}/100".format(result['total_score']))
    output.print_md(u"- **BIM Formu Skoru:** {0}/100 (ağırlık: %{1})".format(
        gsd.get('bim_form_score', 0), int(gsd.get('bim_weight', 0.5) * 100)))
    output.print_md(u"- **Diğer QC Skoru:** {0}/100 (ağırlık: %{1})".format(
        gsd.get('other_qc_score', 0), int(gsd.get('qc_weight', 0.5) * 100)))
    output.print_md(u"- **Kalite Sınıfı:** {0}".format(result['quality_class']))
    output.print_md(u"- **Teslim Kararı:** {0}".format(result['delivery_decision']))
    output.print_md(u"- *Title block verileri skora dahil değildir*")

    # İmza
    sig = result.get('signature') or {}
    output.print_md(u"---")
    output.print_md(u"## İmza: {0} / {1}".format(sig.get('full_name'), sig.get('title')))

    # Kategori skorları (Diğer QC)
    output.print_md(u"---")
    output.print_md(u"## Diğer QC — Kategori Sonuçları")
    for row in result['rows']:
        output.print_md(u"- **{0}** | Ağ:{1} | Puan:{2}/5 | Katkı:{3} | {4}".format(
            row['category'], row['weight'], row['score5'], row['weighted_score'], row['note']))

    # BIM form özet
    output.print_md(u"---")
    output.print_md(u"## BIM Formu Uygunluğu")
    bim = result.get('bim_form_score', {})
    output.print_md(u"- Otomatik skor: {0}/100".format(bim.get('auto_score', 0)))
    output.print_md(u"- Manuel teyit bekleyen: {0} madde".format(bim.get('pending_count', 0)))

    # Pafta personel bilgileri (skor dışı)
    output.print_md(u"---")
    output.print_md(u"## Pafta Personel Bilgileri (skor dışı)")
    sp = result.get('sheet_personnel_metadata', [])
    if sp:
        output.print_md(u"- Toplam pafta: {0}".format(len(sp)))
        for p in sp[:5]:
            output.print_md(u"- {0} | Drawn: {1} | Designed: {2}".format(
                p.get('sheet_number'), p.get('drawn_by'), p.get('designed_by')))
        if len(sp) > 5:
            output.print_md(u"- ... ve {0} pafta daha (Excel'de tam liste)".format(len(sp) - 5))

    # Kırmızı bayraklar
    output.print_md(u"---")
    output.print_md(u"## Kırmızı Bayraklar")
    if result['red_flags']:
        for flag in result['red_flags']:
            output.print_md(u"- {0}".format(flag))
    else:
        output.print_md(u"- Kırmızı bayrak yok.")

    # Karşılaştırma
    cmp = result.get('comparison') or {}
    if cmp.get('has_previous'):
        output.print_md(u"---")
        output.print_md(u"## Önceki Raporla Fark: {0} | Δ{1}".format(
            cmp.get('status'), cmp.get('total_score_delta')))


def main():
    doc = revit.doc
    output = script.get_output()

    if doc.IsFamilyDocument:
        forms.alert(u"Family dosyasında çalışmaz.", exitscript=True)

    state, source = load_project_state(doc)
    state = state or {}

    standard, standard_source, _ = load_company_standard(state)
    discipline_code = state.get('discipline_code')
    if not discipline_code:
        forms.alert(u"Önce 'Kurumsal Ayarlar' ile disiplin seçin.", exitscript=True)

    signature = state.get('signature') or {}
    if not signature.get('username'):
        signature['username'] = get_env_username()
    if not signature.get('full_name'):
        signature['full_name'] = signature.get('username')
    if not signature.get('title'):
        signature['title'] = u"Kalite Kontrol Sorumlusu"
    if not signature.get('signed_at'):
        signature['signed_at'] = now_str()

    previous_summary = get_last_report_summary(state, discipline_code)
    result = evaluate_document(
        doc=doc, discipline_code=discipline_code, standard=standard,
        state_source=source, signature=signature, previous_summary=previous_summary,
    )
    result['standard_summary'] = get_standard_summary(standard, standard_source)

    # --- Manuel kontrol UI ---
    bim_form_results = result.get('bim_form_results', [])
    pending_count = sum(1 for r in bim_form_results if r.get('needs_manual'))
    if pending_count > 0:
        ask_manual = forms.alert(
            u"{0} adet madde manuel teyit bekliyor.\n\nŞimdi kontrol ekranını açmak ister misiniz?".format(pending_count),
            yes=True, no=True,
        )
        if ask_manual:
            bim_form_results = show_manual_check_ui(bim_form_results)
            result['bim_form_results'] = bim_form_results
            # BIM skoru ve genel skoru yeniden hesapla
            new_bim_score = compute_bim_form_score(bim_form_results)
            result['bim_form_score'] = new_bim_score
            new_general = compute_general_score(
                result['other_qc_score'], new_bim_score, standard
            )
            result['general_score_data'] = new_general
            result['total_score'] = new_general['general_score']
            result['quality_class'] = classify_score(result['total_score'], standard)
            result['delivery_decision'] = delivery_decision(
                result['total_score'], len(result['red_flags']), standard
            )

    # Çıktıyı yazdır
    _print_result(output, result)

    # State kaydet
    max_history = get_history_limit(standard)
    state['discipline_code'] = discipline_code
    state['discipline_name'] = result['discipline_name']
    state['signature'] = signature
    state['standard_json_path'] = utext(state.get('standard_json_path')).strip()
    state['last_result'] = {
        'report_id': result['report_id'], 'run_time': result['run_time'],
        'total_score': result['total_score'], 'quality_class': result['quality_class'],
        'delivery_decision': result['delivery_decision'],
        'red_flag_count': len(result['red_flags']),
    }
    result['summary'] = {
        'report_id': result['report_id'], 'run_time': result['run_time'],
        'discipline_code': result['discipline_code'], 'discipline_name': result['discipline_name'],
        'total_score': result['total_score'], 'quality_class': result['quality_class'],
        'delivery_decision': result['delivery_decision'],
        'red_flags': list(result.get('red_flags', [])),
        'red_flag_count': len(result.get('red_flags', [])),
        'category_scores': {row['category']: row['score5'] for row in result.get('rows', [])},
        'metrics_snapshot': {},
        'signature': dict(result.get('signature') or {}),
    }
    state = append_report_history(state, discipline_code, result['summary'], max_count=max_history)
    save_ok, save_msg, _ = save_project_state(doc, state)
    if not save_ok:
        output.print_md(u"---")
        output.print_md(u"## ⚠ State: {0}".format(save_msg))

    # Merkezi log
    log_ok, log_msg, _ = write_central_log(result, standard)
    output.print_md(u"---")
    output.print_md(u"## Merkezi Log: {0}".format(u"Başarılı" if log_ok else log_msg))

    # ========================================
    # EXPORT UI — SADECE "CSV + JSON" veya "Hayır"
    # ========================================
    export_choice = forms.CommandSwitchWindow.show(
        [u'CSV + JSON', u'Hayır'],
        message=u"Rapor dışa aktarılsın mı?\n\nGenel Skor: {0}/100 — {1}".format(
            result['total_score'], result['quality_class']),
    )

    if not export_choice or export_choice == u'Hayır':
        return

    default_base = u"QC_{0}_{1}".format(
        result['discipline_name'].replace(' ', '_').replace('/', '_'),
        doc.Title.replace(' ', '_'),
    )

    csv_path = forms.save_file(file_ext='csv', default_name=default_base + u".csv")
    if csv_path:
        try:
            export_csv_report(result, csv_path)
            json_path = csv_path[:-4] + '.json' if csv_path.lower().endswith('.csv') else csv_path + '.json'
            export_json_report(result, json_path)
            forms.alert(u"CSV + JSON oluşturuldu:\n{0}\n{1}".format(csv_path, json_path))
        except Exception as exc:
            forms.alert(u"Export hatası: {0}".format(exc))
            logger.error(u"Export hatası: %s", exc)


if __name__ == '__main__':
    main()
