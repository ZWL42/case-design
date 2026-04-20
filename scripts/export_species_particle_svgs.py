#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


RASTER_WIDTH = 280
ALPHA_CUTOFF = 20
PARTICLES_EXTINCT = 680
PARTICLES_ENDANGERED = 560
PADDING = 8.0

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "原型" / "sours" / "crap"
OUTPUT_DIR = ROOT / "导出" / "物种粒子SVG_v5"


@dataclass(frozen=True)
class SpeciesConfig:
    key: str
    name: str
    status: str
    image_file: str


SPECIES_CONFIG: list[SpeciesConfig] = [
    SpeciesConfig("baiji", "白鳍豚", "extinct", "白鳍豚.png"),
    SpeciesConfig("rafetus", "斑鳖", "extinct", "斑鳖.png"),
    SpeciesConfig("xj_tiger", "新疆虎", "extinct", "新疆虎.png"),
    SpeciesConfig("snow_leopard", "雪豹", "endangered", "雪豹.png"),
    SpeciesConfig("ibis", "朱鹮", "endangered", "朱鹮.png"),
    SpeciesConfig("alligator", "亚洲象", "endangered", "亚洲象.png"),
    SpeciesConfig("porpoise", "金丝猴", "endangered", "金丝猴.png"),
    SpeciesConfig("south_tiger", "华南虎", "endangered", "华南虎.png"),
]


def particle_count_for(conf: SpeciesConfig) -> int:
    return PARTICLES_EXTINCT if conf.status == "extinct" else PARTICLES_ENDANGERED


def seeded_rng(seed_text: str) -> random.Random:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def resize_for_sampling(image: Image.Image) -> Image.Image:
    rw = RASTER_WIDTH
    rh = max(80, round((rw * image.height) / image.width))
    return image.resize((rw, rh), Image.Resampling.LANCZOS)


def solid_pixels(img: Image.Image) -> list[tuple[int, int, tuple[int, int, int, int]]]:
    rgba = img.convert("RGBA")
    width, height = rgba.size
    px = rgba.load()
    solid: list[tuple[int, int, tuple[int, int, int, int]]] = []
    for y in range(height):
        for x in range(width):
            rgba_px = px[x, y]
            if rgba_px[3] > ALPHA_CUTOFF:
                solid.append((x, y, rgba_px))
    return solid


def sample_particles(
    conf: SpeciesConfig, solid: list[tuple[int, int, tuple[int, int, int, int]]]
) -> list[tuple[float, float, float, tuple[int, int, int], float]]:
    if not solid:
        return []

    rng = seeded_rng(f"v5-particle-svg::{conf.key}")
    order = list(range(len(solid)))
    rng.shuffle(order)
    count = particle_count_for(conf)
    particles: list[tuple[float, float, float, tuple[int, int, int], float]] = []

    for i in range(count):
        x, y, rgba_px = solid[order[i % len(order)]]
        jitter = 0.34
        px = x + (rng.random() * 2 - 1) * jitter
        py = y + (rng.random() * 2 - 1) * jitter
        radius = 0.82 + rng.random() * 1.22
        rgb = rgba_px[:3]
        alpha = min(1.0, max(0.18, rgba_px[3] / 255))
        particles.append((px, py, radius, rgb, alpha))
    return particles


def view_box_for(
    particles: Iterable[tuple[float, float, float, tuple[int, int, int], float]]
) -> tuple[float, float, float, float]:
    parts = list(particles)
    min_x = min(x - r for x, _, r, _, _ in parts) - PADDING
    min_y = min(y - r for _, y, r, _, _ in parts) - PADDING
    max_x = max(x + r for x, _, r, _, _ in parts) + PADDING
    max_y = max(y + r for _, y, r, _, _ in parts) + PADDING
    return min_x, min_y, max_x - min_x, max_y - min_y


def build_svg(
    conf: SpeciesConfig,
    particles: list[tuple[float, float, float, tuple[int, int, int], float]],
) -> str:
    min_x, min_y, width, height = view_box_for(particles)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{min_x:.2f} {min_y:.2f} {width:.2f} {height:.2f}" '
            f'width="{width:.2f}" height="{height:.2f}" '
            f'aria-label="{conf.name} 粒子图形">'
        ),
        f'  <title>{conf.name} 粒子图形</title>',
        '  <g>',
    ]

    for x, y, radius, rgb, alpha in particles:
        lines.append(
            "    "
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
            f'fill="rgb({rgb[0]},{rgb[1]},{rgb[2]})" fill-opacity="{alpha:.3f}"/>'
        )

    lines.extend(["  </g>", "</svg>"])
    return "\n".join(lines) + "\n"


def export_species(conf: SpeciesConfig) -> Path:
    src = IMAGE_DIR / conf.image_file
    if not src.exists():
        raise FileNotFoundError(f"missing source image: {src}")

    image = Image.open(src)
    sampled = resize_for_sampling(image)
    solid = solid_pixels(sampled)
    particles = sample_particles(conf, solid)
    if not particles:
        raise RuntimeError(f"no solid pixels found for {conf.name}")

    svg_text = build_svg(conf, particles)
    out = OUTPUT_DIR / f"{conf.name}_粒子_v5.svg"
    out.write_text(svg_text, encoding="utf-8")
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exported = [export_species(conf) for conf in SPECIES_CONFIG]
    print(f"Exported {len(exported)} SVG files to {OUTPUT_DIR}")
    for path in exported:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
