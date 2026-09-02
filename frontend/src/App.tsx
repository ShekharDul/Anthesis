import { useEffect, useId, useRef, useState } from "react"

import { generateFlower, type GenerationResponse } from "./api"

const MAX_FILE_BYTES = 100 * 1024 * 1024
const STAGES = [
  "Preparing the recording",
  "Separating rhythm and harmony",
  "Reading expression and structure",
  "Painting the flower",
]

type View = "idle" | "processing" | "result"

function titleCase(value: string): string {
  return value
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function downloadBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = name
  anchor.click()
  URL.revokeObjectURL(url)
}

function downloadPng(base64: string, name: string): void {
  const binary = atob(base64)
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
  downloadBlob(new Blob([bytes], { type: "image/png" }), name)
}

function safeStem(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, "").replace(/[^a-zA-Z0-9-_]+/g, "-") || "anthesis"
}

function Metric({ label, value, signed = false }: { label: string; value: number; signed?: boolean }) {
  const normalized = signed ? (value + 1) / 2 : value
  return (
    <div className="metric">
      <div><span>{label}</span><strong>{Math.round(normalized * 100)}</strong></div>
      <span className="meter" aria-hidden="true"><i style={{ width: `${normalized * 100}%` }} /></span>
    </div>
  )
}

function LoadingView({ fileName, stage, onCancel }: { fileName: string; stage: number; onCancel: () => void }) {
  return (
    <main className="loading-view" aria-live="polite">
      <div className="growth-mark" aria-hidden="true"><i /><i /><i /></div>
      <p className="eyebrow">Listening closely</p>
      <h1>Growing your flower.</h1>
      <p className="loading-file">{fileName}</p>
      <ol className="stage-list">
        {STAGES.map((item, index) => (
          <li key={item} className={index < stage ? "complete" : index === stage ? "active" : ""}>
            <span>{index < stage ? "✓" : String(index + 1).padStart(2, "0")}</span>{item}
          </li>
        ))}
      </ol>
      <button className="text-button" type="button" onClick={onCancel}>Cancel</button>
    </main>
  )
}

function ResultView({
  result,
  fileName,
  onReset,
}: {
  result: GenerationResponse
  fileName: string
  onReset: () => void
}) {
  const genome = result.manifest.analysis.genome
  const flower = result.manifest.analysis.flower
  const descriptors = genome.descriptors
  const tempo = Math.round(45 + descriptors.tempo * 135)
  const duration = Math.round(genome.provenance.duration_seconds)
  const imageUrl = `data:${result.image.media_type};base64,${result.image.base64}`
  const stem = safeStem(fileName)
  const pigment = flower.palette
  const pigmentColor = `hsl(${pigment.bloom_hue_degrees} ${pigment.bloom_saturation * 100}% ${pigment.bloom_lightness * 100}%)`

  const saveAnalysis = () => {
    const content = JSON.stringify(result.manifest, null, 2)
    downloadBlob(new Blob([content], { type: "application/json" }), `${stem}.anthesis.json`)
  }

  return (
    <main className="result-view">
      <section className="artwork-panel" aria-labelledby="result-title">
        <div className="artwork-frame">
          <img src={imageUrl} alt={`Procedural flower generated from ${fileName}`} />
        </div>
        <div className="artwork-actions">
          <button type="button" onClick={() => downloadPng(result.image.base64, `${stem}.png`)}>Download flower</button>
          <button className="secondary-button" type="button" onClick={saveAnalysis}>Analysis JSON</button>
        </div>
      </section>

      <section className="reading-panel">
        <p className="eyebrow">Your musical specimen</p>
        <h1 id="result-title">{titleCase(genome.dominant_affect)}</h1>
        <p className="result-file">Grown from <strong>{fileName}</strong></p>

        <div className="musical-facts">
          <div><span>Key</span><strong>{genome.key} {titleCase(genome.mode)}</strong></div>
          <div><span>Tempo</span><strong>{tempo} BPM</strong></div>
          <div><span>Arc</span><strong>{titleCase(genome.energy_arc)}</strong></div>
          <div><span>Duration</span><strong>{Math.floor(duration / 60)}:{String(duration % 60).padStart(2, "0")}</strong></div>
        </div>

        <div className="analysis-block">
          <div className="section-heading"><h2>Expressive reading</h2><span>{Math.round(descriptors.confidence * 100)}% confidence</span></div>
          <Metric label="Valence" value={descriptors.valence} signed />
          <Metric label="Arousal" value={descriptors.arousal} />
          <Metric label="Tension" value={descriptors.tension} />
          <Metric label="Complexity" value={descriptors.formal_complexity} />
        </div>

        <div className="analysis-block botanical-reading">
          <h2>Botanical translation</h2>
          <div className="trait-grid">
            <div><strong>{flower.morphology.petal_count}</strong><span>petals per layer</span></div>
            <div><strong>{flower.morphology.petal_layers}</strong><span>petal layers</span></div>
            <div><strong>{Math.round(flower.morphology.openness * 100)}%</strong><span>openness</span></div>
            <div><i style={{ background: pigmentColor }} /><span>song pigment</span></div>
          </div>
        </div>

        <div className="structure-block">
          <h2>Song structure</h2>
          <div className="section-map" aria-label={`${genome.sections.length} detected song sections`}>
            {genome.sections.map((section) => (
              <span key={`${section.index}-${section.label}`} style={{ flexGrow: section.end - section.start }}>
                {section.label}
              </span>
            ))}
          </div>
        </div>

        <button className="text-button start-over" type="button" onClick={onReset}>Grow another song</button>
      </section>
    </main>
  )
}

