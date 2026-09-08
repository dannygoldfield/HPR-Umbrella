# HPR Candidate Engine and AV Assembler

This component plans finite candidate sets and assembles approved silent visuals
with independently approved audio. It is the code currently referred to as the
**AV Assembler**. It does not contain either generator and it does not select
the final work.

## Responsibilities

1. Plan separate Visual, Audio, Pair, and Publishing banks.
2. Accept one selected silent visual and compatible approved audio candidates.
3. Mux each pair without re-encoding the picture or remixing the soundtrack.
4. Write a JSON provenance manifest beside every review candidate.
5. Preserve visual and audio judgments independently from pair judgments.

## Plan without rendering

```bash
hpr-candidate plan \
  --portrait workspace/portraits/example.tif \
  --grain workspace/grain/filmgrain.mov \
  --duration 7 \
  --video-preset VP-002 \
  --audio-recipe AR-008 \
  --seed 2026080201 \
  --count 3
```

The older `generate` convenience command remains reproducible, but it resolves
the exact standalone repositories locked by HPR Umbrella. The active production
pairing command is `tools/assemble_pair_round/assemble_pair_round.py`, which
accepts only human-banked audio and a selected visual.

If `--audio-recipe` is omitted, the generator selects the current production recipe for the requested duration: AR-008 for 7 seconds, AR-009 for 9 seconds, or the stem-based AR-011 for 11 seconds.
