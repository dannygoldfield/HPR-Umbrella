# Current State

Updated: 2026-08-20

## Permanent decisions

- The SQLite HPR Registry is the authoritative operational record.
- Portrait identity is permanent; episode number is deferred release order.
- The final custom sequence is chosen only after completed visual-and-audio masters can be reviewed.
- Archive production is the current focus; Now mode is deferred.
- Audio, Video, and future Text are plugins coordinated by the engine.
- The production target is 120 archive videos: 40 portraits of people age 100 or older, 40 portraits of people age 12 or younger, and 40 mixed-age portraits involving the number prop.
- The active visual direction is Portrait Development Animation: fixed geometry
  with evolving tone, skin color, surface detail, and restrained texture.
- Camera movement, Ken Burns-style motion, warping, displacement, and facial
  deformation are outside the active testing plan.
- The settled soft sweep `PDE-002` is the portrait-surface baseline: it received
  a five-star rating for 10000, NYChildren, and Infinity. Motion-picture grain
  remains a later finishing decision for all three.
- Each portrait initially receives five constrained development candidates;
  visible mechanism or novelty is a failure mode.
- The audio bank contains 150 unique tracks: 50 per duration.
- A selected visual receives 10 audio pairing options.
- Every final video uses a unique audio track, retired after selection.
- Visual, Audio, Pair, and Publishing banks remain separate.
- Human judgment is recorded, never inferred. A bad pair does not invalidate its components.
- Photo exports can be replaced without losing visual
  recipe, audio, text, or publication decisions.
- Text is optional, nondestructive, and considered after the audio-video master is ready.
- Preserve metadata for every candidate; permanently retain selected masters and banked assets, while disposable renders may be regenerated.
- Lightroom Classic remains authoritative for source-photo edits and source metadata.
- The finished Lightroom export is the authoritative maximum. The active pilot
  creates a deliberately under-resolved surrogate and only reveals toward the
  untouched finished pixels; it never claims to recover information absent
  from the source or to reproduce Lightroom controls.
- Intake JPEGs retain their original filenames; numbered names are created only at release.

## Implemented system and research history

- Reusable JPEG/TIFF inspector for EXIF, IPTC, and XMP with Markdown and JSON output.
- Three-portrait Lightroom metadata survival report and final metadata contract.
- SQLite Registry schema and CLI for source projects, portraits, revisions,
  candidate/review records, final masters, deferred sequences, and publication records.
- Idempotent metadata-report ingestion with per-revision provenance manifests.
- Three pilot portraits ingested as revision 1 with no episode numbers.
- Versioned draft sequencing that assigns episode numbers only when a complete sequence locks.
- Five versioned, loop-safe motion-rhythm recipes with exact frame timelines.
- Fifteen seven-second pilot MP4s rendered and registered: three portraits by
  five rhythms, all 1080 × 1920, 24 fps, 168 frames, and without grain or audio.
- Reproducible JSON provenance beside every pilot render.
- Functional local visual-review screen writing 1–5 ratings, rejection, notes,
  and selection directly to the Registry while preserving review history.
- First rhythm review completed: MR-005 selected for `bahamas.210` and
  `26-Sam-135-Edit`; MR-004 selected for `new_jersey_m_0180`.
- Motion-variable round 2 adds 12 registered candidates while retaining the
  three selected originals as references. It isolates lower scale amplitude,
  higher scale amplitude, horizontal micro-movement, and vertical
  micro-movement.
- Registry experiment and parent-candidate provenance, plus selectable review
  sets in the local interface.
- White Balance round 3 adds 15 image-only candidates: a neutral reference and
  four Temperature/Tint adjustment behaviors for each pilot portrait. No
  Lightroom controls, geometric movement, audio, or grain appear in the video.
- The review interface displays separate read-only Temperature and Tint sliders
  synchronized to the exact rendered frame. These are HPR diagnostic deltas,
  not Lightroom units; `0` means the approved Lightroom JPEG export.
- White Balance extreme test adds 15 separately versioned candidates with an
  intentionally obvious `-100` to `+100` diagnostic range. The earlier round
  remains unchanged for comparison.
- The review screen now uses a compact, mobile-first portrait preview: up to
  300 pixels wide on larger screens and 280 pixels wide on phones.
- The [Portrait Development Animation](components/video-generator/docs/PORTRAIT-DEVELOPMENT-ANIMATION.md)
  creative, computational, parameter, and test specification is now the active
  visual R&D plan.
- Motion-rhythm, motion-variable, and White Balance-only candidates are retained
  as reproducible research history. They are no longer the active visual test.
- Portrait Development round 1 adds 15 registered image-only candidates: a
  static final reference plus global development, broad sparse activation,
  overlapping swells, and a soft diagonal sweep for each pilot portrait.
