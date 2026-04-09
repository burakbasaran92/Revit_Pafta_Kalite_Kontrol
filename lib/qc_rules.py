# -*- coding: utf-8 -*-
"""Kural motoru v6.1 — aciklama ureten, warning cezali.

Her kontrol:
  severity: CRITICAL / WARNING / INFO
  category, message, action, affected_count
  
Her kategori skoru icin ayrica:
  note: aciklama metni (hangi metrikler, guclu/zayif yanlar, gerekceler)
"""
from __future__ import division, print_function

from qc_utils import get_logger, score_from_presence, ratio_to_score

logger = get_logger()

PLACEHOLDER_NAMES = [u'Author', u'Designer', u'Checker', u'Approver',
                     u'author', u'designer', u'checker', u'approver',
                     u'Enter Name', u'enter name', u'Name', u'name']


def _finding(severity, category, message, action=u"", affected=0):
    return {
        'severity': severity,
        'category': category,
        'message': message,
        'action': action,
        'affected_count': affected,
    }


def _status_label(score):
    if score >= 5:
        return u'Guclu'
    elif score >= 4:
        return u'Iyi'
    elif score >= 3:
        return u'Orta'
    elif score >= 2:
        return u'Zayif'
    return u'Riskli'


# ---------------------------------------------------------------------------
# Ortak kurallar
# ---------------------------------------------------------------------------

