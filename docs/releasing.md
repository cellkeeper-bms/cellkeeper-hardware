# Releasing a board revision

`main` holds the last revision that was ordered. Work on the next one happens on a branch named
after it (`rev1.2`, ...). When a revision is ordered:

1. In KiCad, run the fab toolkit (archive name `CellKeeper REV<rev>`), close KiCad, and commit.
2. Collect the release files into `release/REV<rev>/` (git-ignored):

   ```
   python enclosure/cellkeeper_case.py          # only if enclosure/output/print is missing or stale
   python python_scripts/export_release_files.py
   ```

   | File | Contents |
   |------|----------|
   | `CellKeeper_REV<rev>_gerbers.zip` | Gerbers and drill files, as sent to the fab |
   | `CellKeeper_REV<rev>_bom.csv` | JLCPCB BOM (DNP parts left out) |
   | `CellKeeper_REV<rev>_positions.csv` | JLCPCB pick-and-place (CPL) |
   | `CellKeeper_REV<rev>_schematic.pdf` | schematic |
   | `CellKeeper_REV<rev>_board.pdf` | board print at 1:1 on the 400 x 250 mm sheet (fits A3 at 100 %): top, then bottom seen from below; copper pale, silkscreen dark |
   | `CellKeeper_REV<rev>_enclosure_print_files.zip` | print-oriented STEP/STL case files, bracket screw, assembly STEP, Bambu project |

   The schematic and board stay separate PDFs: the schematic is for reading on screen, the board
   print is for printing at 1:1 to check parts and fit against the real board.
3. Merge the revision branch into `main`, tag it (`git tag -a rev<rev>`), push both, and create the
   release from the tag with every file in `release/REV<rev>/`:

   ```
   gh release create rev<rev> --verify-tag --latest --title "Revision <rev>" --notes-file notes.md release/REV<rev>/*
   ```
4. Move the revision's production files into `CellKeeper/production/CellKeeper_REV<rev>/` and
   start the next branch, bumping the title blocks, the silkscreen REV text and the fab toolkit's
   archive name.
