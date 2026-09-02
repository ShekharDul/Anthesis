# Browser experience

The React interface is a focused working surface rather than a marketing site.
Its primary flow is select, understand, and keep the result.

## States

1. The upload studio accepts click selection or drag and drop, displays the
   selected filename and size, and rejects files over the 100 MiB web limit.
2. Processing replaces the studio with four legible stages and a cancel action.
3. Success presents the 900 × 1200 artwork beside its musical and botanical
   reading. Users can download both the PNG and complete generation manifest.
4. Expected failures return to the studio with a concise accessible error and
   preserve the selected recording for retry.

The result reading exposes key, mode, estimated tempo, expressive arc,
duration, valence, arousal, tension, formal complexity, petal
traits, pigment, and detected song sections. It avoids claiming knowledge of a
listener's private feelings.

## Local development

Run the API and Vite interface in separate terminals:

```powershell
.\.venv\Scripts\anthesis.exe serve
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`, keeping browser requests
same-origin during development. The interface uses system fonts and contains
no externally loaded images, trackers, or runtime UI dependencies.

## Accessibility and resilience

- semantic headings, landmarks, labels, buttons, and live status messaging;
- keyboard-visible focus, native file selection, and accessible progress text;
- reduced-motion support;
- responsive single-column layouts below tablet width;
- API errors normalized into human-readable messages;
- downloads created locally from the returned PNG and manifest.
