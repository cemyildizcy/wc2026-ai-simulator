# 2026 FIFA Dünya Kupası AI Simülatörü

Bu proje, **2026 FIFA Dünya Kupası'nı 48 takımlı yeni formatıyla veri bilimi kullanarak simüle eden** uçtan uca bir futbol analitiği projesidir.

Model; takım gücü, resmi FIFA sıralaması, **World Football Elo Ratings** üzerinden çekilen güncel ELO puanları, EA FC 25 oyuncu verileri, Dünya Kupası geçmişi, son form, piyasa değeri ve StatsBomb xG göstergelerini birleştirerek maç skorlarını olasılıksal olarak üretir. Ardından turnuvayı **10.000 kez Monte Carlo simülasyonu** ile çalıştırır ve takımların şampiyonluk / final / yarı final / eleme turu olasılıklarını hesaplar.

Ayrıca proje içinde sonuçları incelemek için **Türkçe Streamlit dashboard** bulunur.

> Not: Bu proje bir “kesin tahmin” veya bahis aracı değildir. Amaç, Dünya Kupası sonuçlarını olasılık dağılımları üzerinden modelleyen bir veri bilimi portföy projesi oluşturmaktır.

---

## Proje Ne Yapıyor?

Bu proje aşağıdaki süreci uçtan uca gerçekleştirir:

1. 2026 Dünya Kupası'na uygun **48 takımlı veri seti** hazırlar.
2. Takımların grup bilgilerini, FIFA sırasını, World Football Elo puanını, geçmiş başarılarını ve güncel formunu işler.
3. EA FC 25 oyuncu verilerinden takımlar için kadro gücü feature'ları üretir.
4. StatsBomb açık verisinden Dünya Kupası xG / xGA / şut / pas göstergeleri ekler.
5. Her takım için birleşik bir **team power score** hesaplar.
6. Maçlar için Poisson tabanlı beklenen gol modeli kurar.
7. 2026 formatına uygun grup aşaması ve eleme turunu simüle eder.
8. Turnuvayı 10.000 kez çalıştırarak Monte Carlo olasılıklarını üretir.
9. En olası bracket yolunu ve maç skor dağılımlarını çıkarır.
10. Sonuçları CSV, rapor, görsel ve interaktif dashboard olarak sunar.

---

## Kullanılan Ana Yöntemler

### 1. Feature Engineering

Takım gücünü tek bir kaynaktan değil, birden fazla veri ailesinden oluşturduk.

Kullanılan feature grupları:

- FIFA sıralaması
- World Football Elo Ratings üzerinden çekilen güncel ELO puanı
- Kadro piyasa değeri
- Dünya Kupası geçmişi
- Son 10 / son 20 maç formu
- Eleme performansı
- Grup zorluk endeksi
- Teknik direktör Dünya Kupası deneyimi
- StatsBomb xG / xGA / şut / pas verileri
- EA FC 25 oyuncu reytingleri

EA FC 25 tarafında üretilen bazı özellikler:

- İlk 11 ortalama overall reytingi
- İlk 23 ortalama overall reytingi
- Hücum / orta saha / savunma / kaleci reytingleri
- Kadro derinliği
- Yıldız oyuncu ve reytingi
- Ortalama yaş
- Genç yetenek skoru
- Hız, şut, pas, dripling, savunma, fizik ortalamaları

---

### 2. Takım Güç Skoru

Her takım için `team_power` adında birleşik bir güç skoru hesaplandı.

Bu skor; tarihsel başarı, güncel kadro kalitesi, form, reyting ve performans göstergelerinden oluşur. Daha sonra bu skor, maç bazında beklenen gol değerlerinin hesaplanmasında kullanılır.

Örnek çıktı:

```text
Germany      0.917
Brazil       0.904
Argentina    0.885
France       0.878
England      0.865
Spain        0.855
Portugal     0.801
```

---

### 3. Poisson xG Maç Modeli

Her maç için iki takımın beklenen gol değeri hesaplanır:

