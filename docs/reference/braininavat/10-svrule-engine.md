# Brain in a Vat: The SVRule Engine

Decompilation findings for the `SVRule` rules engine and `SVRuleDlg` editor as statically compiled into `Vat_1.9.exe`. The Vat was built against the Creature Labs Creatures Engine SDK; this document is a binary-grounded reference for the SVRule machine that drives every C3 lobe state update and every C3 tract dendrite reinforcement.

Companion doc: [00-architecture.md](00-architecture.md). Class registry: [09-class-registry.md](09-class-registry.md). External (peer-reviewed) reference: `<PROJECT_ROOT>\docs\reference\svrule-brain-complete-reference.md`.

## At a glance

| Item | Finding |
|---|---|
| Per-program lines | **16** (loop bound `0xf < iVar10` at `0x00421d04`) |
| Per-line in-memory size | **16 bytes** (4 floats: opcode, operand-index, raw-operand, normalised-operand) |
| Per-line on-disk size | **3 bytes** (opcode byte, operand-index byte, raw-operand byte) |
| Programs per Lobe | 2 parsed at `+0x10` and `+0x128`; **only the first is invoked by the binary's update path** |
| Programs per Tract | 2 parsed at `+0x10` and `+0x128`; **both invoked**, the first gated by tract flag at `+0x8` |
| Opcode range | 0..0x44 (= 68) per the read-side clamp at `0x00424a13` |
| Operand-index range | 0..0xf (= 15) per the read-side clamp at `0x00424a25` |
| Raw operand range | 0..0xff (most types) or 0..0x07 (one type), selected by per-index lookup at `&DAT_0047bd10` |
| Operand-byte normalisation | `byte / 248.0`, then clamped to `<= 1.0` at `0x00424a8c` |
| Interpreter entry | `FUN_00421830` (size 2604 bytes, 8 params) |
| Reader (binary float archive) | `FUN_00424a00` |
| Reader (byte-stream archive) | `FUN_00424aa0` |
| Writer (binary float archive) | `FUN_00424b30` |
| Writer (byte-stream archive) | `FUN_00424be0` |
| RTTI Type Descriptor | `0x0047bda8` (`.?AVSVRule@@`, label `SVRule::RTTI_Type_Descriptor`) |
| `SVRuleDlg` Type Descriptor | `0x0047a430` (`.?AVSVRuleDlg@@`) |

---

## 1. SVRule class structure

### What the binary tells us, and what it does not

The class name and RTTI Type Descriptor for `SVRule` exist:

| Address | String / label |
|---|---|
| `0x0047bd50` | `"SVRule"` (class name tag, copy 1) |
| `0x0047bd58` | `"SVRule"` (class name tag, copy 2) |
| `0x0047bd60` | `"Type mismatch during serialisation of SVRule"` |
| `0x0047bda8` | `SVRule::RTTI_Type_Descriptor` |
| `0x0047bdb0` | `".?AVSVRule@@"` (mangled type name) |

(Source: `notes/strings.txt` lines 435-438, `notes/symbols.txt` line 2645.)

Importantly: **the SVRule type-mismatch string and RTTI Type Descriptor are not referenced by any decompiled function.** I searched all 3,140 decompiled `.c` files for `0x47bda8`, `0x47bd60`, `s_SVRule`, and the mangled tag - no hits.

By contrast, every other engine class with a "Type mismatch during serialisation of X" string (Brain, BrainComponent, Faculty, Instinct, Lobe, Tract) has a matching wrapper function that calls `FUN_00436fc0` (the `CreaturesArchive::ReadObject` dispatcher) and validates the result with the MSVC `__RTDynamicCast` runtime (`FUN_0045a41a`). Five such wrappers exist (Faculty, BrainComponent, Instinct, Lobe, Tract) at addresses `0x0041af70`, `0x004212b0`, `0x004227d0`, `0x004233f0`, `0x00425340`. There is **no SVRule equivalent**.

What this means: SVRule is **not serialised as a polymorphic CreaturesArchive object**. Lobe and Tract serialisers read SVRule programs **inline**, byte-by-byte, into a fixed-offset region of their own struct. The SVRule RTTI Descriptor exists for runtime `dynamic_cast` use elsewhere (probably the editor and brain-validation code) but does not gate object I/O.

### What "an SVRule object" is, in the Vat runtime

There is no separately-allocated SVRule object visible in the decompiled object lifecycle. Every SVRule program lives **embedded** at a fixed offset inside a parent Lobe or Tract:

- Lobe parses two SVRule programs at offsets `+0x10` and `+0x128` of the Lobe struct (Lobe::Read = `FUN_00423490`, lines 70-71).
- Tract parses two SVRule programs at the same two offsets of the Tract struct (Tract::Read = `FUN_00425630`, lines 175-176; alternate Tract::Read = `FUN_00426290`).
- `0x128 - 0x10 = 0x118` = 280 bytes per SVRule region. The actively used 16 lines occupy bytes `+0x14..+0x114` (256 bytes); the remaining 24 bytes are SVRule-region scratch / per-program metadata that the interpreter does not read in the dispatch loop. One 4-byte slot at `this+0x114` IS read by the interpreter (opcodes 6-8), and is a pointer to an external value table (see Section 3).

Because the binary does not give us a vtable or member-function set for `SVRule`, the canonical model of an SVRule object in this Vat tool is exactly: the 16-line program region inside a Lobe or Tract.

---

## 2. SVRule program format

### On-disk format (parsed by `FUN_00424a00`)

`FUN_00424a00(this, stream)` runs a 16-iteration loop. Each iteration calls `FUN_0042a0e0(stream, lo, hi)` three times - that helper reads one byte from a position pointer at `stream+0x10`, advances it, and clamps the byte into `[lo, hi]`. The three reads per line are:

```c
byte0 = stream.next_clamped(0, 0x44);           // opcode, 0..68
byte1 = stream.next_clamped(0, 0x0f);           // operand index, 0..15
range = (op_table[byte1] != 2) ? 0xff : 0x07;   // table at &DAT_0047bd10
byte2 = stream.next_clamped(0, range);          // raw operand byte
```

(Source: `decompiled/00424a00_FUN_00424a00.c` lines 14-22.)

After the three byte reads, the line is materialised into four floats:

