from __future__ import annotations

import math
import sys
from pathlib import Path

from build123d import Box, Color, Compound, Cylinder, Pos, Rot, export_step


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "S44B-RAD1AK.stp"

# JST RAD connector, S44B-RAD1AK male header (44 circuits, side entry).
# Dimensions from the JST RAD connector catalog drawing, in millimeters.
# Model coordinates match the KiCad footprint: pin 1 at the origin, X along
# the pin rows, model +Y = footprint -Y (toward the rear pin rows), Z up from
# the board surface. The mating face points to footprint +Y.
CENTER_X_MM = -16.51  # midway between pin 1 (x = 0) and pin 14 (x = -33.02)
EAR_LINE_Y_MM = -11.5  # ears and retention posts, 11.5 in front of pin row 1
FRONT_TO_EAR_LINE_MM = 17.1
FRONT_Y_MM = EAR_LINE_Y_MM - FRONT_TO_EAR_LINE_MM

BODY_WIDTH_MM = 49.0
BODY_DEPTH_MM = 25.7  # front face to the rear face of the full-height box
BODY_HEIGHT_MM = 37.3
OVERALL_DEPTH_MM = 42.9  # front face to the rear of the side walls
BODY_STANDOFF_MM = 0.6

CAVITY_WIDTH_MM = 46.8
CAVITY_BOTTOM_Z_MM = 2.5
CAVITY_TOP_Z_MM = 35.6
CAVITY_DEPTH_MM = 18.0

EAR_HOLE_SPACING_MM = 53.34
EAR_HOLE_DIAMETER_MM = 2.4
EAR_RADIUS_MM = 4.0
EAR_HEIGHT_MM = 6.3

POST_SPACING_MM = 33.02
POST_DIAMETER_MM = 3.3
POST_BELOW_BOARD_MM = 3.6

SIDE_WALL_THICKNESS_MM = 3.5
SIDE_WALL_STEP_Z_MM = 21.4  # top of the side walls just behind the box
SIDE_WALL_STEP_DEPTH_MM = 31.4
SIDE_WALL_REAR_Z_MM = 10.8

TOP_TAB_HEIGHT_MM = 3.1
TOP_TAB_FIN_DEPTHS_MM = ((7.2, 8.5), (10.6, 11.9))
TOP_TABS = ((-16.5, 7.5), (0.0, 9.0), (16.5, 7.5))  # (x from center, width)

PIN_TAIL_BELOW_BOARD_MM = 2.8
PIN_BEND_RADIUS_MM = 0.8

# (footprint row y, face height above the board, pin x positions, terminal size)
PIN_ROWS = (
    (0.0, 8.8, [-2.54 * i for i in range(14)], "0.64"),
    (-3.0, 11.7, [-2.54 * i for i in range(14)], "0.64"),
    (-7.0, 21.8, [-2.54, -6.01, -9.51, -13.01, -16.51, -20.01, -23.51, -27.01, -30.48], "1.5"),
    (-11.0, 29.8, [-4.26, -9.51, -13.01, -16.51, -20.01, -23.51, -28.76], "1.5"),
)
POWER_PIN_X_MM = (-4.26, -28.76)  # the two 2.8 terminals at the ends of the top row

# terminal size -> (blade width, thickness, tail width, length into the cavity)
TERMINALS = {
    "0.64": (0.64, 0.64, 0.64, 8.0),
    "1.5": (1.5, 0.64, 0.9, 9.0),
    "2.8": (2.8, 0.8, 1.0, 10.0),
}

HOUSING_COLOR = (0.12, 0.12, 0.12)
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


def depth_to_y(depth: float) -> float:
    """Distance behind the mating face -> model Y."""
    return FRONT_Y_MM + depth


