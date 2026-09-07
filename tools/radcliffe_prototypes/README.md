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


## Three-pass delivery after creative selection

After the user explicitly chooses one option per portrait, `prepare_selected.py`
creates 33-second application samples: three exact eleven-second visual passes
and three exact source-WAV passes encoded together in one continuous AAC stream.
This avoids a player restart and separate AAC encoder boundaries at 11 and 22
seconds. It does not modify the native audio family or either generator.

Supply `--review` (the prior review folder), a new `--output` directory, and
three `--selection PROJECT=OPTION` arguments using the keys `10000`,
`NYChildren`, and `Infinity`. Options must be the user's explicit choices.
The command preserves the selected eleven-second references, verifies 792 exact
video packets and continuous timestamps, checks the exact repeated PCM input,
measures output level/peaks, and screens decoded audio at both internal joins.

The Registry is backed up before appending creative pair selections. Audio is
reserved with `reserved_loop_pending`; the three prototype master records use
`loop_pending` and a null `approved_at`. Prior source approvals and all research
history are preserved. Technical screening cannot grant human loop approval.
The resulting review page plays each 33-second file once, without browser looping.
Use `--no-register` to reproduce deliveries in a new folder without duplicating
or changing the existing Registry decisions.


## Extend an existing development comparison

Keep the existing 100%, 125%, and 150% files, all audio, and all Infinity field
comparisons. For each original visual manifest in the selected-prototypes
`selections.json`, independently render 175% and 200% silent candidates in
HPR Video Generator:

```sh
python3 tools/prototype_iteration.py --manifest ORIGINAL_VISUAL_MANIFEST \
  --output media/output/candidates/NEW_EXTENSION/PROJECT-develop-175.mp4 --strength 1.75
python3 tools/prototype_iteration.py --manifest ORIGINAL_VISUAL_MANIFEST \
  --output media/output/candidates/NEW_EXTENSION/PROJECT-develop-200.mp4 --strength 2
```

Use project keys `10000`, `NYChildren`, and `Infinity`. These commands require
NumPy, Pillow, and FFmpeg. For strengths above 150%, the generator extends the
same photographic RGB excursion relative to the finished source, before
Infinity subject compositing. Timing, geometry, alpha, and number field remain
unchanged. Values are limited only to the physical RGB range; the reveal mask
is never clipped into a flat hold. Earlier strength output is unchanged.

With the generator commit recorded in the strict component lock, run in Umbrella:

```sh
python3 tools/radcliffe_prototypes/extend_development_review.py \
  --review workspace/EXISTING_REVIEW \
  --visuals ../HPR-Video-Generator/media/output/candidates/NEW_EXTENSION
```

The extension verifies the complete existing inventory, snapshots the prior
review documents, checks original-source identity, and adds six continuously
encoded 33-second silent samples. It tests exact repeated native input frames,
continuous timestamps, decoded joins, and complete decoding. Existing media is
fingerprinted again before updating the page. The initial preview becomes 150%;
no choice or approval is granted, and browser draft choices are retained.
The Registry and both audio families and audio files remain untouched.
This append operation deliberately refuses a previously extended folder.


## Compare further bed reductions

The selected native eleven-second compositions can be independently rebuilt by
Audio Generator with `tools/prototype_bed_reduction.py`. The optional
`--bed-gain .75` reduces bed amplitude by 25%; `--bed-gain .5` reduces it by 50%.
The default `.9` retains the earlier 10% behavior and candidate identity.
For each selected original audio manifest, use a new candidate output folder:

```sh
PYTHONPATH=src:tools python3 tools/prototype_bed_reduction.py \
  --source-manifest ORIGINAL_AUDIO_MANIFEST --config config/generator.xml \
  --output audio/output/candidates/NEW_BED_COMPARISON --bed-gain .75
```

Repeat for `.5` and each of the three selected soundtracks. Each build must
reproduce the original raw mix exactly and prove, sample by sample, that the
foreground residual is unchanged and only the periodic bed was scaled. The
original master gain is retained; there is no new whole-mix normalization.
Original waveform and source/configuration/code fingerprints, loudness, peak,
and loop checks accompany each native candidate. Human approval stays pending.

After updating the strict audio component lock, run in Umbrella:

```sh
python3 tools/radcliffe_prototypes/extend_audio_review.py \
  --review workspace/EXISTING_REVIEW \
  --audio ../HPR-Audio-Generator/audio/output/candidates/NEW_BED_COMPARISON
```

The extension preserves the existing review and browser storage key, snapshots
prior review documents, and appends six 33-second WAVs as three exact PCM passes.
It verifies original-source identity, bed-only proof, peak and join screening,
and unchanged earlier media. The Sound tab lists original, 10%, 25%, and 50%
bed reductions. Percentages describe amplitude attenuation, not perceived
loudness. The `#sound` link opens that comparison directly. No Registry records
or visual choices are changed.


## Reliable local review playback

Serve the review with byte-range support so both audio and video can seek,
load metadata promptly, and switch previews without restarting unexpectedly:

```sh
python3 tools/radcliffe_prototypes/serve_review.py \
  --review workspace/Radcliffe-Yard-HPR-Next-Iteration-2026-09-07-v2 --port 8769
```

The server binds only to `127.0.0.1`. Keep the original host and port to retain
browser draft choices. It supports partial media requests and revalidation of
updated pages. The review has an in-page Reload review button; choice buttons
show their selected state, saved develop previews are restored, and updates
merge the latest saved draft so another tab's selections are preserved.
Hidden media waits until its section is opened. Preview switches cancel stale
loads, group playback can be cancelled, and quick audio changes retain the
latest requested track.

The server regression test is `tests/test_serve_review.py`. For browser
regression checks, serve an isolated copy on port 18769, then run
`tests/test_review_browser.cjs` with Node and Playwright. Set
`HPR_PLAYWRIGHT_MODULE` to the installed Playwright module when needed and
`HPR_REVIEW_TEST_URL` to the isolated test origin. The test always creates a
fresh browser context and uses synthetic draft choices. It checks all three
sections, rapid switching, seeking, reload, choice feedback and preservation,
Infinity's four players and joins, cancellation, and mobile layout.
