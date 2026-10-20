# Plan: split the isoSPI hat and the precharge board into their own projects

**Status: done 2026-10-14.** Separate projects as recommended:
- **Main board:** keeps its reference designators.
- **Small boards:** re-annotated from 1, with their auto-generated net names following.
- **Mouse bites:** footprints and symbols H5–H13 removed.
- **Board edges:** every edge interrupted by breakaway tabs is now a single line between the
  same end points.
- **Precharge schematic:** got the whole HV system diagram the PTCs were drawn in.

## Where things are now

`CellKeeper.kicad_pcb` is one panel with three boards. They are cut apart by routed slots with
breakaway tabs: five tabs down the main board's right edge at x 308.8 / 310.8, and three between
the two small boards at y 115.6 / 117.6.

| Board | Outline (mm) | Parts |
|---|---|---|
| Main controller | x 48.8–308.8, y 42.4–155.4 (260 × 113) | everything else |
| Precharge | x 310.8–354.8, y 43.5–115.6 (44 × 72) | TH1–TH6 (B59451C1130B070 PTCs: three parallel strings of two in series), H14 / H15 lug pads |
| isoSPI hat | x 310.8–354.8, y 117.6–155.4 (44 × 38) | A1 (Pico), U23 SP3485, U24 AM26LV32, TR2 HM2113, J23 OEM connector, J24 screw terminal, C105–C114, R148–R150, TP45–TP48 |

- **No net is shared between the three boards.** The hat runs on its own `+3.3V2` / `GND2` /
  `IsoSPI2…` nets, and the precharge board has only `Drive Unit Neg`, `/FC Neg` and the three
  string midpoints. Each board connects to the others through wires and lugs, not copper. That
  makes the split clean: no interface nets have to be broken.
- **The schematic is one flat sheet** with all three boards on it.

## Can one schematic drive several PCBs?

**No.** A KiCad project is one root schematic, which can be hierarchical, plus **one** board file.
That includes the 10.0 installed here. The only way to get several boards out of one schematic is
what this project does now: several outlines in one `.kicad_pcb`, i.e. a panel. That is fine for
ordering everything together, but it ties all three boards to one revision, one BOM and one fab
order.

**Hierarchical sheets** (one `.kicad_sch` file per board, under one root) tidy up the schematic,
but there is still one PCB. They help only if you keep the panel.

**Recommendation: three separate KiCad projects in this one repo,** sharing the library folders:

```
CellKeeper-BMS-PCB/
  lib/                     CellKeeper_Local.kicad_sym, CellKeeper_Local.pretty, CellKeeper.3dshapes
  CellKeeper/              main controller (CellKeeper.kicad_pro/.kicad_sch/.kicad_pcb, production/)
  isoSPI-Hat/              isoSPI-Hat.kicad_pro/.kicad_sch/.kicad_pcb, production/
  Precharge/               Precharge.kicad_pro/.kicad_sch/.kicad_pcb, production/
  graphics/, python_scripts/, README.md
```

What this gives:
- **Independent revisions and orders.** The hat and the precharge board change rarely; the main
  board is on its third 1.1 spin.
- **Separate BOM / CPL / Gerbers** per board. JLC also charges a multi-design fee for a customer
  panel containing different designs.
- **Different fab options per board,** e.g. thicker copper for the precharge board.
- **To order everything together again,** panelise the three finished boards with KiKit at order
  time, without merging the sources.

## Steps

The "save a copy, then delete what isn't yours" method keeps the reference designators, symbol to
footprint links and the existing layout of each small board: placement, tracks and zones.

1. **Prepare**
   - Commit, and close KiCad. The `.lck` files must be gone.
   - Make a branch: `git switch -c split-subboards`.
2. **Shared libraries**
   - `git mv` `CellKeeper_Local.kicad_sym`, `CellKeeper_Local.pretty` and `CellKeeper.3dshapes`
     into `lib/`.
   - Point every project's `sym-lib-table` / `fp-lib-table` at `${KIPRJMOD}/../lib/…`.
   - Change the 403 `${KIPRJMOD}/CellKeeper.3dshapes/` model paths to
     `${KIPRJMOD}/../lib/CellKeeper.3dshapes/`. Use a text replace in the `.kicad_pcb`, or set a
     `CELLKEEPER_LIB` path variable.
   - Fix the two broken `../common-mode-filters.3dshapes/` model paths while there.
3. **Main board**
   - `git mv` the project files into `CellKeeper/`.
   - **Schematic:** delete the hat and precharge parts (lists above).
   - **PCB:** delete those footprints with *Update PCB from Schematic* and *Delete extra
     footprints* on.
   - Delete the two small outlines and the tab slots, and make the right-hand edge at x 308.8 one
     continuous line.
   - Run DRC and ERC; there should be no new unconnected items.
4. **isoSPI hat**
   - From the original project, use *File → Save As* (project) to `isoSPI-Hat/isoSPI-Hat`.
   - In that copy, delete everything except the hat (schematic, then *Update PCB* with *Delete
     extra footprints*). Delete the other two outlines.
   - Optional:
     - rename `+3.3V2` / `GND2` / `IsoSPI2…` to plain `+3.3V` / `GND` / `IsoSPI…`;
     - re-annotate from 1;
     - move the board near the origin and set the drill/place origin.
   - Set the title block (title "CellKeeper isoSPI Hat", its own rev, e.g. 1.0).
5. **Precharge board:** same as step 4, into `Precharge/Precharge`.
   - Check the copper weight and clearances for pack voltage across the PTC strings. This
     becomes its own fab setting.
   - Title "CellKeeper Precharge".
6. **Fab outputs**
   - Give each project its own `fabrication-toolkit-options.json`, with an `ARCHIVE_NAME` per board.
   - Move `production/CellKeeper_REV1*` under `CellKeeper/production/`.
7. **Check each project on its own**
   - Opens with no missing symbols, footprints or 3D models.
   - ERC and DRC are clean.
   - The Gerber export shows exactly one outline.
8. **Docs:** in the README, list the three boards, how they connect (the hat's J23 / J24 to the
   BMBs; the precharge board's lugs into the contactor wiring) and the KiKit command for ordering a
   combined panel.
9. **Commit and merge:** one commit for the library move, one per project split.

## Decisions to make

- **Keep the panel?** If the boards will always be ordered together, an alternative is to keep
  one project, put each board on its own hierarchical sheet (`main.kicad_sch`, `isospi_hat.kicad_sch`,
  `precharge.kicad_sch` under one root) and keep the breakaway panel. That is less work, but the
  three boards stay on one revision, BOM and fab order.
- **Refdes and nets on the small boards:** keep them (easy cross-reference with old builds), or
  re-annotate from 1 and rename the `…2` nets (cleaner standalone boards)?
- **Does the hat still need a Pico footprint (A1),** or will it become a hat for the main board?
  That decides which connector it gets in its own revision.
