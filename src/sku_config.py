"""Central SKU registry shared by all ingest and align scripts."""
from __future__ import annotations

# Full 2023–2025 pull
TIMEFRAME = "2023-01-01 2025-12-31"
GEO = "US"

SKU_ALIASES: dict[str, list[str]] = {
    "Bianco Latte": ["bianco latte", "bianco latte giardini di toscana", "giardini di toscana bianco latte"],
    "Dior Sauvage": ["dior sauvage", "sauvage", "sauvage dior"],
    "YSL MYSLF": ["myslf", "myself ysl", "ysl myslf"],
    "Miss Dior Parfum": ["miss dior", "miss dior parfum", "mdp"],
    "Dior Homme Parfum": ["dior homme parfum", "dhp", "dior homme parfum reformulation"],
    "Le Male Elixir": ["le male elixir", "jpg elixir", "jpg le male elixir", "jean paul gaultier elixir"],
    "Glossier You": ["glossier you", "you glossier"],
    "YSL Libre": ["ysl libre", "libre", "libre edp", "libre ysl"],
    "Phlur Vanilla Skin": ["phlur vanilla skin", "vanilla skin phlur", "vanilla skin"],
    "Louis Vuitton Imagination": ["louis vuitton imagination", "lv imagination"],
    "Stronger With You Intensely": ["stronger with you intensely", "swy intensely", "armani stronger with you intensely"],
    "Phlur Missing Person": ["phlur missing person", "missing person phlur", "phlur mp"],
    "Baccarat Rouge 540": ["baccarat rouge 540", "baccarat rouge", "br540", "br 540", "rouge 540"],
    "Azzaro Most Wanted Parfum": ["azzaro most wanted", "most wanted azzaro", "azzaro most wanted parfum"],
    "Bleu de Chanel": ["bleu de chanel", "bdc"],
    "Secretions Magnifiques": ["secretions magnifiques", "secretions mag", "etat libre secretions"],
}

# 2026 fresh releases — the live forward-looking demo (separate window: 2026-01-01 → present).
# New products have no sales history; rising social signal is the only early demand read.
SKU_ALIASES_2026: dict[str, list[str]] = {
    "Le Beau Narcisse": [
        "le beau narcisse", "jean paul gaultier le beau narcisse", "jpg le beau narcisse",
    ],
    "Armani Power of You": [
        "power of you", "armani power of you", "emporio armani power of you",
    ],
    "Valentino Purple Melancholia": [
        "purple melancholia", "born in roma purple melancholia",
        "valentino purple melancholia", "valentino uomo born in roma purple melancholia",
    ],
}

SKU_SLUGS_2026: dict[str, str] = {
    "Le Beau Narcisse": "le_beau_narcisse",
    "Armani Power of You": "armani_power_of_you",
    "Valentino Purple Melancholia": "valentino_purple_melancholia",
}

TIMEFRAME_2026 = "2026-01-01 2026-06-30"

# TikTok hashtag equivalents
TIKTOK_HASHTAGS: dict[str, str] = {
    "Bianco Latte": "biancolatte",
    "Dior Sauvage": "diorsauvage",
    "YSL MYSLF": "myslf",
    "Miss Dior Parfum": "missdior",
    "Dior Homme Parfum": "diorhomme",
    "Le Male Elixir": "lemaleelixir",
    "Glossier You": "glossieryou",
    "YSL Libre": "ysllib re",
    "Phlur Vanilla Skin": "phlurvanillaskin",
    "Louis Vuitton Imagination": "lvimaginaton",
    "Stronger With You Intensely": "strongerwithyouintensely",
    "Phlur Missing Person": "phlurmissingperson",
    "Baccarat Rouge 540": "baccaratrouge540",
    "Azzaro Most Wanted Parfum": "azzaromostwanted",
    "Bleu de Chanel": "bleuedechanel",
    "Secretions Magnifiques": "secretionsmagnifiques",
}

# Safe filename slug per SKU
SKU_SLUGS: dict[str, str] = {
    "Bianco Latte": "bianco_latte",
    "Dior Sauvage": "dior_sauvage",
    "YSL MYSLF": "ysl_myslf",
    "Miss Dior Parfum": "miss_dior_parfum",
    "Dior Homme Parfum": "dior_homme_parfum",
    "Le Male Elixir": "le_male_elixir",
    "Glossier You": "glossier_you",
    "YSL Libre": "ysl_libre",
    "Phlur Vanilla Skin": "phlur_vanilla_skin",
    "Louis Vuitton Imagination": "louis_vuitton_imagination",
    "Stronger With You Intensely": "stronger_with_you_intensely",
    "Phlur Missing Person": "phlur_missing_person",
    "Baccarat Rouge 540": "baccarat_rouge_540",
    "Azzaro Most Wanted Parfum": "azzaro_most_wanted_parfum",
    "Bleu de Chanel": "bleu_de_chanel",
    "Secretions Magnifiques": "secretions_magnifiques",
}
