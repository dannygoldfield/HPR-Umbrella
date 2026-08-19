# Three-portrait pilot report — 2026-08-14

> Historical status: this report records the experiments that led to the
> Portrait Development Animation discovery. Camera-motion and White Balance-only
> tests are no longer the active HPR visual plan. See
> [Portrait Development Animation](../components/video-generator/docs/PORTRAIT-DEVELOPMENT-ANIMATION.md).

## Outcome

The metadata, Registry, motion-rhythm, provenance, and first visual-review
path are functional for the three supplied Lightroom exports. Episode order
is deliberately absent from intake and candidate records. Danny can evaluate
completed motion-and-audio works first and set the custom 120-item sequence at
the end.

## Pilot portraits

| Source portrait | Registry portrait | Source project | Archive group |
| --- | --- | --- | --- |
| `bahamas.210.jpg` | `POR-BC143715AA99` | `NYChildren` | age 12 or younger |
| `new_jersey_m_0180.jpg` | `POR-90500D66EBBF` | `10000` / To Live 10,000 Years | age 100 or older |
| `26-Sam-135-Edit.jpg` | `POR-DDB8C2D1CD71` | `Infinity` / MIT Infinity | number prop |

All are revision `R001`. Original JPEGs remain unchanged.

## Metadata survival

All eleven tested Lightroom fields survived in the exports: IPTC Source,
Title, Caption, Headline, Alt Text, Extended Description, Keywords, Star
Rating, Color Label, Creator, and Copyright. Exact EXIF/IPTC/XMP mappings are
recorded in the metadata report and [metadata contract](metadata-contract.md).

The significant finding is the legacy IPTC Source limit. XMP preserved the
long `To Live 10,000 Years` sentinel, while the IPTC IIM value stopped after 32
characters. Production therefore uses short stable Source codes such as
`NYChildren`, `10000`, and `Infinity`; the Registry stores display names
separately.

## Motion outputs

Fifteen silent MP4 candidates were rendered and registered: five timing
rhythms for each portrait. Every file was decoded and verified as:

- 7.000 seconds;
- 168 frames at 24 fps;
- 1080 × 1920 H.264 video;
- no audio and no grain for motion isolation;
- adjacent JSON provenance manifest.

The recipes are smooth baseline, variable speed, brief hold, two-stage with
near-stillness, and asymmetric approach/return. The exact specification is in
[Motion Rhythm](../components/video-generator/docs/MOTION-RHYTHM.md).

## JSON manifest contract

Each visual manifest is generated automatically and records:

- candidate type and schema version;
- permanent portrait ID and exact portrait revision ID;
- source path and SHA-256 checksum;
- motion recipe ID, name, rhythm type, and configuration version;
- duration, frame rate, exact frame count, and deterministic seed;
- every keyframe's time, scale, position, and easing;
- exact hold frame ranges and durations;
- grain treatment and reason;
- generator version, complete filter graph, and output path.

JSON is provenance, not a human-maintained database or review form.

## Review and sequence method

The local review screen writes directly to SQLite. It shows the looping video,
source project, portrait and revision IDs, recipe, render/review state, and
manifest link. It records 1–5 rating, rejection, notes, and selection while
retaining the decision history. Visual, audio, and pair reviews remain
independent.

Completed masters will later enter a draft Registry sequence. A friendly
sequence view—or a Lightroom Classic collection interchange—will allow the
same kind of drag-and-drop custom ordering Danny already uses. The order can
change repeatedly. Only locking the complete 120-master sequence assigns
episode numbers and creates publication records.

## Build inventory

