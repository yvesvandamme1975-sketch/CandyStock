from src.text_cleaner import clean_article


# ── Whitespace normalization ──────────────────────────────────────────────────

def test_trims_leading_trailing():
    assert clean_article("  Red Bull  ") == "Red Bull"

def test_collapses_multiple_spaces():
    assert clean_article("Red  Bull  original") == "Red Bull original"

def test_letter_digit_boundary():
    assert clean_article("bouteille1x 25cl") == "bouteille 1x 25cl"

def test_no_change_needed():
    assert clean_article("Red Bull 1x 25cl") == "Red Bull 1x 25cl"

def test_empty_string():
    assert clean_article("") == ""

def test_none_passthrough():
    assert clean_article(None) is None  # type: ignore


# ── Brand corrections ─────────────────────────────────────────────────────────

def test_red_bul():
    assert clean_article("Red Bul original 24x25cl") == "Red Bull original 24x 25cl"

def test_redbull_nospace():
    assert clean_article("Redbull energy") == "Red Bull energy"

def test_coca_cola_nospace():
    assert clean_article("Coca Cola 33cl") == "Coca-Cola 33cl"

def test_heineken_typo():
    assert clean_article("Heiniken 24x33cl") == "Heineken 24x 33cl"

def test_hoegaarden_typo():
    assert clean_article("Hoegarden witbier") == "Hoegaarden witbier"

def test_schweppes_typo():
    assert clean_article("Schwepps tonic") == "Schweppes tonic"

def test_case_insensitive():
    assert clean_article("red bul zero") == "Red Bull zero"

def test_no_false_positive():
    # "Stella Artois" already correct — should stay unchanged
    assert clean_article("Stella Artois 33cl") == "Stella Artois 33cl"
