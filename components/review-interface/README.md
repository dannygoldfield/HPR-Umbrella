# HPR local review interface

This is the functional review surface for HPR candidates. It runs
only on the local computer and writes every human decision directly to the
SQLite Registry. JSON manifests remain provenance records, not forms Danny has
to edit.

The Infinity comparison is complete. Review rejected the static-number and
moving-blob round `IBS-001`–`IBS-003`, then superseded the moving `IBK-001`
field with `IBN-001`: completely static `#edeae3` numbers on `#f7f5ef`, with
no blobs. The selected Infinity composite also contains the five-star `PDE-002`
portrait treatment. The moving and blob rounds remain available unchanged as
research history.

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

For production, `IBN-001` holds every background digit completely still.
Portrait identity deterministically changes which digits occupy the fixed grid,
so the 40 Infinity videos remain related but each has a unique layout. There is
no background phase or motion path. `PDE-002` remains the only visual motion;
film grain is disabled under the production policy, while audio and editorial
text remain pending.

The default review set is now **Pair Review — NYChildren (10 audio options)**.
It uses one locked, selected 11-second visual and ten distinct, native
11-second `AR-010` audio candidates. The video player is unmuted in pair mode;
press Play to hear each option. Audio and complete-pair ratings are independent.
Unused audio is visibly marked **Available in audio bank** and requires no
manual Bank toggle. **Select pair** retires that audio from future final use,
**Reject pair** leaves its audio banked, and **Retire audio** is reserved for
sound that should not be reused with another portrait.

The **Production visuals — no film grain** set contains
the selected NYChildren and 10000 `PDE-002` candidates and the selected
Infinity `IBN-001` composite. The completed `film-grain-opacity-v25` set remains
available as research history: 13 10000 candidates using the same Super 35
Light sample at opacities from 10% through 40%. Its read-only panel records the
exact settings; raw grain plates are never served.

The desktop layout is constrained to the browser viewport and verified for the
default 14-inch MacBook Pro scale. Candidate details and effect settings are
collapsible, leaving the portrait, rating, decisions, notes, and navigation in
one uncluttered review surface. At smaller windows, each column scrolls inside
the viewport; phones continue to use the stacked layout.

## Start it

From the repository root:

```bash
PYTHONPATH=components/registry/src:components/review-interface/src \
python -m hpr_review.server --db workspace/registry/hpr.sqlite3
```

It opens `http://127.0.0.1:8765/` in the default browser. Nothing is sent to a
public server. To review temporarily from an iPhone on the same trusted Wi-Fi,
start a second instance with `--host 0.0.0.0 --port 8766 --no-browser`, open the
Mac's local-network address ending in `:8766` on the phone, and stop that server
after review.

Keyboard shortcuts: 1–5 set the visual or complete-pair rating, R toggles
reject, S toggles selection, T retires audio in pair mode, left/right arrows
navigate, and Space pauses or resumes the video. Audio ratings use their own
visible buttons so the two judgments cannot be confused.
