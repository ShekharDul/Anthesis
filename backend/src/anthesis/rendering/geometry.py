"""Seeded construction of one flower with one stem."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np

from anthesis.genome import FlowerBlueprint


@dataclass(frozen=True, slots=True)
class Point:
    """A normalized point where positive y points upward."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class PetalGeometry:
    """Closed petal boundary and its central gesture line."""

    layer: int
    index: int
    angle_radians: float
    boundary: tuple[Point, ...]
    centerline: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class StemGeometry:
    """Tapered stem centerline from ground to blossom."""

    centerline: tuple[Point, ...]
    base_width: float
    tip_width: float


@dataclass(frozen=True, slots=True)
class FlowerGeometry:
    """Renderer-independent geometry for exactly one bloom and stem."""

    blossom_center: Point
    petals: tuple[PetalGeometry, ...]
    center_radius_x: float
    center_radius_y: float
    stem: StemGeometry
    seed: int
    version: str = "anthesis-geometry-v1"

    @property
    def digest(self) -> str:
        payload = {
            "version": self.version,
            "seed": self.seed,
            "center": [round(self.blossom_center.x, 8), round(self.blossom_center.y, 8)],
            "center_radius": [round(self.center_radius_x, 8), round(self.center_radius_y, 8)],
            "stem": [[round(point.x, 8), round(point.y, 8)] for point in self.stem.centerline],
            "petals": [
                {
                    "layer": petal.layer,
                    "index": petal.index,
                    "angle": round(petal.angle_radians, 8),
                    "boundary": [
                        [round(point.x, 8), round(point.y, 8)] for point in petal.boundary
                    ],
                }
                for petal in self.petals
            ],
        }
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


def _bezier(
    start: Point,
    control_one: Point,
    control_two: Point,
    end: Point,
    steps: int,
) -> tuple[Point, ...]:
    points: list[Point] = []
    for parameter in np.linspace(0.0, 1.0, steps):
        inverse = 1.0 - parameter
        x = (
            inverse**3 * start.x
            + 3.0 * inverse**2 * parameter * control_one.x
            + 3.0 * inverse * parameter**2 * control_two.x
            + parameter**3 * end.x
        )
        y = (
            inverse**3 * start.y
            + 3.0 * inverse**2 * parameter * control_one.y
            + 3.0 * inverse * parameter**2 * control_two.y
            + parameter**3 * end.y
        )
        points.append(Point(float(x), float(y)))
    return tuple(points)


def _petal(
    *,
    center: Point,
    angle: float,
    length: float,
    width: float,
    curvature: float,
    edge_detail: float,
    layer: int,
    index: int,
    rng: np.random.Generator,
) -> PetalGeometry:
    direction = np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float64)
    normal = np.asarray([-direction[1], direction[0]], dtype=np.float64)
    base = np.asarray([center.x, center.y], dtype=np.float64) + direction * (0.018 + layer * 0.006)
    bend = normal * curvature * length * 0.22
    tip = base + direction * length + bend
    control_one = base + direction * length * 0.32 + bend * 0.18
    control_two = base + direction * length * 0.76 + bend * 0.72
    phase = float(rng.uniform(0.0, 2.0 * math.pi))
    edge_frequency = 2 + round(edge_detail * 4.0)
    left: list[Point] = []
    right: list[Point] = []
    centerline: list[Point] = []
    for parameter in np.linspace(0.0, 1.0, 25):
        inverse = 1.0 - parameter
        position = (
            inverse**3 * base
            + 3.0 * inverse**2 * parameter * control_one
            + 3.0 * inverse * parameter**2 * control_two
            + parameter**3 * tip
        )
        derivative = (
            3.0 * inverse**2 * (control_one - base)
            + 6.0 * inverse * parameter * (control_two - control_one)
            + 3.0 * parameter**2 * (tip - control_two)
        )
        derivative /= max(float(np.linalg.norm(derivative)), np.finfo(float).eps)
        local_normal = np.asarray([-derivative[1], derivative[0]])
        taper = math.sin(math.pi * parameter) ** 0.72
        organic_edge = 1.0 + edge_detail * 0.07 * math.sin(
            edge_frequency * 2.0 * math.pi * parameter + phase
        )
        half_width = width * 0.5 * taper * organic_edge
        left_position = position + local_normal * half_width
        right_position = position - local_normal * half_width
        left.append(Point(float(left_position[0]), float(left_position[1])))
        right.append(Point(float(right_position[0]), float(right_position[1])))
        centerline.append(Point(float(position[0]), float(position[1])))
    return PetalGeometry(
        layer=layer,
        index=index,
        angle_radians=angle,
        boundary=tuple((*left, *reversed(right))),
        centerline=tuple(centerline),
    )


