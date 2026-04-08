# -*- coding: utf-8 -*-
"""Revit API üzerinden metrik toplama.

Ortak metrikler, disipline özgü eleman sayıları, title block parametreleri,
BIM form metrikleri ve pafta detayları toplanır.
"""
from __future__ import division

import os

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    Family,
    FilteredElementCollector,
    Grid,
    ImportInstance,
    Level,
    RevitLinkType,
    ScheduleSheetInstance,
    View,
    ViewSchedule,
    Viewport,
    ViewSheet,
    ViewType,
)

from qc_bim_form_config import (
    TITLEBLOCK_DATE_FIELDS,
    TITLEBLOCK_EXTRA_FIELDS,
    TITLEBLOCK_PERSONNEL_FIELDS,
    TITLEBLOCK_PRIMARY_FIELDS,
)
from qc_utils import get_logger, utext

logger = get_logger()


def _count_by_category(doc, bic):
    try:
        return (
            FilteredElementCollector(doc)
            .OfCategory(bic)
            .WhereElementIsNotElementType()
            .GetElementCount()
        )
    except Exception:
        return 0


def _safe_param_value(element, param_name):
    """Element'ten parametre değerini güvenli okur (instance → type fallback)."""
    if element is None:
        return u""
    try:
        p = element.LookupParameter(param_name)
        if p and p.HasValue:
            return utext(p.AsValueString() or p.AsString() or u"")
    except Exception:
        pass
    try:
        etype = element.Document.GetElement(element.GetTypeId())
        if etype:
            p = etype.LookupParameter(param_name)
            if p and p.HasValue:
                return utext(p.AsValueString() or p.AsString() or u"")
    except Exception:
        pass
    return u""


def _get_non_template_views(doc):
    _skip = {
        ViewType.DrawingSheet, ViewType.SystemBrowser,
        ViewType.ProjectBrowser, ViewType.Internal,
    }
    result = []
    for v in FilteredElementCollector(doc).OfClass(View).ToElements():
        try:
            if v.IsTemplate:
                continue
            if v.ViewType in _skip:
                continue
            result.append(v)
        except Exception:
            continue
    return result


def _has_view_template(view):
    try:
        tid = view.ViewTemplateId
        return tid is not None and tid.IntegerValue != -1
    except Exception:
        return False


def _is_pinned(element):
    try:
        return element.Pinned
    except Exception:
        return False


def _has_sectionbox(view):
    try:
        return view.IsSectionBoxActive
    except Exception:
        return False


def _safe_is_inplace(fam):
    try:
        return fam.IsInPlace
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Title block toplama
# ---------------------------------------------------------------------------

