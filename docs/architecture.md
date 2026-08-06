# Architecture

HPR Umbrella is a modular, human-in-the-loop production system. The Candidate Engine is the architectural center. Media plugins make assets; the engine turns those assets into finite choices and preserves the human editorial record.

## Candidate Engine

The Candidate Engine owns:

- the 120 archive episode slots;
- deterministic candidate-set planning;
- separate Visual, Audio, Pair, and Publishing banks;
- review status, 0–5 ratings, notes, banking, rejection, and selection;
- unique-audio retirement after final selection;
- replaceable photo sources without losing the creative assembly;
- provenance and regeneration instructions.

It does not make artistic selections. A failed pair never implies that its visual or audio component failed.

## Audio Generator

Input:

- immutable audio beds, gestures, and optional music stems;
- an audio recipe and profile;
- a duration and random seed.

Output:

- one loop-ready WAV candidate;
- reproducible ingredient and timing metadata.

The Audio Generator knows nothing about portraits, video, publishing, or analytics.

## Video Generator

Input:

- one portrait photograph;
- one loop-safe movement preset;
- film grain or a restrained texture;
- a duration and random seed.

Output:

- one silent 1080 × 1920 MP4 candidate;
- a JSON provenance record.

The Video Generator knows nothing about audio, pairing, publishing, or selection.

## Candidate assembly

Input:

- one portrait;
- one duration;
- one video preset;
- one compatible audio recipe;
- a random seed and candidate count.

Output:

- silent intermediate video;
- soundtrack intermediate;
- assembled review MP4;
- a combined JSON provenance manifest.

The Candidate Engine validates that audio and video durations agree, coordinates generation, and muxes the result. It stores ratings and decisions supplied by the artist but does not infer or automate them.

## Archive production model

```text
120 archive episodes
├── 40 × 7 seconds
├── 40 × 9 seconds
└── 40 × 11 seconds

Visual bank: 5 candidates per episode = 600
Audio bank: 50 per duration = 150
Pair bank: 10 options after each visual selection
Publishing bank: 120 final slots, each requiring unique audio
```

Now mode is a future input mode and is outside the current production build.

## Replaceable photo source

An episode owns the creative assembly, not a particular export of the photograph. Replacing a photo increments its revision and marks visual/final renders stale while preserving the selected motion recipe, duration, audio, optional text treatment, and publication metadata.

## Text Plugin boundary

Text remains a nondestructive optional layer. The initial treatment is a minimal “How People Relate” identity element considered only after the audio-video master is selected. Channel-specific necessity remains an editorial decision.

## Human boundary

The artist:

1. chooses which portraits enter production;
2. defines and revises constraints;
3. reviews generated candidates;
4. decides what is successful;
5. selects the published work;
6. changes the system in response to experience.

Automation increases the number of considered possibilities. It does not define quality.

## Reproducibility

Every assembled candidate records:

- portrait path;
- duration;
- video preset and generator version;
- audio recipe, ingredients, and generator version;
- random seed;
- intermediate and final output paths.

The same configuration, assets, and seed reproduce the same source choices and motion recipe.
