# -*- coding: utf-8 -*-
"""Ana orkestrasyon motoru v6.

Veri toplama → Kurallar → Puanlama → Rapor verisi.
IronPython uyumlu. Title block skor disi.
"""
from __future__ import division, print_function

from datetime import datetime

from qc_collectors import (
    collect_common_metrics,
    collect_discipline_metrics,
    collect_titleblock_details,
    summarize_titleblock,
)
from qc_rules import evaluate_common_rules, evaluate_discipline_rules, evaluate_personnel_status
from qc_actions import build_action_list, get_top_issues
from qc_scoring import (
    compute_bim_form_score,
    compute_general_score,
    compute_other_qc_score,
    evaluate_bim_form,
)
from qc_profiles import get_profile
from qc_utils import (
    classify_score,
    delivery_decision,
    get_logger,
    now_str,
    utext,
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


def evaluate_document(doc, discipline_code, standard,
                      state_source=None, signature=None, previous_summary=None):
    """Ana degerlendirme fonksiyonu.

    1) Veri topla
    2) Ortak kurallar calistir
    3) Disiplin kurallari calistir
    4) BIM form degerlendir
    5) Skor hesapla (%50 BIM + %50 QC)
    6) Rapor verisi olustur
    """

    # --- 1) Veri toplama ---
    metrics = {}
    metrics.update(collect_common_metrics(doc, standard))
    metrics.update(collect_discipline_metrics(doc))

    # Title block — SKOR DISI ama veri olarak toplanir
    tb_details = collect_titleblock_details(doc)
    tb_summary = summarize_titleblock(tb_details)

    # Sheet personnel metadata
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
            'date_time_stamp': fields.get('Date', u''),
        })

    # --- 2) Ortak kurallar ---
    common_findings, common_scores, common_notes, warning_penalty_note = evaluate_common_rules(metrics)

    # --- 3) Disiplin kurallari ---
    disc_findings, disc_scores, disc_notes = evaluate_discipline_rules(discipline_code, metrics)

    # Tum findings birlestir
    all_findings = common_findings + disc_findings

    # Kategori skorlarini birlestir
    all_category_scores = {}
    all_category_scores.update(common_scores)
    all_category_scores.update(disc_scores)

    # --- 4) BIM form ---
    bim_form_results = evaluate_bim_form(discipline_code, metrics)
    bim_score_data = compute_bim_form_score(bim_form_results)

    # --- 5) Skor hesapla ---
    other_qc_score = compute_other_qc_score(discipline_code, all_category_scores)
    general_score_data = compute_general_score(other_qc_score, bim_score_data, standard)
    total_score = general_score_data['general_score']

    # Red flags = CRITICAL findings
    red_flags = [f['message'] for f in all_findings if f.get('severity') == 'CRITICAL']

    # Profil bilgisi
    profile = get_profile(discipline_code)
    discipline_name = profile.get('label', discipline_code)

    # Signature
    sig = signature or {}
    signature_data = {
        'username': utext(sig.get('username', u'')),
        'full_name': utext(sig.get('full_name', u'')),
        'title': utext(sig.get('title', u'')),
        'signed_at': utext(sig.get('signed_at', u'')) or now_str(),
    }

    # Standard summary
    std_summary = {}
    if standard:
        md = standard.get('metadata', {})
        std_summary = {
            'company': utext(md.get('company', u'')),
            'standard_name': utext(md.get('standard_name', u'')),
            'version': utext(md.get('version', u'')),
        }

    # Aksiyon listesi
    action_list = build_action_list(all_findings, discipline_name)
    top_issues = get_top_issues(all_findings, 5)

    # Tum notes birlestir
    all_notes = {}
    all_notes.update(common_notes)
    all_notes.update(disc_notes)

    # Pafta personel durumu
    sheet_personnel_evaluated = evaluate_personnel_status(sheet_personnel)

    # Kategori satirlari (rapor icin)
    from qc_profiles import get_category_weights as _get_cw
    cat_weights = _get_cw(discipline_code)

    rows = []
    for cat, sc in sorted(all_category_scores.items()):
        w = cat_weights.get(cat, 10)
        rows.append({
            'category': cat,
            'weight': w,
            'score5': sc,
            'weighted_score': round((float(sc) / 5.0) * float(w), 2),
            'note': all_notes.get(cat, u''),
        })

    # --- 6) Rapor verisi ---
    result = {
        'report_id': u"{0}_{1}".format(discipline_code, datetime.now().strftime('%Y%m%d_%H%M%S')),
        'project_name': _get_project_name(doc),
        'document_title': utext(doc.Title),
        'document_path': utext(doc.PathName),
        'discipline_code': discipline_code,
        'discipline_name': discipline_name,
        'state_source': state_source or u"belirtilmedi",
        'run_time': now_str(),
        'total_score': total_score,
        'quality_class': classify_score(total_score, standard),
        'delivery_decision': delivery_decision(total_score, len(red_flags), standard),
        'rows': rows,
        'metrics': metrics,
        'red_flags': red_flags,
        'findings': all_findings,
        'category_scores': all_category_scores,
        'signature': signature_data,
        'standard_summary': std_summary,
        # Scoring breakdown
        'general_score_data': general_score_data,
        'other_qc_score': other_qc_score,
        'bim_form_results': bim_form_results,
        'bim_form_score': bim_score_data,
        # Title block — skor disi
        'titleblock_details': tb_details,
        'titleblock_summary': tb_summary,
        'sheet_personnel_metadata': sheet_personnel_evaluated,
        # Warning ceza etkisi
        'warning_penalty_note': warning_penalty_note,
        # Aksiyonlar
        'action_list': action_list,
        'top_issues': top_issues,
        # Yonetici ozeti
        'executive_summary': {
            'total_score': total_score,
            'critical_count': len(red_flags),
            'warning_count': len([f for f in all_findings if f.get('severity') == 'WARNING']),
            'info_count': len([f for f in all_findings if f.get('severity') == 'INFO']),
            'delivery_risk': len(red_flags) > 0,
            'top_issues': [f.get('message', u'') for f in top_issues],
        },
    }

    # Diff karsilastirma
    if previous_summary:
        try:
            from qc_diff import compare_reports
            summary_for_diff = {
                'report_id': result['report_id'],
                'run_time': result['run_time'],
                'total_score': result['total_score'],
                'quality_class': result['quality_class'],
                'delivery_decision': result['delivery_decision'],
                'red_flags': result['red_flags'],
                'category_scores': result['category_scores'],
                'metrics_snapshot': {},
            }
            result['comparison'] = compare_reports(summary_for_diff, previous_summary)
        except Exception:
            result['comparison'] = {}
    else:
        result['comparison'] = {}

    result['summary'] = {
        'report_id': result['report_id'],
        'run_time': result['run_time'],
        'discipline_code': discipline_code,
        'discipline_name': discipline_name,
        'total_score': total_score,
        'quality_class': result['quality_class'],
        'delivery_decision': result['delivery_decision'],
        'red_flags': list(red_flags),
        'red_flag_count': len(red_flags),
        'category_scores': dict(all_category_scores),
        'metrics_snapshot': {},
        'signature': dict(signature_data),
    }

    return result
