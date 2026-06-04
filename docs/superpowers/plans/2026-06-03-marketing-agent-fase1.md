# Marketing Agent — Fase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un agent autònom que cada dilluns a les 8h llegeix `admin/analytics.json` + Google Search Console, detecta 5 patrons accionables, crea GitHub Issues al repo del site i envia un resum per Telegram.

**Architecture:** `weekly-agent.yml` (GitHub Actions, dilluns 7h UTC) crida `scripts/run-weekly-agent.py`, que executa `agents/intelligence.py` (5 detectors) i converteix els findings en GitHub Issues via `tasks/github_issues.py`. Desa snapshot setmanal a `admin/snapshots/YYYY-WW.json` i informe a `admin/insights/YYYY-WW.md`, fa commit i push. `admin/analytics.json` ja existeix (actualitzat cada hora per `fetch-analytics.yml`).

**Tech Stack:** Python 3.11, `requests`, `google-api-python-client`, `google-auth`, `PyYAML`, GitHub REST API v2022-11-28, Telegram Bot API, GitHub Actions.

---

## Mapa de fitxers

| Fitxer | Acció | Responsabilitat |
|--------|-------|-----------------|
| `tasks/__init__.py` | Crear | Mòdul buit |
| `tasks/github_issues.py` | Crear | `create_issue()` + `ensure_labels_exist()` via GitHub REST API |
| `agents/__init__.py` | Crear | Mòdul buit |
| `agents/intelligence.py` | Crear | `Finding` dataclass, 4 detectors, `run()`, `generate_insights_report()` |
| `scripts/run-weekly-agent.py` | Crear | Entrypoint del workflow: llegeix config + secrets, crida agent, crea Issues, Telegram |
| `config/pocallum.cat.yaml` | Crear | Config de site per Phase 1 (no-secret, commitable) |
| `requirements-agent.txt` | Crear | Deps Python per al workflow |
| `.github/workflows/weekly-agent.yml` | Crear | Cron dilluns 7h UTC + `workflow_dispatch` |
| `tests/tasks/test_github_issues.py` | Crear | Tests unitaris del task module |
| `tests/agents/test_intelligence.py` | Crear | Tests unitaris dels 4 detectors + `run()` + report |

---

## Task 1: `tasks/github_issues.py` — Creador d'Issues

**Files:**
- Create: `tasks/__init__.py`
- Create: `tasks/github_issues.py`
- Create: `tests/tasks/__init__.py`
- Create: `tests/tasks/test_github_issues.py`

- [ ] **Step 1: Escriu els tests que fallen**

```python
# tests/tasks/test_github_issues.py
import pytest
from unittest.mock import patch, MagicMock
from tasks.github_issues import create_issue, ensure_labels_exist

def test_create_issue_returns_url():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
    mock_resp.raise_for_status.return_value = None
    with patch("tasks.github_issues.requests.post", return_value=mock_resp) as mock_post:
        url = create_issue("owner/repo", "Test title", "Test body", ["seo"], "gh_token_xxx")
    assert url == "https://github.com/owner/repo/issues/1"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["title"] == "Test title"
    assert "seo" in call_kwargs.kwargs["json"]["labels"]

def test_create_issue_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    with patch("tasks.github_issues.requests.post", return_value=mock_resp):
        with pytest.raises(Exception, match="403"):
            create_issue("owner/repo", "Title", "Body", [], "bad_token")

def test_ensure_labels_exist_creates_missing_label():
    list_resp = MagicMock()
    list_resp.json.return_value = [{"name": "seo"}]
    list_resp.raise_for_status.return_value = None
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    with patch("tasks.github_issues.requests.get", return_value=list_resp):
        with patch("tasks.github_issues.requests.post", return_value=create_resp) as mock_post:
            ensure_labels_exist("owner/repo", ["seo", "marketing-agent"], "token")
    assert mock_post.call_count == 1  # only "marketing-agent" is missing
    assert mock_post.call_args.kwargs["json"]["name"] == "marketing-agent"
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/tasks/test_github_issues.py -v
```
Expected: `ModuleNotFoundError: No module named 'tasks'`

- [ ] **Step 3: Implementa els fitxers**

```python
# tasks/__init__.py
# (buit)
```

