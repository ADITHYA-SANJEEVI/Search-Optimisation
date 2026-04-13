"""Generate an expanded benchmark set from curated seed queries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _normalize_spaces(query: str) -> str:
    tokens = query.split()
    return " ".join(tokens)


def _extra_spaces(query: str) -> str:
    tokens = query.split()
    if len(tokens) < 2:
        return query
    return "   " + "   ".join(tokens) + "   "


def _punctuation_noise(query: str) -> str:
    return f"!! {query} ??"


def _natural_language_wrap(query: str) -> str:
    return f"show me a course about {query}"


def _no_space(query: str) -> str | None:
    if any(ord(char) > 127 for char in query):
        return None
    tokens = query.split()
    if len(tokens) < 2:
        return None
    return "".join(tokens)


def _uppercase(query: str) -> str | None:
    if any(ord(char) > 127 for char in query):
        return None
    return query.upper()


def _negative_queries() -> list[dict[str, object]]:
    negatives = [
        "quantum astrophysics for toddlers",
        "best pizza near airport",
        "javascript event loop tutorial",
        "amazon return policy",
        "bollywood latest trailer",
        "football live score",
        "how to build drone engine",
        "cryptocurrency staking basics",
        "advanced kubernetes cluster tuning",
        "guitar chord progressions",
        "movie recommendation for horror fans",
        "real estate tax planning",
        "python dataframe merge examples",
        "vacation packing checklist",
        "wireless router setup",
        "photoshop layer masking",
        "gaming laptop benchmark",
        "air fryer recipes",
        "car insurance premium comparison",
        "graphic design portfolio tips",
    ]
    return [{"query": item, "expected_no_results": True, "tags": ["negative_query"]} for item in negatives]


def main() -> None:
    seed_path = ROOT / "sample_data" / "evaluation_seed_queries.json"
    output_path = ROOT / "sample_data" / "evaluation_queries.json"
    seeds = json.loads(seed_path.read_text(encoding="utf-8"))

    generated: list[dict[str, object]] = []
    seen = set()

    def add(item: dict[str, object]) -> None:
        key = (item["query"], item.get("expected_group_id"), item.get("expected_no_results", False))
        if key in seen:
            return
        seen.add(key)
        generated.append(item)

    for seed in seeds:
        add(seed)
        query = str(seed["query"])
        base_tags = list(seed.get("tags", []))
        variants = [
            (_extra_spaces(query), ["generated_extra_spaces"]),
            (_punctuation_noise(query), ["generated_punctuation"]),
            (_natural_language_wrap(query), ["generated_nlp"]),
            (_uppercase(query), ["generated_uppercase"]),
            (_no_space(query), ["generated_no_space"]),
        ]
        for variant_query, extra_tags in variants:
            if not variant_query:
                continue
            add(
                {
                    **seed,
                    "query": variant_query,
                    "tags": list(dict.fromkeys(base_tags + extra_tags)),
                }
            )

    for negative in _negative_queries():
        add(negative)

    output_path.write_text(json.dumps(generated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated={len(generated)}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
