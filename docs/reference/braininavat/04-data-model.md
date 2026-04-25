# Brain in a Vat: Data Model

Catalogue of the in-memory C++ types that the Vat tool uses to represent a Creatures 3 brain. Same types as the original Creature Labs Engine SDK, statically linked into `Vat_1.9.exe`. RTTI is intact, so class names are recoverable; field offsets are recovered from constructor and serialiser decompilation.

All addresses are virtual addresses inside the binary as analysed by Ghidra. Function names are Ghidra defaults of the form `FUN_<addr>`.

---

## Type hierarchy

Recovered RTTI Type Descriptors (from `notes/classes.txt` and `notes/symbols.txt`):

| Class | RTTI TD | Notes |
|---|---|---|
| `Brain` | `0x0047b850` | Top-level container; size `0x74` (116 bytes) per `operator_new(0x74)` in `FUN_0041aed0` |
| `BrainComponent` | `0x0047ba48` | Base class for `Lobe` and `Tract` (see below) |
| `Lobe` | `0x0047bbe8` | size `0x290` (656 bytes) per `operator_new(0x290)` in `FUN_0041bbf0` |
| `Tract` | `0x0047bec8` | size `0x2f0` (752 bytes) per `operator_new(0x2f0)` in `FUN_0041bf20` |
| `Tract::ReinforcementDetails` | `0x0047bee0` | Nested in Tract; size 20 bytes per slot, two slots per Tract |
| `SVRule` | `0x0047bda8` | Sub-object embedded in BrainComponent; vtable `PTR_LAB_0046e520` |
| `Faculty` | `0x0047b8a8` | Referenced but not in the runtime data path; serialiser exists |
| `Instinct` | `0x0047bb78` | Referenced but not in the runtime data path; serialiser exists |
| `Genome` | `0x0047c058` | Serialiser exists; loaded in offline mode |
| `BrainAccess` | `0x0047a3f8` | IPC client, **not** part of data model (see `00-architecture.md`) |

### Inheritance evidence

`BrainComponent` is the shared base for `Lobe` and `Tract`. Evidence:

- The single helper `FUN_00421310` (the `BrainComponent` constructor) is called as the first action in both the Lobe ctor (`FUN_00423840` line at start) and the Tract ctor (`FUN_00426290` line at start). It writes the same vtable layout (`PTR_LAB_0046e47c` then `PTR_LAB_0046e458`) and initialises the same SVRule pair at `+0x10` and `+0x128`, plus shared name/flag fields up to `+0x244`. That defines the full BrainComponent header.
- The Lobe and Tract loaders both push a single pointer into the Brain's polymorphic vector at `Brain+0x30/+0x38` (`FUN_0041e6e0((void *)(this+0x30), ...)` in `FUN_0041bbf0` line 56 and `FUN_0041bf20` line 47). That vector is the `BrainComponent*` collection.

Each of `Brain`, `Lobe`, `Tract`, `BrainComponent` and `SVRule` has a virtual destructor / vtable observable in the constructor pattern. The vtables I have observed are:

| Class | vtable address |
|---|---|
| Brain | `PTR_LAB_0046e3c0` (primary), `PTR_LAB_0046e3b8` (subobject at `+4`) |
| BrainComponent (early phase) | `PTR_LAB_0046e47c` |
| BrainComponent (late phase) | `PTR_LAB_0046e458` |
| Lobe | `PTR_LAB_0046e4fc` |
| Tract | `PTR_LAB_0046e538` |
| SVRule | `PTR_LAB_0046e520` |
| ReinforcementDetails | `PTR_FUN_0046e55c` |

The "early/late" pattern for BrainComponent's vtable is the standard MSVC two-phase construction artefact: base class writes its vtable, derived class writes over it.

---

## 1. Brain struct

Top-level container. Built at `FUN_0041aed0` with `operator_new(0x74)`, then constructed by `FUN_0041b270`.

