import json
import requests
from dataclasses import dataclass
from pathlib import Path


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
