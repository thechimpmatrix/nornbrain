# Brain in a Vat: Reference

Reverse-engineering catalogue for the 1999 Creature Labs / CyberLife "Brain in a Vat" tool (`Vat_1.9.exe`, version banner reads "v1.8"). Documents derived from a complete Ghidra headless analysis of the binary.

The original tool is closed-source abandonware. Creature Labs / CyberLife are defunct. The binary is freely circulated by the Creatures community. This catalogue records what the binary actually does, with citations to function addresses and string addresses, so we can either host the original tool against our NORNBRAIN engine or build a clean reimplementation.

## Why we care

The Vat tool is a complete genetic-engineer's brain inspector for Creatures 3. It supports both online mode (live introspection of a running creature) and offline mode (load a genome and run the brain in isolation). For NORNBRAIN we want either:

1. **The original tool, working against our engine** - point the Vat at openc2e, get free professional UI for SVRule brain inspection.
2. **A fresh viewer, informed by the Vat's data model and visual conventions** - better long-term, integrated with our web monitor.

This catalogue supports both paths.

## Headline findings

Two findings dominate the catalogue and shape what we should do next.

### 1. The "IPC protocol" is just CAOS over a shared-memory transport

The Vat does not define a custom binary protocol. **The shared-memory IPC carries ASCII CAOS command strings.** Every command the Vat sends - `BRN: DMPB`, `BRN: DMPL`, `BRN: DMPT`, `BRN: DMPN`, `BRN: DMPD`, `BRN: SETL/SETT/SETN/SETD`, `DBG: PAWS/PLAY/TOCK`, `ENUM`, `OUTV CAGE`, `OUTS GTOS`, `OUTS WNAM` - is documented in [`docs/reference/caos-dictionary.md`](../caos-dictionary.md). The shared-memory header has a small fixed layout (`c2e@` magic + server PID + status + payload-len + capacity) and binary-dump responses end with the sentinel `END DUMP V1.1`.

