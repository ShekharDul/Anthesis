# Anthesis example

Create a small deterministic demo recording without downloading any media:

```powershell
python scripts/create_demo_audio.py
```

Render its flower and inspectable manifest:

```powershell
anthesis generate artifacts/demo.wav --output artifacts/demo-flower.png
```

Run those commands again to verify that the image, genome digest, and manifest
remain identical. The demo audio and generated files live under `artifacts/`,
which is intentionally excluded from version control.
