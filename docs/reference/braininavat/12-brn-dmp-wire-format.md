# Brain in a Vat: BRN: DMP* Wire Format

Catalogue of the byte-level layout for every `BRN: DMP*` and `BRN: SET*` CAOS command response, reconstructed from the original Creature Labs C3 engine source. Companion to `03-ipc-protocol.md` (transport envelope) and `04-data-model.md` (Vat in-memory structs); this document fills the gap between them: what bytes the engine actually emits between `execute\nTARG AGNT %d BRN: DMP*` going down and the Vat's `Brain` / `Lobe` / `Tract` constructors consuming the result.

---

## 0. Source of truth

The brief assumed `BRN: DMP*` lives in our openc2e fork. **It does not.** openc2e has no implementation, no stub, and no command-table entry for any `BRN:` subcommand:

- Searched all `openc2e/src/openc2e/caos/caosVM_*.cpp` for `BRN`, `brn`, `DMPB`, `DMPL`, `DMPT`, `DMPN`, `DMPD`, `SETL`, `SETT`, `SETN`, `SETD`, `END DUMP` - no matches.
- The only `DMP` token in the openc2e tree is in `caosVM_motion.cpp` (an unrelated motion command).
- The build artefact `openc2e/build64/generated/commandinfo.json` enumerates 810 CAOS commands; zero contain `BRN` in their match or name.
- `openc2e/src/openc2e/creatures/c2eBrain.cpp` has Brain logic (lobe loaders, dendrite migration) but no dump path; the only `Dump` symbol is `c2eTract::dump()` at line 187, a debug-print helper unrelated to the wire protocol.

Authoritative implementation lives at `<PROJECT_ROOT>/C3sourcecode/engine/` - the recovered Creature Labs C3 engine source archive. All citations in this document are to that path. Any future openc2e port (or Python responder) of `BRN: DMP*` must reproduce these bytes; nothing in the openc2e tree currently anchors the format.

The Vat-side reverse-engineering in `04-data-model.md` and `10-svrule-engine.md` describes the Vat's *reader* contract. This document describes the engine's *writer* contract. Cross-checks confirm the two halves match for V1.0; V1.1 differences are noted in §9.

---

## 1. Where each command is implemented

CAOS dispatch table (`C3sourcecode/engine/Caos/CAOSTables.cpp:273-281`) registers all nine `BRN:` subcommands under category `categoryBrain`. The `OpSpec` ordering (subcommand index → name) is:

| Idx | Name | Args | Description |
|---:|---|---|---|
| 0 | `SETN` | `iiif` | `lobe_number neuron_number state_number new_value` |
| 1 | `SETD` | `iiif` | `tract_number dendrite_number weight_number new_value` |
| 2 | `SETL` | `iif`  | `lobe_number line_number new_value` |
| 3 | `SETT` | `iif`  | `tract_number line_number new_value` |
| 4 | `DMPB` | (none) | "Dumps the sizes of the binary data dumps for current lobes and tracts." |
| 5 | `DMPL` | `i`    | `lobe_number` |
| 6 | `DMPT` | `i`    | `tract_number` |
| 7 | `DMPN` | `ii`   | `lobe_number neuron_number` |
| 8 | `DMPD` | `ii`   | `tract_number dendrite_number` |

Note: `SETL` and `SETT` take **three** integer fields plus a float (`iif`), not four (`iiif`) as the Vat's reverse-engineered format strings at `0047b310` / `0047b35c` suggested in `03-ipc-protocol.md` §3.2. The Vat doc's `BRN: SETL %d %d %d %f` is a binary-string artefact; the engine handler reads `iif`.

Dispatch entry point and per-subcommand handler addresses (`C3sourcecode/engine/Caos/CreatureHandlers.cpp`):

| CAOS verb | Handler | Source |
|---|---|---|
| `BRN:` (dispatch) | `CreatureHandlers::Command_BRN` | `CreatureHandlers.cpp:688-707` |
| `BRN: SETN` | `CreatureHandlers::SubCommand_BRN_SETN` | `CreatureHandlers.cpp:716-724` |
| `BRN: SETD` | `CreatureHandlers::SubCommand_BRN_SETD` | `CreatureHandlers.cpp:727-735` |
| `BRN: SETL` | `CreatureHandlers::SubCommand_BRN_SETL` | `CreatureHandlers.cpp:738-745` |
| `BRN: SETT` | `CreatureHandlers::SubCommand_BRN_SETT` | `CreatureHandlers.cpp:748-755` |
| `BRN: DMPB` | `CreatureHandlers::SubCommand_BRN_DMPB` | `CreatureHandlers.cpp:710-713` |
| `BRN: DMPL` | `CreatureHandlers::SubCommand_BRN_DMPL` | `CreatureHandlers.cpp:758-762` |
| `BRN: DMPT` | `CreatureHandlers::SubCommand_BRN_DMPT` | `CreatureHandlers.cpp:765-769` |
| `BRN: DMPN` | `CreatureHandlers::SubCommand_BRN_DMPN` | `CreatureHandlers.cpp:772-779` |
| `BRN: DMPD` | `CreatureHandlers::SubCommand_BRN_DMPD` | `CreatureHandlers.cpp:782-788` |

Each handler is a thin shim that calls a `Brain::Dump*` / `Brain::Set*` member on the `TARG` creature's brain object and feeds bytes directly into `vm.GetOutStream()`. The actual serialisation logic lives one level deeper:

| Brain method | Source |
|---|---|
| `Brain::DumpSpec` | `Brain.cpp:827-839` |
| `Brain::DumpLobe` | `Brain.cpp:851-859` |
| `Brain::DumpTract` | `Brain.cpp:870-878` |
| `Brain::DumpNeuron` | `Brain.cpp:890-900` |
| `Brain::DumpDendrite` | `Brain.cpp:912-921` |
| `Lobe::DumpLobe` | `Lobe.cpp:566-592` |
| `Lobe::DumpNeuron` | `Lobe.cpp:603-612` |
| `Lobe::DumpSize` | `Lobe.cpp:620-623` |
| `Tract::DumpTract` | `Tract.cpp:997-1025` |
| `Tract::DumpDendrite` | `Tract.cpp:1037-1049` |
| `Tract::DumpSize` | `Tract.cpp:1058-1061` |
| `SVRule::Dump` | `SVRule.cpp:250-260` |

`SetNeuronState`, `SetDendriteWeight`, `SetLobeSVFloat`, `SetTractSVFloat` live on `Brain` and forward to `Lobe::SetNeuronState` (`Lobe.cpp:540-545`), `Tract::SetDendriteWeight`, `Lobe::SetSVFloat` (`Lobe.cpp:555-558`), and `Tract::SetSVFloat` (`Tract.cpp:986-989`) respectively; the `Lobe::SetSVFloat` / `Tract::SetSVFloat` paths terminate at `SVRule::SetFloat` (`SVRule.cpp:305-312`).

---

## 2. Endianness, alignment, packing

All `Dump*` methods write through `BrainIO.h`'s template helper:

```cpp
// BrainIO.h:6-9
template <class T>
static inline void WriteDesc(T *t, std::ostream &out) {
    out.write((char*)t, sizeof(T));
}
```

Implications:

- **Endianness:** native byte order of the originating MSVC build. C3 was 32-bit x86 - **little-endian** for every `int` and `float` field.
- **Alignment / padding:** none. `WriteDesc<int>` writes 4 bytes, `WriteDesc<float>` writes 4 bytes, `WriteDesc<bool>` writes 1 byte (MSVC `bool` is single-byte). The wire stream is the byte concatenation in dump order with **no padding between fields**.
- **No length prefixes** on per-entity blocks; the Vat must know how many bytes to expect from prior `DMPB` output (per-lobe and per-tract sizes are reported there, with the proviso of the `DumpSize` bugs in §11).
- **`(char)0` separators in DMPB only.** DMPB intersperses ASCII integers with single NUL bytes (see §3). DMPL/DMPT/DMPN/DMPD are pure binary blobs (with embedded `0x00` bytes inside `int` and `float` fields); they end with the literal byte sequence `0x00 'E' 'N' 'D' ' ' 'D' 'U' 'M' 'P'`.
- **Mixed text-and-binary discrepancy with the Vat IPC doc.** `03-ipc-protocol.md` §2.2 claims "the Vat copies bytes until it hits NUL when reading". That can only be true for DMPB. For DMPL/DMPT/DMPN/DMPD the Vat must rely on the length field at `view+0x0C` (set by the engine) rather than NUL-termination, because binary payloads contain arbitrary `0x00` bytes inside ints and floats. Treat the Vat doc's "strlen on response" remark as accurate for ASCII responses (WNAM, GTOS, CAGE, DMPB) and inaccurate for binary brain dumps.

`SVRuleVariables` is `typedef float[8]`, so `sizeof(SVRuleVariables) = 32` bytes (`BrainConstants.h:4-5`). Where the dump code does `out.write((char*)states, sizeof(SVRuleVariables))`, it emits 32 contiguous little-endian floats - no per-element framing.

---

## 3. DMPB response layout

`Brain::DumpSpec` - `Brain.cpp:827-839`:

```cpp
void Brain::DumpSpec(std::ostream& out)
{
    out << myLobes.size() << (char)0;
    out << myTracts.size() << (char)0;

    for(int l = 0; l != myLobes.size(); l++)
        out << myLobes[l]->DumpSize() << (char)0;

    for(int t = 0; t != myTracts.size(); t++)
        out << myTracts[t]->DumpSize() << (char)0;

    out << "END DUMP";
};
```

`out << int_value` invokes `std::ostream::operator<<(int)` which formats the integer as **ASCII decimal digits** (no leading sign for unsigned, no padding). `(char)0` writes a single NUL byte. So the entire DMPB response is **ASCII text with NUL separators**.

Pseudo-format:

```
"<numLobes>"     0x00
"<numTracts>"    0x00
"<lobe[0].DumpSize()>"   0x00
"<lobe[1].DumpSize()>"   0x00
... numLobes total ...
"<tract[0].DumpSize()>"  0x00
... numTracts total ...
"END DUMP"
```

Concrete example (12 lobes, 8 tracts, lobe[0] size 1234, tract[0] size 5678, ...):

```
"12" 00 "8" 00 "1234" 00 ... 00 "5678" 00 ... "END DUMP"
```

There is **no trailing NUL** after `END DUMP` - the engine emits exactly the 8 ASCII bytes `E N D space D U M P`. This is the key for the Vat's version probe (`03-ipc-protocol.md` §3.1, fixed at offset `FUN_00403200:558-582`): if the response ends with the byte sequence `END DUMP\0` (where the `\0` is the request-buffer's terminating NUL added by the IPC layer, not by `DumpSpec`) the Vat selects V1.0; if `END DUMP V1.1\0` it selects V1.1. **This source emits only V1.0** (see §9).

### Byte-offset table (concrete encoding)

DMPB is variable-length text, so absolute offsets depend on integer string widths. Logical structure:

| Field | Bytes | Notes |
|---|---|---|
| `numLobes_decimal` | `strlen(itoa(numLobes))` | ASCII digits |
| separator | 1 | `0x00` |
| `numTracts_decimal` | `strlen(itoa(numTracts))` | ASCII digits |
| separator | 1 | `0x00` |
| `lobe[i].DumpSize()_decimal` × numLobes | variable | ASCII digits, each followed by `0x00` |
| `tract[t].DumpSize()_decimal` × numTracts | variable | ASCII digits, each followed by `0x00` |
| sentinel | 8 | literal `END DUMP` |

### Per-lobe DumpSize (the value reported in DMPB)

`Lobe::DumpSize` - `Lobe.cpp:620-623`:

```cpp
int Lobe::DumpSize()
{
    return 40+(7*SVRule::length)+(9*myNeurons.size());
};
```

With `SVRule::length = 16` (`SVRule.h:61`): `40 + 7*16 + 9*N = 152 + 9*N` for a lobe of N neurons.

**This is wrong.** The actual `Lobe::DumpLobe` payload (counted in §4) is:

- 40 bytes of fixed header (10 × `int`)
- 7 × 16 = 112 bytes for one SVRule
- (4 + 4 + 32) × N = 40 × N bytes for neurons

Total actual = `152 + 40*N`. The `DumpSize()` formula reports `9*N` instead of `40*N`. The discrepancy is a long-standing C3 engine bug - the Vat doc's "Lobe too big for transfer" / "Require transfer buffer of: %d" error path (`03-ipc-protocol.md` §5) avoids the bug because it compares the **post-transmission response length** against the IPC capacity, not `DumpSize()`. Tools that consume `DumpSize()` directly (e.g., to pre-allocate a buffer of exactly that size) will under-allocate by `31*N` bytes per lobe.

### Per-tract DumpSize

`Tract::DumpSize` - `Tract.cpp:1058-1061`:

```cpp
int Tract::DumpSize()
{
    return 36+(7*(SVRule::length*2))+4+(16*myDendrites.size());
};
```

= `36 + 224 + 4 + 16*D = 264 + 16*D` for a tract of D dendrites.

Actual `Tract::DumpTract` payload (§5):

- 36 bytes fixed Tract header (see §5)
- 7 × 16 × 2 = 224 bytes for two SVRules (Tract dumps both `myInitRule` and `myUpdateRule`)
- 4 bytes for dendrite count
- (4 + 4 + 4 + 32) × D = 44 × D bytes for dendrites

Total actual = `264 + 44*D`. Reported = `264 + 16*D`. Same kind of bug: under-reports by `28*D` bytes.

A responder reproducing the C3 wire format faithfully must replicate these wrong values in DMPB so the Vat's expectations align with what the original engine sent. A clean responder may emit corrected sizes, at the cost of breaking parity with engines that ship the C3 bug.

---

## 4. DMPL response layout

`Brain::DumpLobe` (`Brain.cpp:851-859`) → `Lobe::DumpLobe` (`Lobe.cpp:566-592`) → trailing `(char)0 "END DUMP"`.