```c
line.opcode_f       = (float) byte0;            // *(this+4)
line.operand_idx_f  = (float) byte1;            // *(this+8)
line.operand_raw_f  = (float) byte2;            // *(this+0xc)
line.operand_norm   = clamp((float)byte2 / 248.0f, ., 1.0f);  // *(this+0x10)
```

Then `this` advances by `0x10` for the next line. **Three bytes on disk become four floats in memory.** The on-disk per-program size is `3 * 16 = 48 bytes`, which matches the genome layout that community references describe.

### In-memory format (used by `FUN_00421830`)

After parsing, each line is a 16-byte block (4 floats). For 16 lines that is 256 bytes, sitting at `program_base + 4 .. program_base + 0x104`. The 4-byte slot at `program_base + 0x114` is a read-only pointer to an external 256-entry value table used by operand-index types 6/7/8 (chemical / index-relative reads).

### Wire format variants

Four serialisation routines exist:

| Function | Purpose | Per-line on-stream |
|---|---|---|
| `FUN_00424a00` | Read, byte-stream mode (used by Lobe::Read, Tract::Read) | 3 bytes |
| `FUN_00424aa0` | Read, archive-float mode (used by Tract::Read variant `FUN_00426290`) | 3 bytes via `FUN_004251a0` OR 4 bytes via `FUN_0041d870` (gated by `DAT_00480e9c == 1.0f`) plus 1 float (`puVar3[+4]`, the normalised value) |
| `FUN_00424b30` | Write, archive-float mode | 4 floats per line via `FUN_00436330` / `FUN_004363e0` (`CreaturesArchive::WriteFloat` family) |
| `FUN_00424be0` | Write, byte-stream mode | 3 bytes plus 1 float via `FUN_00424680` |

The two reader/writer pairs correspond to (a) the embedded genome / brain-snapshot bytes path, and (b) the `CreaturesArchive` typed-float path used when SVRules round-trip through the engine's snapshot files. Probable: `DAT_00480e9c` is a global flag selecting "compact byte" vs "verbose float" archive layout. Uncertain because: the global is not initialised in any decompiled function I located.

### Operand-index → operand-range table at `0x0047bd10`

The expression `(-(uint)(*(int*)(&DAT_0047bd10 + idx*4) != 2) & 0xf8) + 7` decodes as:

- If `op_table[idx] == 2`: range = 7 (operand byte clamped to 0..7)
- Otherwise: range = 0xff (operand byte clamped to 0..255)

The table sits between the opcode metadata table (ends at `0x47bd10`) and the SVRule string at `0x47bd50`, giving exactly `0x40` bytes = 16 entries × 4 bytes - one entry per operand-index value (0..15). **The actual contents of the 16 entries are not enumerated in the decompiled output**; we only know that *some* indices have value 2 (these are the "small operand" indices 0..7, almost certainly the indices that select neuron/dendrite variable slots - there are 8 variables per neuron in the C3 model, so the operand byte must be 0..7) and the rest do not.

### Opcode metadata table at `0x0047bbfc`

The interpreter dispatch begins:

```c
iVar7 = line.opcode;                                   // 0..0x44
iVar8 = *(int *)(&DAT_0047bbfc + iVar7 * 4);           // class lookup
```

(Source: `decompiled/00421830_FUN_00421830.c` line 35.)

The table sits between Lobe RTTI (`0x47bbe8 + 0x14 = 0x47bbfc`) and the operand-index table at `0x47bd10`, giving `0x114 / 4 = 69` entries - exactly the opcode count (0..0x44 = 0..68 inclusive). Each entry is a *class* tag selecting the dispatch path:

| Class | Behaviour |
|---|---|
| 0 | Control flow / no-effect (HALT, NOP, conditional-jumps that consult special state). Falls through to `switchD_00421886_default` (advance to next line) unless the opcode itself overrides. |
| 1 | Operates on the accumulator. Computes a value `param_3` from operand-index dispatch, then does `acc = f(acc, param_3)` or compares acc to it. |
| 2 | Directly mutates a referenced variable (neuron, dendrite, source neuron, chemical) - chooses a target pointer based on operand-index, then applies a function selected by opcode. |

The entries themselves are not enumerated in the decompiled C, but per-opcode classification is recoverable by inspecting which arm of the dispatch each opcode lands in. (See Section 3 opcode catalogue.)

---

## 3. SVRule execution model

### `FUN_00421830` is the interpreter

Signature, recovered from decompilation:

```c
undefined4 SVRule::Execute(
    SVRule*       this_program,   // points to the 16-line block (lobe+0x10 or +0x128, etc.)
    float*        param_1,        // SOURCE neuron variables   (or zero-array for lobe-update)
    float*        param_2,        // DENDRITE variables        (or destination neuron variables for lobe-update)
    float*        param_3,        // DESTINATION neuron vars   (this neuron, for lobe-update)
    float*        param_4,        // CHEMICAL levels           (or zero-array for lobe-update)
    int           param_5,        // SOURCE neuron index
    int           param_6,        // DESTINATION neuron index
    int           param_7);       // host Tract pointer (used by reinforcement-write opcodes; 0 for lobe-update)
```

Return value: 1 if any opcode set `local_c = 1` (this is set by the HALT-class opcodes 0 and 0x1f, and by opcode 0x2a if a comparison trips). 0 otherwise. The return value is the **"register as spare"** signal, used by Winner-Takes-All in lobes that use a spare neuron.

### Per-tick driver functions

| Caller | Address | Role |
|---|---|---|
| **Lobe::Update** | `FUN_004237d0` | Walks the lobe's neuron list. For each neuron, if `lobe+8 == 0` runs SVRule at `lobe+0x10`; if `lobe+8 != 0` calls `FUN_00424880` (zeroes 32 bytes of neuron state). |
| **Tract::Update** | `FUN_00426f20` | Walks the tract's dendrite list. For each dendrite: if `tract+8 != 0` runs SVRule at `tract+0x10` (gated); always runs SVRule at `tract+0x128`; then calls `FUN_00428370` to apply reinforcement deltas. |
| **(predicate)** | `FUN_00421720` | Tiny wrapper that runs an arbitrary SVRule program with `param_2 = this+0xc` and zero-arrays elsewhere - probable: a "test if neuron qualifies" predicate. |