```python
# tasks/github_issues.py
import requests

GH_API = "https://api.github.com"
_GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def _headers(token: str) -> dict:
    return {**_GH_HEADERS, "Authorization": f"Bearer {token}"}

def create_issue(repo: str, title: str, body: str, labels: list[str], token: str) -> str:
    """Creates a GitHub Issue. Returns the issue HTML URL."""
    url = f"{GH_API}/repos/{repo}/issues"
    resp = requests.post(url, headers=_headers(token), json={"title": title, "body": body, "labels": labels})
    resp.raise_for_status()
    return resp.json()["html_url"]

def ensure_labels_exist(repo: str, labels: list[str], token: str) -> None:
    """Creates any labels that don't exist in the repo."""
    url = f"{GH_API}/repos/{repo}/labels"
    existing = {l["name"] for l in requests.get(url, headers=_headers(token)).json()}
    label_colors = {
        "marketing-agent": "0075ca",
        "seo":             "e4e669",
        "content":         "d93f0b",
        "social":          "5319e7",
        "conversion":      "0e8a16",
    }
    for label in labels:
        if label not in existing:
            resp = requests.post(
                url,
                headers=_headers(token),
                json={"name": label, "color": label_colors.get(label, "ededed")},
            )
            resp.raise_for_status()
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/tasks/test_github_issues.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add tasks/ tests/tasks/
git commit -m "feat: add GitHub Issues task module"
```

---

## Task 2: Fonaments de l'agent — `Finding` + carregador d'analytics

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/intelligence.py`
- Create: `tests/agents/__init__.py`
- Create: `tests/agents/test_intelligence.py`

- [ ] **Step 1: Escriu els tests que fallen**

```python
# tests/agents/test_intelligence.py
import json
import pytest
from pathlib import Path
from agents.intelligence import Finding, load_analytics, load_snapshot, save_snapshot

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
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: `ModuleNotFoundError: No module named 'agents'`

- [ ] **Step 3: Implementa la base**

```python
# agents/__init__.py
# (buit)
```

```python
# agents/intelligence.py
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
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/ tests/agents/
git commit -m "feat: intelligence agent foundation — Finding dataclass + analytics loader"
```

---

## Task 3: Detector — URLs mortes amb tràfic

Fa HEAD requests a les pàgines del top 30 de `analytics.json`. Si retornen 404, genera un Finding.

**Files:**
- Modify: `agents/intelligence.py` — afegir `detect_dead_urls()`
- Modify: `tests/agents/test_intelligence.py` — afegir tests

- [ ] **Step 1: Escriu els tests que fallen**

```python
# Afegir a tests/agents/test_intelligence.py
from unittest.mock import patch, MagicMock
from agents.intelligence import detect_dead_urls

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
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py::test_detect_dead_urls_returns_finding_for_404 -v
```
Expected: `ImportError: cannot import name 'detect_dead_urls'`

- [ ] **Step 3: Implementa `detect_dead_urls()`**

Afegir a `agents/intelligence.py`, just after `save_snapshot()`:

```python
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
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/intelligence.py tests/agents/test_intelligence.py
git commit -m "feat: add dead URL detector"
```

---

## Task 4: Detector — Keyword oportunitats (GSC)

Crida Google Search Console API. Retorna findings per a queries amb impressions > 100, CTR < 5%, posició 8–20.

**Files:**
- Modify: `agents/intelligence.py` — afegir `_gsc_search_analytics()` + `detect_keyword_opportunities()`
- Modify: `tests/agents/test_intelligence.py`

- [ ] **Step 1: Instal·la deps i escriu tests que fallen**

```
pip install google-api-python-client google-auth
```

```python
# Afegir a tests/agents/test_intelligence.py
from agents.intelligence import detect_keyword_opportunities

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
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py::test_detect_keyword_opportunities_filters_correctly -v
```
Expected: `ImportError: cannot import name 'detect_keyword_opportunities'`

- [ ] **Step 3: Implementa**

Afegir a `agents/intelligence.py` (afegir `import json as _json` i imports de google al top del fitxer):

```python
import json as _json
from google.oauth2 import service_account
import googleapiclient.discovery

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
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/intelligence.py tests/agents/test_intelligence.py
git commit -m "feat: add GSC keyword opportunity detector"
```

---

## Task 5: Detector — Caiguda de seccions

