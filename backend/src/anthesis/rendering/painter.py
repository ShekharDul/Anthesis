"""Procedural raster painter for a single concept-art flower."""

from __future__ import annotations

import colorsys
import io
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, PngImagePlugin

from anthesis.genome import FlowerBlueprint
from anthesis.rendering.config import RenderConfig
from anthesis.rendering.geometry import FlowerGeometry, Point, generate_flower_geometry

RENDERER_VERSION = "anthesis-painter-v1"


def _rgb(hue: float, saturation: float, lightness: float) -> tuple[int, int, int]:
    red, green, blue = colorsys.hls_to_rgb(
        (hue % 360.0) / 360.0,
        float(np.clip(lightness, 0.0, 1.0)),
        float(np.clip(saturation, 0.0, 1.0)),
    )
    return round(red * 255), round(green * 255), round(blue * 255)


def _paper(
    blueprint: FlowerBlueprint,
    config: RenderConfig,
    width: int,
    height: int,
) -> Image.Image:
    palette = blueprint.palette
    background = np.asarray(
        _rgb(
            palette.background_hue_degrees,
            palette.background_saturation,
            palette.background_lightness,
        ),
        dtype=np.float32,
    )
    rng = np.random.default_rng(blueprint.variation_seed ^ 0xA17E515)
    grain = rng.normal(0.0, config.paper_grain * 255.0, (height, width, 1)).astype(np.float32)
    pixels = np.clip(background[None, None, :] + grain, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(pixels, mode="RGB").convert("RGBA")


def _transformer(width: int, height: int) -> tuple[float, float, float]:
    scale = min(width * 0.76, height * 0.43)
    return width * 0.5, height * 0.52, scale


def _pixel(point: Point, transform: tuple[float, float, float]) -> tuple[float, float]:
    origin_x, origin_y, scale = transform
    return origin_x + point.x * scale, origin_y - point.y * scale


def _paint_stem(
    canvas: Image.Image,
    geometry: FlowerGeometry,
    blueprint: FlowerBlueprint,
    transform: tuple[float, float, float],
    supersampling: int,
) -> None:
    palette = blueprint.palette
    paint = blueprint.paint
    points = [_pixel(point, transform) for point in geometry.stem.centerline]
    _, _, scale = transform
    base_width = max(2, round(geometry.stem.base_width * scale))
    tip_width = max(1, round(geometry.stem.tip_width * scale))
    stem_color = _rgb(palette.stem_hue_degrees, 0.42, 0.31)
    accent_color = _rgb((palette.stem_hue_degrees + 28.0) % 360.0, 0.34, 0.52)

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.line(points, fill=(*stem_color, 95), width=base_width + 3 * supersampling)
    shadow = shadow.filter(ImageFilter.GaussianBlur(1.1 * supersampling))
    canvas.alpha_composite(shadow)

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    segment_count = len(points) - 1
    for index, (start, end) in enumerate(pairwise(points)):
        fraction = index / max(segment_count - 1, 1)
        width = round(base_width * (1.0 - fraction) + tip_width * fraction)
        opacity = round(185 - 40 * paint.wash_transparency)
        draw.line((start, end), fill=(*stem_color, opacity), width=max(1, width))
    highlight = [(x - 0.22 * base_width, y) for x, y in points]
    draw.line(
        highlight,
        fill=(*accent_color, round(70 + 55 * paint.wash_transparency)),
        width=max(1, round(base_width * 0.22)),
    )
    canvas.alpha_composite(layer)


def _polygon_mask(
    coordinates: list[tuple[float, float]],
    padding: int,
) -> tuple[Image.Image, int, int]:
    left = math.floor(min(point[0] for point in coordinates)) - padding
    top = math.floor(min(point[1] for point in coordinates)) - padding
    right = math.ceil(max(point[0] for point in coordinates)) + padding
    bottom = math.ceil(max(point[1] for point in coordinates)) + padding
    width = max(1, right - left + 1)
    height = max(1, bottom - top + 1)
    local = [(x - left, y - top) for x, y in coordinates]
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(local, fill=255)
    return mask, left, top


def _textured_alpha(
    mask: Image.Image,
    *,
    opacity: float,
    granulation: float,
    rng: np.random.Generator,
) -> Image.Image:
    mask_values = np.asarray(mask, dtype=np.float32) / 255.0
    height, width = mask_values.shape
    fine = rng.normal(0.0, 0.035 + 0.13 * granulation, (height, width)).astype(np.float32)
    low_width = max(2, width // 18)
    low_height = max(2, height // 18)
    low_noise = rng.normal(0.0, 1.0, (low_height, low_width)).astype(np.float32)
    low_image = Image.fromarray(low_noise, mode="F").resize(
        (width, height), Image.Resampling.BICUBIC
    )
    cloud = np.asarray(low_image, dtype=np.float32) * (0.05 + 0.15 * granulation)
    pigment = np.clip(1.0 + fine + cloud, 0.45, 1.35)
    alpha = np.clip(mask_values * opacity * pigment * 255.0, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(alpha, mode="L")


def _mix_hue(first: float, second: float, amount: float) -> float:
    distance = (second - first + 180.0) % 360.0 - 180.0
    return (first + distance * amount) % 360.0


def _paint_petals(
    canvas: Image.Image,
    geometry: FlowerGeometry,
    blueprint: FlowerBlueprint,
    transform: tuple[float, float, float],
    supersampling: int,
) -> None:
    palette = blueprint.palette
    character = blueprint.paint
    rng = np.random.default_rng(blueprint.variation_seed ^ 0xF10A3E)
    layer_count = max(petal.layer for petal in geometry.petals) + 1
    padding = 5 * supersampling
    for petal in geometry.petals:
        coordinates = [_pixel(point, transform) for point in petal.boundary]
        mask, left, top = _polygon_mask(coordinates, padding)
        blur_radius = (0.20 + character.edge_softness * 0.70) * supersampling
        soft_mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
        layer_fraction = petal.layer / max(layer_count - 1, 1)
        color_mix = 0.14 + 0.48 * layer_fraction + float(rng.normal(0.0, 0.045))
        hue = _mix_hue(
            palette.bloom_hue_degrees,
            palette.accent_hue_degrees,
            float(np.clip(color_mix, 0.0, 0.75)),
        )
        saturation = float(np.clip(palette.bloom_saturation + rng.normal(0.0, 0.035), 0.0, 1.0))
        lightness = float(
            np.clip(
                palette.bloom_lightness + 0.07 * layer_fraction + rng.normal(0.0, 0.025),
                0.0,
                1.0,
            )
        )
        color = _rgb(hue, saturation, lightness)
        opacity = 0.72 - 0.24 * character.wash_transparency
        alpha = _textured_alpha(
            soft_mask,
            opacity=opacity,
            granulation=character.pigment_granulation,
            rng=rng,
        )
        wash = Image.new("RGBA", mask.size, (*color, 0))
        wash.putalpha(alpha)
        canvas.alpha_composite(wash, (left, top))

        gesture = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(gesture)
        outline = _rgb(hue, min(1.0, saturation + 0.08), max(0.0, lightness - 0.18))
        draw.line(
            [*coordinates, coordinates[0]],
            fill=(*outline, round(35 + 55 * (1.0 - character.edge_softness))),
            width=max(1, supersampling),
            joint="curve",
        )
        vein = [_pixel(point, transform) for point in petal.centerline[2:-3]]
        draw.line(
            vein,
            fill=(*outline, round(28 + 42 * character.stroke_variation)),
            width=max(1, supersampling),
        )
        canvas.alpha_composite(gesture)


def _paint_center(
    canvas: Image.Image,
    geometry: FlowerGeometry,
    blueprint: FlowerBlueprint,
    transform: tuple[float, float, float],
    supersampling: int,
) -> None:
    center_x, center_y = _pixel(geometry.blossom_center, transform)
    _, _, scale = transform
    radius_x = geometry.center_radius_x * scale
    radius_y = geometry.center_radius_y * scale
    palette = blueprint.palette
    rng = np.random.default_rng(blueprint.variation_seed ^ 0xCE07E2)
    center_hue = _mix_hue(palette.accent_hue_degrees, palette.bloom_hue_degrees, 0.28)
    dark = _rgb(center_hue, palette.accent_saturation, palette.accent_lightness)
    light = _rgb(
        (center_hue + 18.0) % 360.0,
        max(0.0, palette.accent_saturation - 0.12),
        min(1.0, palette.accent_lightness + 0.22),
    )
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        (center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y),
        fill=(*dark, 220),
        outline=(*dark, 130),
        width=max(1, supersampling),
    )
    dot_count = max(18, blueprint.morphology.petal_count * 2)
    for index in range(dot_count):
        angle = index * math.pi * (3.0 - math.sqrt(5.0))
        fraction = math.sqrt((index + 0.5) / dot_count)
        jitter = float(rng.uniform(0.90, 1.07))
        x = center_x + math.cos(angle) * radius_x * fraction * jitter
        y = center_y + math.sin(angle) * radius_y * fraction * jitter
        dot_radius = (0.010 + 0.010 * (1.0 - fraction)) * scale
        draw.ellipse(
            (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
            fill=(*light, round(125 + 90 * (1.0 - fraction))),
        )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.12 * supersampling)))


def render_flower(
    blueprint: FlowerBlueprint,
    config: RenderConfig | None = None,
) -> Image.Image:
    """Render one flower deterministically using geometry, pigment, and compositing."""

    settings = config or RenderConfig()
    supersampling = settings.supersampling
    width = settings.width * supersampling
    height = settings.height * supersampling
    geometry = generate_flower_geometry(blueprint)
    transform = _transformer(width, height)
    canvas = _paper(blueprint, settings, width, height)
    _paint_stem(canvas, geometry, blueprint, transform, supersampling)
    _paint_petals(canvas, geometry, blueprint, transform, supersampling)
    _paint_center(canvas, geometry, blueprint, transform, supersampling)
    image = canvas.convert("RGB")
    if supersampling > 1:
        image = image.resize((settings.width, settings.height), Image.Resampling.LANCZOS)
    return image


def render_png_bytes(
    blueprint: FlowerBlueprint,
    config: RenderConfig | None = None,
) -> bytes:
    """Encode a deterministic PNG with reproducibility metadata."""

    image = render_flower(blueprint, config)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Software", RENDERER_VERSION)
    metadata.add_text("Anthesis-Blueprint", blueprint.digest)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", pnginfo=metadata, compress_level=9, optimize=False)
    return buffer.getvalue()


def save_png(
    blueprint: FlowerBlueprint,
    output_path: str | Path,
    config: RenderConfig | None = None,
) -> Path:
    """Render and save a PNG, creating only the requested parent directory."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_png_bytes(blueprint, config))
    return path
