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

Reject an option if it reads as a themed poster, explanatory diagram, sticker,
spotlight, conventional motion trail, smoke, water, or a demonstration of the
cutout technique. The background must remain subordinate to the person's face,
gesture, skin, and the number prop.
