from __future__ import annotations

import math
import sys
from pathlib import Path

from build123d import (
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Color,
    Compound,
    Cylinder,
    FilletPolyline,
    Plane,
    Pos,
    Rectangle,
    Rot,
    chamfer,
    export_step,
    fillet,
    sweep,
)


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "TE_173864-1.step"

# TE 173864-1, 070 Multilock 24-position right-angle cap housing (J17).
# Dimensions from TE customer drawing C-173864 rev E7: 72 between the
# mounting holes, 65 body length, 78.6 over the ears, 15.8 tall, 18.5 deep
# from the ear back face, 7 deep ears with 2x D2.4 holes 3.5 from the back
# face, two cavities 26.2 and 33.2 long and 12.8 high, contact rows 5.9
# apart with the lower one 3.15 above the cavity floor, 0.64 square tails
# on a 4.6 row pitch, 4 below the housing.
# Model coordinates match the KiCad footprint
# BMS_Library__CONN_173864-1_TYC_Empty_Pins: drawing position 0 is the
# column at footprint x = -50.898, the row nearer the housing is at
# footprint y = 0, the outer row at y = +4.6, and the mating face points to
# footprint -Y (model +Y).
PIN0_X_MM = -50.898104
MODULE_1_POSITIONS_MM = (0.0, 3.5, 9.0, 12.5, 18.0, 21.5)
MODULE_2_START_MM = 28.8
MODULE_2_POSITIONS_MM = (0.0, 3.5, 7.0, 12.5, 16.0, 21.5, 25.0, 28.5)
LOWER_ROW_ONLY_MM = (9.0, 12.5, 41.3, 44.8)

PIN_SPAN_MM = MODULE_2_START_MM + MODULE_2_POSITIONS_MM[-1]
CENTER_X_MM = PIN0_X_MM + PIN_SPAN_MM / 2.0
BODY_LENGTH_MM = 65.0
HOLE_PITCH_MM = 72.0
EAR_TIP_HALF_MM = 78.6 / 2.0

HEIGHT_MM = 15.8
BACK_Y_MM = 1.5
FRONT_Y_MM = BACK_Y_MM + 18.5
EAR_DEPTH_MM = 7.0
EAR_HEIGHT_MM = 4.2
EAR_HOLE_D_MM = 2.4
EAR_HOLE_Y_MM = BACK_Y_MM + 3.5
END_CHAMFER_MM = 1.8

WALL_MM = 1.5
CAVITY_HEIGHT_MM = 12.8
CAVITY_END_MARGIN_MM = 2.35
CAVITY_LENGTHS_MM = (26.2, 33.2)
CAVITY_BACK_Y_MM = BACK_Y_MM + 4.0
CAVITY_CHAMFER_MM = 1.2
KEY_LENGTH_MM = 3.3
KEY_DROP_MM = 1.1
POLARIZING_GROOVE_MM = 2.4  # square edge, turned 45 degrees: 3.4 wide V
GROOVE_START_Y_MM = BACK_Y_MM + 4.1

LOWER_CONTACT_Z_MM = WALL_MM + 3.15
UPPER_CONTACT_Z_MM = LOWER_CONTACT_Z_MM + 5.9
OUTER_ROW_Y_MM = -4.6
PIN_SIZE_MM = 0.64
PIN_BEND_RADIUS_MM = 0.8
TAB_TIP_Y_MM = BACK_Y_MM + 10.9
TAIL_TIP_Z_MM = -4.0
PIN_POINT_MM = 0.2

HOUSING_COLOR = (0.92, 0.90, 0.83)  # natural PBT
PIN_COLOR = (0.80, 0.80, 0.78)


def with_color(part, color: tuple[float, float, float]):
    part.color = Color(*color)
    return part


def box_from_extents(x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float):
    return Pos(
        (x_min + x_max) / 2.0,
        (y_min + y_max) / 2.0,
        (z_min + z_max) / 2.0,
    ) * Box(x_max - x_min, y_max - y_min, z_max - z_min)


def chamfer_top_y_edges(part, length: float):
    return chamfer(part.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], length)


def cavity_extents() -> list[tuple[float, float]]:
    starts = (0.0, MODULE_2_START_MM)
    return [
        (PIN0_X_MM + s - CAVITY_END_MARGIN_MM, PIN0_X_MM + s - CAVITY_END_MARGIN_MM + length)
        for s, length in zip(starts, CAVITY_LENGTHS_MM)
    ]


