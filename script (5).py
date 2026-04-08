# -*- coding: utf-8 -*-
from __future__ import print_function
from datetime import datetime

from pyrevit import forms, revit

from qc_rulesets import DISCIPLINE_CHOICES, DISCIPLINE_LABELS
from qc_storage import load_project_state, save_project_state


def _select_discipline(current_code=None):
    options = []
    for code in DISCIPLINE_CHOICES:
        label = DISCIPLINE_LABELS.get(code, code)
        if current_code == code:
            label = u"{0}  [mevcut]".format(label)
        options.append(label)

    selected = forms.SelectFromList.show(
        options,
        title=u"Proje disiplini seç",
        button_name=u"Kaydet",
        multiselect=False,
        width=450,
    )
    if not selected:
        return None

    selected_clean = selected.replace(u"  [mevcut]", u"")
    reverse = dict((v, k) for k, v in DISCIPLINE_LABELS.items())
    return reverse.get(selected_clean)


def main():
    doc = revit.doc
    if doc.IsFamilyDocument:
        forms.alert(u"Bu araç proje dosyası içindir. Family dosyasında kullanma.", exitscript=True)

    state, source = load_project_state(doc)
    current_code = None
    if state:
        current_code = state.get('discipline_code')

    selected_code = _select_discipline(current_code=current_code)
    if not selected_code:
        forms.alert(u"Disiplin seçimi iptal edildi.")
        return

    payload = state or {}
    payload['discipline_code'] = selected_code
    payload['discipline_name'] = DISCIPLINE_LABELS.get(selected_code, selected_code)
    payload['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    ok, message, store_ref = save_project_state(doc, payload)
    if ok:
        forms.alert(
            u"Proje disiplini kaydedildi:\n\n{0}\n\nKayıt yeri: {1}".format(
                payload['discipline_name'], store_ref
            )
        )
    else:
        forms.alert(u"Disiplin kaydı başarısız: {0}".format(message))


if __name__ == '__main__':
    main()