```
+0x00  vtable                       -> PTR_LAB_0046e3c0
+0x04  vtable (subobject)           -> PTR_LAB_0046e3b8
+0x10  uint8                        version-tag flag (initialised from local_5d)
+0x18  uint32                       0
+0x1c  uint32                       0
+0x20  uint32                       0
+0x24  void*                        parent BrainAccess pointer
                                    set by FUN_0041c250(brain, parent_ptr).
+0x30  BrainComponent**             begin (polymorphic Lobe + Tract list, sorted)
+0x34  BrainComponent**             reserved/unused (resv ptr)
+0x38  BrainComponent**             end
+0x40  Lobe**                       begin (lobe-only sorted list)
+0x44  Lobe**                       resv
+0x48  Lobe**                       end
+0x50  Tract**                      begin (tract-only sorted list)
+0x54  Tract**                      resv
+0x58  Tract**                      end
+0x60  uint8                        flag
+0x64  void*                        begin of 12-byte/element aux vector (parallel to lobes)
+0x68  void*                        end of aux vector
+0x70  uint32                       0
```

The Brain owns three vectors:

- **`+0x30/+0x38`**: the polymorphic `BrainComponent*` list. Both `FUN_0041bbf0` (Lobe loader) and `FUN_0041bf20` (Tract loader) call `FUN_0041e6e0(this+0x30, *(this+0x38), 1, &component)` to insert. So this list contains lobes and tracts mixed.
- **`+0x40/+0x48`**: lobe-only sorted-by-name list, populated by `FUN_004020b0(this+0x40, ..., &lobe)` from the Lobe loader.
- **`+0x50/+0x58`**: tract-only sorted-by-name list, populated by `FUN_004022c0(this+0x50, ..., &tract)` from the Tract loader. After all tracts arrive, `FUN_0041c006` sorts by name.

There are also two parameters read from the `Brain Parameters` catalogue (offset `+0x28`, `+0x2c`, set by `FUN_0041b270` from catalogue indices 0 and 1). Their type is byte (one of these is the `is_v1.1` flag based on dump format detection).

### Brain is **not** serialisable as one blob

There is no top-level "serialise Brain" function in the data path. The Vat tool builds a Brain over the wire by issuing three CAOS commands in sequence (`FUN_00403200`):

1. `BRN: DMPB` - dump brain header. Result fed to `FUN_0041b270` (Brain ctor).
2. `BRN: DMPL <n>` - dump lobe `n`. Result fed to `FUN_0041bbf0` per lobe.
3. `BRN: DMPT <t>` - dump tract `t`. Result fed to `FUN_0041bf20` per tract.

Each per-lobe and per-tract response ends with a sentinel byte sequence:

- `END DUMP\0` - version 1.0 (sets `DAT_00480e9c = 0x3f800000` i.e. `1.0f`)
- `END DUMP V1.1\0` - version 1.1 (sets `DAT_00480e9c = 0x3f8ccccd` i.e. approx `1.1f`)

A mismatch raises a CreaturesArchive type-mismatch exception. Strings at `0x47a6ac` and `0x47a6b8`. The dump-format flag controls how SVRule rows are read (see §9).

Offline mode reads a `CreaturesArchive`-format genome from disk; the same per-component type-checking serialisers fire (see §9), but the entry point is different and not yet traced here.

---

## 2. BrainComponent (shared base)

Constructed by `FUN_00421310`. This runs as the **first** action of both `Lobe::Lobe(stream)` (`FUN_00423840`) and `Tract::Tract(stream, lobeList)` (`FUN_00426290`).

```
+0x00   vtable                   PTR_LAB_0046e47c -> PTR_LAB_0046e458 (two-phase)
+0x04   uint32                   0xFFFFFFFF (initialised; meaning unknown)
+0x08   uint32                   0
+0x09   uint8                    0 (initialised)
+0x10   SVRule                   primary SVRule (264 bytes nominal, fits in 0x118)
+0x128  SVRule                   secondary SVRule (264 bytes nominal, fits in 0x120)
+0x244  uint8                    0 (param_1+0x91 in int* terms)
+0x248  ?                        derived classes start using fields here
```

The two SVRule slots match the SVRule reference in `docs/reference/svrule-brain-complete-reference.md`: every BrainComponent has a "main" and "secondary" rule chain.

### SVRule sub-object

Constructed by `FUN_004249d0`. Confirmed fields:

```
+0x00   vtable               PTR_LAB_0046e520
+0x104  uint32               0 (initialised flag; purpose unknown)
```

The SVRule slot is loaded by `FUN_00424aa0`, which reads **16 rows × 16 bytes per row = 256 bytes** of rule data starting at `+0xc` of the slot. Each row is 4 fields: 3 opcodes (read either as variable-length tags or fixed 4-byte ints depending on dump version) plus one 4-byte float operand. 16 rules per chain matches the SVRule reference document's expectation.

---

## 3. Lobe struct

