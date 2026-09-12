"""
metrics/sex_differences.py — Non-parametric group comparisons.

Given small sample sizes (typically n < 10 per cell), we use non-parametric
tests throughout:

* Mann-Whitney U for two-group comparisons (M vs F).
  Effect size reported as rank-biserial r = 1 − 2U/(n_M · n_F).
  r > 0.3 conventionally treated as moderate; r > 0.5 as large.
* Kruskal-Wallis H for k-group comparisons (origin, location).
* Descriptives: mean ± SD, median, n, per cell.

Statistical power is low at these sample sizes; p-values are exploratory.
The primary evidence is pattern-of-means, triangulated with qualitative data.

References
----------
Mann, H. B., & Whitney, D. R. (1947). Annals of Mathematical Statistics.
Kruskal, W. H., & Wallis, W. A. (1952). J. Am. Stat. Assoc.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


# Metrics that this module knows how to compare
METRICS_TO_COMPARE = [
    "mean_fix_ms",
    "median_fix_ms",
    "fixation_rate_per_min",
    "pct_short_fix",
    "pct_long_fix",
    "blink_rate_per_min",
    "mean_blink_ms",
    "mean_sacc_amp_deg",
]


def sex_descriptives(summary_df: pd.DataFrame,
                      metrics: list[str] = None) -> pd.DataFrame:
    """
    Descriptives (mean, SD, n) per sex for each metric.

    Args
    ----
    summary_df : DataFrame with 'sex' column + numeric metric columns
    metrics    : list of metrics to summarise; default METRICS_TO_COMPARE

    Returns
    -------
    Wide DataFrame with rows = metric, columns = (M_mean, M_sd, M_n,
    F_mean, F_sd, F_n).
    """
    if metrics is None:
        metrics = [m for m in METRICS_TO_COMPARE if m in summary_df.columns]

    rows = []
    for m in metrics:
        row = {"metric": m}
        for sx in ("M", "F"):
            grp = summary_df.loc[summary_df["sex"] == sx, m].dropna()
            row[f"{sx}_n"]    = len(grp)
            row[f"{sx}_mean"] = round(float(grp.mean()), 2) if len(grp) else np.nan
            row[f"{sx}_sd"]   = round(float(grp.std()),  2) if len(grp) > 1 else np.nan
            row[f"{sx}_median"] = round(float(grp.median()), 2) if len(grp) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def mannwhitney_tests(summary_df: pd.DataFrame,
                       metrics: list[str] = None) -> pd.DataFrame:
    """
    Mann-Whitney U (M vs F) for each metric. Reports U, p, rank-biserial r.

    Returns DataFrame with columns:
      metric, M_n, F_n, U, p, sig_p05, r_effect
    """
    if metrics is None:
        metrics = [m for m in METRICS_TO_COMPARE if m in summary_df.columns]

    rows = []
    for m in metrics:
        m_vals = summary_df.loc[summary_df["sex"] == "M", m].dropna().values
        f_vals = summary_df.loc[summary_df["sex"] == "F", m].dropna().values
        if len(m_vals) < 2 or len(f_vals) < 2:
            continue
        try:
            u, p = stats.mannwhitneyu(m_vals, f_vals, alternative="two-sided")
        except ValueError:
            continue
        r = 1 - (2 * u) / (len(m_vals) * len(f_vals))
        rows.append({
            "metric":   m,
            "M_n":      len(m_vals),
            "F_n":      len(f_vals),
            "M_mean":   round(float(m_vals.mean()), 2),
            "F_mean":   round(float(f_vals.mean()), 2),
            "U":        round(float(u), 1),
            "p":        round(float(p), 4),
            "sig_p05":  bool(p < 0.05),
            "r_effect": round(float(r), 3),
        })
    return pd.DataFrame(rows)


def kruskal_tests(summary_df: pd.DataFrame,
                   grouping: str,
                   metrics: list[str] = None) -> pd.DataFrame:
    """
    Kruskal-Wallis H test comparing k groups on each metric.

    Args
    ----
    summary_df : DataFrame with the grouping column + numeric metrics
    grouping   : column name to group by (e.g. 'origin', 'location')
    metrics    : list of metrics; default METRICS_TO_COMPARE
    """
    if metrics is None:
        metrics = [m for m in METRICS_TO_COMPARE if m in summary_df.columns]

    if grouping not in summary_df.columns:
        return pd.DataFrame()

    rows = []
    for m in metrics:
        groups = [
            grp[m].dropna().values
            for _, grp in summary_df.groupby(grouping)
            if grp[m].notna().sum() >= 2
        ]
        if len(groups) < 2:
            continue
        try:
            h, p = stats.kruskal(*groups)
        except ValueError:
            continue
        rows.append({
            "metric":   m,
            "grouping": grouping,
            "H":        round(float(h), 3),
            "p":        round(float(p), 4),
            "sig_p05":  bool(p < 0.05),
            "n_groups": len(groups),
            "n_total":  sum(len(g) for g in groups),
        })
    return pd.DataFrame(rows)


def group_means(summary_df: pd.DataFrame,
                 grouping: str,
                 metrics: list[str] = None) -> pd.DataFrame:
    """
    Long-format mean/SD/n table for grouping × metric.

    Useful for plotting.
    """
    if metrics is None:
        metrics = [m for m in METRICS_TO_COMPARE if m in summary_df.columns]
    if grouping not in summary_df.columns:
        return pd.DataFrame()

    rows = []
    for group_val, grp in summary_df.groupby(grouping):
        for m in metrics:
            v = grp[m].dropna()
            rows.append({
                grouping: group_val,
                "metric": m,
                "mean":   round(float(v.mean()), 2) if len(v) else np.nan,
                "sd":     round(float(v.std()),  2) if len(v) > 1 else np.nan,
                "n":      int(len(v)),
            })
    return pd.DataFrame(rows)