def evaluate_common_rules(metrics):
    findings = []
    scores = {}
    notes = {}

    # --- Uyari Yonetimi ---
    wc = metrics.get('warning_count', 0)
    unl = metrics.get('unloaded_link_count', 0)
    no_tmpl = metrics.get('views_without_template', 0)
    cad_imp = metrics.get('cad_import_count', 0)

    # Temel warning skoru
    if wc <= 5:
        ws = 5
    elif wc <= 20:
        ws = 4
    elif wc <= 50:
        ws = 3
    elif wc <= 100:
        ws = 2
    else:
        ws = 1

    # Ek ceza: unloaded link
    penalty_items = []
    if unl > 0:
        ws = max(1, ws - 1)
        penalty_items.append(u'{0} yuklenmemis link (-1)'.format(unl))
        findings.append(_finding('CRITICAL', u'Uyari Yonetimi',
            u'{0} yuklenmemis Revit link'.format(unl),
            u'Link dosyalarini yukleyin veya gereksizleri kaldirin', unl))

    # Ek ceza: template'siz view
    if no_tmpl > 3:
        ws = max(1, ws - 1)
        penalty_items.append(u'{0} template\'siz view (-1)'.format(no_tmpl))
        findings.append(_finding('WARNING', u'Uyari Yonetimi',
            u'{0} view template\'siz'.format(no_tmpl),
            u'View template atayarak gorunus standardini saglayin', no_tmpl))

    if wc > 50:
        findings.append(_finding('CRITICAL' if wc > 100 else 'WARNING', u'Uyari Yonetimi',
            u'Warning sayisi yuksek: {0}'.format(wc),
            u'Oncelikle duplikat ve overlap uyarilarini cozun', wc))

    scores[u'Uyari Yonetimi'] = ws

    # Aciklama
    parts = [u'Warning: {0}'.format(wc)]
    if unl > 0:
        parts.append(u'Yuklenmemis link: {0}'.format(unl))
    if no_tmpl > 0:
        parts.append(u'Template\'siz view: {0}'.format(no_tmpl))
    if cad_imp > 0:
        parts.append(u'Import CAD: {0}'.format(cad_imp))
    if penalty_items:
        parts.append(u'Cezalar: ' + u', '.join(penalty_items))
    notes[u'Uyari Yonetimi'] = u' | '.join(parts)

    # Warning ceza ozeti (ust ozet icin)
    warning_penalty_note = u''
    if penalty_items:
        warning_penalty_note = u'Ek cezalar: ' + u', '.join(penalty_items)

    # --- Modelleme Disiplini ---
    inp = metrics.get('inplace_family_count', 0)
    cad = metrics.get('cad_import_count', 0)
    vtr = metrics.get('view_template_ratio', 0)
    penalty = 0
    mod_strengths = []
    mod_weaknesses = []

    if inp > 5:
        penalty += 3
        mod_weaknesses.append(u'{0} in-place family (cok fazla)'.format(inp))
        findings.append(_finding('WARNING', u'Modelleme Disiplini',
            u'{0} adet in-place family'.format(inp),
            u'In-place family sayisini azaltin, loadable family kullanin', inp))
    elif inp > 2:
        penalty += 2
        mod_weaknesses.append(u'{0} in-place family'.format(inp))
    elif inp > 0:
        penalty += 1

    if cad > 3:
        penalty += 3
        mod_weaknesses.append(u'{0} import CAD'.format(cad))
        findings.append(_finding('WARNING', u'Modelleme Disiplini',
            u'{0} adet import edilmis CAD'.format(cad),
            u'Import CAD dosyalarini kaldirin', cad))
    elif cad > 0:
        penalty += 1

    if vtr >= 0.9:
        mod_strengths.append(u'View template %{0} (iyi)'.format(int(vtr * 100)))
    elif vtr < 0.5:
        mod_weaknesses.append(u'View template %{0} (dusuk)'.format(int(vtr * 100)))

    ms = max(0, 5 - penalty)
    scores[u'Modelleme Disiplini'] = ms

    note_parts = []
    if mod_strengths:
        note_parts.append(u'Guclu: ' + u', '.join(mod_strengths))
    if mod_weaknesses:
        note_parts.append(u'Eksik: ' + u', '.join(mod_weaknesses))
    note_parts.append(u'In-place:{0} CAD:{1} Template:%{2}'.format(inp, cad, int(vtr * 100)))
    notes[u'Modelleme Disiplini'] = u' | '.join(note_parts)

    # --- Temel Kurgu ---
    levels = metrics.get('level_count', 0)
    grids = metrics.get('grid_count', 0)
    pinned = metrics.get('pinned_grids_ratio', 0)
    if levels > 0 and grids > 0:
        scores[u'Temel Kurgu'] = 5
    elif levels > 0 or grids > 0:
        scores[u'Temel Kurgu'] = 2
        findings.append(_finding('WARNING', u'Temel Kurgu',
            u'Level veya Grid eksik', u'Referans sistemini tamamlayin'))
    else:
        scores[u'Temel Kurgu'] = 0
        findings.append(_finding('CRITICAL', u'Temel Kurgu',
            u'Ne Level ne Grid tanimli', u'Koordinat referans sistemi olusturun'))

    notes[u'Temel Kurgu'] = u'Level:{0} Grid:{1} Pin:%{2}'.format(levels, grids, int(pinned * 100))

    # Naming
    bad_views = metrics.get('default_named_view_count', 0)
    if bad_views >= 10:
        findings.append(_finding('WARNING', u'Isimlendirme',
            u'{0} view varsayilan/kotu isimli'.format(bad_views),
            u'View isimlerini proje standardina gore duzenleyin', bad_views))
    unnamed_sheets = metrics.get('unnamed_sheet_count', 0)
    if unnamed_sheets > 0:
        findings.append(_finding('WARNING', u'Isimlendirme',
            u'{0} pafta isimsiz'.format(unnamed_sheets),
            u'Pafta isim ve numaralarini tamamlayin', unnamed_sheets))
    empty_sheets = metrics.get('empty_sheet_count', 0)
    if empty_sheets > 0:
        findings.append(_finding('WARNING', u'Pafta Kalitesi',
            u'{0} bos pafta'.format(empty_sheets),
            u'Bos paftalari kaldirin veya icerik ekleyin', empty_sheets))

    return findings, scores, notes, warning_penalty_note


# ---------------------------------------------------------------------------
# Statik / Kalip
# ---------------------------------------------------------------------------

