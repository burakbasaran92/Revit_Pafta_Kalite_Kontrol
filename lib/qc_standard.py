# -*- coding: utf-8 -*-
"""Şirket kalite standardı yükleme ve doğrulama.

3 katmanlı merge: hardcoded default → paket içi JSON → harici JSON.
"""
from __future__ import division, print_function

import copy
import io
import json
import os

from qc_rulesets import (
    COMMON_CATEGORY_ORDER,
    DEFAULT_VIEW_NAME_EXACT,
    DEFAULT_VIEW_NAME_PREFIXES,
    DISCIPLINE_CATEGORY_ORDER,
    DISCIPLINE_CHOICES,
    DISCIPLINE_LABELS,
    build_default_standard,
)
from qc_utils import expand_path, get_logger, utext

logger = get_logger()

# ---------------------------------------------------------------------------
# JSON merge
# ---------------------------------------------------------------------------


def _deep_merge(base, override):
    """Dict'leri recursive birleştirir. List'ler tamamen override edilir."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {}
        for key in base.keys():
            merged[key] = copy.deepcopy(base[key])
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


# ---------------------------------------------------------------------------
# Schema doğrulama
# ---------------------------------------------------------------------------

_REQUIRED_TOP_KEYS = ['metadata', 'common', 'disciplines']
_REQUIRED_METADATA_KEYS = ['company', 'standard_name', 'version']


def validate_standard_schema(data):
    """Standart JSON'un zorunlu alanlarını kontrol eder.
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    if not isinstance(data, dict):
        return False, [u"Standart verisi dict değil"]

    for key in _REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(u"Zorunlu üst anahtar eksik: '{0}'".format(key))

    md = data.get('metadata')
    if isinstance(md, dict):
        for key in _REQUIRED_METADATA_KEYS:
            if not md.get(key):
                errors.append(u"metadata.{0} boş veya eksik".format(key))

    common = data.get('common')
    if isinstance(common, dict):
        cw = common.get('category_weights')
        if cw is not None and not isinstance(cw, list):
            errors.append(u"common.category_weights list olmalı")
    else:
        if 'common' in data:
            errors.append(u"'common' dict olmalı")

    disciplines = data.get('disciplines')
    if isinstance(disciplines, dict):
        for code in DISCIPLINE_CHOICES:
            if code not in disciplines:
                errors.append(u"disciplines.{0} eksik".format(code))
    else:
        if 'disciplines' in data:
            errors.append(u"'disciplines' dict olmalı")

    return (len(errors) == 0), errors


# ---------------------------------------------------------------------------
# Yükleme
# ---------------------------------------------------------------------------

def get_bundled_standard_path():
    """Paket içi varsayılan standart JSON yolunu döndürür."""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'standards',
        'company_quality_standard.json',
    )


def load_standard_from_path(path_text):
    """Belirtilen yoldan standart JSON yükler.
    Returns:
        (data_dict | None, resolved_path | None, error_message | None)
    """
    path_text = expand_path(path_text)
    if not path_text:
        return None, None, u"JSON yolu boş"
    if not os.path.exists(path_text):
        return None, None, u"JSON yolu bulunamadı: {0}".format(path_text)
    try:
        with io.open(path_text, 'r', encoding='utf-8') as fp:
            data = json.loads(fp.read())
    except (ValueError, IOError, OSError) as exc:
        return None, None, u"JSON okunamadı: {0} — {1}".format(path_text, exc)

    is_valid, schema_errors = validate_standard_schema(data)
    if not is_valid:
        logger.warning(u"Standart JSON schema uyarıları: %s", schema_errors)
        # Uyarı verir ama yine de döndürür — kısmi override mümkün olsun

    return data, path_text, None


