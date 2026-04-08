# -*- coding: utf-8 -*-
from __future__ import print_function
import os

from pyrevit import revit, forms, script

from qc_engine import evaluate_document
from qc_report import export_csv_report
from qc_storage import save_to_model


def print_result(output, result):
    output.close_others()
    output.set_title(u"Çizim Kalite Kontrol")

    output.print_md(u"# Çizim Kalite Kontrol Raporu")
    output.print_md(u"**Proje:** {0}".format(result['project_name']))
    output.print_md(u"**Dosya:** {0}".format(result['document_title']))
    output.print_md(u"**Toplam Skor:** {0}/100".format(result['total_score']))
    output.print_md(u"**Kalite Sınıfı:** {0}".format(result['quality_class']))
    output.print_md(u"**Teslim Kararı:** {0}".format(result['delivery_decision']))
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
    output.print_md(u"## Ham Metrikler")
    for key in sorted(result['metrics'].keys()):
        output.print_md(u"- **{0}**: {1}".format(key, result['metrics'][key]))


def main():
    doc = revit.doc
    output = script.get_output()

    if doc.IsFamilyDocument:
        forms.alert(u"Bu araç proje dosyası için tasarlandı. Family dosyasında çalıştırma.", exitscript=True)

    result = evaluate_document(doc)
    print_result(output, result)

    save_choice = forms.alert(
        u"CSV raporu dışa aktarılsın mı?\n\nToplam skor: {0}/100".format(result['total_score']),
        yes=True,
        no=True
    )

    if save_choice:
        default_name = u"Revit_Kalite_Raporu_{0}.csv".format(doc.Title.replace(' ', '_'))
        csv_path = forms.save_file(file_ext='csv', default_name=default_name)
        if csv_path:
            export_csv_report(result, csv_path)
            forms.alert(u"CSV raporu oluşturuldu:\n{0}".format(csv_path))

    # Şimdilik pasif; 2. fazda gerçek storage tamamlanacak.
    # ok, message = save_to_model(doc, result)


if __name__ == '__main__':
    main()
