"""Language and script heuristics."""

from __future__ import annotations

import re

from app.utils.text import detect_requested_language, normalize_text


def detect_languages(query: str) -> list[str]:
    detected = detect_requested_language(query)
    normalized = normalize_text(query)
    if re.search(r"[\u0900-\u097F]", query):
        detected.append("hindi")
    if re.search(r"[\u0B80-\u0BFF]", query):
        detected.append("tamil")
    if "english" not in detected and re.search(r"[a-zA-Z]", normalized):
        detected.append("english")
    return sorted(set(detected))


def is_code_mixed(query: str) -> bool:
    normalized = normalize_text(query)
    has_latin = bool(re.search(r"[a-zA-Z]", normalized))
    has_indic = bool(re.search(r"[\u0900-\u097F\u0B80-\u0BFF]", query))
    explicit_language = len(detect_requested_language(query)) > 1
    return (has_latin and has_indic) or explicit_language