def make_housing():
    half_w = BODY_WIDTH_MM / 2.0
    x0, x1 = CENTER_X_MM - half_w, CENTER_X_MM + half_w
    housing = box_from_extents(x0, x1, depth_to_y(0), depth_to_y(BODY_DEPTH_MM), BODY_STANDOFF_MM, BODY_HEIGHT_MM)
    housing -= box_from_extents(
        CENTER_X_MM - CAVITY_WIDTH_MM / 2.0,
        CENTER_X_MM + CAVITY_WIDTH_MM / 2.0,
        depth_to_y(0) - 1.0,
        depth_to_y(CAVITY_DEPTH_MM),
        CAVITY_BOTTOM_Z_MM,
        CAVITY_TOP_Z_MM,
    )

    # Center guide rib with four square posts, as seen inside the mating cavity.
    rib_z = 17.6
    housing += box_from_extents(CENTER_X_MM - 13.0, CENTER_X_MM + 13.0, depth_to_y(3.0), depth_to_y(CAVITY_DEPTH_MM),
                                rib_z - 0.5, rib_z + 0.5)
    for dx in (-12.7, -5.5, 5.5, 12.7):
        housing += box_from_extents(CENTER_X_MM + dx - 1.2, CENTER_X_MM + dx + 1.2, depth_to_y(3.0),
                                    depth_to_y(CAVITY_DEPTH_MM), rib_z - 1.2, rib_z + 1.2)

    # Keying ribs on the inner side walls.
    inner = CAVITY_WIDTH_MM / 2.0
    for side in (-1, 1):
        for z0, z1 in ((27.0, 32.0), (7.0, 12.0)):
            xa = CENTER_X_MM + side * inner
            housing += box_from_extents(min(xa, xa - side * 1.2), max(xa, xa - side * 1.2), depth_to_y(2.0),
                                        depth_to_y(CAVITY_DEPTH_MM), z0, z1)

    # Lock tabs on the top: two thin fins bridged at the top.
    for dx, width in TOP_TABS:
        xa, xb = CENTER_X_MM + dx - width / 2.0, CENTER_X_MM + dx + width / 2.0
        top = BODY_HEIGHT_MM + TOP_TAB_HEIGHT_MM
        for d0, d1 in TOP_TAB_FIN_DEPTHS_MM:
            housing += box_from_extents(xa, xb, depth_to_y(d0), depth_to_y(d1), BODY_HEIGHT_MM - 0.01, top)
        housing += box_from_extents(xa, xb, depth_to_y(TOP_TAB_FIN_DEPTHS_MM[0][0]),
                                    depth_to_y(TOP_TAB_FIN_DEPTHS_MM[1][1]), top - 0.8, top)

    # Mounting ears with screw holes, down to the board surface.
    for side in (-1, 1):
        hole_x = CENTER_X_MM + side * EAR_HOLE_SPACING_MM / 2.0
        ear = box_from_extents(min(CENTER_X_MM + side * (half_w - 0.5), hole_x),
                               max(CENTER_X_MM + side * (half_w - 0.5), hole_x),
                               EAR_LINE_Y_MM - EAR_RADIUS_MM, EAR_LINE_Y_MM + EAR_RADIUS_MM, 0.0, EAR_HEIGHT_MM)
        ear += Pos(hole_x, EAR_LINE_Y_MM, EAR_HEIGHT_MM / 2.0) * Cylinder(EAR_RADIUS_MM, EAR_HEIGHT_MM)
        ear -= Pos(hole_x, EAR_LINE_Y_MM, EAR_HEIGHT_MM / 2.0) * Cylinder(EAR_HOLE_DIAMETER_MM / 2.0,
                                                                           EAR_HEIGHT_MM + 1.0)
        housing += ear

    # Split retention posts that snap into the board.
    for side in (-1, 1):
        post_x = CENTER_X_MM + side * POST_SPACING_MM / 2.0
        z0, z1 = -POST_BELOW_BOARD_MM, BODY_STANDOFF_MM + 0.01
        post = Pos(post_x, EAR_LINE_Y_MM, (z0 + z1) / 2.0) * Cylinder(POST_DIAMETER_MM / 2.0, z1 - z0)
        post -= box_from_extents(post_x - 0.4, post_x + 0.4, EAR_LINE_Y_MM - 2.0, EAR_LINE_Y_MM + 2.0, z0 - 0.1, -0.6)
        housing += post

    # Side walls around the pin field, with the stepped and sloped top edge.
    rear_y = depth_to_y(OVERALL_DEPTH_MM)
    for side in (-1, 1):
        xa = CENTER_X_MM + side * half_w
        xb = xa - side * SIDE_WALL_THICKNESS_MM
        wall = box_from_extents(min(xa, xb), max(xa, xb), depth_to_y(BODY_DEPTH_MM) - 0.01, rear_y,
                                BODY_STANDOFF_MM, SIDE_WALL_STEP_Z_MM)
        # Cut the slope: a rotated box removes the corner above the line from
        # (step depth, step z) to (overall depth, rear z).
        run = OVERALL_DEPTH_MM - SIDE_WALL_STEP_DEPTH_MM
        drop = SIDE_WALL_STEP_Z_MM - SIDE_WALL_REAR_Z_MM
        angle = math.degrees(math.atan2(drop, run))
        length = math.hypot(run, drop) * 2.0
        cutter = Pos((xa + xb) / 2.0, depth_to_y(SIDE_WALL_STEP_DEPTH_MM), SIDE_WALL_STEP_Z_MM) * Rot(-angle, 0, 0) * \
            Pos(0, length / 2.0, 10.0) * Box(SIDE_WALL_THICKNESS_MM + 2.0, length, 20.0)
        housing += wall - cutter

    # Tine plate the tails pass through, just above the board.
    housing += box_from_extents(x0 + SIDE_WALL_THICKNESS_MM - 0.01, x1 - SIDE_WALL_THICKNESS_MM + 0.01,
                                depth_to_y(BODY_DEPTH_MM) - 0.01, rear_y - 0.8, BODY_STANDOFF_MM, 2.6)

    return with_color(housing, HOUSING_COLOR)


