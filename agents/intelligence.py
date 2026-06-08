import json
import requests
from dataclasses import dataclass
from pathlib import Path
import json as _json
from google.oauth2.credentials import Credentials
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


def _gsc_search_analytics(gsc_property: str, client_id: str, client_secret: str, refresh_token: str, start: str, end: str) -> list[dict]:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    service = googleapiclient.discovery.build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    resp = service.searchanalytics().query(
        siteUrl=gsc_property,
        body={"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": 500},
    ).execute()
    return resp.get("rows", [])


def detect_keyword_opportunities(gsc_property: str, client_id: str, client_secret: str, refresh_token: str, start: str, end: str) -> list[Finding]:
    rows = _gsc_search_analytics(gsc_property, client_id, client_secret, refresh_token, start, end)
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
    red  = "#cc2200"

    # ── Counts per detector ───────────────────────────────────────────────────
    counts = {"dead_url": 0, "keyword_opportunity": 0, "section_drop": 0, "low_conversion": 0}
    for f in findings:
        if f.detector in counts:
            counts[f.detector] += 1

    # Resum executiu: taula neta de 4 comptadors, sense colors vistosos
    counter_td = (
        "padding:12px 16px;border-right:1px solid #e8e8e8;text-align:center;width:25%;"
    )
    counter_rows = "".join(
        f'<td style="{counter_td}{"border-right:none;" if i == 3 else ""}">'
        f'<p style="margin:0;font-size:22px;font-weight:700;color:{red if n > 0 else "#1a1a1a"}">{n}</p>'
        f'<p style="margin:4px 0 0 0;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.06em">{lbl}</p>'
        f'</td>'
        for i, (n, lbl) in enumerate([
            (counts["dead_url"],           "URLs mortes"),
            (counts["keyword_opportunity"],"Keywords"),
            (counts["section_drop"],       "Caigudes"),
            (counts["low_conversion"],     "Conversió"),
        ])
    )

    # ── SVG chart ─────────────────────────────────────────────────────────────
    hits = (analytics or {}).get("hits", [])
    svg_chart = _build_svg_chart(hits)

    # ── Icona check (SVG, sense emoji) ────────────────────────────────────────
    ico_check = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 15 15" '
        'style="vertical-align:-2px;margin-right:7px" fill="none" '
        'stroke="#1a1a1a" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="7.5" cy="7.5" r="6.5"/>'
        '<polyline points="4.5,8 6.5,10 10.5,5.5"/>'
        '</svg>'
    )

    # ── Findings ──────────────────────────────────────────────────────────────
    if not findings:
        findings_html = (
            f'<p style="border-left:3px solid {red};padding:14px 20px;'
            f'color:#1a1a1a;font-size:14px;margin:0;line-height:1.5">'
            f'{ico_check}Cap finding accionable aquesta setmana.</p>'
        )
    else:
        cards = []
        for f in findings:
            det_label = _detector_label(f.detector)
            body_html = _md_to_html(f.body).replace("\n\n", "<br><br>").replace("\n", " ")
            meta = (
                f'<span style="font-size:11px;color:#888;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-right:16px">{det_label}</span>'
                f'<span style="font-size:11px;color:#888;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-right:16px">Esforç {f.effort}</span>'
                f'<span style="font-size:11px;color:#888;text-transform:uppercase;'
                f'letter-spacing:.06em">Impacte {f.impact}</span>'
            )
            cards.append(
                f'<div style="border-left:3px solid {red};padding:16px 20px;margin-bottom:20px">'
                f'<p style="margin:0 0 6px 0;font-size:15px;font-weight:700;color:#1a1a1a">{f.title}</p>'
                f'<p style="margin:0 0 10px 0">{meta}</p>'
                f'<p style="margin:0;font-size:14px;color:#444;line-height:1.65">{body_html}</p>'
                f'</div>'
            )
        findings_html = "\n".join(cards)

    # ── Full HTML ─────────────────────────────────────────────────────────────
    sep   = "border-bottom:1px solid #e8e8e8;"
    pad   = "padding:28px 32px;"
    label = f"font-size:11px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.08em;margin:0 0 20px 0;"

    # Icona barres per capçalera (color accent, fons blanc)
    ico_bars = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" '
        f'fill="{red}" style="display:inline-block;vertical-align:-4px;margin-right:10px">'
        '<rect x="1" y="11" width="4" height="8" rx="1"/>'
        '<rect x="8" y="6" width="4" height="13" rx="1"/>'
        '<rect x="15" y="2" width="4" height="17" rx="1"/>'
        '</svg>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe setmanal {site} — {iso_week}</title>
</head>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:{font}">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f0f0;padding:32px 0">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#ffffff;border-top:4px solid {red}">

  <!-- CAPÇALERA -->
  <tr><td style="{pad}{sep}">
    <p style="margin:0 0 4px 0;font-size:20px;font-weight:700;color:#1a1a1a;line-height:1.2">
      {ico_bars}Informe setmanal
    </p>
    <p style="margin:8px 0 0 30px;font-size:13px;color:#888">{site} &nbsp;·&nbsp; Setmana {iso_week}</p>
  </td></tr>

  <!-- RESUM EXECUTIU -->
  <tr><td style="{pad}{sep}">
    <p style="{label}">Resum executiu</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8">
      <tr>{counter_rows}</tr>
    </table>
  </td></tr>

  <!-- GRÀFIC TOP PÀGINES -->
  <tr><td style="{pad}{sep}">
    <p style="{label}">Top pàgines per tràfic</p>
    {svg_chart}
  </td></tr>

  <!-- FINDINGS -->
  <tr><td style="{pad}">
    <p style="{label}">Findings accionables</p>
    {findings_html}
  </td></tr>

  <!-- PEU -->
  <tr><td style="padding:16px 32px;border-top:1px solid #e8e8e8;background:#fafafa">
    <p style="margin:0;font-size:11px;color:#aaa;text-align:center">
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
            config["gsc_property"],
            secrets["gsc_client_id"],
            secrets["gsc_client_secret"],
            secrets["gsc_refresh_token"],
            start, end,
        )
    except Exception as exc:
        print(f"GSC detector failed, skipping: {exc}")
    findings += detect_section_drops(analytics, previous)
    findings += detect_low_conversion(
        analytics, config["goatcounter_site"], secrets["goatcounter_token"], start, end,
    )
    save_snapshot(snapshots_dir, iso_week, analytics)
    return findings
