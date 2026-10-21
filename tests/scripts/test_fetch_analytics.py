import pytest

from scripts import fetch_goatcounter_analytics as fetch

HITS = {
    "hits": [
        {
            "path": "/",
            "stats": [
                {"day": "2026-09-01T00:00:00Z", "daily": 3},
                {"day": "2026-09-02T00:00:00Z", "daily": 5},
            ],
        },
        {"path": "/ca/tallers/", "stats": [{"day": "2026-09-02T00:00:00Z", "daily": 2}]},
        {"path": "/en/blog/x", "stats": [{"day": "2026-09-03T00:00:00Z", "daily": 7}]},
    ]
}


@pytest.fixture
def fake_api(monkeypatch):
    def _get(site, token, endpoint, params):
        if endpoint == "/stats/hits":
            return HITS
        return {"stats": []}

    monkeypatch.setattr(fetch, "_gc_get", _get)
    return fetch.fetch_analytics("demo", "token", days=30)


def test_fetch_exposes_pages_daily(fake_api):
    assert fake_api["pages_daily"] == {
        "/": {"2026-09-01": 3, "2026-09-02": 5},
        "/en/blog/x": {"2026-09-03": 7},
        "/ca/tallers/": {"2026-09-02": 2},
    }


def test_fetch_exposes_sections_daily(fake_api):
    assert fake_api["sections_daily"] == {
        "inici": {"2026-09-01": 3, "2026-09-02": 5},
        "blog": {"2026-09-03": 7},
        "tallers": {"2026-09-02": 2},
    }


def test_fetch_daily_totals_match_total(fake_api):
    assert fake_api["total"] == 17
    assert sum(sum(series.values()) for series in fake_api["pages_daily"].values()) == 17
    assert sum(sum(series.values()) for series in fake_api["sections_daily"].values()) == 17
