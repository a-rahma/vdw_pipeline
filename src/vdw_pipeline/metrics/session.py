"""
metrics/session.py — Session-level (whole-recording) summary per participant.

Focuses on the three metric families the paper reports:
  * Fixation duration (mean, median, SD, count, rate, short/long %)
  * Blink rate + duration
  * Gaze coverage (% valid, scene-camera spread)

Output is a flat dict — one row per participant — suitable for concatenation
into a group table.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from ..config import FIX_SHORT_MS, FIX_LONG_MS


def _safe_mean(s):
    v = pd.to_numeric(s, errors="coerce").dropna()
    return float(v.mean()) if len(v) else np.nan

def _safe_sd(s):
    v = pd.to_numeric(s, errors="coerce").dropna()
    return float(v.std()) if len(v) > 1 else np.nan

def _safe_med(s):
    v = pd.to_numeric(s, errors="coerce").dropna()
    return float(v.median()) if len(v) else np.nan


def session_summary(pid: str, data: dict, meta: dict | None = None) -> dict:
    """
    Compute session-level metrics for one participant.

    Args
    ----
    pid  : participant ID (e.g. 'A1')
    data : dict returned by loader.load_participant()
    meta : dict-like from participants.csv row (optional; adds profile columns)

    Returns
    -------
    dict with keys documented in docs/data_dictionary.md
    """
    meta = meta or {}
    dur_s   = data.get("duration_s", 0.0)
    fix     = data.get("fixations", pd.DataFrame())
    blinks  = data.get("blinks",    pd.DataFrame())
    saccades = data.get("saccades", pd.DataFrame())
    gaze    = data.get("gaze",      pd.DataFrame())

    # Fixation metrics
    fix_d = pd.to_numeric(fix.get("duration_ms", pd.Series()), errors="coerce").dropna()
    fix_metrics = {
        "n_fixations":       int(len(fix_d)),
        "mean_fix_ms":       round(_safe_mean(fix_d), 2),
        "median_fix_ms":     round(_safe_med(fix_d),  2),
        "sd_fix_ms":         round(_safe_sd(fix_d),   2),
        "fixation_rate_per_min":
            round(len(fix_d) / (dur_s / 60), 2) if dur_s > 0 else np.nan,
        "pct_short_fix":     round(float((fix_d < FIX_SHORT_MS).mean() * 100), 1) if len(fix_d) else np.nan,
        "pct_long_fix":      round(float((fix_d > FIX_LONG_MS).mean() * 100), 1)  if len(fix_d) else np.nan,
        "total_dwell_s":     round(float(fix_d.sum()) / 1000, 2) if len(fix_d) else np.nan,
    }

    # Blink metrics
    bd = pd.to_numeric(blinks.get("duration_ms", pd.Series()), errors="coerce").dropna()
    blink_metrics = {
        "n_blinks":           int(len(blinks)),
        "blink_rate_per_min": round(len(blinks) / (dur_s / 60), 2) if dur_s > 0 else np.nan,
        "mean_blink_ms":      round(_safe_mean(bd), 1) if len(bd) else np.nan,
        "sd_blink_ms":        round(_safe_sd(bd),   1) if len(bd) > 1 else np.nan,
    }

    # Saccade metrics
    sacc_metrics = {"n_saccades": int(len(saccades))}
    if "amplitude_deg" in saccades.columns:
        a = pd.to_numeric(saccades["amplitude_deg"], errors="coerce").dropna()
        sacc_metrics["mean_sacc_amp_deg"] = round(_safe_mean(a), 2)
        sacc_metrics["sd_sacc_amp_deg"]   = round(_safe_sd(a),   2)
    else:
        sacc_metrics["mean_sacc_amp_deg"] = np.nan
        sacc_metrics["sd_sacc_amp_deg"]   = np.nan

    # Gaze "worn" percentage (device-on-face)
    worn_pct = np.nan
    if not gaze.empty and "worn" in gaze.columns:
        w = pd.to_numeric(gaze["worn"], errors="coerce").dropna()
        if len(w):
            worn_pct = round(float(w.mean()) * 100, 1)

    profile_cols = {
        "pseudonym":      meta.get("pseudonym", ""),
        "sex":            meta.get("sex", ""),
        "location":       meta.get("location", ""),
        "origin":         meta.get("origin", ""),
        "experience":     meta.get("experience", ""),
        "breakdown_code": meta.get("breakdown_code", ""),
        "track":          meta.get("track", ""),
    }

    return {
        "participant_id":   pid,
        **profile_cols,
        "duration_s":       round(dur_s, 1),
        "duration_min":     round(dur_s / 60, 2),
        "worn_pct":         worn_pct,
        **fix_metrics,
        **blink_metrics,
        **sacc_metrics,
    }
