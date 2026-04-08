# -*- coding: utf-8 -*-
"""Ana değerlendirme motoru v4.

Genel Skor = (BIM Formu x 0.50) + (Diğer QC x 0.50)
Title block SKOR DIŞI — sadece raporlama verisi.
Statik = Kalıp Projesi mantığı korunuyor.
"""
from __future__ import division
from datetime import datetime

from qc_collectors import (
    collect_bim_form_metrics,
    collect_common_metrics,
    collect_discipline_metrics,
    collect_titleblock_details,
    summarize_titleblock,
)
from qc_diff import compare_reports
from qc_scoring import (
    build_action_list,
    compute_bim_form_score,
    compute_general_score,
    evaluate_bim_form,
)
from qc_standard import (
    get_category_weights,
    get_common_red_flag_thresholds,
    get_discipline_label,
    get_discipline_red_flags,
    get_manual_review_items,
    get_standard_summary,
)
from qc_utils import (
    classify_score,
    delivery_decision,
    get_logger,
    now_str,
    ratio_to_score,
    score_from_presence,
    utext,
    validate_total_weight,
    weighted_percent,
)

logger = get_logger()


def _get_project_name(doc):
    try:
        pinfo = doc.ProjectInformation
        parts = []
        if pinfo.Number:
            parts.append(utext(pinfo.Number))
        if pinfo.Name:
            parts.append(utext(pinfo.Name))
        if parts:
            return u" - ".join(parts)
    except Exception:
        pass
    return utext(doc.Title)


# ===================================================================
# ORTAK EVALUATOR'LAR
# ===================================================================

def _evaluate_warning_management(metrics, **kw):
    count = metrics.get('warning_count', 0)
    if count <= 5: score = 5
    elif count <= 20: score = 4
    elif count <= 50: score = 3
    elif count <= 100: score = 2
    elif count <= 200: score = 1
    else: score = 0
    return score, u"Warning: {0}".format(count)


def _evaluate_modeling_discipline(metrics, **kw):
    penalties = 0
    inp = metrics.get('inplace_family_count', 0)
    cad = metrics.get('cad_import_count', 0)
    if inp > 5: penalties += 3
    elif inp > 2: penalties += 2
    elif inp > 0: penalties += 1
    if cad > 5: penalties += 3
    elif cad > 2: penalties += 2
    elif cad > 0: penalties += 1
    return max(0, 5 - penalties), u"In-place: {0}, CAD import: {1}".format(inp, cad)


def _evaluate_basic_setup(metrics, **kw):
    levels = metrics.get('level_count', 0)
    grids = metrics.get('grid_count', 0)
    if levels > 0 and grids > 0: score = 5
    elif levels > 0 or grids > 0: score = 2
    else: score = 0
    return score, u"Level: {0}, Grid: {1}".format(levels, grids)


# ===================================================================
# MİMARİ
# ===================================================================

def _evaluate_arch_model_scope(metrics, **kw):
    checks = [
        metrics.get('rooms_count', 0) > 0,
        metrics.get('walls_count', 0) > 0,
        metrics.get('doors_count', 0) > 0,
        metrics.get('windows_count', 0) > 0,
        metrics.get('floors_count', 0) > 0,
        (metrics.get('stairs_count', 0) + metrics.get('ramps_count', 0)) > 0,
        metrics.get('ceilings_count', 0) > 0 or metrics.get('roofs_count', 0) > 0,
        metrics.get('shafts_count', 0) > 0,
    ]
    present = sum(1 for c in checks if c)
    return score_from_presence(present, len(checks)), u"8 kontrol, {0} mevcut".format(present)


