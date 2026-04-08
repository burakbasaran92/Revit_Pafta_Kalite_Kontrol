# -*- coding: utf-8 -*-
"""Genel yardımcı fonksiyonlar.

Tüm modüller tarafından kullanılan ortak araçlar:
unicode uyumluluk, skor hesaplama, path yönetimi, loglama.
"""
from __future__ import division, print_function

import logging
import os
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# pyRevit logger entegrasyonu
# ---------------------------------------------------------------------------
_logger = None


def get_logger(name="RevitKaliteKontrol"):
    """pyRevit logger varsa onu, yoksa standart logging döndürür."""
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
# Unicode uyumluluk
# ---------------------------------------------------------------------------

def utext(value):
    """Herhangi bir değeri güvenli unicode string'e çevirir.
    IronPython2 (unicode) ve CPython3 (str) ile uyumlu."""
    if value is None:
        return u""
    try:
        return unicode(value)
    except NameError:
        return str(value)


# ---------------------------------------------------------------------------
# Tarih / zaman
# ---------------------------------------------------------------------------

def now_str():
    """Şu anki zaman damgasını 'YYYY-MM-DD HH:MM:SS' formatında döndürür."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ---------------------------------------------------------------------------
# Skor hesaplama
# ---------------------------------------------------------------------------

def ratio_to_score(ratio):
    """0.0-1.0 arasındaki oranı 0-5 arası tam puana çevirir."""
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
    """0-5 puanı ağırlıkla yüzdelik katkıya çevirir."""
    return round((float(score5) / 5.0) * float(weight), 2)


def score_from_presence(present_count, total_count):
    """Varlık sayısı / toplam oranından skor üretir."""
    if total_count <= 0:
        return 0
    return ratio_to_score(float(present_count) / float(total_count))


def classify_score(total_score, standard):
    """Toplam skora göre kalite sınıfı etiketini döndürür (ör. A - Çok İyi)."""
    classes = list((standard or {}).get('score_classes', []))
    classes.sort(key=lambda x: x.get('min', 0), reverse=True)
    for item in classes:
        if total_score >= float(item.get('min', 0)):
            return utext(item.get('label'))
    return u"Tanımsız"


def delivery_decision(total_score, red_flag_count, standard):
    """Skor ve kırmızı bayrak sayısına göre teslim kararını belirler."""
    rules = list((standard or {}).get('delivery_rules', []))
    rules.sort(key=lambda x: x.get('min_score', 0), reverse=True)
    for item in rules:
        if (total_score >= float(item.get('min_score', 0))
                and red_flag_count <= int(item.get('max_red_flags', 9999))):
            return utext(item.get('label'))
    return u"Tanımsız"


# ---------------------------------------------------------------------------
# Ağırlık doğrulama
# ---------------------------------------------------------------------------

def validate_total_weight(weights, expected=100):
    """Kategori ağırlıklarının toplamını kontrol eder.
    Args:
        weights: [(category, weight), ...] listesi
        expected: beklenen toplam (varsayılan 100)
    Returns:
        (is_valid, actual_total)
    """
    total = sum(w for _, w in weights)
    return (total == expected), total


# ---------------------------------------------------------------------------
# Dosya / path yönetimi
# ---------------------------------------------------------------------------

def get_env_username():
    """İşletim sistemi oturum kullanıcı adını döndürür."""
    return (
        os.environ.get('USERNAME')
        or os.environ.get('USER')
        or os.environ.get('COMPUTERNAME')
        or u"bilinmeyen_kullanici"
    )


def expand_path(path_text):
    """Ortam değişkenlerini ve ~ ifadesini genişletir."""
    if not path_text:
        return path_text
    return os.path.expandvars(os.path.expanduser(path_text))


def ensure_folder(folder):
    """Klasörün var olduğundan emin olur; yoksa oluşturur.
    Raises:
        OSError: Klasör oluşturulamazsa
    """
    if folder and not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as exc:
            get_logger().error(u"Klasör oluşturulamadı: %s — %s", folder, exc)
            raise
    return folder


_slug_re = re.compile(r'[^A-Za-z0-9._-]+')


def slugify(value, fallback='x'):
    """Dosya adı için güvenli slug üretir. Non-ASCII ve özel
    karakterleri alt çizgiye çevirir."""
    txt = utext(value).strip()
    if not txt:
        return fallback
    txt = txt.replace(' ', '_')
    txt = _slug_re.sub('_', txt)
    txt = re.sub(r'_+', '_', txt).strip('._')
    return txt or fallback


# ---------------------------------------------------------------------------
# Red flag normalleştirme (diff karşılaştırması için)
# ---------------------------------------------------------------------------

_digits_re = re.compile(r'\d+')


def normalize_flag_key(flag_text):
    """Bayrak metnindeki dinamik sayıları '#' ile değiştirerek
    karşılaştırma anahtarı üretir.
    Örnek: 'Warning sayısı çok yüksek: 150' → 'Warning sayısı çok yüksek: #'
    """
    return _digits_re.sub('#', utext(flag_text))
