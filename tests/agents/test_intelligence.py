import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from agents.intelligence import Finding, load_analytics, load_snapshot, save_snapshot, detect_dead_urls

SAMPLE_ANALYTICS = {
    "generated": "2026-06-03T16:00:00Z",
    "period": {"start": "2025-06-03", "end": "2026-06-03"},
    "total": 1500,
    "total_unique": 800,
    "hits": [
        {"path": "/festivals/calella-harmonica/", "count": 250},
        {"path": "/serveis/",                     "count": 180},
        {"path": "/galeria/",                     "count": 90},
    ],
    "hits_by_day": [],
    "by_lang":    {"ca": 900, "es": 400, "en": 200},
    "by_section": {"festivals": 600, "serveis": 300, "galeria": 200, "blog": 400},
    "browsers": [], "systems": [], "sizes": [], "locations": [], "refs": [],
}

def test_load_analytics_reads_json(tmp_path):
    p = tmp_path / "analytics.json"
    p.write_text(json.dumps(SAMPLE_ANALYTICS))
    data = load_analytics(str(p))
    assert data["total"] == 1500
    assert data["hits"][0]["path"] == "/festivals/calella-harmonica/"

def test_load_snapshot_returns_none_when_missing(tmp_path):
    assert load_snapshot(str(tmp_path), "2026-23") is None

def test_save_and_load_snapshot_roundtrip(tmp_path):
    save_snapshot(str(tmp_path), "2026-23", SAMPLE_ANALYTICS)
    loaded = load_snapshot(str(tmp_path), "2026-23")
    assert loaded["total"] == 1500

def test_finding_dataclass():
    f = Finding(
        detector="dead_url",
        title="Redirigir /old/ → /new/",
        body="**Evidència:** 45 visites a URL 404\n\n**Acció:** Afegir redirect 301\n\n**Esforç:** XS | **Impacte:** alt",
        labels=["marketing-agent", "seo"],
        effort="XS",
        impact="alt",
    )
    assert f.detector == "dead_url"
    assert "marketing-agent" in f.labels

def test_detect_dead_urls_returns_finding_for_404():
    mock_404 = MagicMock(); mock_404.status_code = 404
    mock_200 = MagicMock(); mock_200.status_code = 200
    with patch("agents.intelligence.requests.head", side_effect=[mock_404, mock_200, mock_200]):
        findings = detect_dead_urls(SAMPLE_ANALYTICS, "https://pocallum.cat")
    assert len(findings) == 1
    assert "/festivals/calella-harmonica/" in findings[0].title
    assert findings[0].effort == "XS"
    assert "seo" in findings[0].labels

def test_detect_dead_urls_ignores_200():
    mock_200 = MagicMock(); mock_200.status_code = 200
    with patch("agents.intelligence.requests.head", return_value=mock_200):
        findings = detect_dead_urls(SAMPLE_ANALYTICS, "https://pocallum.cat")
    assert findings == []

def test_detect_dead_urls_skips_on_connection_error():
    with patch("agents.intelligence.requests.head", side_effect=Exception("timeout")):
        findings = detect_dead_urls(SAMPLE_ANALYTICS, "https://pocallum.cat")
    assert findings == []
