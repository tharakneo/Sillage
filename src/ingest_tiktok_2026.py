"""TikTok scraper for the 2026 live-demo releases (Apify, caption-filtered).

Casts a net with specific hashtags, then keeps only videos whose CAPTION
mentions the product (many creators name the perfume in text, not tags).
Lean by design: few specific hashtags, low cap, to keep Apify credits minimal.

Requires:  export APIFY_TOKEN="..."
Usage:     python src/ingest_tiktok_2026.py

Output:    data/raw/{slug}_tiktok.csv   (weekly posting velocity + engagement)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

ACTOR_ID = "clockworks/tiktok-scraper"
RESULTS_PER_HASHTAG = 500          # lean cap (new products, low volume)
WEEK_SPINE = pd.date_range("2025-06-01", "2026-06-30", freq="W-MON")

# slug -> (hashtags to scrape, caption keywords to keep)
TARGETS = {
    "armani_power_of_you": (
        ["powerofyou", "armanipowerofyou"],
        ["power of you"],
    ),
    "valentino_purple_melancholia": (
        ["purplemelancholia"],
        ["purple melancholia", "born in roma"],
    ),
}


def scrape(client, hashtags: list[str]) -> list[dict]:
    run_input = {
        "hashtags": hashtags,
        "resultsPerPage": RESULTS_PER_HASHTAG,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
    }
    print(f"  scraping {hashtags} (cap {RESULTS_PER_HASHTAG}/tag)...", flush=True)
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    items = list(client.dataset(ds).iterate_items())
    print(f"    pulled {len(items)} raw videos", flush=True)
    return items


def to_rows(items: list[dict]) -> pd.DataFrame:
    rows = []
    for it in items:
        rows.append({
            "created": it.get("createTimeISO") or it.get("createTime"),
            "views": it.get("playCount", 0) or 0,
            "likes": it.get("diggCount", 0) or 0,
            "comments": it.get("commentCount", 0) or 0,
            "shares": it.get("shareCount", 0) or 0,
            "url": it.get("webVideoUrl", ""),
            "caption": (it.get("text", "") or ""),
        })
    return pd.DataFrame(rows)


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["created"] = pd.to_datetime(df["created"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.dropna(subset=["created"])
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

    for slug, (hashtags, keywords) in TARGETS.items():
        print(f"\n{slug}")
        items = scrape(client, hashtags)
        raw = to_rows(items)
        if raw.empty:
            print("  no videos returned — skipping")
            continue

        # caption filter: keep videos that actually name the product
        cap = raw["caption"].str.lower()
        mask = pd.Series(False, index=raw.index)
        for kw in keywords:
            mask |= cap.str.contains(kw, na=False, regex=False)
        kept = raw[mask]
        print(f"    caption-matched {len(kept)} of {len(raw)} videos "
              f"(keywords: {keywords})", flush=True)
        if kept.empty:
            print("  nothing matched the caption keywords — skipping")
            continue

        weekly = to_weekly(kept)
        weekly.to_csv(RAW_DIR / f"{slug}_tiktok.csv", index=False)
        nz = weekly[weekly["tiktok_videos"] > 0]
        span = f"{nz['week'].min().date()} -> {nz['week'].max().date()}" if not nz.empty else "none"
        print(f"  weekly written. {len(nz)} active weeks | span {span} | "
              f"{int(weekly['tiktok_videos'].sum())} videos, "
              f"{int(weekly['tiktok_views'].sum()):,} views")

    print("\nDone.")


if __name__ == "__main__":
    main()