def evaluate_structural_rules(metrics):
    findings = []
    scores = {}
    notes = {}

    # Tasiyici sistem
    col = metrics.get('structural_columns_count', 0)
    frm = metrics.get('structural_framing_count', 0)
    flr = metrics.get('floors_count', 0)
    wll = metrics.get('walls_count', 0)
    fnd = metrics.get('structural_foundation_count', 0)
    checks = [col > 0, frm > 0, flr > 0, wll > 0]
    present = sum(1 for c in checks if c)
    scores[u'Tasiyici Sistem'] = score_from_presence(present, len(checks))

    strengths = []
    weaknesses = []
    if col > 0:
        strengths.append(u'{0} kolon'.format(col))
    else:
        weaknesses.append(u'Kolon yok')
        findings.append(_finding('CRITICAL', u'Tasiyici Sistem',
            u'Strukurel kolon bulunamadi', u'Kolon elemanlari zorunludur'))
    if frm > 0:
        strengths.append(u'{0} kiris'.format(frm))
    else:
        weaknesses.append(u'Kiris yok')
        findings.append(_finding('CRITICAL', u'Tasiyici Sistem',
            u'Kiris/framing bulunamadi', u'Kiris elemanlari ekleyin'))
    if fnd > 0:
        strengths.append(u'{0} temel (bonus)'.format(fnd))

    note_parts = []
    if strengths:
        note_parts.append(u'Mevcut: ' + u', '.join(strengths))
    if weaknesses:
        note_parts.append(u'Eksik: ' + u', '.join(weaknesses))
    notes[u'Tasiyici Sistem'] = u' | '.join(note_parts)

    # Kalip proje kapsami
    svc = metrics.get('section_view_count', 0)
    dvc = metrics.get('detail_view_count', 0)
    shc = metrics.get('sheet_count', 0)
    sch = metrics.get('schedule_count', 0)
    shaft = metrics.get('shafts_count', 0) + metrics.get('stairs_count', 0)
    kalip_checks = [shaft > 0, svc >= 2, dvc >= 1, shc >= 3]
    present = sum(1 for c in kalip_checks if c)
    scores[u'Kalip Proje Kapsami'] = score_from_presence(present, len(kalip_checks))

    kn = []
    kn.append(u'Kesit:{0} Detay:{1} Pafta:{2} Schedule:{3}'.format(svc, dvc, shc, sch))
    if svc < 2:
        kn.append(u'Kesit yetersiz')
        findings.append(_finding('WARNING', u'Kalip Proje Kapsami',
            u'Kesit sayisi yetersiz: {0}'.format(svc), u'En az 2 kesit gerekli'))
    if shc < 3:
        findings.append(_finding('WARNING', u'Kalip Proje Kapsami',
            u'Pafta sayisi yetersiz: {0}'.format(shc), u'Pafta seti olusturun'))
    notes[u'Kalip Proje Kapsami'] = u' | '.join(kn)

    # Annotation
    dim = metrics.get('dimension_count', 0)
    txt = metrics.get('text_note_count', 0)
    col_tag = metrics.get('structural_column_tag_count', 0)
    frm_tag = metrics.get('structural_framing_tag_count', 0)
    ann_checks = [dim > 10, (col_tag + frm_tag) > 0]
    present = sum(1 for c in ann_checks if c)
    scores[u'Annotation ve Olcu'] = score_from_presence(present, len(ann_checks))

    an = []
    an.append(u'Olcu:{0} Metin:{1} Kolon tag:{2} Kiris tag:{3}'.format(dim, txt, col_tag, frm_tag))
    if col_tag > 0:
        an.append(u'Guclu: Kolon etiketleri mevcut ({0})'.format(col_tag))
    if frm_tag == 0:
        an.append(u'Eksik: Kiris etiketi yok — pafta okunabilirlik riski')
        findings.append(_finding('WARNING', u'Annotation ve Olcu',
            u'Kiris (framing) etiketi bulunamadi (structural_framing_tag_count=0)',
            u'Kiris etiketlerini ekleyin', 0))
    if dim < 10:
        findings.append(_finding('WARNING', u'Annotation ve Olcu',
            u'Olculendirme zayif: {0}'.format(dim), u'Olculendirme ekleyin'))
    notes[u'Annotation ve Olcu'] = u' | '.join(an)

    # Pafta kalitesi
    empty = metrics.get('empty_sheet_count', 0)
    unnamed = metrics.get('unnamed_sheet_count', 0)
    ss = 3
    if shc >= 5:
        ss = 4
    if shc >= 8:
        ss = 5
    if empty > 2:
        ss = max(1, ss - 2)
    scores[u'Pafta Kalitesi'] = ss

    pn = [u'Pafta:{0} Bos:{1} Isimsiz:{2}'.format(shc, empty, unnamed)]
    if empty == 0 and unnamed == 0:
        pn.append(u'Guclu: Bos veya isimsiz pafta yok')
    notes[u'Pafta Kalitesi'] = u' | '.join(pn)

    return findings, scores, notes


