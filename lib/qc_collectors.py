# -*- coding: utf-8 -*-
"""Revit API veri toplama — sadece veri, yorum yok.

IronPython uyumlu. Tum parametre okumalari safe_param uzerinden.
Hicbir durumda exception firlatmaz, eksik veri icin fallback doner.
"""
from __future__ import division, print_function

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

from qc_utils import get_logger, safe_element_name, safe_param, utext

logger = get_logger()


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

def _count_cat(doc, bic):
    try:
        return (
            FilteredElementCollector(doc)
            .OfCategory(bic)
            .WhereElementIsNotElementType()
            .GetElementCount()
        )
    except Exception:
        return 0


def _get_views(doc):
    """Sablon olmayan, navigasyon disi tum view'lari dondurur."""
    skip = set([
        ViewType.DrawingSheet, ViewType.SystemBrowser,
        ViewType.ProjectBrowser, ViewType.Internal,
    ])
    result = []
    try:
        all_views = FilteredElementCollector(doc).OfClass(View).ToElements()
        for v in all_views:
            try:
                if v.IsTemplate:
                    continue
                if v.ViewType in skip:
                    continue
                result.append(v)
            except Exception:
                continue
    except Exception:
        pass
    return result


def _has_template(view):
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


# ---------------------------------------------------------------------------
# Ortak metrikler
# ---------------------------------------------------------------------------

