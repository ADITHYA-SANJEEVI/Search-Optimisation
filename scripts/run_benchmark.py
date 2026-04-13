"""Offline evaluation script for the sample query set."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.schemas.search import SearchRequest
from app.services.bootstrap import build_container


def main() -> None:
    container = build_container()
    queries = json.loads(Path("sample_data/evaluation_queries.json").read_text(encoding="utf-8"))
    verbose = "--verbose" in sys.argv
    top1_hits = 0
    top3_hits = 0
    negative_passes = 0
    per_tag = defaultdict(lambda: {"count": 0, "top1": 0, "top3": 0})
    failures = []
    for item in queries:
        response = container.search_service.search(
            SearchRequest(
                query=item["query"],
                preferred_language=item.get("preferred_language"),
            )
        )
        result_groups = [result.group_id for result in response.results]
        expected = item.get("expected_group_id")
        expected_no_results = bool(item.get("expected_no_results", False))
        top1_hit = False
        top3_hit = False
        if expected_no_results:
            top1_hit = len(result_groups) == 0
            top3_hit = len(result_groups) == 0
            if top1_hit:
                negative_passes += 1
        else:
            top1_hit = result_groups[:1] == [expected]
            top3_hit = expected in result_groups[:3]
            if top1_hit:
                top1_hits += 1
            if top3_hit:
                top3_hits += 1
        for tag in item.get("tags", []):
            per_tag[tag]["count"] += 1
            if top1_hit:
                per_tag[tag]["top1"] += 1
            if top3_hit:
                per_tag[tag]["top3"] += 1
        if not top3_hit:
            failures.append({"query": item["query"], "expected": expected or "NO_RESULTS", "got": result_groups[:3]})
        if verbose:
            print(f"query={item['query']!r} top3={result_groups[:3]}")
    positive_total = sum(1 for item in queries if not item.get("expected_no_results"))
    negative_total = sum(1 for item in queries if item.get("expected_no_results"))
    print(f"top1={top1_hits}/{positive_total} ({top1_hits / positive_total:.0%})")
    print(f"top3={top3_hits}/{positive_total} ({top3_hits / positive_total:.0%})")
    if negative_total:
        print(f"negative_no_result_pass={negative_passes}/{negative_total} ({negative_passes / negative_total:.0%})")
    print("per_tag:")
    for tag in sorted(per_tag):
        count = per_tag[tag]["count"]
        top1 = per_tag[tag]["top1"]
        top3 = per_tag[tag]["top3"]
        print(f"  {tag}: top1={top1}/{count} ({top1 / count:.0%}) top3={top3}/{count} ({top3 / count:.0%})")
    if failures:
        print("failures:")
        for failure in failures:
            print(f"  query={failure['query']!r} expected={failure['expected']} got={failure['got']}")
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "positive_total": positive_total,
        "negative_total": negative_total,
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "negative_passes": negative_passes,
        "per_tag": per_tag,
        "failures": failures,
    }
    (artifacts_dir / "benchmark_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=dict),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
