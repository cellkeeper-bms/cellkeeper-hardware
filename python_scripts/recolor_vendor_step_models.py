from __future__ import annotations

from pathlib import Path

from build123d import Color, Compound, export_step, import_step


PROJECT = Path(__file__).resolve().parents[1]
SHAPES_DIR = PROJECT / "lib" / "CellKeeper.3dshapes"

# Vendor STEP files that ship without colors, so KiCad draws them default grey.
# Each is a single housing solid; give it the real housing color.
MODELS = {
    # J20, Molex 34912-8020: black housing, same as the Hirose ZE05H on J14.
    "CONN_SD-34912-001_02_MOL.step": (0.10, 0.10, 0.10),
    # J17, TE 173864-1: natural (white) nylon housing.
    "CONN_173864-1_TYC_Empty_Pins.step": (0.94, 0.93, 0.88),
}


def recolor(path: Path, color: tuple[float, float, float]) -> None:
    shape = import_step(path)
    solids = []
    for solid in shape.solids():
        solid.color = Color(*color)
        solids.append(solid)
    export_step(Compound(children=solids), path)
    print(f"Recolored {path.name}: {len(solids)} solid(s)")


def main() -> None:
    for name, color in MODELS.items():
        recolor(SHAPES_DIR / name, color)


if __name__ == "__main__":
    main()
