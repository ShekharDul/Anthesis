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

const descriptorKeys: (keyof UnitDescriptors)[] = [
  "energy", "dynamic_range", "tempo", "pulse_clarity", "rhythmic_density",
  "brightness", "harmonicity", "percussiveness", "roughness", "tonal_clarity",
  "formal_complexity", "recurrence", "contrast", "valence", "arousal", "tension",
  "sublimity", "confidence",
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function finiteNumber(value: unknown, minimum: number, maximum: number): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= maximum
}

function validDescriptors(value: unknown): value is UnitDescriptors {
  if (!isRecord(value)) return false
  return descriptorKeys.every((key) => {
    const minimum = key === "valence" ? -1 : 0
    return finiteNumber(value[key], minimum, 1)
  })
}

function validSections(value: unknown): value is GenomeSection[] {
  if (!Array.isArray(value) || value.length === 0) return false
  return value.every((section) => isRecord(section)
    && typeof section.label === "string"
    && finiteNumber(section.index, 0, 1_000)
    && finiteNumber(section.start, 0, 1)
    && finiteNumber(section.end, section.start, 1))
}

function validGeneration(value: unknown): value is GenerationResponse {
  if (!isRecord(value) || !isRecord(value.manifest) || !isRecord(value.image)) return false
  const analysis = value.manifest.analysis
  if (!isRecord(analysis) || !isRecord(analysis.genome) || !isRecord(analysis.flower)) return false
  const genome = analysis.genome
  const flower = analysis.flower
  if (!isRecord(flower.morphology) || !isRecord(flower.palette)) return false
  const hex32 = /^[0-9a-f]{32}$/
  const hex64 = /^[0-9a-f]{64}$/
  return typeof genome.key === "string"
    && typeof genome.mode === "string"
    && typeof genome.dominant_affect === "string"
    && typeof genome.energy_arc === "string"
    && validDescriptors(genome.descriptors)
    && validSections(genome.sections)
    && isRecord(genome.identity)
    && typeof genome.identity.flower_seed === "string"
    && hex32.test(genome.identity.flower_seed)
    && isRecord(genome.provenance)
    && finiteNumber(genome.provenance.duration_seconds, 0, 24 * 60 * 60)
    && finiteNumber(flower.morphology.petal_count, 5, 34)
    && finiteNumber(flower.morphology.petal_layers, 1, 5)
    && finiteNumber(flower.morphology.openness, 0, 1)
    && finiteNumber(flower.morphology.stem_curve, -0.5, 0.5)
    && finiteNumber(flower.palette.bloom_hue_degrees, 0, 360)
    && finiteNumber(flower.palette.bloom_saturation, 0, 1)
    && finiteNumber(flower.palette.bloom_lightness, 0, 1)
    && typeof value.manifest.image_sha256 === "string"
    && hex64.test(value.manifest.image_sha256)
    && value.image.media_type === "image/png"
    && typeof value.image.base64 === "string"
    && value.image.base64.length > 0
}

function apiError(value: unknown): ApiError {
  if (!isRecord(value)) return {}
  const detail = value.detail
  let normalizedDetail: ApiError["detail"]
  if (typeof detail === "string") {
    normalizedDetail = detail
  } else if (isRecord(detail) && typeof detail.message === "string") {
    normalizedDetail = { message: detail.message }
  }
  return {
    message: typeof value.message === "string" ? value.message : undefined,
    detail: normalizedDetail,
  }
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
  let response: Response
  try {
    response = await fetch(
      "/api/v1/generate?width=900&height=1200&supersampling=2",
      { method: "POST", body: form, signal },
    )
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error
    throw new Error(
      "The local Anthesis service is unavailable. Start the API and try again.",
      { cause: error },
    )
  }
  if (!response.ok) {
    let payload: ApiError = {}
    try {
      payload = apiError(await response.json())
    } catch {
      // The status fallback below remains meaningful for non-JSON failures.
    }
    throw new Error(errorMessage(payload, response.status))
  }
  const payload: unknown = await response.json()
  if (!validGeneration(payload)) {
    throw new Error("The local Anthesis service returned an invalid generation result.")
  }
  return payload
}
