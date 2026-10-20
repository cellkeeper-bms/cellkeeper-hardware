from __future__ import annotations

import sys
from pathlib import Path

from build123d import Box, Color, Compound, Pos, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "Hirose_ZE05H-8DP-2H.step"

# Hirose ZE05H-8DP-2H right-angle SMT receptacle (LCSC C17284895).
# Dimensions from the Hirose ZE05 catalog (Dec. 2024), 8-position row:
# A = 10.0 pin span, B = 18.52 across the side bosses, C = 19.9 across the
# retention tabs, D = 8.84 height, 14.8 front face to tail ends.
# Model coordinates match the KiCad footprint CONN_ZE05H-8DP-2H_HIR:
# SMT tails at footprint y = -6.65, retention tab pads at x = +/-8.9,
# y = 0.50; the mating face points to footprint +Y (model -Y).
WIDTH_C_MM = 19.9
WIDTH_B_MM = 18.52
HEIGHT_D_MM = 8.84
OVERALL_DEPTH_MM = 14.8
HOUSING_HALF_WIDTH_MM = WIDTH_C_MM / 2.0 - 2.17
HOUSING_DEPTH_MM = 12.0
STANDOFF_MM = 0.4

TAB_CENTER_FROM_FRONT_MM = 6.5
TAB_PAD_Y_FP_MM = 0.5046
FRONT_Y_MM = -(TAB_PAD_Y_FP_MM + TAB_CENTER_FROM_FRONT_MM)  # model Y of the mating face
REAR_Y_MM = FRONT_Y_MM + HOUSING_DEPTH_MM
TAIL_END_Y_MM = FRONT_Y_MM + OVERALL_DEPTH_MM

CAVITY_WALL_MM = 0.7
CAVITY_TOP_WALL_MM = 0.95
CAVITY_FLOOR_Z_MM = 0.8
CAVITY_DEPTH_MM = 8.5
KEY_HALF_WIDTH_MM = 2.3
KEY_DROP_MM = 2.4

BOSS_HEIGHT_MM = 4.5
BOSS_FRONT_INSET_MM = 1.24
NAIL_LENGTH_MM = 6.4
NAIL_THICKNESS_MM = 0.15
NAIL_HEIGHT_MM = 3.5

UPPER_ROW_Z_MM = 5.47
LOWER_ROW_Z_MM = 2.73
UPPER_ROW_X_MM = (4.0, -4.0)  # pins 1, 2
LOWER_ROW_X_MM = (5.0, 3.0, 1.0, -1.0, -3.0, -5.0)  # pins 3 to 8
PIN_SIZE_MM = 0.5
PIN_INTO_CAVITY_MM = 6.0
TAIL_THICKNESS_MM = 0.3
TAIL_LEG_Y_MM = REAR_Y_MM + 0.6

HOUSING_COLOR = (0.10, 0.10, 0.10)
PIN_COLOR = (0.80, 0.80, 0.78)
NAIL_COLOR = (0.75, 0.75, 0.73)


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


def make_housing():
    hw = HOUSING_HALF_WIDTH_MM
    housing = softened(box_from_extents(-hw, hw, FRONT_Y_MM, REAR_Y_MM, STANDOFF_MM, HEIGHT_D_MM), 0.2)
    inner = hw - CAVITY_WALL_MM
    housing -= box_from_extents(-inner, inner, FRONT_Y_MM - 1.0, FRONT_Y_MM + CAVITY_DEPTH_MM,
                                CAVITY_FLOOR_Z_MM, HEIGHT_D_MM - CAVITY_TOP_WALL_MM)

    # Polarizing key hanging from the cavity roof.
    roof = HEIGHT_D_MM - CAVITY_TOP_WALL_MM
    housing += box_from_extents(-KEY_HALF_WIDTH_MM, KEY_HALF_WIDTH_MM, FRONT_Y_MM + 0.3,
                                FRONT_Y_MM + CAVITY_DEPTH_MM + 0.01, roof - KEY_DROP_MM, roof + 0.01)

    # Two grooves across the top, as in the catalog photo.
    for d0, d1 in ((2.0, 4.5), (9.9, 10.9)):
        housing -= box_from_extents(-hw + 1.6, hw - 1.6, FRONT_Y_MM + d0, FRONT_Y_MM + d1,
                                    HEIGHT_D_MM - 0.3, HEIGHT_D_MM + 1.0)

    # Side bosses that carry the metal retention tabs.
    for side in (-1, 1):
        xa, xb = side * (hw - 0.01), side * WIDTH_B_MM / 2.0
        boss = box_from_extents(min(xa, xb), max(xa, xb), FRONT_Y_MM + BOSS_FRONT_INSET_MM, REAR_Y_MM,
                                STANDOFF_MM, BOSS_HEIGHT_MM)
        housing += boss

    # Rear corner guides beside the tails.
    for side in (-1, 1):
        xa, xb = side * (hw - 1.5), side * hw
        housing += box_from_extents(min(xa, xb), max(xa, xb), REAR_Y_MM - 0.01, TAIL_END_Y_MM, STANDOFF_MM, 2.0)

    return with_color(housing, HOUSING_COLOR)


def make_nail(side: int):
    y0 = -TAB_PAD_Y_FP_MM - NAIL_LENGTH_MM / 2.0
    y1 = y0 + NAIL_LENGTH_MM
    outer = side * WIDTH_C_MM / 2.0
    under = side * (WIDTH_C_MM / 2.0 - 1.43)
    face = side * WIDTH_B_MM / 2.0
    nail = box_from_extents(min(under, outer), max(under, outer), y0, y1, 0.0, NAIL_THICKNESS_MM)
    nail += box_from_extents(min(face, face + side * NAIL_THICKNESS_MM), max(face, face + side * NAIL_THICKNESS_MM),
                             y0 + 0.7, y1 - 0.7, 0.0, NAIL_HEIGHT_MM)
    return with_color(nail, NAIL_COLOR)


def make_pin(x: float, z: float):
    s = PIN_SIZE_MM / 2.0
    tip_y = FRONT_Y_MM + CAVITY_DEPTH_MM - PIN_INTO_CAVITY_MM
    pin = box_from_extents(x - s, x + s, tip_y, TAIL_LEG_Y_MM + s, z - s, z + s)
    pin += box_from_extents(x - s, x + s, TAIL_LEG_Y_MM - s, TAIL_LEG_Y_MM + s, 0.0, z + s)
    pin += box_from_extents(x - s, x + s, TAIL_LEG_Y_MM - s, TAIL_END_Y_MM, 0.0, TAIL_THICKNESS_MM)
    return with_color(pin, PIN_COLOR)


def make_model() -> Compound:
    """Create the ZE05H-8DP-2H aligned to the KiCad footprint."""
    parts = [make_housing(), make_nail(-1), make_nail(1)]
    for x in UPPER_ROW_X_MM:
        parts.append(make_pin(x, UPPER_ROW_Z_MM))
    for x in LOWER_ROW_X_MM:
        parts.append(make_pin(x, LOWER_ROW_Z_MM))
    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