# ---------------------------------------------------------------------------
# Mimari
# ---------------------------------------------------------------------------

def evaluate_architectural_rules(metrics):
    findings = []
    scores = {}
    notes = {}

    checks = [
        metrics.get('rooms_count', 0) > 0, metrics.get('walls_count', 0) > 0,
        metrics.get('doors_count', 0) > 0, metrics.get('windows_count', 0) > 0,
        metrics.get('floors_count', 0) > 0,
        (metrics.get('stairs_count', 0) + metrics.get('ramps_count', 0)) > 0,
        (metrics.get('ceilings_count', 0) + metrics.get('roofs_count', 0)) > 0,
        metrics.get('shafts_count', 0) > 0,
    ]
    present = sum(1 for c in checks if c)
    scores[u'Model Kapsami'] = score_from_presence(present, len(checks))
    notes[u'Model Kapsami'] = u'{0}/8 eleman tipi mevcut | Room:{1} Duvar:{2} Kapi:{3}'.format(
        present, metrics.get('rooms_count', 0), metrics.get('walls_count', 0), metrics.get('doors_count', 0))

    if metrics.get('rooms_count', 0) == 0:
        findings.append(_finding('CRITICAL', u'Model Kapsami', u'Room bulunamadi', u'Room elemanlari yerlestirin'))

    view_checks = [
        metrics.get('section_view_count', 0) > 0, metrics.get('detail_view_count', 0) > 0,
        metrics.get('elevation_view_count', 0) > 0, metrics.get('sheet_count', 0) > 0,
    ]
    present = sum(1 for c in view_checks if c)
    scores[u'Gorunus ve Sunum'] = score_from_presence(present, len(view_checks))
    notes[u'Gorunus ve Sunum'] = u'Kesit:{0} Detay:{1} Cephe:{2} Pafta:{3}'.format(
        metrics.get('section_view_count', 0), metrics.get('detail_view_count', 0),
        metrics.get('elevation_view_count', 0), metrics.get('sheet_count', 0))

    ann_checks = [metrics.get('dimension_count', 0) > 20, metrics.get('room_tag_count', 0) > 0, metrics.get('door_tag_count', 0) > 0]
    present = sum(1 for c in ann_checks if c)
    scores[u'Annotation ve Olcu'] = score_from_presence(present, len(ann_checks))
    notes[u'Annotation ve Olcu'] = u'Olcu:{0} RoomTag:{1} DoorTag:{2}'.format(
        metrics.get('dimension_count', 0), metrics.get('room_tag_count', 0), metrics.get('door_tag_count', 0))

    if metrics.get('room_tag_count', 0) == 0 and metrics.get('rooms_count', 0) > 0:
        findings.append(_finding('WARNING', u'Annotation ve Olcu', u'Room tag eksik', u'Room tag ekleyin'))

    ss = 3
    if metrics.get('sheet_count', 0) >= 5:
        ss = 4
    if metrics.get('empty_sheet_count', 0) > 2:
        ss = max(1, ss - 2)
    scores[u'Pafta Kalitesi'] = ss
    notes[u'Pafta Kalitesi'] = u'Pafta:{0} Bos:{1}'.format(metrics.get('sheet_count', 0), metrics.get('empty_sheet_count', 0))

    return findings, scores, notes


