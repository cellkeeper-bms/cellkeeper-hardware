from __future__ import annotations

import sys
from pathlib import Path

from build123d import Axis, Box, Color, Compound, Cylinder, Pos, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "HM2113ZNLT.step"

# Pulse HM2113ZNL(T) isoSPI transformer, 6-pin gull-wing SMD, 3.45 mm max seated height.
# Model coordinates match the KiCad footprint BMS_Library__HM2113ZNLT, whose origin is
# not the body centre: pads 1-3 sit at x = -5.62, pads 4-6 at x = +8.62, pitch 2.54 in Y.
# Body outline follows the footprint's F.Fab layer; lead shape is approximated.
BODY_CENTER_X_MM = 1.5
BODY_LENGTH_X_MM = 12.15
BODY_WIDTH_Y_MM = 8.3
HEIGHT_MM = 3.45
STANDOFF_MM = 0.15
TOP_EDGE_FILLET_MM = 0.4

PAD_ROW_X_MM = (-5.62, 8.62)
PIN_PITCH_MM = 2.54
LEAD_WIDTH_MM = 0.6
LEAD_THICKNESS_MM = 0.25
LEAD_EXIT_Z_MM = 1.1
LEAD_FOOT_LENGTH_MM = 1.1
LEAD_TIP_PAST_PAD_MM = 0.55
LEAD_EMBED_MM = 0.4

PIN1_DOT_RADIUS_MM = 0.45
PIN1_DOT_INSET_MM = 1.2

BODY_COLOR = (0.10, 0.10, 0.10)
LEAD_COLOR = (0.80, 0.80, 0.78)


def with_color(part, color: tuple[float, float, float]):
    part.color = Color(*color)
    return part


def box_from_extents(x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float):
    return Pos(
        (x_min + x_max) / 2.0,
        (y_min + y_max) / 2.0,
        (z_min + z_max) / 2.0,
    ) * Box(x_max - x_min, y_max - y_min, z_max - z_min)


def make_lead(side: int, y: float):
    """Gull-wing lead; side = -1 for the pin 1-3 row, +1 for the pin 4-6 row."""
    t = LEAD_THICKNESS_MM
    body_edge = BODY_CENTER_X_MM + side * BODY_LENGTH_X_MM / 2.0
    tip = PAD_ROW_X_MM[0 if side < 0 else 1] + side * LEAD_TIP_PAST_PAD_MM
    knee = tip - side * LEAD_FOOT_LENGTH_MM
    y0, y1 = y - LEAD_WIDTH_MM / 2.0, y + LEAD_WIDTH_MM / 2.0

    def span(a: float, b: float) -> tuple[float, float]:
        return min(a, b), max(a, b)

    lead = box_from_extents(*span(body_edge - side * LEAD_EMBED_MM, knee + side * t), y0, y1,
                            LEAD_EXIT_Z_MM, LEAD_EXIT_Z_MM + t)
    lead += box_from_extents(*span(knee, knee + side * t), y0, y1, 0.0, LEAD_EXIT_Z_MM + t)
    lead += box_from_extents(*span(knee, tip), y0, y1, 0.0, t)
    return lead


def make_model() -> Compound:
    hx, hy = BODY_LENGTH_X_MM / 2.0, BODY_WIDTH_Y_MM / 2.0
    cx = BODY_CENTER_X_MM
    body = box_from_extents(cx - hx, cx + hx, -hy, hy, STANDOFF_MM, HEIGHT_MM)
    body = fillet(body.edges().group_by(Axis.Z)[-1], TOP_EDGE_FILLET_MM)

    # Pin 1 is at footprint (-5.62, -2.54); KiCad's 3D Y axis is flipped, so the dot goes at +Y.
    dot = Pos(cx - hx + PIN1_DOT_INSET_MM, hy - PIN1_DOT_INSET_MM, HEIGHT_MM - 0.05) * Cylinder(PIN1_DOT_RADIUS_MM, 0.1)
    # The fillet/cut result is a Compound, which export_step leaves uncoloured; colour the Solid.
    body = (body - dot).solid()

    parts = [with_color(body, BODY_COLOR)]
    for side in (-1, 1):
        for y in (-PIN_PITCH_MM, 0.0, PIN_PITCH_MM):
            parts.append(with_color(make_lead(side, y), LEAD_COLOR))

    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
