# Architecture

Anthesis separates interpretation from illustration. Audio is converted into a
versioned, inspectable `MusicGenome`; renderers consume that schema without
reading the original audio.

```text
audio file
    │
    ▼
canonical audio → time/frequency transforms → musical features
    │                                           │
    ├── robust acoustic identity                ├── structure
    │                                           └── expressive curves
    └──────────────────────┬──────────────────────────────┘
                           ▼
                       MusicGenome
                           │
                           ▼
                flower geometry → paint renderer
                           │
                           ▼
                     PNG + analysis JSON
```

## Boundaries

### Analysis core

Pure Python modules for decoding, canonicalization, feature extraction,
structure analysis, expressive inference, confidence, and identity. This layer
must not import API or frontend code.

### MusicGenome

A versioned Pydantic model containing normalized global descriptors,
time-varying curves, structural sections, identity material, confidence, and
provenance. It contains no source path or audio samples and can round-trip
strictly through JSON. Schema changes require versioning and migration
consideration. See [MusicGenome and flower mapping](music-genome.md).

### Flower system

The mapper converts MusicGenome values into bounded botanical parameters. The
geometry layer builds a single flower and stem. The paint layer rasterizes it
with deterministic procedural media. Musical descriptors determine macro-form;
identity-derived values are reserved for restrained variation and seeded
micro-geometry. See [Deterministic flower rendering](rendering.md).

### Delivery surfaces

The CLI supports scripting and diagnostics. FastAPI provides local processing
for the React interface. Uploaded audio is temporary and local by default.

## Determinism

Every stochastic-looking operation receives a seed derived from the stable
identity material plus the analysis and renderer versions. Tests will detect
unintentional output changes.
