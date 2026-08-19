# HPR local review interface

This is the smallest functional review surface for HPR candidates. It runs
only on the local computer and writes every human decision directly to the
SQLite Registry. JSON manifests remain provenance records, not forms Danny has
to edit.

The active review family is the seven-candidate Infinity visibility-calibration
round, `IBV-001`–`IBV-007`. Every candidate holds the five-star `PDE-002`
subject treatment, subject geometry, light background foundation, timing, and
delivery format constant. Only the separately supplied Background layer
changes. The imperceptibly restrained `INF` round, the 65% landing round, and
all earlier research sets remain available unchanged.

The visual-review screen provides looping video, 1–5 rating, reject, notes,
selection, render/review status, and a provenance link. Episode is explicitly
shown as unassigned because the Archive sequence is chosen from completed
masters at the end of production.

The review-set menu separates the possible-finals set, the 11-second Portrait
Development TIFF round, Portrait Development round 1, both White Balance
rounds, the original rhythm pilot, motion-variable round 2, and the complete
candidate history. Motion round 2 places each previously selected visual first
as a reference, followed by its four new one-variable probes.

White Balance round 3 keeps every video image-only. When one of these candidates
is playing, the page displays separate Temperature and Tint sliders below the
video, synchronized to the exact video frame. The sliders are read-only review
references and never appear inside the exported video. Their values are HPR
diagnostic deltas rather than Lightroom Classic units: `0` is the approved JPEG
export, negative/positive Temperature are cooler/warmer, and negative/positive
Tint are greener/more magenta.

The compact layout is designed for likely mobile review. The portrait preview
is limited to 300 pixels wide on larger screens and 280 pixels wide on phones,
with the synchronized sliders immediately below it. The separately versioned
White Balance extreme test expands both diagnostic scales from `-100` to `+100`
so the direction and character of the shift are easy to see. Round 3 remains
available unchanged in the review-set menu.

Portrait Development candidates remain image-only. Their separate reference
shows the synchronized mean percentage of the untouched finished portrait
revealed and the local minimum–maximum range. It is diagnostic information for
precise feedback and never appears in the exported video.

The same diagnostic card now exposes the exact saved minimum-final, finished
pause, speed, feather, and patch values for every development candidate. This
makes it possible to compare prior rounds or request an interpolated setting
between two tests without estimating from memory.

For the active Infinity set, compare momentum wake, photographic emulsion bloom,
floating photographic print, negative-space aperture, residual gesture,
incomplete geometry, and borrowed-color field. The diagnostic card names the
effect, states its intent, and confirms that `PDE-002` remains unchanged. Grain,
audio, and text are absent. The `IBV` card also shows the recipe's visibility
boost, peak mean 8-bit display-code change, and active background area so a
later refinement can be placed numerically between rounds.

## Start it

From the repository root:

```bash
PYTHONPATH=components/registry/src:components/review-interface/src \
python -m hpr_review.server --db workspace/registry/hpr.sqlite3
```

It opens `http://127.0.0.1:8765/` in the default browser. Nothing is sent to a
public server.

Keyboard shortcuts: 1–5 set the rating, R toggles reject, S toggles selection,
left/right arrows navigate, and Space pauses or resumes the video.
