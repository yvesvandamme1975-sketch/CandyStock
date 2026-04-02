"""
text_cleaner.py
───────────────
Display-time text normalization for article names.
Raw data from Excel is NEVER modified — corrections are applied only when
rendering to the preview canvas or generating PDF output.

Two passes:
  1. Whitespace normalization — collapse multiple spaces, trim, and insert a
     space at letter→digit boundaries (e.g. "bouteille1x" → "bouteille 1x").
  2. Brand spell correction — regex word-boundary replacement for known
     misspellings of popular brands.
"""

import re

# ── Brand corrections ────────────────────────────────────────────────────────
# Key   : lowercase misspelling / common variant
# Value : canonical brand spelling
# CandyStock: sweets, chocolates, drinks — add corrections as needed
_CORRECTIONS = {
    # Coca-Cola
    "cocacola":         "Coca-Cola",
    "coca cola":        "Coca-Cola",
    "coka cola":        "Coca-Cola",
    "coka-cola":        "Coca-Cola",
    # Haribo
    "harribo":          "Haribo",
    # Kinder
    "kinder":           "Kinder",
    # Ferrero
    "ferero":           "Ferrero",
    "ferrero rocher":   "Ferrero Rocher",
    # Nutella
    "nutela":           "Nutella",
    # Mars
    "marss":            "Mars",
    # Snickers
    "snikers":          "Snickers",
    "sniker":           "Snickers",
    # Twix
    "twiks":            "Twix",
    # M&M's
    "m&m":              "M&M's",
    "m & m":            "M&M's",
    # Milka
    "millka":           "Milka",
    # Côte d'Or
    "cote d'or":        "Côte d'Or",
    "cote dor":         "Côte d'Or",
    # Toblerone
    "tobleronee":       "Toblerone",
    # Mentos
    "mentoss":          "Mentos",
    # Schweppes
    "schwepps":         "Schweppes",
    "schweps":          "Schweppes",
    "shweppes":         "Schweppes",
    # Red Bull
    "redbull":          "Red Bull",
    "red-bull":         "Red Bull",
    "red bul":          "Red Bull",
    "redbul":           "Red Bull",
}

# Pre-compile regex patterns with word boundaries, longest pattern first
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'(?<!\w)' + re.escape(wrong) + r'(?!\w)', re.IGNORECASE), right)
    for wrong, right in sorted(_CORRECTIONS.items(), key=lambda kv: len(kv[0]), reverse=True)
]


def clean_article(text: str) -> str:
    """
    Normalize and spell-correct an article name for display/print.
    Source data is never modified — call this only at render time.
    """
    if not text:
        return text

    # Pass 1: whitespace normalization
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)                  # collapse runs of spaces
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)  # letter→digit boundary

    # Pass 2: brand corrections
    for pattern, right in _PATTERNS:
        text = pattern.sub(right, text)

    return text
