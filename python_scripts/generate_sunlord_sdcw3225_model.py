from __future__ import annotations

import sys
from pathlib import Path

from build123d import Box, Color, Compound, Pos, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "Sunlord_SDCW3225S-2.step"

# Sunlord SDCW3225S-2-102TF common-mode filter (LCSC C192586), 3.2 x 2.5 x 1.9 mm.
# Model coordinates match the KiCad footprint FILTER-SMD_4P-L3.2-W2.5-BL:
# the 3.2 mm length runs along Y and the four pads sit at x = +/-0.85, y = +/-1.53.
LENGTH_Y_MM = 3.2
WIDTH_X_MM = 2.5
HEIGHT_MM = 1.9
FLANGE_TOP_Z_MM = 0.55
TOP_PLATE_Z_MM = 1.45
STANDOFF_MM = 0.05

CORE_X_MM = 2.0
CORE_Y_MM = 2.1
WINDING_X_MM = 2.3
WINDING_Y_MM = 1.9

TERMINAL_X_MM = 0.85
TERMINAL_WIDTH_MM = 0.6
TERMINAL_THICKNESS_MM = 0.1
TERMINAL_BOTTOM_LENGTH_MM = 0.5
TERMINAL_RISE_MM = 0.5

FERRITE_COLOR = (0.18, 0.18, 0.18)
TOP_PLATE_COLOR = (0.08, 0.08, 0.08)
WIRE_COLOR = (0.72, 0.45, 0.20)
TERMINAL_COLOR = (0.80, 0.80, 0.78)


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
    """Create the filter centered on the KiCad footprint origin."""
    hx, hy = WIDTH_X_MM / 2.0, LENGTH_Y_MM / 2.0
    flange = softened(box_from_extents(-hx, hx, -hy, hy, STANDOFF_MM, FLANGE_TOP_Z_MM), 0.05)
    core = box_from_extents(-CORE_X_MM / 2, CORE_X_MM / 2, -CORE_Y_MM / 2, CORE_Y_MM / 2,
                            FLANGE_TOP_Z_MM - 0.01, TOP_PLATE_Z_MM + 0.01)
    winding = softened(box_from_extents(-WINDING_X_MM / 2, WINDING_X_MM / 2, -WINDING_Y_MM / 2, WINDING_Y_MM / 2,
                                        FLANGE_TOP_Z_MM + 0.05, TOP_PLATE_Z_MM - 0.05), 0.15)
    top_plate = softened(box_from_extents(-hx, hx, -hy, hy, TOP_PLATE_Z_MM, HEIGHT_MM), 0.05)

    parts = [
        with_color(flange, FERRITE_COLOR),
        with_color(core, FERRITE_COLOR),
        with_color(winding, WIRE_COLOR),
        with_color(top_plate, TOP_PLATE_COLOR),
    ]

    t = TERMINAL_THICKNESS_MM
    for x in (-TERMINAL_X_MM, TERMINAL_X_MM):
        for side in (-1, 1):
            x0, x1 = x - TERMINAL_WIDTH_MM / 2, x + TERMINAL_WIDTH_MM / 2
            inner, outer = side * (hy - TERMINAL_BOTTOM_LENGTH_MM), side * (hy + t)
            terminal = box_from_extents(x0, x1, min(inner, outer), max(inner, outer), 0.0, t)
            face_a, face_b = side * hy, side * (hy + t)
            terminal += box_from_extents(x0, x1, min(face_a, face_b), max(face_a, face_b), 0.0, TERMINAL_RISE_MM)
            parts.append(with_color(terminal, TERMINAL_COLOR))

    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
