# -*- coding: utf-8 -*-
"""Model içi state yönetimi — ExtensibleStorage + dosya fallback.

Rapor geçmişi, disiplin seçimi, imza bilgileri ve ayarlar
Revit modeli içinde DataStorage schema'sında saklanır.
Başarısız olursa %APPDATA% altına JSON dosyasına düşer.
"""
from __future__ import print_function

import hashlib
import io
import json
import os

from System import Guid, String
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    Transaction,
    TransactionStatus,
)
from Autodesk.Revit.DB.ExtensibleStorage import (
    AccessLevel,
    DataStorage,
    Entity,
    Schema,
    SchemaBuilder,
)

from qc_utils import get_logger

logger = get_logger()

SCHEMA_GUID = Guid("4d9c3b3b-7f9b-4706-9d51-aadf1b7ef7cb")
SCHEMA_NAME = "RevitKaliteKontrolCorporateState"
VENDOR_ID = "RKQC"  # Revit Kalite Kontrol — kendi vendor ID'niz
FIELD_NAME = "payload_json"


# ---------------------------------------------------------------------------
# Fallback dosya yolu
# ---------------------------------------------------------------------------

def _safe_state_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    folder = os.path.join(base, 'pyRevit', 'RevitKaliteKontrol', 'state')
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as exc:
            logger.error(u"State klasörü oluşturulamadı: %s — %s", folder, exc)
            raise
    return folder


def _safe_doc_key(doc):
    raw = doc.PathName or doc.Title or 'unsaved_document'
    try:
        rawb = raw.encode('utf-8')
    except Exception:
        try:
            rawb = bytes(raw)
        except Exception:
            rawb = str(raw).encode('utf-8')
    return hashlib.md5(rawb).hexdigest()


def _fallback_path(doc):
    return os.path.join(_safe_state_dir(), _safe_doc_key(doc) + '.json')


# ---------------------------------------------------------------------------
# ExtensibleStorage schema
# ---------------------------------------------------------------------------

def _get_or_create_schema():
    schema = Schema.Lookup(SCHEMA_GUID)
    if schema:
        return schema
    builder = SchemaBuilder(SCHEMA_GUID)
    builder.SetSchemaName(SCHEMA_NAME)
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    try:
        builder.SetVendorId(VENDOR_ID)
    except Exception:
        pass
    field = builder.AddSimpleField(FIELD_NAME, String)
    try:
        field.SetDocumentation('Kurumsal kalite kontrol state payload json')
    except Exception:
        pass
    return builder.Finish()


def _find_storage_element(doc, schema):
    try:
        all_ds = FilteredElementCollector(doc).OfClass(DataStorage).ToElements()
        for ds in all_ds:
            try:
                ent = ds.GetEntity(schema)
                if ent and ent.IsValidObject:
                    return ds
            except Exception:
                continue
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Fallback kaydetme / yükleme
# ---------------------------------------------------------------------------

def _save_fallback(doc, payload):
    try:
        path = _fallback_path(doc)
        with io.open(path, 'w', encoding='utf-8') as fp:
            fp.write(json.dumps(payload, ensure_ascii=False, indent=2))
        return True, u'Sidecar JSON kaydı yapıldı', path
    except (IOError, OSError) as exc:
        logger.error(u"Fallback kaydetme hatası: %s", exc)
        return False, u'Fallback kaydı başarısız: {0}'.format(exc), None


def _load_fallback(doc):
    try:
        path = _fallback_path(doc)
        if not os.path.exists(path):
            return None, None
        with io.open(path, 'r', encoding='utf-8') as fp:
            return json.loads(fp.read()), path
    except (IOError, OSError, ValueError) as exc:
        logger.error(u"Fallback yükleme hatası: %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# Kaydetme / yükleme
# ---------------------------------------------------------------------------

def save_project_state(doc, payload):
    """State'i model içi DataStorage'a kaydeder.
    Başarısız olursa dosya fallback'ine düşer.

    Returns:
        (success: bool, message: str, source_ref: str)
    """
    payload = payload or {}
    try:
        schema = _get_or_create_schema()
        field = schema.GetField(FIELD_NAME)
        raw = json.dumps(payload, ensure_ascii=False)

        t = Transaction(doc, 'Revit Kalite Kontrol - Kurumsal Durum Kaydet')
        t.Start()
        try:
            target = _find_storage_element(doc, schema)
            if target is None:
                target = DataStorage.Create(doc)
            entity = Entity(schema)
            entity.Set[String](field, raw)
            target.SetEntity(entity)
            status = t.Commit()
            if status != TransactionStatus.Committed:
                logger.warning(u"Transaction commit durumu: %s", status)
                return _save_fallback(doc, payload)
        except Exception as exc:
            if t.HasStarted() and not t.HasEnded():
                t.RollBack()
            logger.error(u"DataStorage kaydetme hatası: %s", exc)
            return _save_fallback(doc, payload)

        return True, u'DataStorage ile modele kaydedildi', 'model-datastorage'
    except Exception as exc:
        logger.error(u"Schema/Transaction oluşturma hatası: %s", exc)
        return _save_fallback(doc, payload)


def load_project_state(doc):
    """State'i model içinden veya fallback dosyasından yükler.

    Returns:
        (state_dict | None, source_ref | None)
    """
    # 1) DataStorage'dan oku
    try:
        schema = Schema.Lookup(SCHEMA_GUID)
        if schema:
            field = schema.GetField(FIELD_NAME)
            target = _find_storage_element(doc, schema)
            if target:
                entity = target.GetEntity(schema)
                if entity and entity.IsValidObject:
                    raw = entity.Get[String](field)
                    if raw:
                        return json.loads(raw), 'model-datastorage'
    except Exception as exc:
        logger.debug(u"DataStorage okuma denemesi başarısız: %s", exc)

    # 2) Eski sürüm — ProjectInformation üzerinden (geçiş desteği)
    try:
        schema = Schema.Lookup(SCHEMA_GUID)
        if schema:
            field = schema.GetField(FIELD_NAME)
            entity = doc.ProjectInformation.GetEntity(schema)
            if entity and entity.IsValidObject:
                raw = entity.Get[String](field)
                if raw:
                    logger.info(u"State, ProjectInformation'dan okundu (eski sürüm)")
                    return json.loads(raw), 'model-projectinfo'
    except Exception as exc:
        logger.debug(u"ProjectInformation okuma denemesi başarısız: %s", exc)

    # 3) Dosya fallback
    fallback_data, fallback_path = _load_fallback(doc)
    if fallback_data:
        return fallback_data, fallback_path
    return None, None


# ---------------------------------------------------------------------------
# Rapor geçmişi yönetimi
# ---------------------------------------------------------------------------

def get_last_report_summary(state, discipline_code):
    """Belirtilen disiplin için son rapor özetini döndürür."""
    state = state or {}
    history = (state.get('report_history') or {}).get(discipline_code) or []
    if history:
        return history[-1]
    return None


def get_report_history(state, discipline_code):
    """Belirtilen disiplin için tüm rapor geçmişini döndürür."""
    state = state or {}
    return list((state.get('report_history') or {}).get(discipline_code) or [])


def append_report_history(state, discipline_code, report_summary, max_count=15):
    """Rapor geçmişine yeni özet ekler, max_count sınırını uygular."""
    state = state or {}
    history_map = state.get('report_history') or {}
    rows = list(history_map.get(discipline_code) or [])
    rows.append(report_summary)
    if max_count > 0 and len(rows) > max_count:
        rows = rows[-max_count:]
    history_map[discipline_code] = rows
    state['report_history'] = history_map
    return state
