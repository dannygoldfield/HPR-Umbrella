# Infinity Background Animation

## Decision context

The portrait-surface treatment is no longer a variable in this experiment.
`PDE-002`, the settled soft sweep, received five stars for all three pilot
portraits. Infinity alone has a separately supplied background layer, so this
round tests whether restrained background activity adds presence without
turning the portrait into an illustration.

## Source contract

- Layered TIFF: `26-Sam-359-LAYERS.tif`
- 2104 × 3740, 16 bits per channel, ProPhoto RGB
- Two visible layers: `Subject` and `Background`
- Subject has real transparency from 0 through fully opaque
- Existing light Background layer remains the foundation of every treatment
- Source TIFF is never modified

Photoshop exports 16-bit working copies of both layers. The layer pixels inherit
the authoritative TIFF's embedded ProPhoto RGB profile, then use the same
LittleCMS 16-bit conversion to sRGB as the portrait-development pipeline.

## Controlled comparison

| ID | Treatment | Intended reading |
| --- | --- | --- |
| `INF-001` | Momentum wake | The background registers the pose's implied direction without a literal trail. |
| `INF-002` | Photographic emulsion bloom | Local photographic density emerges and recedes in large organic regions. |
| `INF-003` | Floating photographic print | A soft changing cast shadow makes the cutout feel fractionally suspended. |
| `INF-004` | Negative-space aperture | Empty space opens around the face and gesture while the periphery gains density. |
| `INF-005` | Residual gesture | Faint displaced impressions suggest that the background remembers another instant. |
| `INF-006` | Incomplete geometry | Sparse arcs, points, and relationships appear without explaining themselves. |
| `INF-007` | Borrowed-color field | Large atmospheric regions borrow restrained skin and clothing colors. |

## Visibility-calibration round

The first `INF` render proved that seven files could be technically different
while remaining perceptually identical at the 280-pixel review size. Several
delivered backgrounds changed by an average of only one or two 8-bit display
codes. The original unit test also used a one-code threshold in 16-bit space,
which established mathematical non-identity rather than visible difference.

`infinity-background-visibility-v11` preserves those seven concepts under new
`IBV` identifiers so the failed round remains reproducible. Every recipe now
declares a visibility boost and three minimum display-scale measures:

- mean RGB change in familiar 8-bit code values;
- 95th-percentile RGB change;
- percentage of background pixels whose mean RGB change exceeds three codes.

The renderer refuses a candidate before compositing if any declared minimum is
missed. The seven delivered candidates span approximately 2.2–17.0 mean 8-bit
codes on the uncovered background at peak activity. The sparse geometry option
is intentionally localized; the other six affect broad areas. This is a
calibration round, so an option may be conspicuously too strong.

Human review nevertheless found only one of the seven effects visibly distinct,
and even that one was weak. The analytic floors measured pixel change but did
not prove that a viewer could recognize a coherent event. `IBV` is therefore a
second failed creative test and remains available as evidence; it is not a
candidate-final round.

| ID | Treatment | Boundary being tested |
| --- | --- | --- |
| `IBV-001` | Visible momentum wake | Directional warmth behind the gesture |
| `IBV-002` | Visible emulsion bloom | Broad overlapping photographic density |
| `IBV-003` | Visible floating print | Dimensional shadow versus cutout artifact |
| `IBV-004` | Visible negative-space aperture | Portrait vignette versus spotlight |
| `IBV-005` | Visible residual gesture | Remembered movement versus echo effect |
| `IBV-006` | Visible incomplete geometry | Relational graphic versus explanatory diagram |
| `IBV-007` | Visible borrowed-color field | Chromatic atmosphere versus tinted backdrop |

## Sketch-directed concept round

The `infinity-background-concepts-v12` round replaces abstract tonal variants
with seven explicit spatial constructions derived from Danny's Photoshop
sketches. These are not seven strengths of one effect. Each tests a different
idea and must be recognizable in an ordinary mobile-size frame before artistic
subtlety is considered.