# ---------------------------------------------------------------------------
# Mekanik
# ---------------------------------------------------------------------------

def evaluate_mechanical_rules(metrics):
    findings = []
    scores = {}
    notes = {}

    checks = [metrics.get('mechanical_equipment_count', 0) > 0, metrics.get('mep_curve_total', 0) > 0, metrics.get('spaces_count', 0) > 0]
    present = sum(1 for c in checks if c)
    scores[u'Sistem Kapsami'] = score_from_presence(present, len(checks))
    notes[u'Sistem Kapsami'] = u'Ekipman:{0} Curve:{1} Space:{2}'.format(
        metrics.get('mechanical_equipment_count', 0), metrics.get('mep_curve_total', 0), metrics.get('spaces_count', 0))
    if metrics.get('mechanical_equipment_count', 0) == 0:
        findings.append(_finding('CRITICAL', u'Sistem Kapsami', u'Mekanik ekipman yok', u'Ekipman yerlestirin'))
    if metrics.get('mep_curve_total', 0) == 0:
        findings.append(_finding('CRITICAL', u'Sistem Kapsami', u'Duct/Pipe yok', u'Tesisat sistemi olusturun'))

    fit = metrics.get('duct_fitting_count', 0) + metrics.get('pipe_fitting_count', 0)
    conn_checks = [fit > 0, metrics.get('plumbing_fixture_count', 0) > 0 or metrics.get('mechanical_equipment_count', 0) > 0, metrics.get('duct_terminal_count', 0) > 0]
    present = sum(1 for c in conn_checks if c)
    scores[u'Baglanti Kalitesi'] = score_from_presence(present, len(conn_checks))
    notes[u'Baglanti Kalitesi'] = u'Fitting:{0} Terminal:{1}'.format(fit, metrics.get('duct_terminal_count', 0))

    mep_tags = metrics.get('mep_tag_count', 0)
    if mep_tags == 0 and metrics.get('mep_curve_total', 0) > 0:
        findings.append(_finding('WARNING', u'Etiket ve Parametre', u'MEP etiketi yok', u'Etiketleri ekleyin'))
        scores[u'Etiket ve Parametre'] = 1
    else:
        scores[u'Etiket ve Parametre'] = 4 if mep_tags > 0 else 3
    notes[u'Etiket ve Parametre'] = u'MEP tag:{0}'.format(mep_tags)

    scores[u'Pafta Kalitesi'] = 4 if metrics.get('sheet_count', 0) >= 3 else 2
    notes[u'Pafta Kalitesi'] = u'Pafta:{0}'.format(metrics.get('sheet_count', 0))
    scores[u'Schedule Hazirlik'] = 4 if metrics.get('schedule_count', 0) >= 2 else 2
    notes[u'Schedule Hazirlik'] = u'Schedule:{0}'.format(metrics.get('schedule_count', 0))

    return findings, scores, notes


# ---------------------------------------------------------------------------
# Elektrik
# ---------------------------------------------------------------------------

