import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "process-analytics.py"

RAW = {
    "hits_data": {
        "hits": [
            {
                "path": "/",
                "stats": [
                    {"day": "2026-09-01T00:00:00Z", "daily": 3},
                    {"day": "2026-09-02T00:00:00Z", "daily": 5},
                ],
            },
            {
                "path": "/ca/tallers/",
                "stats": [{"day": "2026-09-02T00:00:00Z", "daily": 2}],
            },
            {
                "path": "/en/blog/x",
                "stats": [{"day": "2026-09-03T00:00:00Z", "daily": 7}],
            },
        ]
    },
    "total_data": {"total_unique": 9},
}


def _run(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(RAW))
    out = tmp_path / "analytics.json"
    subprocess.run(
        [sys.executable, str(SCRIPT), str(raw), str(out), "2026-09-01", "2026-09-30"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.read_text())


def test_daily_breakdown_per_page(tmp_path):
    data = _run(tmp_path)
    assert data["pages_daily"] == {
        "/": {"2026-09-01": 3, "2026-09-02": 5},
        "/en/blog/x": {"2026-09-03": 7},
        "/ca/tallers/": {"2026-09-02": 2},
    }


def test_daily_breakdown_per_section(tmp_path):
    data = _run(tmp_path)
    assert data["sections_daily"] == {
        "inici": {"2026-09-01": 3, "2026-09-02": 5},
        "blog": {"2026-09-03": 7},
        "tallers": {"2026-09-02": 2},
    }


def test_daily_breakdown_adds_up_to_totals(tmp_path):
    data = _run(tmp_path)
    assert data["total"] == 17
    assert sum(d["count"] for d in data["hits_by_day"]) == 17
    assert sum(sum(s.values()) for s in data["pages_daily"].values()) == 17
    assert sum(sum(s.values()) for s in data["sections_daily"].values()) == 17
    assert dict(data["by_section"]) == {
        sec: sum(series.values()) for sec, series in data["sections_daily"].items()
    }
