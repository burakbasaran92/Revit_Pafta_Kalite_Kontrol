# -*- coding: utf-8 -*-
"""Kurumsal Ayarlar butonu.

Disiplin seçimi, kullanıcı imzası ve harici standart JSON yolunu
DataStorage / fallback'e kaydeder.
"""
from __future__ import print_function

from pyrevit import forms, revit

from qc_rulesets import DISCIPLINE_CHOICES
from qc_standard import (
    get_discipline_label,
    load_company_standard,
    load_standard_from_path,
    validate_standard_schema,
)
from qc_storage import load_project_state, save_project_state
from qc_utils import get_env_username, get_logger, now_str, utext

logger = get_logger()


def _ask_text(title, prompt, default_value):
    """Kullanıcıdan metin girişi ister."""
    return forms.ask_for_string(
        default=default_value,
        prompt=prompt,
        title=title,
    )


def _pick_json_file(current_path):
    """Kullanıcıdan JSON dosyası seçtirmeyi dener.
    Başarısızsa metin girişine düşer."""
    try:
        # pyRevit forms.pick_file ile dosya seçici
        picked = forms.pick_file(
            file_ext='json',
            title=u"Şirket Kalite Standardı JSON Dosyası Seç",
        )
        if picked:
            return utext(picked)
    except Exception:
        pass

    # Fallback: metin girişi
    return _ask_text(
        u"Şirket kalite standardı JSON",
        u"Harici JSON yolu gir.\nBoş bırakırsan paket içindeki varsayılan standart kullanılır.",
        current_path,
    )


def main():
    doc = revit.doc
    if doc.IsFamilyDocument:
        forms.alert(
            u"Bu araç proje dosyası içindir. Family dosyasında kullanılamaz.",
            exitscript=True,
        )

    state, source = load_project_state(doc)
    state = state or {}

    standard, standard_source, standard_error = load_company_standard(state)
    current_discipline = state.get('discipline_code')

    # --- Disiplin seçimi ---
    labels = []
    reverse = {}
    for code in DISCIPLINE_CHOICES:
        label = get_discipline_label(standard, code)
        display = label
        if code == current_discipline:
            display = u"{0}  [mevcut]".format(label)
        labels.append(display)
        reverse[label] = code

    selected = forms.SelectFromList.show(
        labels,
        title=u"Proje disiplini seç",
        button_name=u"Devam",
        multiselect=False,
        width=480,
    )
    if not selected:
        forms.alert(u"Ayarlar güncellenmedi.")
        return

    # Seçim etiketinden kodu çıkar — [mevcut] etiketini temizle
    clean_selected = selected.replace(u"  [mevcut]", u"")
    selected_code = reverse.get(clean_selected)
    if not selected_code:
        forms.alert(u"Disiplin eşlenemedi: {0}".format(selected))
        return

    # --- İmza bilgileri ---
    signature = state.get('signature') or {}
    username = utext(signature.get('username')) or get_env_username()

    full_name = _ask_text(
        u"Kullanıcı bazlı imza",
        u"Ad Soyad",
        utext(signature.get('full_name')) or username,
    )
    if full_name is None:
        forms.alert(u"İşlem iptal edildi.")
        return

    title = _ask_text(
        u"Kullanıcı bazlı imza",
        u"Unvan",
        utext(signature.get('title')) or u"Kalite Kontrol Sorumlusu",
    )
    if title is None:
        forms.alert(u"İşlem iptal edildi.")
        return

    # --- Harici standart JSON seçimi ---
    current_standard_path = utext(state.get('standard_json_path')).strip()
    standard_json_path = _pick_json_file(current_standard_path)
    if standard_json_path is None:
        forms.alert(u"İşlem iptal edildi.")
        return

    # Seçilen JSON'u doğrula
    standard_json_path = utext(standard_json_path).strip()
    if standard_json_path:
        test_data, _, load_err = load_standard_from_path(standard_json_path)
        if load_err:
            proceed = forms.alert(
                u"Standart JSON yüklenirken uyarı:\n{0}\n\nDevam etmek istiyor musun?".format(load_err),
                yes=True,
                no=True,
            )
            if not proceed:
                return
        elif test_data:
            is_valid, errors = validate_standard_schema(test_data)
            if not is_valid:
                proceed = forms.alert(
                    u"Standart JSON schema uyarıları:\n{0}\n\nDevam etmek istiyor musun?".format(
                        u"\n".join(errors)
                    ),
                    yes=True,
                    no=True,
                )
                if not proceed:
                    return

    # --- Kaydet ---
    state['discipline_code'] = selected_code
    state['discipline_name'] = get_discipline_label(standard, selected_code)
    state['signature'] = {
        'username': username,
        'full_name': full_name,
        'title': title,
        'signed_at': now_str(),
    }
    state['standard_json_path'] = standard_json_path
    state['updated_at'] = now_str()

    ok, message, store_ref = save_project_state(doc, state)
    if ok:
        std_info = (
            u"Varsayılan kurumsal standart"
            if not state['standard_json_path']
            else state['standard_json_path']
        )
        forms.alert(
            u"Ayarlar kaydedildi.\n\n"
            u"Disiplin: {0}\n"
            u"İmza: {1} / {2}\n"
            u"Standart: {3}\n"
            u"Kayıt yeri: {4}".format(
                state['discipline_name'],
                state['signature']['full_name'],
                state['signature']['title'],
                std_info,
                store_ref,
            )
        )
    else:
        forms.alert(u"Ayarlar kaydedilemedi: {0}".format(message))
        logger.error(u"State kaydetme hatası: %s", message)


if __name__ == '__main__':
    main()
