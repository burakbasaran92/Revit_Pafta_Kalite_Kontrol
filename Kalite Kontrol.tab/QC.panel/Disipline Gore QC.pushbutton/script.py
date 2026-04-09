# -*- coding: utf-8 -*-
from __future__ import print_function
from datetime import datetime

from pyrevit import forms, revit, script

from qc_engine import evaluate_document
from qc_report import export_csv_report
from qc_rulesets import DISCIPLINE_CHOICES, DISCIPLINE_LABELS
from qc_storage import load_project_state, save_project_state


def _ask_discipline():
    selected = forms.SelectFromList.show(
        [DISCIPLINE_LABELS[x] for x in DISCIPLINE_CHOICES],
        title=u"QC için disiplin seç",
        button_name=u"Devam",
        multiselect=False,
        width=450,
    )
    if not selected:
        return None
    reverse = dict((v, k) for k, v in DISCIPLINE_LABELS.items())
    return reverse.get(selected)


def _print_result(output, result):
    output.close_others()
    output.set_title(u"Disipline Göre Kalite Kontrol")

    output.print_md(u"# Disipline Göre Çizim Kalite Kontrol")
    output.print_md(u"**Proje:** {0}".format(result['project_name']))
    output.print_md(u"**Dosya:** {0}".format(result['document_title']))
    output.print_md(u"**Disiplin:** {0}".format(result['discipline_name']))
    output.print_md(u"**Toplam Skor:** {0}/100".format(result['total_score']))
    output.print_md(u"**Kalite Sınıfı:** {0}".format(result['quality_class']))
    output.print_md(u"**Teslim Kararı:** {0}".format(result['delivery_decision']))
    output.print_md(u"**Durum Kaynağı:** {0}".format(result['state_source']))
    output.print_md(u"---")
    output.print_md(u"## Kategori Sonuçları")

    for row in result['rows']:
        line = u"- **{0}** | Ağırlık: {1} | Puan: {2}/5 | Katkı: {3} | {4}".format(
            row['category'], row['weight'], row['score5'], row['weighted_score'], row['note']
        )
        output.print_md(line)

    output.print_md(u"---")
    output.print_md(u"## Kırmızı Bayraklar")
    if result['red_flags']:
        for flag in result['red_flags']:
            output.print_md(u"- {0}".format(flag))
    else:
        output.print_md(u"- Kırmızı bayrak tespit edilmedi.")

    output.print_md(u"---")
    output.print_md(u"## Manuel Kontrol Gereken Maddeler")
    for item in result.get('manual_review_items', []):
        output.print_md(u"- {0}".format(item))

    output.print_md(u"---")
    output.print_md(u"## Ham Metrikler")
    for key in sorted(result['metrics'].keys()):
        output.print_md(u"- **{0}**: {1}".format(key, result['metrics'][key]))


def main():
    doc = revit.doc
    output = script.get_output()

    if doc.IsFamilyDocument:
        forms.alert(u"Bu araç proje dosyası için tasarlandı. Family dosyasında çalıştırma.", exitscript=True)

    state, source = load_project_state(doc)
    discipline_code = None
    if state:
        discipline_code = state.get('discipline_code')

    if not discipline_code:
        discipline_code = _ask_discipline()
        if not discipline_code:
            forms.alert(u"Disiplin seçimi yapılmadı. İşlem iptal edildi.")
            return
        payload = state or {}
        payload['discipline_code'] = discipline_code
        payload['discipline_name'] = DISCIPLINE_LABELS.get(discipline_code, discipline_code)
        payload['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_project_state(doc, payload)
        source = u"oturum içi seçim"

    result = evaluate_document(doc, discipline_code, state_source=source)
    _print_result(output, result)

    payload = state or {}
    payload['discipline_code'] = discipline_code
    payload['discipline_name'] = DISCIPLINE_LABELS.get(discipline_code, discipline_code)
    payload['last_result'] = {
        'run_time': result['run_time'],
        'total_score': result['total_score'],
        'quality_class': result['quality_class'],
        'delivery_decision': result['delivery_decision'],
        'red_flag_count': len(result['red_flags']),
    }
    save_project_state(doc, payload)

    save_choice = forms.alert(
        u"CSV raporu dışa aktarılsın mı?\n\nDisiplin: {0}\nToplam skor: {1}/100".format(
            result['discipline_name'], result['total_score']
        ),
        yes=True,
        no=True
    )

    if save_choice:
        default_name = u"Revit_{0}_Kalite_Raporu_{1}.csv".format(
            result['discipline_name'], doc.Title.replace(' ', '_')
        )
        csv_path = forms.save_file(file_ext='csv', default_name=default_name)
        if csv_path:
            export_csv_report(result, csv_path)
            forms.alert(u"CSV raporu oluşturuldu:\n{0}".format(csv_path))


if __name__ == '__main__':
    main()
