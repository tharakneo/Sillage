"""Align Google Trends and Reddit signals to a common weekly index per SKU.

Reads:  data/raw/{slug}_google.csv, data/raw/{slug}_reddit.csv
Writes: data/processed/{slug}_combined.csv

Output columns:
    week, sku,
    google_interest,                              # demand proxy (0-100)
    reddit_mentions, reddit_pos_mentions,         # buzz volume
    reddit_sentiment_sum, reddit_net_sentiment    # mood

Only the 10 SKUs that have Reddit data get a combined file. SKUs with Google
but no Reddit (e.g. Bleu de Chanel) still get a file with reddit_* = 0.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from sku_config import SKU_SLUGS

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# 3-year weekly spine, Monday-anchored (matches reddit merge + google pull)
WEEK_INDEX = pd.date_range("2023-01-01", "2025-12-31", freq="W-MON")

REDDIT_COLS = [
    "reddit_mentions",
    "reddit_pos_mentions",
    "reddit_sentiment_sum",
    "reddit_net_sentiment",
]

TIKTOK_COLS = ["tiktok_videos", "tiktok_views"]


def _load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["week"])
    df["week"] = pd.to_datetime(df["week"])
    return df


def align_sku(sku: str, slug: str) -> pd.DataFrame:
    spine = pd.DataFrame({"week": WEEK_INDEX})

    google = _load_csv(RAW_DIR / f"{slug}_google.csv")
    reddit = _load_csv(RAW_DIR / f"{slug}_reddit.csv")

    merged = spine.copy()

    if google is not None:
        # Google weeks are Sunday-anchored; snap each to the Monday of its week (spine anchor)
        google = google.copy()
        google["week"] = google["week"] - pd.to_timedelta(google["week"].dt.weekday, unit="D")
        merged = merged.merge(google[["week", "google_interest"]], on="week", how="left")
    else:
        merged["google_interest"] = float("nan")

    if reddit is not None:
        merged = merged.merge(reddit, on="week", how="left")
        for c in ("reddit_mentions", "reddit_pos_mentions"):
            merged[c] = merged[c].fillna(0).astype(int)
        for c in ("reddit_sentiment_sum", "reddit_net_sentiment"):
            merged[c] = merged[c].fillna(0.0)
    else:
        for c in REDDIT_COLS:
            merged[c] = 0

    # TikTok (only the 2 backtest SKUs have it; others get 0)
    tiktok = _load_csv(RAW_DIR / f"{slug}_tiktok.csv")
    if tiktok is not None:
        merged = merged.merge(tiktok[["week", "tiktok_videos", "tiktok_views"]],
                              on="week", how="left")
        for c in TIKTOK_COLS:
            merged[c] = merged[c].fillna(0).astype(int)
    else:
        for c in TIKTOK_COLS:
            merged[c] = 0

    merged.insert(1, "sku", sku)
    return merged[["week", "sku", "google_interest"] + REDDIT_COLS + TIKTOK_COLS]


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for sku, slug in SKU_SLUGS.items():
        df = align_sku(sku, slug)
        out = PROCESSED_DIR / f"{slug}_combined.csv"
        df.to_csv(out, index=False)
        has_reddit = df["reddit_mentions"].sum() > 0
        flag = "" if has_reddit else "  (no reddit)"
        print(f"  aligned › {sku:<32} ({len(df)} weeks){flag}")

    print("Done — all SKUs aligned → data/processed/")


if __name__ == "__main__":
    main()
