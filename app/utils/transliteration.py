"""Indic transliteration helpers and domain-specific romanization expansions."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.utils.text import normalize_for_match

DOMAIN_ROMANIZATION_MAP = {
    "garbhavastha": ["गर्भावस्था", "pregnancy"],
    "khatre": ["खतरे", "danger"],
    "sanket": ["संकेत", "signs"],
    "navjat": ["नवजात", "newborn"],
    "maa": ["माँ", "mother"],
    "surakshit": ["सुरक्षित", "safe"],
    "prasav": ["प्रसव", "delivery"],
    "rakta": ["रक्त", "blood"],
    "mutra": ["मूत्र", "urine"],
    "janch": ["जांच", "examination", "test"],
    "poshan": ["पोषण", "nutrition"],
    "paramarsh": ["परामर्श", "counselling"],
    "samajh": ["समझ", "understanding"],
    "mulyankan": ["मूल्यांकन", "assessment"],
    "navjat shishu": ["नवजात शिशु", "newborn baby"],
    "stanya": ["breastfeeding", "lactation"],
    "parivar niyojan": ["परिवार नियोजन", "family planning"],
    "uchch jokhim": ["उच्च जोखिम", "high risk"],
    "hrp": ["high risk pregnancy", "उच्च जोखिम गर्भावस्था"],
    "pph": ["post partum hemorrage", "प्रसवोत्तर रक्तस्राव"],
    "amtsl": ["active management of third stage of labour", "प्रसव के तीसरे चरण का सक्रिय प्रबंधन"],
    "enbc": ["essential newborn care", "नवजात शिशु देखभाल"],
    "kmc": ["kangaroo mother care", "कंगारू मदर केयर"],
    "anc": ["antenatal care", "गर्भावस्था देखभाल"],
    "iucd": ["आईयूसीडी", "intrauterine contraceptive device"],
    "ppiucd": ["PPIUCD", "postpartum iucd"],
    "lam": ["lactational amenorrhea method", "लैक्टेशनल एमेनोरिया विधि"],
    "lbw": ["low birth weight", "कम वजन नवजात"],
}


def _contains_phrase(text: str, phrase: str) -> bool:
    padded_text = f" {normalize_for_match(text)} "
    padded_phrase = f" {normalize_for_match(phrase)} "
    return padded_phrase in padded_text


@lru_cache(maxsize=1)
def _load_library():
    if not settings.enable_indic_transliteration:
        return None
    try:
        from indic_transliteration import sanscript  # type: ignore
        from indic_transliteration.sanscript import transliterate  # type: ignore

        return sanscript, transliterate
    except Exception:
        return None


def generate_transliterations(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    values = set()
    library = _load_library()
    if library is not None:
        sanscript, transliterate = library
        schemes = [sanscript.ITRANS, sanscript.HK, sanscript.IAST]
        if any("\u0900" <= char <= "\u097f" for char in text):
            for scheme in schemes:
                try:
                    values.add(normalize_for_match(transliterate(text, sanscript.DEVANAGARI, scheme)))
                except Exception:
                    continue
    normalized_text = normalize_for_match(text)
    values.add(normalized_text)
    for romanized, expansions in DOMAIN_ROMANIZATION_MAP.items():
        if _contains_phrase(normalized_text, romanized):
            values.update(normalize_for_match(item) for item in expansions)
        if any(_contains_phrase(normalized_text, item) for item in expansions):
            values.add(normalize_for_match(romanized))
    return sorted(value for value in values if value)


def expand_query_with_transliterations(query: str) -> list[str]:
    normalized = normalize_for_match(query)
    values = set(generate_transliterations(query))
    values.add(normalized)
    for romanized, expansions in DOMAIN_ROMANIZATION_MAP.items():
        if _contains_phrase(normalized, romanized):
            values.update(normalize_for_match(item) for item in expansions)
        for expansion in expansions:
            if _contains_phrase(normalized, expansion):
                values.add(normalize_for_match(romanized))
    return sorted(value for value in values if value)
