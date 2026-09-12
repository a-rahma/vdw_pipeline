# Methodology

Detailed methods for the VDW eye-tracking analysis pipeline. This
document is intended for reviewers and for future researchers reproducing or
extending the analysis. Each processing step names the algorithm used, the
parameter values chosen, and the source of both.

## 1. Data acquisition

### Hardware

* **Eye-tracker**: Pupil Labs Neon (Pupil Labs GmbH, Berlin).
* **Sampling rate**: 100 Hz binocular gaze; 200 Hz eye-state (pupil).
* **Scene camera**: 1600 × 1200 px.

### Software

* **Recording**: Pupil Labs Neon Companion app v2.9.31.
* **Cloud export**: Pupil Cloud, raw-data-exporter v2 (Pupil Labs, 2024).
* **Event annotation**: Manual coding in Pupil Cloud during video review.
  Coders followed a coding manual derived from field observation.

Each participant folder from Pupil Cloud contains:

| File | Description |
|------|-------------|
| `gaze.csv` | 100 Hz gaze position (scene-camera pixels) + fixation/blink IDs |
| `fixations.csv` | Detected fixations with start/end timestamps, duration, centroid |
| `saccades.csv` | Detected saccades with amplitude, duration, peak velocity |
| `blinks.csv` | Detected blinks with onset/offset, duration |
| `3d_eye_states.csv` | 200 Hz pupil diameter, eyelid aperture |
| `events.csv` | Timestamped event labels (recording bounds, work bounds, behavior codes) |
| `world_timestamps.csv` | Scene-camera frame timestamps |
| `info.json` | Recording metadata (device ID, firmware, calibration) |

## 2. Signal processing

### 2.1 Timestamp normalisation

All timestamps in Pupil Labs Neon exports are nanoseconds since Unix epoch. On
load, they are converted to seconds relative to `recording.begin`. See
`src/vdw_pipeline/io/loader.py::_ns_to_s`.

### 2.2 Fixation detection

Fixations are detected on-device by the Pupil Labs Neon Companion app using a
velocity-based algorithm derived from Salvucci & Goldberg (2000). We apply a
post-hoc quality gate:

* **Minimum duration**: 100 ms. Below this threshold, information uptake during
  fixation is unreliable (Rayner, 2009).
* **Maximum duration**: 3000 ms. Above this threshold, the "fixation" is likely
  a tracker artefact during a blink or head movement.

Rate values are the accepted defaults in cognitive eye-tracking work; they are
set in `src/vdw_pipeline/config.py::FIXATION_MIN_DURATION_MS` and can be adjusted
if a different convention applies to the reader's field.

**Metrics reported**: mean, median, and SD of fixation duration; count; rate
per minute; percentage below 120 ms (visual search) and above 300 ms (deep
processing).

### 2.3 Blink detection

Blinks are detected on-device by the Pupil Labs Neon Companion app from IR
eyelid tracking. Quality gate:

* **Minimum duration**: 50 ms. Below this, likely a false positive.
* **Maximum duration**: 500 ms. Above this, likely an eye closure (drowsiness
  or tracker loss) rather than a natural blink (Doughty, 2001; Cardona &
  Quevedo, 2014).

**Metrics reported**: count, rate per minute, mean blink duration.

Blink rate is interpreted as follows, per the eye-tracking literature:
* **Suppressed** blink rate (< participant mean − 1 SD) during high attentional
  load, focused effort, or stress (Maffei & Angrilli, 2018).
* **Elevated** blink rate can indicate fatigue, dry-eye discomfort, or
  post-effort rebound; alternatively, motor consequence of head/eye movement
  during active visual search.

### 2.4 Gaze heatmap

Scene-camera gaze samples are binned into a 16 × 12 grid (matching the aspect
ratio of the 1600 × 1200 px scene). For each event window, samples are counted
per grid cell to produce a heatmap of visual attention.

Grid dimensions are set in `config.py::GRID_W` and `GRID_H`.

## 3. Event categorisation

Event labels annotated in Pupil Cloud (e.g. `signage_5`, `drop_12`, `label_3`)
are normalised — handling spacing, hyphen, and typo variants seen during
coding (`signaage` → `signage`, `coversion_disrupt` → `conversion`,
`rearrage` → `rearrange`) — and assigned a short, descriptive category:

* `signage`, `sticker`, `movepallete`, `foil` — reading/handling physical
  warehouse infrastructure
* `label`, `drop` — reading pick labels, placing items
* `rearrange`, `pause`, `conversion`, `print`, `extra` — other logged
  procedural events
* `protocol` — research/session markers (`recording.begin`, `work_start`, etc.),
  excluded from behavioural analysis

These categories are descriptive only (used for dashboard colour-coding and
grouping); no interpretive framework is attached at the pipeline level. Full
matching rules in `src/vdw_pipeline/io/events.py::EVENT_PATTERNS`.

## 4. Per-event metrics (segments)

For each event *e<sub>i</sub>*, gaze metrics are aggregated over the window
[t(*e<sub>i</sub>*), t(*e<sub>i+1</sub>*)] — i.e. from the event's timestamp
to the next event's timestamp. Metrics per segment:

| Metric | Description |
|--------|-------------|
| `dur` | Window duration (s) |
| `fix` | Number of fixations starting in window |
| `fixMs` | Mean fixation duration in window (ms) |
| `fixRate` | Fixations per minute in window |
| `fixPct` | % of window time spent fixating |
| `sacc` | Number of saccades in window |
| `saccAmp` | Mean saccade amplitude (°) |
| `blk` | Number of blinks with onset in window |
| `blkRate` | Blinks per minute in window |
| `gzN` | Number of gaze samples in window |
| `gxM`, `gyM` | Mean gaze position (scene-camera px) |
| `gxSd`, `gySd` | SD of gaze position |
| `worn` | % of window during which device was worn |
| `heat` | Gaze heatmap: list of [col, row, count] triples for occupied cells |

Implementation: `src/vdw_pipeline/metrics/segments.py`.

**Note on windowing**: This differs from the ±2 s window used in an earlier
version of this pipeline. The event-anchored window better matches the
duration of the behavior it represents (long for `signage`, short for `drop`)
but means windows do not overlap. Both choices are defensible; the
event-anchored version is used in the dashboards. Fixed ±2 s windows can be
requested by passing `--window-fixed 2.0` to the pipeline entry point.

## 5. Session-level summary

For each participant:

* Total recording duration, work duration (from `work_start` / `work_end`
  markers if present, else recording bounds).
* Total counts: fixations, saccades, blinks.
* Mean and median fixation duration.
* Mean blink duration, blink rate per minute.
* Fixation rate per minute.
* Event counts by category (signage, drop, label, sticker, etc.).

Implementation: `src/vdw_pipeline/metrics/session.py`.

## 6. Group comparisons

Given small sample size (n < 10 in most cells), we use non-parametric tests
throughout:

* **Two-group comparisons** (male vs female): Mann-Whitney U test. Effect
  size reported as rank-biserial correlation *r* = 1 − 2U/(n₁·n₂).
* **k-group comparisons** (origin, location): Kruskal-Wallis H test with H
  statistic and p-value. Post-hoc pairwise Mann-Whitney tests reported without
  multiple-comparison correction (given exploratory nature; correction would
  be inappropriate at this sample size).
* **Descriptive statistics**: mean ± SD, median, min, max, n for every cell.

Implementation: `src/vdw_pipeline/metrics/sex_differences.py` and
`metrics/group_by.py`.

**Interpretive caution**: With n typically 4–12 per cell, statistical power
is low. p-values should be treated as exploratory. The primary evidence is the
pattern of means and their consistency across participants, triangulated with
qualitative data from interviews.

## 7. Visualisations

### 7.1 Per-participant dashboards

Interactive HTML dashboards produced by `src/vdw_pipeline/viz/dashboard.py`.
Data embedded as JSON in the HTML file (no server needed). Sections:

1. **KPIs**: header cards summarising session (duration, event counts, mean fix).
2. **Session timeline**: horizontal bar per event, width = duration, coloured by
   category.
3. **Per-event scatter**: dots for blink rate, fixation duration across time.
4. **Category means**: bar chart of mean values per behavior category.
5. **Gaze heatmap**: 16 × 12 grid per category showing where the picker looked.
6. **Event table**: sortable table of every event with all metrics.

Template: `src/vdw_pipeline/viz/templates/dashboard.html`.

### 7.2 Sex-difference summary graphs

Grouped bar charts (matplotlib) showing mean of each metric by sex, with SD
error bars and individual participant points overlaid. Non-parametric test
results (U, p, r) annotated on each panel.

Implementation: `src/vdw_pipeline/viz/sex_graphs.py`.

## 9. Data integrity handling

Two of the 21 raw exports (`A9`, `A11`) had been opened and
re-saved in a spreadsheet application under a non-English locale prior to
being handed to the analysis pipeline. This silently changes the field
delimiter (`,` → `;`) and decimal separator (`.` → `,`), and for
high-precision columns can further corrupt the value by inserting spurious
separator characters (e.g. `-22.9583901229847` becomes the string
`-22.958.390.122.984.700`).

The pipeline detects and repairs this automatically (`io/loader.py::
_robust_read_csv`): it retries a failed comma-delimited parse with
semicolon delimiter and comma decimal, then coerces every numeric column
individually, so cells that survive repair become usable floats and cells
that don't become `NaN` rather than crashing the run or silently
propagating garbage.

For `A9`, the corruption was severe enough that `recording.begin` and
`recording.end` rounded to the same timestamp after repair. The pipeline
detects this case explicitly (`io/loader.py::load_events`, timestamp-span
sanity check against the gaze-based recording duration) and falls back to
session-level metrics only for that participant — per-event behaviour
classification is unavailable for `A9` until the export is
re-pulled from Pupil Cloud. This is logged as an explicit warning at
runtime rather than failing silently.

This is disclosed here, rather than only in a code comment, because it
affects the analysable N for per-event (though not session-level) metrics
and should be reported as a data-quality limitation in the paper.

## 10. Reproducibility and versioning

* All parameters in `src/vdw_pipeline/config.py`.
* `requirements.txt` pins exact versions of pandas, numpy, scipy,
  matplotlib, openpyxl.
* Pipeline is deterministic; running twice on identical input produces
  identical output (no random components; sort orders explicit).
* Every intermediate output is saved to `data/processed/` so partial re-runs
  are possible.

## References

* Salvucci, D. D., & Goldberg, J. H. (2000). Identifying fixations and saccades
  in eye-tracking protocols. *Proceedings of the 2000 Symposium on Eye Tracking
  Research & Applications*, 71–78.
* Pupil Labs GmbH. (2024). Neon documentation.
  https://docs.pupil-labs.com/neon/
* ATLAS.ti Scientific Software Development GmbH. (2024). ATLAS.ti (Version
  24). https://atlasti.com
