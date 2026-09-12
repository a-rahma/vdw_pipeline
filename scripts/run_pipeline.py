#!/usr/bin/env python3
"""
run_pipeline.py — Full end-to-end pipeline for the VDW study.

Executes:
  1. Discover participant folders in data/raw/
  2. Load each participant's Pupil Labs Neon export
  3. Compute session-level summaries
  4. Compute per-event segments (windowed metrics)
  5. Render per-participant HTML dashboards
  6. Compute sex- and group-level statistical comparisons
  7. Render summary graphs

Command-line options
--------------------
--only A_N       Process only one participant
--skip-dashboards    Skip HTML dashboard generation
--skip-figures       Skip summary PNG figures
--skip-stats         Skip statistical tests

Outputs
-------
results/dashboards/<pid>.html
results/figures/sex_differences_*.png
results/figures/origin_group_means.png
results/figures/location_group_means.png
results/stats/participant_summary.csv
results/stats/sex_descriptives.csv
results/stats/sex_mannwhitney.csv
results/stats/origin_kruskal.csv
results/stats/location_kruskal.csv
"""
from __future__ import annotations
import argparse
import json
import sys
import traceback
from pathlib import Path

# Make src/ importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from vdw_pipeline.config import (
    RAW_DIR, SUMMARIES_DIR, SEGMENTS_DIR, GROUP_DIR,
    STATS_DIR, DASHBOARDS_DIR, FIGURES_DIR,
)
from vdw_pipeline.io.loader   import discover_participants, load_participant, load_participant_metadata
from vdw_pipeline.metrics.session   import session_summary
from vdw_pipeline.metrics.segments  import build_segments
from vdw_pipeline.metrics.sex_differences import (
    sex_descriptives, mannwhitney_tests, kruskal_tests,
)
from vdw_pipeline.viz.dashboard  import render_dashboard, build_dashboard_payload, _sanitise_for_json
from vdw_pipeline.viz.sex_graphs import generate_all as generate_figures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument("--only",           type=str, default=None,
                         help="Process only this participant ID")
    parser.add_argument("--skip-dashboards", action="store_true")
    parser.add_argument("--skip-figures",    action="store_true")
    parser.add_argument("--skip-stats",      action="store_true")
    args = parser.parse_args()

    # Ensure output dirs exist
    for d in (SUMMARIES_DIR, SEGMENTS_DIR, GROUP_DIR,
              STATS_DIR, DASHBOARDS_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    print(f"── VDW pipeline ──")
    print(f"Raw data dir : {RAW_DIR}")

    # 1. Discover participants
    participants = discover_participants(RAW_DIR)
    if not participants:
        print(f"No participants found in {RAW_DIR}")
        print("Drop Pupil Labs Neon exports into data/raw/A_N/")
        return 1
    print(f"Discovered   : {len(participants)} participant folder(s)")

    if args.only:
        if args.only not in participants:
            print(f"Requested '{args.only}' not found. Available: {list(participants)}")
            return 1
        participants = {args.only: participants[args.only]}

    # 2. Load metadata
    metadata_df = load_participant_metadata()
    if metadata_df.empty:
        print("WARNING: data/metadata/participants.csv missing or empty. "
              "Profile columns will be blank.")

    # 3. Process each participant
    summaries = []
    for i, (pid, folder) in enumerate(sorted(participants.items()), 1):
        print(f"\n[{i}/{len(participants)}] {pid}")
        try:
            data = load_participant(pid, folder)
        except Exception as e:
            print(f"   LOAD FAILED: {e}")
            traceback.print_exc()
            continue

        meta = metadata_df.loc[pid].to_dict() if pid in metadata_df.index else {}

        # Session summary
        summary = session_summary(pid, data, meta)
        summaries.append(summary)
        pd.DataFrame([summary]).to_csv(SUMMARIES_DIR / f"{pid}.csv", index=False)
        print(f"   dur={summary['duration_min']:.1f}min · "
              f"fix={summary.get('mean_fix_ms',0):.0f}ms · "
              f"blinks={summary.get('blink_rate_per_min',0):.1f}/min · "
              f"worn={summary.get('worn_pct','?')}%")

        # Segments (also used for dashboard)
        payload = build_dashboard_payload(data)
        (SEGMENTS_DIR / f"{pid}.json").write_text(
            json.dumps(_sanitise_for_json(payload), ensure_ascii=False, indent=2))

        # Dashboard
        if not args.skip_dashboards:
            try:
                out = render_dashboard(pid, data, DASHBOARDS_DIR)
                print(f"   dashboard → {out.name}")
            except Exception as e:
                print(f"   DASHBOARD FAILED: {e}")
                traceback.print_exc()

    if not summaries:
        print("No participants processed successfully.")
        return 1

    # 4. Group-level outputs
    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(STATS_DIR / "participant_summary.csv", index=False)
    print(f"\n── Group summary ─────────────────────────")
    display_cols = [c for c in
                     ["participant_id","sex","location","origin","duration_min",
                      "mean_fix_ms","blink_rate_per_min","worn_pct"]
                     if c in summary_df.columns]
    print(summary_df[display_cols].to_string(index=False))

    if not args.skip_stats:
        # Sex descriptives + Mann-Whitney
        desc = sex_descriptives(summary_df)
        desc.to_csv(STATS_DIR / "sex_descriptives.csv", index=False)
        mw = mannwhitney_tests(summary_df)
        mw.to_csv(STATS_DIR / "sex_mannwhitney.csv", index=False)
        if not mw.empty:
            print(f"\n── Mann-Whitney U (M vs F) ────────────────")
            print(mw.to_string(index=False))

        # Origin / location Kruskal-Wallis
        for grouping in ("origin", "location"):
            if grouping in summary_df.columns:
                kw = kruskal_tests(summary_df, grouping)
                if not kw.empty:
                    kw.to_csv(STATS_DIR / f"{grouping}_kruskal.csv", index=False)
                    print(f"\n── Kruskal-Wallis H by {grouping} ──")
                    print(kw.to_string(index=False))

    # 5. Figures
    if not args.skip_figures:
        print(f"\n── Generating figures ────────────────────")
        try:
            paths = generate_figures(summary_df, FIGURES_DIR)
            for p in paths:
                print(f"   figure → {p.name}")
        except Exception as e:
            print(f"   FIGURE GENERATION FAILED: {e}")
            traceback.print_exc()

    print(f"\n── Done ──────────────────────────────────")
    print(f"Dashboards : {DASHBOARDS_DIR}")
    print(f"Figures    : {FIGURES_DIR}")
    print(f"Stats      : {STATS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