**Important caveat:** despite the CAOS dictionary listing the BRN: commands as relevant, **openc2e does NOT implement any of them** (verified across `caosVM_*.cpp` and the 810-command `commandinfo.json`). To make the Vat work against our engine - or to build a Vat-equivalent viewer that drives the same brain dynamics - we have to implement BRN: commands ourselves. The byte-level wire format is fully documented in [12-brn-dmp-wire-format.md](12-brn-dmp-wire-format.md), reconstructed from the original Creature Labs C3 source code at `<PROJECT_ROOT>\C3sourcecode\engine\`.

See [03-ipc-protocol.md](03-ipc-protocol.md) for the transport, [12-brn-dmp-wire-format.md](12-brn-dmp-wire-format.md) for the wire format.

### 2. The SVRule rules engine is in this binary

`SVRule` and `SVRuleDlg` are statically linked. The interpreter at `FUN_00421830` (a 2604-byte function with a three-arm opcode dispatch driven by a class table at `0x0047bbfc`) is the actual SVRule evaluation engine. Programs are 16 lines × 16 bytes in memory (4 floats per line); on disk each line is 3 bytes plus a precomputed fourth float (`byte / 248.0`). Every `BrainComponent` carries two SVRule programs at offsets `+0x10` and `+0x128`. Tract dendrite reinforcement is `(rate - threshold) * gain` per channel.

The binary contains no opcode mnemonic strings - those live in the engine's `.catalogue` files at runtime. So while we have the bytecode interpreter and the layout, the human-readable opcode names need to come from the C3 install, not the .exe.

See [10-svrule-engine.md](10-svrule-engine.md). This is the highest-value lift available from the binary, and it gives us a faithful reference for the brain dynamics NORNBRAIN's own SVRule layer should reproduce.

### Knock-on finding: brain reference data lives in the C3 install, not the .exe

`Brain Lobe Quads`, `Brain Lobes`, `Brain Lobe Neuron Names`, `Brain Parameters`, and the action-script-to-neuron mappings are **not** static data in the binary. They are loaded at runtime via the global `Catalogue` system (data ref `0x00481048`) from `.catalogue` text files in the C3 install (`creaturesexodusgame/Creatures Exodus/Creatures 3/Catalogue/*.catalogue`).

Important correction from the catalogue read: **`Brain Lobe Quads` is *not* (x,y,w,h) coordinates** as initially assumed - it's an array of 12 four-character lobe TYPE TAGS (`attn`, `decn`, `verb`, `noun`, `visn`, `smel`, `driv`, `sitn`, `detl`, `resp`, `prox`, `stim`). "Quad" refers to the 4-character tag width, not a quadrilateral. The actual visual coordinates for lobe rendering live in `BrainViewport`'s paint code, hardcoded - not in any catalogue file. They can be recovered by reading `FUN_00406900` in the decompilation.

See [11-catalogue-data.md](11-catalogue-data.md) for the full catalogue extract.

## Documents in this catalogue

| # | Doc | Purpose |
|---|---|---|
| 00 | [Architecture summary](00-architecture.md) | High-level shape: GUI + statically-linked engine SDK + Win32 IPC |
| 01 | [Tweakability verdict](01-tweakability.md) | Three paths ranked by effort, recommendation, open questions |
| 03 | [IPC protocol](03-ipc-protocol.md) | Shared-memory layout, connection lifecycle, every CAOS command catalogued, sync pattern, error paths, Python responder checklist |
| 04 | [Data model](04-data-model.md) | Brain / Lobe / Tract / Neuron / Dendrite struct layouts, Brain Lobe Quads coordinates, action-script-to-neuron mappings, serialisation |
| 05 | [GUI inventory](05-gui-inventory.md) | Every dialog, viewport, menu command, paint cycle, what to lift vs reimplement |
| 06 | [File formats](06-file-formats.md) | CreaturesArchive container, Catalogue files, CRA/CLE error codes |
| 07 | [Strings catalogue](07-strings-catalogue.md) | 875 strings curated by purpose (CAOS templates, registry paths, brain labels, error messages) |
| 08 | [Imports catalogue](08-imports-catalogue.md) | All 186 Win32 imports across 6 DLLs, grouped by purpose (IPC, file I/O, drawing, registry) |
| 09 | [Class registry](09-class-registry.md) | All 114 RTTI-recovered C++ classes (engine SDK + GUI + STL) |
| 10 | [SVRule engine](10-svrule-engine.md) | SVRule interpreter, program format, opcode dispatch, reinforcement model, SVRuleDlg UI flow |
| 11 | [Catalogue data](11-catalogue-data.md) | C3 install's `.catalogue` files: lobe type tags, action mappings, brain parameters, drive→chemical bindings |
| 12 | [BRN: DMP wire format](12-brn-dmp-wire-format.md) | Byte-level layout for every BRN: DMP/SET command, reconstructed from Creature Labs C3 source |
| 13 | [Engine SDK classes](13-engine-sdk-classes.md) | Faculty, ChemicallyActive, Instinct, Genome, Agent, CAOSVar, PersistentObject, CreatureFacultyInterface internals |
| 14 | [PE resources](14-pe-resources.md) | Toolbar layout, menus, dialog templates, bitmaps, accelerators extracted from the .exe resource section |
| 15 | [RTTI inheritance](15-rtti-inheritance.md) | Full class inheritance DAG for all 102 classes with CHD records, including multiple-inheritance offsets |

Document 02 is reserved for a future cross-cutting "what we'd build next" plan when reimplementation work begins.

## Raw artefacts (working data, not part of the reference)

Under [`<PROJECT_ROOT>\analysis\braininavat\`](../../../analysis/braininavat/):

- `Vat_1.9.exe` - the binary itself (read-only)
- `Vat_Kit_readme.txt` - the original CyberLife readme
- `ghidra_project/` - saved Ghidra project (open with `tools/ghidra.bat`)
- `notes/` - Ghidra-export artefacts:
  - `decompiled/` (3,140 individual `.c` files, one per function)
  - `decompiled_all.c` (2.6 MB aggregate)
  - `functions.tsv` (3,141 functions: address, name, size, params)
  - `symbols.txt` (2,620 named symbols including imports)
  - `classes.txt` (1,381 namespaced symbols)
  - `strings.txt` (875 referenced strings)
- `scripts/` - Ghidra extraction scripts (`ExtractAll.java`)

## Binary identity

| Field | Value |
|---|---|
| Filename | `Vat_1.9.exe` |
| Banner | `CyberLife Vat Kit for Creatures 3 v1.8` |
| Format | PE32 i386 GUI, 6 sections |
| Size | 581,689 bytes |
| SHA-256 | `9c93b48c98c4d42fe11bc0359aba962b5b340534676d3ca5d2099abbd7856f18` |
| Compiler | MSVC ~6.0 era (Ghidra applied `windows_vs12_32` data type archive) |
| Linkage | Statically linked: MFC, zLib 1.13, Creatures Engine SDK |
| Imports | 186 functions across KERNEL32, USER32, GDI32, COMCTL32, COMDLG32, ADVAPI32 only |
| RTTI | Fully intact, 114 classes recoverable |
| Source | https://lisdude.com/cdn/brain_vat_kit.zip |

## Status

| Catalogue area | Status |
|---|---|
| Architecture | Done |
| Tweakability assessment | Done |
| IPC protocol (transport) | Done |
| BRN: DMP wire format (payload) | Done |
| Data model (in-memory layouts) | Done |
| GUI inventory (behaviour) | Done |
| PE resources (templates and assets) | Done |
| File formats (CreaturesArchive, Catalogue) | Done |
| C3 install catalogue data extraction | Done |
| Strings | Done |
| Imports | Done |
| Class registry | Done |
| RTTI inheritance hierarchy | Done |
| SVRule engine | Done |
| Engine SDK classes (Faculty/ChemicallyActive/Instinct/Genome/Agent/CAOSVar/PersistentObject/CFI) | Done |
| BrainViewport hardcoded lobe coordinates | Open - need a focused read of `FUN_00406900` to extract the actual rectangles |
| SVRule opcode mnemonics | Open - not in any `.catalogue`; require a focused read of the interpreter dispatch table at `0x0047bbfc` and behavioural naming from the interpreter at `FUN_00421830` |
| openc2e BRN: command implementation | **Open - NOT YET IMPLEMENTED IN OUR ENGINE.** Wire format is documented; the work is to add the C++ implementations |

## Recommended reading order

1. [00-architecture.md](00-architecture.md) - orient
2. [03-ipc-protocol.md](03-ipc-protocol.md) - the headline finding, fully resolved
3. [01-tweakability.md](01-tweakability.md) - what to do with this knowledge
4. The rest as needed.

## How this catalogue was produced

A single Ghidra 12.0.4 headless run analysed `Vat_1.9.exe` and exported decompilations + symbol metadata. A Java post-script (`ExtractAll.java`) walked every function, decompiled to C pseudocode, and dumped functions, symbols, classes, and strings as TSV/text. Synthesis docs were written by reading those artefacts. Every non-trivial claim cites a function address (e.g. `FUN_0043f8f0`) or a string address (e.g. `0x0047d048`).

To re-run the analysis: `<PROJECT_ROOT>\tools\ghidra.bat`, open the saved project, or `analyzeHeadless.bat` with `-postScript ExtractAll.java`.
