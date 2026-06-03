import json
import requests
from dataclasses import dataclass
from pathlib import Path
import json as _json
from google.oauth2 import service_account
import googleapiclient.discovery


@dataclass
class Finding:
    detector: str
    title: str
    body: str
    labels: list[str]
    effort: str   # XS / S / M / L
    impact: str   # alt / mig / baix


def load_analytics(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_snapshot(snapshots_dir: str, iso_week: str) -> dict | None:
    p = Path(snapshots_dir) / f"{iso_week}.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def save_snapshot(snapshots_dir: str, iso_week: str, analytics: dict) -> None:
    Path(snapshots_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(snapshots_dir) / f"{iso_week}.json", "w") as f:
        json.dump(analytics, f, indent=2)


def detect_dead_urls(analytics: dict, site_base_url: str) -> list[Finding]:
    findings = []
    for page in analytics.get("hits", []):
        path = page["path"]
        count = page["count"]
        if count == 0:
            continue
        url = site_base_url.rstrip("/") + path
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            if resp.status_code == 404:
                findings.append(Finding(
                    detector="dead_url",
                    title=f"URL morta amb tràfic: {path}",
                    body=(
                        f"**Evidència:** {count} visites a una URL que retorna 404\n\n"
                        f"**URL:** `{url}`\n\n"
                        f"**Acció:** Afegir redirect 301 des de `{path}` a la pàgina equivalent activa\n\n"
                        f"**Esforç:** XS | **Impacte:** alt"
                    ),
                    labels=["marketing-agent", "seo"],
                    effort="XS",
                    impact="alt",
                ))
        except Exception:
            continue
    return findings


def _gsc_search_analytics(gsc_property: str, creds_json: str, start: str, end: str) -> list[dict]:
    creds = service_account.Credentials.from_service_account_info(
        _json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = googleapiclient.discovery.build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    resp = service.searchanalytics().query(
        siteUrl=gsc_property,
        body={"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": 500},
    ).execute()
    return resp.get("rows", [])


def detect_keyword_opportunities(gsc_property: str, creds_json: str, start: str, end: str) -> list[Finding]:
    rows = _gsc_search_analytics(gsc_property, creds_json, start, end)
    findings = []
    for row in rows:
        query = row["keys"][0]
        impressions = row["impressions"]
        ctr = row["ctr"]
        position = row["position"]
        if impressions > 100 and ctr < 0.05 and 8 <= position <= 20:
            findings.append(Finding(
                detector="keyword_opportunity",
                title=f"Keyword oportunitat: «{query}»",
                body=(
                    f"**Evidència:** {impressions:.0f} impressions · CTR {ctr * 100:.1f}% · posició {position:.1f}\n\n"
                    f"**Acció:** Millorar meta description i títol H1 de la pàgina que apareix per «{query}». "
                    f"Objectiu: pujar CTR per sobre del 5%.\n\n"
                    f"**Esforç:** S | **Impacte:** alt"
                ),
                labels=["marketing-agent", "seo"],
                effort="S",
                impact="alt",
            ))
    return findings


def detect_section_drops(analytics: dict, previous: dict | None) -> list[Finding]:
    if previous is None:
        return []
    current_sections = analytics.get("by_section", {})
    prev_sections = previous.get("by_section", {})
    findings = []
    for section, current_count in current_sections.items():
        prev_count = prev_sections.get(section)
        if not prev_count:
            continue
        drop_pct = (prev_count - current_count) / prev_count
        if drop_pct >= 0.30:
            findings.append(Finding(
                detector="section_drop",
                title=f"Caiguda de tràfic a /{section}/ ({drop_pct * 100:.0f}% vs setmana anterior)",
                body=(
                    f"**Evidència:** /{section}/ ha passat de {prev_count} a {current_count} visites "
                    f"({drop_pct * 100:.0f}% menys)\n\n"
                    f"**Acció:** Revisar si hi ha canvis recents al contingut, problemes tècnics "
                    f"o pèrdua de posicions a GSC.\n\n"
                    f"**Esforç:** M | **Impacte:** alt"
                ),
                labels=["marketing-agent", "seo", "content"],
                effort="M",
                impact="alt",
            ))
    return findings


def _fetch_event_count(gc_site: str, gc_token: str, event_path: str, start: str, end: str) -> int:
    url = f"https://{gc_site}.goatcounter.com/api/v0/stats/hits"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {gc_token}"},
        params={"start": start, "end": end, "limit": 1, "event": "true", "path": event_path},
        timeout=10,
    )
    if resp.status_code != 200:
        return 0
    return sum(h.get("count", 0) for h in resp.json().get("hits", []))


def detect_low_conversion(analytics: dict, gc_site: str, gc_token: str, start: str, end: str) -> list[Finding]:
    total = analytics.get("total", 0)
    if total == 0:
        return []
    wizard_count = _fetch_event_count(gc_site, gc_token, "wizard-sent", start, end)
    if wizard_count == 0:
        return []
    rate = wizard_count / total
    if rate >= 0.005:
        return []
    return [Finding(
        detector="low_conversion",
        title=f"Conversió del formulari baixa: {rate * 100:.1f}%",
        body=(
            f"**Evidència:** {wizard_count} enviaments sobre {total} visites = {rate * 100:.1f}%\n\n"
            f"**Benchmark:** Objectiu ≥ 0.5%\n\n"
            f"**Acció:** Revisar el wizard de contacte: CTA visible, camps mínims, missatge de confirmació clar.\n\n"
            f"**Esforç:** M | **Impacte:** alt"
        ),
        labels=["marketing-agent", "conversion"],
        effort="M",
        impact="alt",
    )]