```text
home_xG
away_xG
```

Sonra bu xG değerlerinden Poisson dağılımı ile olası skorlar üretilir.

Model her maç için şunları hesaplar:

- Ev sahibi kazanma olasılığı
- Beraberlik olasılığı
- Deplasman kazanma olasılığı
- En olası skor
- İlk 5 skor dağılımı
- Maçın xG değerleri

Örnek final dağılımı:

```text
Brazil vs Argentina

1-1 → %12.4
1-0 → %9.7
0-1 → %9.1
2-1 → %8.4
1-2 → %8.0
```

Burada önemli nokta: Model “final kesin 1-0 biter” demiyor. 1-0 sadece merkezi bracket’te seçilen skor. Asıl çıktı bir olasılık dağılımı.

---

### 4. Monte Carlo Simülasyonu

Turnuva tek sefer değil, **10.000 kez** çalıştırıldı.

Her simülasyonda:

1. Grup maçları oynatılır.
2. Her grup için puan tablosu oluşturulur.
3. İlk 2 takım çıkar.
4. En iyi 8 üçüncü takım eklenir.
5. 32 takımlı eleme turu oynatılır.
6. Şampiyon, finalist, üçüncü ve aşama ulaşma bilgileri kaydedilir.

Bu 10.000 çalıştırmadan sonra takımların şampiyonluk olasılıkları hesaplandı.

---

## Güncel Model Sonuçları

> Bu sonuçlar, World Football Elo Ratings entegrasyonu sonrası güncellenmiştir. ELO verileri `eloratings.net` üzerinden pipeline çalıştırılırken otomatik çekilir.

### En Yüksek Şampiyonluk Olasılıkları

```text
Argentina      12.07%
Spain          11.69%
England         8.39%
France          7.46%
Germany         7.28%
Brazil          6.87%
Portugal        6.69%
Belgium         3.57%
Netherlands     3.00%
Turkey          2.66%
```

### Merkezi En Olası Final

```text
France 0-1 Argentina
```

Final xG:

```text
France:    1.28
Argentina: 1.39
```

Bu sonuçlar, finalin çok dengeli olduğunu ve küçük farkların büyük etkiler yaratabileceğini gösteriyor.

---

## Streamlit Dashboard

Projede sonuçları incelemek için Türkçe bir Streamlit dashboard bulunuyor.

Çalıştırmak için:

```bash
streamlit run dashboard/app.py
```

Streamlit Cloud deploy ayarı:

```text
Repository: cemyildizcy/wc2026-ai-simulator
Branch: main
Main file path: dashboard/app.py
```

Dashboard sayfaları:

### Genel Bakış

- Monte Carlo favorisi
- Merkezi final
- Takım ve maç sayısı
- İlk 15 şampiyonluk olasılığı
- En olası final eşleşmeleri
- Aşama ulaşma olasılıkları

### Takım İnceleme

Seçilen takım için:

- Şampiyonluk olasılığı
- İkincilik olasılığı
- Takım gücü
- FIFA sırası
- ELO reytingi
- Aşama ulaşma grafiği
- Hücum / savunma / kadro gücü radar grafiği
- Yıldız oyuncu
- Kadro piyasa değeri
- Son form bilgileri
- En olası turnuva yolu

### Maç İnceleme

Seçilen maç için:

- Kazanma / beraberlik / kaybetme olasılıkları
- xG karşılaştırması
- En olası 5 skor
- Maç sonucu dağılımı

### Grup Aşaması

- 12 grup tablosu
- Puan, galibiyet, beraberlik, mağlubiyet
- Atılan/yenen gol
- Averaj
- Ortalama grup gücü

### Eleme Turu

- Son 32
- Son 16
- Çeyrek final
- Yarı final
- Üçüncülük maçı
- Final
- Her maç için skor, xG ve G/B/M dağılımı

### Metodoloji

- Veri kaynakları
- Model mimarisi
- Poisson xG yaklaşımı
- Monte Carlo süreci
- Sınırlamalar

