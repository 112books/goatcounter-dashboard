import json
import requests
from dataclasses import dataclass
from pathlib import Path
import json as _json
from google.oauth2 import service_account
import googleapiclient.discovery
from datetime import datetime, timedelta, timezone


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
    for page in analytics.get("hits", [])[:30]:
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


def _md_to_html(text: str) -> str:
    """Convert basic Markdown bold (**text**) to HTML <strong>."""
    import re
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def _detector_label(detector: str) -> str:
    return {
        "dead_url": "URL morta",
        "keyword_opportunity": "Keyword oportunitat",
        "section_drop": "Caiguda de secció",
        "low_conversion": "Conversió baixa",
    }.get(detector, detector)


def _impact_color(impact: str) -> str:
    return {"alt": "#cc2200", "mig": "#e07b00", "baix": "#4a7c59"}.get(impact, "#888888")


def _build_svg_chart(hits: list[dict]) -> str:
    """Build an inline SVG bar chart for top 10 pages by traffic."""
    top = hits[:10]
    if not top:
        return (
            '<p style="color:#888;font-style:italic;margin:0">Sense dades de tràfic disponibles.</p>'
        )

    max_count = max(h["count"] for h in top) or 1
    bar_height = 22
    gap = 8
    label_width = 260
    bar_area = 300
    chart_width = label_width + bar_area + 60
    chart_height = len(top) * (bar_height + gap) + 10

    rows = []
    for i, h in enumerate(top):
        y = i * (bar_height + gap)
        bar_w = max(2, int(h["count"] / max_count * bar_area))
        path = h["path"] if len(h["path"]) <= 38 else h["path"][:35] + "…"
        rows.append(
            f'<g transform="translate(0,{y})">'
            f'<text x="{label_width - 8}" y="{bar_height - 6}" '
            f'text-anchor="end" font-size="12" fill="#1a1a1a" font-family="Arial,sans-serif">{path}</text>'
            f'<rect x="{label_width}" y="2" width="{bar_w}" height="{bar_height - 4}" '
            f'fill="#cc2200" rx="2"/>'
            f'<text x="{label_width + bar_w + 6}" y="{bar_height - 6}" '
            f'font-size="11" fill="#555" font-family="Arial,sans-serif">{h["count"]}</text>'
            f'</g>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{chart_height}" '
        f'style="max-width:100%;display:block">'
        + "".join(rows)
        + "</svg>"
    )


