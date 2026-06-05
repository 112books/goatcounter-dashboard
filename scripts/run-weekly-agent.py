#!/usr/bin/env python3
"""Entrypoint del workflow. Llegeix config + secrets, corre l'agent, crea Issues, envia email."""
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import yaml
import requests as http

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.intelligence import run as run_agent, generate_insights_report, generate_insights_report_html
from tasks.github_issues import create_issue, ensure_labels_exist


def main():
    config_path = os.environ["AGENT_CONFIG"]
    with open(config_path) as f:
        config = yaml.safe_load(f)

    secrets = {
        "goatcounter_token":           os.environ.get("GOATCOUNTER_TOKEN", ""),
        "google_service_account_json": os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
        "gh_token":                    os.environ["GH_TOKEN"],
    }

    iso_week = datetime.now(timezone.utc).strftime("%Y-%W")
    snapshots_dir = "admin/snapshots"
    insights_dir  = "admin/insights"
    Path(insights_dir).mkdir(parents=True, exist_ok=True)

    analytics_url = config.get("analytics_url")
    if analytics_url:
        resp = http.get(analytics_url, timeout=15)
        resp.raise_for_status()
        analytics_path = "/tmp/analytics.json"
        Path(analytics_path).write_text(resp.text)
        print(f"Analytics descarregats: {analytics_url}")
    else:
        analytics_path = "admin/analytics.json"

    findings = run_agent(config, secrets, analytics_path, snapshots_dir, iso_week)
    report   = generate_insights_report(findings, iso_week)

    Path(f"{insights_dir}/{iso_week}.md").write_text(report)

    try:
        import json as _json
        with open(analytics_path) as _f:
            analytics = _json.load(_f)
    except Exception:
        analytics = None

    report_html = generate_insights_report_html(findings, iso_week, analytics, config.get("site", ""))
    Path(f"{insights_dir}/{iso_week}.html").write_text(report_html)

    if findings:
        all_labels = list({label for f in findings for label in f.labels})
        ensure_labels_exist(config["github_repo"], all_labels, secrets["gh_token"])

    issue_urls = []
    for finding in findings:
        url = create_issue(
            config["github_repo"], finding.title, finding.body, finding.labels, secrets["gh_token"]
        )
        issue_urls.append(url)
        print(f"Issue creat: {url}")

    print(f"Done. {len(findings)} findings, {len(issue_urls)} issues.")

    _send_email(config, iso_week, report_html)


def _send_email(config, iso_week, html):
    username = os.environ.get("GMAIL_USERNAME", "linuxbcn@gmail.com")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not password:
        print("Email: GMAIL_APP_PASSWORD no configurat, saltant")
        return

    site = config.get("site", "")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Informe setmanal {site} — setmana {iso_week}"
    msg["From"]    = f"Marketing Agent <{username}>"
    msg["To"]      = username
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(username, password)
            server.send_message(msg)
        print("Email enviat ✓")
    except Exception as e:
        print(f"Email error: {e}")


if __name__ == "__main__":
    main()
