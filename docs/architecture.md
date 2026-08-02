# Architecture

HPR Umbrella is a modular, human-in-the-loop production system. Component boundaries prevent technical automation from quietly becoming artistic decision-making.

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

## Candidate Generator

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

The Candidate Generator validates that audio and video durations agree, coordinates generation, and muxes the result. It does not rate, rank, approve, or publish candidates.

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
