from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_raw_sphere_captures_are_not_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert not any(path.startswith(".local-fixtures/") for path in tracked)
    assert "sphere-pregnancy.json" not in tracked
    assert "sphere-nutrition.json" not in tracked
    assert "sphere-course.json" not in tracked
    assert "sphere-response.json" not in tracked


def test_synthetic_contract_fixtures_contain_no_forwarded_authentication_data() -> None:
    fixtures = ROOT / "tests" / "fixtures"
    content = "\n".join(path.read_text(encoding="utf-8").casefold() for path in fixtures.glob("sphere_*.json"))

    assert '"cookie"' not in content
    assert '"authorization"' not in content
    assert '"session"' not in content