Constructor: `FUN_00423840`. Total size **`0x290`** (656 bytes). After the inherited `BrainComponent` header (`+0x00..+0x247`), Lobe-specific fields are:

```
+0x248  uint32                lobe id / param tag (read 4 bytes from stream)
+0x24c  char*                  display name pointer (set to *(int*)(this+0x264) + 4)
                               i.e. first neuron's name pointer + 4
+0x250  uint32                4-byte tag (used as a string key in catalogue lookups;
                               byte 0 of this becomes the first char of a lookup key)
+0x254  char[256]              lobe name (4-byte type tag from +0x250, copied as
                               null-terminated string; up to 256 bytes)
+0x25c  uint32                read 4 bytes from stream
+0x260  uint8                 1-byte param flag (initialised first thing in ctor)
+0x264  Neuron**              begin of neuron pointer vector
+0x268  Neuron**              end of neuron pointer vector
+0x26c  Neuron**              capacity (allocated end)
+0x270  uint32                4-byte param (purpose unknown)
+0x274  uint32                4-byte param (purpose unknown)
+0x278  uint32                grid width  (W)
+0x27c  uint32                grid height (H)
+0x280  uint32                4-byte param
+0x284  uint32                4-byte param
+0x288  uint32                4-byte param
+0x28c  uint32*               pointer to int[W*H] flag/state array
                               (allocated as operator_new(W*H*4))
```

**Constraint:** `W * H` must be `> 0` and `< 0xfe01` (65,025) or the Lobe ctor throws a CreaturesArchive exception. So a Lobe is fundamentally a 2-D grid of W×H neurons capped at ~64K cells.

### Neuron vector

The neuron list at `+0x264..+0x268` holds `W*H` `Neuron*`. Each neuron is constructed by `FUN_00424870` (which calls `FUN_00424880` - body not yet traced) with `operator_new(0x24)`. After construction, the loader reads 0x24 bytes of float data into the neuron starting at offset 4.

**Neuron struct (size 0x24 = 36 bytes):**

```
+0x00  vtable / first-field    set by FUN_00424880, read first from stream
+0x04..+0x23                   8 × 4-byte fields read in sequence from stream
                               (presumably the 8 neuron variables)
```

The 8 floats per neuron correspond to the SVRule-reference's Neuron Variables 0..7. Names like the V0, V1 etc. are not stored on the neuron itself - they come from the `Brain Lobe Neuron Names` catalogue (see §7).

### Two SVRule slots

The Lobe ctor reads its two SVRule slots in this order:

1. `+0x10` - primary SVRule, **only** in dump version 1.1 (when `DAT_00480e9c != 1.0f`)
2. `+0x128` - secondary SVRule, always

So in version 1.0 dumps, the primary SVRule slot is left at its zero default. This matches a known engine-side change between Creatures 3 launch and the late patches.

---

## 4. Tract struct

Constructor: `FUN_00426290`. Total size **`0x2f0`** (752 bytes). Inherits the BrainComponent header. Tract-specific layout:

```
+0x248  std::string-like      tract display name (built as src->dst, see below)
+0x258  uint32                ?
+0x25c  uint32                ?
+0x260  Dendrite**            begin of dendrite vector
+0x264  Dendrite**            end of dendrite vector
+0x268  Lobe*                 source lobe pointer (resolved from index)
+0x26c  uint32                source-side neuron range start
+0x270  uint32                source-side neuron range end
+0x274  uint8                 source-side flag (read via variable-length tag)
+0x278  ? (sub-struct)        source migration parameters block (FUN_00428600)
+0x28c  Lobe*                 destination lobe pointer (resolved from index)
+0x290  uint32                dest-side neuron range start
+0x294  uint32                dest-side neuron range end
+0x298  uint8                 dest-side flag (variable-length tag)
+0x29c  ? (sub-struct)        dest migration parameters block (FUN_00428600)
+0x2a0  void**                begin of secondary aux vector (also required non-empty)
+0x2a4  void**                end
+0x2b0  uint8                 read 1 byte from stream
+0x2b1  uint8                 read 1 byte from stream
+0x2b2  uint8                 migration param index 0 (from "Migration Parameters" catalogue, idx 0)
+0x2b3  uint8                 migration param index 1 (from "Migration Parameters" catalogue, idx 1)
+0x2b4  uint8                 0
+0x2b8  uint32                0
+0x2bc  uint32                0
+0x2c0  uint32                0
+0x2c8  ReinforcementDetails  slot #1 (vtable PTR_FUN_0046e55c)
+0x2dc  ReinforcementDetails  slot #2 (vtable PTR_FUN_0046e55c)
+0x2f0                        end (size = 0x2f0)
```

