# -*- coding: utf-8 -*-
"""Manuel kontrol UI modülü.

QC tamamlandıktan sonra kullanıcıya MANUAL ve SEMI_AUTO maddeler
için onay/red ekranı gösterir. Sonuçlar skora ve rapora yansır.
"""
from __future__ import division, print_function

from qc_utils import get_logger, utext

logger = get_logger()


def show_manual_check_ui(bim_form_results):
    """MANUAL ve SEMI_AUTO maddeler için kullanıcıdan onay alır.

    pyRevit forms.SelectFromList ile checklist gösterir.
    Kullanıcının onayladığı maddeler PASS (5 puan),
    onaylamadıkları FAIL (1 puan) olarak işaretlenir.

    Args:
        bim_form_results: evaluate_bim_form çıktısı (list of dict)

    Returns:
        list of dict: Güncellenmiş bim_form_results
    """
    try:
        from pyrevit import forms
    except ImportError:
        logger.warning(u"pyrevit.forms import edilemedi, manual check atlanıyor")
        return bim_form_results

    # Sadece pending (needs_manual=True) maddeleri topla
    pending_items = []
    pending_indices = []
    for i, item in enumerate(bim_form_results):
        if item.get('needs_manual', False):
            pending_items.append(item)
            pending_indices.append(i)

    if not pending_items:
        return bim_form_results

    # Checklist oluştur
    labels = []
    for item in pending_items:
        label = u"[{0}] {1}".format(item.get('id', ''), item.get('description', ''))
        labels.append(label)

    # Kullanıcıya göster
    selected = forms.SelectFromList.show(
        labels,
        title=u"Manuel Kontrol — Uygun Maddeleri İşaretleyin",
        button_name=u"Onayla",
        multiselect=True,
        width=700,
    )

    if selected is None:
        # Kullanıcı iptal etti — maddeler pending kalır
        logger.info(u"Manuel kontrol iptal edildi, maddeler pending kalıyor")
        return bim_form_results

    selected_set = set(selected)

    # Sonuçları güncelle
    for idx, label in zip(pending_indices, labels):
        item = bim_form_results[idx]
        if label in selected_set:
            # Kullanıcı onayladı → PASS
            item['score'] = 5
            item['status'] = u'Manuel onay: UYGUN'
            item['needs_manual'] = False
            item['user_approved'] = True
        else:
            # Kullanıcı onaylamadı → FAIL
            item['score'] = 1
            item['status'] = u'Manuel onay: UYGUN DEĞİL'
            item['needs_manual'] = False
            item['user_approved'] = False

    return bim_form_results
