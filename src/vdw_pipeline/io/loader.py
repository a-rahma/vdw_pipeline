"""
io/loader.py — Read Pupil Labs Neon export folders into pandas DataFrames.

Pupil Cloud raw-data-exporter (v2) writes one folder per recording containing
CSV files with ns-since-epoch timestamps. This module:

1. Discovers participant folders matching PARTICIPANT_GLOB in data/raw/
2. Handles two nesting patterns seen in exports:
     data/raw/A_N/<csvs>              (flat)
     data/raw/A_N/A_N/<csvs>      (double-nested — some Cloud exports)
     data/raw/A_N/<date-uuid>/<csvs>  (timestamped subfolder)
3. Normalises timestamps to seconds since recording.begin
4. Renames Pupil Labs' bracket-suffix columns to snake_case
5. Applies quality gates from config.py

Loads are read-only; no side effects. Every returned DataFrame is a fresh
in-memory object.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

from ..config import (
    RAW_DIR, PARTICIPANT_GLOB,
    FIXATION_MIN_DURATION_MS, FIXATION_MAX_DURATION_MS,
    BLINK_MIN_DURATION_MS, BLINK_MAX_DURATION_MS,
    PUPIL_MIN_MM, PUPIL_MAX_MM,
)


# ── Discovery ────────────────────────────────────────────────────────────────

def find_data_root(participant_folder: Path) -> Path:
    """
    Return the folder that actually contains gaze.csv.

    Pupil Cloud exports sometimes nest the CSVs one or two levels deep
    (e.g. A_N/A_N/, A_N/<date-uuid>/). We search until we
    find gaze.csv.
    """
    if not participant_folder.is_dir():
        raise FileNotFoundError(f"Not a directory: {participant_folder}")
    if (participant_folder / "gaze.csv").exists():
        return participant_folder
    matches = list(participant_folder.rglob("gaze.csv"))
    if matches:
        # Prefer the shallowest match if there are several
        matches.sort(key=lambda p: len(p.parts))
        return matches[0].parent
    raise FileNotFoundError(
        f"No gaze.csv found under {participant_folder}. "
        "Verify this is a Pupil Labs Neon export folder."
    )


def discover_participants(raw_dir: Path = RAW_DIR) -> dict[str, Path]:
    """
    Return {participant_id: data_folder} for every valid participant export.

    Case-insensitive on the participant folder name; data_folder is the
    inner directory that actually contains the CSV files.
    """
    result: dict[str, Path] = {}
    if not raw_dir.exists():
        return result
    for folder in sorted(raw_dir.glob(PARTICIPANT_GLOB)):
        if not folder.is_dir():
            continue
        try:
            data_root = find_data_root(folder)
            result[folder.name] = data_root
        except FileNotFoundError:
            continue
    return result


# ── Time helpers ─────────────────────────────────────────────────────────────

def _ns_to_s(series: pd.Series, t0_ns: float) -> pd.Series:
    """Convert nanosecond timestamps to seconds relative to t0_ns."""
    return (series - t0_ns) / 1e9


def _recording_bounds(data_root: Path) -> tuple[float, float]:
    """
    Return (t0_ns, t_end_ns) for the recording.

    Preference order: gaze.csv > world_timestamps.csv > events.csv.

    gaze.csv is preferred because it is sampled continuously at 100 Hz and
    is never hand-edited. events.csv, by contrast, is sometimes opened and
    re-saved in a spreadsheet application, which can silently truncate
    timestamp precision (see _read_events_csv) badly enough that
    recording.begin and recording.end round to the same value. Using
    gaze.csv as the primary source avoids that failure mode entirely;
    events.csv is still used for the event *log* itself (load_events),
    just not for the authoritative recording span.
    """
    gaze_path = data_root / "gaze.csv"
    if gaze_path.exists():
        g = _robust_read_csv(gaze_path)
        if "timestamp [ns]" in g.columns and not g.empty:
            ts = pd.to_numeric(g["timestamp [ns]"], errors="coerce").dropna()
            if len(ts) and (ts.max() - ts.min()) > 0:
                return float(ts.min()), float(ts.max())

    wt_path = data_root / "world_timestamps.csv"
    if wt_path.exists():
        wt = _robust_read_csv(wt_path)
        if not wt.empty:
            ts = pd.to_numeric(wt.iloc[:, 0], errors="coerce").dropna()
            if len(ts) and (ts.max() - ts.min()) > 0:
                return float(ts.min()), float(ts.max())

    ev_path = data_root / "events.csv"
    if ev_path.exists():
        ev = _read_events_csv(ev_path)
        if "timestamp [ns]" in ev.columns and not ev.empty:
            begin = ev.loc[ev["name"] == "recording.begin", "timestamp [ns]"]
            end   = ev.loc[ev["name"] == "recording.end",   "timestamp [ns]"]
            t0 = float(begin.iloc[0]) if len(begin) else float(ev["timestamp [ns]"].min())
            te = float(end.iloc[0])   if len(end)   else float(ev["timestamp [ns]"].max())
            return t0, te

    raise ValueError(f"Cannot determine recording bounds in {data_root}")


# ── Per-file loaders ────────────────────────────────────────────────────────

_ID_LIKE_COLUMNS = {
    "section id", "recording id", "name", "type",
    "fixation id", "blink id", "saccade id",
}


def _robust_read_csv(path: Path) -> pd.DataFrame:
    """
    Read a Pupil Labs CSV, tolerating a common field-data corruption: the
    file was opened and re-saved in a spreadsheet application under a
    non-English locale (observed: pt-BR/pt-PT), which silently:

      * changes the field delimiter from ',' to ';'
      * changes the decimal separator from '.' to ','
      * for numbers with many digits, sometimes inserts additional '.'
        characters at thousands-like intervals, e.g. a value that should
        read -22.9583901229847 becomes the string "-22.958.390.122.984.700"

    The first two corruptions are fully recoverable. The third is only
    partially recoverable — high-precision columns (observed: azimuth/
    elevation) end up mostly unparseable and are coerced to NaN rather
    than silently used as garbage. Lower-precision columns (gaze x/y in
    pixels, timestamps in the affected files) survive largely intact
    because they have too few digits to trigger the extra-separator bug.

    Strategy
    --------
    1. Try a standard comma-delimited read.
    2. If that raises a ParserError (ragged rows — the tell-tale sign of
       comma-as-decimal inside a comma-delimited file) or produces a
       DataFrame missing an expected structure, retry with
       sep=';', decimal=','.
    3. After a successful read, coerce every column that is not in
       _ID_LIKE_COLUMNS to numeric with errors='coerce'. Cells that
       survived the repair become floats; cells still mangled become NaN.
       Downstream code already treats NaN as missing, so this degrades
       gracefully rather than crashing or silently propagating corrupted
       values.

    Any participant for which this repair path is used is exactly the
    kind of data-quality event worth flagging in a methods section: it
    means someone opened a raw export by hand. Callers that care (see
    load_events) print an explicit warning; this function stays silent
    for the high-volume signal files (gaze, fixations, etc.) since a
    partial-NaN column here does not invalidate the whole participant.
    """
    try:
        df = pd.read_csv(path)
        looks_ok = df.shape[1] > 1
    except pd.errors.ParserError:
        df = None
        looks_ok = False

    if not looks_ok:
        df = pd.read_csv(path, sep=";", decimal=",")

    for col in df.columns:
        if col in _ID_LIKE_COLUMNS:
            continue
        coerced = pd.to_numeric(df[col], errors="coerce")
        # Only replace if coercion actually produced usable numbers;
        # a column that's genuinely non-numeric (shouldn't occur here,
        # but defensively) is left untouched.
        if coerced.notna().any():
            df[col] = coerced
    return df


def _read(data_root: Path, name: str) -> pd.DataFrame:
    p = data_root / f"{name}.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return _robust_read_csv(p)
    except Exception:
        return pd.DataFrame()


def _read_events_csv(path: Path) -> pd.DataFrame:
    """events.csv has a `name` column that must stay as text; reuse the
    shared robust reader, which already protects columns in
    _ID_LIKE_COLUMNS (includes 'name') from numeric coercion."""
    df = _robust_read_csv(path)
    if "timestamp [ns]" not in df.columns:
        raise ValueError(
            f"{path} is not a recognised Pupil Labs events export "
            "(missing 'timestamp [ns]' column even after delimiter repair). "
            "The file may have been edited by hand; check it manually."
        )
    return df


def load_events(data_root: Path, t0_ns: float,
                 expected_duration_s: float | None = None) -> pd.DataFrame:
    """
    Load events.csv and add a `time_s` column (relative to recording.begin).

    If `expected_duration_s` is given (normally the gaze-based recording
    span from _recording_bounds), sanity-check the parsed event timeline
    against it. A hand-edited events.csv that was corrupted by Excel's
    locale conversion (see _read_events_csv) can still parse successfully
    while losing enough precision that recording.begin/recording.end land
    within seconds of each other despite a session lasting 20+ minutes. In
    that case the event log is unusable for per-event analysis: we return
    an empty DataFrame and let the caller fall back to session-level
    metrics (which come from fixations.csv/blinks.csv/gaze.csv and are
    unaffected by this corruption).
    """
    p = data_root / "events.csv"
    if not p.exists():
        return pd.DataFrame()
    df = _read_events_csv(p)
    if df.empty:
        return df
    df["time_s"] = _ns_to_s(df["timestamp [ns]"], t0_ns).round(3)
    df["name"]   = df["name"].astype(str).str.strip()
    df = df.sort_values("time_s").reset_index(drop=True)

    if expected_duration_s and expected_duration_s > 0:
        begin = df.loc[df["name"] == "recording.begin", "time_s"]
        end   = df.loc[df["name"] == "recording.end",   "time_s"]
        if len(begin) and len(end):
            parsed_span = float(end.iloc[0]) - float(begin.iloc[0])
            # Allow generous tolerance (50%) — this only needs to catch
            # gross corruption (spans collapsing to ~0, or wildly exceeding
            # the true duration), not flag minor clock drift.
            if parsed_span <= 0 or abs(parsed_span - expected_duration_s) > 0.5 * expected_duration_s:
                print(f"   WARNING: {p.name} timestamps inconsistent with "
                      f"gaze-based duration ({parsed_span:.1f}s parsed vs "
                      f"{expected_duration_s:.1f}s expected). Likely locale "
                      f"corruption from re-saving in Excel. Event log discarded; "
                      f"falling back to session-level metrics only. "
                      f"Re-export events.csv from Pupil Cloud to restore "
                      f"per-behaviour analysis for this participant.")
                return pd.DataFrame()
    return df


def load_gaze(data_root: Path, t0_ns: float) -> pd.DataFrame:
    """
    Load gaze.csv. Returns columns: time_s, gaze_x, gaze_y, worn (if present),
    fixation_id, blink_id, azimuth_deg, elevation_deg.
    """
    df = _read(data_root, "gaze")
    if df.empty:
        return df
    df["time_s"] = _ns_to_s(df["timestamp [ns]"], t0_ns)
    rename = {
        "gaze x [px]":     "gaze_x",
        "gaze y [px]":     "gaze_y",
        "worn":            "worn",
        "fixation id":     "fixation_id",
        "blink id":        "blink_id",
        "azimuth [deg]":   "azimuth_deg",
        "elevation [deg]": "elevation_deg",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    keep = [c for c in ["time_s", "gaze_x", "gaze_y", "worn",
                         "fixation_id", "blink_id", "azimuth_deg", "elevation_deg"]
            if c in df.columns]
    return df[keep].reset_index(drop=True)


def load_fixations(data_root: Path, t0_ns: float) -> pd.DataFrame:
    """
    Load fixations.csv with quality gate (FIXATION_MIN/MAX_DURATION_MS).

    Returns start_s, end_s, duration_ms, centroid_x, centroid_y, azimuth_deg,
    elevation_deg (columns present depend on Pupil Labs firmware version).
    """
    df = _read(data_root, "fixations")
    if df.empty:
        return df
    df["start_s"] = _ns_to_s(df["start timestamp [ns]"], t0_ns)
    if "end timestamp [ns]" in df.columns:
        df["end_s"] = _ns_to_s(df["end timestamp [ns]"], t0_ns)
    elif "duration [ms]" in df.columns:
        df["end_s"] = df["start_s"] + df["duration [ms]"] / 1000.0
    else:
        df["end_s"] = df["start_s"]
    rename = {
        "fixation id":     "fixation_id",
        "duration [ms]":   "duration_ms",
        "fixation x [px]": "centroid_x",
        "fixation y [px]": "centroid_y",
        "azimuth [deg]":   "azimuth_deg",
        "elevation [deg]": "elevation_deg",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df = df[df["duration_ms"].between(
        FIXATION_MIN_DURATION_MS, FIXATION_MAX_DURATION_MS
    )].reset_index(drop=True)
    keep = [c for c in ["fixation_id", "start_s", "end_s", "duration_ms",
                         "centroid_x", "centroid_y", "azimuth_deg", "elevation_deg"]
            if c in df.columns]
    return df[keep]


def load_blinks(data_root: Path, t0_ns: float) -> pd.DataFrame:
    """Load blinks.csv with quality gate (BLINK_MIN/MAX_DURATION_MS)."""
    df = _read(data_root, "blinks")
    if df.empty:
        return df
    df["onset_s"] = _ns_to_s(df["start timestamp [ns]"], t0_ns)
    if "end timestamp [ns]" in df.columns:
        df["offset_s"] = _ns_to_s(df["end timestamp [ns]"], t0_ns)
    elif "duration [ms]" in df.columns:
        df["offset_s"] = df["onset_s"] + df["duration [ms]"] / 1000.0
    else:
        df["offset_s"] = df["onset_s"]
    rename = {"blink id": "blink_id", "duration [ms]": "duration_ms"}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df = df[df["duration_ms"].between(
        BLINK_MIN_DURATION_MS, BLINK_MAX_DURATION_MS
    )].reset_index(drop=True)
    keep = [c for c in ["blink_id", "onset_s", "offset_s", "duration_ms"] if c in df.columns]
    return df[keep]


def load_saccades(data_root: Path, t0_ns: float) -> pd.DataFrame:
    """Load saccades.csv. No quality gate applied; report as-detected by Neon."""
    df = _read(data_root, "saccades")
    if df.empty:
        return df
    df["start_s"] = _ns_to_s(df["start timestamp [ns]"], t0_ns)
    if "end timestamp [ns]" in df.columns:
        df["end_s"] = _ns_to_s(df["end timestamp [ns]"], t0_ns)
    elif "duration [ms]" in df.columns:
        df["end_s"] = df["start_s"] + df["duration [ms]"] / 1000.0
    else:
        df["end_s"] = df["start_s"]
    rename = {
        "saccade id":          "saccade_id",
        "duration [ms]":       "duration_ms",
        "amplitude [px]":      "amplitude_px",
        "amplitude [deg]":     "amplitude_deg",
        "mean velocity [px/s]":"mean_velocity_px_s",
        "peak velocity [px/s]":"peak_velocity_px_s",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    keep = [c for c in ["saccade_id", "start_s", "end_s", "duration_ms",
                         "amplitude_px", "amplitude_deg",
                         "mean_velocity_px_s", "peak_velocity_px_s"]
            if c in df.columns]
    return df[keep]


def load_eye_states(data_root: Path, t0_ns: float) -> pd.DataFrame:
    """Load 3d_eye_states.csv (pupil diameter). Not used in v1 dashboards."""
    df = _read(data_root, "3d_eye_states")
    if df.empty:
        return df
    df["time_s"] = _ns_to_s(df["timestamp [ns]"], t0_ns)
    rename = {
        "pupil diameter left [mm]":   "pupil_l_mm",
        "pupil diameter right [mm]":  "pupil_r_mm",
        "eyelid aperture left [mm]":  "eyelid_l_mm",
        "eyelid aperture right [mm]": "eyelid_r_mm",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ("pupil_l_mm", "pupil_r_mm"):
        if col in df.columns:
            df.loc[~df[col].between(PUPIL_MIN_MM, PUPIL_MAX_MM), col] = np.nan
    keep = [c for c in ["time_s", "pupil_l_mm", "pupil_r_mm",
                         "eyelid_l_mm", "eyelid_r_mm"] if c in df.columns]
    return df[keep].reset_index(drop=True)


# ── Public API ──────────────────────────────────────────────────────────────

def load_participant(pid: str, folder: Path) -> dict:
    """
    Load all signal files for one participant.

    Returns a dict with keys:
      pid, data_root, t0_ns, duration_s, info,
      gaze, fixations, saccades, blinks, eye_states, events
    """
    data_root = find_data_root(folder) if folder.is_dir() else folder
    t0_ns, t_end_ns = _recording_bounds(data_root)
    duration_s      = (t_end_ns - t0_ns) / 1e9

    info_path = data_root / "info.json"
    info      = json.load(open(info_path)) if info_path.exists() else {}

    return {
        "pid":         pid,
        "data_root":   data_root,
        "t0_ns":       t0_ns,
        "duration_s":  duration_s,
        "info":        info,
        "gaze":        load_gaze(data_root, t0_ns),
        "fixations":   load_fixations(data_root, t0_ns),
        "saccades":    load_saccades(data_root, t0_ns),
        "blinks":      load_blinks(data_root, t0_ns),
        "eye_states":  load_eye_states(data_root, t0_ns),
        "events":      load_events(data_root, t0_ns, expected_duration_s=duration_s),
    }


def load_participant_metadata(csv_path: Path = None) -> pd.DataFrame:
    """
    Load participants.csv → DataFrame indexed by et_code.

    Returns empty DataFrame with the expected schema if the file is missing.
    """
    from ..config import PARTICIPANTS_CSV
    if csv_path is None:
        csv_path = PARTICIPANTS_CSV
    cols = ["et_code", "pseudonym", "code", "interview_code", "breakdown_code",
             "sex", "location", "origin", "experience", "track"]
    if not csv_path.exists():
        return pd.DataFrame(columns=cols).set_index("et_code")
    df = pd.read_csv(csv_path)
    missing = [c for c in cols if c not in df.columns]
    for c in missing:
        df[c] = ""
    return df.set_index("et_code")