def _evaluate_view_presentation(metrics, **kw):
    checks = [
        metrics.get('section_view_count', 0) > 0,
        metrics.get('detail_view_count', 0) > 0,
        metrics.get('elevation_view_count', 0) > 0,
        metrics.get('sheet_count', 0) > 0,
    ]
    present = sum(1 for c in checks if c)
    total = metrics.get('view_count', 0)
    default_named = metrics.get('default_named_view_count', 0)
    naming_ratio = (1.0 - default_named / float(total)) if total > 0 else 0
    base = score_from_presence(present, len(checks))
    naming_score = ratio_to_score(naming_ratio)
    score = max(0, min(5, (base + naming_score) // 2))
    return score, u"View çeşitlilik: {0}/4, isimlendirme: %{1}".format(present, int(naming_ratio * 100))


# ===================================================================
# STATİK / KALIP
# ===================================================================

def _evaluate_structural_system(metrics, **kw):
    checks = [
        metrics.get('structural_columns_count', 0) > 0,
        metrics.get('structural_framing_count', 0) > 0,
        metrics.get('floors_count', 0) > 0,
        metrics.get('walls_count', 0) > 0,
    ]
    present = sum(1 for c in checks if c)
    return score_from_presence(present, len(checks)), u"Kolon:{0} Kiriş:{1} Döşeme:{2} Duvar:{3}".format(
        metrics.get('structural_columns_count', 0), metrics.get('structural_framing_count', 0),
        metrics.get('floors_count', 0), metrics.get('walls_count', 0))


def _evaluate_kalip_project_scope(metrics, **kw):
    checks = [
        metrics.get('shafts_count', 0) > 0 or metrics.get('stairs_count', 0) > 0,
        metrics.get('section_view_count', 0) >= 2,
        metrics.get('detail_view_count', 0) >= 1,
        metrics.get('sheet_count', 0) >= 3,
    ]
    present = sum(1 for c in checks if c)
    score = score_from_presence(present, len(checks))
    bonus = []
    if metrics.get('structural_foundation_count', 0) > 0: bonus.append(u"temel mevcut")
    if metrics.get('rebar_count', 0) > 0: bonus.append(u"donatı mevcut")
    return score, u"Kalıp kapsam: {0}/4{1}".format(present, u" | Bonus: " + u", ".join(bonus) if bonus else u"")


# ===================================================================
# MEKANİK & ELEKTRİK
# ===================================================================

def _evaluate_mechanical_system(metrics, **kw):
    checks = [metrics.get('spaces_count', 0) > 0, metrics.get('mechanical_equipment_count', 0) > 0,
              metrics.get('mep_curve_total', 0) > 0]
    return score_from_presence(sum(1 for c in checks if c), len(checks)), u"Space:{0} Ekipman:{1} Curve:{2}".format(
        metrics.get('spaces_count', 0), metrics.get('mechanical_equipment_count', 0), metrics.get('mep_curve_total', 0))

def _evaluate_mechanical_distribution(metrics, **kw):
    checks = [
        (metrics.get('duct_fitting_count', 0) + metrics.get('duct_accessory_count', 0) + metrics.get('duct_terminal_count', 0)) > 0,
        (metrics.get('pipe_fitting_count', 0) + metrics.get('pipe_accessory_count', 0)) > 0,
        metrics.get('plumbing_fixture_count', 0) > 0 or metrics.get('mechanical_equipment_count', 0) > 0,
    ]
    return score_from_presence(sum(1 for c in checks if c), len(checks)), u"DuctFit:{0} PipeFit:{1}".format(
        metrics.get('duct_fitting_count', 0), metrics.get('pipe_fitting_count', 0))

def _evaluate_electrical_system(metrics, **kw):
    checks = [metrics.get('electrical_equipment_count', 0) > 0, metrics.get('electrical_device_total', 0) > 0,
              metrics.get('electrical_circuit_count', 0) > 0]
    return score_from_presence(sum(1 for c in checks if c), len(checks)), u"Ekip:{0} Cihaz:{1} Devre:{2}".format(
        metrics.get('electrical_equipment_count', 0), metrics.get('electrical_device_total', 0), metrics.get('electrical_circuit_count', 0))

def _evaluate_electrical_routes(metrics, **kw):
    checks = [metrics.get('electrical_route_total', 0) > 0, metrics.get('conduit_fitting_count', 0) > 0,
              (metrics.get('fire_alarm_device_count', 0) + metrics.get('data_device_count', 0) + metrics.get('communication_device_count', 0)) > 0]
    return score_from_presence(sum(1 for c in checks if c), len(checks)), u"Route:{0} ZayıfAkım:{1}".format(
        metrics.get('electrical_route_total', 0), metrics.get('fire_alarm_device_count', 0))


# ===================================================================
# EVALUATOR HARİTASI — Title block YOK
# ===================================================================

COMMON_EVALUATORS = {
    u"Uyarı Yönetimi": _evaluate_warning_management,
    u"Modelleme Disiplini": _evaluate_modeling_discipline,
    u"Temel Kurgu": _evaluate_basic_setup,
}

DISCIPLINE_EVALUATORS = {
    'MIMARI': {u"Model Kapsamı (Mimari)": _evaluate_arch_model_scope, u"Görünüş ve Sunum": _evaluate_view_presentation},
    'STATIK': {u"Taşıyıcı Sistem Kapsamı": _evaluate_structural_system, u"Kalıp Projesi Kapsamı": _evaluate_kalip_project_scope},
    'MEKANIK': {u"Mekanik Sistem Kapsamı": _evaluate_mechanical_system, u"Dağıtım ve Ekipman Kapsamı": _evaluate_mechanical_distribution},
    'ELEKTRIK': {u"Elektrik Sistem Kapsamı": _evaluate_electrical_system, u"Hat ve Cihaz Kapsamı": _evaluate_electrical_routes},
}


# ===================================================================
# KIRMIZI BAYRAKLAR
# ===================================================================

def _build_red_flags(metrics, discipline_code, standard):
    flags = []
    th = get_common_red_flag_thresholds(standard)
    if metrics.get('warning_count', 0) >= int(th.get('warnings', 100)):
        flags.append(u"Warning çok yüksek: {0}".format(metrics['warning_count']))
    if metrics.get('empty_sheet_count', 0) >= int(th.get('empty_sheets', 3)):
        flags.append(u"Boş pafta: {0}".format(metrics['empty_sheet_count']))
    if metrics.get('unloaded_link_count', 0) >= int(th.get('unloaded_links', 1)):
        flags.append(u"Yüklenmemiş link: {0}".format(metrics['unloaded_link_count']))
    if metrics.get('inplace_family_count', 0) >= int(th.get('inplace_families', 5)):
        flags.append(u"In-place family: {0}".format(metrics['inplace_family_count']))
    if metrics.get('cad_import_count', 0) >= int(th.get('cad_imports', 3)):
        flags.append(u"CAD import: {0}".format(metrics['cad_import_count']))
    if metrics.get('default_named_view_count', 0) >= int(th.get('default_named_views', 10)):
        flags.append(u"Varsayılan isimli view: {0}".format(metrics['default_named_view_count']))
    # TB artık red flag üretmez
    for item in get_discipline_red_flags(standard, discipline_code):
        key = item.get('metric')
        trigger = item.get('max_value', 0)
        val = metrics.get(key, 0)
        if val <= trigger:
            flags.append(utext(item.get('text')) + u" (değer: {0})".format(val))
    return flags


# ===================================================================
# RAPOR ÖZETİ
# ===================================================================

_SNAPSHOT_KEYS = [
    'warning_count', 'sheet_count', 'empty_sheet_count', 'view_count',
    'default_named_view_count', 'level_count', 'grid_count',
    'link_count', 'unloaded_link_count', 'cad_import_count', 'inplace_family_count',
    'rooms_count', 'walls_count', 'floors_count',
    'structural_columns_count', 'structural_framing_count',
    'mep_curve_total', 'electrical_device_total', 'electrical_route_total',
]

def _build_report_summary(result):
    metrics = result.get('metrics', {})
    snapshot = {k: metrics[k] for k in _SNAPSHOT_KEYS if k in metrics}
    return {
        'report_id': result['report_id'], 'run_time': result['run_time'],
        'discipline_code': result['discipline_code'], 'discipline_name': result['discipline_name'],
        'total_score': result['total_score'], 'quality_class': result['quality_class'],
        'delivery_decision': result['delivery_decision'],
        'red_flags': list(result.get('red_flags', [])),
        'red_flag_count': len(result.get('red_flags', [])),
        'category_scores': {row['category']: row['score5'] for row in result.get('rows', [])},
        'metrics_snapshot': snapshot,
        'signature': dict(result.get('signature') or {}),
        'standard_version': (result.get('standard_summary') or {}).get('version'),
    }


def _build_signature(sig):
    sig = sig or {}
    return {
        'username': utext(sig.get('username')), 'full_name': utext(sig.get('full_name')),
        'title': utext(sig.get('title')), 'signed_at': utext(sig.get('signed_at')) or now_str(),
    }


# ===================================================================
# ANA DEĞERLENDİRME
# ===================================================================

def evaluate_document(doc, discipline_code, standard, state_source=None,
                      signature=None, previous_summary=None):

    # --- Veri toplama ---
    metrics = {}
    metrics.update(collect_common_metrics(doc, standard))
    metrics.update(collect_discipline_metrics(doc))
    bim_metrics = collect_bim_form_metrics(doc)
    metrics.update(bim_metrics)

    # Title block — SKOR DIŞI ama veri olarak toplanır
    tb_details = collect_titleblock_details(doc)
    tb_summary = summarize_titleblock(tb_details)

    # Sheet personnel metadata — Excel/JSON raporlama için
    sheet_personnel = []
    for td in tb_details:
        fields = td.get('fields', {})
        sheet_personnel.append({
            'sheet_number': td.get('sheet_number', u''),
            'sheet_name': td.get('sheet_name', u''),
            'drawn_by': fields.get('Drawn By', u''),
            'designed_by': fields.get('Designed By', u''),
            'checked_by': fields.get('Checked By', u''),
            'approved_by': fields.get('Approved By', u''),
            'sheet_issue_date': fields.get('Sheet Issue Date', u''),
            'date_time_stamp': fields.get('Date', fields.get('Date/Time Stamp', u'')),
        })

    # --- BIM form değerlendirme ---
    bim_form_results = evaluate_bim_form(discipline_code, metrics, tb_summary)
    bim_score_data = compute_bim_form_score(bim_form_results)

    # --- Diğer QC skoru (kategoriler) ---
    weights = get_category_weights(standard, discipline_code)
    is_valid, actual_total = validate_total_weight(weights)
    if not is_valid:
        logger.warning(u"Ağırlık toplamı %s (beklenen 100), disiplin: %s", actual_total, discipline_code)

    evalmap = {}
    evalmap.update(COMMON_EVALUATORS)
    evalmap.update(DISCIPLINE_EVALUATORS.get(discipline_code, {}))

    rows = []
    other_qc_total = 0.0
    for category, weight in weights:
        evaluator = evalmap.get(category)
        if evaluator is None:
            logger.error(u"Evaluator bulunamadı: '%s'", category)
            score5, note = 0, u"Evaluator eksik"
        else:
            try:
                score5, note = evaluator(metrics)
            except Exception as exc:
                logger.error(u"Evaluator hatası '%s': %s", category, exc)
                score5, note = 0, u"Hata: {0}".format(exc)
        w_score = weighted_percent(score5, weight)
        other_qc_total += w_score
        rows.append({
            'category': category, 'weight': weight,
            'score5': score5, 'weighted_score': w_score, 'note': note,
        })

    other_qc_total = round(other_qc_total, 2)

    # --- GENEL SKOR: %50 BIM + %50 QC ---
    general_score_data = compute_general_score(other_qc_total, bim_score_data, standard)
    total = general_score_data['general_score']

    red_flags = _build_red_flags(metrics, discipline_code, standard)
    signature_data = _build_signature(signature)

    result = {
        'report_id': u"{0}_{1}".format(discipline_code, datetime.now().strftime('%Y%m%d_%H%M%S')),
        'project_name': _get_project_name(doc),
        'document_title': utext(doc.Title),
        'document_path': utext(doc.PathName),
        'discipline_code': discipline_code,
        'discipline_name': get_discipline_label(standard, discipline_code),
        'state_source': state_source or u"belirtilmedi",
        'run_time': now_str(),
        'total_score': total,
        'quality_class': classify_score(total, standard),
        'delivery_decision': delivery_decision(total, len(red_flags), standard),
        'rows': rows,
        'metrics': metrics,
        'red_flags': red_flags,
        'manual_review_items': get_manual_review_items(standard, discipline_code),
        'signature': signature_data,
        'standard_summary': get_standard_summary(standard, None),
        'weight_total': actual_total,
        # v4 alanları
        'other_qc_score': other_qc_total,
        'general_score_data': general_score_data,
        'titleblock_details': tb_details,
        'titleblock_summary': tb_summary,
        'sheet_personnel_metadata': sheet_personnel,
        'bim_form_results': bim_form_results,
        'bim_form_score': bim_score_data,
    }

    result['action_list'] = build_action_list(result)
    result['summary'] = _build_report_summary(result)
    result['comparison'] = compare_reports(result['summary'], previous_summary)
    return result
