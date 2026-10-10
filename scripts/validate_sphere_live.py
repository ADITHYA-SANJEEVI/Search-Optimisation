"""Read-only acceptance against a running API, public records, and local OpenSearch."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import httpx


def main():
    base = os.environ.get("ADVANCED_SEARCH_BASE_URL", "http://127.0.0.1:8017")
    index_url = os.environ.get("OPENSEARCH_URL", "http://127.0.0.1:9200")
    index = os.environ.get("OPENSEARCH_INDEX", "sphere-courses-v1")
    source = os.environ["SPHERE_PUBLIC_SEARCH_URL"]
    with httpx.Client(timeout=30) as client:
        def search(body):
            response = client.post(base + "/v1/search", json=body)
            response.raise_for_status()
            result = response.json()
            assert set(result) <= {"ids", "total", "corrected_query"}
            return result
        ready = client.get(base + "/api/v1/ready")
        assert ready.status_code == 200 and ready.json()["status"] == "ready"
        results = search({"query": "pregnancy", "limit": 100})
        assert results["ids"]
        assert search({"query": "pregnancy", "limit": 100}) == results
        page = search({"query": "pregnancy", "limit": 2, "offset": 2})
        assert page["ids"] == results["ids"][2:4] and page["total"] == results["total"]
        assert search({"query": "pregnancy", "offset": results["total"]})["ids"] == []
        browse = search({"limit": 100})
        expected = client.post(f"{index_url}/{index}/_search", json={"size": 100,
            "query": {"bool": {"filter": [{"term": {"category": "Course"}}, {"term": {"publication_status": "Live"}}]}},
            "sort": [{"updated_on": {"order": "desc", "missing": "_last"}}, {"course_id": "asc"}]}).json()
        assert browse["ids"] == [hit["_id"] for hit in expected["hits"]["hits"]]
        assert search({"limit": 2, "offset": 2})["ids"] == browse["ids"][2:4]
        indexed = client.get(f"{index_url}/{index}/_count").json()["count"]
        assert browse["total"] == indexed
        typo = search({"query": "postpartm hemorhage managment", "limit": 5})
        assert typo["ids"] and typo.get("corrected_query")
        fetched = client.post(source, json={"request": {"filters": {"identifier": page["ids"],
            "primaryCategory": ["Course"], "status": ["Live"]}, "limit": len(page["ids"]), "offset": 0}})
        fetched.raise_for_status()
        records = fetched.json()["result"]["content"]
        by_id = {r["identifier"]: r for r in reversed(records)}
        ordered = [by_id[id]["identifier"] for id in page["ids"] if id in by_id]
        assert ordered == page["ids"]
        report = {"timestamp": datetime.now(timezone.utc).isoformat(), "api_base": base,
            "backend_index": index, "index_count": indexed, "readiness_status": ready.status_code,
            "query": "pregnancy", "query_total": results["total"], "query_page": page,
            "browse_total": browse["total"], "browse_ids_first5": browse["ids"][:5],
            "typo": typo, "fetched_original_ids_reordered": ordered,
            "passed_scenarios": ["A: query/pagination/public-record-fetch/reorder", "B: typo correction",
                                 "C: browse matches OpenSearch date sort", "readiness", "determinism", "offset >= total"]}
    Path("artifacts/sphere_live_acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
