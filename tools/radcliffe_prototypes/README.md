# Radcliffe Yard application review

This focused AV Assembler entry point pairs the three locked five-star visuals
with ten explicit, independently human-approved native eleven-second tracks.
It imports the existing assembler's technical checks, copies the video stream,
and encodes AAC at 320 kb/s with no audio filters or gain changes.

Both standalone generators must match the strict component lock. Each chosen
track must have a current explicit audio approval and `banked` availability;
`banked` alone and a star rating alone do not qualify. Seven- and nine-second
families cannot enter this eleven-second round. The selected audio IDs and the
exact approval rows are preserved in the private output provenance.

From the Umbrella root, use Python 3.11 or later:

```sh
python3 tools/radcliffe_prototypes/build_review.py \
  --output workspace/Radcliffe-Yard-HPR-Application/review \
  --audio-id APPROVED_ID_01 --audio-id APPROVED_ID_02 \
  --audio-id APPROVED_ID_03 --audio-id APPROVED_ID_04 \
  --audio-id APPROVED_ID_05 --audio-id APPROVED_ID_06 \
  --audio-id APPROVED_ID_07 --audio-id APPROVED_ID_08 \
  --audio-id APPROVED_ID_09 --audio-id APPROVED_ID_10
```

The IDs are explicit to preserve editorial reservations for other portraits.
Use a new output directory for each review. Existing files are never overwritten.
Open the resulting `index.html` locally, or serve just that private review folder
on `127.0.0.1`. Do not publish it. The page's choices are drafts; confirm the
three choices in the HPR task before recording final pair approvals and masters.

The Registry is read-only throughout this preparation. This keeps prior
superseded pair experiments and their reviews intact. The review manifest is an
audition set, not a duplicate generator or an alternative approval database.

The output includes thirty MP4 comparisons, per-pair checks and fingerprints,
the source manifests, approved review rows, component locks, and source-file
checksums. Source WAV levels, AAC levels/peaks, stream start times/durations,
video packet identity, and full-file decoding are checked. The approved visual
source states match at the loop boundary, but decoded H.264 endpoint pixels are
not mathematically identical. Perceptual audio/video loop approval remains human.

Final application files are created only after three explicit soundtrack
selections and final AV loop review. All private media and provenance stay under
the existing ignored `workspace/` directory.