- Every round-1 development candidate is fixed-geometry, one-direction
  surrogate-to-final, silent, without grain or text, 1080 × 1920, 24 fps,
  seven seconds, and 168 frames. The Registry now contains 72 visuals.
- The review interface shows a synchronized percentage of the untouched final
  portrait revealed, including the local spatial range, outside the video.
- The film-grain source is recorded for later testing but intentionally omitted
  until the development behavior is evaluated.
- The second Portrait Development intake uses native 16-bit TIFFs for
  NYChildren, 10000, and Infinity. All 11 tested Lightroom metadata fields
  survive in every file. The 10000 TIFF is revision 2 of its existing portrait;
  the new NYChildren and Infinity photographs have new portrait identities.
- Portrait Development TIFF round 2 adds 15 registered image-only candidates:
  a finished TIFF reference, global development with a long finished rest,
  slow sparse activation, faster overlapping swells, and an unhurried soft
  sweep for each portrait.
- Every round-2 candidate is 11 seconds, 1080 × 1920, 24 fps, and 264 frames.
  The source is transformed from embedded ProPhoto RGB into sRGB in native
  16-bit precision, the compositor stays 16-bit until delivery conversion, and
  the H.264 output carries complete BT.709 characteristics. Grain, audio, text,
  and Infinity background separation remain deferred. The Registry now
  contains 87 visual candidates.
- The round-2 review favored sparse activation and the soft sweep. The fully
  finished pause felt too long; the approved refinement is 40% of the prior
  pause, or about 1.4 seconds total around the 11-second loop boundary.
- The possible-finals intake replaces NYChildren with
  `israel.batel.oshrat.398.tif`, whose eyes are sharp, and records the adjusted
  full-resolution Infinity edit as revision 2. 10000 remains unchanged as its
  revision 2 control. Every finalist source meets or exceeds 1080 × 1920.
- Portrait Development possible-finals round adds nine registered candidates:
  refined sparse activation, refined soft sweep, and an intentionally
  assertive sparse boundary test for each portrait. All remain fixed-geometry,
  11 seconds, 24 fps, 264 frames, 16-bit through compositing, H.264/BT.709,
  silent, and without grain or text. The Registry now contains 96 visual
  candidates. Infinity background ideation remains a separate later decision.
- The visibility-boundary round records the exposure-corrected NYChildren TIFF
  as revision 2 and adds nine deliberately noticeable candidates. Daring sparse
  activation and daring sweep retain only a 25% finished-image floor; the
  deliberate ceiling test reaches the full under-resolved state. Pauses shorten
  again and feathering is reduced. All three portraits receive the same hard
  push. The Registry now contains 105 visual candidates.
- All nine visibility-boundary candidates received a latest rating of 4. The
  settlement round therefore interpolates every continuous parameter in each
  matching recipe 65% of the way from the possible-finals round toward the
  visibility-boundary round. The first two recipes now retain a 40.75%
  finished-image floor; the activation ceiling retains 17.5%. Integer patch
  counts use the nearest practical whole number. Nine registered `PDE`
  candidates passed 11-second, 264-frame, BT.709, fixed-geometry, and decoded
  loop-closure audits. The Registry now contains 114 visual candidates.
- Every development candidate remains available in its original review set.
  The review interface now displays saved minimum-final, finished-pause, speed,
  feather, and patch values beside the synchronized diagnostic so an eventual
  setting can be chosen numerically between rounds.
- Infinity layered-background round v10 uses the supplied 153 MB Photoshop TIFF:
  2104 × 3740, 16-bit, ProPhoto RGB, with separate `Subject` and `Background`
  layers. Seven background-only concepts are registered: momentum wake,
  photographic emulsion bloom, floating photographic print, negative-space
  aperture, residual gesture, incomplete geometry, and borrowed-color field.
  Each holds `PDE-002` and subject geometry constant, begins and ends on the
  supplied light background, and omits grain, audio, and text. All seven passed
  11-second, 264-frame, BT.709, provenance, fixed-geometry, and decoded
  loop-closure audits. The Registry now contains 121 visual candidates.
- Human review found the seven v10 backgrounds indistinguishable at the
  mobile-sized preview. Measurement confirmed that several delivered effects
  averaged only one or two 8-bit display-code changes. The former unit check
  proved only non-identical pixels and was not a valid perceptual acceptance
  test; v10 is retained as failed research evidence.
- Infinity visibility-calibration round v11 preserves the same seven concepts
  under `IBV-001`–`IBV-007`, increases their contrast, coverage, displacement,
  or graphic weight, and may deliberately go too far. Every recipe declares
  minimum mean, 95th-percentile, and active-area visibility values measured in
  8-bit display-code terms. Rendering stops when a minimum is missed. All seven
  passed those gates plus the 11-second, 264-frame, BT.709, fixed-geometry, and
  decoded loop-closure audits. The Registry now contains 128 visuals.
