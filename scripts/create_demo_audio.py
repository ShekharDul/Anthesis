"""Create a deterministic, dependency-free demo song for Anthesis."""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22_050
DURATION_SECONDS = 8.0
CHORD_SECONDS = 2.0
CHORDS = (
    (261.63, 329.63, 392.00),
    (220.00, 261.63, 329.63),
    (174.61, 220.00, 261.63),
    (196.00, 246.94, 293.66),
)


def _sample(time: float) -> float:
    chord_position = time % CHORD_SECONDS
    chord = CHORDS[min(int(time / CHORD_SECONDS), len(CHORDS) - 1)]
    fade = min(1.0, chord_position * 5.0, (CHORD_SECONDS - chord_position) * 5.0)
    harmony = sum(math.sin(2.0 * math.pi * frequency * time) for frequency in chord) / 3.0

    beat_position = time % 0.5
    pulse = math.exp(-18.0 * beat_position) * math.sin(2.0 * math.pi * 82.41 * time)
    shimmer = math.sin(2.0 * math.pi * (523.25 + 10.0 * math.sin(time)) * time)
    return max(-1.0, min(1.0, fade * (0.46 * harmony + 0.16 * pulse + 0.05 * shimmer)))


def create_demo(path: Path) -> None:
    """Write the canonical Anthesis demo as mono 16-bit PCM WAV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = round(SAMPLE_RATE * DURATION_SECONDS)
    frames = bytearray()
    for index in range(frame_count):
        frames.extend(struct.pack("<h", round(_sample(index / SAMPLE_RATE) * 32_767)))

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("artifacts/demo.wav"))
    arguments = parser.parse_args()
    create_demo(arguments.output)
    print(arguments.output.resolve())


if __name__ == "__main__":
    main()
