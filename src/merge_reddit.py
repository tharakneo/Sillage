"""Merge distributed Reddit partial files into final per-SKU CSVs.

Reads every data/raw/_partial/*.csv produced by parallel ingest_reddit.py runs,
sums them by (sku, week), and writes data/raw/{slug}_reddit.csv with columns:

    week, reddit_mentions, reddit_sentiment_sum, reddit_pos_mentions, reddit_net_sentiment

reddit_net_sentiment = sentiment_sum / mentions  (avg sentiment per mention, -1..+1)

Run after all chunks finish: python src/merge_reddit.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from sku_config import SKU_ALIASES, SKU_SLUGS

RAW_DIR     = Path(__file__).resolve().parent.parent / "data" / "raw"
PARTIAL_DIR = RAW_DIR / "_partial"
WEEK_SPINE  = pd.date_range("2023-01-01", "2025-12-31", freq="W-MON")


def main() -> None:
    partials = sorted(PARTIAL_DIR.glob("*.csv"))
    if not partials:
        print("No partial files found in", PARTIAL_DIR)
        return
    print(f"Merging {len(partials)} partial files: {[p.name for p in partials]}")

    combined = pd.concat([pd.read_csv(p) for p in partials], ignore_index=True)

    # normalize week: snap each date to its Monday (same anchor as spine W-MON)
    combined["week"] = pd.to_datetime(combined["week"], errors="coerce")
    combined = combined.dropna(subset=["week"])
    combined["week"] = (
        combined["week"] - pd.to_timedelta(combined["week"].dt.weekday, unit="D")
    ).dt.strftime("%Y-%m-%d")

    # sum overlapping (sku, week) across chunks
    agg = combined.groupby(["sku", "week"], as_index=False).agg(
        mentions=("mentions", "sum"),
        sentiment_sum=("sentiment_sum", "sum"),
        pos_mentions=("pos_mentions", "sum"),
    )

    spine = pd.DataFrame({"week": WEEK_SPINE})
    spine["week"] = spine["week"].dt.date.astype(str)

    for sku in SKU_ALIASES:
        slug = SKU_SLUGS[sku]
        sub = agg[agg["sku"] == sku]
        merged = spine.merge(sub, on="week", how="left")
        merged["reddit_mentions"]      = merged["mentions"].fillna(0).astype(int)
        merged["reddit_sentiment_sum"] = merged["sentiment_sum"].fillna(0).round(4)
        merged["reddit_pos_mentions"]  = merged["pos_mentions"].fillna(0).astype(int)
        # avg sentiment per mention; 0 when no mentions
        merged["reddit_net_sentiment"] = (
            merged["reddit_sentiment_sum"] / merged["reddit_mentions"].replace(0, pd.NA)
        ).fillna(0).round(4)
        merged["week"] = pd.to_datetime(merged["week"])

        out = RAW_DIR / f"{slug}_reddit.csv"
        merged[["week", "reddit_mentions", "reddit_sentiment_sum",
                "reddit_pos_mentions", "reddit_net_sentiment"]].to_csv(out, index=False)

    print(f"Done — {len(SKU_ALIASES)} per-SKU CSVs written.")

    # summary
    totals = agg.groupby("sku").agg(
        mentions=("mentions", "sum"),
        pos=("pos_mentions", "sum"),
        sent=("sentiment_sum", "sum"),
    )
    totals["net_per_mention"] = (totals["sent"] / totals["mentions"]).round(3)
    totals["pos_pct"] = (totals["pos"] / totals["mentions"] * 100).round(1)
    totals = totals.sort_values("mentions", ascending=False)
    print("\nSKU              mentions   pos%   net_sentiment")
    for sku, r in totals.iterrows():
        print(f"  {sku:<42} {int(r['mentions']):>6}  {r['pos_pct']:>5}%  {r['net_per_mention']:>6}")


if __name__ == "__main__":
    main()
