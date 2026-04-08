# -*- coding: utf-8 -*-
"""Rapor Geçmişi butonu.

Seçili disiplin için modelde kayıtlı rapor geçmişini listeler.
Skor trendi, kalite sınıfı değişimleri ve kırmızı bayrak sayılarını
pyRevit çıktı penceresinde gösterir.
"""
from __future__ import print_function

from pyrevit import forms, revit, script

from qc_rulesets import DISCIPLINE_CHOICES
from qc_standard import get_discipline_label, load_company_standard
from qc_storage import get_report_history, load_project_state
from qc_utils import get_logger, utext

logger = get_logger()


def main():
    doc = revit.doc
    output = script.get_output()

    if doc.IsFamilyDocument:
        forms.alert(
            u"Bu araç proje dosyası içindir.",
            exitscript=True,
        )

    state, source = load_project_state(doc)
    state = state or {}

    standard, _, _ = load_company_standard(state)

    # Disiplin seçimi
    labels = []
    reverse = {}
    for code in DISCIPLINE_CHOICES:
        label = get_discipline_label(standard, code)
        count = len(get_report_history(state, code))
        display = u"{0}  ({1} rapor)".format(label, count)
        labels.append(display)
        reverse[display] = code

    selected = forms.SelectFromList.show(
        labels,
        title=u"Geçmişini görmek istediğin disiplini seç",
        button_name=u"Göster",
        multiselect=False,
        width=480,
    )
    if not selected:
        return

    discipline_code = reverse.get(selected)
    if not discipline_code:
        forms.alert(u"Disiplin eşlenemedi.")
        return

    history = get_report_history(state, discipline_code)
    discipline_name = get_discipline_label(standard, discipline_code)

    output.close_others()
    output.set_title(u"Rapor Geçmişi — {0}".format(discipline_name))

    output.print_md(u"# Rapor Geçmişi: {0}".format(discipline_name))
    output.print_md(u"**Toplam kayıtlı rapor:** {0}".format(len(history)))

    if not history:
        output.print_md(u"\nBu disiplin için henüz kayıtlı rapor bulunmuyor.")
        output.print_md(u"Önce **Kurumsal QC** komutunu çalıştırın.")
        return

    output.print_md(u"---")

    # Tablo başlığı
    output.print_md(u"| # | Tarih | Skor | Sınıf | Teslim Kararı | Kırmızı Bayrak | Rapor ID |")
    output.print_md(u"|---|-------|------|-------|---------------|----------------|----------|")

    for idx, report in enumerate(history, 1):
        output.print_md(
            u"| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
                idx,
                utext(report.get('run_time', '')),
                utext(report.get('total_score', '')),
                utext(report.get('quality_class', '')),
                utext(report.get('delivery_decision', '')),
                utext(report.get('red_flag_count', 0)),
                utext(report.get('report_id', '')),
            )
        )

    # Trend özeti
    output.print_md(u"---")
    output.print_md(u"## Trend Özeti")

    scores = []
    for r in history:
        try:
            scores.append(float(r.get('total_score', 0)))
        except (ValueError, TypeError):
            scores.append(0.0)

    if len(scores) >= 2:
        first = scores[0]
        last = scores[-1]
        delta = round(last - first, 2)
        best = round(max(scores), 2)
        worst = round(min(scores), 2)

        if delta > 0:
            trend = u"📈 İyileşme trendi (+{0})".format(delta)
        elif delta < 0:
            trend = u"📉 Gerileme trendi ({0})".format(delta)
        else:
            trend = u"➡ Değişim yok"

        output.print_md(u"- **Genel trend:** {0}".format(trend))
        output.print_md(u"- **İlk skor:** {0} → **Son skor:** {1}".format(
            round(first, 2), round(last, 2),
        ))
        output.print_md(u"- **En iyi:** {0} | **En kötü:** {1}".format(best, worst))
    else:
        output.print_md(u"- Trend hesabı için en az 2 rapor gerekli.")

    # Son rapor detayı
    latest = history[-1]
    output.print_md(u"---")
    output.print_md(u"## Son Rapor Detayı")
    output.print_md(u"- **Rapor ID:** {0}".format(latest.get('report_id')))
    output.print_md(u"- **Tarih:** {0}".format(latest.get('run_time')))
    output.print_md(u"- **Skor:** {0}/100".format(latest.get('total_score')))
    output.print_md(u"- **Kalite Sınıfı:** {0}".format(latest.get('quality_class')))
    output.print_md(u"- **Teslim Kararı:** {0}".format(latest.get('delivery_decision')))

    flags = latest.get('red_flags', [])
    if flags:
        output.print_md(u"### Kırmızı Bayraklar")
        for flag in flags:
            output.print_md(u"- {0}".format(flag))

    cat_scores = latest.get('category_scores', {})
    if cat_scores:
        output.print_md(u"### Kategori Puanları")
        for cat in sorted(cat_scores.keys()):
            output.print_md(u"- **{0}:** {1}/5".format(cat, cat_scores[cat]))

    sig = latest.get('signature', {})
    if sig.get('full_name'):
        output.print_md(u"### Kontrol Eden")
        output.print_md(u"- {0} / {1}".format(
            sig.get('full_name'), sig.get('title'),
        ))


if __name__ == '__main__':
    main()
