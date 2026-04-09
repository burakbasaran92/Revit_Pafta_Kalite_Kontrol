# V2 Değişiklik Özeti

## V1'e göre eklenenler
- Mimari, Statik, Mekanik, Elektrik için ayrı skor setleri
- Proje disiplini seçme komutu
- Proje içine durum kaydetme denemesi (Extensible Storage)
- Fallback olarak sidecar JSON kayıt
- CSV raporunda disiplin ve manuel kontrol maddeleri

## Mantık
Önce proje hangi disiplin için değerlendirilecekse onu işaretliyorsun.
Sonra QC komutu sadece o disipline uygun kriterleri çalıştırıyor.

## Dikkat
Bu sürüm ofis standardına göre mutlaka revize edilmelidir.
Özellikle şu üç şey sana göre değişecek:
1. ağırlıklar
2. kırmızı bayrak eşikleri
3. zorunlu saydığın disiplin elemanları
