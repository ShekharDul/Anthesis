# Validation and operational boundaries

Anthesis is designed as a local creative tool. Its current API is safe for a
trusted local user; it is not an authenticated multi-tenant internet service
and should not be exposed publicly without an external authentication, rate
limiting, and isolation layer.

## Determinism locks

The end-to-end regression fixture fixes five expected SHA-256 values:

- canonical audio identity;
- MusicGenome content;
- complete analysis document;
- normalized flower geometry;
- final PNG bytes.

The same fixture is processed twice and must also produce byte-identical PNGs
and equal manifests. Golden values may change only alongside an intentional,
documented algorithm or renderer version change. This detects accidental drift
between analysis, mapping, geometry, compositing, and serialization.

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
concurrency, CLI output, full-pipeline digests, and all browser states. Static
checks use strict mypy, Ruff, ESLint, and TypeScript settings.
