# HPR Audio Generator

An audio-first, human-in-the-loop system for building a reusable library of short, publication-quality soundtracks.

This repository intentionally knows nothing about portraits, video, episodes, publishing, or analytics. Its only job is to generate, review, and improve audio.

## Creative model

Each candidate is generated from:

1. one continuous **bed**;
2. zero, one, or two nearby **gestures**;
3. an optional **music stem**;
4. a recipe, profile, and deterministic random seed.

The generator creates constrained surprises. A human listens, rates, and decides what enters the approved library.

## What is included

- `config/generator.xml`: the machine-readable source of truth for 90 locally managed audio assets
- `config/generator.xsd`: validation schema for the XML
- a dependency-free Python reference generator
- tests, documentation, and empty output folders

Licensed source WAV files, generated audio, and the live production workbook are intentionally excluded from this public repository.

## First run

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
hpr-audio validate
hpr-audio generate --recipe AR-001 --count 10
```

Generated candidates are written to `audio/output/candidates/`. Their IDs, seeds, and ingredients should then be recorded in the workbook.

## Source of truth

- Software reads `config/generator.xml`.
- Humans author and curate recipes in the private Google Sheet Audio Recipe
  Library and review generated candidates through the HPR review workflow.
- WAV files remain immutable ingredients.
- Generated audio is reproducible from recipe ID, generator version, and seed.

The Google Sheet is the live operational workbook. A future importer will make
a dated, checksummed configuration snapshot for each production batch; audio
manifests will record its snapshot ID. Danny will not manually mirror recipe
rows into SQLite. Do not commit exported workbook copies to this repository.

## Initial goal

Generate and review audio independently until the system can reliably produce 150 approved loops. Generated candidates do not count toward the goal; only tracks explicitly marked `Approved` count.
