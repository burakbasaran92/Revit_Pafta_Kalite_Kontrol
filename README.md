# RevitKaliteKontrolV3.extension — v3.2

Revit BIM projelerinin teslim öncesi kurumsal kalite kontrolü.

## Gereksinimler
- pyRevit 4.8+ (CPython3)
- Revit 2019+
- openpyxl (xlsx export için): `pip install openpyxl`

## v3.2 Yenilikler

### Statik = Kalıp Projesi
- Temel/donatı yokluğu artık skor kırmaz
- Kalıp Projesi Kapsamı kategorisi eklendi
- Temel/donatı varsa bonus, yoksa ceza yok

### BIM Kontrol Formu Entegrasyonu
- 34 maddelik BIM kontrol formu sisteme gömüldü
- AUTO / SEMI_AUTO / MANUAL sınıflandırma
- Disiplin ve aşama bazlı uygulanabilirlik
- BIM Form Uygunluğu: ayrı kategori ve ayrı skor

### Title Block Kontrolü
- Drawn By, Designed By, Checked By, Approved By
- Sheet Issue Date, Date/Time Stamp
- Onay kutuları, not alanları
- Pafta bazlı detay raporu
- Personel ve birincil alan doluluğu oranı

### Excel Raporu
- 6 sheet'li profesyonel .xlsx
- Executive Summary, BIM Form, Title Block, Action List, Red Flags, Raw Metrics
- Başlık stili, filtre, freeze, renk kodlama

### Güçlendirilmiş Disiplin Kontrolleri
- Mimari: 8 varlık kontrolü + görünüş çeşitliliği
- Mekanik/Elektrik: mevcut kontroller korundu
- Tüm disiplinler: Pafta ve BIM Form kategorileri

## Komutlar
1. **Kurumsal Ayarlar** — Disiplin, imza, standart JSON
2. **Kurumsal QC** — Tam kontrol + Excel/CSV/JSON export
3. **Rapor Geçmişi** — Trend analizi

## Ağırlık Sistemi (toplam 100)
- Uyarı Yönetimi: 10
- Modelleme Disiplini: 8
- Temel Kurgu: 7
- Disiplin Özel (2 kategori): 20 + 15 = 35
- Pafta ve Title Block: 20
- BIM Formu Uygunluğu: 20
