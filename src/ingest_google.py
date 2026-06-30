"""Pull Google Trends weekly interest for each SKU, Q1 2025.

One file per SKU: data/raw/{slug}_google.csv
Columns: week (YYYY-MM-DD Monday), google_interest (0-100 index)

Pulls the primary alias only,  pytrends normalises interest across batches,
but a single keyword pull keeps the scale anchored to that term, which is
what we need for per-SKU comparison.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from pytrends.request import TrendReq

from sku_config import GEO, SKU_ALIASES, SKU_SLUGS, TIMEFRAME

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch_sku(pytrends: TrendReq, sku: str, aliases: list[str]) -> pd.DataFrame:
    """Pull interest-over-time for the primary alias of a SKU.

    Uses only the first alias as the query term so every pull is on a
    consistent 0-100 scale anchored to that single keyword.
    """
    term = aliases[0]
    pytrends.build_payload([term], timeframe=TIMEFRAME, geo=GEO, gprop="")
    raw = pytrends.interest_over_time()
    if raw.empty:
        return pd.DataFrame(columns=["week", "google_interest"])
    raw = raw.drop(columns=["isPartial"], errors="ignore").reset_index()
    raw = raw.rename(columns={"date": "week", term: "google_interest"})
    raw["week"] = pd.to_datetime(raw["week"])
    return raw[["week", "google_interest"]]


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pytrends = TrendReq(hl="en-US", tz=360)

    for sku, aliases in SKU_ALIASES.items():
        slug = SKU_SLUGS[sku]
        print(f"  google › {sku} ({aliases[0]}) …", end=" ", flush=True)
        try:
            df = fetch_sku(pytrends, sku, aliases)
            out = RAW_DIR / f"{slug}_google.csv"
            df.to_csv(out, index=False)
            print(f"{len(df)} weeks")
        except Exception as exc:
            print(f"ERROR: {exc}")
        time.sleep(10)

    print("Done — Google Trends pull complete.")


if __name__ == "__main__":
    main()
