# -*- coding: utf-8 -*-
"""Puanlama motoru v6.

Genel Skor = (BIM Formu x 0.50) + (Diger QC x 0.50)

Diger QC skoru qc_rules.py'nin urettigi kategori skorlarindan
ve qc_profiles.py'deki agirliklardan hesaplanir.

Title block SKOR DISI.
"""
from __future__ import division, print_function

from qc_profiles import get_category_weights
from qc_utils import get_logger, ratio_to_score, utext

logger = get_logger()


# ---------------------------------------------------------------------------
# BIM form madde degerlendirme (v5'ten tasinmis, IronPython uyumlu)
# ---------------------------------------------------------------------------

def evaluate_bim_form_item(item, metrics):
    """Tek BIM form maddesini degerlendirir."""
    check_type = item.get('check_type', 'MANUAL')
    metric_key = item.get('metric_key')
    item_id = item.get('id', '')

    if check_type == 'MANUAL' or metric_key is None:
        return {'status': u'Manuel teyit gerekir', 'score': -1,
                'evidence': u'Otomatik kontrol edilemez', 'needs_manual': True}

    val = metrics.get(metric_key)

    # Madde bazli kurallar
    if item_id == 'BIM-G01':
        if not val:
            return _semi(u'Revit surumu okunamadi')
        try:
            ver = int(val)
            if ver >= 2022:
                sc = 5
            elif ver >= 2020:
                sc = 3
            else:
                sc = 1
        except (ValueError, TypeError):
            sc = 3
        return _auto(sc, u'Revit {0}'.format(val))

    if item_id == 'BIM-G03':
        if val is None or val < 0:
            return _semi(u'Dosya boyutu okunamadi')
        if val < 500:
            sc = 5
        elif val < 800:
            sc = 3
        else:
            sc = 1
        return _auto(sc, u'{0} MB'.format(val))

    if item_id == 'BIM-G04':
        if val is True:
            return _auto(3, u'Model workshared')
        return _auto(5, u'Model standalone')

    if item_id == 'BIM-G05':
        if val is None:
            return _semi(u'Warning okunamadi')
        if val <= 5:
            sc = 5
        elif val <= 20:
            sc = 4
        elif val <= 50:
            sc = 3
        elif val <= 100:
            sc = 2
        else:
            sc = 1
        return _auto(sc, u'{0} warning'.format(val))

    if item_id == 'BIM-G07':
        if val is None or val < 0:
            return _semi(u'Kullanilmayan family okunamadi')
        if val == 0:
            sc = 5
        elif val <= 10:
            sc = 4
        elif val <= 30:
            sc = 3
        else:
            sc = 1
        return _auto(sc, u'{0} kullanilmayan family'.format(val))

    if item_id == 'BIM-G08':
        if val:
            return _auto(5, u'Section box kapali 3D view var')
        return _auto(2, u'Section box kapali 3D view yok')

    if item_id == 'BIM-G09':
        if val:
            return _auto(5, u'Starting view var')
        return _auto(1, u'Starting view yok')

    if item_id == 'BIM-G10':
        v = val if val else 0
        return _auto(ratio_to_score(v), u'Proje bilgi %{0}'.format(int(v * 100)))

    if item_id == 'BIM-G11':
        v = val if val else 0
        if v == 0:
            return _auto(5, u'Tum linkler yuklu')
        elif v <= 2:
            return _auto(3, u'{0} yuklenmemis link'.format(v))
        return _auto(1, u'{0} yuklenmemis link'.format(v))

    if item_id == 'BIM-M13':
        v = val if val else 0
        return _auto(ratio_to_score(v), u'Level/Grid isimlendirme %{0}'.format(int(v * 100)))

    if item_id == 'BIM-M15':
        total = metrics.get('view_count', 0)
        if total == 0:
            return _semi(u'View bulunamadi')
        v = val if val else 0
        ratio = 1.0 - (v / float(total))
        return _auto(ratio_to_score(ratio), u'{0}/{1} view duzgun isimli'.format(total - v, total))

    if item_id == 'BIM-M16':
        total = metrics.get('sheet_count', 0)
        if total == 0:
            return _semi(u'Pafta bulunamadi')
        v = val if val else 0
        ratio = 1.0 - (v / float(total))
        return _auto(ratio_to_score(ratio), u'{0}/{1} pafta duzgun isimli'.format(total - v, total))

    if item_id == 'BIM-M19':
        total = metrics.get('room_total_count', 0)
        if total == 0:
            return _auto(3, u'Room bulunamadi')
        v = val if val else 0
        ratio = 1.0 - (v / float(total))
        return _auto(ratio_to_score(ratio), u'{0}/{1} room isimli'.format(total - v, total))

    if item_id == 'BIM-M21':
        if val:
            return _auto(5, u'Base/Survey point mevcut')
        return _auto(2, u'Base/Survey point kontrol gerekli')

    if item_id in ('BIM-M26', 'BIM-M27'):
        v = val if val else 0
        return _auto(ratio_to_score(v), u'View template %{0}'.format(int(v * 100)))

    if item_id == 'BIM-M28':
        v = val if val else 0
        if v >= 10:
            sc = 5
        elif v >= 5:
            sc = 4
        elif v >= 1:
            sc = 3
        else:
            sc = 1
        return _auto(sc, u'{0} project parameter'.format(v))

    if item_id == 'BIM-M29':
        v = val if val else 0
        return _auto(ratio_to_score(v), u'Pin orani %{0}'.format(int(v * 100)))

    if item_id == 'BIM-M30':
        if val:
            return _auto(5, u'Keynote table yuklu')
        return _auto(2, u'Keynote table yuklu degil')

    if item_id in ('BIM-M17', 'BIM-M32'):
        v = val if val else 0
        if v >= 5:
            sc = 5
        elif v >= 1:
            sc = 3
        else:
            sc = 0
        return _auto(sc, u'{0} schedule'.format(v))

    if item_id == 'BIM-M33':
        if val and utext(val).strip():
            return _auto(4, u'Antet: {0}'.format(val))
        return _auto(1, u'Antet bulunamadi')

    # Varsayilan SEMI_AUTO
    if check_type == 'SEMI_AUTO':
        return _semi(u'{0} = {1}'.format(metric_key, val))

    # Varsayilan AUTO
    if val is None:
        return _semi(u'{0} metrik yok'.format(metric_key))
    if isinstance(val, bool):
        if val:
            return _auto(5, u'{0}: Evet'.format(metric_key))
        return _auto(1, u'{0}: Hayir'.format(metric_key))
    if isinstance(val, (int, float)):
        if val > 0:
            return _auto(5, u'{0}: {1}'.format(metric_key, val))
        return _auto(1, u'{0}: {1}'.format(metric_key, val))
    return _semi(u'{0}: {1}'.format(metric_key, val))


