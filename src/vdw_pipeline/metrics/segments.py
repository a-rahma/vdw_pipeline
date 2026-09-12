"""
metrics/segments.py — Per-event windowed metrics.

For each event *e_i* in events.csv, gaze metrics are aggregated over
[t(e_i), t(e_{i+1})]. This event-anchored windowing (as opposed to fixed
±2 s windows) means:

  * the window matches the true duration of the behaviour episode
  * windows do not overlap
  * signage events (long dwell) get long windows;
    drop events (brief) get short windows

Output schema matches the JSON consumed by the HTML dashboard template
(see viz/dashboard.py for the field mapping).
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

from ..io.events import classify_event
from ..preprocessing.gaze import gaze_heatmap, gaze_summary


def _fix_in_window(fixations: pd.DataFrame, t0: float, t1: float) -> pd.DataFrame:
    if fixations.empty or "start_s" not in fixations.columns:
        return pd.DataFrame(columns=fixations.columns)
    return fixations[fixations["start_s"].between(t0, t1)]

def _blinks_in_window(blinks: pd.DataFrame, t0: float, t1: float) -> pd.DataFrame:
    if blinks.empty or "onset_s" not in blinks.columns:
        return pd.DataFrame(columns=blinks.columns)
    return blinks[blinks["onset_s"].between(t0, t1)]

def _sacc_in_window(saccades: pd.DataFrame, t0: float, t1: float) -> pd.DataFrame:
    if saccades.empty or "start_s" not in saccades.columns:
        return pd.DataFrame(columns=saccades.columns)
    return saccades[saccades["start_s"].between(t0, t1)]

def _extract_num(name: str) -> int | None:
    if not name:
        return None
    m = re.search(r"(\d+)", str(name))
    return int(m.group(1)) if m else None


def build_segments(data: dict) -> list[dict]:
    """
    Build the per-event segment list for one participant.

    Args
    ----
    data : dict returned by loader.load_participant()

    Returns
    -------
    list of segment dicts, one per event. Fields match the dashboard's
    expected JSON schema (see viz/dashboard.py).

    Notes
    -----
    * Events with the same base name are numbered by occurrence order
      (`occ`), so signage_5 appearing twice becomes occ=1 and occ=2.
    * If no events other than recording bounds are present, returns a
      single segment covering the whole recording.
    """
    events    = data.get("events", pd.DataFrame())
    fixations = data.get("fixations", pd.DataFrame())
    blinks    = data.get("blinks",    pd.DataFrame())
    saccades  = data.get("saccades",  pd.DataFrame())
    gaze      = data.get("gaze",      pd.DataFrame())
    duration  = data.get("duration_s", 0.0)

    # Filter out recording bounds (they aren't behavioural events)
    if not events.empty:
        ev = events[~events["name"].isin(["recording.begin", "recording.end"])]
        ev = ev.sort_values("time_s").reset_index(drop=True)
    else:
        ev = pd.DataFrame()

    if ev.empty:
        # No behavioural events — return single "session" segment
        return [_build_segment(
            idx=0, name="session", occ=1, cat="other",
            t0=0.0, t1=duration,
            fixations=fixations, blinks=blinks, saccades=saccades, gaze=gaze,
        )]

    # Number occurrences of each event name
    ev["occ"] = ev.groupby("name").cumcount() + 1

    segments = []
    for i in range(len(ev)):
        row = ev.iloc[i]
        t0  = float(row["time_s"])
        t1  = float(ev.iloc[i + 1]["time_s"]) if i + 1 < len(ev) else duration
        if t1 <= t0:
            t1 = t0 + 0.001   # avoid zero-length windows

        cat, _, _ = classify_event(row["name"])
        # "work"/"other" fold protocol/unclassified markers into the
        # dashboard's neutral colour bucket.
        if cat in ("protocol", "unclassified"):
            cat = "work" if str(row["name"]).lower().startswith(("work", "recording")) else "other"

        segments.append(_build_segment(
            idx=i, name=str(row["name"]), occ=int(row["occ"]),
            cat=cat,
            t0=t0, t1=t1,
            fixations=fixations, blinks=blinks, saccades=saccades, gaze=gaze,
        ))
    return segments


def _build_segment(idx: int, name: str, occ: int, cat: str,
                    t0: float, t1: float,
                    fixations: pd.DataFrame,
                    blinks: pd.DataFrame,
                    saccades: pd.DataFrame,
                    gaze: pd.DataFrame) -> dict:
    """Build a single segment record with all metrics + heatmap."""
    dur = t1 - t0
    f = _fix_in_window(fixations, t0, t1)
    b = _blinks_in_window(blinks,  t0, t1)
    s = _sacc_in_window(saccades,  t0, t1)

    # Fixation metrics
    fix_ms   = float(f["duration_ms"].mean()) if len(f) else np.nan
    fix_pct  = round(float(f["duration_ms"].sum()) / (dur * 1000) * 100, 1) \
                if dur > 0 and len(f) else np.nan
    fix_rate = round(len(f) / (dur / 60), 1) if dur > 0 else np.nan

    # Blink metrics
    blk_rate = round(len(b) / (dur / 60), 1) if dur > 0 else np.nan

    # Saccade metrics
    sacc_amp = np.nan
    if len(s) and "amplitude_deg" in s.columns:
        amp = pd.to_numeric(s["amplitude_deg"], errors="coerce").dropna()
        if len(amp):
            sacc_amp = round(float(amp.mean()), 2)

    # Gaze summary + heatmap
    g_stat = gaze_summary(gaze, t0, t1)
    heat   = gaze_heatmap(gaze, t0, t1)

    n_num = _extract_num(name)

    return dict(
        i=int(idx),
        name=name,
        occ=int(occ),
        cat=cat,
        num=n_num,
        t0=round(float(t0), 1),
        dur=round(float(dur), 1),
        blk=int(len(b)),
        blkRate=blk_rate,
        fix=int(len(f)),
        fixRate=fix_rate,
        fixMs=round(fix_ms, 1) if not np.isnan(fix_ms) else None,
        fixPct=fix_pct if not (isinstance(fix_pct, float) and np.isnan(fix_pct)) else None,
        sacc=int(len(s)),
        saccAmp=sacc_amp if not np.isnan(sacc_amp) else None,
        gzN=int(g_stat["gz_n"]),
        gxSd=g_stat["gx_sd"] if not (isinstance(g_stat["gx_sd"], float) and np.isnan(g_stat["gx_sd"])) else None,
        gySd=g_stat["gy_sd"] if not (isinstance(g_stat["gy_sd"], float) and np.isnan(g_stat["gy_sd"])) else None,
        gxM=g_stat["gx_m"]   if not (isinstance(g_stat["gx_m"],  float) and np.isnan(g_stat["gx_m"]))  else None,
        gyM=g_stat["gy_m"]   if not (isinstance(g_stat["gy_m"],  float) and np.isnan(g_stat["gy_m"]))  else None,
        worn=g_stat["worn_pct"] if not (isinstance(g_stat["worn_pct"], float) and np.isnan(g_stat["worn_pct"])) else None,
        heat=heat,
    )
