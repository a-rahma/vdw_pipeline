"""
viz/dashboard.py — Generate per-participant HTML dashboards.

Reads the template at viz/templates/dashboard.html and populates it with:

* Header title / participant name
* Embedded JSON payload matching the schema the template's JavaScript consumes:

    {
      "summary":  {participant, recDur, workDur, totBlk, totFix, totSacc,
                    meanFixMs, medFixMs, meanBlkMs, blkRatePerMin,
                    fixRatePerMin, nSignage, nDrop, nRearrange, nRepallet,
                    gridW, gridH},
      "segments": [ {i, name, occ, cat, num, t0, dur, blk, blkRate, fix,
                      fixRate, fixMs, fixPct, sacc, saccAmp, gzN, gxSd, gySd,
                      gxM, gyM, worn, heat}, ... ]
    }

The dashboard file is fully self-contained: it embeds the JSON in a
<script type="application/json"> tag and contains all CSS/JS inline. No
network or server needed to view.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

from ..config import GRID_W, GRID_H, DASHBOARDS_DIR
from ..metrics.segments import build_segments

TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"


def _human_pid(pid: str) -> str:
    """A1 → 'A1' for display (underscores, if present, become spaces)."""
    return pid.replace("_", " ")


def _safe_pid(pid: str) -> str:
    """A1 → 'a1' for HTML/JS ids (no underscore/space)."""
    return pid.lower().replace("_", "").replace(" ", "")


def build_summary(data: dict, segments: list[dict]) -> dict:
    """
    Assemble the top-level summary dict expected by the dashboard template.
    """
    fix       = data.get("fixations", pd.DataFrame())
    blinks    = data.get("blinks",    pd.DataFrame())
    saccades  = data.get("saccades",  pd.DataFrame())
    events    = data.get("events",    pd.DataFrame())
    dur_s     = data.get("duration_s", 0.0)

    fix_d = pd.to_numeric(fix.get("duration_ms", pd.Series()), errors="coerce").dropna()
    blk_d = pd.to_numeric(blinks.get("duration_ms", pd.Series()), errors="coerce").dropna()

    # Work duration from work_start / work_end if present
    work_dur = None
    if not events.empty:
        ws = events.loc[events["name"] == "work_start", "time_s"]
        we = events.loc[events["name"] == "work_end",   "time_s"]
        if len(ws) and len(we):
            work_dur = float(we.iloc[0]) - float(ws.iloc[0])

    # Event category counts (using dashboard's short codes)
    n_by_cat = {"signage": 0, "drop": 0, "rearrange": 0, "repallet": 0}
    for seg in segments:
        cat = seg.get("cat")
        if cat in n_by_cat:
            n_by_cat[cat] += 1

    return {
        "participant":   _human_pid(data.get("pid", "")),
        "recDur":        round(float(dur_s), 1),
        "workDur":       round(float(work_dur), 1) if work_dur else round(float(dur_s), 1),
        "totBlk":        int(len(blinks)),
        "totFix":        int(len(fix_d)),
        "totSacc":       int(len(saccades)),
        "meanFixMs":     round(float(fix_d.mean()), 1) if len(fix_d) else 0.0,
        "medFixMs":      round(float(fix_d.median()), 1) if len(fix_d) else 0.0,
        "meanBlkMs":     round(float(blk_d.mean()), 1) if len(blk_d) else 0.0,
        "blkRatePerMin": round(len(blinks) / (dur_s / 60), 1) if dur_s > 0 else 0.0,
        "fixRatePerMin": round(len(fix_d) / (dur_s / 60), 1) if dur_s > 0 else 0.0,
        "nSignage":      n_by_cat["signage"],
        "nDrop":         n_by_cat["drop"],
        "nRearrange":    n_by_cat["rearrange"],
        "nRepallet":     n_by_cat["repallet"],
        "gridW":         GRID_W,
        "gridH":         GRID_H,
    }


def _sanitise_for_json(obj):
    """Recursively replace NaN, ±inf with None so json.dumps stays strict."""
    if isinstance(obj, dict):
        return {k: _sanitise_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitise_for_json(v) for v in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (np.isnan(f) or np.isinf(f)) else f
    return obj


def build_dashboard_payload(data: dict) -> dict:
    """Assemble the full JSON payload the dashboard template consumes."""
    segments = build_segments(data)
    summary  = build_summary(data, segments)
    return {"summary": summary, "segments": segments}


def render_dashboard(pid: str, data: dict,
                      out_dir: Path = DASHBOARDS_DIR) -> Path:
    """
    Render one participant's dashboard to an HTML file. Returns the path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_payload(data)
    payload = _sanitise_for_json(payload)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = (template
             .replace("{{PID_DISPLAY}}", _human_pid(pid))
             .replace("{{PID_SAFE}}",    _safe_pid(pid))
             .replace("__DATA_JSON__",   json.dumps(payload, ensure_ascii=False)))

    out_path = out_dir / f"{pid}_dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
