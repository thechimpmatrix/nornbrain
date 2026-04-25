# Brain in a Vat: Strings Catalogue

875 referenced strings extracted from `Vat_1.9.exe`. This document curates them by purpose. Raw list at `analysis/braininavat/notes/strings.txt`.

This catalogue surfaces three load-bearing findings about how the Vat actually talks to the engine. They are summarised at the top, then the categorised strings follow.

## Top finding: the "IPC protocol" is CAOS

The Win32 shared-memory IPC transport carries **CAOS command text**, not a custom binary protocol. The Vat sends `execute\n<CAOS-script>` strings via shared memory; the engine evaluates them and writes the textual/binary response back through the same channel. Every CAOS command the Vat uses is already implemented in openc2e and documented in [`docs/reference/caos-dictionary.md`](../caos-dictionary.md).

This dramatically simplifies what we need to do to host the Vat (or replace it with our own viewer): there is no proprietary opcode set to map. There is just a Win32 transport, and a known set of CAOS commands.

### CAOS scripts embedded as static strings

These are the actual command templates the Vat injects. `%d` and `%f` are filled in with agent IDs, indices, and float values at runtime.

| Address | CAOS template | Purpose |
|---|---|---|
| `0047a520` | `execute\nOUTS WNAM` | Get the world name |
| `0047a564` | `execute\nTARG AGNT %d OUTS GTOS 0` | Get an agent's name |
| `0047a5a4` | `execute\nTARG AGNT %d OUTV CAGE` | Get an agent's age |
| `0047a5f0` | `execute\nTARG AGNT %d BRN: DMPB` | **Dump brain sizes** (which lobes/tracts exist, how big each is) |
| `0047a6e0` | `execute\nTARG AGNT %d BRN: DMPL %d` | **Dump lobe** as binary |
| `0047a724` | `execute\nTARG AGNT %d BRN: DMPT %d` | **Dump tract** as binary |
| `0047a8b8` | `execute\nTARG AGNT %d BRN: DMPL %d` | (Duplicate - likely two callsites) |
| `0047a8dc` | `execute\nTARG AGNT %d BRN: DMPT %d` | (Duplicate) |
| `0047a900` | `execute\nTARG AGNT %d BRN: DMPN %d %d` | **Dump neuron** in lobe |
| `0047a928` | `execute\nTARG AGNT %d BRN: DMPD %d %d` | **Dump dendrite** in tract |
| `0047b310` | `execute\nTARG AGNT %d BRN: SETL %d %d %f` | **Set lobe SVRule float** at line N |
| `0047b35c` | `execute\nTARG AGNT %d BRN: SETT %d %d %f` | **Set tract SVRule float** at line N |
| `0047b490` | `execute\nTARG AGNT %d BRN: SETN %d %d %d %f` | **Set neuron weight** (state index) |
| `0047b4f8` | `execute\nTARG AGNT %d BRN: SETD %d %d %d %f` | **Set dendrite weight** |
| `0047a80c` | `execute\nDBG: TOCK` | **Debug single-tick** the engine (so the brain advances one step while paused) |
| `0047af18` | `execute\nDBG: PLAY` | **Debug resume** (game runs) |
| `0047b068` | `execute\nDBG: PAWS` | **Debug pause** (game pauses - the readme's "the game should now pause") |
| `0047b0e0` | `execute\nENUM 0 0 0 DOIF TYPE TARG = 7 OUTS HIST NAME GTOS 0 OUTS "\\n" OUTV UNID OUTS "\\n" ENDI NEXT` | **Enumerate creatures** (TYPE=7 is creature; outputs name + UNID for each) |
| `0047d0bc` | `execute\n` | Empty CAOS prefix - used as a noop |

### How the Vat connects, in plain language

1. Read `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine` to find the active game name (e.g. `Docking Station`, `Creatures 3`).
2. Open the named kernel objects: `<game>_mutex`, `<game>_request`, `<game>_result`, `<game>_mem`.
3. Validate magic `c2e@` at offset 0 of the shared memory.
4. Issue `DBG: PAWS` to pause the game, then `ENUM ... TYPE TARG = 7 ...` to list creatures.
5. User picks a creature → store its agent ID (UNID).
6. Issue `BRN: DMPB` to discover the brain's lobe and tract counts.
7. Loop: for each lobe, `BRN: DMPL`. For each tract, `BRN: DMPT`. For each neuron and dendrite of interest, `BRN: DMPN` / `BRN: DMPD`.
8. On user mutation: `BRN: SETL/SETT/SETN/SETD` with new values.
9. To advance: `DBG: TOCK` (single-step) or `DBG: PLAY` (resume).

### Implication for our viewer

We do not need the Vat's IPC layer at all. openc2e already speaks CAOS over TCP port 20001, and every BRN: and DBG: command above is implemented. A native Python viewer can issue these commands directly, parse the binary dumps from `BRN: DMPL/DMPT/DMPN/DMPD`, and render the same data the Vat does. The Vat .exe itself can be retired from the workflow once this viewer exists.

The remaining unknown is the **binary format of the BRN: DMP* responses** - the layout of a dumped lobe, tract, neuron, dendrite. This is documented in CAOS but not at the byte level. Reading the openc2e implementation of `BRN: DMPL` etc. (in the C++ source under `openc2e/src/openc2e/`) will give us the canonical layout, since we own that code.

## Engine identity and version

| Address | String | Note |
|---|---|---|
| `0046e6e0` | `Software\CyberLife Technology\Creatures Engine` | Registry key (HKCU) |
| `0046e710` | `Default Game` | Registry value name under that key |
| `0046e720` | `Software\CyberLife Technology\` | Registry parent path |
| `0047aef0` | `CyberLife Vat Kit for Creatures 3 v1.8` | Banner - version 1.8 (binary itself is `Vat_1.9.exe`, suggesting a minor unreleased revision) |
| `0047d180` | `Default game name not found.  Check you have a correct registry entry for\nHKEY_CURRENT_USER\\` | Connect-failure message |
| `0047d260` | `Expected registry key not found.  Check you have a correct registry entry for\nHKEY_LOCAL_MACHINE\\` | Falls back to HKLM if HKCU lookup fails |

## IPC handshake strings

| Address | String |
|---|---|
| `0047d048` | `Internal IPC mutex error` |
| `0047d064` | `%s_mutex` |
| `0047d070` | `%s_request` |
| `0047d07c` | `%s_result` |
| `0047d088` | `%s_mem` |
| `0047d0a0` | `Initial connection failed` |

## Brain data model labels

These format strings reveal the entity addressing scheme used in the GUI and likely in the BRN: DMP* binary responses:

| Address | String | Indexing pattern |
|---|---|---|
| `0047a878` | `Dendrite: (%d) from %s to %s in Tract: %s->%s` | `(slot) src→dest` in named tract |
| `0047a8a8` | `Tract: %s->%s` | Tract by source-lobe → dest-lobe pair |
| `0047b338` | `(T:%s) Tract: %s` | Tract with type prefix |
| `0047b34c` | `Tract: %s->%s` | Same as above |
| `0047b52c` | `(D:(%d)%d->%d, %s) Dendrite: (%d) from %s to %s in Tract: %s` | Full dendrite descriptor: `(slot)(src_idx→dst_idx, type)` |
| `0047b5a8` | `Tract: %s ` | |
| `0047b690` | `(D:(%d)%d->%d, %s) Dendrite: (%d) from %s to %s in Tract: %s` | Duplicate |
| `0047ae34` | `Brain Lobe Quads` | Static layout coordinate table (x, y, w, h per lobe) |
| `0047ae48` | `Brain Lobe Quads` | (Duplicate ref) |
| `0047ae5c` | `Brain Lobes` | List of lobe definitions |
| `0047ae68` | `Brain Lobe Neuron Names` | Per-lobe neuron labels |
| `0047b720` | `Brain` | Class identifier (probably for serialisation tag) |
| `0047b75c` | `Brain Parameters` | Brain-level parameters table |
| `0047c684` | `Action Script To Neuron Mappings` | Action-to-neuron lookup table |

## SVRule type identifiers (engine internals)

| Address | String |
|---|---|
| `0047a438` | `.?AVSVRuleDlg@@` (SVRuleDlg RTTI) |
| `0047bd50` | `SVRule` (class identifier) |
| `0047bd60` | `Type mismatch during serialisation of SVRule` |
| `0047bdb0` | `.?AVSVRule@@` |
| `0047bee8` | `.?AVReinforcementDetails@Tract@@` |

The presence of `Type mismatch during serialisation of SVRule` confirms SVRule programs are CreaturesArchive-serialisable as polymorphic objects.

## Variables and graphs

| Address | String |
|---|---|
| | `Variables Neuron:%d, %s` |
| | `Variables Dendrite:%d, %s` |
| | `Graph Neuron:%d, %s` |
| | `Graph Dendrite:%d, %s` |
| | `Graph Lobe:%s` |
| | `Inputs for lobe: ` |

## CreaturesArchive format markers

| Address | String |
|---|---|
| `0046e748` | `deflate 1.1.3 Copyright 1995-1998 Jean-loup Gailly ` |
| `0046f274` | `inflate 1.1.3 Copyright 1995-1998 Mark Adler ` |
| `0047c904` | `Creatures Evolution Engine - Archived information file. zLib 1.13 compressed.` |
| `0047c980` | `CRA0002: Not a creatures archive` |
| `0047c9d8` | (duplicate banner) |
| `0047cba4` | `CreaturesArchive::WriteFloatRef` |
| `0047cc04` | `CreaturesArchive::ReadFloatRef` |
| `0047ccd0` | `creatures_engine_logfile.txt` |

(Full CRA error code list and Catalogue error codes are in [06-file-formats.md](06-file-formats.md).)

## Error message families

### Connection / online-mode failures

`Could not load genome` · `Could not create brain` · `Could not initialize brain` · `Could not create brain support` · `Could not get Worlds Directory` · `Could not find norn` · `Could not load genome` · `Could not fetch brain` · `Could not download brain` · `Could not download brain lobe` · `Could not download brain tract` · `Could not download brain.\nDisconnected.` · `Could not suspend game.` · `Failed to connect to game.` · `Connecting to creatures` · `Could not find any creatures or perhaps some other problem.` · `Connected to Creatures` · `Tract to big for transfer\nRequire transfer buffer of:` · `Lobe to big for transfer` · `Brain Initialization Error` · `Brain Update Error`

The "Tract to big for transfer" / "Lobe to big for transfer" strings imply the shared memory has a fixed buffer size; oversized lobes/tracts can't be retrieved in one round-trip. Worth bearing in mind if a Norn brain has a large lobe.

### Internal CRT / runtime errors (ignore)

`Unknown exception` · `Access violation - no RTTI data!` · `Bad read pointer - no RTTI data!` · `Attempted a typeid of NULL pointer!` · `Bad dynamic_cast!` · `Runtime Error!` · `R6018 - unexpected heap error` · `R6017 - unexpected multithread lock error` · `bad allocation` · `string too long` · `invalid string position` · `bad locale name`. Standard MSVC CRT error strings.

## Mangled type names (108 entries - ignore for analysis)

108 strings begin with `.?AV...` - these are MSVC-mangled C++ type names embedded for RTTI. Not needed for analysis; the corresponding demangled names are in [09-class-registry.md](09-class-registry.md).

## CRA / CLE error codes (file format errors)

Full list catalogued in [06-file-formats.md](06-file-formats.md). Notable ones referenced from strings.txt:

- `CRA0002: Not a creatures archive`
- `CLE0010: Number of strings doesn't match array count`
- `CLE0011: Number of strings doesn't match array count`
- `CLE0013: Internal catalogue error, unexpected -1`
- `CLE0019: Two tags with the same name "%s" but different contents at item %d`

## What we did NOT find in strings

- **No TCP/network strings.** Confirms zero networking surface.
- **No Steam / Galaxy / GOG identifiers.** The Vat targets the original CD release.
- **No `.cob` references.** The Vat doesn't load Creature Object packs.
- **No agent script (CAOS file) loading.** The CAOS strings are all template-based, hardcoded; there's no path that reads CAOS from a file.
- **No `BBD:` (brain-build) commands.** The Vat reads and writes existing brains; it does not construct them. Brain construction is the engine's job at creature birth.
