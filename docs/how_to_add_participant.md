# How to add a new participant

The pipeline is designed to accept new participants without any code changes.

## Three steps

### 1. Drop the Pupil Cloud export into `data/raw/`

After exporting a participant's recording from Pupil Cloud, unzip it into
`data/raw/` using the participant's ID as the folder name:

```
data/raw/
├── A1/
│   ├── gaze.csv
│   ├── fixations.csv
│   ├── saccades.csv
│   ├── blinks.csv
│   ├── 3d_eye_states.csv
│   ├── events.csv
│   ├── world_timestamps.csv
│   └── info.json
├── A22/             ← new participant goes here
│   └── ...
```

The folder name pattern is a single letter followed by digits (`A1`, `A22`, `B7`, ...), matching the `interview_code` convention in participants.csv. Case-insensitive.

### 2. Add a row to `data/metadata/participants.csv`

Open the file and add one row for the new participant:

```csv
et_code,pseudonym,code,interview_code,breakdown_code,sex,location,origin,experience,track
A22,Xavier,#22_PBL_DM,A22,BR-T03,M,PBL,Portugal,2 years,B
```

Column meanings:

| Column | Value |
|--------|-------|
| `et_code` | Eye-tracking code = folder name in `data/raw/` |
| `pseudonym` | Human-readable name used in outputs |
| `code` | Combined code from field notes |
| `interview_code` | Interview transcript identifier (for cross-referencing ATLAS.ti) |
| `breakdown_code` | Breakdown taxonomy code from qualitative analysis |
| `sex` | `M` or `F` |
| `location` | Warehouse zone: `PBL`, `PBS`, `TC`, or `Frozen` |
| `origin` | Country of origin |
| `experience` | Free-text experience description |
| `track` | Track code from study protocol: `A`, `B`, or `A+B` |

### 3. Re-run the pipeline

```bash
python scripts/run_pipeline.py
```

Or to process just the new participant (skipping the rest):

```bash
python scripts/run_pipeline.py --only A22
```

The dashboard for the new participant will appear at
`results/dashboards/A22_dashboard.html`, and group-level outputs
(sex-difference figures, statistical tables) will be refreshed
automatically.

## Behaviour label enrichment

The pipeline detects per-event behaviour categories from event labels in
each participant's `events.csv`. If the Pupil Cloud export contains only
`recording.begin`, `recording.end`, and optionally `work_start` / `work_end`,
the pipeline will still process the participant but will report session-level
metrics only — no per-behaviour analysis.

To enable per-behaviour analysis for a participant:

1. Open the recording in Pupil Cloud.
2. Add events at each moment the picker performs a coded behaviour:
   - `label_N` when reading the pick label (N = pick number)
   - `signage_N` when reading overhead signage
   - `sticker_N` when reading a location sticker
   - `drop_N` when dropping an item
   - `movepallete_N` when moving a pallet
   - `foil_N` when wrapping / foiling
   - `rearrange_N` when unexpectedly rearranging items
   - `pause_start` / `pause_end` for unplanned pauses
   - `conversion_disruption_start` / `conversion_disruption_end` for mismatch
     recoveries
   - `print_start` when printing is required
   - `repallete_N` when re-palletising
3. Re-export to `data/raw/`.
4. Re-run the pipeline.

Typo variants (`signaage`, `coversion_disrupt`, `rearrage`) are automatically
normalised — you don't need to re-code past recordings.
