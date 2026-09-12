# Data Dictionary

Every field name that appears in an output file, with its meaning, unit,
and source.

## `data/metadata/participants.csv`

| Column | Type | Description |
|--------|------|-------------|
| `et_code` | str | Eye-tracking code (matches folder name in `data/raw/`) |
| `pseudonym` | str | Human-readable name used in outputs |
| `code` | str | Combined field code (e.g. `#1_PBL_DM`) |
| `interview_code` | str | Interview transcript ID (cross-refs ATLAS.ti project) |
| `breakdown_code` | str | Breakdown taxonomy code from qualitative analysis |
| `sex` | str | `M` or `F` |
| `location` | str | Warehouse zone: `PBL`, `PBS`, `TC`, `Frozen` |
| `origin` | str | Country of origin |
| `experience` | str | Free-text experience description |
| `track` | str | Study protocol track: `A`, `B`, `A+B` |

## `results/stats/participant_summary.csv`

One row per participant. All eye-tracking metrics computed over the full
session. Missing values are blank.

| Column | Unit | Description |
|--------|------|-------------|
| `participant_id` | str | Eye-tracking code |
| `pseudonym`, `sex`, `location`, `origin`, `experience`, `breakdown_code`, `track` | str | From participants.csv |
| `duration_s` | seconds | Recording duration (recording.begin to recording.end) |
| `duration_min` | minutes | Same, in minutes |
| `worn_pct` | % | Fraction of session during which device was worn |
| `n_fixations` | count | Fixations after quality gate (100–3000 ms) |
| `mean_fix_ms` | ms | Arithmetic mean of fixation durations |
| `median_fix_ms` | ms | Median fixation duration |
| `sd_fix_ms` | ms | SD of fixation durations |
| `fixation_rate_per_min` | count/min | Fixations divided by session minutes |
| `pct_short_fix` | % | Fraction of fixations < 120 ms (visual search) |
| `pct_long_fix` | % | Fraction of fixations > 300 ms (deep processing) |
| `total_dwell_s` | seconds | Summed fixation duration (total gaze-on-target time) |
| `n_blinks` | count | Blinks after quality gate (50–500 ms) |
| `blink_rate_per_min` | count/min | Blinks divided by session minutes |
| `mean_blink_ms` | ms | Mean blink duration |
| `sd_blink_ms` | ms | SD of blink durations |
| `n_saccades` | count | Saccades (no quality gate — as detected by Neon) |
| `mean_sacc_amp_deg` | degrees | Mean saccade amplitude |
| `sd_sacc_amp_deg` | degrees | SD of saccade amplitude |

## `data/processed/segments/<pid>.json`

Per-event windowed metrics. This is the payload the HTML dashboard consumes.

### `summary` object

| Key | Unit | Description |
|-----|------|-------------|
| `participant` | str | Display name (`A1`) |
| `recDur` | seconds | Recording duration |
| `workDur` | seconds | Work window duration (if `work_start`/`work_end` present) |
| `totBlk`, `totFix`, `totSacc` | count | Session totals |
| `meanFixMs`, `medFixMs`, `meanBlkMs` | ms | Session means/medians |
| `blkRatePerMin`, `fixRatePerMin` | count/min | Session rates |
| `nSignage`, `nDrop`, `nRearrange`, `nRepallet` | count | Event category counts |
| `gridW`, `gridH` | grid cells | Heatmap grid dimensions (16 × 12) |

### `segments` array — one object per event

| Key | Unit | Description |
|-----|------|-------------|
| `i` | int | Sequential index (0-based) |
| `name` | str | Original event name from `events.csv` |
| `occ` | int | Occurrence number for this name (1 = first occurrence) |
| `cat` | str | Short category code: `signage`, `drop`, `rearrange`, `repallet`, `extra`, `work`, `label`, `sticker`, `movepallete`, `foil`, `pause`, `conversion`, `print`, `other` |
| `num` | int, null | Trailing digit extracted from name (e.g. `signage_5` → 5) |
| `t0` | seconds | Event onset time (from recording.begin) |
| `dur` | seconds | Window duration = time until next event |
| `blk` | count | Blinks with onset in window |
| `blkRate` | /min | Blink rate in window |
| `fix` | count | Fixations with start in window |
| `fixRate` | /min | Fixation rate in window |
| `fixMs` | ms | Mean fixation duration in window |
| `fixPct` | % | % of window time spent fixating |
| `sacc` | count | Saccades starting in window |
| `saccAmp` | degrees | Mean saccade amplitude in window |
| `gzN` | count | Number of gaze samples in window |
| `gxM`, `gyM` | scene px | Mean gaze position |
| `gxSd`, `gySd` | scene px | SD of gaze position |
| `worn` | % | % of window with device worn |
| `heat` | list | Sparse heatmap: [[col, row, count], ...] on 16 × 12 grid |

## `results/stats/sex_descriptives.csv`

Wide-format descriptives per sex.

| Column | Description |
|--------|-------------|
| `metric` | Metric name |
| `M_n`, `F_n` | Sample sizes |
| `M_mean`, `F_mean` | Group means |
| `M_sd`, `F_sd` | Group SDs |
| `M_median`, `F_median` | Group medians |

## `results/stats/sex_mannwhitney.csv`

| Column | Description |
|--------|-------------|
| `metric` | Metric name |
| `M_n`, `F_n` | Sample sizes |
| `M_mean`, `F_mean` | Group means (repeated for convenience) |
| `U` | Mann-Whitney U statistic |
| `p` | Two-sided p-value |
| `sig_p05` | Boolean, p < 0.05 |
| `r_effect` | Rank-biserial effect size: 1 − 2U/(n_M · n_F). Positive means F > M. |

## `results/stats/{origin,location}_kruskal.csv`

| Column | Description |
|--------|-------------|
| `metric` | Metric name |
| `grouping` | Grouping column (`origin` or `location`) |
| `H` | Kruskal-Wallis H statistic |
| `p` | p-value |
| `sig_p05` | Boolean |
| `n_groups`, `n_total` | Numbers of groups and total observations |
