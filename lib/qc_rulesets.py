# -*- coding: utf-8 -*-
"""Sabit veri kümeleri ve varsayılan standart üretici v4.

Title Block kategorisi skordan çıkarıldı.
BIM formu %50, diğer QC %50 ağırlıkla çalışır.
Ağırlıklar sadece 'diğer QC' kısmını temsil eder (toplam 100).
"""
from __future__ import division

DISCIPLINE_LABELS = {
    'MIMARI': u'Mimari',
    'STATIK': u'Statik / Kalıp',
    'MEKANIK': u'Mekanik',
    'ELEKTRIK': u'Elektrik',
}

DISCIPLINE_CHOICES = ['MIMARI', 'STATIK', 'MEKANIK', 'ELEKTRIK']

DEFAULT_VIEW_NAME_PREFIXES = [
    u"Copy of ", u"Section ", u"Elevation ", u"3D View ",
    u"Drafting View ", u"Callout ", u"Legend ",
    u"Floor Plan ", u"Ceiling Plan ", u"Area Plan ",
    u"Kopya - ", u"Kopyası - ", u"Kesit ", u"Cephe ",
    u"3B Görünüş ", u"Taslak Görünüş ", u"Detay Çağrısı ",
    u"Açıklama ", u"Kat Planı ", u"Tavan Planı ", u"Alan Planı ",
]

DEFAULT_VIEW_NAME_EXACT = [
    u"{3D}", u"Section", u"Elevation", u"3D View",
    u"Drafting View", u"Callout", u"Legend",
    u"{3B}", u"Kesit", u"Cephe", u"3B Görünüş",
    u"Taslak Görünüş", u"Açıklama",
]

# ---------------------------------------------------------------------------
# Kategori sıralaması — Title Block KATEGORİSİ YOK (skor dışı)
# ---------------------------------------------------------------------------

COMMON_CATEGORY_ORDER = [
    u"Uyarı Yönetimi",
    u"Modelleme Disiplini",
    u"Temel Kurgu",
]

DISCIPLINE_CATEGORY_ORDER = {
    'MIMARI': [
        u"Model Kapsamı (Mimari)",
        u"Görünüş ve Sunum",
    ],
    'STATIK': [
        u"Taşıyıcı Sistem Kapsamı",
        u"Kalıp Projesi Kapsamı",
    ],
    'MEKANIK': [
        u"Mekanik Sistem Kapsamı",
        u"Dağıtım ve Ekipman Kapsamı",
    ],
    'ELEKTRIK': [
        u"Elektrik Sistem Kapsamı",
        u"Hat ve Cihaz Kapsamı",
    ],
}

# Ağırlıklar — Bu kısım "Diğer QC" skorunu temsil eder.
# Toplam 100 üzerinden hesaplanır, sonra genel skorda %50 ağırlıkla kullanılır.
DEFAULT_COMMON_CATEGORY_WEIGHTS = [
    {'category': u"Uyarı Yönetimi", 'weight': 20},
    {'category': u"Modelleme Disiplini", 'weight': 15},
    {'category': u"Temel Kurgu", 'weight': 15},
]

DEFAULT_DISCIPLINE_CATEGORY_WEIGHTS = {
    'MIMARI': [
        {'category': u"Model Kapsamı (Mimari)", 'weight': 25},
        {'category': u"Görünüş ve Sunum", 'weight': 25},
    ],
    'STATIK': [
        {'category': u"Taşıyıcı Sistem Kapsamı", 'weight': 25},
        {'category': u"Kalıp Projesi Kapsamı", 'weight': 25},
    ],
    'MEKANIK': [
        {'category': u"Mekanik Sistem Kapsamı", 'weight': 25},
        {'category': u"Dağıtım ve Ekipman Kapsamı", 'weight': 25},
    ],
    'ELEKTRIK': [
        {'category': u"Elektrik Sistem Kapsamı", 'weight': 25},
        {'category': u"Hat ve Cihaz Kapsamı", 'weight': 25},
    ],
}

DEFAULT_RED_FLAG_THRESHOLDS_COMMON = {
    'warnings': 100,
    'empty_sheets': 3,
    'unloaded_links': 1,
    'inplace_families': 5,
    'cad_imports': 3,
    'default_named_views': 10,
}

