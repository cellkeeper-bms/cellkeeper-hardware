from __future__ import annotations

import sys
from pathlib import Path

from build123d import Align, Axis, Box, Color, Compound, Cylinder, Pos, Torus, export_step, fillet


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"
STEP_PATH = SHAPES_DIR / "CP_Polymer_D10x15mm_P5mm_Jieerrui_PA.step"

# Jieerrui PA35V680M10x15 (LCSC C46550429): 680uF 35V polymer, D10 x L15 mm, 5 mm lead pitch.
# Bare matte aluminum can (no sleeve), pink-red ink polarity mark on the top over the
# negative side, black rubber seal inside the rolled bottom rim, crimp bead near the base.
# Model coordinates match the KiCad footprint CP_Radial_D10.0mm_P5.00mm: pin 1 (+) at the
# origin, pin 2 (-) at x = 5.
CENTER_X_MM = 2.5
CAN_DIAMETER_MM = 10.0
CAN_LENGTH_MM = 15.0
STANDOFF_MM = 0.4
TOP_EDGE_RADIUS_MM = 0.5
BOTTOM_CURL_RADIUS_MM = 0.6
BEAD_Z_MM = 1.7  # height of the sealing crimp above the can bottom
BEAD_RADIUS_MM = 0.28
SEAL_INSET_MM = 0.45
SEAL_RECESS_MM = 0.25

MARK_START_X_MM = 0.8  # the mark covers the top from this offset past center toward pin 2
MARK_THICKNESS_MM = 0.02

LEAD_PITCH_MM = 5.0
LEAD_DIAMETER_MM = 0.6
LEAD_BELOW_BOARD_MM = 3.0

CAN_COLOR = (0.80, 0.81, 0.83)
MARK_COLOR = (0.86, 0.24, 0.40)
SEAL_COLOR = (0.06, 0.06, 0.06)
LEAD_COLOR = (0.78, 0.78, 0.76)


def with_color(part, color: tuple[float, float, float]):
    # Booleans can return a compound wrapper; color the solid itself so the STEP keeps it.
    solids = part.solids()
    part = solids[0] if len(solids) == 1 else part
    part.color = Color(*color)
    return part


def make_model() -> Compound:
    """Create the capacitor aligned to the KiCad footprint (pin 1 at the origin)."""
    r = CAN_DIAMETER_MM / 2.0
    bottom = STANDOFF_MM
    top = STANDOFF_MM + CAN_LENGTH_MM

    can = Pos(CENTER_X_MM, 0, bottom) * Cylinder(r, CAN_LENGTH_MM, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        can = fillet(can.edges().group_by(Axis.Z)[-1], TOP_EDGE_RADIUS_MM)
        can = fillet(can.edges().group_by(Axis.Z)[0], BOTTOM_CURL_RADIUS_MM)
    except Exception:
        pass
    # Rubber seal pocket at the bottom of the can and the crimp bead around it.
    can -= Pos(CENTER_X_MM, 0, bottom - 0.01) * Cylinder(
        r - SEAL_INSET_MM, SEAL_RECESS_MM + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    can -= Pos(CENTER_X_MM, 0, bottom + BEAD_Z_MM) * Torus(r + BEAD_RADIUS_MM * 0.35, BEAD_RADIUS_MM)

    seal = Pos(CENTER_X_MM, 0, bottom + 0.02) * Cylinder(
        r - SEAL_INSET_MM - 0.02, SEAL_RECESS_MM, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    # Ink mark: the part of the top face on the negative (pin 2) side.
    mark_r = r - TOP_EDGE_RADIUS_MM
    mark = Pos(CENTER_X_MM, 0, top) * Cylinder(mark_r, MARK_THICKNESS_MM, align=(Align.CENTER, Align.CENTER, Align.MIN))
    mark &= Pos(CENTER_X_MM + MARK_START_X_MM + r, 0, top) * Box(2 * r, 2 * r, 1.0)

    parts = [with_color(can, CAN_COLOR), with_color(seal, SEAL_COLOR), with_color(mark, MARK_COLOR)]
    for x in (0.0, LEAD_PITCH_MM):
        lead = Pos(x, 0, -LEAD_BELOW_BOARD_MM) * Cylinder(
            LEAD_DIAMETER_MM / 2.0, LEAD_BELOW_BOARD_MM + bottom + 0.05, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        parts.append(with_color(lead, LEAD_COLOR))
    return Compound(children=parts)


def main() -> None:
    step_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP_PATH
    step_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(make_model(), step_path)
    print(f"Wrote {step_path}")


if __name__ == "__main__":
    main()
