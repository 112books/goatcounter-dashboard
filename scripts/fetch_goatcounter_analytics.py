"""Fetch analytics directly from GoatCounter API and return processed dict.

Used when a site config has `goatcounter_fetch: true` (no public analytics_url).
"""
from __future__ import annotations

import requests
from datetime import datetime, timedelta, timezone


def _gc_get(gc_site: str, gc_token: str, endpoint: str, params: dict) -> dict:
    url = f"https://{gc_site}.goatcounter.com/api/v0{endpoint}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {gc_token}"},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _extract_section(path: str) -> str:
    LANGS = {"ca", "es", "en", "fr", "de", "it", "pt"}
    if not path:
        return "inici"
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return "inici"
    idx = 1 if parts[0] in LANGS else 0
    return parts[idx] if idx < len(parts) else "inici"


def _norm_stats(stats: list) -> list:
    out = []
    for item in stats:
        name = item.get("name") or item.get("id") or "Desconegut"
        count = item.get("count", 0)
        if count > 0:
            out.append({"name": name, "id": item.get("id", name), "count": count})
    return sorted(out, key=lambda x: x["count"], reverse=True)


def fetch_analytics(gc_site: str, gc_token: str, days: int = 7) -> dict:
    """Fetch last `days` days from GoatCounter API and return analytics dict."""
    now = datetime.now(timezone.utc)
    end = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {"start": start, "end": end, "limit": 50}

    # ── Hits per page ─────────────────────────────────────────────────────────
    try:
        hits_raw = _gc_get(gc_site, gc_token, "/stats/hits", params).get("hits", [])
    except Exception as exc:
        print(f"WARN: GoatCounter hits fetch failed: {exc}")
        hits_raw = []

    by_section: dict[str, int] = {}
    total = 0
    hits_by_day: dict[str, int] = {}
    hits_pages: dict[str, int] = {}

    for path_item in hits_raw:
        path = path_item.get("path", "")
        section = _extract_section(path)
        path_total = 0

        for stat in path_item.get("stats", []):
            date = (stat.get("day") or "")[:10]
            count = stat.get("daily", 0)
            if not count:
                continue
            total += count
            path_total += count
            by_section[section] = by_section.get(section, 0) + count
            if date:
                hits_by_day[date] = hits_by_day.get(date, 0) + count

        if path_total > 0:
            hits_pages[path] = hits_pages.get(path, 0) + path_total

    hits_by_day_list = [{"date": k, "count": v} for k, v in sorted(hits_by_day.items())]
    hits_top = sorted(
        [{"path": k, "count": v} for k, v in hits_pages.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:30]

    # ── Optional stats (non-fatal) ────────────────────────────────────────────
    def safe_fetch_stats(endpoint: str) -> list:
        try:
            data = _gc_get(gc_site, gc_token, endpoint, params)
            return _norm_stats(data.get("stats", []))
        except Exception as exc:
            print(f"WARN: {endpoint} failed: {exc}")
            return []

    return {
        "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "period": {"start": start, "end": end},
        "total": total,
        "total_unique": 0,
        "hits_by_day": hits_by_day_list,
        "hits": hits_top,
        "by_section": by_section,
        "browsers": safe_fetch_stats("/stats/browsers"),
        "systems": safe_fetch_stats("/stats/systems"),
        "sizes": safe_fetch_stats("/stats/sizes"),
        "locations": safe_fetch_stats("/stats/locations"),
        "refs": safe_fetch_stats("/stats/toprefs"),
    }
