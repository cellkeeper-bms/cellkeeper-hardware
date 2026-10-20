from __future__ import annotations

import sys
from pathlib import Path

from build123d import Box, Color, Compound, Cylinder, Pos, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "Inductor_2016_AOTA-B201610.step"

# AOTA-B201610S3R3-101-T molded power inductor (LCSC C42411119), 2.0 x 1.6 x 1.0 mm.
# Model coordinates match the KiCad footprint L_pol_2016: pads at x = +/-0.7,
# pin 1 (polarity dot) on the -X side.
LENGTH_X_MM = 2.0
WIDTH_Y_MM = 1.6
HEIGHT_MM = 1.0
STANDOFF_MM = 0.02

TERMINAL_INNER_X_MM = 0.45
TERMINAL_WIDTH_Y_MM = 1.3
TERMINAL_THICKNESS_MM = 0.05
TERMINAL_RISE_MM = 0.35

DOT_X_MM = -0.55
DOT_DIAMETER_MM = 0.3

BODY_COLOR = (0.22, 0.22, 0.24)
TERMINAL_COLOR = (0.80, 0.80, 0.78)
DOT_COLOR = (0.85, 0.85, 0.85)


def with_color(part, color: tuple[float, float, float]):
    part.color = Color(*color)
    return part


def softened(part, radius: float):
    try:
        return fillet(part.edges(), radius)
    except Exception:
        return part


def box_from_extents(x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float):
    return Pos(
        (x_min + x_max) / 2.0,
        (y_min + y_max) / 2.0,
        (z_min + z_max) / 2.0,
    ) * Box(x_max - x_min, y_max - y_min, z_max - z_min)


def make_model() -> Compound:
    """Create the inductor centered on the KiCad footprint origin."""
    hx, hy = LENGTH_X_MM / 2.0, WIDTH_Y_MM / 2.0
    body = softened(box_from_extents(-hx, hx, -hy, hy, STANDOFF_MM, HEIGHT_MM), 0.06)
    parts = [with_color(body, BODY_COLOR)]

    t = TERMINAL_THICKNESS_MM
    ty = TERMINAL_WIDTH_Y_MM / 2.0
    for side in (-1, 1):
        inner, outer = side * TERMINAL_INNER_X_MM, side * (hx + t)
        terminal = box_from_extents(min(inner, outer), max(inner, outer), -ty, ty, 0.0, STANDOFF_MM + t)
        face_a, face_b = side * hx, side * (hx + t)
        terminal += box_from_extents(min(face_a, face_b), max(face_a, face_b), -ty, ty, 0.0, TERMINAL_RISE_MM)
        parts.append(with_color(terminal, TERMINAL_COLOR))

    dot = Pos(DOT_X_MM, 0.0, HEIGHT_MM + 0.005) * Cylinder(DOT_DIAMETER_MM / 2.0, 0.01)
    parts.append(with_color(dot, DOT_COLOR))
    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
