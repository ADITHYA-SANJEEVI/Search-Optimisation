"""Validate voice-search behavior against generated fixture audio files."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["STT_PROVIDER"] = "whisper"

from app.main import app
from app.services.bootstrap import build_container


def main() -> None:
    manifest_path = ROOT / "sample_data" / "voice" / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("Voice fixture manifest missing. Run scripts/generate_voice_fixtures.ps1 first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    app.state.container = build_container()
    failures: list[dict[str, object]] = []
    with TestClient(app) as client:
        for item in manifest:
            file_path = ROOT / item["path"]
            response = client.post(
                f"/api/v1/search/voice?preferred_language={item['preferred_language']}",
                files={"file": (file_path.name, file_path.read_bytes(), "audio/wav")},
            )
            payload = response.json()
            top_group = None
            if payload.get("search_response", {}).get("results"):
                top_group = payload["search_response"]["results"][0]["group_id"]
            print(f"{file_path.name}: top_group={top_group} degraded={payload.get('degraded')}")
            if top_group != item["expected_group_id"]:
                failures.append(
                    {
                        "file": file_path.name,
                        "expected_group_id": item["expected_group_id"],
                        "actual_group_id": top_group,
                    }
                )
    artifacts_dir = ROOT / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    report_path = artifacts_dir / "voice_validation_report.json"
    report_path.write_text(json.dumps({"failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise SystemExit(f"Voice validation failed for {len(failures)} fixture(s). See {report_path}.")
    print(f"Voice validation passed. report={report_path}")


if __name__ == "__main__":
    main()