---

## Dosya Yapısı

```text
wc2026-ai-simulator/
│
├── dashboard/
│   └── app.py
│       Türkçe Streamlit dashboard.
│
├── src/
│   ├── pipeline.py
│   │   Ham verileri işler, temizler, final datasetleri hazırlar.
│   │
│   ├── add_eafc25_features.py
│   │   EA FC 25 oyuncu verilerinden takım bazlı kadro feature'ları üretir.
│   │
│   ├── simulate_tournament.py
│   │   Grup aşaması, eleme turu ve Monte Carlo simülasyonunu çalıştırır.
│   │
│   ├── generate_most_likely_path.py
│   │   En olası turnuva yolunu ve merkezi bracket çıktısını üretir.
│   │
│   ├── generate_match_score_distributions.py
│   │   Maç bazlı skor dağılımlarını hesaplar.
│   │
│   ├── create_eda_figures.py
│   │   Grafik ve görsel çıktıları üretir.
│   │
│   └── run_final_pipeline.py
│       Final pipeline'ı tek komutla çalıştırır.
│
├── data/
│   ├── raw/
│   │   Ham veri kaynakları.
│   │
│   ├── processed/
│   │   Temizlenmiş ara veri dosyaları.
│   │
│   └── final/
│       Modelin kullandığı final veri setleri.
│
├── outputs/
│   ├── *.csv
│   │   Simülasyon ve model çıktı dosyaları.
│   │
│   └── figures/
│       Grafik çıktıları.
│
├── reports/
│   Markdown formatında veri, model ve simülasyon raporları.
│
├── requirements.txt
│   Proje bağımlılıkları.
│
├── README.md
│   Proje açıklaması.
│
└── LICENSE
    MIT lisansı.
```

---

## Ana Veri Dosyaları

### Final Takım Veri Seti

```text
data/final/team_features_2026_enriched.csv
```

Bu dosya 48 takım için modelin kullandığı zenginleştirilmiş feature setidir.

İçerdiği bazı kolonlar:

```text
team
confederation
group
fifa_rank
wc_titles
best_finish
wc_appearances
is_host
elo_rating
squad_market_value_eur_m
recent form features
StatsBomb xG features
EA FC squad features
```

### 2026 Bracket Dosyası

```text
data/final/wc2026_bracket.json
```

Turnuva formatını tutar:

- 12 grup
- Grup maçları
- Son 32 eşleşme slotları
- Eleme turu yapısı

### Tarihsel Maçlar

```text
data/final/historical_matches.csv
```

Geçmiş maçlar ve form hesaplamaları için kullanılır.

---

## Ana Output Dosyaları

### Monte Carlo Takım Olasılıkları

```text
outputs/monte_carlo_team_probabilities.csv
```

Her takım için:

- Şampiyonluk olasılığı
- Final oynama olasılığı
- Yarı final olasılığı
- Çeyrek final olasılığı
- Eleme turuna kalma olasılığı
- Takım gücü

### Final Eşleşme Olasılıkları

```text
outputs/monte_carlo_final_pair_probabilities.csv
```

10.000 simülasyonda hangi final eşleşmelerinin ne kadar oluştuğunu gösterir.

### En Olası Turnuva Maçları

```text
outputs/most_likely_tournament_matches.csv
```

Grup aşamasından finale kadar merkezi en olası bracket yolundaki 104 maçı içerir.

Her maç için:

- Aşama
- Ev sahibi
- Deplasman
- Skor
- Kazanan
- xG değerleri
- Karar biçimi

### En Olası Grup Tabloları

```text
outputs/most_likely_group_standings.csv
```

Merkezi senaryodaki 12 grup tablosunu içerir.

### Maç Skor Dağılımları

```text
outputs/most_likely_match_score_distributions.csv
```

Her maç için:

- Merkezi skor
- xG
- Kazanma / beraberlik / kaybetme olasılıkları
- En olası 5 skor

