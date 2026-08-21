# Film Grain Animation

Status: active finishing test after the Development Animation and Infinity
background decisions were locked on 2026-08-20.

## Creative purpose

Film Grain Animation should make the photographed surface feel continuously
alive even when the subject and camera do not move. It is the smallest and
fastest visual event in the HPR system. It must support human presence rather
than announce a vintage treatment.

The active reference is Steven Spielberg's description of grain as always
moving or “swimming,” allowing a still subject to remain alive. HPR adopts the
underlying principle, not a period-film look.

## Order of operations

Grain is a finishing layer:

1. Render the locked `PDE-002` Development Animation.
2. For Infinity, composite the locked `IBK-001` number background.
3. Apply grain to the complete approved visual.
4. Add and review audio.
5. Create the release master only after both visual and audio decisions lock.

Applying grain last lets one treatment unify the portrait, background, and
graphic field. It also means the Development Animation and Infinity background
remain independently reproducible.

## Source and rights record

The locally managed scans were downloaded from the TDCatTech/LightKino film
grain page:

- Page: <https://tdcat.com/downloads/filmgrain>
- Permission wording observed 2026-08-20: “free to download and use as you wish”
- Format: 4096 × 2160 ProRes 422 HQ, 10-bit, 24 fps, 15 seconds
- Local policy: retain raw plates locally; never commit, redistribute, or expose
  them as downloadable project assets

Each candidate manifest records the exact plate filename and SHA-256 checksum.
This keeps the public repository reproducible without containing the licensed
media itself.

## Image model

The grain plate is converted to a neutral grayscale signal and composited only
into the approved video's luma plane. The original chroma planes pass through
unchanged. The current test uses Overlay because the supplied scans are
centered around neutral gray:

```text
output_luma = overlay(base_luma, grain_luma, opacity)
output_chroma = base_chroma
```

The output returns to 4:2:0 only at delivery encoding and carries complete
limited-range BT.709 characteristics. Geometry never changes.

## Layer-completeness comparison: `film-grain-composite-v21`

This round applied the same seven recipes to all three complete locked
visuals. This makes the layer stack explicit in every test:

1. the photograph stays fixed in the frame;
2. the five-star `PDE-002` Development Animation remains active;
3. Infinity also retains the shipped `IBK-001` moving-number background;
4. film grain is applied last to the complete image.

The renderer uses `VIS-30FE48FB73CE-PDE-002` for NYChildren,
`VIS-90500D66EBBF-PDE-002` for 10000, and
`VIS-4DF5D853ACDA-IBK-001` for Infinity. A decoded registration audit at five
points in each representative medium-grain candidate measured zero horizontal
and zero vertical displacement from its parent visual.

| ID | Treatment | Purpose |
| --- | --- | --- |
| `FGC-001` | No-grain transcode control | Separate grain from delivery re-encoding |
| `FGC-002` | Super 35 Light at 6% | Subtle visibility boundary |
| `FGC-003` | 35mm Light at 12% | Finer-grain character |
| `FGC-004` | Super 35 Light at 12% | Existing-source medium control |
| `FGC-005` | 16mm Light at 12% | Coarser-grain character |
| `FGC-006` | Super 35 Heavy at 12% | Denser source boundary |
| `FGC-007` | Super 35 Light at 20% | Strong visibility boundary |

The review found no visible difference among the 21 candidates. Measurement at
the 280-pixel-wide review size confirmed why: the strongest candidate changed
the image by only 0.726 display-code values on average, with no pixels changing
by more than four values. Fine scanned grain had been averaged away by delivery
compression and display reduction. V21 is therefore failed visibility research,
not a grain-character decision.

## Active visibility calibration: `film-grain-visibility-v22`

V22 uses the fixed-camera 10000 `PDE-002` parent and one Super 35 Light plate.
It varies only delivered grain size and signal magnitude so the visibility
threshold can be found before repeating a cross-portrait comparison.

| ID | Texture scale | Signal gain | Mix | Purpose |
| --- | ---: | ---: | ---: | --- |
| `FGV-001` | 1.0× | 1.0× | 0% | No-grain control |
| `FGV-002` | 1.0× | 1.0× | 50% | Native-grain lower boundary |
| `FGV-003` | 1.0× | 1.0× | 100% | Full native scanned signal |
| `FGV-004` | 1.5× | 1.5× | 65% | Moderately enlarged grain |
| `FGV-005` | 2.0× | 2.0× | 65% | Clearly visible grain |
| `FGV-006` | 2.0× | 3.0× | 85% | Strong boundary |
| `FGV-007` | 2.5× | 4.0× | 100% | Intentionally excessive boundary |

At review size, the new sequence progresses from 1.125 average display-code
change in `FGV-002` to 12.436 in `FGV-007`; the share of pixels changing by
more than four values rises from 0.22% to 73.62%. This is a genuine visible
range. Grain size and signal gain are recorded separately in every manifest.

## Review questions

- Does the surface feel alive before the viewer consciously identifies grain?
- Is grain visible on skin at mobile review size without competing with eyes or
  expression?
- Does the grain remain photographic rather than digital noise?
- Does the grain survive browser playback without turning into compression
  smearing?
- Is there any brightness pulse or recognizable reset at the loop boundary?
- Does the coarser material exaggerate wrinkles or make skin feel harsh?
- Does Heavy read as atmosphere, or merely as an effect?

Reject a candidate for color drift, dirt or scratches, gate weave, flicker,
skin harshness, a visible loop pulse, or grain that disappears after ordinary
web playback.

## Production uniqueness after selection

The chosen stock, opacity, and playback speed remain consistent across the 120
portraits. Each portrait receives deterministic variation in only two places:

- the starting frame within the 15-second scan;
- the horizontal crop within the wide 4K plate.

Those variations keep the grain realization unique without creating a new
style or tempo for every portrait. Multiple videos viewed together therefore
share one material character but do not display identical grain patterns.

The earlier seven-candidate 10000 round v19 remains reproducible. A temporary
v20 grain-only diagnostic removed Development Animation to isolate the apparent
motion report; that was not the desired creative test. V21 restored the proper
three-layer stack but failed visibility. V22 is the current decision set. Once
a credible visible range is found, test only that range on NYChildren and the
complete Infinity composite.
