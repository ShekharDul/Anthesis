import hashlib
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from anthesis.genome import (
    FlowerBlueprint,
    FlowerMorphology,
    PaintCharacter,
    PigmentPalette,
)
from anthesis.rendering import (
    RenderConfig,
    generate_flower_geometry,
    render_flower,
    render_png_bytes,
)


def _blueprint(seed: int = 0xA17E515) -> FlowerBlueprint:
    return FlowerBlueprint(
        variation_seed=seed,
        morphology=FlowerMorphology(
            petal_count=13,
            petal_layers=3,
            petal_length=0.72,
            petal_width=0.48,
            openness=0.76,
            petal_curvature=0.18,
            radial_irregularity=0.14,
            edge_detail=0.58,
            center_size=0.24,
            stem_length=0.78,
            stem_thickness=0.065,
            stem_curve=0.16,
            blossom_tilt=0.08,
        ),
        palette=PigmentPalette(
            bloom_hue_degrees=338.0,
            bloom_saturation=0.62,
            bloom_lightness=0.58,
            accent_hue_degrees=42.0,
            accent_saturation=0.72,
            accent_lightness=0.43,
            stem_hue_degrees=112.0,
            background_hue_degrees=158.0,
            background_saturation=0.055,
            background_lightness=0.94,
        ),
        paint=PaintCharacter(
            wash_transparency=0.63,
            pigment_granulation=0.46,
            edge_softness=0.61,
            stroke_variation=0.54,
        ),
    )


def test_geometry_is_deterministic_bounded_and_contains_one_stem() -> None:
    blueprint = _blueprint()
    first = generate_flower_geometry(blueprint)
    second = generate_flower_geometry(blueprint)

    assert first == second
    assert first.digest == second.digest
    assert len(first.stem.centerline) == 72
    assert len(first.petals) == sum(
        max(5, round(blueprint.morphology.petal_count * (1.0 - 0.16 * layer)))
        for layer in range(blueprint.morphology.petal_layers)
    )
    assert all(len(petal.boundary) == 50 for petal in first.petals)
    assert all(-1.1 <= point.x <= 1.1 for petal in first.petals for point in petal.boundary)
    assert all(-1.1 <= point.y <= 1.1 for petal in first.petals for point in petal.boundary)


def test_mapped_stem_length_changes_the_stem_span() -> None:
    short_blueprint = _blueprint().model_copy(
        update={"morphology": _blueprint().morphology.model_copy(update={"stem_length": 0.4})}
    )
    long_blueprint = _blueprint().model_copy(
        update={"morphology": _blueprint().morphology.model_copy(update={"stem_length": 1.0})}
    )
    short = generate_flower_geometry(short_blueprint)
    long = generate_flower_geometry(long_blueprint)

    assert long.stem.centerline[0].y < short.stem.centerline[0].y


def test_png_is_repeatable_and_contains_reproducibility_metadata() -> None:
    blueprint = _blueprint()
    config = RenderConfig(width=240, height=320, supersampling=1, paper_grain=0.01)

    first = render_png_bytes(blueprint, config)
    second = render_png_bytes(blueprint, config)
    image = Image.open(BytesIO(first))

    assert first == second
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
    assert image.size == (240, 320)
    assert image.mode == "RGB"
    assert image.info["Software"] == "anthesis-painter-v1"
    assert image.info["Anthesis-Blueprint"] == blueprint.digest


def test_render_has_plain_background_and_song_specific_artwork() -> None:
    config = RenderConfig(width=240, height=320, supersampling=1, paper_grain=0.005)
    first = np.asarray(render_flower(_blueprint(1234), config))
    second = np.asarray(render_flower(_blueprint(5678), config))
    corner = first[:30, :30].astype(np.float32)
    center = first[70:220, 35:205].astype(np.float32)

    assert float(np.std(corner)) < 12.0
    assert float(np.std(center)) > float(np.std(corner))
    assert not np.array_equal(first, second)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"width": 100}, "dimensions"),
        ({"supersampling": 5}, "supersampling"),
        ({"paper_grain": 0.2}, "paper_grain"),
        ({"width": 4_096, "height": 4_096, "supersampling": 2}, "20 million"),
    ],
)
def test_render_config_rejects_unsafe_values(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RenderConfig(**kwargs)  # type: ignore[arg-type]
