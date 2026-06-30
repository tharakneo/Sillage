# Sillage

*Sillage* — **S**ocial **I**ntelligence for **L**ive **L**uxury **A**llocation and
**G**rowth **E**stimation. Forecasts **fragrance demand from social signals**, so a
supply-chain planner can act on a demand shift *before* it shows up in sales.

You can also use it to track how a fragrance is doing over the years — its buzz,
its sentiment, what people think of it — and compare SKUs head-to-head with the
numbers to back it up.

<img src="notebooks/images/sauvage.jpg" width="420">

The core idea: a product's demand is driven by **seasonality** (learned across a
portfolio), its **intrinsic profile** (notes/accords → season), and **live social
buzz** (Reddit, TikTok). Google search interest is used as a demand proxy.

---

## Case studies

One pooled model, trained across the portfolio, applied to three different demand
archetypes:

| SKU | Archetype | What the model does | MAE |
|-----|-----------|---------------------|-----|
| **Bianco Latte** | New viral launch | No sales history → forecasts the surge from social signal | 12.3 |
| **Stronger With You Intensely** | Seasonal gifting | Anticipates the winter spike from learned seasonality | 9.2 |
| **Dior Homme Parfum** | Reformulation event | Catches the Q1 surge and the Q2 reversion to baseline | 4.3 |

*(MAE on the 0–100 Google-interest scale.)*

---

## Signals

| Source | Signal | Role |
|--------|--------|------|
| Google Trends | search interest | demand proxy (forecast target) |
| Reddit (r/fragrance census) | mentions + VADER sentiment | live buzz; sentiment can lead, volume confirms |
| TikTok (Apify) | posting velocity | discovery signal (recency-biased — recent only) |
| Fragrantica | notes / accords → derived season | static product prior (known at launch, no leakage) |

---

## Pipeline

```
ingest_google.py  ─┐
ingest_reddit.py  ─┼─►  align.py  ─►  data/processed/{sku}_combined.csv
ingest_tiktok.py  ─┤                          │
build_fragrantica.py ┘                        ▼
                                    notebooks/backtest.ipynb
                                  (features → pooled model → forecast)
```

| Script | What it does |
|--------|--------------|
| `src/sku_config.py` | SKU registry — **edit this for your own perfumes** |
| `src/ingest_google.py` | Pull weekly Google Trends interest (pytrends) |
| `src/ingest_reddit.py` | Census-scrape r/fragrance + VADER sentiment (Arctic Shift, no auth) |
| `src/merge_reddit.py` | Merge distributed Reddit chunks into per-SKU CSVs |
| `src/ingest_tiktok.py` | Pull TikTok hashtag posting velocity (Apify) |
| `src/build_fragrantica.py` | Extract notes/accords, derive season prior |
| `src/align.py` | Merge all signals onto one weekly panel per SKU |

The model (feature engineering, training, forecasting, charts) lives in
`notebooks/backtest.ipynb`.

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

TikTok ingestion needs an Apify token:

```bash
export APIFY_TOKEN="apify_api_..."
```

---

## Run it for your own SKUs

1. **Pick your fragrances** — edit `SKU_ALIASES` and `SKU_SLUGS` in `src/sku_config.py`.
2. **Pull the signals:**
   ```bash
   python src/ingest_google.py
   ./run_reddit_distributed.sh 2023 2025      # distributed census scrape + merge
   python src/ingest_tiktok.py                # optional (needs APIFY_TOKEN)
   python src/build_fragrantica.py            # needs data/raw/fra_cleaned.csv
   ```
3. **Align:**
   ```bash
   python src/align.py
   ```
4. **Forecast** — open `notebooks/backtest.ipynb` and run the cells.

---


## Notes & honest limitations

- **Google interest is a demand *proxy*, not sales.** Search and purchase correlate
  in high-consideration categories like fragrance; with real POS data the same
  pipeline holds with the target swapped. (ref: Predicting the Present with Google Trends
Hyunyoung Choi, Hal Varian)
- **No ratings used** — Fragrantica ratings accumulate over time and would leak
  future popularity into a launch forecast.
- **TikTok hashtag data is recency-biased** — sparse/unreliable for older years,
  dense only recently.
- **Buzz ≠ purchase intent** — the model over-predicts notoriety products like
  Sécrétions Magnifiques (added specifically as a polarizing control), where people
  discuss but don't buy. Real sales data would resolve this.

---

## Layout

```
sillage/
├── src/                  # ingestion + alignment pipeline
├── notebooks/            # backtest.ipynb — model + forecasts
├── data/                 # (gitignored) raw + processed signals
├── run_reddit_distributed.sh
├── requirements.txt
└── README.md
```
