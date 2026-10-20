from __future__ import annotations

from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Color,
    Compound,
    Cone,
    Cylinder,
    Helix,
    Line,
    Plane,
    Polygon,
    Pos,
    Rot,
    ThreePointArc,
    Torus,
    chamfer,
    export_step,
    extrude,
    fillet,
    make_face,
    revolve,
    sweep,
)


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "XFCN_T34008_M3_Terminal_Frame_PCB.step"

# Dimensions from the T34008 M3 terminal frame drawing, in millimeters.
BODY_X_MM = 7.90
BODY_Y_MM = 7.90
BODY_HEIGHT_MM = 11.20
PIN_SPACING_X_MM = 6.90
PIN_SPACING_Y_MM = 5.00
SHEET_THICKNESS_MM = 1.00
TAB_WIDTH_MM = 1.50
OUTER_SHOULDER_FROM_TOP_MM = 6.20
INNER_SHOULDER_FROM_TOP_MM = 5.40
OUTER_SHOULDER_Z_MM = BODY_HEIGHT_MM - OUTER_SHOULDER_FROM_TOP_MM
INNER_SHOULDER_Z_MM = BODY_HEIGHT_MM - INNER_SHOULDER_FROM_TOP_MM
BEND_RADIUS_MM = 0.45
M3_THREAD_MAJOR_DIAMETER_MM = 3.00
M3_THREAD_MINOR_DIAMETER_MM = 2.50
M3_EMBOSS_DIAMETER_MM = 4.20
M3_CENTER_TOTAL_THICKNESS_MM = 2.20
M3_UNDERSIDE_EMBOSS_HEIGHT_MM = M3_CENTER_TOTAL_THICKNESS_MM - SHEET_THICKNESS_MM
# M3 Phillips pan head screw, ISO 7045 (dk 5.6, k 2.4) with an H1 recess.
SCREW_HEAD_DIAMETER_MM = 5.60
SCREW_HEAD_HEIGHT_MM = 2.40
SCREW_HEAD_FLANK_HEIGHT_MM = 1.30  # straight-ish side before the domed crown
SCREW_HEAD_FLANK_TOP_RADIUS_MM = 2.62
SCREW_HEAD_UNDERSIDE_GAP_MM = 1.00
SCREW_THREAD_LENGTH_MM = 5.00
SCREW_THREAD_PITCH_MM = 0.50
SCREW_THREAD_MINOR_RADIUS_MM = 1.19
SCREW_THREAD_RUNOUT_MM = 0.30
SCREW_TIP_CHAMFER_MM = 0.30
PHILLIPS_RECESS_DIAMETER_MM = 3.00
PHILLIPS_WING_WIDTH_MM = 0.70
PHILLIPS_RECESS_DEPTH_MM = 1.75
PHILLIPS_CONE_TOP_RADIUS_MM = 0.85

METAL_COLOR = (0.74, 0.72, 0.66)
SCREW_COLOR = (0.72, 0.73, 0.75)  # bright zinc-plated steel


def with_color(part, color: tuple[float, float, float] = METAL_COLOR):
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


def fillet_outer_bend_edges(part, body_x_min: float, body_x_max: float):
    bend_edges = []
    for edge in part.edges():
        center = edge.center()
        bounds = edge.bounding_box()
        y_length = bounds.max.Y - bounds.min.Y
        is_long_side_edge = abs(y_length - BODY_Y_MM) < 1e-6
        is_top_outer_bend = abs(center.Z - BODY_HEIGHT_MM) < 1e-6 and (
            abs(center.X - body_x_min) < 1e-6 or abs(center.X - body_x_max) < 1e-6
        )
        if is_long_side_edge and is_top_outer_bend:
            bend_edges.append(edge)

    try:
        return fillet(bend_edges, BEND_RADIUS_MM)
    except Exception:
        return part


