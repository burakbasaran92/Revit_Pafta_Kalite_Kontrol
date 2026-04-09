# -*- coding: utf-8 -*-
"""Rapor uretimi v6.1 — profesyonel CSV/JSON.

CSV bolum sirasi:
A) Ust Ozet (warning ceza etkisi dahil)
B) Kategori Bazli Ana Degerlendirme (aciklama dolu)
C) Kirmizi Bayraklar (tablo formatinda)
D) Pafta Personel Bilgileri (durum sutunlu)
E) Gruplanmis Ham Metrikler (disipline gore filtrelenmis)
F) Oncelikli Duzeltme Listesi
"""
from __future__ import print_function

import io
import json
import os

from qc_utils import ensure_folder, expand_path, get_logger, slugify, utext

logger = get_logger()

# Statik/Kalip icin gereksiz MEP/Elektrik metrikleri
_MEP_ELEC_KEYS = set([
    'duct_count', 'flex_duct_count', 'duct_fitting_count', 'duct_accessory_count',
    'duct_terminal_count', 'pipe_count', 'flex_pipe_count', 'pipe_fitting_count',
    'pipe_accessory_count', 'plumbing_fixture_count', 'spaces_count',
    'mechanical_equipment_count', 'mep_curve_total', 'mep_tag_count',
    'electrical_equipment_count', 'electrical_fixture_count', 'lighting_fixture_count',
    'conduit_count', 'conduit_fitting_count', 'cable_tray_count',
    'fire_alarm_device_count', 'data_device_count', 'communication_device_count',
    'electrical_circuit_count', 'electrical_device_total', 'electrical_route_total',
    'electrical_tag_count',
])

# Metrik gruplama
_METRIC_GROUPS = {
    u'Model Genel': ['file_size_mb', 'revit_version', 'is_workshared', 'inplace_family_count'],
    u'Pafta ve Gorunus': ['sheet_count', 'empty_sheet_count', 'unnamed_sheet_count',
                          'view_count', 'default_named_view_count', 'plan_view_count',
                          'section_view_count', 'detail_view_count', 'elevation_view_count',
                          'view_template_ratio', 'views_without_template', 'schedule_count'],
    u'Annotation ve Tag': ['dimension_count', 'text_note_count', 'room_tag_count',
                           'door_tag_count', 'window_tag_count',
                           'structural_column_tag_count', 'structural_framing_tag_count',
                           'mep_tag_count', 'electrical_tag_count'],
    u'Referans Sistemi': ['level_count', 'grid_count', 'pinned_grids_ratio'],
    u'Tasiyici Sistem': ['structural_columns_count', 'structural_framing_count',
                         'structural_foundation_count', 'rebar_count', 'structural_connections_count',
                         'walls_count', 'floors_count'],
    u'Mimari Elemanlar': ['rooms_count', 'doors_count', 'windows_count', 'ceilings_count',
                          'roofs_count', 'stairs_count', 'ramps_count', 'shafts_count'],
    u'Uyarilar ve Riskler': ['warning_count', 'unloaded_link_count', 'link_count',
                              'cad_import_count', 'cad_link_count', 'has_starting_view',
                              'project_info_filled'],
}


def _w(fp, row, delimiter=u';'):
    cells = []
    for cell in row:
        text = utext(cell)
        if delimiter in text or u'"' in text or u'\n' in text:
            text = u'"' + text.replace(u'"', u'""') + u'"'
        cells.append(text)
    fp.write(delimiter.join(cells) + u'\r\n')


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