| ID | Construction | What changes behind the subject |
| --- | --- | --- |
| `IBC-001` | Deep number field | Individual digits at several apparent depths recede toward a vanishing area. |
| `IBC-002` | Side-entering numbers | Digits enter from both side edges and diminish into depth. |
| `IBC-003` | Evasive number corridor | Larger digits curve around the pose and disappear behind the isolated subject. |
| `IBC-004` | Moving gradient curtain | A broad, low-contrast tonal curtain crosses the light field and returns. |
| `IBC-005` | Sliding panel | A legible vertical edge carries a two-dimensional panel across the background. |
| `IBC-006` | Hinged perspective door | A plane stays fixed to its left hinge while its far edge contracts away from the viewer. |
| `IBC-007` | Number doorway | Two perspective panels open to reveal a receding numerical field. |

The digits are the separate characters `1` through `9` and `0`, not multi-digit
numbers, set in Brandon Grotesque Regular. The renderer resolves the locally
licensed Adobe font by its internal family and style name. It records that name
and a local provenance hash in each private render manifest but never copies the
font file into the repository.

This round deliberately permits obvious graphic structure. A successful test
can later be softened; another imperceptible test cannot be meaningfully judged.
The subject remains in front of every construction, so its transparency creates
the apparent occlusion without moving or warping the person.

## Flat-field response round

Review of `IBC-001`–`IBC-007` established a useful direction and a firm
correction: digits should be read as a two-dimensional graphic system, not as
objects traveling toward or away from the viewer. The
`infinity-background-flat-fields-v13` round therefore removes every number
z-axis cue. Each digit receives its size and opacity once; neither value changes
during the video. No digit is emphasized to match the `26` on the hand prop.

| ID | Construction | Review note translated into motion |
| --- | --- | --- |
| `IBF-001` | Dense varied-size 2D drift | Many more digits; evenly distributed fixed sizes; slow independent x-y drift. |
| `IBF-002` | Dense same-size 2D plane | One fixed digit size; the entire flat field moves slowly in and out of frame. |
| `IBF-003` | Orderly 2D separation field | A larger, orderly field separates laterally around the subject without scaling. |
| `IBF-004` | Visible 2D gradient curtain | A stronger two-tone gradient crosses the full background and returns. |
| `IBF-005` | Full-width sliding panel | The panel enters from the right, reaches the opposite edge, and returns with easing over 11 seconds. |
| `IBF-006` | Eleven-second hinged door | One door opens for the full video, disappears, then deliberately resets at the loop. |
| `IBF-007` | Dense 2D number wipe | A right-to-left panel erases a very dense flat field, followed by a deliberate loop reset. |

The first five options remain continuous loops. The last two explicitly test an
abrupt replay cue requested in review; their manifests use
`intentional_hard_reset` rather than falsely describing them as seamless.

Every candidate uses the identical `PDE-002` recipe, seed, focal point, and
264-frame development timeline. The subject is composited from its unmatted
16-bit layer rather than extracted from a flattened video, preventing a pale
cutout halo.

## Output and safeguards

- Seven silent, image-only candidates
- 11 seconds, 24 fps, 264 frames, 1080 × 1920
- 16-bit source preparation, effect generation, and compositing
- H.264/BT.709 delivery
- Fixed subject position, scale, rotation, and geometry
- Exact matching first and last procedural background frames
- No grain, audio, text, camera motion, displacement, or facial deformation

For `IBC`, “text” means no caption or editorial copy. Single digits are treated
as background graphic material and are explicitly recorded as typography.

Reject an option if it reads as a themed poster, explanatory diagram, sticker,
spotlight, conventional motion trail, smoke, water, or a demonstration of the
cutout technique. The background must remain subordinate to the person's face,
gesture, skin, and the number prop.
