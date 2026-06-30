"""Reddit mention + sentiment scraper for Project Sillage via Arctic Shift.

Full census of r/fragrance posts and comments, with VADER sentiment scoring.
Designed to run DISTRIBUTED, each process handles a date chunk and writes a
partial file. merge_reddit.py combines partials into final per-SKU CSVs.

For each SKU-matching post/comment we record:
  - mention count          (raw volume)
  - sentiment sum          (sum of VADER compound scores → net buzz)
  - positive mention count (compound > 0.05 → clean demand signal)

Usage (single chunk):
  python src/ingest_reddit.py --start 2024-01-01 --end 2024-06-30 --tag q1q2_2024

Run several in parallel (see run_reddit_distributed.sh).

Partial output: data/raw/_partial/{tag}.csv  (sku, week, mentions, sentiment_sum, pos_mentions)
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from sku_config import SKU_ALIASES, SKU_SLUGS
import re

RAW_DIR     = Path(__file__).resolve().parent.parent / "data" / "raw"
PARTIAL_DIR = RAW_DIR / "_partial"
WEEK_SPINE  = pd.date_range("2023-01-01", "2025-12-31", freq="W-MON")

BASE    = "https://arctic-shift.photon-reddit.com/api"
HEADERS = {"User-Agent": "sillage-research/0.1"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

ANALYZER = SentimentIntensityAnalyzer()
POS_THRESHOLD = 0.05  # VADER compound above this = positive mention

# Reddit SKUs — subset selected for community signal analysis
REDDIT_SKUS = [
    "Phlur Vanilla Skin",
    "Bianco Latte",
    "YSL MYSLF",
    "Louis Vuitton Imagination",
    "Stronger With You Intensely",
    "Glossier You",
    "Dior Sauvage",
    "Miss Dior Parfum",
    "YSL Libre",
    "Secretions Magnifiques",
    "Dior Homme Parfum",
]


# ── One compiled regex per SKU ───────────────────────────────────────────────

def _build_patterns() -> dict[str, re.Pattern]:
    patterns = {}
    for sku in REDDIT_SKUS:
        aliases = SKU_ALIASES[sku]
        escaped = [re.escape(a.lower()) for a in aliases]
        patterns[sku] = re.compile(r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)")
    return patterns

PATTERNS = _build_patterns()


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _fetch(endpoint: str, params: dict, retries: int = 4) -> list[dict]:
    url = f"{BASE}/{endpoint}/search"
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                print(f"    rate limited — sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return []
            return r.json().get("data") or []
        except Exception:
            time.sleep(5 * (attempt + 1))
    return []


def _fetch_all(endpoint: str, after: str, before: str) -> list[dict]:
    items, cur = [], after
    while True:
        batch = _fetch(endpoint, {
            "subreddit": "fragrance",
            "after": cur, "before": before,
            "limit": 100, "sort": "asc",
        })
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        last_ts = batch[-1]["created_utc"]
        cur = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        time.sleep(0.15)
    return items


# ── Scoring ──────────────────────────────────────────────────────────────────

def _score_text(text: str, accum: dict) -> None:
    """Match all SKUs in text; if any match, score sentiment once and attribute it."""
    t = text.lower()
    matched = {sku: len(pat.findall(t)) for sku, pat in PATTERNS.items()}
    matched = {sku: n for sku, n in matched.items() if n}
    if not matched:
        return
    compound = ANALYZER.polarity_scores(text)["compound"]
    is_pos = compound > POS_THRESHOLD
    week = accum["_week"]
    for sku, n in matched.items():
        accum[sku][week]["mentions"]     += n
        accum[sku][week]["sentiment_sum"] += compound * n
        if is_pos:
            accum[sku][week]["pos_mentions"] += n


def _new_accum() -> dict:
    return {sku: defaultdict(lambda: {"mentions": 0, "sentiment_sum": 0.0, "pos_mentions": 0})
            for sku in REDDIT_SKUS}


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--end",   required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--tag",   required=True, help="label for this chunk's partial file")
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end   = datetime.strptime(args.end,   "%Y-%m-%d").date()
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)

    accum = _new_accum()
    total_days = (end - start).days + 1
    day = start

    while day <= end:
        after  = day.strftime("%Y-%m-%d")
        before = (day + timedelta(days=1)).strftime("%Y-%m-%d")
        accum["_week"] = str(pd.Timestamp(day).to_period("W-MON").start_time.date())

        posts    = _fetch_all("posts",    after, before)
        comments = _fetch_all("comments", after, before)

        for post in posts:
            _score_text((post.get("title") or "") + " " + (post.get("selftext") or ""), accum)
        for comment in comments:
            _score_text(comment.get("body") or "", accum)

        days_done = (day - start).days + 1
        if days_done % 7 == 0 or day == end:
            pct = days_done / total_days * 100
            print(f"[{args.tag}] [{pct:5.1f}%] {accum['_week']}  "
                  f"posts={len(posts)} comments={len(comments)}", flush=True)

        day += timedelta(days=1)
        time.sleep(0.2)

    # ── flatten to long rows and write partial ────────────────────────────────
    rows = []
    for sku in REDDIT_SKUS:
        for week, vals in accum[sku].items():
            rows.append({
                "sku": sku, "week": week,
                "mentions": vals["mentions"],
                "sentiment_sum": round(vals["sentiment_sum"], 4),
                "pos_mentions": vals["pos_mentions"],
            })
    out = PARTIAL_DIR / f"{args.tag}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{args.tag}] wrote {len(rows)} rows → {out}", flush=True)


if __name__ == "__main__":
    main()