The engine sequence is exactly:

```cpp
WriteDesc(&myIdInList, out);          // int    4 bytes
WriteDesc(&myWinningNeuronId, out);   // int    4 bytes
WriteDesc(&myToken, out);             // TOKEN  4 bytes (4-char ID)
WriteDesc(&myUpdateAtTime, out);      // int    4 bytes

WriteDesc(&myX, out);                 // int    4 bytes
WriteDesc(&myY, out);                 // int    4 bytes
WriteDesc(&myWidth, out);             // int    4 bytes
WriteDesc(&myHeight, out);            // int    4 bytes
WriteDesc(&myColour[0], out);         // int    4 bytes
WriteDesc(&myColour[1], out);         // int    4 bytes
WriteDesc(&myColour[2], out);         // int    4 bytes

WriteDesc(&myTissueId, out);          // int    4 bytes

myUpdateRule.Dump(out);               // 16 lines × 7 bytes = 112 bytes (see §8)

for n in 0..myNeurons.size()-1:       // 40 bytes per neuron (see §6)
    WriteDesc(&myNeuronInput[n], out);             // float 4 bytes
    WriteDesc(&myNeurons[n]->idInList, out);       // int   4 bytes
    out.write((char*)states, sizeof(SVRuleVariables));  // 8 floats = 32 bytes

// then Brain::DumpLobe appends:
out << (char)0 << "END DUMP";
```

Pseudo-C struct (packed, little-endian):

```c
struct __attribute__((packed)) DMPL_Response {
    // ----- Lobe header (40 bytes total) -----
    int32  myIdInList;          // sequential lobe index (0..numLobes-1)
    int32  myWinningNeuronId;   // current winning neuron index
    char   myToken[4];          // 4-char ASCII type tag (TOKEN type)
    int32  myUpdateAtTime;      // tick timing parameter

    int32  myX, myY;            // grid origin (vat-tool view coordinates)
    int32  myWidth, myHeight;   // grid dimensions; numNeurons = W * H
    int32  myColour[3];         // R, G, B (each int, full range)

    int32  myTissueId;          // biochemistry tissue index

    // ----- One SVRule (112 bytes) -----
    SVRuleEntry  myUpdateRule[16];  // 16 × 7-byte lines (see §8)

    // ----- Neurons (40 × W*H bytes) -----
    NeuronBlock  neurons[W * H];    // see DMPL_Neuron below

    // ----- Sentinel (9 bytes) -----
    uint8  separator;           // 0x00
    char   end_dump[8];         // "END DUMP"
};

struct __attribute__((packed)) NeuronBlock {  // 40 bytes
    float  neuronInput;         // myNeuronInput[n]
    int32  idInList;            // neuron index in lobe
    float  states[8];           // SVRuleVariables (V0..V7)
};
```

Total response bytes = `40 + 112 + 40*W*H + 1 + 8 = 161 + 40*N`.
DMPB-reported size for the same lobe = `152 + 9*N` (under by `9 + 31*N`; see §3).

### Field semantics (cross-checked with `Lobe::Lobe(istream&)` reader at `Lobe.cpp:140-192`)

The reader consumes fields in identical order. `myToken` is the `TOKEN` type (4-byte ID); after reading, `Lobe::Lobe` calls `Ezinekot(myToken)` to expand it into the 5-char `myName` array (`Lobe.cpp:169`). On the wire it's just 4 bytes interpreted by `WriteDesc<TOKEN>` as `sizeof(TOKEN) = 4`.

`myWidth * myHeight` is validated `> 0` and `<= MAX_NEURONS_PER_LOBE = 255*255 = 65025` (`BrainConstants.h:10`, `Lobe.cpp:171-175`). This matches the Vat's `< 0xfe01 = 65025` clamp (`04-data-model.md` §3 "Constraint").

### One SVRule in DMPL, not two

`Lobe::DumpLobe` emits exactly **one** SVRule (`myUpdateRule.Dump(out)` at `Lobe.cpp:587`). The Vat reverse-engineering's claim of two SVRule slots per Lobe (`04-data-model.md` §3 "Two SVRule slots", `10-svrule-engine.md` §5) describes the in-memory layout of `BrainComponent` (which has both `myInitRule` and `myUpdateRule` from the genome), not the DMPL wire format. The wire format dumps only the update rule because `Lobe::DoUpdate` only ever runs `myUpdateRule` for lobes (`Lobe.cpp:250-253`); the init rule is consumed at genome-load time and not re-dumped. (Tracts dump both - see §5.)