Compara `by_section` entre l'analytics actual i el snapshot de la setmana anterior. Marca seccions amb ≥ −30%.

**Files:**
- Modify: `agents/intelligence.py` — afegir `detect_section_drops()`
- Modify: `tests/agents/test_intelligence.py`

- [ ] **Step 1: Escriu els tests que fallen**

```python
# Afegir a tests/agents/test_intelligence.py
from agents.intelligence import detect_section_drops

def test_detect_section_drops_flags_30pct_drop():
    current  = {**SAMPLE_ANALYTICS, "by_section": {"festivals": 400, "galeria": 55, "serveis": 300}}
    previous = {**SAMPLE_ANALYTICS, "by_section": {"festivals": 600, "galeria": 90, "serveis": 300}}
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
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py::test_detect_section_drops_flags_30pct_drop -v
```
Expected: `ImportError: cannot import name 'detect_section_drops'`

- [ ] **Step 3: Implementa**

```python
# Afegir a agents/intelligence.py
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
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 12 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/intelligence.py tests/agents/test_intelligence.py
git commit -m "feat: add section drop detector"
```

---

## Task 6: Detector — Conversió baixa (wizard-sent)

Crida GoatCounter events API per obtenir el count de `wizard-sent`. Marca si < 0.5% del total de visites.

**Files:**
- Modify: `agents/intelligence.py` — afegir `_fetch_event_count()` + `detect_low_conversion()`
- Modify: `tests/agents/test_intelligence.py`

- [ ] **Step 1: Escriu els tests que fallen**

```python
# Afegir a tests/agents/test_intelligence.py
from agents.intelligence import detect_low_conversion

def test_detect_low_conversion_flags_below_threshold():
    analytics = {**SAMPLE_ANALYTICS, "total": 2000}
    with patch("agents.intelligence._fetch_event_count", return_value=5):
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert len(findings) == 1
    assert "0.3%" in findings[0].body  # 5/2000 = 0.25% → arrodonit a 0.3%
    assert findings[0].effort == "M"
    assert "conversion" in findings[0].labels

def test_detect_low_conversion_ok_when_above_threshold():
    analytics = {**SAMPLE_ANALYTICS, "total": 1000}
    with patch("agents.intelligence._fetch_event_count", return_value=10):  # 10/1000 = 1.0%
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert findings == []

def test_detect_low_conversion_skips_when_no_total():
    analytics = {**SAMPLE_ANALYTICS, "total": 0}
    with patch("agents.intelligence._fetch_event_count", return_value=0):
        findings = detect_low_conversion(analytics, "pocallum", "gc_token_xxx", "2026-05-01", "2026-06-01")
    assert findings == []
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py::test_detect_low_conversion_flags_below_threshold -v
```
Expected: `ImportError: cannot import name 'detect_low_conversion'`

- [ ] **Step 3: Implementa**

```python
# Afegir a agents/intelligence.py
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
```

- [ ] **Step 4: Executa per verificar que passen**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 15 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/intelligence.py tests/agents/test_intelligence.py
git commit -m "feat: add low conversion detector"
```

---

## Task 7: `run()` + `generate_insights_report()` — Orquestrador i informe

Connecta tots els detectors en `run()` i genera l'informe markdown setmanal.

**Files:**
- Modify: `agents/intelligence.py` — afegir `generate_insights_report()` + `run()`
- Modify: `tests/agents/test_intelligence.py`

- [ ] **Step 1: Escriu els tests que fallen**

```python
# Afegir a tests/agents/test_intelligence.py
import json
from agents.intelligence import generate_insights_report
from agents.intelligence import run as run_agent

