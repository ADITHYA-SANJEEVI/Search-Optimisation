"""Run before API startup, or restart API after an external sync to reload its cache."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations.sphere_sync import SpherePublicClient, SyncFailure, SyncReport, sync_catalogue
from app.search.encoder import SemanticEncoder
from app.search.opensearch_backend import OpenSearchBackedSearchBackend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--report", default="artifacts/sphere_sync_report.json")
    args = parser.parse_args()
    endpoint = os.environ.get("SPHERE_PUBLIC_SEARCH_URL")
    if not endpoint:
        parser.error("Set SPHERE_PUBLIC_SEARCH_URL to the publicContent/v1/search endpoint")
    source = SpherePublicClient(endpoint)
    try:
        backend = OpenSearchBackedSearchBackend(SemanticEncoder())
        report = sync_catalogue(source, backend, mode=args.mode, page_size=args.page_size)
        code = 0
    except SyncFailure as exc:
        report = exc.report
        code = 1
    except Exception as exc:
        report = SyncReport(endpoint, args.page_size, args.mode, failures=[type(exc).__name__])
        code = 1
    finally:
        source.client.close()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in asdict(report).items() if k != "diagnostics"}))
    return code


if __name__ == "__main__":
    sys.exit(main())
