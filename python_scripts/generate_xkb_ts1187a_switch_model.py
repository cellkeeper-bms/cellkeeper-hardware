from __future__ import annotations

from pathlib import Path

from build123d import Axis, Box, Color, Compound, Cylinder, Pos, chamfer, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "SW_Push_1P1T_XKB_TS-1187A.step"

# XKB TS-1187A-B-A-B (LCSC C318884): 5.1 x 5.1 mm SMD tact switch, 1.5 mm tall.
# Lead positions match the KiCad footprint pads (x = +/-3.0, y = +/-1.875).
BODY_SIZE_MM = 5.10
BODY_CORNER_CHAMFER_MM = 0.90
BODY_BOTTOM_Z_MM = 0.05
BODY_TOP_Z_MM = 0.95
PLATEAU_SIZE_MM = 3.90
PLATEAU_CORNER_CHAMFER_MM = 1.00
PLATEAU_TOP_Z_MM = 1.07
ACTUATOR_DIAMETER_MM = 2.00
TOTAL_HEIGHT_MM = 1.50
LEAD_PITCH_Y_MM = 3.75
LEAD_WIDTH_MM = 0.50
LEAD_THICKNESS_MM = 0.15
LEAD_TIP_X_MM = 2.90
LEAD_EXIT_Z_MM = 0.50

BODY_COLOR = (0.70, 0.71, 0.70)
LEAD_COLOR = (0.62, 0.62, 0.62)
ACTUATOR_COLOR = (0.85, 0.65, 0.16)


def with_color(part, color: tuple[float, float, float]):
    part.color = Color(*color)
    return part


def softened(part, radius: float, edges=None):
    try:
        return fillet(edges if edges is not None else part.edges(), radius)
    except Exception:
        return part


def box_from_extents(x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float):
    return Pos(
        (x_min + x_max) / 2.0,
        (y_min + y_max) / 2.0,
        (z_min + z_max) / 2.0,
    ) * Box(x_max - x_min, y_max - y_min, z_max - z_min)


def octagon_prism(size: float, corner: float, z_min: float, z_max: float):
    prism = Pos(0, 0, (z_min + z_max) / 2.0) * Box(size, size, z_max - z_min)
    return chamfer(prism.edges().filter_by(Axis.Z), corner)


def make_lead(side: int, y: float):
    """Gull-wing lead leaving the body side and landing on the pad."""
    half_body = BODY_SIZE_MM / 2.0
    x_in = half_body - 0.15
    x_bend = half_body + LEAD_THICKNESS_MM
    x_tip = LEAD_TIP_X_MM
    y_min, y_max = y - LEAD_WIDTH_MM / 2.0, y + LEAD_WIDTH_MM / 2.0

    def span(a: float, b: float):
        return (min(a * side, b * side), max(a * side, b * side))

    lead = box_from_extents(*span(x_in, x_bend), y_min, y_max, LEAD_EXIT_Z_MM - LEAD_THICKNESS_MM, LEAD_EXIT_Z_MM)
    lead += box_from_extents(*span(half_body, x_bend), y_min, y_max, 0.0, LEAD_EXIT_Z_MM)
    lead += box_from_extents(*span(half_body, x_tip), y_min, y_max, 0.0, LEAD_THICKNESS_MM)
    return with_color(lead, LEAD_COLOR)


def make_model() -> Compound:
    """Create the switch centered on the KiCad footprint origin."""
    body = octagon_prism(BODY_SIZE_MM, BODY_CORNER_CHAMFER_MM, BODY_BOTTOM_Z_MM, BODY_TOP_Z_MM)
    body += octagon_prism(PLATEAU_SIZE_MM, PLATEAU_CORNER_CHAMFER_MM, BODY_TOP_Z_MM - 0.01, PLATEAU_TOP_Z_MM)
    body = softened(body, 0.05, body.edges().group_by(Axis.Z)[-1])
    body = with_color(body, BODY_COLOR)

    actuator_height = TOTAL_HEIGHT_MM - PLATEAU_TOP_Z_MM
    actuator = Pos(0, 0, PLATEAU_TOP_Z_MM + actuator_height / 2.0) * Cylinder(
        ACTUATOR_DIAMETER_MM / 2.0,
        actuator_height,
    )
    actuator = softened(actuator, 0.08, actuator.edges().group_by(Axis.Z)[-1])
    actuator = with_color(actuator, ACTUATOR_COLOR)

    parts = [body, actuator]
    for side in (-1, 1):
        for y in (-LEAD_PITCH_Y_MM / 2.0, LEAD_PITCH_Y_MM / 2.0):
            parts.append(make_lead(side, y))

    return Compound(children=parts)


def main() -> None:
    SHAPES_DIR.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), STEP_PATH)
    print(f"Wrote {STEP_PATH}")


if __name__ == "__main__":
    main()