def export_csv_report(result, csv_path):
    ensure_folder(os.path.dirname(csv_path))
    gsd = result.get('general_score_data', {})
    disc_code = result.get('discipline_code', u'')

    with io.open(csv_path, 'w', encoding='utf-8-sig') as f:
        # ====== A) UST OZET ======
        _w(f, [u'=== UST OZET ==='])
        _w(f, [u'Proje', utext(result.get('project_name'))])
        _w(f, [u'Dosya', utext(result.get('document_title'))])
        _w(f, [u'Disiplin', utext(result.get('discipline_name'))])
        _w(f, [u'Rapor ID', utext(result.get('report_id'))])
        _w(f, [u'Tarih', utext(result.get('run_time'))])
        _w(f, [])
        _w(f, [u'Genel Skor', utext(result.get('total_score'))])
        _w(f, [u'BIM Formu Skoru', utext(gsd.get('bim_form_score', u''))])
        _w(f, [u'Diger QC Skoru', utext(gsd.get('other_qc_score', u''))])
        _w(f, [u'Warning Ceza Etkisi', utext(result.get('warning_penalty_note', u'Yok'))])
        _w(f, [u'BIM Agirlik', u'%{0}'.format(int(gsd.get('bim_weight', 0.5) * 100))])
        _w(f, [u'QC Agirlik', u'%{0}'.format(int(gsd.get('qc_weight', 0.5) * 100))])
        _w(f, [u'Kalite Sinifi', utext(result.get('quality_class'))])
        _w(f, [u'Teslim Karari', utext(result.get('delivery_decision'))])
        _w(f, [u'NOT', u'Title block verileri skora dahil degildir'])
        _w(f, [])

        # Imza
        sig = result.get('signature', {})
        _w(f, [u'Kontrol Eden', utext(sig.get('full_name')), utext(sig.get('title'))])
        _w(f, [])

        # ====== B) KATEGORİ BAZLI ANA DEĞERLENDİRME ======
        _w(f, [u'=== KATEGORI BAZLI DEGERLENDIRME ==='])
        _w(f, [u'Kategori', u'Agirlik', u'Puan (0-5)', u'Katki', u'Durum',
               u'Dikkate Alinan Metrikler', u'Onerilen Aksiyon'])
        for row in result.get('rows', []):
            note = row.get('note', u'')
            sc = row.get('score5', 0)
            _w(f, [
                utext(row.get('category')),
                utext(row.get('weight')),
                utext(sc),
                utext(row.get('weighted_score')),
                _status_label(sc),
                note,
                u'',
            ])
        _w(f, [])

        # ====== C) KIRMIZI BAYRAKLAR (tablo) ======
        _w(f, [u'=== KIRMIZI BAYRAKLAR ==='])
        _w(f, [u'Seviye', u'Sorun', u'Adet', u'Etki', u'Onerilen Aksiyon'])
        findings = result.get('findings', [])
        for fin in findings:
            sev = fin.get('severity', u'')
            if sev in ('CRITICAL', 'WARNING'):
                _w(f, [
                    sev,
                    utext(fin.get('message', u'')),
                    utext(fin.get('affected_count', u'')),
                    utext(fin.get('category', u'')),
                    utext(fin.get('action', u'')),
                ])
        if not any(f.get('severity') in ('CRITICAL', 'WARNING') for f in findings):
            _w(f, [u'', u'Kritik veya uyari bulgusu yok', u'', u'', u''])
        _w(f, [])

        # ====== D) PAFTA PERSONEL BİLGİLERİ ======
        _w(f, [u'=== PAFTA PERSONEL BILGILERI (skor disi) ==='])
        _w(f, [u'Sheet No', u'Sheet Name', u'Drawn By', u'Designed By',
               u'Checked By', u'Approved By', u'Issue Date', u'Durum', u'Aciklama'])
        for p in result.get('sheet_personnel_metadata', []):
            _w(f, [
                utext(p.get('sheet_number')),
                utext(p.get('sheet_name')),
                utext(p.get('drawn_by')),
                utext(p.get('designed_by')),
                utext(p.get('checked_by')),
                utext(p.get('approved_by')),
                utext(p.get('sheet_issue_date')),
                utext(p.get('durum', u'')),
                utext(p.get('aciklama', u'')),
            ])
        _w(f, [])

        # ====== E) GRUPLANMIŞ HAM METRİKLER ======
        _w(f, [u'=== HAM METRIKLER (gruplu) ==='])
        metrics = result.get('metrics', {})
        shown_keys = set()

        for group_name, keys in sorted(_METRIC_GROUPS.items()):
            # Statik/Kalip disiplininde MEP/Elektrik grubunu atla
            has_data = False
            group_rows = []
            for key in keys:
                if key in metrics:
                    val = metrics[key]
                    # Sifir MEP metrikleri Statik raporunda atla
                    if disc_code == 'STATIK' and key in _MEP_ELEC_KEYS and val == 0:
                        continue
                    group_rows.append((key, val))
                    shown_keys.add(key)
                    has_data = True

            if has_data:
                _w(f, [u'--- {0} ---'.format(group_name)])
                for key, val in group_rows:
                    _w(f, [utext(key), utext(val)])

        # Kalan (gruplanmamis) metrikler
        remaining = []
        for key in sorted(metrics.keys()):
            if key not in shown_keys:
                val = metrics[key]
                if disc_code == 'STATIK' and key in _MEP_ELEC_KEYS and val == 0:
                    continue
                remaining.append((key, val))
        if remaining:
            _w(f, [u'--- Diger ---'])
            for key, val in remaining:
                _w(f, [utext(key), utext(val)])
        _w(f, [])

        # ====== F) ÖNCELİKLİ DÜZELTME LİSTESİ ======
        _w(f, [u'=== ONCELIKLI DUZELTME LISTESI ==='])
        _w(f, [u'Oncelik', u'Kategori', u'Sorun', u'Aksiyon'])
        for act in result.get('action_list', [])[:10]:
            _w(f, [
                utext(act.get('priority')),
                utext(act.get('category')),
                utext(act.get('issue')),
                utext(act.get('action')),
            ])

    return csv_path


def _json_default(obj):
    return utext(obj)


def export_json_report(result, json_path):
    ensure_folder(os.path.dirname(json_path))
    with io.open(json_path, 'w', encoding='utf-8') as fp:
        fp.write(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))
    return json_path


def write_central_log(result, standard):
    cfg = (standard or {}).get('central_logging', {})
    if not cfg.get('enabled'):
        return False, u"Merkezi loglama kapali", None
    if utext(cfg.get('mode')).lower() != 'file':
        return False, u"Sadece dosya tabanli destekleniyor", None
    root = expand_path(cfg.get('path'))
    if not root:
        return False, u"Log yolu tanimli degil", None
    try:
        company = slugify(((result.get('standard_summary') or {}).get('company')) or 'company')
        project = slugify(result.get('project_name') or result.get('document_title') or 'project')
        folder = os.path.join(root, company, project)
        ensure_folder(folder)
        filename = u"{0}_{1}_{2}.json".format(
            slugify(result.get('report_id') or 'report'),
            slugify(result.get('discipline_name') or 'disiplin'),
            slugify(((result.get('signature') or {}).get('username')) or 'user'),
        )
        path = os.path.join(folder, filename)
        export_json_report(result, path)
        return True, u"Merkezi log yazildi", path
    except Exception as exc:
        return False, u"Log yazilamadi: {0}".format(exc), None