function UploadView({
  file,
  error,
  dragging,
  inputId,
  onFile,
  onDragState,
  onGenerate,
}: {
  file: File | null
  error: string
  dragging: boolean
  inputId: string
  onFile: (file: File | null) => void
  onDragState: (dragging: boolean) => void
  onGenerate: () => void
}) {
  return (
    <main className="workspace">
      <section className="introduction" aria-labelledby="page-title">
        <p className="eyebrow">One song · one botanical form</p>
        <h1 id="page-title">Grow a flower from your music.</h1>
        <p className="summary">Anthesis listens for rhythm, harmony, texture, and emotional movement—then paints one singular flower using only signal processing and procedural code.</p>
        <ol className="method" aria-label="How Anthesis works">
          <li><span>01</span> Select a recording</li>
          <li><span>02</span> Read its musical structure</li>
          <li><span>03</span> Render its flower</li>
        </ol>
      </section>

      <section className="studio" aria-labelledby="studio-title">
        <div className="studio-heading">
          <div><p className="eyebrow">New specimen</p><h2 id="studio-title">Choose a song</h2></div>
          <span className="local-note">Local processing</span>
        </div>
        <label
          className={`drop-zone${dragging ? " dragging" : ""}`}
          htmlFor={inputId}
          onDragEnter={(event) => { event.preventDefault(); onDragState(true) }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => { event.preventDefault(); onDragState(false) }}
          onDrop={(event) => { event.preventDefault(); onDragState(false); onFile(event.dataTransfer.files[0] ?? null) }}
        >
          <input id={inputId} aria-label="Music audio file" type="file" accept="audio/*,.mp3,.wav,.flac,.ogg" onChange={(event) => onFile(event.target.files?.[0] ?? null)} />
          <span className="upload-mark" aria-hidden="true">↑</span>
          <strong>{file?.name || "Place a recording here"}</strong>
          <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · ready to grow` : "or choose a file from your computer"}</span>
        </label>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="studio-footer">
          <p>MP3, WAV, FLAC or OGG · up to 100 MB</p>
          <button type="button" disabled={!file} onClick={onGenerate}>Grow this song</button>
        </div>
      </section>
    </main>
  )
}

export function App() {
  const inputId = useId()
  const controller = useRef<AbortController | null>(null)
  const [view, setView] = useState<View>("idle")
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState("")
  const [dragging, setDragging] = useState(false)
  const [stage, setStage] = useState(0)
  const [result, setResult] = useState<GenerationResponse | null>(null)

  useEffect(() => {
    if (view !== "processing") return
    const timer = window.setInterval(() => setStage((current) => Math.min(current + 1, 3)), 5000)
    return () => window.clearInterval(timer)
  }, [view])

  const chooseFile = (candidate: File | null) => {
    setError("")
    if (!candidate) { setFile(null); return }
    if (candidate.size > MAX_FILE_BYTES) { setFile(null); setError("Choose a recording smaller than 100 MB."); return }
    setFile(candidate)
  }

  const generate = async () => {
    if (!file) return
    setError("")
    setStage(0)
    setView("processing")
    controller.current = new AbortController()
    try {
      const generated = await generateFlower(file, controller.current.signal)
      setResult(generated)
      setStage(3)
      setView("result")
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return
      setError(requestError instanceof Error ? requestError.message : "Anthesis could not process this recording.")
      setView("idle")
    }
  }

  const reset = () => { controller.current?.abort(); setView("idle"); setFile(null); setResult(null); setError(""); setStage(0) }

  return (
    <div className="site-shell">
      <header className="masthead">
        <button className="wordmark" type="button" onClick={reset}>Anthesis</button>
        <p>Music interpreted through mathematics</p>
      </header>
      {view === "processing" && file && <LoadingView fileName={file.name} stage={stage} onCancel={reset} />}
      {view === "result" && result && file && <ResultView result={result} fileName={file.name} onReset={reset} />}
      {view === "idle" && <UploadView file={file} error={error} dragging={dragging} inputId={inputId} onFile={chooseFile} onDragState={setDragging} onGenerate={() => void generate()} />}
      <footer className="footer"><p>No generative AI. No presets. Just the mathematics inside your music.</p><p>Anthesis v0.1</p></footer>
    </div>
  )
}