- Human review found the v11 visibility-calibration round creatively
  unsuccessful: only one of seven effects was visible, and that one was weak.
  The metrics proved pixel change but not a recognizable visual event. V11 is
  retained unchanged as failed research evidence.
- Infinity sketch-directed round v12 translates Danny's reference sketches into
  seven different spatial constructions: three Brandon Grotesque number fields,
  a moving gradient curtain, a sliding panel, a hinged perspective door, and a
  number doorway. All hold `PDE-002`, the isolated subject, and the supplied
  light background constant. The seven 11-second candidates are registered as
  `IBC-001`–`IBC-007`; the Registry now contains 135 visual candidates.
- V12 review established that the numbers must remain two-dimensional; z-axis
  travel is rejected. The v13 response round adds two dense flat number fields
  (varied fixed sizes and one uniform size), an orderly lateral-separation
  field, a visibly stronger gradient, a full-width sliding panel, an
  eleven-second one-way door, and a dense number wipe. No digit is coordinated
  with the `26` prop. `IBF-006` and `IBF-007` intentionally reset abruptly at
  replay; the other five are continuous. The Registry now contains 142 visuals.
- V13 review rejected `IBF-003` without a repair direction and expanded the
  requested response beyond seven options. The v14 directed-variation round
  therefore registers eleven candidates as `IBR-001`–`IBR-011`: three bold
  fixed-size number fields with coordinated motion, three gradient direction or
  palette studies, two one-way panel lightness pairs, an accelerating hinged
  door, and static-versus-moving accelerating number wipes. `IBR-001` uses 420
  balanced single digits and measures 57.2% active background in the finished
  render. `IBR-007`–`IBR-011` intentionally cut back to their first frame;
  `IBR-001`–`IBR-006` close continuously. All values are deterministic and
  recorded. The Registry now contains 153 visuals.
- V14 review repeatedly requested lower contrast and established an exact
  background palette: `#f0eee9` and `#f7f5ef`. V15 registers eleven corrected
  candidates as `IBP-001`–`IBP-011` and permits no other graphic neutral.
  Columns are slower and bleed beyond the frame, panels compare two accelerating
  rhythms, the door edge is substantially softer, wipe digits abandon visible
  rows and columns, and `IBP-011` moves its irregular number field opposite the
  wipe. All eleven are rendered and registered; the Registry now contains 164
  visuals.
- Mobile review found all eleven v15 backgrounds indistinguishable. The palette
  differs by only seven, seven, and six 8-bit RGB codes, and the generator's
  normal half-strength mix ceiling reduced the delivered signal again. V16 is a
  six-candidate contrast-survival calibration rather than another eleven-effect
  creative round. `IBK-001`–`IBK-006` compare `#edeae3`, `#e8e4dc`, and
  `#e2ddd4` against fixed `#f7f5ef`, each in matched thin-number and broad-panel
  constructions at an explicitly recorded full color mix. All six are rendered
  and registered; the Registry now contains 170 visuals.

## Earlier implemented work

- Archive production planner and domain records.
- Deterministic 120-episode / 600-visual / 150-audio dry run.
- Separate Episode, Visual, Audio, Pair, and Publishing bank files.
- Duration-compatible pairing options that exclude retired audio.
- Independent visual/audio/pair review fields.
- Photo replacement that preserves the creative assembly and marks dependent renders stale.

## Next production work

1. Review `IBK-001`–`IBK-006` at normal phone size and choose the lightest darker
   endpoint that is still clearly visible in both thin numbers and the broad
   panel. This round calibrates contrast only; do not select a shipping effect
   from it. Use the chosen contrast interval to rebuild the creative family.
2. Freeze `PDE-002` as the portrait-surface treatment for 10000 and NYChildren;
   freeze Infinity after its background decision.
3. Continue using embedded-profile 16-bit TIFF as the preferred portrait
   source. Seven Lightroom stage exports remain an optional calibration
   experiment, not a requirement for every portrait or video.
4. Test the recorded film-grain source after the Infinity background decision,
   applying it uniformly after development and background compositing.
5. After shippable visuals are selected, connect them to selected Audio
   Generator tracks and complete pair review.
6. Test one completed video on both the visible and structured-data development
   site pages, then schedule one clearly labeled disposable test post through
   Buffer. Do not begin those external publication steps before a visual/audio
   pair is approved.
7. Replace the legacy early `EpisodeRecord` planner with Registry-backed portrait work records.
8. Add a friendly completed-master sequence view or Lightroom interchange and
   test it before planning the full 120-portrait production run.
