# V3 Değişiklikleri

## V3.2.0 — Kalıp Projesi + BIM Form + Title Block + Excel

### Statik = Kalıp Projesi
- `_evaluate_structural_foundation_rebar` kaldırıldı
- Yeni `_evaluate_kalip_project_scope`: shaft, merdiven, kesit/detay, pafta sayısı
- Temel/donatı yokluğu skor kırmaz; varsa bonus notu
- Red flag'lardan foundation/rebar çıkarıldı

### BIM Kontrol Formu
- 34 maddelik BIM kontrol formu `qc_bim_form_config.py`'de merkezi tanım
- AUTO / SEMI_AUTO / MANUAL sınıflandırma
- Disiplin ve aşama bazlı uygulanabilirlik filtresi
- `qc_scoring.py` ile madde bazlı değerlendirme
- Pending maddeler denominatörden çıkarılır — skoru bozmazlar
- "BIM Formu Uygunluğu" yeni kategori (ağırlık: 20)

### Title Block Kontrolü
- `collect_titleblock_details()`: Her paftada TB instance parametreleri
- 8 birincil alan + 11 ekstra alan okunur
- Drawn By, Designed By, Checked By, Approved By, Date, Issue Date
- Onay kutuları, not alanları, disiplin bilgisi
- `summarize_titleblock()`: Eksik sayıları ve oranlar
- "Pafta ve Title Block" yeni kategori (ağırlık: 20)
- TB eksik paftalar kırmızı bayrak olarak eklenir

### Excel (.xlsx) Raporu
- `qc_export_excel.py`: openpyxl ile 6 sheet
- Sheet 1: Executive Summary (proje, skor, kategoriler)
- Sheet 2: BIM Form Compliance (34 madde detayı)
- Sheet 3: Title Block Details (pafta bazlı TB parametreleri)
- Sheet 4: Action List (öncelikli aksiyon listesi)
- Sheet 5: Red Flags & Manuel Kontrol
- Sheet 6: Raw Metrics (tüm ham veriler + TB özet)
- Header stili, auto filter, freeze panes, renk kodlama
- openpyxl yoksa uyarı verir, CSV'ye fallback

### Puanlama Sistemi
- Uyarı Yönetimi: 10
- Modelleme Disiplini: 8
- Temel Kurgu: 7
- Disiplin Özel 1: 20
- Disiplin Özel 2: 15
- Pafta ve Title Block: 20
- BIM Formu Uygunluğu: 20
- TOPLAM: 100

### Güçlendirilmiş Disiplinler
- Mimari: 8 varlık kontrolü (room, wall, door, window, floor, stairs/ramp, ceiling/roof, shaft)
- Mimari: Görünüş ve sunum (section, detail, elevation, sheet, schedule, naming)
- Statik: Taşıyıcı sistem + kalıp projesi kapsamı
- Mekanik/Elektrik: Mevcut kontroller korundu

### Aksiyon Listesi
- Kırmızı bayraklardan otomatik aksiyon üretimi
- Title block eksiklerinden aksiyon üretimi
- BIM form pending maddelerinden aksiyon üretimi
- Öncelik sıralaması, kritiklik işareti

### Yeni Dosyalar
- `lib/qc_bim_form_config.py` — BIM form merkezi yapılandırma
- `lib/qc_scoring.py` — Puanlama motoru
- `lib/qc_export_excel.py` — Excel rapor üretici

### Geriye Dönük Uyumluluk
- CSV/JSON export bozulmadı
- Mevcut state yapısı korundu
- Eski raporlarla karşılaştırma çalışır

## V3.1.0
- engine: cpython zorunlu
- CSV custom writer
- Merkezi log hata koruması
- Bayrak normalize
- Schema doğrulama
- Türkçe view prefix
- Rapor Geçmişi butonu

## V3.0.0
- İlk kurumsal sürüm
