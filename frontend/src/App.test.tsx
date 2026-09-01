import "@testing-library/jest-dom/vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { App } from "./App"

const response = {
  manifest: {
    analysis: {
      genome: {
        key: "A",
        mode: "major",
        dominant_affect: "bright-energy",
        energy_arc: "rising",
        descriptors: {
          energy: 0.7,
          dynamic_range: 0.4,
          tempo: 0.55,
          pulse_clarity: 0.8,
          rhythmic_density: 0.5,
          brightness: 0.6,
          harmonicity: 0.75,
          percussiveness: 0.3,
          roughness: 0.2,
          tonal_clarity: 0.8,
          formal_complexity: 0.62,
          recurrence: 0.5,
          contrast: 0.4,
          valence: 0.65,
          arousal: 0.72,
          tension: 0.28,
          sublimity: 0.68,
          confidence: 0.84,
        },
        sections: [
          { index: 0, label: "A", start: 0, end: 0.5, novelty: 0, contrast: 0, recurrence: 0.8 },
          { index: 1, label: "B", start: 0.5, end: 1, novelty: 0.7, contrast: 0.6, recurrence: 0.3 },
        ],
        identity: { flower_seed: "0123456789abcdef0123456789abcdef" },
        provenance: { duration_seconds: 187 },
      },
      flower: {
        morphology: { petal_count: 14, petal_layers: 3, openness: 0.78, stem_curve: 0.12 },
        palette: {
          bloom_hue_degrees: 338,
          bloom_saturation: 0.62,
          bloom_lightness: 0.58,
        },
      },
    },
    image_sha256: "a".repeat(64),
  },
  image: { media_type: "image/png", base64: "aW1hZ2U=" },
}

function chooseAudio(): void {
  const input = screen.getByLabelText("Music audio file")
  fireEvent.change(input, { target: { files: [new File(["audio"], "sunrise.wav", { type: "audio/wav" })] } })
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("App", () => {
  it("opens on the working upload surface", () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "Grow a flower from your music." })).toBeVisible()
    expect(screen.getByRole("button", { name: "Grow this song" })).toBeDisabled()
    expect(screen.getByText("No generative AI. No presets. Just the mathematics inside your music.")).toBeVisible()
  })

  it("accepts a recording and enables generation", () => {
    render(<App />)
    chooseAudio()

    expect(screen.getByText("sunrise.wav")).toBeVisible()
    expect(screen.getByRole("button", { name: "Grow this song" })).toBeEnabled()
  })

  it("renders artwork and its musical reading", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200 })))
    render(<App />)
    chooseAudio()
    fireEvent.click(screen.getByRole("button", { name: "Grow this song" }))

    expect(screen.getByRole("heading", { name: "Growing your flower." })).toBeVisible()
    await waitFor(() => expect(screen.getByRole("heading", { name: "Bright Energy" })).toBeVisible())
    expect(screen.getByAltText("Procedural flower generated from sunrise.wav")).toBeVisible()
    expect(screen.getByText("119 BPM")).toBeVisible()
    expect(screen.getByRole("button", { name: "Download flower" })).toBeEnabled()
  })

  it("returns safely to the studio when processing fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "The recording could not be decoded." }), { status: 422 }),
      ),
    )
    render(<App />)
    chooseAudio()
    fireEvent.click(screen.getByRole("button", { name: "Grow this song" }))

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("could not be decoded"))
    expect(screen.getByRole("button", { name: "Grow this song" })).toBeEnabled()
  })
})
