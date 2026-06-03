import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from agents.intelligence import Finding, load_analytics, load_snapshot, save_snapshot, detect_dead_urls, detect_keyword_opportunities, detect_section_drops, detect_low_conversion, generate_insights_report
from agents.intelligence import run as run_agent

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

_GSC_ROWS = [
    {"keys": ["fotografia jazz barcelona"],     "impressions": 210, "ctr": 0.031, "position": 14.2},
    {"keys": ["fotògrafs barcelona"],           "impressions": 50,  "ctr": 0.08,  "position": 5.0},
    {"keys": ["fotografia concerts"],           "impressions": 180, "ctr": 0.12,  "position": 12.0},
    {"keys": ["fotografia festival primavera"], "impressions": 120, "ctr": 0.02,  "position": 18.5},
]

def test_detect_keyword_opportunities_filters_correctly():
    with patch("agents.intelligence._gsc_search_analytics", return_value=_GSC_ROWS):
        findings = detect_keyword_opportunities(
            gsc_property="https://pocallum.cat/",
            creds_json='{"type":"service_account"}',
            start="2026-05-01",
            end="2026-06-01",
        )
    assert len(findings) == 2
    titles = [f.title for f in findings]
    assert any("fotografia jazz barcelona" in t for t in titles)
    assert any("fotografia festival primavera" in t for t in titles)
    assert findings[0].effort == "S"
    assert "seo" in findings[0].labels

def test_detect_keyword_opportunities_returns_empty_on_no_rows():
    with patch("agents.intelligence._gsc_search_analytics", return_value=[]):
        findings = detect_keyword_opportunities("https://pocallum.cat/", "{}", "2026-05-01", "2026-06-01")
    assert findings == []

def test_detect_section_drops_flags_30pct_drop():
    current  = {**SAMPLE_ANALYTICS, "by_section": {"galeria": 55, "serveis": 300}}
    previous = {**SAMPLE_ANALYTICS, "by_section": {"galeria": 90, "serveis": 300}}
    findings = detect_section_drops(current, previous)
    assert len(findings) == 1
    assert "galeria" in findings[0].title
    assert findings[0].impact == "alt"

def test_detect_section_drops_no_previous_returns_empty():
    assert detect_section_drops(SAMPLE_ANALYTICS, None) == []

def test_detect_section_drops_ignores_small_drops():
    current  = {**SAMPLE_ANALYTICS, "by_section": {"festivals": 560}}
    previous = {**SAMPLE_ANALYTICS, "by_section": {"festivals": 600}}
    assert detect_section_drops(current, previous) == []

def test_detect_low_conversion_flags_below_threshold():
    analytics = {**SAMPLE_ANALYTICS, "total": 2000}
    with patch("agents.intelligence._fetch_event_count", return_value=5):
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert len(findings) == 1
    assert "0.2%" in findings[0].body  # 5/2000 = 0.25% → rounds to 0.2%
    assert findings[0].effort == "M"
    assert "conversion" in findings[0].labels

def test_detect_low_conversion_ok_when_above_threshold():
    analytics = {**SAMPLE_ANALYTICS, "total": 1000}
    with patch("agents.intelligence._fetch_event_count", return_value=10):  # 1.0%
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert findings == []

def test_detect_low_conversion_skips_when_no_total():
    analytics = {**SAMPLE_ANALYTICS, "total": 0}
    with patch("agents.intelligence._fetch_event_count", return_value=0):
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert findings == []

SAMPLE_FINDINGS = [
    Finding("dead_url",    "URL morta: /old/",          "cos1", ["marketing-agent", "seo"],            "XS", "alt"),
    Finding("keyword_opp", "Keyword: «jazz barcelona»", "cos2", ["marketing-agent", "seo"],            "S",  "alt"),
    Finding("section_drop","Caiguda /galeria/ (-35%)",  "cos3", ["marketing-agent", "seo", "content"], "M",  "alt"),
]

def test_generate_insights_report_contains_findings():
    report = generate_insights_report(SAMPLE_FINDINGS, "2026-23")
    assert "# Informe setmanal" in report
    assert "2026-23" in report
    assert "URL morta: /old/" in report
    assert "jazz barcelona" in report
    assert "3" in report

def test_generate_insights_report_empty():
    report = generate_insights_report([], "2026-23")
    assert "Cap finding" in report

def test_run_agent_calls_all_detectors(tmp_path):
    config = {
        "site": "pocallum.cat",
        "goatcounter_site": "pocallum",
        "gsc_property": "https://pocallum.cat/",
        "github_repo": "joan-linux/pocallum.cat",
    }
    secrets = {
        "goatcounter_token": "gc_token",
        "google_service_account_json": "{}",
        "gh_token": "gh_token",
    }
    analytics_path = tmp_path / "analytics.json"
    analytics_path.write_text(json.dumps(SAMPLE_ANALYTICS))
    with patch("agents.intelligence.detect_dead_urls",            return_value=[]) as m1, \
         patch("agents.intelligence.detect_keyword_opportunities", return_value=[]) as m2, \
         patch("agents.intelligence.detect_section_drops",         return_value=[]) as m3, \
         patch("agents.intelligence.detect_low_conversion",        return_value=[]) as m4:
        findings = run_agent(config, secrets, str(analytics_path), str(tmp_path / "snapshots"), "2026-23")
    m1.assert_called_once()
    m2.assert_called_once()
    m3.assert_called_once()
    m4.assert_called_once()
    assert findings == []
    assert (tmp_path / "snapshots" / "2026-23.json").exists()
