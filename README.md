## Opening
Analysis pipeline and post-experiment question catalogue for a Voice-Directed Warehousing (VDW) eye-tracking study. This repository contains two components, deposited together so both are covered by a single citation and DOI (See CITATION.cff)


# VDW Eye-Tracking Analysis Pipeline

1. **Analysis pipeline** — processes Pupil Labs Neon exports, computes per-event fixation duration and blink rate, and performs non-parametric (Mann-Whitney U) group comparisons by sex, origin, and warehouse location, produces per-participant dashboards outputs.


2. **Post-experiment question catalogue** — the full semi-structured interview and participatory mapping protocol administered alongside the eye-tracking task (`docs/post_experiment_questions.md`).

## Purpose

Companion code to *[Embodied Navigation Paper]* defined as "Python codes". 
Every processing step is a named module in `src/vdw_pipeline/` with a docstring citing its source.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Drop each Pupil Labs Neon export into data/raw/
#    data/raw/A1/gaze.csv, fixations.csv, blinks.csv, ...
#    data/raw/A2/...

# 3. Run the full pipeline
python scripts/run_pipeline.py

# 4. Outputs
#    results/dashboards/A_N.html        — per-participant interactive dashboard
#    results/figures/sex_differences_*.png — group summary graphs
#    results/stats/*.csv                — statistical tables
```

Adding a new participant later requires only dropping their folder into
`data/raw/`, adding one row to `data/metadata/participants.csv`, and re-running
the pipeline. Nothing else needs to change.

## Repository structure

```
VDW_pipeline/
├── README.md              (this file)
├── LICENSE                GPL v3
├── CITATION.cff           Citation metadata for Zenodo DOI
├── requirements.txt       Python dependencies (pinned)
├── src/vdw_pipeline/      Python package
│   ├── config.py          Constants, thresholds, category definitions
│   ├── io/                Loading Pupil Labs Neon exports
│   │   ├── loader.py      CSV I/O with quality gates
│   │   └── events.py      Event parsing + descriptive categorisation
│   ├── preprocessing/     Signal cleaning
│   │   ├── fixations.py   Fixation validation
│   │   ├── blinks.py      Blink validation
│   │   └── gaze.py        Gaze heatmap on scene-camera grid
│   ├── metrics/           Metric computation
│   │   ├── session.py     Session-level summary metrics
│   │   ├── segments.py    Per-event windowed metrics
│   │   └── sex_differences.py  Non-parametric group comparisons
│   └── viz/               Visualisation
│       ├── dashboard.py   Per-participant HTML dashboard
│       ├── sex_graphs.py  matplotlib figures for sex differences
│       └── templates/     HTML templates
├── scripts/               Command-line entry points
│   ├── run_pipeline.py    Full pipeline (all participants)
│   ├── add_participant.py Guided helper for adding new participants
│   └── generate_dashboard.py  Single-participant dashboard
├── data/
│   ├── raw/               Pupil Labs Neon exports (INPUT — read-only in code)
│   ├── processed/         Derived data (segments, summaries — regenerated)
│   └── metadata/
│       └── participants.csv  Participant profiles (edit here to add participants)
├── results/               Final deliverables
│   ├── dashboards/        HTML per-participant dashboards
│   ├── figures/           PNG group-level figures
│   └── stats/             CSV statistical tables
├── docs/                  Documentation (see below)
└── tests/                 Unit tests
```

## Methodology summary

Full detail in [`docs/methodology.md`](docs/methodology.md). Brief overview:

### Signal processing

* **Fixations, saccades, blinks**: Detected on-device by the Pupil Labs Neon
  Companion App using its published algorithms (Pupil Labs, 2024). Quality-gated
  in `preprocessing/fixations.py` and `preprocessing/blinks.py` following ranges
  reported in the eye-tracking literature: fixations 100–3000 ms
  (Salvucci & Goldberg, 2000), blinks 50–500 ms (Doughty, 2001).
* **Gaze**: Sampled at 100 Hz on the scene camera (1600×1200 px). Aggregated
  into a 16×12 grid for the heatmap visualisation.

### Event categorisation

Applied to event labels manually annotated in Pupil Cloud during video review
(e.g. `signage_5`, `drop_12`, `label_3`). Each event name is normalised —
handling spacing, hyphen, and typo variants seen during coding (`signaage` →
`signage`, `rearrage` → `rearrange`) — and assigned a short, descriptive
category (signage, drop, label, sticker, pallet movement, foil, rearrange,
pause, conversion, print, extra, or protocol marker). Categories are purely
descriptive of the physical action logged; no interpretive framework is
attached at this stage. Full matching rules in
`src/vdw_pipeline/io/events.py`.

### Per-event windowed metrics

For each event, gaze metrics are aggregated over the window from that event's
timestamp to the next event's timestamp. This differs from a fixed ±2 s window
(used in the earlier iteration of this study) and is documented in
`src/vdw_pipeline/metrics/segments.py`.

### Group comparisons

Non-parametric throughout, given small group sizes (typically n < 10 per cell):
Mann-Whitney U for two-group tests (male vs female), Kruskal-Wallis H for
three+ groups (origin, location), reporting rank-biserial r as effect size.
Implemented in `src/vdw_pipeline/metrics/sex_differences.py`.

### Qualitative data software

Interview transcripts were coded in **ATLAS.ti** (ATLAS.ti Scientific Software
Development GmbH, 2024), informing the study design and event-annotation
convention used here. See `docs/citations.md`.

## Documentation for reviewers

* [`docs/methodology.md`](docs/methodology.md) — detailed methods, algorithm
  citations, and parameter justifications
* [`docs/data_dictionary.md`](docs/data_dictionary.md) — every field name in
  every output file, explained
* [`docs/citations.md`](docs/citations.md) — bibliography, ATLAS.ti citation,
  Pupil Labs citation, all algorithmic references
* [`docs/how_to_add_participant.md`](docs/how_to_add_participant.md) — three-step
  guide for adding a new participant
* [`docs/post_experiment_questions.md`](docs/post_experiment_questions.md)
  — full post-experiment assessment question catalogue (interview + participatory mapping)

## Reproducibility

All parameters (thresholds, window sizes, weights) are in `src/vdw_pipeline/config.py`
and documented inline. `requirements.txt` pins exact versions. The pipeline is
deterministic — running twice on the same input produces identical output.

## Citation

If you use this pipeline or the question catalogue, please cite via Zenodo DOI.

## License

GPL v3 — see `LICENSE`.
