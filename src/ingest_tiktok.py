"""TikTok hashtag scraper via Apify (clockworks/tiktok-scraper).

Scoped to the two backtest SKUs only. For each hashtag we pull videos with
their post date + engagement, then bucket into a weekly time series:

    week, tiktok_videos, tiktok_views, tiktok_likes, tiktok_comments, tiktok_shares

We also save the raw top videos (by views) for narrative/presentation.

Requires:  export APIFY_TOKEN="..."
Usage:     python src/ingest_tiktok.py

Output:
    data/raw/{slug}_tiktok.csv        weekly time series
    data/raw/{slug}_tiktok_top.csv    top 20 videos by views (narrative)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

# Backtest SKUs + Dior Homme (reformulation) + 2026 live releases
TIKTOK_TARGETS = {
    "Bianco Latte": ("bianco_latte", "biancolatte"),
    "Stronger With You Intensely": ("stronger_with_you_intensely", "strongerwithyou"),
    "Dior Homme Parfum": ("dior_homme_parfum", "diorhomme"),
    "Armani Power of You": ("armani_power_of_you", "armanipowerofyou"),
    "Valentino Purple Melancholia": ("valentino_purple_melancholia", "purplemelancholia"),
}

ACTOR_ID = "clockworks/tiktok-scraper"
RESULTS_PER_HASHTAG = 1000  # cap; raise if coverage is thin
WEEK_SPINE = pd.date_range("2023-01-01", "2025-12-31", freq="W-MON")


def scrape_hashtag(client, hashtag: str) -> pd.DataFrame:
    run_input = {
        "hashtags": [hashtag],
        "resultsPerPage": RESULTS_PER_HASHTAG,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
    }
    print(f"  running actor for #{hashtag} (cap {RESULTS_PER_HASHTAG})...", flush=True)
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    # apify-client 3.x: .call() may return a Run object or a dict depending on version
    dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"    got {len(items)} videos", flush=True)

    rows = []
    for it in items:
        ts = it.get("createTimeISO") or it.get("createTime")
        rows.append({
            "created": ts,
            "views": it.get("playCount", 0) or 0,
            "likes": it.get("diggCount", 0) or 0,
            "comments": it.get("commentCount", 0) or 0,
            "shares": it.get("shareCount", 0) or 0,
            "url": it.get("webVideoUrl", ""),
            "desc": (it.get("text", "") or "")[:120],
        })
    return pd.DataFrame(rows)


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["created"] = pd.to_datetime(df["created"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.dropna(subset=["created"])
    # snap each video to the Monday of its week (matches google/reddit spine)
    df["week"] = df["created"] - pd.to_timedelta(df["created"].dt.weekday, unit="D")
    df["week"] = df["week"].dt.normalize()

    weekly = df.groupby("week").agg(
        tiktok_videos=("url", "count"),
        tiktok_views=("views", "sum"),
        tiktok_likes=("likes", "sum"),
        tiktok_comments=("comments", "sum"),
        tiktok_shares=("shares", "sum"),
    ).reset_index()

    spine = pd.DataFrame({"week": WEEK_SPINE})
    out = spine.merge(weekly, on="week", how="left").fillna(0)
    for c in out.columns:
        if c != "week":
            out[c] = out[c].astype(int)
    return out


def main() -> None:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print('ERROR: set APIFY_TOKEN env var first:\n  export APIFY_TOKEN="..."')
        sys.exit(1)

    from apify_client import ApifyClient
    client = ApifyClient(token)

    for sku, (slug, hashtag) in TIKTOK_TARGETS.items():
        out_path = RAW_DIR / f"{slug}_tiktok.csv"
        if out_path.exists():
            print(f"\n{sku}  (#{hashtag}) — already pulled, skipping (delete {out_path.name} to re-scrape)")
            continue
        print(f"\n{sku}  (#{hashtag})")
        raw = scrape_hashtag(client, hashtag)
        if raw.empty:
            print("  no videos returned — skipping")
            continue

        weekly = to_weekly(raw)
        weekly.to_csv(RAW_DIR / f"{slug}_tiktok.csv", index=False)

        raw_dated = raw.copy()
        raw_dated["created"] = pd.to_datetime(raw_dated["created"], errors="coerce", utc=True)
        top = raw_dated.sort_values("views", ascending=False).head(20)
        top.to_csv(RAW_DIR / f"{slug}_tiktok_top.csv", index=False)

        # coverage report — TikTok hashtag feeds are recency-biased, so check 2023
        nonzero = weekly[weekly["tiktok_videos"] > 0]
        if not nonzero.empty:
            span = f"{nonzero['week'].min().date()} -> {nonzero['week'].max().date()}"
            in_2023 = (nonzero["week"].dt.year == 2023).sum()
            print(f"  weekly written. coverage: {span} | weeks w/ data: {len(nonzero)} "
                  f"| 2023 weeks: {in_2023}")

    print("\nDone.")


if __name__ == "__main__":
    main()