### Takım Güç Sıralaması

```text
outputs/team_power_rankings.csv
```

Takımları model gücüne göre sıralar.

---

## Görsel Çıktılar

Grafikler şu klasörde üretilir:

```text
outputs/figures/
```

Üretilen görseller:

```text
champion_probabilities_top15.png
team_power_top15.png
stage_reach_probabilities_top10.png
final_scoreline_distribution.png
most_likely_knockout_path.png
```

Bu görseller GitHub README, LinkedIn postu veya sunumlarda kullanılabilir.

---

## Raporlar

```text
reports/data_quality_report.md
reports/eafc25_feature_report.md
reports/final_model_report.md
reports/simulation_report.md
reports/next_phase_plan.md
```

Raporların amacı:

- Veri kalitesini özetlemek
- EA FC feature üretimini açıklamak
- Model yapısını anlatmak
- Simülasyon sonuçlarını belgelemek
- Dashboard / GitHub / LinkedIn sonrası planı tutmak

---

## Kurulum

Python 3.10+ önerilir.

```bash
git clone https://github.com/cemyildizcy/wc2026-ai-simulator.git
cd wc2026-ai-simulator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows Git Bash için de aynı komutlar kullanılabilir.

---

## Final Pipeline Nasıl Çalıştırılır?

Tüm final model sürecini çalıştırmak için:

```bash
python src/run_final_pipeline.py
```

Bu komut sırasıyla şunları yapar:

1. EA FC 25 oyuncu verilerinden takım feature'larını yeniden üretir.
2. Final zenginleştirilmiş takım veri setini günceller.
3. Monte Carlo simülasyonunu çalıştırır.
4. En olası bracket yolunu üretir.
5. Maç skor dağılımlarını hesaplar.
6. Grafik çıktılarını oluşturur.

Başarılı çalıştırma sonrası şu klasörler güncellenir:

```text
outputs/
outputs/figures/
reports/
```

---

## Önemli Sınırlamalar

Bu proje bilinçli olarak bazı basitleştirmeler içerir:

1. FIFA'nın tam 3. sıra eşleşme kombinasyon tablosu kamuya açık olmadığı için, model belgelenmiş uyumlu bir fallback kullanır.
2. Grup eşitlik bozma kuralları FIFA'nın tüm detaylarını birebir içermez. Puan, averaj, atılan gol ve takım gücü fallback'i kullanılır.
3. EA FC 25 reytingleri gerçek futbol gücü için bir proxy olarak kullanılır; birebir gerçek performans anlamına gelmez.
4. Sakatlıklar, cezalı oyuncular, maç içi taktik değişimler, hava durumu ve yorgunluk modele dahil değildir.
5. Poisson modeli gol sayılarını bağımsız varsayar. Gerçek futbolda maçın gidişatı bu dağılımı değiştirebilir.
6. StatsBomb verisi sınırlı sayıda Dünya Kupası edisyonundan gelir.
7. Sonuçlar feature ağırlıklarına ve veri kalitesine duyarlıdır.

Bu nedenle sonuçlar kesin tahmin olarak değil, **olasılık temelli model çıktısı** olarak okunmalıdır.

---

## Öğrenilenler

Bu projede kullanılan ana veri bilimi becerileri:

- Veri temizleme
- Feature engineering
- Çok kaynaklı veri birleştirme
- Olasılıksal modelleme
- Poisson dağılımı
- Monte Carlo simülasyonu
- Turnuva bracket simülasyonu
- Veri görselleştirme
- Streamlit dashboard geliştirme
- GitHub proje paketleme

---

## Teknolojiler

```text
Python
Pandas
NumPy
Matplotlib
Plotly
Streamlit
StatsBombPy
Git / GitHub
```

---

## Geliştiren

**Cem Yıldız**  
Matematik-Bilgisayar Bilimleri öğrencisi · Veri Bilimi / Yapay Zeka / Full-Stack

GitHub: [cemyildizcy](https://github.com/cemyildizcy)