Vat-side observation: `FUN_00424aa0` (Vat's archive-mode SVRule reader) reads two slots back-to-back when in V1.1 mode. That implies the V1.1 engine dumps both slots; this V1.0 source dumps only one. Branch on §9 for behaviour.

---

## 5. DMPT response layout

`Brain::DumpTract` (`Brain.cpp:870-878`) → `Tract::DumpTract` (`Tract.cpp:997-1025`) → `(char)0 "END DUMP"`.

```cpp
WriteDesc(&myIdInList, out);                                // int   4 bytes
WriteDesc(&myUpdateAtTime, out);                            // int   4 bytes

// Source attachment block (13 bytes)
WriteDesc(mySrc.lobe->GetPointerToIdInList(), out);         // int   4 bytes  (src lobe index)
WriteDesc(&mySrc.neuronRangeToUse.min, out);                // int   4 bytes  (src range MIN)
WriteDesc(&mySrc.neuronRangeToUse.min, out);                // int   4 bytes  *** writes .min AGAIN ***
out.put((char&)mySrc.noOfDendritesPerNeuronOnEachPass);     // byte  1 byte

// Destination attachment block (13 bytes)
WriteDesc(myDst.lobe->GetPointerToIdInList(), out);         // int   4 bytes  (dst lobe index)
WriteDesc(&myDst.neuronRangeToUse.min, out);                // int   4 bytes  (dst range MIN)
WriteDesc(&myDst.neuronRangeToUse.min, out);                // int   4 bytes  *** writes .min AGAIN ***
out.put((char&)myDst.noOfDendritesPerNeuronOnEachPass);     // byte  1 byte

// Flags (2 bytes, MSVC bool = 1 byte each)
WriteDesc(&myDendritesAreRandomlyConnectedAndMigrate, out); // bool  1 byte
WriteDesc(&myNoOfDendritesPerNeuronIsRandomUpToSpecifiedUpperBound, out); // bool 1 byte

// Two SVRules (224 bytes)
myInitRule.Dump(out);                                       // 16 × 7 = 112 bytes
myUpdateRule.Dump(out);                                     // 16 × 7 = 112 bytes

// Dendrite count
int noDendrites = myDendrites.size();
WriteDesc(&noDendrites, out);                               // int   4 bytes

// Per-dendrite block (44 bytes each, see §7)
for d in 0..noDendrites-1:
    DumpDendrite(d, out);

// Trailing sentinel from Brain::DumpTract
out << (char)0 << "END DUMP";
```

Total wire bytes: `4+4 + 13 + 13 + 2 + 224 + 4 + 44*D + 1 + 8 = 273 + 44*D`.

Pseudo-C struct:

```c
struct __attribute__((packed)) DMPT_Response {
    int32  myIdInList;
    int32  myUpdateAtTime;

    int32  src_lobe_idx;
    int32  src_neuronRange_min;
    int32  src_neuronRange_min_DUPLICATE;   // BUG: should be .max - see §11
    uint8  src_noOfDendritesPerNeuronOnEachPass;

    int32  dst_lobe_idx;
    int32  dst_neuronRange_min;
    int32  dst_neuronRange_min_DUPLICATE;   // BUG: should be .max
    uint8  dst_noOfDendritesPerNeuronOnEachPass;

    uint8  dendritesAreRandomlyConnectedAndMigrate;        // bool
    uint8  noOfDendritesPerNeuronIsRandomUpToUpperBound;   // bool

    SVRuleEntry  myInitRule[16];     // 112 bytes
    SVRuleEntry  myUpdateRule[16];   // 112 bytes

    int32  noDendrites;

    DendriteBlock  dendrites[noDendrites];  // 44 bytes each

    uint8  separator;       // 0x00
    char   end_dump[8];     // "END DUMP"
};
```

The Vat reader at `04-data-model.md` §4 expects `min, max` for each range. **A C3-engine wire dump always reports `max == min` because of the duplicated write** (see §11). The Vat reader doesn't notice the bug - it just stores both values into `+0x26c, +0x270` (source) and `+0x290, +0x294` (dest) and passes them through to `InitNeuronLists()`, which iterates over the range. Tracts thus appear to have one-neuron source and one-neuron destination ranges in the Vat's view, but the engine's internal range (read from disk genome via `Tract::Read`) is correct because that path uses the full archive serialiser, not the DMP* wire path.

Cross-reference with the `Tract::Tract(istream&)` reader at `Tract.cpp:235-300`:

```cpp
ReadDesc(&mySrc.neuronRangeToUse.min, in);
ReadDesc(&mySrc.neuronRangeToUse.max, in);  // <-- READS MAX ON THIS SIDE
```

The reader consumes 13 bytes per attachment block (4+4+4+1) expecting `min, max, byte`. The writer emits 13 bytes per attachment block but with `min, min, byte`. The byte-count is consistent so the protocol doesn't desync, but the second field is garbage from the reader's perspective.

### Tract attachment offset note

`mySrc.lobe->GetPointerToIdInList()` returns `&BrainComponent::myIdInList` (`BrainComponent.h:37`). `WriteDesc(int*)` derefs and writes the int. So the wire field is the **lobe index** in `Brain::myLobes`, not a pointer.

---

## 6. DMPN response layout

`Brain::DumpNeuron` (`Brain.cpp:890-900`) → `Lobe::DumpNeuron` (`Lobe.cpp:603-612`) → `(char)0 "END DUMP"`.

```cpp
bool Lobe::DumpNeuron(int n, std::ostream& out)
{
    if(n < 0 || n > myNeurons.size()-1)
        return false;

    WriteDesc(&myNeuronInput[n], out);                          // float 4
    WriteDesc(&myNeurons[n]->idInList, out);                    // int   4
    out.write((char*)(myNeurons[n]->states), sizeof(SVRuleVariables));  // 32
    return true;
};
```

Pseudo-C struct:

```c
struct __attribute__((packed)) DMPN_Response {
    float  neuronInput;     // current input being accumulated for this neuron
    int32  idInList;        // sequential index of this neuron within its lobe
    float  states[8];       // V0..V7 - the 8 SVRule variables
    uint8  separator;       // 0x00
    char   end_dump[8];     // "END DUMP"
};
```

Total = 40 + 9 = 49 bytes. The 40-byte payload matches the per-neuron block embedded inside DMPL (§4); a DMPN response is exactly **one** of those neuron blocks, framed with the trailing sentinel.

Out-of-range index returns false from `Lobe::DumpNeuron`, which propagates back up to `CreatureHandlers::SubCommand_BRN_DMPN` and triggers `vm.ThrowRunError(CAOSMachine::sidCouldNotDumpNeurone)` (`CreatureHandlers.cpp:777-778`). On the wire, a CAOS run-time error becomes a non-zero status in `view+0x08`, surfacing to the Vat as `Could not download brain.\nDisconnected.` (`03-ipc-protocol.md` §5).

The `states[8]` array decodes as the SVRule neuron variables `STATE_VAR, INPUT_VAR, OUTPUT_VAR, THIRD_VAR, FOURTH_VAR, FIFTH_VAR, SIXTH_VAR, NGF_VAR` per `SVRule.h:19-28`. This binding is engine-internal; the Vat catalogues map them to display names via `Brain Lobe Neuron Names`.

---

## 7. DMPD response layout

`Brain::DumpDendrite` (`Brain.cpp:912-921`) → `Tract::DumpDendrite` (`Tract.cpp:1037-1049`) → `(char)0 "END DUMP"`.

```cpp
bool Tract::DumpDendrite(int d, std::ostream& out)
{
    if(d < 0 || d > myDendrites.size()-1)
        return false;

    WriteDesc(&myDendrites[d]->idInList, out);             // int 4
    WriteDesc(&myDendrites[d]->srcNeuron->idInList, out);  // int 4 (neuron idx in src lobe)
    WriteDesc(&myDendrites[d]->dstNeuron->idInList, out);  // int 4 (neuron idx in dst lobe)
    out.write((char*)(myDendrites[d]->weights), sizeof(SVRuleVariables));  // 32

    return true;
};
```

Pseudo-C struct:

```c
struct __attribute__((packed)) DMPD_Response {
    int32  idInList;            // sequential dendrite index within tract
    int32  src_neuron_idx;      // neuron index in src lobe (resolves via tract.src_lobe.neurons[i])
    int32  dst_neuron_idx;      // neuron index in dst lobe
    float  weights[8];          // SVRule dendrite vars: WEIGHT_SHORTTERM_VAR, WEIGHT_LONGTERM_VAR,
                                //   SECOND..SIXTH_DENDRITE_VAR, STRENGTH_VAR
    uint8  separator;           // 0x00
    char   end_dump[8];         // "END DUMP"
};
```

Total = 44 + 9 = 53 bytes. The 44-byte payload matches the per-dendrite block embedded inside DMPT (§5).

Variable names per `SVRule.h:30-39`:

| Index | Name |
|---:|---|
| 0 | `WEIGHT_SHORTTERM_VAR` |
| 1 | `WEIGHT_LONGTERM_VAR` |
| 2 | `SECOND_DENDRITE_VAR` |
| 3 | `THIRD_DENDRITE_VAR` |
| 4 | `FOURTH_DENDRITE_VAR` |
| 5 | `FIFTH_DENDRITE_VAR` |
| 6 | `SIXTH_DENDRITE_VAR` |
| 7 | `STRENGTH_VAR` |

These are the canonical C3 ST/LT-weight + strength variables. Reinforcement opcodes (§3 of `10-svrule-engine.md`) write back to `weights[WEIGHT_SHORTTERM_VAR]` (`Tract.cpp:1095, 1100`).

There is one notable bug in `Brain::DumpDendrite`'s bounds check at `Brain.cpp:914`:

```cpp
if(t < 0 || t > myLobes.size()-1)   // checks myLobes, should be myTracts
    return false;
```

The check uses `myLobes.size()` even though `t` is a tract index. This means DMPD with a valid tract index >= `myLobes.size()` returns false even if the tract exists. In practice C3 brains have similar lobe and tract counts so the bug rarely matters; a faithful responder should mirror it.

---

## 8. SVRule.Dump byte format (used by DMPL §4 and DMPT §5)

`SVRule::Dump` - `SVRule.cpp:250-260`:

```cpp
void SVRule::Dump(std::ostream& out)
{
    for (int i=0; i<length; i++) {              // length = 16
        SVRuleEntry& e = myRule[i];
        out.put(e.opCode);                      // 1 byte
        out.put(e.operandVariable);             // 1 byte
        out.put(e.arrayIndex);                  // 1 byte
        WriteDesc(&e.floatValue, out);          // 4 bytes (float)
    }
};
```

Per-line wire layout (7 bytes):

```c
struct __attribute__((packed)) SVRuleEntry_wire {
    uint8  opCode;            // 0..68 (per FUN_00421830 dispatch in 10-svrule-engine.md §3)
    uint8  operandVariable;   // 0..15 (operand-class selector)
    uint8  arrayIndex;        // 0..7 if operandVariable selects a variable slot, else 0..255
    float  floatValue;        // little-endian IEEE-754, normalised in [-1, +1]
};
```

A program is `16 * 7 = 112 bytes`. There is no padding between lines; opcode bytes are emitted sequentially and the float is packed immediately after (so `out.put(arrayIndex)` writes byte at offset 2, `WriteDesc(&floatValue)` writes bytes at offsets 3..6 of each line).

### Reconciling with the Vat reverse-engineering

`10-svrule-engine.md` §2 describes two on-disk formats: 3 bytes/line ("byte-stream") and 4-floats-via-archive ("verbose"). The C3 source confirms the 3-bytes-plus-1-float = 7 bytes/line layout matches the Vat's `FUN_00424aa0` reader (`10-svrule-engine.md` table at §2.4: "3 bytes via `FUN_004251a0` ... plus 1 float" for V1.0). The Vat reverse-engineering's "3 bytes per line" claim (`04-data-model.md` §2 "SVRule sub-object: 16 rows × 16 bytes per row = 256 bytes") was reading the 16-byte **in-memory** struct (4 floats: opcode, operand-var, array-index, normalised-value) as if it were the wire format. The wire format is 7 bytes; the float is the third operand decoded back from the genome's 1-byte normalised representation but transmitted full-precision in DMPL/DMPT.

`SVRule::SetFloat(int entryNo, float value)` (`SVRule.cpp:305-312`) clamps `entryNo` to `0..length-1` (i.e. 0..15) and `value` to `[-1, +1]` and stores it directly into `myRule[entryNo].floatValue`. So `BRN: SETL` and `BRN: SETT` only touch the `floatValue` field of one line - the opcode, operand-variable, and array-index bytes are not editable via the wire (they are baked into the genome).

---

## 9. V1.0 vs V1.1

This C3 source emits **V1.0 only**.

Evidence:

- `Brain::DumpSpec` writes the literal string `END DUMP` (no `V1.1` suffix) at `Brain.cpp:838`.
- `Brain::DumpLobe`, `DumpTract`, `DumpNeuron`, `DumpDendrite` all append `(char)0 "END DUMP"` - no version branch (`Brain.cpp:857, 876, 898, 919`).
- No string `"V1.1"` exists anywhere in `C3sourcecode/engine/Creature/Brain/`.
- `Lobe::DumpLobe` dumps **one** SVRule (`myUpdateRule` only); the Vat's V1.1 reader path expects **two** SVRules per lobe.
- The persistence-archive code path (`CreaturesArchive`-based, used for snapshot/genome files) does have a `version >= 3` branch (`Brain.cpp:780`, `Lobe.cpp:486`, `Tract.cpp:889`, `SVRule.cpp:228`, etc.) but that is the on-disk archive format, not the DMP* wire format.

### V1.1 differences (from Vat-side reverse engineering)

The Vat (`Vat_1.9.exe`) probes for both footers and selects format constant `0x3f8ccccd` (≈ 1.1f) when it sees `END DUMP V1.1` (`03-ipc-protocol.md` §3.1, fixed at `FUN_00403200:558-582`). The Vat's V1.1 reader differs from V1.0 in two known ways (`10-svrule-engine.md` §2, §5):

1. **Two SVRules per Lobe.** V1.1 Lobe dumps include both `myInitRule` and `myUpdateRule`. The Vat parses them into Lobe `+0x10` (init) and Lobe `+0x128` (update). V1.0 dumps only the update rule.
2. **SVRule line opcode/operand/index encoding.** V1.0 encodes opcodes as variable-length tags via `FUN_004251a0`; V1.1 reads them as fixed 4-byte ints via `FUN_0041d870`. (The float operand is unchanged - 4 bytes either way.)

A C3-engine port that emits V1.1 would need to:

- Append `" V1.1"` to the literal `"END DUMP"` in all five `Dump*` methods (or only in `DumpSpec` and trust the per-entity dumps to match - the Vat probes only the DMPB footer for version selection).
- Add a second `Dump` call in `Lobe::DumpLobe` for `myInitRule`.
- Switch `SVRule::Dump` from `out.put(byte)` × 3 to `WriteDesc<int32>` × 3 for the opcode triplet, raising per-line size from 7 to 16 bytes.

This C3 source predates that change. If a Vat connecting to a responder reproducing this source's behaviour selects V1.0 (because the footer is `END DUMP\0` not `END DUMP V1.1\0`), all per-entity dumps will be parsed correctly. A responder that misjudges the footer (e.g., emits `END DUMP V1.1` from V1.0-shaped per-entity bytes) will desync because the Vat will apply V1.1 readers to V1.0 byte streams.

---

## 10. SET* request payloads

`BRN: SET*` are **CAOS-arg-tokenised** commands, not byte-packed structs. The Vat sends an ASCII CAOS line ending in NUL (e.g. `execute\nTARG AGNT 1 BRN: SETL 3 7 0.500\0`); the engine's CAOS lexer parses it into integer and float arguments before dispatching to the handler. There is no separate "request body byte format" the way DMPL has a "response body byte format" - the request body is just the CAOS string itself.

### SETN - `iiif`

`CreatureHandlers::SubCommand_BRN_SETN` - `CreatureHandlers.cpp:716-724`:

```cpp
int lobe = vm.FetchIntegerRV();
int neuron = vm.FetchIntegerRV();
int state = vm.FetchIntegerRV();
float value = vm.FetchFloatRV();
if(!vm.GetCreatureTarg().GetBrain()->SetNeuronState(lobe, neuron, state, value))
    vm.ThrowRunError(CAOSMachine::sidCouldNotSetNeuron);
```

| Arg | Type | Range | Purpose |
|---|---|---|---|
| `lobe` | int | `0..numLobes-1` | Lobe index in `Brain::myLobes` |
| `neuron` | int | `0..lobe.W*H-1` | Neuron index in `Lobe::myNeurons` |
| `state` | int | `0..7` | Index into `SVRuleVariables` (V0..V7) |
| `value` | float | `[-1, +1]` | New value, clamped on write |

`Lobe::SetNeuronState` (`Lobe.cpp:540-545`) validates: `neuron in [0, size)`, `state in [0, 8)` (implicit: it indexes `states[state]` directly with bounds checked elsewhere), and `value in [-1, +1]` (`Lobe.cpp:540`). Out-of-range returns false → `sidCouldNotSetNeuron` CAOS error.

### SETD - `iiif`

`SubCommand_BRN_SETD` - `CreatureHandlers.cpp:727-735`:

```cpp
int tract = vm.FetchIntegerRV();
int dendrite = vm.FetchIntegerRV();
int weight = vm.FetchIntegerRV();
float value = vm.FetchFloatRV();
if(!vm.GetCreatureTarg().GetBrain()->SetDendriteWeight(tract, dendrite, weight, value))
    vm.ThrowRunError(CAOSMachine::sidCouldNotSetDendrite);
```

| Arg | Type | Range | Purpose |
|---|---|---|---|
| `tract` | int | `0..numTracts-1` | Tract index in `Brain::myTracts` |
| `dendrite` | int | `0..tract.dendrites.size()-1` | Dendrite index within tract |
| `weight` | int | `0..7` | Index into dendrite `weights` (`SVRuleVariables`) |
| `value` | float | `[-1, +1]` | New value |

### SETL - `iif`

`SubCommand_BRN_SETL` - `CreatureHandlers.cpp:738-745`:

```cpp
int lobe = vm.FetchIntegerRV();
int entryNo = vm.FetchIntegerRV();
float value = vm.FetchFloatRV();
if(!vm.GetCreatureTarg().GetBrain()->SetLobeSVFloat(lobe, entryNo, value))
    vm.ThrowRunError(CAOSMachine::sidCouldNotSetLobe);
```

| Arg | Type | Range | Purpose |
|---|---|---|---|
| `lobe` | int | `0..numLobes-1` | Lobe index |
| `entryNo` | int | `0..15` | SVRule line index (`SVRule::length = 16`) |
| `value` | float | `[-1, +1]` | New `myUpdateRule[entryNo].floatValue` |

`Lobe::SetSVFloat` forwards to `SVRule::SetFloat` on `myUpdateRule` (`Lobe.cpp:557`). Note **only the update rule is editable via SETL**; the init rule (genome-loaded) is immutable from the Vat.

### SETT - `iif`

`SubCommand_BRN_SETT` - `CreatureHandlers.cpp:748-755`. Same shape as SETL but targets `Tract::myUpdateRule` (`Tract.cpp:986-989`). Tract init rules are similarly immutable.

| Arg | Type | Range | Purpose |
|---|---|---|---|
| `tract` | int | `0..numTracts-1` | Tract index |
| `entryNo` | int | `0..15` | SVRule line index in `Tract::myUpdateRule` |
| `value` | float | `[-1, +1]` | New `floatValue` |

### Common parsing notes

- `vm.FetchIntegerRV()` consumes the next CAOS integer expression (literal, variable, or computed); `vm.FetchFloatRV()` does the same for floats. The CAOS lexer handles whitespace and decimals.
- All four SET* commands return no payload; the response is empty success (`view[0x08] = 0`, `view[0x0C] = 0`) on success or a CAOS run-time error otherwise.
- The Vat's reverse-engineered format strings `BRN: SETL %d %d %d %f` and `BRN: SETT %d %d %d %f` (`03-ipc-protocol.md` §3.2) carry **four** integer-then-float specifiers. The actual engine handlers expect **three** ints + one float (`iif`). Either the Vat strings have an extra `%d` from a handler that was unwired before shipping, or the Vat formats them with one more integer than the engine consumes (in which case the trailing field would be parsed as part of the float by CAOS or trigger a syntax error). A responder should accept the three-`%d` shape per the engine source; if the Vat actually emits four, the wire form is `lobe lineindex extra value` and the engine would error. Resolution requires capturing what the Vat actually sends.

---

## 11. Engine bugs in the wire format

The C3 source has at least three bugs that surface on the DMP wire. A responder must decide whether to be **bug-faithful** (match the original engine's bytes exactly, so existing Vat builds load successfully) or **clean** (emit correct bytes, accepting that some Vat behaviour may diverge).

### 11.1 Tract source/dest range duplicated

`Tract::DumpTract` writes `mySrc.neuronRangeToUse.min` twice instead of `min, max` (Tract.cpp:1003-1004), and the same for `myDst` (1009-1010). The reader at `Tract::Tract(istream&)` reads `min, max` (Tract.cpp:249-250, 256-257). After deserialisation by the Vat, both `min` and `max` fields hold the source's `min`, making the range degenerate.

Bug-faithful: emit `min` twice. Clean: emit `min, max`. The Vat doesn't validate `max >= min`, so either works syntactically.

### 11.2 `Lobe::DumpSize` and `Tract::DumpSize` undercount

`Lobe::DumpSize()` returns `40 + 7*16 + 9*N`; actual bytes are `40 + 7*16 + 40*N`. Off by `31*N`.

`Tract::DumpSize()` returns `36 + 7*32 + 4 + 16*D`; actual bytes are `36 + 7*32 + 4 + 44*D`. Off by `28*D`.

These are reported in DMPB. The Vat appears not to use them for buffer sizing (the IPC capacity is the cap, set in `view+0x10`); the values are informational only, used by the Vat to display per-lobe / per-tract size summaries. Bug-faithful emitters should report the wrong values; clean emitters that compute correct values may produce inconsistent UI output in the Vat tool.

In addition, `SVRule::DumpSize` (`SVRule.cpp:269-295`) is more egregiously broken: it has a shadowing bug where the local `int length = 0;` shadows `SVRule::length = 16`, so the `for (int i=0; i<length; i++)` loop never executes and the function returns 0. This output isn't actually called by any DMP* path - Lobe/Tract `DumpSize` use the constant `7 * SVRule::length` directly - so it doesn't affect the wire format, but if a future port routes through `SVRule::DumpSize` the result will be useless.

### 11.3 `Brain::DumpDendrite` checks the wrong vector

`Brain::DumpDendrite` (`Brain.cpp:912-921`) bounds-checks `t` against `myLobes.size()` instead of `myTracts.size()` (Brain.cpp:914). Tracts beyond `myLobes.size()` cannot be dumped via DMPD. Faithful emitters mirror this; clean emitters should check `myTracts.size()`.

### 11.4 `myInitRule` not exposed for SETL

`Brain::SetLobeSVFloat` only mutates `myUpdateRule`. To edit the init rule (the SVRule that runs at neuron creation), no wire command exists. This may be intentional (init-time-only logic), but the Vat's slider UI surfaces both rules in the in-memory model (`04-data-model.md` §3 "Two SVRule slots"), so a clean responder either has to reject SETL targeted at the init rule slot or extend the protocol with a fourth-arg variant - neither of which the Vat will exercise without source modifications.

---

## 12. Cross-reference: Vat in-memory struct fields ↔ wire bytes

For each Vat-side struct in `04-data-model.md`, this table shows whether the field arrives via DMP* and from where.

### Brain (size 0x74)

| Vat offset | Field | Wire source | Notes |
|---|---|---|---|
| `+0x00..+0x07` | vtables | - | Vat-only, set by `new Brain` |
| `+0x10` | version flag | DMPB footer | Set from `END DUMP` vs `END DUMP V1.1` (this source emits V1.0 only) |
| `+0x18..+0x23` | zeros | - | Vat-only init |
| `+0x24` | parent BrainAccess | - | Vat-only |
| `+0x28..+0x2c` | brain params | catalogue | From `Brain Parameters` catalogue, not DMP* |
| `+0x30..+0x38` | BrainComponent[] | constructed from DMPL/DMPT | Vat builds this on receipt |
| `+0x40..+0x48` | Lobe[] | constructed from DMPL | One element per DMPL response |
| `+0x50..+0x58` | Tract[] | constructed from DMPT | One element per DMPT response |
| `+0x60` | flag | - | Vat-only |
| `+0x64..+0x68` | aux vector | - | Vat-only, sized parallel to lobes |
| `+0x70` | zero | - | Vat-only |

The DMPB response itself populates only the lobe-count and tract-count loop bounds; per-lobe and per-tract sizes are informational.

### Lobe (size 0x290) - populated from DMPL §4

| Vat offset | Field | Wire offset (DMPL) | Source field |
|---|---|---|---|
| `+0x00..+0x07` | vtables | - | `new Lobe` |
| `+0x04` | int 0xFFFFFFFF | - | `BrainComponent` ctor default |
| `+0x08` | flag (`migration_enabled` / `frozen`) | wire byte 0..3 OR not in DMPL | Vat reads from V1.1 trailing byte; not present in this V1.0 source. **Open question: see §13.** |
| `+0x10..+0x127` | primary SVRule | only V1.1 | Not in V1.0 wire; this source dumps `myUpdateRule` to `+0x128` only |
| `+0x128..+0x23F` | secondary SVRule | wire 36..147 | `myUpdateRule.Dump` |
| `+0x244` | flag | - | `BrainComponent` default 0 |
| `+0x248` | id / param tag | wire 0..3 | `myIdInList` |
| `+0x24c` | display name ptr | - | Computed Vat-side from neurons[0]+4 |
| `+0x250` | TOKEN tag | wire 8..11 | `myToken` |
| `+0x254` | name string | derived from TOKEN | `Ezinekot(myToken)` (engine) / catalogue (Vat) |
| `+0x25c` | int | wire 12..15 | `myUpdateAtTime` |
| `+0x260` | flag byte | - | Vat-only init |
| `+0x264..+0x26c` | Neuron*[] | constructed from per-neuron blocks | Filled W×H times from neuron-block stream |
| `+0x270` | int | wire 4..7 | `myWinningNeuronId` |
| `+0x274` | int | not yet matched | - |
| `+0x278` | grid W | wire 20..23 | `myWidth` |
| `+0x27c` | grid H | wire 24..27 | `myHeight` |
| `+0x280..+0x288` | params (3) | wire 28..39 | `myColour[0..2]` |
| `+0x28c` | int* flags array | - | Vat allocates `int[W*H]` |

This source's V1.0 wire fields, in order with byte positions:

| Wire offset | Bytes | C3 field | Vat target |
|---:|---:|---|---|
| 0 | 4 | `myIdInList` | `+0x248` |
| 4 | 4 | `myWinningNeuronId` | `+0x270` |
| 8 | 4 | `myToken` | `+0x250` |
| 12 | 4 | `myUpdateAtTime` | `+0x25c` |
| 16 | 4 | `myX` | (not in Vat data model - Vat ignores) |
| 20 | 4 | `myY` | (Vat ignores) |
| 24 | 4 | `myWidth` | `+0x278` |
| 28 | 4 | `myHeight` | `+0x27c` |
| 32 | 4 | `myColour[0]` | `+0x280` |
| 36 | 4 | `myColour[1]` | `+0x284` |
| 40 | 4 | `myColour[2]` | `+0x288` |
| 44 | 4 | `myTissueId` | (Vat ignores or stores in unmatched int) |
| 48..159 | 112 | `myUpdateRule` (16 × 7 bytes) | `+0x128..+0x23f` |
| 160 + 40k | 40 | per-neuron block k of N | `Neurons[k]` at `+0x264` |
| 160 + 40N | 1 | `0x00` separator | - |
| 161 + 40N | 8 | `END DUMP` | - |

The Vat's wire-position assignments in `04-data-model.md` §3 differ slightly: the Vat-side reverse-engineering inferred the order from `FUN_00423840` decompilation but didn't observe `myX, myY, myColour, myTissueId` - those map to fields the Vat reverse-engineering listed as "purpose unknown" (`+0x270, +0x274, +0x280, +0x284, +0x288`). This document supersedes the Vat-side guesses with the engine-source names.

### Tract (size 0x2f0) - populated from DMPT §5

| Wire offset | Bytes | C3 field | Vat target (`04-data-model.md` §4) |
|---:|---:|---|---|
| 0 | 4 | `myIdInList` | `+0x004` (BrainComponent base) |
| 4 | 4 | `myUpdateAtTime` | `+0x00c` |
| 8 | 4 | `mySrc.lobe->idInList` | `+0x268` (resolved to Lobe*) |
| 12 | 4 | `mySrc.neuronRange.min` | `+0x26c` |
| 16 | 4 | `mySrc.neuronRange.min` (DUPLICATE - bug) | `+0x270` (Vat thinks it's max) |
| 20 | 1 | `mySrc.noOfDendritesPerNeuron` | `+0x274` |
| 21 | 4 | `myDst.lobe->idInList` | `+0x28c` |
| 25 | 4 | `myDst.neuronRange.min` | `+0x290` |
| 29 | 4 | `myDst.neuronRange.min` (DUPLICATE) | `+0x294` |
| 33 | 1 | `myDst.noOfDendritesPerNeuron` | `+0x298` |
| 34 | 1 | `myDendritesAreRandomlyConnectedAndMigrate` (bool) | `+0x2b0` |
| 35 | 1 | `myNoOfDendritesPerNeuronIsRandomUpToUpperBound` (bool) | `+0x2b1` |
| 36..147 | 112 | `myInitRule` (16 × 7) | `+0x10..+0x127` (BrainComponent first SVRule slot) |
| 148..259 | 112 | `myUpdateRule` (16 × 7) | `+0x128..+0x23f` |
| 260 | 4 | `noDendrites` | (used by reader only) |
| 264 + 44d | 44 | dendrite d of D | per-dendrite at `+0x260` |
| 264 + 44D | 1 | `0x00` | - |
| 265 + 44D | 8 | `END DUMP` | - |

Tract's `Migration Parameters` byte fields at Vat `+0x2b2, +0x2b3` come from the `Migration Parameters` catalogue at Vat-construct time, not the wire (`04-data-model.md` §4). `ReinforcementDetails` slots at `+0x2c8, +0x2dc` are constructed empty by the Vat ctor and populated only via the `CreaturesArchive` snapshot path, never via DMPT wire.

### Neuron (size 0x24) - populated from DMPN §6 or per-neuron block in DMPL §4

| Wire offset | Bytes | C3 field | Vat target |
|---:|---:|---|---|
| 0 | 4 | `myNeuronInput[n]` (host-Lobe-owned) | `+0x00` (Vat reads as "first field, purpose unknown") |
| 4 | 4 | `Neuron::idInList` | (Vat reads into neuron `+0x04`?) |
| 8..39 | 32 | `Neuron::states[8]` | `+0x04..+0x23` (8 floats) |

The Vat-side reverse-engineering noted (`04-data-model.md` §5) that the first 4 bytes of a neuron block are an unknown field. Source confirms: it's `myNeuronInput[n]`, the per-tick input accumulator, **stored on the Lobe not the Neuron**, but emitted into the per-neuron block. The Vat's Neuron struct is 0x24 bytes total but the wire emits 8 + 32 = 40 bytes per neuron - the Vat's per-neuron storage doesn't keep `myNeuronInput`, so the Vat must either store it elsewhere or discard.

### Dendrite (size 0x2c) - populated from DMPD §7 or per-dendrite block in DMPT §5

| Wire offset | Bytes | C3 field | Vat target |
|---:|---:|---|---|
| 0 | 4 | `Dendrite::idInList` | `+0x00` |
| 4 | 4 | `srcNeuron->idInList` | `+0x04` (resolved to Neuron*) |
| 8 | 4 | `dstNeuron->idInList` | `+0x08` |
| 12..43 | 32 | `Dendrite::weights[8]` | `+0x0c..+0x2b` |

Total 44 bytes, exact match with Vat in-memory size 0x2c. The Vat's `04-data-model.md` §6 noted the eight 4-byte fields' identity was guessed; `SVRule.h:30-39` gives canonical names: `WEIGHT_SHORTTERM_VAR, WEIGHT_LONGTERM_VAR, SECOND_DENDRITE_VAR, THIRD_DENDRITE_VAR, FOURTH_DENDRITE_VAR, FIFTH_DENDRITE_VAR, SIXTH_DENDRITE_VAR, STRENGTH_VAR`.

---

## 13. Open questions

Items that the C3 source alone does not resolve.

1. **V1.1 emitter location.** This source emits V1.0. The Vat clearly supports V1.1 (with two SVRules per Lobe and 4-byte opcodes). Where does that come from? Candidates: a later C3 patch not in this source archive, the Docking Station engine (later C3 derivative), or the Creature Labs internal SDK that shipped with the Brain Editor. Resolving requires comparing a different engine binary's `Lobe::DumpLobe` against this source.

2. **SETL/SETT argument count.** Engine handlers expect 3 ints + 1 float (`iif`). Vat string table has format strings with 4 ints + 1 float. Is the Vat actually sending the 4-`%d` form (and the engine erroring), or is the format string dead code? Resolve by capturing the Vat's actual emitted string against any engine.

3. **Lobe `+0x008` byte source.** The Vat reverse-engineering noted (`10-svrule-engine.md` §5 "The +8 byte") that V1.1 dumps trail with a 1-byte flag. This source has no such trailing byte (the V1.0 wire ends with the last neuron's `weights`). Is the byte added by the V1.1 patch, or is the Vat reading uninitialised memory? Without a V1.1 source we cannot tell.

4. **Init-rule editing.** The Vat's SVRule editor dialog (`10-svrule-engine.md` §6) shows "(L:X) Lobe: Y" titles for both rules in the Lobe's two SVRule slots. Editing the init rule is impossible via SETL because the engine's `Lobe::SetSVFloat` targets `myUpdateRule` only. Either the Vat's "init rule slider" is non-functional, or it sends a different command (e.g., a SETL variant we haven't located in the Vat string table). Resolve by exercising the Vat's UI against a stub responder and observing.

5. **Reinforcement parameters on the wire.** `Tract::ReinforcementDetails` has `myThreshold, myRate, myChemicalIndex, myDendritesSupportReinforcement` fields (`Tract.h:101-126`) but they are **never** dumped in `Tract::DumpTract`. They ride on the genome / archive path only. The Vat constructs them empty and reads them only from snapshot files, so the live brain view shows zero-initialised reinforcement state regardless of the engine's actual values. Faithful behaviour for a responder; a richer protocol would require an additional `BRN: DMPR` (or similar) command not present in either codebase.

6. **`mySrc.lobe` resolution before lobes exist.** `Tract::Tract(istream&)` resolves `mySrc.lobe = lobes[l]` from the lobe vector index. If the Vat sends DMPT before all DMPL responses are received and processed, the resolution would fail. The Vat's brain-init driver `FUN_00403200` handles this by sending all DMPL first, then all DMPT (`03-ipc-protocol.md` §3.1, callsites 598 and 614). A responder must enforce this ordering on its side too - emitting DMPT for a tract whose source/dest lobe wasn't yet sent breaks the Vat's reader.

7. **`myColour[3]` endianness on the wire.** The colour fields are typed `int`, not `uint8[4]`. So a colour like RGB(255, 128, 0) is emitted as three little-endian 4-byte ints: `FF 00 00 00 80 00 00 00 00 00 00 00`. A responder that packs RGB into a single int (`0xFF8000`) would corrupt the field. The Vat reverse-engineering doc flags `+0x280..+0x288` as "params (3) of unknown purpose"; this document corrects: they are colour channels.

---

## 14. Summary

The wire format is a hybrid: DMPB is ASCII text with NUL separators; DMPL/DMPT/DMPN/DMPD are little-endian binary blobs of `WriteDesc`-emitted struct fields, terminated by `0x00 "END DUMP"`. Per-line SVRule entries are 7 bytes (3 opcode bytes + 4-byte float). All five DMP* commands originate in `C3sourcecode/engine/Caos/CreatureHandlers.cpp` and serialise via `C3sourcecode/engine/Creature/Brain/{Brain,Lobe,Tract,SVRule}.cpp` using `BrainIO.h`'s `WriteDesc<T>` template. The C3 source emits **V1.0 only**; V1.1 emitter source is not available and the V1.1 differences are inferred from the Vat reader's reverse-engineering. Three engine-side bugs (range duplication, undercounted DumpSize, wrong bounds vector in DumpDendrite) and one missing feature (init-rule editing) are present in the wire format and must be replicated for bug-for-bug Vat compatibility, or corrected for a clean reimplementation. **No part of openc2e currently implements `BRN:` commands**; any port must be authored fresh against this catalogue.
