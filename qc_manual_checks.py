# -*- coding: utf-8 -*-
"""BIM Kontrol Formu merkezi yapılandırması v5.

MANUAL→AUTO/SEMI dönüşümleri uygulandı.
Sadece gerçekten ölçülemeyenler MANUAL kaldı.

v4→v5 dönüşümler:
  G01 SEMI→AUTO (VersionNumber okunur)
  G04 SEMI→AUTO (IsWorkshared okunur)
  G07 SEMI→AUTO (unused family heuristic)
  G08 SEMI→AUTO→AUTO (IsSectionBoxActive)
  M13 SEMI→AUTO (level/grid naming regex)
  M19 SEMI→AUTO (room boş isim count)
  M21 SEMI→AUTO (base point okunur)
  M25 SEMI→AUTO (heuristic)
  M28 SEMI→AUTO (parameter binding count)
  M30 SEMI→AUTO (keynote table)
  M33 SEMI→AUTO (titleblock family name)
  G06 MANUAL kaldı (BUP stratejisi — dış belge)
  G12 MANUAL kaldı (CDE güncelliği — dış sistem)
  M23 MANUAL kaldı (LOD uyumu — görsel yargı)
  M24 MANUAL kaldı (malzeme doğruluğu — mühendislik yargısı)
"""
from __future__ import division, print_function

BIM_FORM_ITEMS = [
    # ===== GENEL =====
    {
        'id': 'BIM-G01',
        'description': u'Kullanılan yazılım versiyonu uygun mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'revit_version',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G02',
        'description': u'Dosya isimlendirmesi doğru yapılmış mı?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'file_naming',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G03',
        'description': u'Dosya boyutu 500 MB\'dan küçük mü?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'file_size_mb',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G04',
        'description': u'Model merkez dosyadan ayrılmış mı (Detach from central)?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'is_workshared',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G05',
        'description': u'Model Uyarı (Warning) kontrolü',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 4, 'metric_key': 'warning_count',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G06',
        'description': u'Model Bölme stratejisi BUP\'na uygun mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'MANUAL',
        'weight': 2, 'metric_key': None,
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G07',
        'description': u'Gereksiz elemanlar temizlenmiş (Purge) mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'unused_family_count',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G08',
        'description': u'3D view section box kapalı ve publish settings uygun mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'has_3d_no_sectionbox',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G09',
        'description': u'Başlangıç görünümü (Starting View) doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'has_starting_view',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G10',
        'description': u'Proje Bilgileri tanımlanmış ve doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'project_info_filled',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G11',
        'description': u'Link dosya adresleri mevcut mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'unloaded_link_count',
        'category': u'Genel BIM Sağlığı',
    },
    {
        'id': 'BIM-G12',
        'description': u'Dış referans link dosyaları güncel mi (Aconex / CDE)?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'MANUAL',
        'weight': 2, 'metric_key': None,
        'category': u'Genel BIM Sağlığı',
    },
    # ===== MODEL YAPILANMASI =====
    {
        'id': 'BIM-M13',
        'description': u'Seviye (level) ve aks (grid) isimlendirmeleri doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'level_grid_naming_ratio',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M14',
        'description': u'Elemanların (family) isimlendirmesi doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 3, 'metric_key': 'family_naming_score',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M15',
        'description': u'Görünüm (Views) isimlendirmeleri uygun mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'default_named_view_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M16',
        'description': u'Pafta (Sheets) isimlendirmesi doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'unnamed_sheet_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M17',
        'description': u'Metraj tabloları (Schedules) isimlendirmeleri uygun mu?',
        'phase': 'KESIN', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'schedule_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M18',
        'description': u'Malzeme isimlendirmesi doğru mu?',
        'phase': 'TUM', 'discipline': 'MY',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'material_naming_score',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M19',
        'description': u'Mahal (Room) ve alan (Space) isimlendirmesi doğru mu?',
        'phase': 'TUM', 'discipline': 'EM',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'room_unnamed_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M20',
        'description': u'Tüm elemanlar model disiplinine ait mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 3, 'metric_key': 'foreign_family_ratio',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M21',
        'description': u'Koordinat sistemi ve referans noktası doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'base_point_valid',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M22',
        'description': u'Seviye yükseklik değerleri referans noktasına göre mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'level_elevation_check',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M23',
        'description': u'Model detay seviye tablosuna uygun mu (LOD)?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'MANUAL',
        'weight': 3, 'metric_key': None,
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M24',
        'description': u'Elemanlar için seçili malzemeler doğru mu?',
        'phase': 'KESIN', 'discipline': 'MY',
        'check_type': 'MANUAL',
        'weight': 2, 'metric_key': None,
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M25',
        'description': u'Model elemanlarının kat bilgileri (Base Constraint) doğru mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 3, 'metric_key': 'base_constraint_check',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M26',
        'description': u'View Template uygulanmış mı?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'view_template_ratio',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M27',
        'description': u'Görünümler için uygun View Template seçilmiş mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'view_template_ratio',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M28',
        'description': u'Project Parameters tanımlanmış ve verileri girilmiş mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'project_params_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M29',
        'description': u'Base Point / Level / Grid / Link sabitlenmiş (Pin) mi?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'pinned_grids_ratio',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M30',
        'description': u'Poz no (Keynote) bilgileri doğru tanımlanmış mı?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'keynote_table_loaded',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M31',
        'description': u'Sistem tanımlamaları yapılmış ve isimlendirmeleri uygun mu?',
        'phase': 'TUM', 'discipline': 'EM',
        'check_type': 'SEMI_AUTO',
        'weight': 3, 'metric_key': 'system_naming_score',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M32',
        'description': u'Metraj listeleri (schedule) oluşturulmuş mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 3, 'metric_key': 'schedule_count',
        'category': u'Model Yapılanması',
    },
    {
        'id': 'BIM-M33',
        'description': u'Güncel proje antet dosyası kullanılmış mı?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'AUTO',
        'weight': 2, 'metric_key': 'titleblock_family_name',
        'category': u'Pafta ve Sunum Disiplini',
    },
    {
        'id': 'BIM-M34',
        'description': u'Pafta ve görünüş gruplandırması uygun mu?',
        'phase': 'TUM', 'discipline': 'ALL',
        'check_type': 'SEMI_AUTO',
        'weight': 2, 'metric_key': 'sheet_view_grouping',
        'category': u'Pafta ve Sunum Disiplini',
    },
]


