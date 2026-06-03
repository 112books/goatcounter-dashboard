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
        "goatcounter_token":           os.environ["GOATCOUNTER_TOKEN"],
        "google_service_account_json": os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
        "gh_token":                    os.environ["GH_TOKEN"],
    }

    iso_week = datetime.now(timezone.utc).strftime("%Y-%W")
    snapshots_dir = "admin/snapshots"
    insights_dir  = "admin/insights"
    Path(insights_dir).mkdir(parents=True, exist_ok=True)

    findings = run_agent(config, secrets, "admin/analytics.json", snapshots_dir, iso_week)
    report   = generate_insights_report(findings, iso_week)

    Path(f"{insights_dir}/{iso_week}.md").write_text(report)

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
            safe_title = (
                finding.title
                .replace(".", "\\.")
                .replace("-", "\\-")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            lines.append(f"{i}\\. [{safe_title}]({url})")

    try:
        resp = http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "MarkdownV2"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        print(f"Telegram notification failed (non-fatal): {exc}")


if __name__ == "__main__":
    main()
