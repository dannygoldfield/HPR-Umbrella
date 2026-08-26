# Assemble Pair Round

This is the thin HPR AV Assembler. It does not generate or remix sound and it
does not render portrait animation. It combines one selected 11-second visual
with exactly ten explicit, registered 11-second audio candidates.

The assembler verifies source fingerprints, native duration, video dimensions,
frame rate, audio format, and the absence of a meaningful loudness change after
AAC delivery encoding. The video stream is copied without re-encoding and no
audio filter is applied.

The review interface offers three mutually exclusive outcomes:

- **Select pair** assigns that soundtrack to the portrait.
- **Bank audio** rejects the pairing but keeps the soundtrack reusable.
- **Reject audio** rejects the pairing and removes the bad mix from the bank.

The caller supplies ten `--audio-id` arguments in the desired review order.
This keeps the rolling pool explicit and reproducible.
