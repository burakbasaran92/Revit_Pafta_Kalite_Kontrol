# -*- coding: utf-8 -*-
"""Merkezi puanlama motoru v5.

Genel Skor = (BIM Formu x 0.50) + (Diğer QC x 0.50)
Title block skor dışı.
v5: Daha fazla AUTO madde, daha az MANUAL.
"""
from __future__ import division, print_function

from qc_bim_form_config import get_applicable_items
from qc_utils import get_logger, ratio_to_score, utext

logger = get_logger()


def evaluate_bim_form_item(item, metrics, tb_summary):
    check_type = item.get('check_type', 'MANUAL')
    metric_key = item.get('metric_key')
    item_id = item.get('id', '')

    if check_type == 'MANUAL' or metric_key is None:
        return {
            'status': u'Manuel teyit gerekir',
            'score': -1,
            'evidence': u'Otomatik kontrol edilemez',
            'needs_manual': True,
        }

    val = metrics.get(metric_key)

    # ===== AUTO MADDELER =====

    # G01 — Revit version (yeni AUTO)
    if item_id == 'BIM-G01':
        if not val:
            return _semi(u'Revit sürümü okunamadı')
        try:
            ver = int(val)
            score = 5 if ver >= 2022 else (3 if ver >= 2020 else 1)
        except (ValueError, TypeError):
            score = 3
        return _auto(score, u'Revit {0}'.format(val))

    # G03 — dosya boyutu
    if item_id == 'BIM-G03':
        if val is None or val < 0:
            return _semi(u'Dosya boyutu okunamadı')
        score = 5 if val < 500 else (3 if val < 800 else 1)
        return _auto(score, u'{0} MB'.format(val))

    # G04 — workshared/detach (yeni AUTO)
    if item_id == 'BIM-G04':
        if val is True:
            return _auto(3, u'Model workshared — detach durumu kontrol edilmeli')
        return _auto(5, u'Model standalone')

    # G05 — warning count
    if item_id == 'BIM-G05':
        if val is None: return _semi(u'Warning sayısı okunamadı')
        if val <= 5: score = 5
        elif val <= 20: score = 4
        elif val <= 50: score = 3
        elif val <= 100: score = 2
        else: score = 1
        return _auto(score, u'{0} warning'.format(val))

    # G07 — unused family / purge (yeni AUTO)
    if item_id == 'BIM-G07':
        if val is None or val < 0:
            return _semi(u'Kullanılmayan family sayısı okunamadı')
        if val == 0: score = 5
        elif val <= 10: score = 4
        elif val <= 30: score = 3
        elif val <= 60: score = 2
        else: score = 1
        return _auto(score, u'{0} kullanılmayan family'.format(val))

    # G08 — 3D section box
    if item_id == 'BIM-G08':
        return _auto(5 if val else 2, u'Section box kapalı 3D view: {0}'.format(u'var' if val else u'yok'))

    # G09 — starting view
    if item_id == 'BIM-G09':
        return _auto(5 if val else 1, u'Starting view: {0}'.format(u'var' if val else u'yok'))

    # G10 — project info
    if item_id == 'BIM-G10':
        val = val or 0
        return _auto(ratio_to_score(val), u'Proje bilgi doluluğu: %{0}'.format(int(val * 100)))

    # G11 — unloaded links
    if item_id == 'BIM-G11':
        val = val or 0
        return _auto(5 if val == 0 else (3 if val <= 2 else 1), u'{0} yüklenmemiş link'.format(val))

    # M13 — level/grid naming (yeni AUTO)
    if item_id == 'BIM-M13':
        if val is None: val = 0
        return _auto(ratio_to_score(val), u'Level/Grid isimlendirme oranı: %{0}'.format(int(val * 100)))

    # M15 — view naming
    if item_id == 'BIM-M15':
        total = metrics.get('view_count', 0)
        if total == 0: return _semi(u'View bulunamadı')
        ratio = 1.0 - (val / float(total)) if total > 0 else 0
        return _auto(ratio_to_score(ratio), u'{0}/{1} view düzgün isimli'.format(total - val, total))

    # M16 — sheet naming
    if item_id == 'BIM-M16':
        total = metrics.get('sheet_count', 0)
        if total == 0: return _semi(u'Pafta bulunamadı')
        ratio = 1.0 - (val / float(total)) if total > 0 else 0
        return _auto(ratio_to_score(ratio), u'{0}/{1} pafta düzgün isimli'.format(total - val, total))

    # M19 — room unnamed count (yeni AUTO)
    if item_id == 'BIM-M19':
        total = metrics.get('room_total_count', 0)
        if total == 0: return _auto(3, u'Room bulunamadı — nötr skor')
        ratio = 1.0 - (val / float(total))
        return _auto(ratio_to_score(ratio), u'{0}/{1} room isimli'.format(total - val, total))

    # M21 — base point valid (yeni AUTO)
    if item_id == 'BIM-M21':
        return _auto(5 if val else 2, u'Base/Survey point: {0}'.format(u'mevcut' if val else u'kontrol gerekli'))

    # M26/M27 — view template
    if item_id in ('BIM-M26', 'BIM-M27'):
        val = val or 0
        return _auto(ratio_to_score(val), u'View template oranı: %{0}'.format(int(val * 100)))

    # M28 — project parameters (yeni AUTO)
    if item_id == 'BIM-M28':
        val = val or 0
        if val >= 10: score = 5
        elif val >= 5: score = 4
        elif val >= 1: score = 3
        else: score = 1
        return _auto(score, u'{0} project parameter'.format(val))

    # M29 — pinned
    if item_id == 'BIM-M29':
        val = val or 0
        return _auto(ratio_to_score(val), u'Pin oranı: %{0}'.format(int(val * 100)))

    # M30 — keynote (yeni AUTO)
    if item_id == 'BIM-M30':
        return _auto(5 if val else 2, u'Keynote table: {0}'.format(u'yüklü' if val else u'yüklü değil'))

    # M32 — schedule count
    if item_id in ('BIM-M17', 'BIM-M32'):
        val = val or 0
        return _auto(5 if val >= 5 else (3 if val >= 1 else 0), u'{0} schedule'.format(val))

    # M33 — titleblock family name (yeni AUTO)
    if item_id == 'BIM-M33':
        if val and utext(val).strip():
            return _auto(4, u'Antet: {0}'.format(val))
        return _auto(1, u'Antet bulunamadı')

    # ===== SEMI_AUTO VARSAYILAN =====
    if check_type == 'SEMI_AUTO':
        return _semi(u'Yarı-otomatik: {0} = {1}'.format(metric_key, val))

    # AUTO ama özel kural yok
    if val is None:
        return _semi(u'Metrik bulunamadı: {0}'.format(metric_key))
    if isinstance(val, bool):
        return _auto(5 if val else 1, u'{0}: {1}'.format(metric_key, val))
    if isinstance(val, (int, float)):
        return _auto(5 if val > 0 else 1, u'{0}: {1}'.format(metric_key, val))
    return _semi(u'{0}: {1}'.format(metric_key, val))


