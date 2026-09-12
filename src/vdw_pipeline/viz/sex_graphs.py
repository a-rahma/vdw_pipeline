"""
viz/sex_graphs.py — Group-level summary figures (matplotlib PNG).

Produces:
  * sex_differences_fixation.png  — three-panel: mean fix, median fix, fix rate
  * sex_differences_blink.png     — two-panel: blink rate, blink duration
  * sex_differences_gaze.png      — one-panel: worn %, mean saccade amp
  * origin_group_means.png        — 4-panel by origin group
  * location_group_means.png      — 4-panel by warehouse location

Each figure shows means as bars with SD error bars and individual participant
points overlaid, and annotates Mann-Whitney U p-values on the sex figures.

Uses matplotlib only — no seaborn dependency for maximum portability.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..config import SEX_COLORS, FIGURES_DIR
from ..metrics.sex_differences import mannwhitney_tests, kruskal_tests


# ── Style ────────────────────────────────────────────────────────────────────

def _apply_style():
    plt.rcParams.update({
        "font.family":         "DejaVu Sans",
        "font.size":           10,
        "axes.spines.top":     False,
        "axes.spines.right":   False,
        "axes.titlesize":      11,
        "axes.titleweight":    "500",
        "axes.labelsize":      10,
        "axes.labelcolor":     "#2c2c2a",
        "axes.edgecolor":      "#c3c2b7",
        "xtick.color":         "#5f5e5a",
        "ytick.color":         "#5f5e5a",
        "figure.facecolor":    "white",
        "savefig.facecolor":   "white",
        "savefig.bbox":        "tight",
        "savefig.dpi":         150,
    })


# ── Helpers ──────────────────────────────────────────────────────────────────

def _plot_grouped_bars(ax, df, group_col, value_col, colors,
                        ylabel, title, annotate_p=None):
    """
    Bar chart of means ± SD per group, with individual points overlaid.

    Args
    ----
    ax          : matplotlib axes
    df          : DataFrame with group_col and value_col
    group_col   : column defining the groups (e.g. 'sex')
    value_col   : numeric metric to plot
    colors      : dict group_value → hex colour
    ylabel      : y-axis label
    title       : subplot title
    annotate_p  : optional p-value string to annotate top-right
    """
    groups = sorted(df[group_col].dropna().unique())
    xs     = np.arange(len(groups))
    means, sds, ns = [], [], []
    for i, g in enumerate(groups):
        v = df.loc[df[group_col] == g, value_col].dropna()
        means.append(float(v.mean()) if len(v) else 0)
        sds.append(float(v.std())   if len(v) > 1 else 0)
        ns.append(len(v))

    bar_colors = [colors.get(g, "#898781") for g in groups]
    ax.bar(xs, means, yerr=sds, color=bar_colors, alpha=0.65,
           edgecolor=bar_colors, linewidth=1.5, capsize=6, width=0.55,
           error_kw={"ecolor": "#5f5e5a", "linewidth": 1.2})

    # Overlay individual points
    for i, g in enumerate(groups):
        v = df.loc[df[group_col] == g, value_col].dropna().values
        jitter = np.random.default_rng(i).uniform(-0.11, 0.11, size=len(v))
        ax.scatter(np.full(len(v), i) + jitter, v,
                    color=bar_colors[i], edgecolor="white",
                    linewidth=0.8, s=40, zorder=3, alpha=0.9)

    ax.set_xticks(xs)
    ax.set_xticklabels([f"{g}\n(n={n})" for g, n in zip(groups, ns)])
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=8)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    if annotate_p:
        ax.text(0.98, 0.97, annotate_p, transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5,
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="#f5f4f0", edgecolor="#d3d1c7"))


def _p_annotation(mw_row: pd.Series | None) -> str:
    if mw_row is None or mw_row.empty:
        return "n/a"
    p = float(mw_row["p"])
    r = float(mw_row["r_effect"])
    sig = "*" if p < 0.05 else ""
    return f"U={mw_row['U']:.0f}, p={p:.3f}{sig}\nr={r:+.2f}"


# ── Public entry points ─────────────────────────────────────────────────────

def sex_differences_fixation(summary_df: pd.DataFrame,
                              out_path: Path = None) -> Path:
    """Three-panel figure: mean fix, median fix, fix rate — M vs F."""
    _apply_style()
    if out_path is None:
        out_path = FIGURES_DIR / "sex_differences_fixation.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mw = mannwhitney_tests(summary_df)
    def get_row(m):
        if mw.empty or "metric" not in mw.columns:
            return pd.Series()
        r = mw[mw["metric"] == m]
        return r.iloc[0] if len(r) else pd.Series()

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    _plot_grouped_bars(axes[0], summary_df, "sex", "mean_fix_ms",
                        SEX_COLORS, "Mean fixation duration (ms)",
                        "Mean fixation duration",
                        _p_annotation(get_row("mean_fix_ms")))
    _plot_grouped_bars(axes[1], summary_df, "sex", "median_fix_ms",
                        SEX_COLORS, "Median fixation duration (ms)",
                        "Median fixation duration",
                        _p_annotation(get_row("median_fix_ms")))
    _plot_grouped_bars(axes[2], summary_df, "sex", "fixation_rate_per_min",
                        SEX_COLORS, "Fixations / min",
                        "Fixation rate",
                        _p_annotation(get_row("fixation_rate_per_min")))
    fig.suptitle("Fixation metrics by sex", fontsize=13, fontweight="600", y=1.02)
    fig.text(0.5, -0.02,
              "Bars: mean ± SD | Dots: individual participants | * = p < 0.05 (Mann–Whitney U)",
              ha="center", fontsize=8.5, color="#5f5e5a")
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def sex_differences_blink(summary_df: pd.DataFrame,
                           out_path: Path = None) -> Path:
    """Two-panel figure: blink rate, blink duration — M vs F."""
    _apply_style()
    if out_path is None:
        out_path = FIGURES_DIR / "sex_differences_blink.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mw = mannwhitney_tests(summary_df)
    def get_row(m):
        if mw.empty or "metric" not in mw.columns:
            return pd.Series()
        r = mw[mw["metric"] == m]
        return r.iloc[0] if len(r) else pd.Series()

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    _plot_grouped_bars(axes[0], summary_df, "sex", "blink_rate_per_min",
                        SEX_COLORS, "Blinks / min",
                        "Blink rate",
                        _p_annotation(get_row("blink_rate_per_min")))
    _plot_grouped_bars(axes[1], summary_df, "sex", "mean_blink_ms",
                        SEX_COLORS, "Mean blink duration (ms)",
                        "Blink duration",
                        _p_annotation(get_row("mean_blink_ms")))
    fig.suptitle("Blink metrics by sex", fontsize=13, fontweight="600", y=1.02)
    fig.text(0.5, -0.02,
              "Bars: mean ± SD | Dots: individual participants | * = p < 0.05 (Mann–Whitney U)",
              ha="center", fontsize=8.5, color="#5f5e5a")
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def sex_differences_gaze(summary_df: pd.DataFrame,
                          out_path: Path = None) -> Path:
    """Two-panel figure: worn %, mean saccade amplitude — M vs F."""
    _apply_style()
    if out_path is None:
        out_path = FIGURES_DIR / "sex_differences_gaze.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mw = mannwhitney_tests(summary_df)
    def get_row(m):
        if mw.empty or "metric" not in mw.columns:
            return pd.Series()
        r = mw[mw["metric"] == m]
        return r.iloc[0] if len(r) else pd.Series()

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    _plot_grouped_bars(axes[0], summary_df, "sex", "worn_pct",
                        SEX_COLORS, "Device worn (% of session)",
                        "Gaze coverage",
                        _p_annotation(get_row("worn_pct")))
    _plot_grouped_bars(axes[1], summary_df, "sex", "mean_sacc_amp_deg",
                        SEX_COLORS, "Mean saccade amplitude (°)",
                        "Saccade amplitude",
                        _p_annotation(get_row("mean_sacc_amp_deg")))
    fig.suptitle("Gaze quality and saccade amplitude by sex", fontsize=13,
                  fontweight="600", y=1.02)
    fig.text(0.5, -0.02,
              "Bars: mean ± SD | Dots: individual participants | * = p < 0.05 (Mann–Whitney U)",
              ha="center", fontsize=8.5, color="#5f5e5a")
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def group_bars_by_column(summary_df: pd.DataFrame,
                          grouping: str,
                          out_path: Path = None,
                          title: str = None,
                          palette: dict = None) -> Path:
    """
    Four-panel figure: mean_fix_ms, median_fix_ms, blink_rate_per_min,
    mean_sacc_amp_deg — grouped by `grouping` (e.g. 'origin', 'location').
    """
    _apply_style()
    if out_path is None:
        out_path = FIGURES_DIR / f"{grouping}_group_means.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if grouping not in summary_df.columns:
        return None

    palette = palette or {}
    default_cycle = ["#185FA5", "#1D9E75", "#D85A30", "#BA7517", "#7F77DD",
                      "#D4537E", "#0F6E56", "#4A3AA7"]
    groups = sorted(summary_df[grouping].dropna().unique())
    colors = {g: palette.get(g, default_cycle[i % len(default_cycle)])
              for i, g in enumerate(groups)}

    kw = kruskal_tests(summary_df, grouping)
    def get_h(m):
        if kw.empty or "metric" not in kw.columns:
            return "n/a"
        r = kw[kw["metric"] == m]
        if r.empty:
            return "n/a"
        p = float(r.iloc[0]["p"])
        sig = "*" if p < 0.05 else ""
        return f"H={r.iloc[0]['H']:.2f}, p={p:.3f}{sig}"

    metrics = [
        ("mean_fix_ms",          "Mean fixation (ms)",  "Fixation duration"),
        ("median_fix_ms",        "Median fixation (ms)", "Fixation duration (median)"),
        ("blink_rate_per_min",   "Blinks / min",         "Blink rate"),
        ("mean_sacc_amp_deg",    "Saccade amplitude (°)", "Saccade amplitude"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (col, ylab, subtitle) in zip(axes.flat, metrics):
        if col not in summary_df.columns:
            ax.axis("off"); continue
        _plot_grouped_bars(ax, summary_df, grouping, col, colors, ylab,
                            subtitle, annotate_p=get_h(col))
    fig.suptitle(title or f"Gaze metrics by {grouping}", fontsize=13,
                  fontweight="600", y=1.00)
    fig.text(0.5, -0.01,
              "Bars: mean ± SD | Dots: individual participants | * = p < 0.05 (Kruskal-Wallis H)",
              ha="center", fontsize=8.5, color="#5f5e5a")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def generate_all(summary_df: pd.DataFrame,
                  out_dir: Path = FIGURES_DIR) -> list[Path]:
    """Generate every sex- and group-difference figure. Returns list of paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    paths.append(sex_differences_fixation(summary_df, out_dir / "sex_differences_fixation.png"))
    paths.append(sex_differences_blink(summary_df,    out_dir / "sex_differences_blink.png"))
    paths.append(sex_differences_gaze(summary_df,     out_dir / "sex_differences_gaze.png"))
    if "origin" in summary_df.columns:
        paths.append(group_bars_by_column(summary_df, "origin",
                                            out_dir / "origin_group_means.png",
                                            title="Gaze metrics by origin"))
    if "location" in summary_df.columns:
        paths.append(group_bars_by_column(summary_df, "location",
                                            out_dir / "location_group_means.png",
                                            title="Gaze metrics by shopfloor location"))
    return [p for p in paths if p is not None]
