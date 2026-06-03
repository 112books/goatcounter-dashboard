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