SAMPLE_FINDINGS = [
    Finding("dead_url",    "URL morta: /old/",          "cos1", ["marketing-agent", "seo"],          "XS", "alt"),
    Finding("keyword_opp", "Keyword: «jazz barcelona»", "cos2", ["marketing-agent", "seo"],          "S",  "alt"),
    Finding("section_drop","Caiguda /galeria/ (-35%)",  "cos3", ["marketing-agent", "seo", "content"], "M","alt"),
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
```

- [ ] **Step 2: Executa per verificar que fallen**

```
pytest tests/agents/test_intelligence.py::test_generate_insights_report_contains_findings -v
```
Expected: `ImportError: cannot import name 'generate_insights_report'`

- [ ] **Step 3: Implementa**

```python
# Afegir a agents/intelligence.py
from datetime import datetime, timezone

def generate_insights_report(findings: list[Finding], iso_week: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Informe setmanal — setmana {iso_week}",
        f"_Generat: {now}_",
        "",
        f"**{len(findings)} findings detectats**",
        "",
    ]
    if not findings:
        lines.append("Cap finding accionable aquesta setmana.")
        return "\n".join(lines)
    for i, f in enumerate(findings, 1):
        lines += [f"## {i}. {f.title}", "", f.body, "", "---", ""]
    return "\n".join(lines)

def run(config: dict, secrets: dict, analytics_path: str, snapshots_dir: str, iso_week: str) -> list[Finding]:
    analytics = load_analytics(analytics_path)
    previous = load_snapshot(snapshots_dir, iso_week)
    period = analytics.get("period", {})
    start, end = period.get("start", ""), period.get("end", "")

    findings: list[Finding] = []
    findings += detect_dead_urls(analytics, f"https://{config['site']}")
    findings += detect_keyword_opportunities(
        config["gsc_property"], secrets["google_service_account_json"], start, end,
    )
    findings += detect_section_drops(analytics, previous)
    findings += detect_low_conversion(
        analytics, config["goatcounter_site"], secrets["goatcounter_token"], start, end,
    )
    save_snapshot(snapshots_dir, iso_week, analytics)
    return findings
```

- [ ] **Step 4: Executa tots els tests**

```
pytest tests/agents/test_intelligence.py -v
```
Expected: 18 PASSED

- [ ] **Step 5: Commit**

```bash
git add agents/intelligence.py tests/agents/test_intelligence.py
git commit -m "feat: wire detectors into run() + insights report generator"
```

---

## Task 8: Workflow + entrypoint + config del site

Crea el workflow de GitHub Actions, l'entrypoint Python i la config de pocallum.cat.

**Files:**
- Create: `requirements-agent.txt`
- Create: `config/pocallum.cat.yaml`
- Create: `scripts/run-weekly-agent.py`
- Create: `.github/workflows/weekly-agent.yml`

- [ ] **Step 1: Crea `requirements-agent.txt`**

```
requests>=2.31
google-api-python-client>=2.100
google-auth>=2.23
PyYAML>=6.0
```

- [ ] **Step 2: Crea `config/pocallum.cat.yaml`**

```yaml
site: pocallum.cat
goatcounter_site: pocallum
gsc_property: https://pocallum.cat/
github_repo: joan-linux/pocallum.cat
```

_(El `telegram_chat_id` va com a secret `TELEGRAM_CHAT_ID`, no aquí)_

- [ ] **Step 3: Crea `scripts/run-weekly-agent.py`**

```python
#!/usr/bin/env python3
"""Entrypoint del workflow. Llegeix config + secrets, corre l'agent, crea Issues, notifica Telegram."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
import requests as http

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.intelligence import run as run_agent, generate_insights_report
from tasks.github_issues import create_issue, ensure_labels_exist

def main():
    config_path = os.environ["AGENT_CONFIG"]
    with open(config_path) as f:
        config = yaml.safe_load(f)

    secrets = {
        "goatcounter_token":          os.environ["GOATCOUNTER_TOKEN"],
        "google_service_account_json": os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
        "gh_token":                   os.environ["GH_TOKEN"],
    }

    iso_week = datetime.now(timezone.utc).strftime("%Y-%W")
    snapshots_dir = "admin/snapshots"
    insights_dir  = "admin/insights"
    Path(insights_dir).mkdir(parents=True, exist_ok=True)

    findings = run_agent(config, secrets, "admin/analytics.json", snapshots_dir, iso_week)
    report   = generate_insights_report(findings, iso_week)

    Path(f"{insights_dir}/{iso_week}.md").write_text(report)

    if findings:
        all_labels = list({l for f in findings for l in f.labels})
        ensure_labels_exist(config["github_repo"], all_labels, secrets["gh_token"])

    issue_urls = []
    for finding in findings:
        url = create_issue(config["github_repo"], finding.title, finding.body, finding.labels, secrets["gh_token"])
        issue_urls.append(url)
        print(f"Issue creat: {url}")

    _send_telegram(config, findings, issue_urls, iso_week)
    print(f"Done. {len(findings)} findings, {len(issue_urls)} issues.")

def _send_telegram(config: dict, findings: list, issue_urls: list, iso_week: str) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("Telegram no configurat, saltant notificació.")
        return

    lines = [f"📊 *Informe setmanal {iso_week}* — {config['site']}", ""]
    if not findings:
        lines.append("Cap finding accionable aquesta setmana\\. ✅")
    else:
        for i, (finding, url) in enumerate(zip(findings, issue_urls), 1):
            safe_title = finding.title.replace(".", "\\.").replace("-", "\\-").replace("(", "\\(").replace(")", "\\)")
            lines.append(f"{i}\\. [{safe_title}]({url})")

    http.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "MarkdownV2"},
        timeout=10,
    )

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Crea `.github/workflows/weekly-agent.yml`**

```yaml
name: Weekly Marketing Agent

on:
  schedule:
    - cron: '0 7 * * 1'   # dilluns 08:00 CET (UTC+1 hivern) = 07:00 UTC
  workflow_dispatch:

jobs:
  intelligence:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements-agent.txt

      - name: Run intelligence agent
        env:
          GOATCOUNTER_TOKEN:           ${{ secrets.GOATCOUNTER_TOKEN }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GH_TOKEN:                    ${{ secrets.GH_AGENT_TOKEN }}
          TELEGRAM_BOT_TOKEN:          ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:            ${{ secrets.TELEGRAM_CHAT_ID }}
          AGENT_CONFIG:                config/pocallum.cat.yaml
        run: python scripts/run-weekly-agent.py

      - name: Commit insights + snapshot
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add admin/snapshots/ admin/insights/ || true
          git diff --staged --quiet || git commit -m "chore: weekly insights [skip ci]"
          git pull --rebase
          git push
```

- [ ] **Step 5: Commit**

```bash
git add requirements-agent.txt config/ scripts/run-weekly-agent.py .github/workflows/weekly-agent.yml
git commit -m "feat: weekly-agent workflow + entrypoint + pocallum.cat config"
```

---

## Task 9: Suite de tests completa + push

- [ ] **Step 1: Executa tots els tests**

```
pytest tests/ -v --tb=short
```
Expected: 18+ PASSED, 0 FAILED.

- [ ] **Step 2: Comprova que el workflow és vàlid amb `actionlint` (opcional)**

```bash
brew install actionlint  # si no instal·lat
actionlint .github/workflows/weekly-agent.yml
```
Expected: cap error.

- [ ] **Step 3: Push i verifica que el workflow apareix a GitHub Actions**

```bash
git push origin main
```
Navega a `112books/goatcounter-dashboard → Actions`. Ha d'apareixer "Weekly Marketing Agent" a la llista de workflows.

- [ ] **Step 4: Comprova estructura de fitxers final**

```bash
find agents/ tasks/ scripts/ config/ tests/ .github/workflows/ -type f | sort
```
Expected:
```
.github/workflows/fetch-analytics.yml
.github/workflows/weekly-agent.yml
agents/__init__.py
agents/intelligence.py
config/pocallum.cat.yaml
requirements-agent.txt
scripts/run-weekly-agent.py
tasks/__init__.py
tasks/github_issues.py
tests/agents/__init__.py
tests/agents/test_intelligence.py
tests/tasks/__init__.py
tests/tasks/test_github_issues.py
```

---

## Secrets a configurar a GitHub (pas 5 de l'usuari)

A `112books/goatcounter-dashboard → Settings → Secrets and variables → Actions`:

| Secret | Valor | Notes |
|--------|-------|-------|
| `GOATCOUNTER_TOKEN` | token API de GoatCounter | ja existeix |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON sencer del service account | compte de Google Cloud amb GSC API activa |
| `GH_AGENT_TOKEN` | PAT amb `repo` scope | ha de poder crear Issues a `joan-linux/pocallum.cat` |
| `TELEGRAM_BOT_TOKEN` | token del bot de Telegram | creat via @BotFather |
| `TELEGRAM_CHAT_ID` | ID del xat on enviar | obtenir via `https://api.telegram.org/bot{token}/getUpdates` |

Per provar el primer informe sense esperar el dilluns: **Actions → Weekly Marketing Agent → Run workflow**.
