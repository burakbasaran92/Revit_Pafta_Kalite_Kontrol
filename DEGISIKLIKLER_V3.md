# -*- coding: utf-8 -*-
"""Önceki raporla fark analizi.

İki rapor özeti arasında skor, kategori, metrik ve kırmızı bayrak
farklarını hesaplar.
"""
from __future__ import division

from qc_utils import normalize_flag_key, utext


def compare_reports(current_summary, previous_summary):
    """Mevcut rapor özetini önceki raporla karşılaştırır.

    Args:
        current_summary: Güncel rapor özet dict'i
        previous_summary: Önceki rapor özet dict'i (veya None)

    Returns:
        dict: status, skor delta, bayrak farkları, kategori farkları vb.
    """
    if not previous_summary:
        return {
            'status': u'İlk rapor',
            'has_previous': False,
            'summary_text': u'Bu disiplin için daha önce kayıtlı rapor bulunmadı.',
            'total_score_delta': None,
            'quality_class_changed': False,
            'delivery_decision_changed': False,
            'red_flags_added': [],
            'red_flags_removed': [],
            'category_deltas': [],
            'metric_changes': [],
        }

    # --- Skor farkı ---
    prev_score = float(previous_summary.get('total_score', 0))
    cur_score = float(current_summary.get('total_score', 0))
    score_delta = round(cur_score - prev_score, 2)

    # --- Kalite / teslim kararı ---
    prev_quality = utext(previous_summary.get('quality_class'))
    cur_quality = utext(current_summary.get('quality_class'))
    prev_delivery = utext(previous_summary.get('delivery_decision'))
    cur_delivery = utext(current_summary.get('delivery_decision'))

    # --- Kırmızı bayrak fark analizi ---
    # Normalize edilmiş anahtar kullanarak dinamik sayılardan bağımsız karşılaştır
    prev_flags_raw = list(previous_summary.get('red_flags') or [])
    cur_flags_raw = list(current_summary.get('red_flags') or [])

    prev_flag_map = {}
    for f in prev_flags_raw:
        key = normalize_flag_key(f)
        prev_flag_map[key] = f

    cur_flag_map = {}
    for f in cur_flags_raw:
        key = normalize_flag_key(f)
        cur_flag_map[key] = f

    added_keys = set(cur_flag_map.keys()) - set(prev_flag_map.keys())
    removed_keys = set(prev_flag_map.keys()) - set(cur_flag_map.keys())

    red_flags_added = sorted([cur_flag_map[k] for k in added_keys])
    red_flags_removed = sorted([prev_flag_map[k] for k in removed_keys])

    # --- Kategori farkları ---
    prev_cat = previous_summary.get('category_scores') or {}
    cur_cat = current_summary.get('category_scores') or {}
    category_deltas = []
    all_cats = set(list(prev_cat.keys()) + list(cur_cat.keys()))
    for cat in sorted(all_cats):
        prev_val = float(prev_cat.get(cat, 0))
        cur_val = float(cur_cat.get(cat, 0))
        delta = round(cur_val - prev_val, 2)
        if delta != 0:
            category_deltas.append({
                'category': utext(cat),
                'previous': prev_val,
                'current': cur_val,
                'delta': delta,
            })
    category_deltas.sort(key=lambda x: abs(x['delta']), reverse=True)

    # --- Metrik farkları (en büyük 12 fark) ---
    prev_metrics = previous_summary.get('metrics_snapshot') or {}
    cur_metrics = current_summary.get('metrics_snapshot') or {}
    metric_changes = []
    for key in sorted(set(list(prev_metrics.keys()) + list(cur_metrics.keys()))):
        prev_val = prev_metrics.get(key, 0)
        cur_val = cur_metrics.get(key, 0)
        try:
            delta = cur_val - prev_val
        except Exception:
            continue
        if delta != 0:
            metric_changes.append({
                'metric': utext(key),
                'previous': prev_val,
                'current': cur_val,
                'delta': delta,
            })
    metric_changes.sort(key=lambda x: abs(x['delta']), reverse=True)
    metric_changes = metric_changes[:12]

    # --- Durum etiketi ---
    if score_delta > 0:
        status = u'İyileşme'
    elif score_delta < 0:
        status = u'Gerileme'
    else:
        status = u'Skor Değişmedi'

    summary_text = u"Önceki rapora göre skor farkı: {0}".format(score_delta)

    return {
        'status': status,
        'has_previous': True,
        'summary_text': summary_text,
        'previous_report_id': utext(previous_summary.get('report_id')),
        'previous_run_time': utext(previous_summary.get('run_time')),
        'total_score_delta': score_delta,
        'quality_class_changed': prev_quality != cur_quality,
        'delivery_decision_changed': prev_delivery != cur_delivery,
        'red_flags_added': red_flags_added,
        'red_flags_removed': red_flags_removed,
        'category_deltas': category_deltas,
        'metric_changes': metric_changes,
    }