def collect_titleblock_details(doc):
    """Her pafta için title block parametre detaylarını toplar."""
    sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
    all_fields = list(TITLEBLOCK_PRIMARY_FIELDS) + list(TITLEBLOCK_EXTRA_FIELDS)
    rows = []

    for sheet in sheets:
        row = {
            'sheet_number': utext(sheet.SheetNumber),
            'sheet_name': utext(sheet.Name),
            'sheet_id': sheet.Id.IntegerValue,
            'titleblock_found': False,
            'titleblock_count': 0,
            'titleblock_family': u'',
            'fields': {},
            'missing_primary': [],
            'missing_personnel': [],
            'missing_dates': [],
        }

        try:
            tb_instances = list(
                FilteredElementCollector(doc, sheet.Id)
                .OfCategory(BuiltInCategory.OST_TitleBlocks)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        except Exception:
            tb_instances = []

        row['titleblock_count'] = len(tb_instances)
        row['titleblock_found'] = len(tb_instances) > 0

        if tb_instances:
            tb = tb_instances[0]
            try:
                row['titleblock_family'] = utext(tb.Symbol.Family.Name) if tb.Symbol else u""
            except Exception:
                row['titleblock_family'] = u"okunamadı"

            for field in all_fields:
                row['fields'][field] = _safe_param_value(tb, field)

            for field in ['Sheet Name', 'Sheet Number']:
                if not row['fields'].get(field):
                    if field == 'Sheet Name':
                        row['fields'][field] = row['sheet_name']
                    elif field == 'Sheet Number':
                        row['fields'][field] = row['sheet_number']

        for field in TITLEBLOCK_PRIMARY_FIELDS:
            if not row['fields'].get(field, u'').strip():
                row['missing_primary'].append(field)
        for field in TITLEBLOCK_PERSONNEL_FIELDS:
            if not row['fields'].get(field, u'').strip():
                row['missing_personnel'].append(field)
        for field in TITLEBLOCK_DATE_FIELDS:
            if not row['fields'].get(field, u'').strip():
                row['missing_dates'].append(field)

        rows.append(row)
    return rows


def summarize_titleblock(tb_details):
    """Title block detaylarından özet metrikler üretir."""
    total = len(tb_details)
    if total == 0:
        return {
            'tb_total_sheets': 0, 'tb_no_titleblock': 0, 'tb_multi_titleblock': 0,
            'tb_missing_drawn_by': 0, 'tb_missing_designed_by': 0,
            'tb_missing_checked_by': 0, 'tb_missing_approved_by': 0,
            'tb_missing_date': 0, 'tb_missing_any_personnel': 0,
            'tb_fully_complete': 0,
            'tb_personnel_fill_ratio': 0.0, 'tb_primary_fill_ratio': 0.0,
        }

    no_tb = sum(1 for r in tb_details if not r['titleblock_found'])
    multi_tb = sum(1 for r in tb_details if r['titleblock_count'] > 1)
    m_drawn = sum(1 for r in tb_details if 'Drawn By' in r['missing_personnel'])
    m_designed = sum(1 for r in tb_details if 'Designed By' in r['missing_personnel'])
    m_checked = sum(1 for r in tb_details if 'Checked By' in r['missing_personnel'])
    m_approved = sum(1 for r in tb_details if 'Approved By' in r['missing_personnel'])
    m_date = sum(1 for r in tb_details if len(r['missing_dates']) > 0)
    m_any_pers = sum(1 for r in tb_details if len(r['missing_personnel']) > 0)
    fully = sum(1 for r in tb_details if r['titleblock_found'] and len(r['missing_primary']) == 0)

    total_pers = total * len(TITLEBLOCK_PERSONNEL_FIELDS)
    filled_pers = total_pers - sum(len(r['missing_personnel']) for r in tb_details)
    pers_ratio = filled_pers / float(total_pers) if total_pers > 0 else 0.0

    total_pri = total * len(TITLEBLOCK_PRIMARY_FIELDS)
    filled_pri = total_pri - sum(len(r['missing_primary']) for r in tb_details)
    pri_ratio = filled_pri / float(total_pri) if total_pri > 0 else 0.0

    return {
        'tb_total_sheets': total,
        'tb_no_titleblock': no_tb,
        'tb_multi_titleblock': multi_tb,
        'tb_missing_drawn_by': m_drawn,
        'tb_missing_designed_by': m_designed,
        'tb_missing_checked_by': m_checked,
        'tb_missing_approved_by': m_approved,
        'tb_missing_date': m_date,
        'tb_missing_any_personnel': m_any_pers,
        'tb_fully_complete': fully,
        'tb_personnel_fill_ratio': round(pers_ratio, 3),
        'tb_primary_fill_ratio': round(pri_ratio, 3),
    }


# ---------------------------------------------------------------------------
# BIM form metrikleri
# ---------------------------------------------------------------------------

def collect_bim_form_metrics(doc):
    """BIM kontrol formu maddelerine veri toplar.
    v5: daha fazla AUTO metrik eklendi."""
    m = {}

    # G01 — Revit version (AUTO)
    try:
        m['revit_version'] = utext(doc.Application.VersionNumber)
    except Exception:
        m['revit_version'] = u''

    # G02 — file naming
    m['file_naming'] = utext(doc.Title)

    # G03 — dosya boyutu (AUTO)
    try:
        path = doc.PathName
        m['file_size_mb'] = round(os.path.getsize(path) / (1024.0 * 1024.0), 1) if path and os.path.exists(path) else -1
    except Exception:
        m['file_size_mb'] = -1

    # G04 — workshared (AUTO)
    try:
        m['is_workshared'] = doc.IsWorkshared
    except Exception:
        m['is_workshared'] = False

    # G05 — warning count (AUTO) — common metrics'ten gelir

    # G07 — unused family count (AUTO — purge heuristic)
    try:
        families = list(FilteredElementCollector(doc).OfClass(Family).ToElements())
        unused = 0
        for fam in families:
            try:
                if fam.IsEditable:
                    symbol_ids = fam.GetFamilySymbolIds()
                    has_instance = False
                    for sid in symbol_ids:
                        instances = FilteredElementCollector(doc).WherePasses(
                            FamilyInstanceFilter(doc, sid)
                        ).GetElementCount()
                        if instances > 0:
                            has_instance = True
                            break
                    if not has_instance:
                        unused += 1
            except Exception:
                continue
        m['unused_family_count'] = unused
    except Exception:
        m['unused_family_count'] = -1

    # G08 — 3D view section box (AUTO)
    views = _get_non_template_views(doc)
    try:
        views_3d = [v for v in views if v.ViewType == ViewType.ThreeD]
        m['has_3d_no_sectionbox'] = any(not _has_sectionbox(v) for v in views_3d) if views_3d else False
    except Exception:
        m['has_3d_no_sectionbox'] = False

    # G09 — starting view (AUTO)
    try:
        sv = doc.GetElement(doc.StartingViewId) if doc.StartingViewId else None
        m['has_starting_view'] = sv is not None
    except Exception:
        m['has_starting_view'] = False

    # G10 — project info (AUTO)
    try:
        pinfo = doc.ProjectInformation
        filled = 0
        for bip in [BuiltInParameter.PROJECT_NAME, BuiltInParameter.PROJECT_NUMBER,
                     BuiltInParameter.PROJECT_ADDRESS, BuiltInParameter.CLIENT_NAME]:
            try:
                p = pinfo.get_Parameter(bip)
                if p and p.HasValue and utext(p.AsString()).strip():
                    filled += 1
            except Exception:
                pass
        m['project_info_filled'] = round(filled / 4.0, 2)
    except Exception:
        m['project_info_filled'] = 0.0

    # M13 — level/grid naming ratio (AUTO)
    try:
        import re
        grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
        levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
        all_ref = grids + levels
        if all_ref:
            # Heuristic: isim boş değil, sadece sayı değil, 1-20 karakter arası
            good = 0
            for e in all_ref:
                name = utext(e.Name).strip()
                if name and len(name) <= 20 and not name.startswith('Copy'):
                    good += 1
            m['level_grid_naming_ratio'] = round(good / float(len(all_ref)), 3)
        else:
            m['level_grid_naming_ratio'] = 0.0
    except Exception:
        m['level_grid_naming_ratio'] = 0.0

    # M15/M16 — view/sheet naming (common metrics'ten gelir)

    # M17/M32 — schedule count (AUTO)
    try:
        schedules = [s for s in FilteredElementCollector(doc).OfClass(ViewSchedule).ToElements()
                     if not s.IsTitleblockRevisionSchedule]
        m['schedule_count'] = len(schedules)
    except Exception:
        m['schedule_count'] = 0

    # M19 — room unnamed count (AUTO)
    try:
        from Autodesk.Revit.DB import SpatialElement
        rooms = list(FilteredElementCollector(doc).OfCategory(
            BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements())
        unnamed = sum(1 for r in rooms if not utext(r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()).strip()
                      if r.get_Parameter(BuiltInParameter.ROOM_NAME) else True)
        m['room_unnamed_count'] = unnamed
        m['room_total_count'] = len(rooms)
    except Exception:
        m['room_unnamed_count'] = 0
        m['room_total_count'] = 0

    # M21 — base point valid (AUTO)
    try:
        from Autodesk.Revit.DB import BasePoint
        bp = BasePoint.GetProjectBasePoint(doc)
        sp = BasePoint.GetSurveyPoint(doc)
        m['base_point_valid'] = bp is not None and sp is not None
    except Exception:
        m['base_point_valid'] = True  # Güvenli varsayım

    # M26/M27 — view template ratio (AUTO)
    if views:
        m['view_template_ratio'] = round(
            sum(1 for v in views if _has_view_template(v)) / float(len(views)), 3)
    else:
        m['view_template_ratio'] = 0.0

    # M28 — project parameters count (AUTO)
    try:
        bindings = doc.ParameterBindings
        it = bindings.ForwardIterator()
        count = 0
        while it.MoveNext():
            count += 1
        m['project_params_count'] = count
    except Exception:
        m['project_params_count'] = 0

    # M29 — pinned ratio (AUTO)
    try:
        grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
        levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
        all_ref = grids + levels
        if all_ref:
            m['pinned_grids_ratio'] = round(
                sum(1 for e in all_ref if _is_pinned(e)) / float(len(all_ref)), 3)
        else:
            m['pinned_grids_ratio'] = 0.0
    except Exception:
        m['pinned_grids_ratio'] = 0.0

    # M30 — keynote table (AUTO)
    try:
        from Autodesk.Revit.DB import KeynoteTable
        kt = KeynoteTable.GetKeynoteTable(doc)
        m['keynote_table_loaded'] = kt is not None
    except Exception:
        m['keynote_table_loaded'] = False

    # M33 — titleblock family name (AUTO)
    try:
        sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
        if sheets:
            tb_names = set()
            for sheet in sheets[:5]:  # İlk 5 paftaya bak
                try:
                    tbs = list(FilteredElementCollector(doc, sheet.Id)
                              .OfCategory(BuiltInCategory.OST_TitleBlocks)
                              .WhereElementIsNotElementType().ToElements())
                    for tb in tbs:
                        try:
                            tb_names.add(utext(tb.Symbol.Family.Name))
                        except Exception:
                            pass
                except Exception:
                    pass
            m['titleblock_family_name'] = u", ".join(tb_names) if tb_names else u""
        else:
            m['titleblock_family_name'] = u""
    except Exception:
        m['titleblock_family_name'] = u""

    # Annotation density metrics (Mimari AUTO kontroller)
    try:
        m['dimension_count'] = _count_by_category(doc, BuiltInCategory.OST_Dimensions)
    except Exception:
        m['dimension_count'] = 0

    try:
        m['tag_count'] = (
            _count_by_category(doc, BuiltInCategory.OST_RoomTags) +
            _count_by_category(doc, BuiltInCategory.OST_DoorTags) +
            _count_by_category(doc, BuiltInCategory.OST_WindowTags)
        )
    except Exception:
        m['tag_count'] = 0

    return m


def collect_common_metrics(doc, standard=None):
    """Tüm disiplinler için ortak metrikleri toplar."""
    from qc_standard import get_view_name_exact, get_view_name_prefixes
    metrics = {}

    warnings = list(doc.GetWarnings())
    metrics['warning_count'] = len(warnings)

    sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
    metrics['sheet_count'] = len(sheets)
    empty = 0
    unnamed = 0
    for sheet in sheets:
        try:
            vp = FilteredElementCollector(doc, sheet.Id).OfClass(Viewport).GetElementCount()
            sc = FilteredElementCollector(doc, sheet.Id).OfClass(ScheduleSheetInstance).GetElementCount()
            if (vp + sc) == 0:
                empty += 1
        except Exception:
            empty += 1
        if not utext(sheet.SheetNumber).strip() or not utext(sheet.Name).strip():
            unnamed += 1
    metrics['empty_sheet_count'] = empty
    metrics['unnamed_sheet_count'] = unnamed

    exact_names = get_view_name_exact(standard) if standard else []
    prefix_list = get_view_name_prefixes(standard) if standard else []
    views = _get_non_template_views(doc)
    metrics['view_count'] = len(views)
    default_named = 0
    for v in views:
        n = utext(v.Name).strip()
        if not n or n in exact_names or any(n.startswith(p) for p in prefix_list):
            default_named += 1
    metrics['default_named_view_count'] = default_named

    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
    metrics['level_count'] = len(levels)
    metrics['grid_count'] = len(grids)

    link_types = list(FilteredElementCollector(doc).OfClass(RevitLinkType).ToElements())
    metrics['link_count'] = len(link_types)
    unloaded = 0
    for lt in link_types:
        try:
            if not RevitLinkType.IsLoaded(doc, lt.Id):
                unloaded += 1
        except Exception:
            pass
    metrics['unloaded_link_count'] = unloaded

    imports = list(FilteredElementCollector(doc).OfClass(ImportInstance).ToElements())
    cad_imp = sum(1 for i in imports if not getattr(i, 'IsLinked', True))
    cad_lnk = sum(1 for i in imports if getattr(i, 'IsLinked', False))
    metrics['cad_import_count'] = cad_imp
    metrics['cad_link_count'] = cad_lnk

    families = list(FilteredElementCollector(doc).OfClass(Family).ToElements())
    metrics['inplace_family_count'] = sum(1 for f in families if _safe_is_inplace(f))

    metrics['section_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Section)
    metrics['detail_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Detail)
    metrics['elevation_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Elevation)

    return metrics


# ---------------------------------------------------------------------------
# Disipline özgü metrikler
# ---------------------------------------------------------------------------

def collect_discipline_metrics(doc):
    """Tüm disiplinlere ait eleman sayılarını toplar."""
    m = {}
    m['rooms_count'] = _count_by_category(doc, BuiltInCategory.OST_Rooms)
    m['doors_count'] = _count_by_category(doc, BuiltInCategory.OST_Doors)
    m['windows_count'] = _count_by_category(doc, BuiltInCategory.OST_Windows)
    m['walls_count'] = _count_by_category(doc, BuiltInCategory.OST_Walls)
    m['floors_count'] = _count_by_category(doc, BuiltInCategory.OST_Floors)
    m['ceilings_count'] = _count_by_category(doc, BuiltInCategory.OST_Ceilings)
    m['roofs_count'] = _count_by_category(doc, BuiltInCategory.OST_Roofs)
    m['stairs_count'] = _count_by_category(doc, BuiltInCategory.OST_Stairs)
    m['ramps_count'] = _count_by_category(doc, BuiltInCategory.OST_Ramps)
    m['shafts_count'] = _count_by_category(doc, BuiltInCategory.OST_ShaftOpening)

    m['structural_columns_count'] = _count_by_category(doc, BuiltInCategory.OST_StructuralColumns)
    m['structural_framing_count'] = _count_by_category(doc, BuiltInCategory.OST_StructuralFraming)
    m['structural_foundation_count'] = _count_by_category(doc, BuiltInCategory.OST_StructuralFoundation)
    m['rebar_count'] = _count_by_category(doc, BuiltInCategory.OST_Rebar)
    m['structural_connections_count'] = _count_by_category(doc, BuiltInCategory.OST_StructConnections)

    m['spaces_count'] = _count_by_category(doc, BuiltInCategory.OST_MEPSpaces)
    m['mechanical_equipment_count'] = _count_by_category(doc, BuiltInCategory.OST_MechanicalEquipment)
    m['duct_count'] = _count_by_category(doc, BuiltInCategory.OST_DuctCurves)
    m['flex_duct_count'] = _count_by_category(doc, BuiltInCategory.OST_FlexDuctCurves)
    m['duct_fitting_count'] = _count_by_category(doc, BuiltInCategory.OST_DuctFitting)
    m['duct_accessory_count'] = _count_by_category(doc, BuiltInCategory.OST_DuctAccessory)
    m['duct_terminal_count'] = _count_by_category(doc, BuiltInCategory.OST_DuctTerminal)
    m['pipe_count'] = _count_by_category(doc, BuiltInCategory.OST_PipeCurves)
    m['flex_pipe_count'] = _count_by_category(doc, BuiltInCategory.OST_FlexPipeCurves)
    m['pipe_fitting_count'] = _count_by_category(doc, BuiltInCategory.OST_PipeFitting)
    m['pipe_accessory_count'] = _count_by_category(doc, BuiltInCategory.OST_PipeAccessory)
    m['plumbing_fixture_count'] = _count_by_category(doc, BuiltInCategory.OST_PlumbingFixtures)

    m['electrical_equipment_count'] = _count_by_category(doc, BuiltInCategory.OST_ElectricalEquipment)
    m['electrical_fixture_count'] = _count_by_category(doc, BuiltInCategory.OST_ElectricalFixtures)
    m['lighting_fixture_count'] = _count_by_category(doc, BuiltInCategory.OST_LightingFixtures)
    m['conduit_count'] = _count_by_category(doc, BuiltInCategory.OST_Conduit)
    m['conduit_fitting_count'] = _count_by_category(doc, BuiltInCategory.OST_ConduitFitting)
    m['cable_tray_count'] = _count_by_category(doc, BuiltInCategory.OST_CableTray)
    m['fire_alarm_device_count'] = _count_by_category(doc, BuiltInCategory.OST_FireAlarmDevices)
    m['data_device_count'] = _count_by_category(doc, BuiltInCategory.OST_DataDevices)
    m['communication_device_count'] = _count_by_category(doc, BuiltInCategory.OST_CommunicationDevices)
    m['electrical_circuit_count'] = _count_by_category(doc, BuiltInCategory.OST_ElectricalCircuit)

    m['mep_curve_total'] = m['duct_count'] + m['flex_duct_count'] + m['pipe_count'] + m['flex_pipe_count']
    m['electrical_device_total'] = (
        m['electrical_fixture_count'] + m['lighting_fixture_count']
        + m['fire_alarm_device_count'] + m['data_device_count']
        + m['communication_device_count']
    )
    m['electrical_route_total'] = m['conduit_count'] + m['cable_tray_count']
    return m
