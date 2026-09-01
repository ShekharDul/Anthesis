import numpy as np

from anthesis.features.tonality import chroma_entropy, estimate_tonality, harmonic_change


def test_tonality_estimates_clear_c_major_profile() -> None:
    chroma = np.zeros((12, 8), dtype=np.float32)
    chroma[[0, 4, 7], :] = np.asarray([[1.0], [0.8], [0.9]])

    estimate = estimate_tonality(chroma)

    assert estimate.key == "C"
    assert estimate.mode == "major"
    assert estimate.mode_evidence > 0


def test_chroma_complexity_and_change_respond_to_distribution() -> None:
    chroma = np.zeros((12, 2), dtype=np.float32)
    chroma[0, 0] = 1
    chroma[:, 1] = 1 / 12

    entropy = chroma_entropy(chroma)
    change = harmonic_change(chroma)

    assert entropy[0] < 0.01
    assert entropy[1] > 0.99
    assert change[0] == 0
    assert change[1] > 0


def test_tonality_marks_empty_harmonic_evidence_as_ambiguous() -> None:
    estimate = estimate_tonality(np.zeros((12, 4), dtype=np.float32))

    assert estimate.key == "unknown"
    assert estimate.mode == "ambiguous"
    assert estimate.mode_evidence == 0
