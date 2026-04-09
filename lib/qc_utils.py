# -*- coding: utf-8 -*-
"""Ortak yardimci fonksiyonlar — IronPython uyumlu.

Tum modul tarafindan kullanilan safe helper'lar:
- parameter okuma (null-safe)
- unicode donusum
- skor hesaplama
- path yonetimi
- loglama
"""
from __future__ import division, print_function

import logging
import os
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
_logger = None


def get_logger(name="RevitKaliteKontrol"):
    global _logger
    if _logger is not None:
        return _logger
    try:
        from pyrevit import script
        _logger = script.get_logger()
    except Exception:
        _logger = logging.getLogger(name)
        if not _logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "[%(levelname)s] %(name)s: %(message)s"
            ))
            _logger.addHandler(handler)
            _logger.setLevel(logging.DEBUG)
    return _logger


# ---------------------------------------------------------------------------
# Unicode / string
# ---------------------------------------------------------------------------

def utext(value):
    """Herhangi bir degeri guvenli unicode string'e cevirir."""
    if value is None:
        return u""
    try:
        return unicode(value)
    except NameError:
        return str(value)


def safe_str(value, fallback=u""):
    """None-safe string donusumu."""
    if value is None:
        return fallback
    result = utext(value).strip()
    if not result:
        return fallback
    return result


# ---------------------------------------------------------------------------
# Revit parameter okuma — NULL-SAFE
# ---------------------------------------------------------------------------

def safe_param(element, param_name, fallback=u""):
    """Element'ten parametre degerini guvenli okur.
    Once instance, sonra type parametresini dener.
    Hicbir durumda exception firlatmaz."""
    if element is None:
        return fallback
    # Instance seviyesi
    try:
        p = element.LookupParameter(param_name)
        if p is not None and p.HasValue:
            val = p.AsValueString()
            if val is None:
                val = p.AsString()
            if val is not None and utext(val).strip():
                return utext(val).strip()
    except Exception:
        pass
    # Type seviyesi
    try:
        type_id = element.GetTypeId()
        if type_id is not None:
            doc = element.Document
            etype = doc.GetElement(type_id)
            if etype is not None:
                p = etype.LookupParameter(param_name)
                if p is not None and p.HasValue:
                    val = p.AsValueString()
                    if val is None:
                        val = p.AsString()
                    if val is not None and utext(val).strip():
                        return utext(val).strip()
    except Exception:
        pass
    return fallback


def safe_builtin_param(element, builtin_param, fallback=u""):
    """BuiltInParameter ile guvenli parametre okuma."""
    if element is None:
        return fallback
    try:
        p = element.get_Parameter(builtin_param)
        if p is not None and p.HasValue:
            val = p.AsValueString()
            if val is None:
                val = p.AsString()
            if val is not None and utext(val).strip():
                return utext(val).strip()
    except Exception:
        pass
    return fallback


def safe_element_name(element, fallback=u""):
    """Element ismini guvenli okur."""
    if element is None:
        return fallback
    try:
        name = element.Name
        if name is not None:
            return utext(name)
    except Exception:
        pass
    return fallback


# ---------------------------------------------------------------------------
# Tarih / zaman
# ---------------------------------------------------------------------------

def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ---------------------------------------------------------------------------
# Skor hesaplama
# ---------------------------------------------------------------------------

def ratio_to_score(ratio):
    """0.0-1.0 araligindaki orani 0-5 arasi tam puana cevirir."""
    if ratio >= 0.95:
        return 5
    elif ratio >= 0.85:
        return 4
    elif ratio >= 0.70:
        return 3
    elif ratio >= 0.50:
        return 2
    elif ratio > 0:
        return 1
    return 0


def weighted_percent(score5, weight):
    return round((float(score5) / 5.0) * float(weight), 2)


def score_from_presence(present_count, total_count):
    if total_count <= 0:
        return 0
    return ratio_to_score(float(present_count) / float(total_count))


def classify_score(total_score, standard):
    classes = list((standard or {}).get('score_classes', []))
    classes.sort(key=lambda x: x.get('min', 0), reverse=True)
    for item in classes:
        if total_score >= float(item.get('min', 0)):
            return utext(item.get('label'))
    return u"Tanimsiz"


def delivery_decision(total_score, red_flag_count, standard):
    rules = list((standard or {}).get('delivery_rules', []))
    rules.sort(key=lambda x: x.get('min_score', 0), reverse=True)
    for item in rules:
        min_s = float(item.get('min_score', 0))
        max_f = int(item.get('max_red_flags', 9999))
        if total_score >= min_s and red_flag_count <= max_f:
            return utext(item.get('label'))
    return u"Tanimsiz"


def validate_total_weight(weights, expected=100):
    total = sum(w for _, w in weights)
    return (total == expected), total


# ---------------------------------------------------------------------------
# Dosya / path yonetimi
# ---------------------------------------------------------------------------

def get_env_username():
    return (
        os.environ.get('USERNAME')
        or os.environ.get('USER')
        or os.environ.get('COMPUTERNAME')
        or u"bilinmeyen_kullanici"
    )


def expand_path(path_text):
    if not path_text:
        return path_text
    return os.path.expandvars(os.path.expanduser(path_text))


def ensure_folder(folder):
    if folder and not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as exc:
            get_logger().error(u"Klasor olusturulamadi: %s", exc)
            raise
    return folder


_slug_re = re.compile(r'[^A-Za-z0-9._-]+')


def slugify(value, fallback='x'):
    txt = utext(value).strip()
    if not txt:
        return fallback
    txt = txt.replace(' ', '_')
    txt = _slug_re.sub('_', txt)
    txt = re.sub(r'_+', '_', txt).strip('._')
    return txt or fallback


_digits_re = re.compile(r'\d+')


def normalize_flag_key(flag_text):
    return _digits_re.sub('#', utext(flag_text))


# ---------------------------------------------------------------------------
# Naming pattern helpers
# ---------------------------------------------------------------------------

# Varsayilan / kotu isim pattern'lari
BAD_NAME_PATTERNS = [
    u"Copy of", u"Kopya", u"Unnamed", u"New", u"Default",
    u"Section 1", u"Elevation 1", u"3D View 1",
    u"Floor Plan", u"Ceiling Plan", u"Level 1",
]


def is_bad_name(name):
    """Ismin varsayilan/kotu bir isim olup olmadigini kontrol eder."""
    n = utext(name).strip()
    if not n:
        return True
    for pattern in BAD_NAME_PATTERNS:
        if n.startswith(pattern) or n == pattern:
            return True
    return False
