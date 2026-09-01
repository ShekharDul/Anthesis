# Deterministic flower rendering

Anthesis renders with Pillow, NumPy, geometry, and compositing. It does not call
an image model or use a generated visual asset.

## Geometry

`anthesis-geometry-v1` builds exactly one radial bloom and one cubic Bézier
stem in normalized coordinates. Petal length, width, count, layers, openness,
curvature, edge detail, and irregularity come from the flower blueprint. Each
petal is a closed sampled boundary around a curved centerline. The song seed
introduces bounded differences in angle, size, bend, and edge phase.

Geometry is independent of pixels and has its own stable digest. Canvas size
and supersampling therefore change output resolution without changing the
underlying flower.

## Painter

`anthesis-painter-v1` rasterizes the geometry as translucent pigment washes:

- a near-white monochrome background receives subtle deterministic paper grain;
- the tapered stem is painted first with a softened under-stroke and highlight;
- petals are layered back-to-front with seeded pigment density and soft edges;
- contour and centerline gestures retain a drawn quality;
- a deterministic phyllotactic dot pattern forms the flower center;
- supersampling provides smooth organic contours without 3D rendering.

PNG files contain the renderer version and flower-blueprint digest as metadata.
The default output is 900 × 1200 pixels with 2× supersampling. Dimensions,
quality, and paper grain are bounded to prevent accidental excessive memory
use. Identical blueprint, renderer version, and render settings produce
identical PNG bytes in the supported environment.
