# Current State

Updated: 2026-08-06

## Permanent decisions

- The Candidate Engine is the architectural center of HPR Umbrella.
- Archive production is the current focus; Now mode is deferred.
- Audio, Video, and future Text are plugins coordinated by the engine.
- The production target is 120 archive videos: 40 each at 7, 9, and 11 seconds.
- Each portrait receives five restrained visual candidates; noticeable motion is a failure mode.
- The audio bank contains 150 unique tracks: 50 per duration.
- A selected visual receives 10 audio pairing options.
- Every final video uses a unique audio track, retired after selection.
- Visual, Audio, Pair, and Publishing banks remain separate.
- Human judgment is recorded, never inferred. A bad pair does not invalidate its components.
- Photo exports can be replaced without losing motion, audio, text, or publication decisions.
- Text is optional, nondestructive, and considered after the audio-video master is ready.
- Preserve metadata for every candidate; permanently retain selected masters and banked assets, while disposable renders may be regenerated.

## Implemented in this session

- Archive production planner and domain records.
- Deterministic 120-episode / 600-visual / 150-audio dry run.
- Separate Episode, Visual, Audio, Pair, and Publishing bank files.
- Duration-compatible pairing options that exclude retired audio.
- Independent visual/audio/pair review fields.
- Photo replacement that preserves the creative assembly and marks dependent renders stale.

## Next production work

1. Supply the authoritative CSV of 120 selected archive portraits.
2. Run and inspect the production dry run.
3. Add bank persistence commands for recording reviews and selections.
4. Connect the plan to queued batch rendering in the Video and Audio plugins.
5. Run a small end-to-end pilot before rendering all 600 visual candidates and 150 audio tracks.