| Area | Status |
| --- | --- |
| Lightroom metadata instructions and verified contract | Built for pilot |
| Metadata extraction/validation tool | Built and tested |
| SQLite Registry, portrait revision intake, reviews, sequence foundation | Initial implementation built |
| Five motion-rhythm recipes and 15 candidates | Built and verified |
| Visual review interface | Functional first version |
| Audio Recipe Library snapshot importer | Specified, not built |
| Registry-backed replacement for legacy early episode planner | Not built |
| Audio-candidate and pair-review connection | Schema present, interface not built |
| Grain treatment selection and final-master production | Not built |
| Friendly completed-master sequence editor / Lightroom interchange | Foundation present, interface not built |
| Release renderer, social publishing, response capture | Not built; no public action taken |

## Prioritized next build at the time of this report

Launch-critical:

1. Complete Danny's review of the 15 motion candidates and translate the notes
   into the next restrained-motion experiment.
2. Replace the legacy slot-first planner with Registry portrait work records.
3. Build the versioned Audio Recipe Library snapshot importer.
4. Connect audio production, audio review, pair review, and final-master
   approval to the Registry.
5. Build and test the completed-master sequence surface before any 120-item
   production render.
6. Build release naming, publication ledger execution, and response capture.

This list has been superseded for visual R&D by the active plan in
`CURRENT-STATE.md`: capture aligned Lightroom development states, build the
stage-delta and activation-field renderer, and review the new 15-candidate
fixed-geometry pilot before advancing visual/audio pairing.

Later enhancements:

1. Optional text treatment after audio-video master approval.
2. Richer review filtering, comparisons, and exported reports.
3. Regeneration and stale-render queues after portrait revisions.
4. HPR Now and any additional portrait series.

## Follow-up: motion-variable round 2

Danny completed the first rhythm review. The selected references were MR-005
for `bahamas.210`, MR-004 for `new_jersey_m_0180`, and MR-005 for
`26-Sam-135-Edit`. MR-002 and MR-003 were rejected for all three portraits,
confirming that rhythm should remain portrait-specific rather than universal.

Twelve additional silent candidates now test lower and higher scale amplitude,
horizontal-only micro-movement, and vertical-only micro-movement. Together
with the three references, the second review set contains 15 comparisons. All
new outputs were verified at 7 seconds, 168 frames, 1080 × 1920, 24 fps, and
loop-return PSNR above 45 dB. They retain parent-reference provenance and do
not overwrite the first review.

## Follow-up: White Balance round 3

Danny proposed a new animation language based on the enjoyable part of editing
a portrait in Lightroom Classic: moving a small number of Develop sliders while
searching for accurate skin color and tone. The first isolated test uses
Temperature and Tint only.

Fifteen image-only candidates now provide five behaviors for each portrait: an
unchanged export reference, a Temperature search, a Tint search, a sequential
Temperature-then-Tint correction, and coupled fine-tuning. No Lightroom user
interface, geometric motion, grain, audio, or text is embedded in these files.
Every candidate returns to the approved JPEG at the loop boundary.

The review page shows external, read-only Temperature and Tint sliders that are
synchronized to the exact frame. Their values make comments such as “reduce the
warm peak from +6 to +4” precise without putting controls in the finished work.
The numbers are stable HPR diagnostic deltas, not purported Lightroom units;
`0` always identifies the approved Lightroom export.

All 15 outputs were decoded and verified at 7 seconds, 168 frames, 1080 × 1920,
and 24 fps. First-to-last-frame PSNR was at least 53.348 dB across the set. The
complete specification is in [White Balance animation](../components/video-generator/docs/WHITE-BALANCE-ANIMATION.md).

## Follow-up: extreme White Balance boundary test

To make the color direction easier to judge, a fourth, separately versioned
review set expands the diagnostic Temperature and Tint range from `-10`–`+10`
to `-100`–`+100`. The earlier round remains intact. Fifteen new image-only
candidates were rendered and verified at the same 7-second, 168-frame,
1080 × 1920, 24 fps specification; their channel gains span approximately
0.85–1.15 and their loop-return PSNR is at least 48.300 dB.

The local review page now presents the portrait at a compact mobile-oriented
size—up to 280 pixels wide on phones—with the expanded synchronized diagnostic
sliders directly below it. No controls are embedded in the video.