def evaluate_electrical_rules(metrics):
    findings = []
    scores = {}
    notes = {}

    checks = [metrics.get('electrical_equipment_count', 0) > 0, metrics.get('electrical_device_total', 0) > 0, metrics.get('electrical_circuit_count', 0) > 0]
    present = sum(1 for c in checks if c)
    scores[u'Sistem Kapsami'] = score_from_presence(present, len(checks))
    notes[u'Sistem Kapsami'] = u'Ekipman:{0} Cihaz:{1} Devre:{2}'.format(
        metrics.get('electrical_equipment_count', 0), metrics.get('electrical_device_total', 0), metrics.get('electrical_circuit_count', 0))
    if metrics.get('electrical_equipment_count', 0) == 0:
        findings.append(_finding('CRITICAL', u'Sistem Kapsami', u'Elektrik ekipmani yok', u'Panel yerlestirin'))

    circuit = metrics.get('electrical_circuit_count', 0)
    devices = metrics.get('electrical_device_total', 0)
    if devices > 0 and circuit == 0:
        findings.append(_finding('CRITICAL', u'Devre Kalitesi', u'{0} cihaz devresiz'.format(devices), u'Devrelere atayin'))
        scores[u'Devre Kalitesi'] = 1
    elif circuit > 0:
        scores[u'Devre Kalitesi'] = 4
    else:
        scores[u'Devre Kalitesi'] = 2
    notes[u'Devre Kalitesi'] = u'Devre:{0} Cihaz:{1}'.format(circuit, devices)

    etags = metrics.get('electrical_tag_count', 0)
    if etags == 0 and devices > 0:
        findings.append(_finding('WARNING', u'Etiket ve Parametre', u'Elektrik etiketi yok', u'Etiketleri ekleyin'))
        scores[u'Etiket ve Parametre'] = 1
    else:
        scores[u'Etiket ve Parametre'] = 4 if etags > 0 else 3
    notes[u'Etiket ve Parametre'] = u'E.Tag:{0}'.format(etags)

    scores[u'Pafta Kalitesi'] = 4 if metrics.get('sheet_count', 0) >= 3 else 2
    notes[u'Pafta Kalitesi'] = u'Pafta:{0}'.format(metrics.get('sheet_count', 0))
    scores[u'Schedule Hazirlik'] = 4 if metrics.get('schedule_count', 0) >= 2 else 2
    notes[u'Schedule Hazirlik'] = u'Schedule:{0}'.format(metrics.get('schedule_count', 0))

    return findings, scores, notes


# ---------------------------------------------------------------------------
# Disipline gore kural secici
# ---------------------------------------------------------------------------

DISCIPLINE_RULE_MAP = {
    'STATIK': evaluate_structural_rules,
    'MIMARI': evaluate_architectural_rules,
    'MEKANIK': evaluate_mechanical_rules,
    'ELEKTRIK': evaluate_electrical_rules,
}


def evaluate_discipline_rules(discipline_code, metrics):
    func = DISCIPLINE_RULE_MAP.get(discipline_code)
    if func is None:
        return [], {}, {}
    return func(metrics)


# ---------------------------------------------------------------------------
# Pafta personel durumu degerlendirme
# ---------------------------------------------------------------------------

def evaluate_personnel_status(sheet_personnel):
    """Her pafta icin personel alanlarinin durumunu degerlendirir.
    Returns: list of dict with 'durum' and 'aciklama' eklenmis."""
    result = []
    for p in sheet_personnel:
        issues = []
        fields = [
            ('drawn_by', u'Drawn By'),
            ('designed_by', u'Designed By'),
            ('checked_by', u'Checked By'),
            ('approved_by', u'Approved By'),
        ]
        for key, label in fields:
            val = p.get(key, u'').strip()
            if not val:
                issues.append(u'{0} bos'.format(label))
            elif val in PLACEHOLDER_NAMES:
                issues.append(u'{0} standart disi ("{1}")'.format(label, val))

        if not p.get('sheet_issue_date', u'').strip():
            issues.append(u'Issue Date bos')

        entry = dict(p)
        if not issues:
            entry['durum'] = u'Tam'
            entry['aciklama'] = u'Tum alanlar dolu'
        elif any(u'standart disi' in i for i in issues):
            entry['durum'] = u'Standart Disi'
            entry['aciklama'] = u'; '.join(issues)
        else:
            entry['durum'] = u'Eksik'
            entry['aciklama'] = u'; '.join(issues)
        result.append(entry)
    return result
