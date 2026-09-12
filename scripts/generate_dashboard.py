#!/usr/bin/env python3
"""
generate_dashboard.py — Render one participant's dashboard.

Convenience wrapper for `run_pipeline.py --only <pid> --skip-figures --skip-stats`.

Usage
-----
    python scripts/generate_dashboard.py A1
"""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vdw_pipeline.io.loader   import discover_participants, load_participant
from vdw_pipeline.viz.dashboard import render_dashboard


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_dashboard.py <participant_id>")
        sys.exit(1)
    pid = sys.argv[1]
    participants = discover_participants()
    if pid not in participants:
        print(f"'{pid}' not found. Available: {sorted(participants)}")
        sys.exit(1)
    data = load_participant(pid, participants[pid])
    out  = render_dashboard(pid, data)
    print(f"Dashboard → {out}")


if __name__ == "__main__":
    main()
