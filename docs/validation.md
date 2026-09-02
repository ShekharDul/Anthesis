# Validation and operational boundaries

Anthesis is designed as a local creative tool. Its current API is safe for a
trusted local user; it is not an authenticated multi-tenant internet service
and should not be exposed publicly without an external authentication, rate
limiting, and isolation layer.

## Determinism locks

The end-to-end regression fixture fixes the canonical PCM identity to a
platform-independent SHA-256 value. It processes the fixture twice and requires
byte-identical PNGs, equal manifests, and valid linked digests for the genome,
analysis document, geometry, and image.

Numerical DSP libraries may produce final-bit differences across operating
systems, processor architectures, or dependency versions. Anthesis therefore
guarantees repeatability within the same supported runtime and dependency
environment; it does not treat Windows-generated derived hashes as Linux golden
values. This still detects nondeterminism and broken artifact integrity without
mistaking legitimate numerical-backend variation for an algorithm regression.

## Input and resource controls

- Browser uploads are streamed in 1 MiB chunks and stop at 100 MiB.
- Empty, silent, too-short, malformed, and over-limit audio is rejected.
- Uploaded filenames are never used as filesystem paths.
- Every request receives an isolated temporary directory that is removed after
  success or failure.
- At most two analysis jobs run concurrently; excess work receives HTTP 503
  with a retry hint instead of exhausting memory.
- Render dimensions, supersampling, and a 20-million-working-pixel ceiling
  bound raster memory.
- The compact feature timeline and maximum genome trajectory size bound later
  structural and serialization work.
- Harmonic separation and feature extraction reuse the same spectral matrices;
  regression tests prevent accidental duplicate transforms.

## Trust boundaries

API errors are translated into stable public messages so decoder paths and
tracebacks are not disclosed. Responses disable caching, framing, MIME
sniffing, referrer sharing, and unnecessary browser permissions. CORS accepts
only the two local Vite development origins.

The browser checks ranges and required fields in every successful generation
response before using it. Network failures, malformed JSON, malformed result
shapes, and expected audio errors all return to a retryable interface state.
Generated artifacts verify their embedded analysis digest, PNG signature, and
image checksum before leaving the processing layer.

## Automated coverage

The suite covers controlled audio behavior, separation reconstruction,
features, structure, expression, fingerprints, MusicGenome validation,
botanical mapping, geometry, repeatable rendering, API streaming and
concurrency, CLI output, full-pipeline identity and integrity, and all browser states. Static
checks use strict mypy, Ruff, ESLint, and TypeScript settings.