def _auto(score, evidence):
    return {'status': u'Otomatik', 'score': score, 'evidence': evidence, 'needs_manual': False}

def _semi(evidence):
    return {'status': u'Yari-otomatik', 'score': -1, 'evidence': evidence, 'needs_manual': True}


# ---------------------------------------------------------------------------
# BIM form toplam
# ---------------------------------------------------------------------------

def evaluate_bim_form(discipline_code, metrics):
    """Tum BIM form maddelerini degerlendirir."""
    from qc_bim_form_config import get_applicable_items
    items = get_applicable_items(discipline_code)
    results = []
    for item in items:
        ev = evaluate_bim_form_item(item, metrics)
        results.append({
            'id': item['id'], 'description': item['description'],
            'phase': item['phase'], 'discipline': item['discipline'],
            'check_type': item['check_type'], 'weight': item['weight'],
            'category': item.get('category', u''),
            'status': ev['status'], 'score': ev['score'],
            'evidence': ev['evidence'], 'needs_manual': ev['needs_manual'],
            'user_approved': None,
        })
    return results


def compute_bim_form_score(bim_form_results):
    """BIM form sonuclarindan 0-100 arasi skor hesaplar."""
    scored_weight = 0
    weighted_sum = 0.0
    pending = 0
    for r in bim_form_results:
        w = r.get('weight', 1)
        if r['score'] < 0:
            pending += 1
        else:
            scored_weight += w
            weighted_sum += (r['score'] / 5.0) * w
    ratio = weighted_sum / float(scored_weight) if scored_weight > 0 else 0.5
    return {
        'auto_score': round(ratio * 100, 2),
        'pending_count': pending,
        'total_items': len(bim_form_results),
        'scored_weight': scored_weight,
        'ratio': round(ratio, 3),
    }


# ---------------------------------------------------------------------------
# Diger QC skoru — profil agirliklarindan
# ---------------------------------------------------------------------------

def compute_other_qc_score(discipline_code, category_scores):
    """Kural motoru skorlarindan agirliklari profil uzerinden hesaplar."""
    weights = get_category_weights(discipline_code)
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0

    weighted_sum = 0.0
    for cat, weight in weights.items():
        sc = category_scores.get(cat, 3)  # varsayilan 3/5
        weighted_sum += (float(sc) / 5.0) * float(weight)

    return round((weighted_sum / float(total_weight)) * 100, 2)


# ---------------------------------------------------------------------------
# Genel skor — %50 BIM + %50 QC
# ---------------------------------------------------------------------------

def compute_general_score(other_qc_score, bim_form_score_data, standard=None):
    scoring_cfg = (standard or {}).get('scoring', {})
    bim_w = float(scoring_cfg.get('bim_form_weight', 0.50))
    qc_w = float(scoring_cfg.get('other_qc_weight', 0.50))

    bim_100 = bim_form_score_data.get('auto_score', 0)
    bim_comp = bim_100 * bim_w
    qc_comp = other_qc_score * qc_w
    general = round(bim_comp + qc_comp, 2)

    return {
        'general_score': general,
        'bim_form_score': round(bim_100, 2),
        'other_qc_score': round(other_qc_score, 2),
        'bim_weight': bim_w, 'qc_weight': qc_w,
        'bim_component': round(bim_comp, 2),
        'qc_component': round(qc_comp, 2),
    }