def make_m3_phillips_screw(center_x: float, center_y: float):
    head_bottom_z = BODY_HEIGHT_MM + SCREW_HEAD_UNDERSIDE_GAP_MM

    major_r = M3_THREAD_MAJOR_DIAMETER_MM / 2.0
    minor_r = SCREW_THREAD_MINOR_RADIUS_MM

    # Pan head: near-vertical flank rising into a domed crown, revolved about Z.
    flank_top = (SCREW_HEAD_FLANK_TOP_RADIUS_MM, SCREW_HEAD_FLANK_HEIGHT_MM)
    crown = (0.0, SCREW_HEAD_HEIGHT_MM)
    head_outline = (
        Line((0.0, 0.0), (SCREW_HEAD_DIAMETER_MM / 2.0, 0.0))
        + Line((SCREW_HEAD_DIAMETER_MM / 2.0, 0.0), flank_top)
        + ThreePointArc(flank_top, (1.60, 2.20), crown)
        + Line(crown, (0.0, 0.0))
    )
    head = revolve(Plane.XZ * make_face(head_outline), axis=Axis.Z)
    head = softened(head, 0.08)

    # H1 Phillips recess: two crossed slots with sloped floors plus a center cone.
    top = SCREW_HEAD_HEIGHT_MM
    half = PHILLIPS_RECESS_DIAMETER_MM / 2.0
    slot = Plane.XZ * Polygon(
        (-half, top + 0.5),
        (half, top + 0.5),
        (half, top - 0.45),
        (0.32, top - PHILLIPS_RECESS_DEPTH_MM + 0.15),
        (-0.32, top - PHILLIPS_RECESS_DEPTH_MM + 0.15),
        (-half, top - 0.45),
        align=None,
    )
    slot = extrude(slot, amount=PHILLIPS_WING_WIDTH_MM / 2.0, both=True)
    recess = slot + Rot(0, 0, 90) * slot
    cone_height = PHILLIPS_RECESS_DEPTH_MM + 0.5
    recess += Pos(0, 0, top - PHILLIPS_RECESS_DEPTH_MM) * Cone(
        0.12, PHILLIPS_CONE_TOP_RADIUS_MM + 0.5 * 0.55, cone_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    head = head - recess

    # Threaded shank: minor-diameter core with a 60 degree helical thread,
    # a short runout under the head and a chamfered tip.
    core = Cylinder(minor_r, SCREW_THREAD_LENGTH_MM, align=(Align.CENTER, Align.CENTER, Align.MAX))
    core = chamfer(core.edges().group_by(Axis.Z)[0], SCREW_TIP_CHAMFER_MM)
    thread_height = SCREW_THREAD_LENGTH_MM - SCREW_THREAD_RUNOUT_MM - SCREW_TIP_CHAMFER_MM - 0.2
    flank = 0.22
    thread_profile = Plane.XZ * Polygon(
        (minor_r - 0.05, -flank),
        (major_r, -0.03),
        (major_r, 0.03),
        (minor_r - 0.05, flank),
        align=None,
    )
    helix = Helix(pitch=SCREW_THREAD_PITCH_MM, height=thread_height, radius=minor_r)
    thread = sweep(thread_profile, path=helix, is_frenet=True)
    thread = Pos(0, 0, -SCREW_THREAD_LENGTH_MM + SCREW_TIP_CHAMFER_MM + 0.2) * thread
    runout = Cylinder(major_r - 0.05, SCREW_THREAD_RUNOUT_MM, align=(Align.CENTER, Align.CENTER, Align.MAX))

    # The swept thread is kept as its own solid: fusing it to the core fails in OCCT.
    screw = Pos(center_x, center_y, head_bottom_z) * (head + core + runout)
    thread = Pos(center_x, center_y, head_bottom_z) * thread
    return [with_color(screw, SCREW_COLOR), with_color(thread, SCREW_COLOR)]


def make_model() -> Compound:
    """Create the M3 terminal frame aligned to the KiCad footprint pad centers."""
    body_x_min = -0.50
    body_x_max = body_x_min + BODY_X_MM
    body_y_min = -(BODY_Y_MM - PIN_SPACING_Y_MM) / 2.0 - PIN_SPACING_Y_MM
    body_y_max = body_y_min + BODY_Y_MM
    top_z_min = BODY_HEIGHT_MM - SHEET_THICKNESS_MM
    center_x = PIN_SPACING_X_MM / 2.0
    center_y = -PIN_SPACING_Y_MM / 2.0

    screw_cut = Pos(center_x, center_y, BODY_HEIGHT_MM / 2.0) * Cylinder(
        M3_THREAD_MINOR_DIAMETER_MM / 2.0,
        BODY_HEIGHT_MM + M3_CENTER_TOTAL_THICKNESS_MM + 2.0,
    )

    # Form the part as one continuous 1 mm sheet: top plate, side flanges,
    # and lower mounting tabs at the four footprint hole centers.
    outer_shell = box_from_extents(body_x_min, body_x_max, body_y_min, body_y_max, top_z_min, BODY_HEIGHT_MM)
    for x_min, x_max in (
        (body_x_min, body_x_min + SHEET_THICKNESS_MM),
        (body_x_max - SHEET_THICKNESS_MM, body_x_max),
    ):
        outer_shell += box_from_extents(x_min, x_max, body_y_min, body_y_max, OUTER_SHOULDER_Z_MM, top_z_min)

    metal = fillet_outer_bend_edges(outer_shell, body_x_min, body_x_max)

    for x in (0.0, PIN_SPACING_X_MM):
        for y in (0.0, -PIN_SPACING_Y_MM):
            metal += Pos(x, y, INNER_SHOULDER_Z_MM / 2.0) * Box(
                SHEET_THICKNESS_MM,
                TAB_WIDTH_MM,
                INNER_SHOULDER_Z_MM,
            )

    emboss = Pos(center_x, center_y, top_z_min - M3_UNDERSIDE_EMBOSS_HEIGHT_MM / 2.0) * Cylinder(
        M3_EMBOSS_DIAMETER_MM / 2.0,
        M3_UNDERSIDE_EMBOSS_HEIGHT_MM,
    )
    metal += emboss
    metal = metal - screw_cut
    metal = softened(metal, 0.08)
    metal = with_color(metal)

    parts = [metal]

    # Small internal rings give the M3 threaded hole visible detail in KiCad's
    # viewer without requiring a heavy fully modeled helical thread.
    for z in (9.30, 9.80, 10.30, 10.80):
        thread_ring = Pos(center_x, center_y, z) * Torus(
            M3_THREAD_MAJOR_DIAMETER_MM / 2.0,
            0.035,
        )
        parts.append(with_color(thread_ring))

    parts.extend(make_m3_phillips_screw(center_x, center_y))

    return Compound(children=parts)


def main() -> None:
    SHAPES_DIR.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), STEP_PATH)
    print(f"Wrote {STEP_PATH}")


if __name__ == "__main__":
    main()
