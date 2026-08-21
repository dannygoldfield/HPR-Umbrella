# HPR local review interface

This is the smallest functional review surface for HPR candidates. It runs
only on the local computer and writes every human decision directly to the
SQLite Registry. JSON manifests remain provenance records, not forms Danny has
to edit.

The Infinity comparison is complete. Review rejected the static-number and
moving-blob round `IBS-001`–`IBS-003` and locked `IBK-001`: gently moving
`#edeae3` numbers on `#f7f5ef`, with no blobs. The selected Infinity composite
also contains the five-star `PDE-002` portrait treatment. The blob rounds remain
available unchanged as research history.

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

For production, `IBK-001` uses one fixed speed and closed two-dimensional motion
path. Portrait-specific deterministic number layouts and starting phases keep
the 40 Infinity videos related without making a future grid move in lockstep.
`PDE-002` remains unchanged; grain, audio, and editorial text are absent.

The active film-grain review set is `film-grain-composite-v21`. It contains 21
candidates: the same seven `FGC-001`–`FGC-007` treatments for 10000,
NYChildren, and Infinity. The first two retain their locked `PDE-002`
Development Animation; Infinity retains the complete selected `IBK-001`
composite. A read-only panel shows film format, Light/Heavy source, mix
percentage, plate filename, starting frame, luma-only color handling, and the
unchanged parent visual. The raw grain plates are never served by the review
interface. The grain-only v20 diagnostic remains registered as superseded
research but is omitted from the normal review-set menu.

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
