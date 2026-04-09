# -*- coding: utf-8 -*-
"""Aksiyon onerisi motoru.

Findings listesinden kullaniciya yonelik duzeltme aksiyonlari uretir.
Her aksiyon onceliklendirilir ve raporlanir.
"""
from __future__ import division, print_function


def build_action_list(findings, discipline_name=u""):
    """Findings listesinden oncelikli aksiyon listesi uretir."""
    actions = []
    priority = 0

    # Once CRITICAL, sonra WARNING
    criticals = [f for f in findings if f.get('severity') == 'CRITICAL']
    warnings = [f for f in findings if f.get('severity') == 'WARNING']

    for f in criticals:
        priority += 1
        actions.append({
            'priority': priority,
            'severity': 'CRITICAL',
            'discipline': discipline_name,
            'category': f.get('category', u''),
            'issue': f.get('message', u''),
            'action': f.get('action', u''),
            'affected_count': f.get('affected_count', 0),
        })

    for f in warnings:
        priority += 1
        actions.append({
            'priority': priority,
            'severity': 'WARNING',
            'discipline': discipline_name,
            'category': f.get('category', u''),
            'issue': f.get('message', u''),
            'action': f.get('action', u''),
            'affected_count': f.get('affected_count', 0),
        })

    return actions


def get_top_issues(findings, count=5):
    """En kritik N sorunu dondurur — yonetici ozeti icin."""
    criticals = [f for f in findings if f.get('severity') == 'CRITICAL']
    warnings = [f for f in findings if f.get('severity') == 'WARNING']
    combined = criticals + warnings
    return combined[:count]
