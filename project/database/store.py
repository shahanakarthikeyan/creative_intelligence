"""database/store.py — lightweight JSON-backed persistence for the pipeline.

No real database needed for the MVP. This gives Scout a memory of which ad
IDs it has already seen (so "new_ads" is meaningful across runs) and keeps
a timestamped history of every pipeline report. Swap this module for
SQLite/Postgres later without touching orchestrator/pipeline.py — it only
depends on the four functions below.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
KNOWN_IDS_PATH = os.path.join(DATA_DIR, "known_ad_ids.json")
HISTORY_DIR = os.path.join(DATA_DIR, "reports")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)


def load_known_ids() -> set:
    """Ad IDs Scout has already seen in a previous run."""
    if not os.path.exists(KNOWN_IDS_PATH):
        return set()
    with open(KNOWN_IDS_PATH, "r") as f:
        return set(json.load(f))


def save_known_ids(ids: set) -> None:
    with open(KNOWN_IDS_PATH, "w") as f:
        json.dump(sorted(ids), f, indent=2)


def save_report(report: dict) -> str:
    """Persists a full pipeline run as a timestamped JSON file. Returns the path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(HISTORY_DIR, f"report_{ts}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def load_latest_report() -> Optional[dict]:
    """Returns the most recent saved report, or None if no runs yet (useful for a dashboard)."""
    files = sorted(os.listdir(HISTORY_DIR))
    if not files:
        return None
    with open(os.path.join(HISTORY_DIR, files[-1]), "r") as f:
        return json.load(f)