### Lobe pointer resolution

When the Tract loader reads a source/dest lobe **index** from the buffer, it looks the lobe up via `param_2 + 4` (the brain's lobe-only vector at `+0x40`):

```c
FUN_0041d870(param_1, &iStack_74, 4);                    // read source lobe index
*(undefined4 *)((int)this + 0x268) =
    *(undefined4 *)(*(int *)(param_2 + 4) + iStack_74 * 4);  // lobe ptr
```

So the wire format stores **lobe indices**, not pointers. The deserialiser dereferences them against the brain's lobe table.

### Tract size constraint

The transfer-buffer ceiling is enforced by `FUN_00403200`. If a tract dump exceeds `*(int *)(DAT_00481288 + 0x10)` bytes, the message box raises:

> Tract to big for transfer\nRequire transfer buffer of: <size>

(string at `0x0047a674`). The same check fires per-lobe with "Lobe to big for transfer" (at `0x0047a63c`). The buffer cap is part of the engine SDK, not the Vat - `DAT_00481288` is a global config object the Catalogue loader fills in.

### Migration Parameters

The Tract ctor pulls two catalogue strings from `Migration Parameters`:

- entry 0 → stored at `+0x2b2` (single byte) - first migration param index
- entry 1 → stored at `+0x2b3` - second migration param index

These match the SVRule-reference's "migration rule" descriptor for tracts.

### Tract::ReinforcementDetails

Two slots inside every Tract: `+0x2c8` and `+0x2dc`. The default ctor `FUN_004253a0` initialises each like this:

```
+0x00   vtable      PTR_FUN_0046e55c
+0x04   uint8       0   (flag)
+0x08   uint32      0   (probably the float operand)
+0x0c   uint32      0
+0x10   uint8       0
+0x14                end (next slot starts)
```

Total size **20 bytes** per ReinforcementDetails. These are the per-Tract reinforcement parameters - the engine uses them to evolve dendrite weights during reinforcement events. The fact that there are **two** slots (matching the two SVRule chains in BrainComponent) suggests one is "main reinforcement" and one is "secondary reinforcement", paralleling the SVRule rule split.

The fields in each slot have not been mapped to specific reinforcement quantities (rate, threshold, decay, etc.) from this binary alone. The SVRule reference suggests `(strength, rate, decay, target)` is plausible but not verified here.

---

## 5. Neuron struct

Allocated as `operator_new(0x24)` and constructed by `FUN_00424870 -> FUN_00424880`. Total size **0x24 = 36 bytes**.

```
+0x00  uint32   first field set by Neuron ctor; read 4 bytes from stream
+0x04..+0x23    eight × 4-byte fields read sequentially from stream
                (the SVRule "neuron variables" V0..V7)
```

Neuron does **not** own its name or its position. The display name comes from the `Brain Lobe Neuron Names` catalogue (§7), keyed by lobe name and neuron index. The position is implicit: the neuron's index in the `Lobe.neurons[]` vector maps to a `(x, y)` cell in the `W × H` grid via `index = y * W + x`.

The dialog `NeuronVarDlg` formats variables as `"Variables Neuron:%d, %s"` (string at `0x47a330`) and graphs as `"Graph Neuron:%d, %s"` (string at `0x47a364`), confirming the variables are graphable per neuron.

---

## 6. Dendrite struct

Constructed by `FUN_00421700` (which zeros 8 fields starting at `+0xc` then calls `FUN_00421750`). Total size **0x2c = 44 bytes**, allocated with `operator_new(0x2c)`.

```
+0x00  uint32   first field, read from stream
                (purpose unknown; possibly bookkeeping/index)
+0x04  Neuron*  source neuron pointer
                (stream supplies an index; loader resolves
                 *(srcLobe.neurons.begin + idx) and stores the ptr)
+0x08  Neuron*  destination neuron pointer (same scheme via dst lobe)
+0x0c..+0x2b    eight × 4-byte fields read sequentially from stream
                The SVRule reference identifies these as
                (W, S, L, A, B, suscept, reinforce, locus_in_src/dst)
                but exact ordering is not nailed down from this binary alone.
```

The eight 4-byte fields per dendrite carry weight, gain, spatial position (dendrites migrate in src/dst neuron locus space), reinforcement state, and book-keeping. The position component is what makes a dendrite "spatial": each dendrite has a locus on its source neuron and one on its dest neuron.

### Dendrite addressing

The Vat formats a dendrite as:

```
(D:(slot)src->dst, name) Dendrite: (slot) from <srcLobe[srcIdx]> to <dstLobe[dstIdx]> in Tract: <srcLobe>->...
```

Strings at `0x47b52c` and `0x47a878` give the format. Decomposing:

- **slot** - the dendrite's index within its containing Tract's `dendrites[]` vector. Tracts hold their dendrites in insertion order, so `slot` is just `tract.dendrites[i]` and `i` is what `(D:(i)...)` prints.
- **src** - the index of the **source neuron within the source lobe**, not within the tract. So in the format `(slot)src->dst`, `src` and `dst` are neuron indices in their respective lobes.
- The textual addressing is `"Dendrite: (slot)src_neuron_idx -> dst_neuron_idx in Tract: srcLobe -> dstLobe"`.

The reverse format `"Dendrite: (slot), %s->%s (was %d->%d)"` (string at `0x47b56c`) is used when the dendrite has migrated - `was %d->%d` is the previous neuron-locus pair, `%s->%s` is the current one resolved to neuron names. Confirming dendrites carry migration state.

---

## 7. Brain Lobe Quads, lobe names, neuron names - catalogue-loaded, not in binary

**This contradicts the brief.** The Brain Lobe Quads coordinate data is **not** a static table baked into the .rdata section. It is loaded at runtime from external Creatures `*.catalogue` files via the engine's `Catalogue` class (statically linked into the Vat).

Evidence trail:

- The string `Brain Lobe Quads` lives at `0x47ae34` (and `0x47ae48`) but is **only** ever used as a lookup key.
- `FUN_00410ab0` (the lobe-name resolver) dispatches lookups via `FUN_0040c9d0(&DAT_00481048, key)` and `FUN_0040bd90(&DAT_0048105c, ...)` - the Catalogue object lives at `DAT_00481048` and its tag-list at `DAT_0048105c`.
- Strings `*.catalogue` (`0x47cd60`), `Catalogue Directory` (`0x47d23c`), `Catalogue Error:` (`0x47cd4c`) confirm the Catalogue is reading external `.catalogue` files at startup.
- The Vat queries `HKCU\Software\CyberLife Technology\Creatures Engine` for the catalogue directory (see `00-architecture.md`) and scans `*.catalogue` from there.

So **for our viewer**: we do not lift quad coordinates out of `Vat_1.9.exe`. We read them from the same `.catalogue` files the Vat reads, which are part of the C3 game install.

### Catalogue tag layout

By tracing catalogue lookups:

- **`Brain Lobes`** - list of lobe **names** (one per lobe). Indexed 0..N-1.
- **`Brain Lobe Quads`** - list of lobe quad coordinates. Same indexing as `Brain Lobes`. Each entry is one **string** (catalogue is a string-list catalogue) - likely `"x y w h"` space-separated, parsed as 4 ints. Confirmed by `FUN_00410ab0` calling `FUN_004118d0` (string-format-with-int-arg) on the quad value, which suggests an `sprintf`-style transform after retrieval. The exact string format is parsed by the Vat at lookup time, not deserialised in bulk.
- **`Brain Lobe Neuron Names`** - per-lobe neuron name list. The lobe ctor uses these to populate UI labels keyed by neuron index. If a neuron has no name in the catalogue, the Vat falls back to `"Neuron %d"` (string at `0x47ae90`, `s_Neuron__d_0047ae90`).
- **`Brain Parameters`** - top-level brain params. The Brain ctor (`FUN_0041b270`) reads two byte-valued entries (indices 0 and 1) into Brain offsets `+0x28` and `+0x2c`. Their meaning is not stated in the binary.
- **`Migration Parameters`** - tract migration param indices. The Tract ctor reads two byte-valued entries (indices 0 and 1) into Tract `+0x2b2` and `+0x2b3`.
- **`Decision Offsets to Expected Agent Script`** - see §8.

### What we do for our own viewer

Re-read the Creatures 3 catalogue files at startup. The Vat tool tells us **which catalogue tags exist** but not their values. Values are at `<C3 install>/Catalogue/*.catalogue`. The cross-reference doc `docs/reference/svrule-brain-complete-reference.md` already lists the Quad coords as part of its lobe table; we use that as our authoritative quad source.

---

## 8. Action Script To Neuron Mappings

Loaded by `FUN_0042b710` at startup. It reads **14 entries** (loop guard `if (0xd < iVar9)` exits at iVar9 == 14) from two parallel catalogues:

- **`Action Script To Neuron Mappings`** (string `0x47c684`) - a flat string-list catalogue. Entry `i` is the **name of the neuron** in the Decision lobe that fires Decision script `i`. The Vat parses each entry as text and stores it at `&DAT_00480fa8 + i*4`.
- **`Decision Offsets to Expected Agent Script`** (string `0x47c658`) - parallel catalogue, also 14 entries. Stored at `&DAT_00480fe0 + i*4`. This holds the **expected agent-script offset** per decision (i.e. which CAOS script number the action triggers).

Together they implement the Action↔Decision↔Script mapping table that lives in the engine's Decision lobe.

After loading both, the Vat sets `DAT_00481038 = 1` (cache flag) so subsequent calls reuse the loaded mapping.

The 14 action / decision count matches the engine's hardcoded Decision lobe (see `svrule-brain-complete-reference.md`, Decision lobe section).

---

## 9. Serialisation format (CreaturesArchive over Brain types)

Each serialisable class has a thin **type-checking wrapper** that calls a base read function, then verifies the read object is the expected RTTI type:

| Wrapper | Class | Type Descriptor used |
|---|---|---|
| `FUN_0041af70` | Brain | `0x47b850` |
| `FUN_004212b0` | BrainComponent | `0x47ba48` |
| `FUN_004233f0` | Lobe | `0x47bbe8` |
| `FUN_00425340` | Tract | `0x47bec8` |

All four wrappers have an identical body:

```c
FUN_00436fc0(this, archive);  // base CreaturesArchive read
if (*archive != 0) {
    if (FUN_0045a41a(*archive, 0, RTTI_TD, RTTI_TD, 0) == 0) {
        throw "Type mismatch during serialisation of <Class>";
    }
}
return this;
```

`FUN_00436fc0` is the polymorphic CreaturesArchive read function (vtable-dispatched on the archive's `Read` op). `FUN_0045a41a` is the MSVC RTTI `__RTtypeid` check. The error strings are:

- Brain: `0x47b730`
- BrainComponent: `0x47ba10`
- Faculty: `0x47ba8c`
- Instinct: `0x47bad4`
- Lobe: `0x47bba0`
- SVRule: `0x47bd60`
- Tract: `0x47bdd0`
- Genome: `0x47bf1c`

So `Faculty`, `Instinct`, `SVRule`, `Genome` are **all** part of the on-disk archive format even though only `Brain`, `Lobe`, `Tract` are exercised by the wire-protocol path. They appear in offline-mode genome files.

### Serialisation order per class

Recovered from the constructors that take a stream argument (`FUN_00423840` Lobe, `FUN_00426290` Tract, `FUN_0041b270` Brain).

**Brain** - does not deserialise from stream directly (built by sequential CAOS dump commands). The Brain ctor sets up empty containers and pulls two byte-valued params from the `Brain Parameters` catalogue. There is no top-level Brain serialiser invocation in the data path.

**Lobe** (read order):

1. `FUN_0041d870(stream, this+0x004, 4)` - 4 bytes
2. `FUN_0041d870(stream, this+0x248, 4)` - 4 bytes
3. `FUN_0041d870(stream, this+0x250, 4)` - 4 bytes (lobe type tag, used as 4-char key)
4. `FUN_0041d870(stream, this+0x00c, 4)` - 4 bytes
5. seven × 4 bytes into `this+0x270, +0x274, +0x278, +0x27c, +0x280, +0x284, +0x288` (grid params; `+0x278 * +0x27c` = neuron count)
6. `FUN_0041d870(stream, this+0x25c, 4)` - 4 bytes
7. **If V1.1**: SVRule at `+0x10` (16 rules × 16 bytes via `FUN_00424aa0`)
8. SVRule at `+0x128` (always)
9. Compute lobe name as 4-char string from `+0x250` tag, copied to `+0x254`.
10. Validate `W * H > 0` and `< 0xfe01`; throw if not.
11. Allocate `int[W*H]` flag array at `+0x28c`.
12. For each of the `W*H` neurons: read 4 bytes into the flag entry, then construct Neuron (`FUN_00424870`) and read 8 × 4 bytes (`+0x4..+0x23`) into it. Append to `this->neurons` vector at `+0x264`.
13. **If V1.1**: read 1 byte into `+0x008`.

**Tract** (read order):

1. Two `Migration Parameters` byte-fetches from catalogue → `+0x2b2`, `+0x2b3`.
2. `FUN_0041d870(stream, this+0x004, 4)`
3. `FUN_0041d870(stream, this+0x00c, 4)`
4. Read source-lobe index (4 bytes), resolve into `+0x268` Lobe pointer via brain-lobe-vector lookup.
5. `FUN_0041d870(stream, this+0x26c, 4)` - source-side range start
6. `FUN_0041d870(stream, this+0x270, 4)` - source-side range end
7. Variable-length tag (`FUN_004251a0`) → `+0x274` (1 byte)
8. Read dest-lobe index (4 bytes), resolve into `+0x28c`.
9. `+0x290`, `+0x294` (4 bytes each) - dest-side range
10. Variable-length tag → `+0x298`
11. `+0x2b0`, `+0x2b1` - 1 byte each
12. SVRule at `+0x10` (always; here this is the BrainComponent's first slot)
13. SVRule at `+0x128`
14. Build display name: `srcLobeName + "->" + dstLobeName` into `+0x248`.
15. Validate non-empty source and dest neuron lists; throw if not.
16. Read 4 bytes - dendrite count `N`.
17. For each dendrite (N times): allocate `Dendrite` (44 bytes), read first 4 bytes into `+0x00`, read source-neuron-index (4 bytes) and resolve to pointer in `+0x04`, read dest-neuron-index (4 bytes) and resolve to pointer in `+0x08`, then read 8 × 4 bytes into `+0x0c..+0x2b`. Append to `tract.dendrites` at `+0x260`.
18. **If V1.1**: read 1 byte into `+0x008`.

### Version sensitivity

The dump-format flag `DAT_00480e9c` (1.0f or 1.1f, set from `END DUMP` vs `END DUMP V1.1` sentinels) changes how SVRule rows are read. In `FUN_00424aa0`:

- **V1.0**: SVRule's first three opcode columns are read as **variable-length tags** via `FUN_004251a0` (1 byte each, with -1 sentinel meaning "skip"). Only the float operand is read as fixed 4 bytes.
- **V1.1**: All four columns are read as fixed 4 bytes via `FUN_0041d870`.

Anyone reimplementing serialisation **must** branch on this flag, or the SVRule chain will misalign and the brain will decode as garbage. The flag is set globally per dump - there's no per-component switch.

### Catalogue loads at component construction

Tract construction reads the `Migration Parameters` catalogue **inside** the Tract ctor. Lobe construction does not read any catalogue (the lobe name comes from the in-stream tag at `+0x250`, mapped via the catalogue at lookup time but stored as-is at construction). Brain construction reads two `Brain Parameters` entries.

This means the catalogue must be loaded **before** any Brain/Lobe/Tract is deserialised - and it is, from app startup (in `FUN_00403200` and earlier).

---

## 10. Open questions and unverified fields

The following are visible but not yet decoded:

- **Lobe `+0x270` and `+0x274`**: 4-byte each, read from stream. Likely "neuron loci size in X" and "in Y" (the dendrite locus space dimensions per axis), but not confirmed against an engine-source ground truth.
- **Lobe `+0x280, +0x284, +0x288`**: 4-byte each, read from stream. SVRule reference suggests "default state values for new neurons" and similar; not yet anchored to specific fields here.
- **Neuron `+0x00`**: first 4-byte field read into Neuron. Could be a state flag, an activation cache, or a back-pointer. Not determined.
- **Neuron 8-float ordering**: we know there are 8 floats at `+0x04..+0x23`, but their identity (which is V0 vs V7) is taken on faith from the SVRule reference. The Vat does not ship this binding anywhere we have located inside the binary; the binding is purely externalised to the `Brain Lobe Neuron Names` catalogue.
- **Dendrite 8-float ordering**: same situation as neurons. Eight 4-byte fields at `+0x0c..+0x2b` with names from the catalogue, not from the Vat code.
- **Tract `+0x278` and `+0x29c` "migration parameters" sub-structs**: built by `FUN_00428600`. Not yet traced. These are 0x14 bytes each (`+0x278..+0x28b` source side, `+0x29c..+0x2af` dest side) and probably hold the migration vector (locus delta, momentum, learning rate).
- **ReinforcementDetails fields**: 20 bytes per slot, layout known structurally (1 byte, 4 bytes, 4 bytes, 1 byte) but field semantics not yet confirmed against the engine source. Plausible layout per the SVRule reference is `(active_flag, threshold, rate, sign)`.
- **Brain `+0x64/+0x68` aux vector**: 12 bytes per element, sized parallel to the lobe list. The Lobe loader initialises new entries to `{0xFFFFFFFF, 0xFFFFFFFF, ?}`. Purpose unknown - possibly per-lobe runtime-state placeholders the Vat fills in when querying `BRN: DMPN`/`BRN: DMPD`.
- **Brain `+0x28, +0x2c`**: byte-valued fields populated from `Brain Parameters` catalogue. Field names not in the binary.
- **Lobe `+0x250` tag → `+0x254` name conversion**: The Lobe ctor copies the 4-byte tag at `+0x250` into the first 4 bytes of `+0x254`, then null-terminates. So the lobe **name** at `+0x254` is a 4-char ASCII type tag (matching the C3 lobe naming convention: 4-char IDs like "perc", "drv0", "stim" etc.). The display name comes from looking up that tag in the `Brain Lobes` catalogue. Worth verifying.

---

## ASCII layout diagram

```
                    +-----------------------------+
                    |  Brain (size 0x74)          |
                    |  +0x30/+0x38 BrainComp[]    |
                    |  +0x40/+0x48 Lobe[]   ------+--+
                    |  +0x50/+0x58 Tract[]  ---+  |  |
                    +--------------------------+  |  |
                                               |  |  |
                                  +------------+  |  |
                                  v               v  |
              +--------------+   +-------------------+
              | Tract        |   | Lobe              |
              | size 0x2f0   |   | size 0x290        |
              | inherits     |   | inherits          |
              | BrainComp    |   | BrainComp         |
              |--------------|   |-------------------|
              | +0x10  SVRule|   | +0x10  SVRule (v1.1 only)
              | +0x128 SVRule|   | +0x128 SVRule
              | +0x248 name  |   | +0x254 name (4-char tag)
              | +0x260 dend* |   | +0x264 neuron* []
              | +0x268 srcL  |---+ +0x278/+0x27c W*H
              | +0x28c dstL  |---+ +0x28c flags[]
              | +0x2b2 migr  |   |
              | +0x2c8 ReinD |   |  Each neuron:
              | +0x2dc ReinD |   |    Neuron* (size 0x24)
              +------+-------+   |      8 × 4-byte vars
                     |           +-------------------+
                     |
                     | each dendrite (size 0x2c)
                     v
              +------------------+
              | Dendrite         |
              | +0x00 ?          |
              | +0x04 src Neuron*|
              | +0x08 dst Neuron*|
              | +0x0c..+0x2b     |
              |   8 × 4-byte vars|
              +------------------+
```

---

## Summary for the porting effort

| Question | Answer |
|---|---|
| Are coordinates in the binary? | **No.** They are in `*.catalogue` files in the C3 install. |
| Can I deserialise a Brain blob? | **No, not as one blob.** The Vat builds Brain piecewise via `BRN: DMPB`, `DMPL`, `DMPT` calls, each producing a per-component buffer terminated by `END DUMP` or `END DUMP V1.1`. Offline mode does use a single CreaturesArchive but per-component type-checking is preserved. |
| Brain size, Lobe size, Tract size, Neuron size, Dendrite size? | 0x74, 0x290, 0x2f0, 0x24, 0x2c bytes respectively. |
| Two SVRule chains per BrainComponent? | **Yes**, at `+0x10` (primary) and `+0x128` (secondary). 16 rules × 16 bytes each. |
| Two ReinforcementDetails per Tract? | **Yes**, at `+0x2c8` and `+0x2dc`. 20 bytes each. |
| Dendrites carry spatial state? | **Yes**, 8 × 4-byte vars per dendrite include weight, locus on src/dst neurons, plus reinforcement state. |
| Action-to-Neuron mappings? | **14 entries**, loaded from `Action Script To Neuron Mappings` and `Decision Offsets to Expected Agent Script` catalogues at startup. |
| Dump-format versioning? | **Yes**, V1.0 (sentinel `END DUMP`) reads SVRule opcodes as variable-length 1-byte tags; V1.1 (`END DUMP V1.1`) reads them as fixed 4-byte ints. Reimplementations must branch. |