def generate_flower_geometry(blueprint: FlowerBlueprint) -> FlowerGeometry:
    """Generate deterministic normalized geometry from a bounded blueprint."""

    morphology = blueprint.morphology
    rng = np.random.default_rng(blueprint.variation_seed)
    center = Point(morphology.blossom_tilt * 0.20, 0.28)
    flattening = 1.0 - abs(morphology.blossom_tilt) * 0.45
    petals: list[PetalGeometry] = []
    for layer in range(morphology.petal_layers):
        layer_fraction = layer / max(morphology.petal_layers - 1, 1)
        count = max(5, round(morphology.petal_count * (1.0 - 0.16 * layer)))
        stagger = layer * math.pi / count
        for index in range(count):
            irregularity = morphology.radial_irregularity
            angle_jitter = float(
                np.clip(
                    rng.normal(0.0, irregularity * 0.09),
                    -irregularity * 0.25,
                    irregularity * 0.25,
                )
            )
            angle = 2.0 * math.pi * index / count + stagger + angle_jitter
            length_variation = float(
                np.clip(1.0 + rng.normal(0.0, irregularity * 0.13), 0.82, 1.18)
            )
            length = (
                (0.31 + 0.30 * morphology.petal_length)
                * (1.0 - 0.13 * layer_fraction)
                * (0.82 + 0.18 * morphology.openness)
                * length_variation
            )
            width_variation = float(np.clip(1.0 + rng.normal(0.0, irregularity * 0.10), 0.85, 1.15))
            width = (
                (0.065 + 0.18 * morphology.petal_width)
                * (1.0 - 0.08 * layer_fraction)
                * width_variation
            )
            petal = _petal(
                center=center,
                angle=angle,
                length=max(0.08, length),
                width=max(0.025, width),
                curvature=float(
                    np.clip(
                        morphology.petal_curvature + rng.normal(0.0, irregularity * 0.16),
                        -1.0,
                        1.0,
                    )
                ),
                edge_detail=morphology.edge_detail,
                layer=layer,
                index=index,
                rng=rng,
            )
            if flattening < 1.0:
                petal = PetalGeometry(
                    layer=petal.layer,
                    index=petal.index,
                    angle_radians=petal.angle_radians,
                    boundary=tuple(
                        Point(point.x, center.y + (point.y - center.y) * flattening)
                        for point in petal.boundary
                    ),
                    centerline=tuple(
                        Point(point.x, center.y + (point.y - center.y) * flattening)
                        for point in petal.centerline
                    ),
                )
            petals.append(petal)

    stem_end = Point(center.x, center.y - 0.025)
    stem_span = 0.82 + 0.50 * morphology.stem_length
    stem_base_y = max(-0.94, stem_end.y - stem_span)
    stem_base = Point(-morphology.stem_curve * 0.10, stem_base_y)
    curve = morphology.stem_curve
    stem_line = _bezier(
        stem_base,
        Point(stem_base.x + curve * 0.65, stem_base_y + stem_span * 0.32),
        Point(center.x - curve * 0.42, stem_base_y + stem_span * 0.72),
        stem_end,
        72,
    )
    stem = StemGeometry(
        centerline=stem_line,
        base_width=0.018 + morphology.stem_thickness * 0.26,
        tip_width=0.010 + morphology.stem_thickness * 0.11,
    )
    center_radius = 0.048 + morphology.center_size * 0.18
    return FlowerGeometry(
        blossom_center=center,
        petals=tuple(petals),
        center_radius_x=center_radius,
        center_radius_y=center_radius * flattening,
        stem=stem,
        seed=blueprint.variation_seed,
    )