DEFAULT_DISCIPLINE_RED_FLAGS = {
    'MIMARI': [
        {'metric': 'rooms_count', 'max_value': 0, 'text': u"Mahal/oda bulunamadı"},
        {'metric': 'walls_count', 'max_value': 0, 'text': u"Duvar bulunamadı"},
        {'metric': 'doors_count', 'max_value': 0, 'text': u"Kapı bulunamadı"},
    ],
    'STATIK': [
        {'metric': 'structural_columns_count', 'max_value': 0, 'text': u"Strüktürel kolon bulunamadı"},
        {'metric': 'structural_framing_count', 'max_value': 0, 'text': u"Strüktürel kiriş bulunamadı"},
    ],
    'MEKANIK': [
        {'metric': 'mechanical_equipment_count', 'max_value': 0, 'text': u"Mekanik ekipman bulunamadı"},
        {'metric': 'mep_curve_total', 'max_value': 0, 'text': u"Duct/Pipe sistemi bulunamadı"},
    ],
    'ELEKTRIK': [
        {'metric': 'electrical_equipment_count', 'max_value': 0, 'text': u"Elektrik ekipmanı bulunamadı"},
        {'metric': 'electrical_device_total', 'max_value': 0, 'text': u"Aydınlatma/cihaz bulunamadı"},
    ],
}

DEFAULT_MANUAL_REVIEW_ITEMS = {
    'MIMARI': [
        u"Kapı yönleri ve mahal fonksiyonuna uygunluk",
        u"Pencere parapet ve başlık kotlarının doğruluğu",
        u"Kesitlerin model ile birebir uyumu",
        u"Detay çağrılarının doğru paftaya gitmesi",
    ],
    'STATIK': [
        u"Kolon-kiriş birleşim geometrisinin doğru çözülmesi",
        u"Kalıp pafta detaylarının kesit/plan uyumu",
        u"Perde ve çekirdek boşluklarının kalıp gösteriminde doğruluğu",
    ],
    'MEKANIK': [
        u"Duct ve pipe çakışmalarının disiplinler arası çözülmesi",
        u"Şaft ve tavan boşluklarının yeterliliği",
        u"Sistem isimlendirme ve şema-pafta uyumu",
    ],
    'ELEKTRIK': [
        u"Panel, devre ve yük dağılımı mantığının proje standardına uyumu",
        u"Kablo tavası ve conduit güzergah çakışmalarının çözülmesi",
        u"Etiket, devre ve panel schedule tutarlılığı",
    ],
}


def build_default_standard():
    return {
        'metadata': {
            'company': u'Kurumsal Sirket',
            'standard_name': u'Revit Kalite Standardı',
            'version': u'4.0.0',
            'last_updated': u'2026-04-07',
        },
        'score_classes': [
            {'min': 85, 'label': u'A - Çok İyi'},
            {'min': 70, 'label': u'B - İyi'},
            {'min': 55, 'label': u'C - Orta'},
            {'min': 40, 'label': u'D - Zayıf'},
            {'min': 0, 'label': u'E - Kritik'},
        ],
        'delivery_rules': [
            {'min_score': 85, 'max_red_flags': 0, 'label': u'Teslime Uygun'},
            {'min_score': 70, 'max_red_flags': 2, 'label': u'Düzeltmelerle Teslime Yakın'},
            {'min_score': 55, 'max_red_flags': 999, 'label': u'Ciddi Revizyon Gerekli'},
            {'min_score': 0, 'max_red_flags': 999, 'label': u'Teslime Uygun Değil'},
        ],
        'scoring': {
            'bim_form_weight': 0.50,
            'other_qc_weight': 0.50,
        },
        'history': {'max_reports_per_discipline': 15},
        'central_logging': {
            'enabled': True, 'mode': 'file',
            'path': r'%APPDATA%\pyRevit\RevitKaliteKontrol\central_logs',
        },
        'view_name_prefixes': list(DEFAULT_VIEW_NAME_PREFIXES),
        'view_name_exact': list(DEFAULT_VIEW_NAME_EXACT),
        'common': {
            'category_weights': list(DEFAULT_COMMON_CATEGORY_WEIGHTS),
            'red_flag_thresholds': dict(DEFAULT_RED_FLAG_THRESHOLDS_COMMON),
        },
        'disciplines': dict(
            (code, {
                'label': DISCIPLINE_LABELS.get(code, code),
                'category_weights': list(DEFAULT_DISCIPLINE_CATEGORY_WEIGHTS.get(code, [])),
                'discipline_red_flags': list(DEFAULT_DISCIPLINE_RED_FLAGS.get(code, [])),
                'manual_review_items': list(DEFAULT_MANUAL_REVIEW_ITEMS.get(code, [])),
            })
            for code in DISCIPLINE_CHOICES
        ),
    }
