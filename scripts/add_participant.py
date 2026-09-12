#!/usr/bin/env python3
"""
add_participant.py — Interactive helper for registering a new participant.

Adds a row to data/metadata/participants.csv after prompting for each field.
Does NOT copy raw data — that step is manual (see docs/how_to_add_participant.md).

Usage
-----
    python scripts/add_participant.py               # interactive
    python scripts/add_participant.py --et-code A22 --sex M --location PBL \
        --origin Portugal --pseudonym Xavier

Both --et-code and --pseudonym are required; other fields prompt if omitted.
"""
from __future__ import annotations
import argparse
import sys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vdw_pipeline.config import PARTICIPANTS_CSV, RAW_DIR

COLUMNS = ["et_code", "pseudonym", "code", "interview_code", "breakdown_code",
            "sex", "location", "origin", "experience", "track"]


def prompt(field: str, default: str = "") -> str:
    val = input(f"  {field} [{default}]: ").strip()
    return val or default


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    for c in COLUMNS:
        ap.add_argument(f"--{c.replace('_','-')}", default=None)
    args = ap.parse_args()
    fields = {c: getattr(args, c) for c in COLUMNS}

    print(f"── Add participant to {PARTICIPANTS_CSV.name} ──")

    # Prompt for missing fields
    for c in COLUMNS:
        if fields[c] is None:
            fields[c] = prompt(c)

    # Validate essentials
    if not fields["et_code"]:
        print("ERROR: et_code required.")
        sys.exit(1)

    # Check for existing entry
    existing = []
    if PARTICIPANTS_CSV.exists():
        with open(PARTICIPANTS_CSV) as f:
            existing = list(csv.DictReader(f))
        if any(r["et_code"] == fields["et_code"] for r in existing):
            print(f"ERROR: {fields['et_code']} already exists in {PARTICIPANTS_CSV.name}")
            sys.exit(1)
    else:
        PARTICIPANTS_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Append the row
    write_header = not PARTICIPANTS_CSV.exists() or PARTICIPANTS_CSV.stat().st_size == 0
    with open(PARTICIPANTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(fields)

    print(f"\n✓ Added {fields['et_code']} ({fields['pseudonym']}) to {PARTICIPANTS_CSV.name}")

    raw_dir = RAW_DIR / fields["et_code"]
    if not raw_dir.exists():
        print(f"\nNext step:")
        print(f"  Unzip the Pupil Cloud export into {raw_dir}/")
        print(f"  Then run: python scripts/run_pipeline.py --only {fields['et_code']}")
    else:
        print(f"\nRaw folder already exists. Run the pipeline:")
        print(f"  python scripts/run_pipeline.py --only {fields['et_code']}")


if __name__ == "__main__":
    main()