def load_company_standard(state=None):
    """Şirket kalite standardını 3 katmanlı merge ile yükler.
    Returns:
        (merged_standard, source_path, error_or_None)
    """
    default_standard = build_default_standard()
    bundled_path = get_bundled_standard_path()
    bundled_data, _, bundled_error = load_standard_from_path(bundled_path)
    if bundled_data:
        default_standard = _deep_merge(default_standard, bundled_data)

    state = state or {}
    external_path = utext(state.get('standard_json_path')).strip()
    if external_path:
        user_data, resolved_path, err = load_standard_from_path(external_path)
        if user_data:
            merged = _deep_merge(default_standard, user_data)
            return merged, resolved_path, None
        return default_standard, bundled_path, err

    return default_standard, bundled_path, bundled_error


# ---------------------------------------------------------------------------
# Veri erişim fonksiyonları
# ---------------------------------------------------------------------------

def get_discipline_label(standard, discipline_code):
    """Disiplin etiketini döndürür."""
    d = ((standard or {}).get('disciplines') or {}).get(discipline_code) or {}
    return utext(d.get('label')) or DISCIPLINE_LABELS.get(discipline_code, discipline_code)


def _weights_to_map(items):
    result = {}
    for item in items or []:
        result[utext(item.get('category'))] = int(item.get('weight', 0))
    return result


def get_category_weights(standard, discipline_code):
    """Sıralı (category, weight) tuple listesi döndürür.
    Toplam ağırlığı da kontrol eder ve uyarı verir."""
    standard = standard or {}
    common_map = _weights_to_map(
        ((standard.get('common') or {}).get('category_weights') or [])
    )
    discipline_map = _weights_to_map(
        (((standard.get('disciplines') or {}).get(discipline_code) or {}).get('category_weights') or [])
    )

    rows = []
    for category in COMMON_CATEGORY_ORDER:
        if category in common_map:
            rows.append((category, common_map[category]))
    for category in DISCIPLINE_CATEGORY_ORDER.get(discipline_code, []):
        if category in discipline_map:
            rows.append((category, discipline_map[category]))

    # Ağırlık toplamı kontrolü
    total = sum(w for _, w in rows)
    if total != 100:
        logger.warning(
            u"Ağırlık toplamı 100 değil! Disiplin: %s, toplam: %s",
            discipline_code, total,
        )

    return rows


def get_common_red_flag_thresholds(standard):
    """Ortak kırmızı bayrak eşiklerini döndürür."""
    return ((standard or {}).get('common') or {}).get('red_flag_thresholds') or {}


def get_discipline_red_flags(standard, discipline_code):
    """Disipline özgü kırmızı bayrak kurallarını döndürür."""
    return (
        (((standard or {}).get('disciplines') or {}).get(discipline_code) or {})
        .get('discipline_red_flags') or []
    )


def get_manual_review_items(standard, discipline_code):
    """Manuel kontrol maddelerini döndürür."""
    return list(
        (((standard or {}).get('disciplines') or {}).get(discipline_code) or {})
        .get('manual_review_items') or []
    )


def get_history_limit(standard):
    """Disiplin başına tutulacak maksimum rapor sayısını döndürür."""
    try:
        return int(
            (((standard or {}).get('history') or {}).get('max_reports_per_discipline'))
            or 15
        )
    except Exception:
        return 15


def get_view_name_prefixes(standard):
    """Standart JSON'dan view isim prefix listesini döndürür.
    Yoksa varsayılan listeyi döndürür."""
    return (standard or {}).get('view_name_prefixes') or list(DEFAULT_VIEW_NAME_PREFIXES)


def get_view_name_exact(standard):
    """Standart JSON'dan exact view isim listesini döndürür."""
    return (standard or {}).get('view_name_exact') or list(DEFAULT_VIEW_NAME_EXACT)


def get_standard_summary(standard, source_path):
    """Standart metadata özetini döndürür."""
    md = (standard or {}).get('metadata') or {}
    return {
        'company': utext(md.get('company')),
        'standard_name': utext(md.get('standard_name')),
        'version': utext(md.get('version')),
        'last_updated': utext(md.get('last_updated')),
        'source_path': utext(source_path),
    }
