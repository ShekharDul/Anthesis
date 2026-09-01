# Contributing to Anthesis

Anthesis is being developed in small, reviewable checkpoints. Contributions
should preserve determinism, explainability, and local-first processing.

## Expectations

1. Open an issue before making a large architectural change.
2. Keep analysis code independent from rendering code.
3. Document the mathematical meaning and expected range of new features.
4. Add tests for deterministic behavior and edge cases.
5. Do not introduce generative-AI models or network processing into the core.

## Local checks

Backend changes must pass Ruff, mypy, and pytest. Frontend changes must pass
TypeScript, ESLint, Vitest, and the production build. The root check scripts
will run these tools once dependencies are installed.