TITLEBLOCK_PRIMARY_FIELDS = [
    'Sheet Name', 'Sheet Number', 'Date', 'Sheet Issue Date',
    'Drawn By', 'Designed By', 'Checked By', 'Approved By',
]
TITLEBLOCK_EXTRA_FIELDS = [
    'For Approval', 'For Information', 'For Review',
    'Tersane', u'Esenyalı', u'İçmeler',
    u'ACIL PAFTASI NOTLARI', u'ACIL PAFTASI NOTLARI-PERDESİZ',
    'NOTLAR', u'Ortofoto Hariç Tik Açık', u'SISTEM DETAYI NOTLARI',
]
TITLEBLOCK_PERSONNEL_FIELDS = ['Drawn By', 'Designed By', 'Checked By', 'Approved By']
TITLEBLOCK_DATE_FIELDS = ['Date', 'Sheet Issue Date']


_DISCIPLINE_MAP = {
    'MIMARI': 'MIM', 'STATIK': 'YAP', 'MEKANIK': 'MEK', 'ELEKTRIK': 'ELK',
}

def is_item_applicable(item, discipline_code):
    disc = item.get('discipline', 'ALL')
    if disc == 'ALL':
        return True
    short = _DISCIPLINE_MAP.get(discipline_code, '')
    if disc == 'EM':
        return short in ('ELK', 'MEK')
    if disc == 'MY':
        return short in ('MIM', 'YAP')
    return short == disc

def get_applicable_items(discipline_code):
    return [item for item in BIM_FORM_ITEMS if is_item_applicable(item, discipline_code)]