(Sources: `decompiled/004237d0_FUN_004237d0.c`, `decompiled/00426f20_FUN_00426f20.c`, `decompiled/00421720_FUN_00421720.c`.)

### Parameter mapping by context

For **Lobe::Update** (`FUN_004237d0` lines 19-20):

```c
FUN_00421830(
    /*program*/ lobe + 0x10,
    /*param_1*/ &DAT_00480f3c,        // ZERO ARRAY
    /*param_2*/ &DAT_00480f3c,        // ZERO ARRAY
    /*param_3*/ neuron->vars,         // (puVar2 + 1) - the neuron's float[8] block
    /*param_4*/ &DAT_00480f3c,        // ZERO ARRAY
    /*param_5*/ neuron_index,
    /*param_6*/ neuron_index,
    /*param_7*/ 0);
```

For **Tract::Update** (`FUN_00426f20` lines 20-28), runs once per dendrite:

```c
// First SVRule: ONLY if tract+8 != 0
if (tract->flags8) {
  FUN_00421830(
    /*program*/ tract + 0x10,
    /*param_1*/ src_neuron->vars,            // (*(int**)(dendrite+4) + 1)
    /*param_2*/ dendrite->vars,              // (dendrite + 0xc)
    /*param_3*/ dst_neuron->vars,            // (*(int**)(dendrite+8) + 1)
    /*param_4*/ creature_chemicals,          // (*(int*)(tract->dst_lobe + 0x24c))
    /*param_5*/ src_neuron_index,
    /*param_6*/ dst_neuron_index,
    /*param_7*/ tract);
}
// Second SVRule: ALWAYS
FUN_00421830(
    /*program*/ tract + 0x128,
    /*param_1*/ src_neuron->vars,
    /*param_2*/ dendrite->vars,
    /*param_3*/ dst_neuron->vars,
    /*param_4*/ creature_chemicals,
    /*param_5*/ src_neuron_index,
    /*param_6*/ dst_neuron_index,
    /*param_7*/ tract);
FUN_00428370(tract, dendrite);              // apply reinforcement deltas
```

This confirms: for a dendrite, **the SVRule has read access to source neuron, destination neuron, dendrite, and chemicals**, and write access to all four (subject to clamping) plus to two pre-baked reinforcement slots on the host tract (see Section 7).

### Internal registers

The interpreter keeps two persistent per-call registers:

