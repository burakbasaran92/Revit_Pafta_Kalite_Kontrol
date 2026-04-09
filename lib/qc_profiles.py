# -*- coding: utf-8 -*-
"""Disiplin bazli kalite profilleri.

Her disiplin icin aktif kontroller, agirliklar, esikler ve
zorunlu pafta kurallari tanimlanir. JSON ile override edilebilir.
"""
from __future__ import division, print_function


# ---------------------------------------------------------------------------
# Profil tanimlari
# ---------------------------------------------------------------------------

PROFILES = {
    'STATIK': {
        'label': u'Statik / Kalip',
        'code': 'STRUCTURAL_FORMWORK',
        'category_weights': {
            u'Uyari Yonetimi': 15,
            u'Modelleme Disiplini': 10,
            u'Temel Kurgu': 10,
            u'Tasiyici Sistem': 20,
            u'Kalip Proje Kapsami': 15,
            u'Pafta Kalitesi': 15,
            u'Annotation ve Olcu': 15,
        },
        'min_pass_score': 55,
        'critical_checks': [
            'structural_columns_count',
            'structural_framing_count',
            'floors_count',
            'sheet_count',
            'section_view_count',
        ],
        'required_views': ['plan', 'section', 'detail'],
        'naming_blacklist': [
            u"Copy of", u"Section 1", u"Unnamed",
        ],
    },
    'MIMARI': {
        'label': u'Mimari',
        'code': 'ARCHITECTURE',
        'category_weights': {
            u'Uyari Yonetimi': 10,
            u'Modelleme Disiplini': 10,
            u'Temel Kurgu': 10,
            u'Model Kapsami': 20,
            u'Gorunus ve Sunum': 15,
            u'Pafta Kalitesi': 20,
            u'Annotation ve Olcu': 15,
        },
        'min_pass_score': 55,
        'critical_checks': [
            'rooms_count',
            'walls_count',
            'sheet_count',
            'doors_count',
        ],
        'required_views': ['plan', 'section', 'elevation', 'detail'],
        'naming_blacklist': [
            u"Copy of", u"Section 1", u"Unnamed", u"Room",
        ],
    },
    'MEKANIK': {
        'label': u'Mekanik',
        'code': 'MECHANICAL',
        'category_weights': {
            u'Uyari Yonetimi': 10,
            u'Modelleme Disiplini': 10,
            u'Temel Kurgu': 5,
            u'Sistem Kapsami': 20,
            u'Baglanti Kalitesi': 15,
            u'Pafta Kalitesi': 15,
            u'Etiket ve Parametre': 15,
            u'Schedule Hazirlik': 10,
        },
        'min_pass_score': 55,
        'critical_checks': [
            'mechanical_equipment_count',
            'mep_curve_total',
            'sheet_count',
        ],
        'required_views': ['plan', 'section'],
        'naming_blacklist': [
            u"Copy of", u"Unnamed",
        ],
    },
    'ELEKTRIK': {
        'label': u'Elektrik',
        'code': 'ELECTRICAL',
        'category_weights': {
            u'Uyari Yonetimi': 10,
            u'Modelleme Disiplini': 10,
            u'Temel Kurgu': 5,
            u'Sistem Kapsami': 15,
            u'Devre Kalitesi': 20,
            u'Pafta Kalitesi': 15,
            u'Etiket ve Parametre': 15,
            u'Schedule Hazirlik': 10,
        },
        'min_pass_score': 55,
        'critical_checks': [
            'electrical_equipment_count',
            'electrical_device_total',
            'sheet_count',
        ],
        'required_views': ['plan'],
        'naming_blacklist': [
            u"Copy of", u"Unnamed",
        ],
    },
}


def get_profile(discipline_code):
    """Disiplin koduna gore profil dondurur."""
    return PROFILES.get(discipline_code, PROFILES.get('MIMARI'))


def get_category_weights(discipline_code):
    """Profildeki kategori agirliklarini dondurur."""
    profile = get_profile(discipline_code)
    return profile.get('category_weights', {})


def get_critical_checks(discipline_code):
    """Kritik kontrol metriklerini dondurur."""
    profile = get_profile(discipline_code)
    return profile.get('critical_checks', [])