def generate_insights_report_html(
    findings: list[Finding],
    iso_week: str,
    analytics: dict | None,
    site: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"

    # ── Counts per detector type ──────────────────────────────────────────────
    counts = {"dead_url": 0, "keyword_opportunity": 0, "section_drop": 0, "low_conversion": 0}
    for f in findings:
        if f.detector in counts:
            counts[f.detector] += 1

    pill_style = (
        "display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;"
        "font-weight:600;margin:3px 4px 3px 0;white-space:nowrap;"
    )
    pill_map = {
        "dead_url":           ("#fdecea", "#cc2200", "URL mortes"),
        "keyword_opportunity": ("#fff3e0", "#e07b00", "Keywords"),
        "section_drop":       ("#e8f4fd", "#1565c0", "Caigudes"),
        "low_conversion":     ("#f3e5f5", "#7b1fa2", "Conversió"),
    }
    pills_html = ""
    for key, (bg, fg, label) in pill_map.items():
        n = counts[key]
        pills_html += (
            f'<span style="{pill_style}background:{bg};color:{fg}">'
            f'{label}: {n}</span>'
        )

    # ── SVG chart ─────────────────────────────────────────────────────────────
    hits = (analytics or {}).get("hits", [])
    svg_chart = _build_svg_chart(hits)

    # ── Findings cards ────────────────────────────────────────────────────────
    if not findings:
        findings_html = (
            '<p style="background:#e8f5e9;border-left:4px solid #4caf50;padding:16px 20px;'
            'border-radius:4px;color:#2e7d32;font-size:15px;margin:0">'
            '✅ Cap finding accionable aquesta setmana.</p>'
        )
    else:
        card_style = (
            "background:#ffffff;border:1px solid #e0e0e0;border-radius:6px;"
            "padding:20px 24px;margin-bottom:16px;"
        )
        cards = []
        for f in findings:
            det_label = _detector_label(f.detector)
            imp_color = _impact_color(f.impact)
            body_html = _md_to_html(f.body).replace("\n\n", "<br><br>").replace("\n", " ")
            cards.append(
                f'<div style="{card_style}">'
                f'<p style="margin:0 0 8px 0;font-size:15px;font-weight:700;color:#1a1a1a">{f.title}</p>'
                f'<div style="margin-bottom:12px">'
                f'<span style="{pill_style}background:#f5f5f5;color:#555;border:1px solid #ddd">'
                f'{det_label}</span>'
                f'<span style="{pill_style}background:{imp_color}22;color:{imp_color}">'
                f'Impacte {f.impact}</span>'
                f'<span style="{pill_style}background:#f5f5f5;color:#555;border:1px solid #ddd">'
                f'Esforç {f.effort}</span>'
                f'</div>'
                f'<p style="margin:0;font-size:14px;color:#444;line-height:1.6">{body_html}</p>'
                f'</div>'
            )
        findings_html = "\n".join(cards)

    # ── Full HTML ─────────────────────────────────────────────────────────────
    section_style = "background:#ffffff;padding:24px 32px;border-bottom:1px solid #e0e0e0;"
    h2_style = "margin:0 0 16px 0;font-size:14px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.08em"

    html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe setmanal {site} — {iso_week}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:{font}">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

  <!-- CAPÇALERA -->
  <tr><td style="background:#1a1a1a;padding:28px 32px">
    <p style="margin:0 0 4px 0;font-size:22px;font-weight:700;color:#ffffff">📊 Informe setmanal</p>
    <p style="margin:0;font-size:14px;color:#aaaaaa">{site} &nbsp;·&nbsp; Setmana {iso_week}</p>
  </td></tr>

  <!-- RESUM EXECUTIU -->
  <tr><td style="{section_style}">
    <p style="{h2_style}">Resum executiu</p>
    <p style="margin:0 0 12px 0;font-size:15px;color:#1a1a1a">
      <strong>{len(findings)} finding{"s" if len(findings) != 1 else ""}</strong> detectat{"s" if len(findings) != 1 else ""} aquesta setmana.
    </p>
    <div>{pills_html}</div>
  </td></tr>

  <!-- GRÀFIC TOP PÀGINES -->
  <tr><td style="{section_style}">
    <p style="{h2_style}">Top pàgines per tràfic</p>
    {svg_chart}
  </td></tr>

  <!-- FINDINGS -->
  <tr><td style="background:#ffffff;padding:24px 32px">
    <p style="{h2_style}">Findings accionables</p>
    {findings_html}
  </td></tr>

  <!-- PEU -->
  <tr><td style="background:#f5f5f5;padding:20px 32px;border-top:1px solid #e0e0e0">
    <p style="margin:0;font-size:12px;color:#888;text-align:center">
      Generat per Marketing Agent &nbsp;·&nbsp; linuxbcn.com &nbsp;·&nbsp; {now}
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html


def run(config: dict, secrets: dict, analytics_path: str, snapshots_dir: str, iso_week: str) -> list[Finding]:
    analytics = load_analytics(analytics_path)
    prev_week = (datetime.now(timezone.utc) - timedelta(weeks=1)).strftime("%Y-%W")
    previous = load_snapshot(snapshots_dir, prev_week)
    period = analytics.get("period", {})
    start, end = period.get("start", ""), period.get("end", "")

    findings: list[Finding] = []
    findings += detect_dead_urls(analytics, f"https://{config['site']}")
    try:
        findings += detect_keyword_opportunities(
            config["gsc_property"], secrets["google_service_account_json"], start, end,
        )
    except Exception as exc:
        print(f"GSC detector failed, skipping: {exc}")
    findings += detect_section_drops(analytics, previous)
    findings += detect_low_conversion(
        analytics, config["goatcounter_site"], secrets["goatcounter_token"], start, end,
    )
    save_snapshot(snapshots_dir, iso_week, analytics)
    return findings