- `local_8` - the **accumulator** (called `acc` in the external reference). Starts as `*param_1` (source neuron's variable[0], for tract programs) or `0` (effectively, for lobe programs that pass zero for `param_1`).
- `local_10` - a **persistent register** initialised to `0`, written by opcode `0x18` (set persistence rate) and consumed by opcodes `0x19` (mix-toward) and `0x23` (operand-class-2 mix-store). Probable: this is the "tend rate" / persistence-rate register. Basis: opcode `0x18` calls `FUN_004595ab` (a `min`/`max` clamp) and stores the result; opcode `0x19` performs `acc = operand * persist + (1 - persist) * acc`. Uncertain because: the function name is not recovered; the use pattern is clear.

The interpreter also reads `iVar10` (the program counter) and modifies it for skip/branch opcodes.

### Per-line dispatch (recovered from `FUN_00421830`)

```c
PC = 0
acc = *param_1        // accumulator initial value
persist = 0
return_flag = 0
loop:
  line = program[PC]
  class = opcode_table[line.opcode]               // &DAT_0047bbfc + opcode*4
  if class == 0:
    handle_control_flow(line.opcode)              // HALT (0), specials (0x1f, 0x2a)
  elif class == 1:
    operand_value = resolve_class1_operand(       // 16-way switch on line.operand_idx
        line.operand_idx, line.operand_raw, line.operand_norm,
        param_1..param_4, persist, srcidx, dstidx, this->ext_table)
    apply_class1_op(line.opcode, &acc, operand_value, &persist, return_flag, ...)
  elif class == 2:
    target = select_class2_target(                // 4-way switch on line.operand_idx 1..4
        line.operand_idx, line.operand_raw,
        param_1..param_4)
    apply_class2_op(line.opcode, target, &acc, persist)
  PC += 1
  if PC > 15: return return_flag
```

(Source: `decompiled/00421830_FUN_00421830.c`, full body. The three switch statements are at lines 50-65, 130-189, 190-505.)

### Class-1 operand resolution (line.operand_idx → value)

```
case 0:  operand = acc                           // accumulator self-reference
case 1:  operand = param_1[line.operand_raw]     // source neuron var
case 2:  operand = param_2[line.operand_raw]     // dendrite var
case 3:  operand = param_3[line.operand_raw]     // destination neuron var
case 4:  operand = param_4[line.operand_raw]     // chemical / spare-neuron var
case 5:  operand = (LCG_step() >> 17 * 0x10001) >> 15) / 65535.0  // random in [0,1)
case 6:  operand = ext_table[(line.operand_raw + param_5) & 0xff]  // src-relative
case 7:  operand = ext_table[line.operand_raw & 0xff]              // direct chemical
case 8:  operand = ext_table[(line.operand_raw + param_6) & 0xff]  // dst-relative
case 0xa: operand = 1.0                          // constant 1.0
case 0xb: operand = line.operand_norm            // raw normalised [0,1]
case 0xc: operand = -line.operand_norm           // raw negated
case 0xd: operand = line.operand_norm * 10.0     // value × 10
case 0xe: operand = line.operand_norm / 10.0     // value / 10
case 0xf: operand = round(line.operand_norm * 248.0)  // raw integer back from norm
default: operand = 0                             // including case 9 = "zero"
```

(Source: lines 130-189.)

The LCG used by case 5 is `seed = seed * 0x19660d + 0x3c6ef35f` - the canonical MSVC `rand()` constants. Same generator is used in random-dendrite construction in Tract::Read. The seed lives at `&DAT_00481248` (engine-global).

### Class-2 operand resolution (line.operand_idx → write target)

```
case 1: target = &param_1[line.operand_raw]      // source neuron var
case 2: target = &param_2[line.operand_raw]      // dendrite var
case 3: target = &param_3[line.operand_raw]      // destination neuron var
case 4: target = &param_4[line.operand_raw]      // chemical (write back to chemicals!)
default: skip line
```

(Source: lines 50-65.)

### Class-1 opcode catalogue

The named labels below are **descriptive** (derived from the binary's behaviour). The Vat binary contains no opcode-name strings; the editor (`SVRuleDlg`) almost certainly fetches mnemonics from a `.catalogue` file at runtime. Do not treat these names as authoritative - they are notes for cross-referencing the external community-maintained tables.

| Op (hex) | Op (dec) | Behaviour | Decompilation case |
|---|---|---|---|
| 0x00 | 0 | HALT - return immediately | `iVar7 == 0` early return at line 38 |
| 0x04 | 4 | If `acc != operand` then PC += 1 (skip next) | `case 4` line 191 |
| 0x05 | 5 | If `acc == operand` then skip | `case 5` line 196 |
| 0x06 | 6 | If `acc <= operand` then skip | `case 6` line 201 |
| 0x07 | 7 | If `operand <= acc` then skip | `case 7` line 206 |
| 0x08 | 8 | If `acc < operand` then skip | `case 8` line 211 |
| 0x09 | 9 | If `operand < acc` then skip | `case 9` line 216 |
| 0x0a | 10 | If `operand != 0` then skip | `case 10` line 221 |
| 0x0b | 11 | If `operand == 0` then skip | `case 11` line 226 |
| 0x0c | 12 | If `operand <= 0` then skip | `case 12` line 231 |
| 0x0d | 13 | If `operand >= 0` then skip | `case 13` line 236 |
| 0x0e | 14 | If `operand < 0` then skip | `case 14` line 241 |
| 0x0f | 15 | If `operand > 0` then skip | `case 15` line 246 |
| 0x10 | 16 | `acc += operand` | `case 0x10` line 251 |
| 0x11 | 17 | `acc -= operand` | fallthrough from 0x1c, line 303 |
| 0x12 | 18 | `acc = operand - acc` | `case 0x12` line 254 |
| 0x13 | 19 | `acc *= operand` | `case 0x13` line 259 |
| 0x14 | 20 | `if (operand != 0) acc /= operand` | `case 0x14` line 262 |
| 0x15 | 21 | `if (acc != 0) acc = operand / acc` | `case 0x15` line 267 |
| 0x16 | 22 | `acc = min(acc, operand)` | `case 0x16` line 272 |
| 0x17 | 23 | `acc = max(acc, operand)` | `case 0x17` line 277 |
| 0x18 | 24 | `persist = clamp(operand)` (set persistence rate) | `case 0x18` line 282 |
| 0x19 | 25 | `acc = operand * persist + (1 - persist) * acc` (tend-toward) | `case 0x19` line 287 |
| 0x1a | 26 | `acc = -operand` | `case 0x1a` line 291 |
| 0x1b | 27 | `acc = abs(operand)` (negate-if-negative) | `case 0x1b` line 295 |
| 0x1c | 28 | If `acc <= operand`: `acc = operand - acc`; else `acc -= operand` | `case 0x1c` line 301 |
| 0x1d | 29 | (alias of 0x12) `acc = operand - acc` | `case 0x1d` line 254 |
| 0x1f | 31 | Set `return_flag = 1` and continue | `iVar7 == 0x1f` line 40-46 |
| 0x20 | 32 | `acc = clamp(operand, 0, 1)` | `case 0x20` line 306 |
| 0x21 | 33 | `acc = clamp(operand, -1, 1)` | `case 0x21` line 315 |
| 0x24 | 36 | If `param_3[1] < operand`: `param_3[1] = 0` (threshold-zero) | `case 0x24` line 324 |
| 0x25 | 37 | `persist = operand` (alternate persistence-set) | `case 0x25` line 329 |
| 0x26 | 38 | `param_3[1] = operand * persist + (1 - persist) * param_3[1]` | `case 0x26` line 332 |
| 0x27 | 39 | `param_3[1] = operand * param_3[1]` | `case 0x27` line 335 |
| 0x28 | 40 | `param_3[0] = operand * param_3[0] + (1 - operand) * param_3[1]` | `case 0x28` line 338 |
| 0x29 | 41 | `param_3[0] += LCG_random_float * operand` (signal noise) | `case 0x29` line 341 |
| 0x2a | 42 | If `*param_3 < *param_4`: `param_3[2] = *param_3; param_4[2] = 0` (winner-take-all comparison) | `iVar7 == 0x2a` line 41-43 |
| 0x2b | 43 | `tract->0x2c4 = clamp_min0(operand)` (set short-term-relax-rate) | `case 0x2b` calls `FUN_00424ec0` line 346 |
| 0x2c | 44 | Bidirectional smoothing of `param_3[0]` and `param_3[1]` using `tract->0x2c4` and `operand` | `case 0x2c` calls `FUN_00424ef0` line 349 |
| 0x2e | 46 | If `operand == 0` HALT | `case 0x2e` line 352 |
| 0x2f | 47 | If `operand != 0` HALT | `case 0x2f` line 357 |
| 0x30 | 48 | If `acc == 0`: jump to line `round(operand) - 1` (forward only) | `case 0x30` line 362 |
| 0x31 | 49 | If `acc != 0`: jump to line `round(operand) - 1` (forward only) | `case 0x31` line 373 |
| 0x32 | 50 | If `operand != 0`: `acc /= operand; param_3[1] = clamp(acc + param_3[1])` | `case 0x32` line 376 |
| 0x33 | 51 | `acc *= operand; param_3[1] = clamp(acc + param_3[1])` | `case 0x33` line 392 |
| 0x34 | 52 | Unconditional jump to line `round(operand) - 1` (forward only) | `case 0x34` line 406 |
| 0x35 | 53 | If `acc < operand` HALT | `case 0x35` line 416 |
| 0x36 | 54 | If `operand < acc` HALT | `case 0x36` line 421 |
| 0x37 | 55 | If `acc <= operand` HALT | `case 0x37` line 426 |
| 0x38 | 56 | If `operand <= acc` HALT | `case 0x38` line 431 |
| 0x39 | 57 | Tract reinforcement: set `tract->0x2d0 = clamp(operand, -1, 1)` (probable: STW reinforcement amount) | `case 0x39` calls `FUN_00424cc0` line 436 |
| 0x3a | 58 | Tract reinforcement: set `tract->0x2d4 = clamp(operand, -1, 1)` (probable: LTW or second-channel) | `case 0x3a` calls `FUN_00424d20` line 439 |
| 0x3b | 59 | Tract reinforcement: set `tract->0x2d8 = (byte)operand`, set marker `tract->0x2cc = 1` | `case 0x3b` calls `FUN_00424d80` line 442 |
| 0x3c | 60 | Tract reinforcement: set `tract->0x2e4 = clamp(operand, -1, 1)` | `case 0x3c` calls `FUN_00424dc0` line 446 |
| 0x3d | 61 | Tract reinforcement: set `tract->0x2e8 = clamp(operand, -1, 1)` | `case 0x3d` calls `FUN_00424e20` line 449 |
| 0x3e | 62 | Tract reinforcement: set `tract->0x2ec = (byte)operand`, set marker `tract->0x2e0 = 1` | `case 0x3e` calls `FUN_00424e80` line 452 |
| 0x3f | 63 | `param_3[4] = param_3[round(operand) & 7]` (preserve neuron SV - opcode 63 in the external ref) | `case 0x3f` line 456 |
| 0x40 | 64 | `param_3[round(operand) & 7] = param_3[4]` (restore neuron SV) | `case 0x40` line 463 |
| 0x41 | 65 | `param_4[4] = param_4[round(operand) & 7]` (preserve "spare" SV) | `case 0x41` line 470 |
| 0x42 | 66 | `param_4[round(operand) & 7] = param_4[4]` (restore "spare" SV) | `case 0x42` line 477 |
| 0x43 | 67 | If `acc < 0`: jump to line `round(operand) - 1` (forward only) | `case 0x43` line 484 |
| 0x44 | 68 | If `acc > 0`: jump to line `round(operand) - 1` (forward only) | `case 0x44` line 495 |
| (default) |  | Any unhandled opcode falls to `switchD_00421886_default` and advances PC by 1 | line 506 |
| 0x03 | 3 | `acc = operand` (load) - labelled `case 3` line 297 (chained from 0x1b/0x20/0x21) |  |

Several integer values in `[0..0x44]` are not handled by any explicit case (the binary leaves them to fall through `switchD_00421886_default`, effectively NOPs). The presence of opcode metadata table entries for these slots suggests they may be marked as invalid - but the table contents are not enumerated in the decompiled code.

### Class-2 opcode catalogue (operand_idx selects target var, opcode selects op)

This is the second arm - when the metadata table classifies the opcode as 2, it operates **directly on a writable target variable** (one of `param_1[i]`, `param_2[i]`, `param_3[i]`, `param_4[i]`):

| Op | Behaviour |
|---|---|
| 1 | `*target = 0.0` (zero the variable) |
| 2 | `*target = clamp(acc, -1, 1)` (store accumulator) |
| 0x22 | `*target = clamp(acc + *target, -1, 1)` (add and store) |
| 0x23 | `*target = clamp(persist * *target + (1 - persist) * acc, -1, 1)` (tend-store) |
| 0x2d | `*target = clamp(abs(acc), 0, 1)` (store absolute) |

(Source: `decompiled/00421830_FUN_00421830.c` lines 50-126.)

**Important**: opcodes 1, 2, 0x22, 0x23, 0x2d appear in BOTH dispatch arms - class-1 (operating via the operand value) and class-2 (operating via a target pointer). The metadata table at `0x47bbfc` decides which path each opcode actually takes for a given line. The class-2 path is what the external reference calls "store in" / "blank" / "store abs in" etc.

### Control-flow notes

- All jump opcodes (0x30, 0x31, 0x34, 0x43, 0x44) compute `target_PC = round(operand) - 1`. Since the loop then increments `iVar10`, the actual landing line is `round(operand) - 1 + 1 = round(operand)`. The condition `if (target_PC > 0x10) return` means a jump out-of-range terminates execution.
- All jumps are guarded by `if (iVar10 < target_PC)` - they cannot jump backward. There are no loops.
- HALT-class opcodes (0, 0x2e, 0x2f, 0x35..0x38) `return local_c` directly, terminating the program.
- Skip opcodes (4..15) advance PC by an extra 1 via `iVar10 = iVar10 + 1` then fall through to `switchD_00421886_default` which advances by 1 again - net +2.

---

## 4. Parameters indexed by line - the BRN: SETL / SETT semantics

The CAOS commands sent by `SVRuleDlg`:

```
execute\nTARG AGNT %d BRN: SETL %d %d %f          (string at 0x0047b310)
execute\nTARG AGNT %d BRN: SETT %d %d %f          (string at 0x0047b35c)
```

Three integers and a float follow each verb. Mapping (cross-referenced against the external reference, since the actual SETL/SETT handler lives in the engine and is not in this binary):

| Param | Meaning |
|---|---|
| `%d` (1st) | Lobe ID (for SETL) or Tract ID (for SETT) |
| `%d` (2nd) | Line index in the SVRule program - `0..15` |
| `%d` (3rd) | "Field" index within that line. Per the binary, each line stores 4 values (opcode, operand-idx, raw, normalised); however SVRuleDlg's slider format `%s%1.3f` is consistent with editing a **single normalised float**, so this index almost certainly selects opcode/operand-idx/operand-byte, and the `%f` is the new value. |
| `%f` | New value, normalised float (precision 3 decimals - matches the `%s%1.3f` slider format string at `0x47b2d4`) |

**Caveat**: I could not locate the function in this binary that constructs the `BRN: SETL %d %d %f` string from slider events - the format strings at `0x47b310` and `0x47b35c` are not referenced in any decompiled `.c` file I searched. Ghidra appears to have not symbolicated the code path that uses them (probably an MFC dialog message handler emitted as straight machine code without enough context for pattern-matching). The exact semantics of the second `%d` therefore rest on the external reference plus the fact that BRN: SETL expects three integer fields per line in genome encoding (3 bytes per line on disk = 3 indexable fields).

So **the line model the binary supports** is: 16 lines × 3 raw byte fields. The fourth in-memory float (the normalised value) is derived (`raw / 248`) and is not separately addressable.

---

## 5. Lobe SVRule vs Tract SVRule

### Same struct slots, different semantics

Both Lobe and Tract have **two SVRule program regions** at identical offsets:

- `+0x10` - first SVRule (256 bytes, 16 lines × 16 bytes plus 24 bytes scratch)
- `+0x128` - second SVRule (same layout)

Both `Lobe::Read` and `Tract::Read` call `FUN_00424a00(this+0x10, stream)` and `FUN_00424a00(this+0x128, stream)` - they parse two SVRule programs. The struct layout for SVRule storage is uniform across the two component types.

### But the update paths differ

For **Lobes**, `Lobe::Update` (`FUN_004237d0`) executes only `lobe+0x10`:

```c
if (lobe->frozen_at_offset_8 == 0) {
    FUN_00421830(lobe + 0x10, ...);     // run primary SVRule
} else {
    FUN_00424880(neuron);                // zero 32 bytes of neuron state
}
```

I searched all 3,140 decompiled functions for any caller of `FUN_00421830` that passes `something + 0x128` as the program pointer. Three matches: `FUN_00426f20` (Tract::Update - the always-on dendrite SVRule), `FUN_004237d0` does NOT, and the read/write helpers (which don't execute). **The lobe's second SVRule region (`lobe+0x128`) is parsed and serialised but never executed by the binary's update path.**

Plausible explanations (uncertain):
- It is the **initialiser SVRule** that runs once at lobe creation (per the external reference) - the initialiser path lives elsewhere and Ghidra didn't symbolicate it.
- It is **vestigial**: the Lobe and Tract structs share a base layout with two SVRule slots even though Lobes only exercise one in C3.
- It is **driven by a separate code path** the Vat does not include (e.g., genome-construction-time only).

For **Tracts**, both programs are used:

```c
if (tract->flag_at_offset_8 != 0) {
    FUN_00421830(tract + 0x10, ...);    // first SVRule (gated)
}
FUN_00421830(tract + 0x128, ...);       // second SVRule (always)
FUN_00428370(tract, dendrite);          // apply reinforcement deltas to dendrite
```

The first SVRule's gate flag was set in `Tract::Read` from `FUN_0042a0e0(stream, 0, 1)` - a 0-or-1 boolean. In the genome this is the **migration flag** per the external reference. So tract first-SVRule = "migration / per-spike" rule (gated on migration), tract second-SVRule = "every-tick reinforcement" rule (always).

### The `+8` byte: same offset, different meanings (binary finding)

This is a concrete observation worth highlighting. Both Lobe and Tract are `BrainComponent` subclasses; they share the byte at `BrainComponent + 0x8`. The Lobe::Read and Tract::Read both initialise that byte from a single `FUN_0042a0e0(stream, 0, 1)` byte read. **But the Lobe::Update and Tract::Update paths interpret it differently**:

- Lobe `+0x8 == 0` → run the primary SVRule.
- Lobe `+0x8 != 0` → zero the neuron (skip SVRule).
- Tract `+0x8 == 0` → skip the first SVRule.
- Tract `+0x8 != 0` → run the first SVRule (also).

Same offset; opposite polarity per the gating. This is not a bug - it reflects two different uses of a shared `BrainComponent` flag byte. Names worth tentatively assigning: lobe → `frozen_or_clear`, tract → `migration_enabled`.

---

## 6. SVRuleDlg

The recovered evidence for the editor is sparse: only externally visible artefacts (window class, title strings, slider widget, CAOS format strings).

| Address | Artefact |
|---|---|
| `0x0047a430` | `SVRuleDlg::RTTI_Type_Descriptor` |
| `0x0047a438` | `".?AVSVRuleDlg@@"` |
| `0x0047a3a0`, `0x0047a3ac` | Title format `"SV Rule %s"` (two copies - almost certainly one for lobe context, one for tract) |
| `0x0047b288` | Window-class name `"SV Rule Dlg"` |
| `0x0047b294` | Font `"MS Sans Serif"` |
| `0x0047b2a8`, `0x0047b2c4` | Static labels |
| `0x0047b2b0` | Widget class `"msctls_trackbar32"` - confirms **the editor uses Win32 trackbar (slider) controls** to edit the parameters |
| `0x0047b2d4`, `0x0047b2ec` | Display format `"%s%1.3f"` - confirms 3-decimal-place float editing, matching the normalisation of the operand byte |
| `0x0047b2f4`, `0x0047b304` | Lobe-context label formats: `"(L:%s) Lobe: %s"`, `"Lobe: %s "` |
| `0x0047b310` | Lobe set-value command: `"execute\nTARG AGNT %d BRN: SETL %d %d %f"` |
| `0x0047b338`, `0x0047b34c` | Tract-context label formats: `"(T:%s) Tract: %s"`, `"Tract: %s->%s"` |
| `0x0047b35c` | Tract set-value command: `"execute\nTARG AGNT %d BRN: SETT %d %d %f"` |

What this tells us about the user-facing model of an SVRule program: **a fixed grid of trackbar sliders, each editing one normalised float in `[0,1]` to 3 decimals, with the dialog title indicating whether the program is a Lobe SVRule or a Tract SVRule**, and the dialog bound to a single Lobe or Tract by `%s` (component name). Slider movement triggers a CAOS `BRN: SETL/SETT` command to the live engine, identifying line and field.

What we cannot recover from this binary: the actual MFC dialog template (it's in a resource section), the slider-to-line/field mapping, and the opcode-mnemonic display strings (those would be loaded from a `.catalogue` file at runtime - see the `Catalogue` class in [09-class-registry.md](09-class-registry.md)).

---

## 7. Reinforcement and ReinforcementDetails

### `Tract::ReinforcementDetails` is real, with an RTTI Type Descriptor

`0x0047bee0  Tract::ReinforcementDetails::RTTI_Type_Descriptor`
`0x0047bee8  ".?AVReinforcementDetails@Tract@@"`

It is a nested class of `Tract`. Within the Tract struct there are **two** ReinforcementDetails instances - at offsets `+0x2c8` and `+0x2dc` - used by `FUN_00428370` (the after-SVRule reinforcement applier) for two reinforcement channels.

### Fields of ReinforcementDetails (from `FUN_00428400`)

```c
void ReinforcementDetails::Apply(this, float rate, float* target_dendrite_var) {
    if (rate > this->threshold) {                               // *(this+8)
        float delta = (rate - this->threshold) * this->gain;    // *(this+0xc)
        target = clamp(*target + delta, -1, 1);
        *target = target;
    }
}
```

(Source: `decompiled/00428400_FUN_00428400.c`.)

| Offset | Type | Meaning |
|---|---|---|
| `+0x00` | vtable / config metadata | `&PTR_FUN_0046e55c` set in `FUN_00425630` lines 71, 76 |
| `+0x08` | float | reinforcement threshold |
| `+0x0c` | float | reinforcement gain |
| `+0x14` | (struct end) | size = 20 bytes (gap from 0x2c8 to 0x2dc) |

There may be more fields beyond `+0xc` - `FUN_00428400` only reads two - but the gap of 0x14 between the two embedded instances bounds the class to **at most 20 bytes**. Names beyond threshold/gain are uncertain.

### The "reinforcement registers" set by SVRule and consumed by `FUN_00428370`

The SVRule interpreter writes scratch values into a range of slots on the host Tract (see Class-1 opcodes 0x39..0x3e in Section 3):

| Tract offset | Field | Set by | Used by |
|---|---|---|---|
| `+0x2c4` | smoothing rate | opcode 0x2b → `FUN_00424ec0` | opcode 0x2c → `FUN_00424ef0` |
| `+0x2c8..0x2db` | ReinforcementDetails A (channel 1) | (constructor) | `FUN_00428370` first `if` |
| `+0x2cc` | byte: "channel 1 active marker" | opcode 0x3b sets to 1 | `FUN_00428370` first `if` |
| `+0x2d0` | float: channel 1 rate | opcode 0x39 (clamp [-1,1]) | passed to `FUN_00428400` as `rate` |
| `+0x2d4` | float: (unused by `FUN_00428370`) | opcode 0x3a | (read elsewhere) |
| `+0x2d8` | byte: state-index | opcode 0x3b | `FUN_00428370` indexes `tract->0x240` table by it |
| `+0x2dc..0x2ef` | ReinforcementDetails B (channel 2) | (constructor) | `FUN_00428370` second `if` |
| `+0x2e0` | byte: "channel 2 active marker" | opcode 0x3e sets to 1 | `FUN_00428370` second `if` |
| `+0x2e4` | float: (unused by `FUN_00428370`) | opcode 0x3c | |
| `+0x2e8` | float: channel 2 rate | opcode 0x3d (clamp [-1,1]) | passed to `FUN_00428400` as `rate` |
| `+0x2ec` | byte: state-index | opcode 0x3e | `FUN_00428370` indexes `tract->0x240` table by it |

`tract->0x240` is a pointer to a per-tract float table, indexed by the byte state-index, that supplies the `rate` value passed to `ReinforcementDetails::Apply`. Decompilation:

```c
// FUN_00428370 - applies reinforcement after second SVRule
if (tract->channel1_active && dendrite->vars[0] != 0.0f) {
    if (tract->channel1_active) {
        ReinforcementDetails::Apply(
            &tract->RD_A,                                  // tract+0x2c8
            tract->state_table[tract->channel1_state],     // tract+0x240 indexed
            &dendrite->vars[0]);                            // dendrite+0xc
    }
    if (tract->channel2_active) {
        ReinforcementDetails::Apply(
            &tract->RD_B,                                  // tract+0x2dc
            tract->state_table[tract->channel2_state],     // tract+0x240 indexed
            &dendrite->vars[0]);
    }
}
```

(Source: `decompiled/00428370_FUN_00428370.c`.)

### What this means for the brain

The C3 reinforcement model has two channels (probable: STW reinforcement and LTW reinforcement, matching the external reference's "STW" and "LTW" terminology). Each channel has its own `(threshold, gain)` pair. SVRule chooses a per-tick rate (clamped `[-1,1]`) and a state-index (a byte selecting which lookup-table value to consult). After SVRule runs, `FUN_00428370` reads the chosen rate and applies `clamp(dendrite[0] + (rate - threshold) * gain, -1, 1)` for each active channel.

The `BRN: SETD %d %d %d %f` CAOS command (string at `0x0047b4f8`, used by DendriteVarDlg per address `0x0047b524`'s `"%s->%s"` neighbour) correspondingly takes (tract_id, dendrite_index, state_index, value) - the third index addresses the per-state float channels of a dendrite.

---

## 8. Comparison to the external SVRule reference

The external doc (`docs/reference/svrule-brain-complete-reference.md`) describes SVRule based on openc2e source plus community references. Cross-checking that against the Vat binary:

### Where they agree

- **16 lines per program**: confirmed (loop bound 0xf at `0x00421d04`).
- **3 bytes per line on disk**: confirmed (Reader byte counts in `FUN_00424a00`).
- **48 bytes total per program**: confirmed (3 × 16 = 48 on the wire).
- **Operand normalisation = byte / 248**: confirmed exactly (line 23 of `FUN_00424a00`).
- **Operand types include accumulator (0), input neuron (1), dendrite (2), neuron (3), spare neuron (4), random (5), chemical (7), constants 9-15**: all confirmed in the Class-1 dispatch.
- **HALT, conditional skip, arithmetic, min/max, tend, abs/neg, store-in, jump, divide-by-add-input, multiply-by-add-input** opcode families: all present and behaving as the external doc describes (with the same numbering).
- **STW/LTW two-channel reinforcement**: the binary structure confirms two reinforcement channels with `(threshold, gain)` pairs, fed by SVRule writes to `tract+0x2d0` and `tract+0x2e8`.
- **Dendrite has 8 variables, neuron has 8 variables**: implied by the operand-byte 0..7 clamp at `&DAT_0047bd10` for indices that select variable slots, and by the clamp `& 7` in opcodes 0x3f-0x42 (variable preserve/restore).
- **Static persistence-rate register**: confirmed (`local_10` in `FUN_00421830`, set by 0x18, consumed by 0x19 and 0x23 - though the binary only shows it static within a single call, not across calls; "STW relax rate persists across SVRule calls" in the external ref would require checking the engine binary).
- **MSVC LCG random generator**: constants `0x19660d` and `0x3c6ef35f` match exactly.

### Where the binary is more specific than the external doc

- **The fourth float per line in memory** (`raw / 248` precomputed normalisation) is a runtime-only artefact not visible in the genome wire format.
- **Two SVRule programs per Lobe** (the second never executed in this binary) is a layout fact the external doc partially acknowledges (calling them "Initialiser SVRule" and "Update SVRule"). The Vat binary parses both but only runs one.
- **The `+0x8` flag has different polarity for Lobe vs Tract** is a concrete struct observation not captured in the external doc.
- **Reinforcement uses `(threshold, gain)` from a class type `Tract::ReinforcementDetails`** with size ≤ 20 bytes - the external doc names STW/LTW relax rates but doesn't formalise the `ReinforcementDetails` shape.
- **Per-tract state lookup at `tract+0x240`** indexed by a byte from SVRule. The external doc's STW/LTW model doesn't describe this indirection layer.

### Where the binary is less specific than the external doc

- **Opcode names (mnemonics)**: the binary contains *no* opcode-name strings. The mnemonics in the external doc ("blank", "store in", "load from", "if =", "if <>", "tend to", etc.) are presumably loaded from a `.catalogue` file at engine runtime. **All opcode names in this document are descriptive paraphrases of the binary's behaviour, not names from the Vat binary itself.**
- **Operand-index → operand-range table contents**: the binary uses an indexed lookup (`&DAT_0047bd10`) but the actual 16 entries are not enumerated in any decompiled function - only the dispatch behaviour is.
- **Opcode-class table contents**: the 69-entry opcode-class table at `&DAT_0047bbfc` likewise only shows up as an indexed lookup; specific entries aren't enumerated.
- **C1/C2 vs C3/DS history**: the Vat is a C3 tool - no C1/C2 mnemonics or behaviours appear.
- **Unimplemented opcodes (37, 38, 39, 40, 41, 42, 57-62)**: these *are* unhandled in the binary's `FUN_00421830` (they fall through `switchD_00421886_default`), but the binary doesn't tell us they were *intended* to be implemented. The external doc's claim that they are placeholders is not contradicted but also not corroborated by the binary alone.

### Where they disagree

I found no genuine contradictions. The binary is consistent with the external reference on every point that I could check.

---

## 9. Open questions

1. **Why is `lobe+0x128` parsed but never executed?** Three hypotheses (initialiser code path elsewhere; vestigial layout; engine-only code path). Resolving this requires examining the engine binary, not the Vat.

2. **What are the contents of the opcode-class table (`&DAT_0047bbfc`, 69 entries × 4 bytes)?** Each entry is 0/1/2 selecting a dispatch arm. Determining which opcode falls into which arm requires reading the binary's `.data` section - not available in the decompiled `.c` files. This would let us validate the catalogue in Section 3 against the binary's intended arm for each opcode.

3. **What are the contents of the operand-index range table (`&DAT_0047bd10`, 16 entries × 4 bytes)?** Same situation. Likely indices 1-4 (variable selectors) hold value 2 (range 0..7), and 5-15 hold something else (range 0..255), but this is inferred not enumerated.

4. **Where is the `BRN: SETL/SETT` slider-callback function?** The format strings at `0x47b310` and `0x47b35c` are not referenced in any decompiled function. Either Ghidra failed to identify the call site, or the format string is pulled from a resource table indirectly. Resolving this would let us know exactly how SVRuleDlg maps slider position to (line, field, value).

5. **What does opcode `0x2a` actually mean?** It is a class-0 opcode that compares `*param_3` and `*param_4`, sets a "register" bit, and does some side effect. Names in external community references include "winner-takes-all comparison" but this is not certain. The decompiled body (line 41-43) is short and clear about the behaviour but not the intent.

6. **Are class-1 and class-2 opcode dispatches mutually exclusive?** Opcodes 1, 2, 0x22, 0x23, 0x2d appear in BOTH switch arms in `FUN_00421830`. The opcode-class table chooses which arm runs. Without enumerating the table, I cannot say for sure which arm any specific opcode actually takes - though the external reference's behaviour for "blank" (1) and "store in" (2) is consistent with class-2.

7. **Does `Tract::ReinforcementDetails` have fields beyond `(threshold, gain)`?** The 20-byte size leaves room for two more 4-byte fields. `FUN_00428400` reads only the first two; other fields might be touched by code paths not yet examined.

8. **What does `tract->0x240` (the per-tract state float table) look like?** It's indexed by SVRule's state-index byte (0..255) and yields a float fed to ReinforcementDetails::Apply as the `rate`. Where it's allocated and what its size is is not visible in the functions I examined.

9. **Are there `SVRule` virtual methods we should know about?** The RTTI Type Descriptor exists but no `vftable` symbol was extracted by Ghidra (only `type_info::vftable` at `0x46fb78`). Without the vtable we don't know if `SVRule` has Read/Write virtuals - the inline reader/writer functions (`FUN_00424a00`/`FUN_00424b30`) suggest non-virtual file I/O.

---

## Cross-references

- `decompiled/00421830_FUN_00421830.c` - `SVRule::Execute` (the interpreter), 2604 bytes
- `decompiled/00424a00_FUN_00424a00.c` - `SVRule::Read` (byte-stream)
- `decompiled/00424aa0_FUN_00424aa0.c` - `SVRule::Read` (archive-mode)
- `decompiled/00424b30_FUN_00424b30.c` - `SVRule::Write` (archive-mode)
- `decompiled/00424be0_FUN_00424be0.c` - `SVRule::Write` (byte-stream)
- `decompiled/00423490_FUN_00423490.c` - `Lobe::Read`
- `decompiled/004237d0_FUN_004237d0.c` - `Lobe::Update`
- `decompiled/00425630_FUN_00425630.c` - `Tract::Read`
- `decompiled/00426290_FUN_00426290.c` - `Tract::Read` (variant for archive load)
- `decompiled/00426f20_FUN_00426f20.c` - `Tract::Update`
- `decompiled/00428370_FUN_00428370.c` - Reinforcement applier (post-SVRule)
- `decompiled/00428400_FUN_00428400.c` - `Tract::ReinforcementDetails::Apply`
- `decompiled/00424cc0_FUN_00424cc0.c` through `decompiled/00424ef0_FUN_00424ef0.c` - reinforcement-write helpers (opcodes 0x2b..0x3e)
- `decompiled/0042a0e0_FUN_0042a0e0.c` - clamping byte-stream reader

Tables in `.data`:
- `0x0047bbfc` - opcode-class table (69 × 4 bytes)
- `0x0047bd10` - operand-index-range table (16 × 4 bytes)
- `0x00481248` - engine LCG random seed (MSVC `rand` constants)
- `0x00480f3c` - zero-array constant (used as null fallback for unused SVRule params)
- `0x00480e9c` - archive-format flag (1.0f selects byte-stream vs float-stream layout)