def _auto(score, evidence):
    return {'status': u'Otomatik', 'score': score, 'evidence': evidence, 'needs_manual': False}

def _semi(evidence):
    return {'status': u'Yarı-otomatik', 'score': -1, 'evidence': evidence, 'needs_manual': True}


def evaluate_bim_form(discipline_code, metrics, tb_summary):
    items = get_applicable_items(discipline_code)
    results = []
    for item in items:
        ev = evaluate_bim_form_item(item, metrics, tb_summary)
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
    total_weight = 0
    scored_weight = 0
    weighted_sum = 0.0
    pending_count = 0
    for r in bim_form_results:
        w = r.get('weight', 1)
        total_weight += w
        if r['score'] < 0:
            pending_count += 1
        else:
            scored_weight += w
            weighted_sum += (r['score'] / 5.0) * w
    ratio = weighted_sum / float(scored_weight) if scored_weight > 0 else 0.5
    return {
        'auto_score': round(ratio * 100, 2),
        'pending_count': pending_count,
        'total_items': len(bim_form_results),
        'total_weight': total_weight,
        'scored_weight': scored_weight,
        'ratio': round(ratio, 3),
    }


def compute_general_score(other_qc_score, bim_form_score_data, standard=None):
    scoring_cfg = ((standard or {}).get('scoring') or {})
    bim_weight = float(scoring_cfg.get('bim_form_weight', 0.50))
    qc_weight = float(scoring_cfg.get('other_qc_weight', 0.50))
    bim_score_100 = bim_form_score_data.get('auto_score', 0)
    bim_component = bim_score_100 * bim_weight
    qc_component = other_qc_score * qc_weight
    general = round(bim_component + qc_component, 2)
    return {
        'general_score': general,
        'bim_form_score': round(bim_score_100, 2),
        'other_qc_score': round(other_qc_score, 2),
        'bim_weight': bim_weight, 'qc_weight': qc_weight,
        'bim_component': round(bim_component, 2),
        'qc_component': round(qc_component, 2),
    }


def build_action_list(result):
    actions = []
    p = 0
    for flag in result.get('red_flags', []):
        p += 1
        actions.append({
            'priority': p, 'discipline': result.get('discipline_name', u''),
            'category': u'Kırmızı Bayrak', 'issue': flag,
            'action': u'Acil düzeltme gerekli', 'affected_count': u'',
            'is_critical': True, 'check_type': 'AUTO',
        })
    for item in result.get('bim_form_results', []):
        if item.get('needs_manual'):
            p += 1
            actions.append({
                'priority': p, 'discipline': result.get('discipline_name', u''),
                'category': u'BIM Form', 'issue': item['description'],
                'action': u'Manuel teyit gerekir', 'affected_count': u'',
                'is_critical': False, 'check_type': item['check_type'],
            })
    return actions
