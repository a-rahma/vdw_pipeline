"""
io/events.py — Classify Pupil Cloud event labels into descriptive categories.

Event names logged in Pupil Cloud follow the site's coding convention
(e.g. `signage_5`, `drop_12`, `label_3`). This module normalises those names
(handling spacing/hyphen/typo variants seen during coding) and assigns each
event a short, purely descriptive category — signage, drop, label, sticker,
move-pallet, foil, rearrange, repalletise, pause, conversion, print, extra,
or protocol marker — used for dashboard colouring and grouping.

This module does not attach any interpretive or theoretical framing to the
event categories; it only recognises which physical/procedural action an
event label refers to. Typo variants encountered during coding are
normalised (signaage → signage, coversion_disrupt → conversion, rearrage →
rearrange).
"""
from __future__ import annotations
import re
import pandas as pd


# ── Event-name patterns ──────────────────────────────────────────────────────
# Ordered — longer/more-specific prefixes must come before shorter ones so
# `conversion_disruption` matches before any prefix that could partially match.
# (category, description) — category matches the short codes used by
# config.CATEGORY_COLORS for dashboard colouring.
EVENT_PATTERNS: list[tuple[str, str, str]] = [
    ("conversion_disruption", "conversion",   "Conversion disruption event"),
    ("coversion_disrupt",     "conversion",   "Conversion disruption (typo variant)"),
    ("conversion_disrupt",    "conversion",   "Conversion disruption (typo variant)"),
    ("rearrange",             "rearrange",    "Rearrange items"),
    ("rearrage",              "rearrange",    "Rearrange (typo variant)"),
    ("pause",                 "pause",        "Unplanned pause"),
    ("print",                 "print",        "Print required"),
    ("repallete",             "repallet",     "Repalletise"),
    ("repallet",              "repallet",     "Repalletise (spelling variant)"),
    ("fixed_boxes",           "extra",        "Fixing boxes"),
    ("extra_obj",             "extra",        "Extra object handling"),
    ("movepallete",           "movepallete",  "Move pallet along aisle"),
    ("signage",               "signage",      "Read overhead signage / aisle marker"),
    ("signaage",              "signage",      "Read signage (typo variant)"),
    ("signing",               "signage",      "Read signage (typo variant)"),
    ("sticker",                "sticker",      "Read unit sticker"),
    ("foil",                  "foil",         "Wrap / foil pallet"),
    ("label",                 "label",        "Read pick label"),
    ("drop",                  "drop",         "Drop / place item"),
]

PROTOCOL_EVENTS = {"recording.begin", "recording.end", "work_start", "work_end"}
REPEAT_RE       = re.compile(r"repeat_?\d*_?(start|end)?", re.I)


# ── Normalisation ────────────────────────────────────────────────────────────

def normalise(name: str) -> str:
    """Lowercase; replace spaces/hyphens with underscore; strip repeats."""
    if not name:
        return ""
    n = str(name).strip().lower()
    n = re.sub(r"[\s\-]+", "_", n)
    n = re.sub(r"_+", "_", n)
    return n.strip("_")


def extract_num(name: str) -> int | None:
    """Extract trailing digits from an event name (e.g., signage_5 → 5)."""
    if not name:
        return None
    m = re.search(r"(\d+)", str(name))
    return int(m.group(1)) if m else None


# ── Classifier ────────────────────────────────────────────────────────────────

def classify_event(raw_name: str) -> tuple[str, str, str]:
    """
    Classify a single event name into a short descriptive category.

    Returns (category, base_name, description).

    `category` is one of: signage, drop, label, sticker, movepallete, foil,
    rearrange, repallet, pause, conversion, print, extra, protocol,
    unclassified. These are purely descriptive event-type codes (also used
    for dashboard colouring via config.CATEGORY_COLORS) — no interpretive
    framework is attached.
    """
    if not raw_name:
        return ("unclassified", "", "Uncategorised")
    n = normalise(raw_name)
    if n in PROTOCOL_EVENTS or REPEAT_RE.fullmatch(n):
        return ("protocol", n, "Research protocol marker")
    for prefix, cat, desc in EVENT_PATTERNS:
        if n == prefix or n.startswith(prefix + "_") or n.startswith(prefix):
            return (cat, prefix, desc)
    return ("unclassified", n, "Uncategorised")
