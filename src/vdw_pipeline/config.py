"""
config.py — Central configuration for the VDW pipeline.

All parameters that affect the analysis live here. Modify with care; every
change should be reflected in docs/methodology.md and the paper's methods.
"""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT              = Path(__file__).resolve().parents[2]
DATA_DIR          = ROOT / "data"
RAW_DIR           = DATA_DIR / "raw"
PROCESSED_DIR     = DATA_DIR / "processed"
SEGMENTS_DIR      = PROCESSED_DIR / "segments"
SUMMARIES_DIR     = PROCESSED_DIR / "summaries"
GROUP_DIR         = PROCESSED_DIR / "group"
METADATA_DIR      = DATA_DIR / "metadata"
PARTICIPANTS_CSV  = METADATA_DIR / "participants.csv"

RESULTS_DIR       = ROOT / "results"
DASHBOARDS_DIR    = RESULTS_DIR / "dashboards"
FIGURES_DIR       = RESULTS_DIR / "figures"
STATS_DIR         = RESULTS_DIR / "stats"

# ── Participant discovery ────────────────────────────────────────────────────
# Participant folders are named with a letter + number code (e.g. A1, A2, ...
# A21), matching the interview_code convention in participants.csv. This
# glob matches any single-letter prefix (upper or lowercase) followed by
# digits: A1, a1, B12, etc. Adjust if your site uses a different scheme.
PARTICIPANT_GLOB = "[A-Za-z][0-9]*"


# ── Device (Pupil Labs Neon) ─────────────────────────────────────────────────
GAZE_HZ         = 100
SCENE_WIDTH_PX  = 1600
SCENE_HEIGHT_PX = 1200

# ── Signal quality gates ─────────────────────────────────────────────────────
# Fixations: Rayner (2009) reports meaningful information uptake begins at
# ~100 ms; above 3000 ms is likely a tracker artefact.
FIXATION_MIN_DURATION_MS = 100
FIXATION_MAX_DURATION_MS = 3000

# Blinks: Doughty (2001) reports typical spontaneous blink duration 100-400 ms.
# Our gate is wider (50-500) to admit fast blinks and short lid closures.
BLINK_MIN_DURATION_MS = 50
BLINK_MAX_DURATION_MS = 500

# Pupil (optional; used only if pupil analysis enabled)
PUPIL_MIN_MM = 1.5
PUPIL_MAX_MM = 9.0

# ── Fixation duration bands ──────────────────────────────────────────────────
# For per-participant summary: % of fixations below/above these thresholds.
# Below 120 ms suggests visual search / scanning (short saccadic recovery);
# above 300 ms suggests deep processing (Rayner, 2009).
FIX_SHORT_MS = 120
FIX_LONG_MS  = 300

# ── Gaze heatmap grid ────────────────────────────────────────────────────────
# Scene-camera grid for the dashboard "where they looked" heatmap.
GRID_W = 16
GRID_H = 12

# ── Optional Cognitive Load Index (composite) — off by default in v1 ────────
# Retained here for backward-compatibility with earlier iterations of the
# pipeline. Not used in the current dashboard.
CLI_WEIGHT_PUPIL   = 0.40
CLI_WEIGHT_FIX_DUR = 0.30
CLI_WEIGHT_BLINK   = 0.15
CLI_WEIGHT_SACC    = 0.15
CLI_WINDOW_S       = 30
CLI_STEP_S         = 10


# ── Origin grouping ──────────────────────────────────────────────────────────
# Maps country → cultural/linguistic proximity group relative to Portuguese
# VDW. Extend here when a new origin appears.
ORIGIN_GROUPS = {
    "Native",
    "Non-Native",
    }


def origin_group(origin: str) -> str:
    return ORIGIN_GROUPS.get(origin, "Other")


# ── Visual palette ───────────────────────────────────────────────────────────
# Colours match the dashboard template. Add categories here when adding new
# event types.
CATEGORY_COLORS = {
    "signage":   "#2a78d6",
    "drop":      "#eb6834",
    "rearrange": "#1baf7a",
    "repallet":  "#eda100",
    "extra":     "#e87ba4",
    "work":      "#008300",
    "label":     "#4a3aa7",
    "sticker":   "#7f77dd",
    "movepallete":"#0f6e56",
    "foil":      "#c98500",
    "pause":     "#a32d2d",
    "conversion":"#7c0c3a",
    "print":     "#5f5e5a",
    "other":     "#898781",
}

SEX_COLORS = {
    "M": "#185FA5",
    "F": "#D4537E",
}
