from __future__ import annotations

from app.utils.text import (
    apply_transliteration_map,
    compact_text,
    normalize_for_match,
    remove_fillers,
    tokenize,
)


def test_normalize_handles_spacing_noise_and_case() -> None:
    assert normalize_for_match("  Breast---Feeding   BASICS!! ") == "breast feeding basic"


def test_compact_text_recovers_missing_spaces() -> None:
    assert compact_text("Breastfeeding Basics") == "breastfeedingbasic"


def test_transliteration_mapping_normalizes_romanized_indic() -> None:
    assert apply_transliteration_map("tamizh thaippal basics") == "tamil breastfeeding basics"


def test_remove_fillers_cleans_voice_style_queries() -> None:
    assert remove_fillers("um please newborn care basics") == "newborn care basics"


def test_tokenize_removes_stopwords() -> None:
    assert tokenize("i need a course about breastfeeding in tamil") == ["breastfeeding", "tamil"]