def make_pin(x: float, row_y_fp: float, face_z: float, size: str):
    width, thick, tail_width, into_cavity = TERMINALS[size]
    r = PIN_BEND_RADIUS_MM
    bend_y = -row_y_fp  # model Y of the vertical leg (footprint hole)
    tip_y = depth_to_y(CAVITY_DEPTH_MM - into_cavity)
    xa, xb = x - width / 2.0, x + width / 2.0

    pin = box_from_extents(xa, xb, tip_y, bend_y - r, face_z - thick / 2.0, face_z + thick / 2.0)
    pin += box_from_extents(xa, xb, bend_y - thick / 2.0, bend_y + thick / 2.0, 2.0, face_z - r)

    # Rounded 90 degree bend between the horizontal and vertical legs.
    center_y, center_z = bend_y - r, face_z - r
    ring = Rot(0, 90, 0) * Cylinder(r + thick / 2.0, width)
    ring -= Rot(0, 90, 0) * Cylinder(max(r - thick / 2.0, 0.01), width + 1.0)
    ring = Pos(x, center_y, center_z) * ring
    quadrant = box_from_extents(xa - 0.1, xb + 0.1, center_y, center_y + r + thick, center_z, center_z + r + thick)
    pin += ring & quadrant

    # Narrower press-in tail through the board.
    pin += box_from_extents(x - tail_width / 2.0, x + tail_width / 2.0, bend_y - thick / 2.0, bend_y + thick / 2.0,
                            -PIN_TAIL_BELOW_BOARD_MM, 2.01)
    return with_color(pin, PIN_COLOR)


def make_model() -> Compound:
    """Create the S44B-RAD1AK header aligned to the KiCad footprint."""
    parts = [make_housing()]
    for row_y, face_z, xs, size in PIN_ROWS:
        for x in xs:
            pin_size = "2.8" if size == "1.5" and row_y == -11.0 and x in POWER_PIN_X_MM else size
            parts.append(make_pin(x, row_y, face_z, pin_size))
    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