def collect_common_metrics(doc, standard=None):
    """Tum disiplinler icin ortak metrikleri toplar."""
    m = {}

    # Warnings
    try:
        m['warning_count'] = len(list(doc.GetWarnings()))
    except Exception:
        m['warning_count'] = 0

    # Sheets
    try:
        sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
    except Exception:
        sheets = []
    m['sheet_count'] = len(sheets)

    empty_sheets = 0
    unnamed_sheets = 0
    for sheet in sheets:
        try:
            vp = FilteredElementCollector(doc, sheet.Id).OfClass(Viewport).GetElementCount()
            sc = FilteredElementCollector(doc, sheet.Id).OfClass(ScheduleSheetInstance).GetElementCount()
            if (vp + sc) == 0:
                empty_sheets += 1
        except Exception:
            empty_sheets += 1
        sn = utext(sheet.SheetNumber).strip()
        sname = utext(sheet.Name).strip()
        if not sn or not sname:
            unnamed_sheets += 1
    m['empty_sheet_count'] = empty_sheets
    m['unnamed_sheet_count'] = unnamed_sheets

    # Views
    views = _get_views(doc)
    m['view_count'] = len(views)

    bad_named = 0
    from qc_utils import is_bad_name
    for v in views:
        if is_bad_name(safe_element_name(v)):
            bad_named += 1
    m['default_named_view_count'] = bad_named

    # View type counts
    m['section_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Section)
    m['detail_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Detail)
    m['elevation_view_count'] = sum(1 for v in views if v.ViewType == ViewType.Elevation)
    m['plan_view_count'] = sum(1 for v in views if v.ViewType in (ViewType.FloorPlan, ViewType.CeilingPlan, ViewType.AreaPlan))

    # View template ratio
    if views:
        m['view_template_ratio'] = round(
            sum(1 for v in views if _has_template(v)) / float(len(views)), 3
        )
        m['views_without_template'] = sum(1 for v in views if not _has_template(v))
    else:
        m['view_template_ratio'] = 0.0
        m['views_without_template'] = 0

    # Levels & Grids
    try:
        levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
        grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
    except Exception:
        levels = []
        grids = []
    m['level_count'] = len(levels)
    m['grid_count'] = len(grids)

    # Pinned ratio
    all_ref = grids + levels
    if all_ref:
        m['pinned_grids_ratio'] = round(
            sum(1 for e in all_ref if _is_pinned(e)) / float(len(all_ref)), 3
        )
    else:
        m['pinned_grids_ratio'] = 0.0

    # Links
    try:
        link_types = list(FilteredElementCollector(doc).OfClass(RevitLinkType).ToElements())
    except Exception:
        link_types = []
    m['link_count'] = len(link_types)
    unloaded = 0
    for lt in link_types:
        try:
            if not RevitLinkType.IsLoaded(doc, lt.Id):
                unloaded += 1
        except Exception:
            pass
    m['unloaded_link_count'] = unloaded

    # CAD imports
    try:
        imports = list(FilteredElementCollector(doc).OfClass(ImportInstance).ToElements())
    except Exception:
        imports = []
    cad_imp = 0
    cad_lnk = 0
    for inst in imports:
        try:
            if inst.IsLinked:
                cad_lnk += 1
            else:
                cad_imp += 1
        except Exception:
            cad_imp += 1
    m['cad_import_count'] = cad_imp
    m['cad_link_count'] = cad_lnk

    # In-place families
    try:
        families = list(FilteredElementCollector(doc).OfClass(Family).ToElements())
        m['inplace_family_count'] = sum(1 for f in families if _safe_inplace(f))
    except Exception:
        m['inplace_family_count'] = 0

    # Schedules
    try:
        schedules = list(FilteredElementCollector(doc).OfClass(ViewSchedule).ToElements())
        m['schedule_count'] = len([s for s in schedules if not s.IsTitleblockRevisionSchedule])
    except Exception:
        m['schedule_count'] = 0

    # Annotation counts
    m['dimension_count'] = _count_cat(doc, BuiltInCategory.OST_Dimensions)
    m['text_note_count'] = _count_cat(doc, BuiltInCategory.OST_TextNotes)

    # Tag counts
    m['room_tag_count'] = _count_cat(doc, BuiltInCategory.OST_RoomTags)
    m['door_tag_count'] = _count_cat(doc, BuiltInCategory.OST_DoorTags)
    m['window_tag_count'] = _count_cat(doc, BuiltInCategory.OST_WindowTags)

    # File info
    try:
        m['file_size_mb'] = round(os.path.getsize(doc.PathName) / (1024.0 * 1024.0), 1) if doc.PathName and os.path.exists(doc.PathName) else -1
    except Exception:
        m['file_size_mb'] = -1

    try:
        m['revit_version'] = utext(doc.Application.VersionNumber)
    except Exception:
        m['revit_version'] = u''

    # Starting view
    try:
        sv = doc.GetElement(doc.StartingViewId) if doc.StartingViewId else None
        m['has_starting_view'] = sv is not None
    except Exception:
        m['has_starting_view'] = False

    # Project info
    try:
        pinfo = doc.ProjectInformation
        filled = 0
        for bip in [BuiltInParameter.PROJECT_NAME, BuiltInParameter.PROJECT_NUMBER,
                     BuiltInParameter.PROJECT_ADDRESS, BuiltInParameter.CLIENT_NAME]:
            try:
                p = pinfo.get_Parameter(bip)
                if p is not None and p.HasValue:
                    val = p.AsString()
                    if val is not None and utext(val).strip():
                        filled += 1
            except Exception:
                pass
        m['project_info_filled'] = round(filled / 4.0, 2)
    except Exception:
        m['project_info_filled'] = 0.0

    # Workshared
    try:
        m['is_workshared'] = doc.IsWorkshared
    except Exception:
        m['is_workshared'] = False

    return m


def _safe_inplace(fam):
    try:
        return fam.IsInPlace
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Disipline ozgu metrikler
# ---------------------------------------------------------------------------

def collect_discipline_metrics(doc):
    m = {}
    # Mimari
    m['rooms_count'] = _count_cat(doc, BuiltInCategory.OST_Rooms)
    m['doors_count'] = _count_cat(doc, BuiltInCategory.OST_Doors)
    m['windows_count'] = _count_cat(doc, BuiltInCategory.OST_Windows)
    m['walls_count'] = _count_cat(doc, BuiltInCategory.OST_Walls)
    m['floors_count'] = _count_cat(doc, BuiltInCategory.OST_Floors)
    m['ceilings_count'] = _count_cat(doc, BuiltInCategory.OST_Ceilings)
    m['roofs_count'] = _count_cat(doc, BuiltInCategory.OST_Roofs)
    m['stairs_count'] = _count_cat(doc, BuiltInCategory.OST_Stairs)
    m['ramps_count'] = _count_cat(doc, BuiltInCategory.OST_Ramps)
    m['shafts_count'] = _count_cat(doc, BuiltInCategory.OST_ShaftOpening)

    # Statik
    m['structural_columns_count'] = _count_cat(doc, BuiltInCategory.OST_StructuralColumns)
    m['structural_framing_count'] = _count_cat(doc, BuiltInCategory.OST_StructuralFraming)
    m['structural_foundation_count'] = _count_cat(doc, BuiltInCategory.OST_StructuralFoundation)
    m['rebar_count'] = _count_cat(doc, BuiltInCategory.OST_Rebar)
    m['structural_connections_count'] = _count_cat(doc, BuiltInCategory.OST_StructConnections)

    # Mekanik
    m['spaces_count'] = _count_cat(doc, BuiltInCategory.OST_MEPSpaces)
    m['mechanical_equipment_count'] = _count_cat(doc, BuiltInCategory.OST_MechanicalEquipment)
    m['duct_count'] = _count_cat(doc, BuiltInCategory.OST_DuctCurves)
    m['flex_duct_count'] = _count_cat(doc, BuiltInCategory.OST_FlexDuctCurves)
    m['duct_fitting_count'] = _count_cat(doc, BuiltInCategory.OST_DuctFitting)
    m['duct_accessory_count'] = _count_cat(doc, BuiltInCategory.OST_DuctAccessory)
    m['duct_terminal_count'] = _count_cat(doc, BuiltInCategory.OST_DuctTerminal)
    m['pipe_count'] = _count_cat(doc, BuiltInCategory.OST_PipeCurves)
    m['flex_pipe_count'] = _count_cat(doc, BuiltInCategory.OST_FlexPipeCurves)
    m['pipe_fitting_count'] = _count_cat(doc, BuiltInCategory.OST_PipeFitting)
    m['pipe_accessory_count'] = _count_cat(doc, BuiltInCategory.OST_PipeAccessory)
    m['plumbing_fixture_count'] = _count_cat(doc, BuiltInCategory.OST_PlumbingFixtures)

    # Elektrik
    m['electrical_equipment_count'] = _count_cat(doc, BuiltInCategory.OST_ElectricalEquipment)
    m['electrical_fixture_count'] = _count_cat(doc, BuiltInCategory.OST_ElectricalFixtures)
    m['lighting_fixture_count'] = _count_cat(doc, BuiltInCategory.OST_LightingFixtures)
    m['conduit_count'] = _count_cat(doc, BuiltInCategory.OST_Conduit)
    m['conduit_fitting_count'] = _count_cat(doc, BuiltInCategory.OST_ConduitFitting)
    m['cable_tray_count'] = _count_cat(doc, BuiltInCategory.OST_CableTray)
    m['fire_alarm_device_count'] = _count_cat(doc, BuiltInCategory.OST_FireAlarmDevices)
    m['data_device_count'] = _count_cat(doc, BuiltInCategory.OST_DataDevices)
    m['communication_device_count'] = _count_cat(doc, BuiltInCategory.OST_CommunicationDevices)
    m['electrical_circuit_count'] = _count_cat(doc, BuiltInCategory.OST_ElectricalCircuit)

    # Turetilmis
    m['mep_curve_total'] = m['duct_count'] + m['flex_duct_count'] + m['pipe_count'] + m['flex_pipe_count']
    m['electrical_device_total'] = (
        m['electrical_fixture_count'] + m['lighting_fixture_count']
        + m['fire_alarm_device_count'] + m['data_device_count']
        + m['communication_device_count']
    )
    m['electrical_route_total'] = m['conduit_count'] + m['cable_tray_count']

    # MEP tag counts
    m['mep_tag_count'] = (
        _count_cat(doc, BuiltInCategory.OST_DuctTags)
        + _count_cat(doc, BuiltInCategory.OST_PipeTags)
        + _count_cat(doc, BuiltInCategory.OST_MechanicalEquipmentTags)
    )
    m['electrical_tag_count'] = (
        _count_cat(doc, BuiltInCategory.OST_ElectricalFixtureTags)
        + _count_cat(doc, BuiltInCategory.OST_LightingFixtureTags)
    )

    # Structural tag counts
    m['structural_column_tag_count'] = _count_cat(doc, BuiltInCategory.OST_StructuralColumnTags)
    m['structural_framing_tag_count'] = _count_cat(doc, BuiltInCategory.OST_StructuralFramingTags)

    return m


# ---------------------------------------------------------------------------
# Title block toplama — SKOR DISI, raporlama verisi
# ---------------------------------------------------------------------------

def collect_titleblock_details(doc):
    """Her pafta icin title block parametre detaylarini toplar."""
    try:
        sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
    except Exception:
        return []

    PERSONNEL = ['Drawn By', 'Designed By', 'Checked By', 'Approved By']
    DATE_FIELDS = ['Date', 'Sheet Issue Date']
    rows = []

    for sheet in sheets:
        row = {
            'sheet_number': utext(sheet.SheetNumber),
            'sheet_name': utext(sheet.Name),
            'titleblock_found': False,
            'titleblock_family': u'',
            'fields': {},
        }

        try:
            tbs = list(
                FilteredElementCollector(doc, sheet.Id)
                .OfCategory(BuiltInCategory.OST_TitleBlocks)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        except Exception:
            tbs = []

        row['titleblock_found'] = len(tbs) > 0

        if tbs:
            tb = tbs[0]
            try:
                row['titleblock_family'] = utext(tb.Symbol.Family.Name)
            except Exception:
                row['titleblock_family'] = u""

            for field in PERSONNEL + DATE_FIELDS:
                row['fields'][field] = safe_param(tb, field)

            # Sheet fallback
            if not row['fields'].get('Sheet Name'):
                row['fields']['Sheet Name'] = row['sheet_name']
            if not row['fields'].get('Sheet Number'):
                row['fields']['Sheet Number'] = row['sheet_number']

        rows.append(row)

    return rows


def summarize_titleblock(tb_details):
    """Title block ozet metrikleri — skor disi, raporlama icin."""
    total = len(tb_details)
    if total == 0:
        return {'tb_total_sheets': 0}

    no_tb = sum(1 for r in tb_details if not r['titleblock_found'])
    return {
        'tb_total_sheets': total,
        'tb_no_titleblock': no_tb,
        'tb_missing_drawn_by': sum(1 for r in tb_details if not r['fields'].get('Drawn By')),
        'tb_missing_designed_by': sum(1 for r in tb_details if not r['fields'].get('Designed By')),
        'tb_missing_checked_by': sum(1 for r in tb_details if not r['fields'].get('Checked By')),
        'tb_missing_approved_by': sum(1 for r in tb_details if not r['fields'].get('Approved By')),
    }
