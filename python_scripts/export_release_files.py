"""Collect the files for a GitHub release of the main board into release/REV<rev>/:

    CellKeeper_REV<rev>_gerbers.zip               from the fab toolkit's production output
    CellKeeper_REV<rev>_bom.csv                   JLCPCB BOM
    CellKeeper_REV<rev>_positions.csv             JLCPCB CPL
    CellKeeper_REV<rev>_schematic.pdf             schematic
    CellKeeper_REV<rev>_board.pdf                 board print, 1:1: top, and bottom seen from below
    CellKeeper_REV<rev>_enclosure_print_files.zip enclosure/output print files, if they exist

    python python_scripts/export_release_files.py

The revision comes from the board's title block. Run the fab toolkit first; its files are read
from the top of production/ (git-ignored), or from production/CellKeeper_REV<rev>/ if moved there.
The board PDF uses its own colour theme through a temporary KiCad config, so KiCad's settings
are not touched. Set KICAD_CLI if kicad-cli is not at the KiCad 10 path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pymupdf

PROJECT = Path(__file__).resolve().parents[1]
BOARD_DIR = PROJECT / "CellKeeper"
BOARD = BOARD_DIR / "CellKeeper.kicad_pcb"
SCHEMATIC = BOARD_DIR / "CellKeeper.kicad_sch"
ENCLOSURE_OUT = PROJECT / "enclosure" / "output"
KICAD_CLI = Path(os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"))

# Paper-friendly plot colours: pale copper under near-black silkscreen.
PRINT_THEME = {
    "meta": {"name": "CellKeeperPrint", "version": 5},
    "board": {
        "copper": {"f": "rgb(236, 160, 150)", "b": "rgb(150, 185, 230)"},
        "f_silks": "rgb(25, 25, 25)",
        "b_silks": "rgb(25, 25, 25)",
        "edge_cuts": "rgb(0, 0, 0)",
        "worksheet": "rgb(120, 120, 120)",
        "background": "rgb(255, 255, 255)",
    },
}
SIDES = [
    # page label, layers, extra kicad-cli arguments
    ("Top", "F.Cu,F.SilkS,Edge.Cuts", []),
    ("Bottom, seen from below", "B.Cu,B.SilkS,Edge.Cuts", ["--mirror"]),
]
ENCLOSURE_FILES = ["print", "cellkeeper_case_assembly.step", "bracket_screw.step", "enclosure_bambu.3mf"]


def cli(*args: str, env: dict | None = None) -> None:
    subprocess.run([str(KICAD_CLI), *args], check=True, env=env, stdout=subprocess.DEVNULL)


def revision() -> str:
    m = re.search(r'\(title_block\s.*?\(rev "([^"]+)"\)', BOARD.read_text(encoding="utf-8"), re.S)
    return m.group(1)


def production_files(rev: str, out: Path) -> None:
    prod = BOARD_DIR / "production"
    name = f"CellKeeper_REV{rev}"
    src = prod / name if (prod / name / f"{name}.zip").exists() else prod
    for suffix, dest in ((".zip", "_gerbers.zip"), ("_bom.csv", "_bom.csv"), ("_positions.csv", "_positions.csv")):
        f = src / f"{name}{suffix}"
        if not f.exists():
            raise SystemExit(f"missing {f.relative_to(PROJECT)}: run the fab toolkit for rev {rev} first")
        shutil.copy2(f, out / f"{name}{dest}")


def board_pdf(out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        colors = Path(tmp) / "config" / "10.0" / "colors"
        colors.mkdir(parents=True)
        (colors / "CellKeeperPrint.json").write_text(json.dumps(PRINT_THEME), encoding="utf-8")
        env = {**os.environ, "KICAD_CONFIG_HOME": str(Path(tmp) / "config")}
        doc = pymupdf.open()
        for i, (label, layers, extra) in enumerate(SIDES):
            page_pdf = Path(tmp) / f"side{i}.pdf"
            cli("pcb", "export", "pdf", "--mode-single", "-l", layers, "--include-border-title",
                "--theme", "CellKeeperPrint", "--drill-shape-opt", "1", *extra,
                "-o", str(page_pdf), str(BOARD), env=env)
            with pymupdf.open(page_pdf) as side:
                doc.insert_pdf(side)
            doc[-1].insert_text((40, 50), label, fontsize=16, fontname="helv")
        doc.save(out)


def enclosure_zip(out: Path) -> bool:
    files = []
    for name in ENCLOSURE_FILES:
        p = ENCLOSURE_OUT / name
        files += sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p] if p.exists() else []
    if not any("print" in f.relative_to(ENCLOSURE_OUT).parts for f in files):
        return False
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            z.write(f, Path("enclosure") / f.relative_to(ENCLOSURE_OUT))
    return True


def main() -> None:
    rev = revision()
    out = PROJECT / "release" / f"REV{rev}"
    out.mkdir(parents=True, exist_ok=True)
    name = f"CellKeeper_REV{rev}"
    production_files(rev, out)
    cli("sch", "export", "pdf", "-o", str(out / f"{name}_schematic.pdf"), str(SCHEMATIC))
    board_pdf(out / f"{name}_board.pdf")
    if not enclosure_zip(out / f"{name}_enclosure_print_files.zip"):
        print("no enclosure/output/print: run enclosure/cellkeeper_case.py to include the print files")
    for f in sorted(out.iterdir()):
        print(f"{f.relative_to(PROJECT)}  {f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
