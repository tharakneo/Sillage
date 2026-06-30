# Sillage

*Sillage*. **S**ocial **I**ntelligence for **L**ive **L**uxury **A**llocation and
**G**rowth **E**stimation. Forecasts **fragrance demand from social signals**, so a
supply-chain planner can act on a demand shift *before* it shows up in sales.

You can also use it to track how a fragrance is doing over the years (its buzz,
its sentiment, what people think of it) and compare SKUs head-to-head with the
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
| **Bianco Latte** | New viral launch | No sales history, so it forecasts the surge from social signal | 12.3 |
| **Stronger With You Intensely** | Seasonal gifting | Anticipates the winter spike from learned seasonality | 9.2 |
| **Dior Homme Parfum** | Reformulation event | Catches the Q1 surge and the Q2 reversion to baseline | 4.3 |
| **Armani Power of You** | **2026 live launch** | Forecasts a brand-new product the model *never saw*, from early social signal | 13.6 |

*(MAE on the 0 to 100 Google-interest scale.)*

The first three are **backtests** (hold out the event window, train on everything
else, forecast the held-out window). Armani is the **live application**: a 2026
release that is *not in the training set at all*, the real test of forecasting a
product with zero history. Backtests prove the method; the live launch shows it
working forward. Notebooks: `backtest.ipynb` and `armani_power_of_you_2026_forecast.ipynb`.

This is **V1**, built on free/public proxies. The MAE is already in a usable range and
would tighten substantially with: **real POS sales** (replacing the Google proxy
target), **richer Reddit history** (deeper census, more subreddits), and **fuller
TikTok scraping** as a model feature (computationally heavier, but it's the earliest
leading signal). The architecture is built to absorb these without changes.

---

## Signals

| Source | Signal | Role |
|--------|--------|------|
| Google Trends | search interest | demand proxy (forecast target) |
| Reddit (r/fragrance census) | mentions + VADER sentiment | live buzz; sentiment can lead, volume confirms |
| TikTok (Apify) | posting velocity | discovery signal (recency-biased, recent only) |
| Fragrantica | notes / accords → derived season | static product prior (known at launch, no leakage) |

---

## Method

- **Target:** weekly Google Trends interest (demand proxy).
- **Features:** lagged Reddit signals (*t−1…t−4*), lagged demand, calendar, and a
  static season prior from Fragrantica accords, all leakage safe. No ratings.
- **Model:** pooled `GradientBoostingRegressor` trained across all SKUs at once, so it
  can forecast a new SKU with no history of its own.
- **Validation:** hold out the event window (or the entire 2026 SKU for Armani), train
  on the rest, forecast the held out data.

See `notebooks/backtest.ipynb` for the full feature set, hyperparameters, and rationale.

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
| `src/sku_config.py` | SKU registry (**edit this for your own perfumes**) |
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

1. **Pick your fragrances.** Edit `SKU_ALIASES` and `SKU_SLUGS` in `src/sku_config.py`.
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
4. **Forecast.** Open `notebooks/backtest.ipynb` and run the cells.

---


## Notes & honest limitations

- **Google interest is a demand *proxy*, not sales.** Search and purchase correlate
  in high-consideration categories like fragrance; with real POS data the same
  pipeline holds with the target swapped. (ref: Predicting the Present with Google Trends
Hyunyoung Choi, Hal Varian)
- **No ratings used.** Fragrantica ratings accumulate over time and would leak
  future popularity into a launch forecast.
- **TikTok hashtag data is recency-biased.** Sparse/unreliable for older years,
  dense only recently. It's shown as a *leading indicator* in the cascade charts but
  is **not yet a model feature** (the historical training SKUs lack reliable TikTok
  history); backfilling it across the portfolio is the next step.
- **Buzz ≠ purchase intent.** The model over-predicts notoriety products like
  Sécrétions Magnifiques (added specifically as a polarizing control), where people
  discuss but don't buy. Real sales data would resolve this.

---

## Layout

```
sillage/
├── src/                  # ingestion + alignment pipeline
├── notebooks/
│   ├── backtest.ipynb                          # 3 backtest archetypes + supply plan
│   └── armani_power_of_you_2026_forecast.ipynb # live 2026 launch forecast + S&OP
├── data/                 # (gitignored) raw + processed signals
├── run_reddit_distributed.sh
├── requirements.txt
└── README.md
```
