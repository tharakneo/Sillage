"""Extract intrinsic product attributes for our SKUs from the Fragrantica dump.

Leakage safe features only: notes, accords, year, gender (all fixed at the
moment a fragrance exists). NO ratings (those accumulate over time and would
leak future popularity into a launch forecast).

Derives a `season` prior from the main accords: sweet/warm/gourmand accords
skew cold weather; fresh/citrus/aquatic skew warm weather.

Source:  data/raw/fra_cleaned.csv  (latin-1, ';'-delimited)
Output:  data/processed/fragrantica.csv

Run: python src/build_fragrantica.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "fra_cleaned.csv"
OUT = ROOT / "data" / "processed" / "fragrantica.csv"

# Explicit SKU -> Fragrantica slug map (hand verified to pick the right variant).
# SKUs absent from this dump (Glossier You, Secretions Magnifiques) are omitted.
SKU_SLUG = {
    "Bianco Latte": "bianco-latte",
    "Dior Sauvage": "sauvage-eau-de-parfum",
    "YSL MYSLF": "myslf-eau-de-parfum",
    "Miss Dior Parfum": "miss-dior-parfum-2024",
    "Dior Homme Parfum": "dior-homme-parfum",
    "Le Male Elixir": "le-male-elixir",
    "YSL Libre": "libre",
    "Phlur Vanilla Skin": "vanilla-skin",
    "Louis Vuitton Imagination": "imagination",
    "Stronger With You Intensely": "emporio-armani-stronger-with-you-intensely",
    "Baccarat Rouge 540": "baccarat-rouge-540",
    "Azzaro Most Wanted Parfum": "the-most-wanted-parfum",
    "Bleu de Chanel": "bleu-de-chanel",
}

# Accord -> season skew. Cold weather vs warm weather demand drivers.
COLD_ACCORDS = {"vanilla", "sweet", "caramel", "amber", "warm spicy", "cinnamon",
                "balsamic", "honey", "tobacco", "leather", "oud", "gourmand",
                "powdery", "almond", "chocolate", "coffee"}
WARM_ACCORDS = {"citrus", "fresh", "aquatic", "fresh spicy", "green", "marine",
                "fruity", "floral", "white floral", "aromatic", "ozonic", "herbal"}


def derive_season(accords: list[str]) -> str:
    cold = sum(1 for a in accords if a in COLD_ACCORDS)
    warm = sum(1 for a in accords if a in WARM_ACCORDS)
    if cold > warm:
        return "cold-weather"
    if warm > cold:
        return "warm-weather"
    return "all-season"


def main() -> None:
    df = pd.read_csv(RAW, encoding="latin-1", sep=";", on_bad_lines="skip")
    df["slug"] = df["Perfume"].astype(str).str.lower()

    rows = []
    for sku, slug in SKU_SLUG.items():
        match = df[df["slug"] == slug]
        if match.empty:
            print(f"  MISSING: {sku} ({slug})")
            continue
        r = match.iloc[0]
        accords = [str(r[f"mainaccord{i}"]).strip().lower()
                   for i in range(1, 6) if pd.notna(r.get(f"mainaccord{i}"))]
        accords = [a for a in accords if a and a != "nan"]
        rows.append({
            "sku": sku,
            "brand": r.get("Brand"),
            "year": r.get("Year"),
            "gender": r.get("Gender"),
            "top_notes": r.get("Top"),
            "middle_notes": r.get("Middle"),
            "base_notes": r.get("Base"),
            "accords": ", ".join(accords),
            "season": derive_season(accords),
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"\nWrote {len(out)} SKUs → {OUT.relative_to(ROOT)}")
    print(out[["sku", "accords", "season"]].to_string(index=False))


if __name__ == "__main__":
    main()
