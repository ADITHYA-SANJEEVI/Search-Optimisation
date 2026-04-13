"""Text normalization and lightweight linguistic helpers."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter


STOPWORDS = {
    "a",
    "an",
    "about",
    "for",
    "the",
    "to",
    "i",
    "need",
    "learn",
    "show",
    "me",
    "course",
    "courses",
    "of",
    "and",
    "in",
    "on",
    "with",
    "please",
}

ABBREVIATIONS = {
    "bf": "breastfeeding",
    "nb": "newborn",
    "ppd": "postpartum depression",
    "pp": "postpartum",
}

SYNONYM_MAP = {
    "breast feeding": ["breastfeeding", "lactation", "nursing"],
    "breastfeeding": ["lactation", "nursing"],
    "lactation": ["breastfeeding", "nursing"],
    "new born": ["newborn", "infant", "baby care"],
    "newborn": ["new born", "infant", "baby care"],
    "post partum": ["postpartum"],
    "postpartum": ["post partum", "after delivery"],
    "depression": ["low mood", "mental health"],
    "basics": ["beginner", "foundation", "intro"],
    "beginner": ["basics", "introductory"],
    "advanced": ["expert", "specialist"],
    "tamil": ["tamizh", "thamizh"],
    "hindi": ["hindhi"],
    "c section": ["cesarean", "caesarean"],
}

TRANSLITERATION_MAP = {
    "tamizh": "tamil",
    "thamizh": "tamil",
    "thaippal": "breastfeeding",
    "palootal": "breastfeeding",
    "kulanthai": "newborn",
    "paramarippu": "care",
    "pirandha": "newborn",
    "piragu": "postpartum",
}

DIFFICULTY_TERMS = {
    "beginner": {"beginner", "basic", "basics", "foundation", "intro", "introductory", "starter"},
    "advanced": {"advanced", "expert", "specialist", "professional"},
    "intermediate": {"intermediate"},
}

LANGUAGE_WORDS = {
    "english": {"english", "eng"},
    "tamil": {"tamil", "tamizh", "thamizh"},
    "hindi": {"hindi", "hindhi"},
    "telugu": {"telugu"},
}

FILLER_WORDS = {"uh", "um", "please", "actually", "basically", "like"}
WEAK_RETRIEVAL_TERMS = {
    "advanced",
    "advance",
    "expert",
    "specialist",
    "beginner",
    "basic",
    "basics",
    "foundation",
    "intro",
    "introductory",
    "starter",
    "intermediate",
}


def unicode_normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def normalize_repeated_letters(text: str) -> str:
    return re.sub(r"([a-zA-Z])\1{2,}", r"\1\1", text)


def strip_noise(text: str) -> str:
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    return re.sub(r"[_]+", " ", text)


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def expand_abbreviations(text: str) -> str:
    words = []
    for token in text.split():
        words.append(ABBREVIATIONS.get(token, token))
    return " ".join(words)


def normalize_text(text: str) -> str:
    text = unicode_normalize(text or "")
    text = text.lower()
    text = expand_abbreviations(text)
    text = normalize_repeated_letters(text)
    text = strip_noise(text)
    return collapse_spaces(text)


def singularize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def singularize_phrase(text: str) -> str:
    return " ".join(singularize_token(token) for token in text.split())


def normalize_for_match(text: str) -> str:
    return singularize_phrase(normalize_text(text))


def compact_text(text: str) -> str:
    return normalize_for_match(text).replace(" ", "")


def tokenize(text: str, *, keep_stopwords: bool = False) -> list[str]:
    normalized = normalize_for_match(text)
    tokens = [token for token in normalized.split() if token]
    if keep_stopwords:
        return tokens
    return [token for token in tokens if token not in STOPWORDS]


def detect_requested_language(text: str) -> list[str]:
    tokens = set(tokenize(text, keep_stopwords=True))
    detected = []
    for language, words in LANGUAGE_WORDS.items():
        if tokens & words:
            detected.append(language)
    return detected


def extract_difficulty(text: str) -> str | None:
    tokens = set(tokenize(text, keep_stopwords=True))
    for difficulty, words in DIFFICULTY_TERMS.items():
        if tokens & words:
            return difficulty
    return None


def apply_transliteration_map(text: str) -> str:
    tokens = []
    for token in normalize_text(text).split():
        tokens.append(TRANSLITERATION_MAP.get(token, token))
    return collapse_spaces(" ".join(tokens))


def expand_synonyms(tokens: list[str]) -> list[str]:
    expanded = set(tokens)
    joined = " ".join(tokens)
    for phrase, synonyms in SYNONYM_MAP.items():
        if phrase in joined:
            expanded.update(tokenize(" ".join(synonyms), keep_stopwords=True))
    for token in list(tokens):
        expanded.update(tokenize(" ".join(SYNONYM_MAP.get(token, [])), keep_stopwords=True))
    return [token for token in expanded if token]


def remove_fillers(text: str) -> str:
    tokens = [token for token in normalize_text(text).split() if token not in FILLER_WORDS]
    return collapse_spaces(" ".join(tokens))


def filter_retrieval_terms(tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in WEAK_RETRIEVAL_TERMS]


def make_char_ngrams(text: str, size: int = 3) -> list[str]:
    compact = compact_text(text)
    if len(compact) <= size:
        return [compact] if compact else []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]


def counter_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def build_weighted_counter(text: str) -> Counter[str]:
    tokens = tokenize(text, keep_stopwords=False)
    ngrams = make_char_ngrams(text)
    return Counter(tokens + ngrams)


def soundex(token: str) -> str:
    token = re.sub(r"[^a-z]", "", token.lower())
    if not token:
        return ""
    mappings = {
        "bfpv": "1",
        "cgjkqsxz": "2",
        "dt": "3",
        "l": "4",
        "mn": "5",
        "r": "6",
    }
    first = token[0].upper()
    encoded = []
    previous = ""
    for char in token[1:]:
        code = ""
        for letters, value in mappings.items():
            if char in letters:
                code = value
                break
        if code != previous:
            encoded.append(code)
        if code:
            previous = code
    digits = "".join(code for code in encoded if code)
    return (first + digits + "000")[:4]
