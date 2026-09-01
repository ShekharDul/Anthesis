export type UnitDescriptors = {
  energy: number
  dynamic_range: number
  tempo: number
  pulse_clarity: number
  rhythmic_density: number
  brightness: number
  harmonicity: number
  percussiveness: number
  roughness: number
  tonal_clarity: number
  formal_complexity: number
  recurrence: number
  contrast: number
  valence: number
  arousal: number
  tension: number
  sublimity: number
  confidence: number
}

export type GenomeSection = {
  index: number
  label: string
  start: number
  end: number
  novelty: number
  contrast: number
  recurrence: number
}

export type GenerationResponse = {
  manifest: {
    analysis: {
      genome: {
        key: string
        mode: string
        dominant_affect: string
        energy_arc: string
        descriptors: UnitDescriptors
        sections: GenomeSection[]
        identity: { flower_seed: string }
        provenance: { duration_seconds: number }
      }
      flower: {
        morphology: {
          petal_count: number
          petal_layers: number
          openness: number
          stem_curve: number
        }
        palette: {
          bloom_hue_degrees: number
          bloom_saturation: number
          bloom_lightness: number
        }
      }
    }
    image_sha256: string
  }
  image: {
    media_type: "image/png"
    base64: string
  }
}

type ApiError = {
  message?: string
  detail?: string | { message?: string }
}

function errorMessage(payload: ApiError, status: number): string {
  if (typeof payload.detail === "object" && payload.detail?.message) {
    return payload.detail.message
  }
  if (typeof payload.detail === "string") {
    return payload.detail
  }
  return payload.message ?? `Anthesis could not process this recording (${status}).`
}

export async function generateFlower(
  audio: File,
  signal: AbortSignal,
): Promise<GenerationResponse> {
  const form = new FormData()
  form.append("audio", audio)
  const response = await fetch(
    "/api/v1/generate?width=900&height=1200&supersampling=2",
    { method: "POST", body: form, signal },
  )
  if (!response.ok) {
    let payload: ApiError = {}
    try {
      payload = (await response.json()) as ApiError
    } catch {
      // The status fallback below remains meaningful for non-JSON failures.
    }
    throw new Error(errorMessage(payload, response.status))
  }
  return (await response.json()) as GenerationResponse
}
