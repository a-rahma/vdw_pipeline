"""
preprocessing/gaze.py — Gaze quality and spatial aggregation.

Two functions:

* gaze_heatmap: bin gaze samples in a window into a GRID_W × GRID_H grid
  (matching the scene camera aspect ratio) for the dashboard visualization.
* gaze_summary: compute mean, SD, and worn-percentage for gaze in a window.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from ..config import GRID_W, GRID_H, SCENE_WIDTH_PX, SCENE_HEIGHT_PX


def gaze_heatmap(gaze: pd.DataFrame,
                  t_start: float,
                  t_end: float,
                  grid_w: int = GRID_W,
                  grid_h: int = GRID_H) -> list[list[int]]:
    """
    Bin gaze samples in [t_start, t_end] into a grid_w × grid_h grid.

    Returns a list of [col, row, count] triples for occupied cells only
    (sparse representation matches the dashboard's JSON schema).

    Bin index formula:
        col = floor(gaze_x / SCENE_WIDTH_PX  * grid_w)
        row = floor(gaze_y / SCENE_HEIGHT_PX * grid_h)
    Samples with NaN or off-canvas coordinates are dropped.
    """
    if gaze.empty or "gaze_x" not in gaze.columns:
        return []
    mask = (gaze["time_s"] >= t_start) & (gaze["time_s"] < t_end)
    sub  = gaze.loc[mask, ["gaze_x", "gaze_y"]].dropna()
    if sub.empty:
        return []
    cols = np.floor(sub["gaze_x"].values / SCENE_WIDTH_PX  * grid_w).astype(int)
    rows = np.floor(sub["gaze_y"].values / SCENE_HEIGHT_PX * grid_h).astype(int)
    valid = (cols >= 0) & (cols < grid_w) & (rows >= 0) & (rows < grid_h)
    if not valid.any():
        return []
    cols, rows = cols[valid], rows[valid]
    # Count occurrences per (col, row) cell
    flat = cols * grid_h + rows
    counts = np.bincount(flat)
    result = []
    for idx, c in enumerate(counts):
        if c == 0:
            continue
        col, row = idx // grid_h, idx % grid_h
        result.append([int(col), int(row), int(c)])
    return result


def gaze_summary(gaze: pd.DataFrame,
                  t_start: float,
                  t_end: float) -> dict:
    """
    Compute mean, SD, sample count and worn-percentage for gaze in a window.

    Returns dict with keys: gz_n, gx_m, gy_m, gx_sd, gy_sd, worn_pct.
    """
    if gaze.empty:
        return dict(gz_n=0, gx_m=np.nan, gy_m=np.nan,
                    gx_sd=np.nan, gy_sd=np.nan, worn_pct=np.nan)
    mask = (gaze["time_s"] >= t_start) & (gaze["time_s"] < t_end)
    sub  = gaze.loc[mask]
    if sub.empty:
        return dict(gz_n=0, gx_m=np.nan, gy_m=np.nan,
                    gx_sd=np.nan, gy_sd=np.nan, worn_pct=np.nan)

    gx = pd.to_numeric(sub["gaze_x"], errors="coerce").dropna()
    gy = pd.to_numeric(sub["gaze_y"], errors="coerce").dropna()

    worn = np.nan
    if "worn" in sub.columns:
        worn_series = pd.to_numeric(sub["worn"], errors="coerce").dropna()
        if len(worn_series):
            # `worn` is 0 or 1 per sample in Neon exports
            worn = round(float(worn_series.mean()) * 100, 1)

    return dict(
        gz_n=int(len(sub)),
        gx_m=round(float(gx.mean()), 2)  if len(gx) else np.nan,
        gy_m=round(float(gy.mean()), 2)  if len(gy) else np.nan,
        gx_sd=round(float(gx.std()), 1)  if len(gx) > 1 else np.nan,
        gy_sd=round(float(gy.std()), 1)  if len(gy) > 1 else np.nan,
        worn_pct=worn,
    )