def make_housing():
    half = BODY_LENGTH_MM / 2.0
    housing = box_from_extents(CENTER_X_MM - half, CENTER_X_MM + half, BACK_Y_MM, FRONT_Y_MM, 0.0, HEIGHT_MM)
    housing = chamfer_top_y_edges(housing, END_CHAMFER_MM)

    roof = WALL_MM + CAVITY_HEIGHT_MM
    for x0, x1 in cavity_extents():
        cavity = box_from_extents(x0, x1, CAVITY_BACK_Y_MM, FRONT_Y_MM + 1.0, WALL_MM, roof)
        housing -= chamfer_top_y_edges(cavity, CAVITY_CHAMFER_MM)

    # Keys hanging from the roof over the single-row positions.
    for a, b in ((LOWER_ROW_ONLY_MM[0], LOWER_ROW_ONLY_MM[1]), (LOWER_ROW_ONLY_MM[2], LOWER_ROW_ONLY_MM[3])):
        x = PIN0_X_MM + (a + b) / 2.0
        housing += box_from_extents(x - KEY_LENGTH_MM / 2.0, x + KEY_LENGTH_MM / 2.0, CAVITY_BACK_Y_MM - 0.01,
                                    FRONT_Y_MM - 2.0, roof - KEY_DROP_MM, roof + 0.01)

    # Polarizing V groove along the top, over the wall between the cavities.
    (_, c1_end), (c2_start, _) = cavity_extents()
    groove_len = FRONT_Y_MM - GROOVE_START_Y_MM + 1.0
    housing -= (
        Pos((c1_end + c2_start) / 2.0, GROOVE_START_Y_MM + groove_len / 2.0, HEIGHT_MM)
        * Rot(0, 45, 0)
        * Box(POLARIZING_GROOVE_MM, groove_len, POLARIZING_GROOVE_MM)
    )

    # Screw-down ears with rounded tips.
    for side in (-1, 1):
        xa, xb = CENTER_X_MM + side * (half - 0.01), CENTER_X_MM + side * EAR_TIP_HALF_MM
        ear = box_from_extents(min(xa, xb), max(xa, xb), BACK_Y_MM, BACK_Y_MM + EAR_DEPTH_MM, 0.0, EAR_HEIGHT_MM)
        tip_edges = ear.edges().filter_by(Axis.Z).sort_by(Axis.X)
        ear = fillet(tip_edges[-2:] if side > 0 else tip_edges[:2], 3.0)
        hole_x = CENTER_X_MM + side * HOLE_PITCH_MM / 2.0
        ear -= Pos(hole_x, EAR_HOLE_Y_MM, EAR_HEIGHT_MM / 2.0) * Cylinder(EAR_HOLE_D_MM / 2.0, EAR_HEIGHT_MM + 1.0)
        housing += ear

    return with_color(housing, HOUSING_COLOR)


def make_pin(x: float, tail_y: float, contact_z: float):
    with BuildPart() as pin:
        with BuildLine() as path:
            FilletPolyline(
                (x, TAB_TIP_Y_MM, contact_z),
                (x, tail_y, contact_z),
                (x, tail_y, TAIL_TIP_Z_MM),
                radius=PIN_BEND_RADIUS_MM,
            )
        with BuildSketch(Plane(origin=path.line @ 0, x_dir=(1, 0, 0), z_dir=path.line % 0)):
            Rectangle(PIN_SIZE_MM, PIN_SIZE_MM)
        sweep()
    part = pin.part
    part = chamfer(part.faces().sort_by(Axis.Z)[0].edges(), PIN_POINT_MM)
    part = chamfer(part.faces().sort_by(Axis.Y)[-1].edges(), PIN_POINT_MM)
    return with_color(part, PIN_COLOR)


def pin_positions_mm() -> list[float]:
    return [*MODULE_1_POSITIONS_MM, *(MODULE_2_START_MM + p for p in MODULE_2_POSITIONS_MM)]


def make_model() -> Compound:
    """Create the 173864-1 aligned to the KiCad footprint."""
    parts = [make_housing()]
    for p in pin_positions_mm():
        x = PIN0_X_MM + p
        parts.append(make_pin(x, 0.0, LOWER_CONTACT_Z_MM))
        if not any(math.isclose(p, q) for q in LOWER_ROW_ONLY_MM):
            parts.append(make_pin(x, OUTER_ROW_Y_MM, UPPER_CONTACT_Z_MM))
    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
