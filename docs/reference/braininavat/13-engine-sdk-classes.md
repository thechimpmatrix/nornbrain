# Brain in a Vat: Engine SDK Classes

Catalogue of the Creature Labs Engine SDK classes that are statically linked into `Vat_1.9.exe` alongside the brain types (`Brain`, `Lobe`, `Tract`, `Neuron`, `Dendrite`) already documented in [04-data-model.md](04-data-model.md). These types provide the surrounding Engine object model. Many of them appear here only as RTTI breadcrumbs and partial constructors because the Vat exercises only a fraction of their behaviour; the rest was either dead-code-eliminated or never reachable from the Vat's offline / online code paths.

All addresses are virtual addresses inside `Vat_1.9.exe` as analysed by Ghidra. Function names use the Ghidra default `FUN_<addr>`. RTTI Type Descriptors come from `notes/classes.txt`; mangled-name strings come from `notes/strings.txt`.

---

## Inheritance map (recovered)

```
                       PersistentObject  (vftable 0x46e47c primary, 0x46e4d4 secondary)
                       /        |       \              \              \           \
              Faculty    ChemicallyActive   BrainComponent           Instinct     Genome
              (0x46e4a8) (0x46e4a0)         (0x46e458)               (0x46e4e0)   (0x46e56c)
                  \         /                |   \
                   \       /                Lobe  Tract
                    \     /              (0x46e4fc) (0x46e538)
                     Brain
                    (0x46e3c0 primary, 0x46e3b8 secondary)

  CreatureFacultyInterface (0x47c630)      Agent (0x47c618)
                  \                            |
                   \                           |
                    +--- (cross-cast at runtime; see Agent §3) ---

  CAOSVar (0x47ac68) - RTTI only; no observable usage in the Vat.
```

Established by:
- `BrainComponent`, `Lobe`, `Tract`, `Brain`, `Instinct` deserialiser type-checks at `FUN_004212b0`, `FUN_004233f0`, `FUN_00425340`, `FUN_0041af70`, `FUN_004227d0` (per [04-data-model.md §9](04-data-model.md)) - the Type Descriptors whose strings are present in the binary are the observable members of the polymorphic archive set.
- vftable pointer pairs written during construction in `FUN_00421310` (BrainComponent), `FUN_00422a70` (Instinct), `FUN_00428dd0` (Genome), `FUN_00422500` (Brain's combined-base subobject), `FUN_0041b270` (Brain).
- one and only one runtime `__RTDynamicCast` against an engine class: `FUN_0045a41a(piVar1, 0, 0x47c618, 0x47c630, 0)` at `FUN_0042ae20` - Agent⇄CreatureFacultyInterface (see §3).

Note on hierarchy uncertainty: Brain's combined base subobject has primary vftable `0x46e4a8` and secondary `0x46e4a0`. One is `Faculty`, the other is `ChemicallyActive`. The Vat alone does not discriminate which is primary; we infer `Faculty` is primary and `ChemicallyActive` is secondary from the order of vftable writes in the destructor (`FUN_00422520` writes the `+4` slot first, then the `+0` slot - MSVC destroys derived → base, so the secondary base is the `+4` slot). Treat that as a reasonable but unverified assumption.

---

## 1. PersistentObject

**RTTI Type Descriptor:** `0x47b888`  
**Mangled name:** `.?AVPersistentObject@@` at `0x47b890`  
**Type-mismatch string for serialiser:** none observed in the binary. (Brain, BrainComponent, Lobe, Tract, Instinct, SVRule, Faculty, Genome each have one - PersistentObject does not, consistent with it being abstract.)  
**Vftable addresses:**
- `0x46e47c` - primary-base layout (placement at offset `+0` in objects whose only base is PersistentObject)
- `0x46e4d4` - secondary-base layout (placement at offset `+4` in objects with multiple inheritance)

### Role

Virtual base for the engine's archive-serialisable object model. Every recoverable engine class in this binary either contains a PersistentObject vftable in its layout, or is reachable via the type-checking serialiser pattern (`FUN_00436fc0` then `__RTtypeid` against the expected RTTI TD). The dual vftable (`0x46e47c` / `0x46e4d4`) is the standard MSVC artefact for a base that appears at two different sub-object offsets in derived classes that use multiple inheritance.

### Vftable layout

The Vat's decompilation does not let us enumerate the function pointers stored at `0x46e47c` and `0x46e4d4` (`classes.txt` only labels the RTTI Type Descriptors, not the vftable slot data). The brief asked for `Read` and `Write` virtuals at slot 1 and slot 2; without a data-section dump we can confirm only that:

- `FUN_00436fc0(this, archive)` is the engine's polymorphic archive read entry point. It is invoked by every per-class type-checking wrapper (`FUN_0041af70` Brain, `FUN_004212b0` BrainComponent, `FUN_004233f0` Lobe, `FUN_00425340` Tract, `FUN_004227d0` Instinct). The wrappers all share the body `FUN_00436fc0(this, archive); if (*archive != 0) { __RTtypeid_check(*archive, expected_TD); throw "Type mismatch..."; } return this;`. So `FUN_00436fc0` is dispatching through a vftable on `*archive`, and `Read` is one of those slots.
- `Write` is presumed symmetric (slot for the writer side of CreaturesArchive) but no caller in the Vat exercises it for any class - the Vat is a viewer, not a saver.

### Classes that derive from PersistentObject (observed in this binary)

| Class | First-vftable write | Pattern |
|---|---|---|
| `BrainComponent` | `FUN_00421310` writes `0x46e47c` then `0x46e458` | single inheritance |
| `Lobe` | `FUN_00423840` (calls BrainComponent ctor) | through BrainComponent |
| `Tract` | `FUN_00426290` (calls BrainComponent ctor) | through BrainComponent |
| `Instinct` | `FUN_00422a70` writes `0x46e47c` then `0x46e4e0` | single inheritance |
| `Genome` | `FUN_00428e90`, `FUN_00428dd0` write `0x46e47c` then `0x46e56c` | single inheritance |
| `Faculty` (subobject) | `FUN_00422500` writes `0x46e4a8` (Faculty's vftable, which contains PO+Faculty virtuals) | single inheritance from PO |
| `ChemicallyActive` (subobject) | `FUN_00422500` writes `0x46e4d4` then `0x46e4a0` (ChemicallyActive vftable; PO is at `+4` here) | single inheritance from PO, placed as secondary base |
| `Brain` | `FUN_0041b270` calls `FUN_00422500` then writes `0x46e3c0` and `0x46e3b8` | multiple inheritance via Faculty + ChemicallyActive |

### Standalone functions that look like base-vftable resets

Two trivial functions write the PersistentObject vftable and return:

- `FUN_00421650` @ `0x421650`: `*param_1 = &PTR_LAB_0046e47c; return;`
- `FUN_004249f0` @ `0x4249f0`: `*param_1 = &PTR_LAB_0046e47c; return;`

These are the destructor finalisers (the "reset to base vftable" final step that MSVC emits in derived class destructors). They are not the PersistentObject constructor - a real constructor would zero fields too.

---

## 2. CAOSVar

**RTTI Type Descriptor:** `0x47ac68`  
**Mangled name:** `.?AVCAOSVar@@` at `0x47ac70`  
**Vftable address:** not located. No vftable label can be associated to CAOSVar from the decompiled output.

### Honest assessment

CAOSVar appears in this binary **only** as a compiled-in RTTI Type Descriptor and mangled-name string. There is no observable evidence of:
- a CAOSVar constructor call,
- a CAOSVar `operator new` (no `operator_new(N)` block in the disassembled code paths is followed by anything that matches a CAOSVar shape),
- a `__RTtypeid` or `__RTDynamicCast` against the descriptor,
- field accesses keyed by a tag offset that we can attribute to CAOSVar.

So the Vat tool **does not exercise CAOSVar** during either online (IPC) or offline (genome-load) operation. It carries the type's RTTI because the Engine SDK headers it was compiled against unconditionally instantiated the descriptor, and the linker preserved it.

### What we still know (from name + Engine context)

The class is the engine's universal scripting variable type. By external Engine documentation (CAOS reference) the value is a tagged union over `int`, `float`, `string`, and `Agent*` reference. From the Vat alone we cannot recover:

- the type-tag offset
- the union layout
- the constructor variants
- the conversion functions

If CAOSVar layout is needed for the NORNBRAIN port, that has to come from another binary in the Engine fleet (e.g. an `engine.exe`) where it is actually used. Open question.

### Note on a 16-byte multi-inheritance object that is **not** CAOSVar

There is a tempting candidate at `FUN_00422400` (factory) → `FUN_00422500` (constructor) - it allocates 16 bytes and writes vftables `0x46e4a8` at `+0` and `0x46e4a0` at `+4`, which is exactly the shape one would hope CAOSVar would take. **This is not CAOSVar.** Reasons:

1. The same constructor `FUN_00422500` is invoked at the start of `Brain::Brain` (`FUN_0041b270` line at the binary offset corresponding to decompiled line 22185). Brain's first action after `FUN_00422500` is to write its OWN primary and secondary vftables `0x46e3c0` / `0x46e3b8` (lines 22207–22208 of decompilation). The pattern is base-class construct then derived-vftable-overwrite. So `FUN_00422500` is the **constructor of Brain's combined base subobject** - `Faculty + ChemicallyActive` (see §4 and §6).
2. `FUN_00422400` is an unreferenced factory - it has zero call sites in the decompilation. It is leftover engine-SDK code that was compiled in but never invoked from the Vat.
3. The 16-byte multi-vftable shape is what `class Brain : public Faculty, public ChemicallyActive` requires, not what `class CAOSVar` requires.

So the 16-byte multi-inherited subobject shape belongs to Faculty+ChemicallyActive bridges, not to CAOSVar.

---

## 3. Agent

**RTTI Type Descriptor:** `0x47c618`  
**Mangled name:** `.?AVAgent@@` at `0x47c620`  
**Vftable address:** not directly located in the Vat's call paths; Agent objects are never constructed by the Vat (it is a viewer / serialiser, not a simulator).  
**Size:** **at least `0xc88` bytes** (about 3,208 bytes), inferred from field accesses in the only Agent-touching live code (see below). Cannot be tightened from this binary alone.

### Honest assessment

Agent is **partially present**. Like CAOSVar, the bulk of Agent's behaviour was dead-code-eliminated because the Vat never instantiates one. What survives is one runtime-handle-check function that touches Agent fields and dispatches across a vftable.

### Live code that touches Agent

Function `FUN_0042ae20` @ `0x42ae20` is the Agent-handle accessor for the "expect a Creature" type:

```c
void __fastcall FUN_0042ae20(undefined4 *param_1) {
  int *piVar1 = (int *)*param_1;
  if (piVar1 == NULL) throw "AHE0019: Attempt to access NULL handle";
  if (((char)piVar1[0x2de]) != '\0') throw "AHE0020: Attempt to access garbaged handle";
  if ((*(byte *)(piVar1 + 0x321) & 0x20) == 0) throw "AHE0021: Attempt to access incorrect type (creature expected)";
  FUN_0045a41a(piVar1, 0, 0x47c618, 0x47c630, 0);  // __RTDynamicCast(Agent, CFI)
  return;
}
```

This gives us:

- Agent has a **garbage flag** at offset `0x2de * 4 = 0xb78`. Set when an agent has been destroyed; AgentHandleException is thrown if it is read after destruction. This is what the C3 engine calls a "garbaged" agent handle.
- Agent has a **type bitfield** byte at offset `0x321 * 4 = 0xc84`. Bit `0x20` is the "is creature" bit. By the AHE0010-15 error series in the strings table (see §3.2 below) we know other bits in this same field denote "compound agent", "vehicle", and "raw / simple / pointer" subtypes.
- Agent's class size therefore extends to at least byte `0xc84 + 1 = 0xc85`, rounded up by alignment ≈ `0xc88`.
- The `__RTDynamicCast(piVar1, 0, AgentTD, CFI_TD, 0)` at the end invokes a runtime type cast from Agent to CreatureFacultyInterface. The result is discarded by Ghidra's decompilation, but in real MSVC C++ this is the body of `dynamic_cast<CreatureFacultyInterface*>(agent_ptr)`. The return value is presumed to be used by the caller after the function returns (the function is `void` in Ghidra's view, but that may be a decompilation artefact).

### What the cast tells us about Agent ↔ CreatureFacultyInterface

The cast is **bidirectional** (Agent and CFI are both sibling classes of a common derived class that combines them, OR Agent inherits from CFI, OR a Creature subclass multiply inherits from both). The Vat alone does **not** discriminate between these. The most common engine pattern is:

> `class Creature : public Agent, public CreatureFacultyInterface { ... };`

with the runtime cast being a **cross-cast** (sideways through MI) rather than an upcast. Under that interpretation, Agent itself does not derive from CFI directly. We do not have evidence to commit to this interpretation; we note it is the standard Engine SDK shape.

What we **do** know: in the Vat, the Agent type is reachable from a Creature handle, and any code dereferencing such a handle must validate `+0xb78 == 0` and `(byte at +0xc84) & 0x20` before accessing it. These two checks are the AHE0019/0020/0021 triple.

### Agent type-handle error families

From `notes/strings.txt`:

| Error code | Type expected | Address triple (NULL / garbaged / wrong-type strings) |
|---|---|---|
| AHE0003-0009 | raw / simple / pointer agent | three triples at `0x47c128`, `0x47c1bc`, `0x47c254`, `0x47c2ec` |
| AHE0010-0012 | compound agent | `0x47c2ec`, `0x47c298`, `0x47c2c0` |
| AHE0013-0015 | vehicle | `0x47c330`, `0x47c358`, `0x47c384` |
| AHE0019-0021 | creature | `0x47c3c4`, `0x47c3ec`, `0x47c418` (also `0x47c458`/`0x47c480`/`0x47c4ac` and `0x47c580`/`0x47c5a8`/`0x47c5d4`) |

Each triple is one Agent → SubAgent handle accessor. Only the creature triple is observed in live decompiled code (`FUN_0042ae20`). The other accessors exist but are not called from the Vat. They constitute the rest of Agent's RTTI surface that the Engine SDK defines for `RawAgent`, `SimpleAgent`, `PointerAgent`, `CompoundAgent`, `Vehicle`.

### Open Agent questions

- Whole-class size beyond the high-water mark `0xc84` is unknown. The Engine likely defines a much larger Agent class with sound, animation, script, mover, attribute, position, world-link, etc. fields. None of those are reachable from the Vat.
- Where is the `Agent::Read` / `Agent::Write` archive serialiser? The Vat doesn't deserialise an Agent (only a Genome which references neuron mappings, plus per-component brain dumps over IPC), so the wrapper for `0x47c618` is not in `decompiled_all.c`. It exists in the Engine code itself; in this binary, only the Type Descriptor remains.

---

## 4. Faculty

**RTTI Type Descriptor:** `0x47b8a8`  
**Mangled name:** `.?AVFaculty@@` at `0x47b8b0`  
**Type-mismatch string:** `"Type mismatch during serialisation of Faculty"` at `0x47ba8c`  
**Vftable address (inferred):** `0x46e4a8` - the primary-base vftable written at `+0` of Brain's combined base subobject by `FUN_00422500`.

### Role

Abstract base class for "creature subsystem" objects. The Engine SDK defines several Faculty types (Brain, Decision, Reproduction, etc.); this Vat only carries Brain's instantiation and the bare RTTI for the abstract Faculty itself.

### Inheritance evidence: Brain *is-a* Faculty

`FUN_0041b270` (Brain ctor) line 22185:

```c
FUN_00422500(param_1);   // construct combined Faculty + ChemicallyActive base
// ... initialise Brain's own fields ...
*param_1   = &PTR_LAB_0046e3c0;   // Brain's primary vftable (override of Faculty's)
param_1[1] = &PTR_LAB_0046e3b8;   // Brain's secondary vftable (override of ChemicallyActive's)
```

`FUN_00422500` (combined-base ctor) writes:

```c
param_1[1] = &PTR_LAB_0046e4d4;   // PO secondary-base vftable, transient (set by ChemicallyActive's PO base ctor)
*param_1   = &PTR_LAB_0046e4a8;   // Faculty vftable (or ChemicallyActive - see hierarchy note)
param_1[1] = &PTR_LAB_0046e4a0;   // ChemicallyActive vftable (or Faculty)
```

Brain therefore has **two vptrs** in its header (the standard MSVC layout for `class Brain : public Faculty, public ChemicallyActive`), and it overrides both base vtables with its own.

### Faculty's vftable

Almost no observable virtual dispatch through `0x46e4a8`. The Vat never calls a virtual method on Faculty directly - when it has a Brain it calls Brain virtuals (`0x46e3c0`). Slots and member functions cannot be enumerated from this binary alone.

### Faculty serialisation

There is a "Type mismatch during serialisation of Faculty" string at `0x47ba8c`, paired with mangled name `Faculty` at `0x47ba7c` and `0x47ba84`. This means the engine has a Faculty serialiser type-check wrapper of the same shape as the Brain/Lobe/Tract ones (call `FUN_00436fc0`, then `__RTtypeid` against `0x47b8a8`, throw if mismatch). The wrapper was either dead-code-eliminated or never decompiled because the Vat's own load paths never hit it. Per [04-data-model.md §9](04-data-model.md), Faculty is part of the on-disk archive format even though only Brain/Lobe/Tract are exercised by the wire-protocol path.

---

## 5. CreatureFacultyInterface

**RTTI Type Descriptor:** `0x47c630`  
**Mangled name:** `.?AVCreatureFacultyInterface@@` at `0x47c638`  
**Vftable address:** not located.  
**Size:** unknown.

### Role

The bridge interface that sits between an `Agent`-typed Creature and the rest of its faculty stack. By the AHE0019-21 cast (see §3) we know that the Engine routinely converts Agent pointers to CFI pointers when it has identified the agent as a creature. CFI is therefore the entry point through which a Creature exposes its faculties to the rest of the engine.

### Honest assessment

Apart from being the target of one `__RTDynamicCast` call (line 34427 in `FUN_0042ae20`), CFI is invisible in this binary. No constructors, no virtual calls, no field accesses. It is almost certainly an abstract interface (all-virtual class with a virtual destructor), but we cannot confirm that from the Vat - we cannot enumerate its slots, its ABI, or its concrete implementations.

The Engine SDK defines this class fully in the live engine binaries; in the Vat only the RTTI and the cast remain.

---

## 6. ChemicallyActive

**RTTI Type Descriptor:** `0x47b868`  
**Mangled name:** `.?AVChemicallyActive@@` at `0x47b870`  
**Vftable address (inferred):** `0x46e4a0` - the secondary-base vftable written at `+4` of Brain's combined base subobject by `FUN_00422500`.

### Role

Mixin / second base for objects that participate in the engine's biochemistry simulation. Provides chemical-receptor and chemical-emitter behaviour through virtual methods (specifics not recoverable from this binary).

### Inheritance evidence: Brain is-a ChemicallyActive

Same as §4: Brain's ctor calls `FUN_00422500` which sets `0x46e4a0` at `+4`, then Brain overrides with its own `0x46e3b8` secondary vftable.

### What is *not* ChemicallyActive

Importantly, **`Lobe` and `Tract` are not ChemicallyActive**. Their ctors (`FUN_00423840` Lobe, `FUN_00426290` Tract) inherit from BrainComponent, which writes vftables `0x46e47c` (PersistentObject) then `0x46e458` (BrainComponent), with no secondary vptr at `+4`. There is no chemistry mixin in their layout. This answers open question #3 from [09-class-registry.md](09-class-registry.md): biochemistry feeds the brain only via input neurons (the Decision lobe, etc.), **not** by chemicals directly modulating per-lobe or per-tract dynamics. Brain itself is ChemicallyActive (so chemistry can affect Brain-level state), but its components are not.

### ChemicallyActive virtual surface

Not enumerable from this binary. The vftable at `0x46e4a0` would contain the polymorphic methods; we have no way to print its slots from the decompiled-only artefact set.

---

## 7. Instinct

**RTTI Type Descriptor:** `0x47bb78`  
**Mangled name:** `.?AVInstinct@@` at `0x47bb80`  
**Type-mismatch string:** `"Type mismatch during serialisation of Instinct"` at `0x47bad4`  
**Vftable address:** `0x46e4e0`  
**Size:** **`0x54` (84) bytes**, established by `operator_new(0x54)` at three sites (`FUN_00422730`, decompiled lines 22511 and 22694) all paired with the Instinct ctor.

### Constructors

- **Default ctor:** `FUN_00422a10` @ `0x422a10`. Writes `*this = 0x46e47c` (PersistentObject), initialises `+8` as a 3-element array of 20-byte (`0x14`) elements via `FUN_00459c0c(this+8, 0x14, 3, &LAB_004232a0)`, then writes `*this = 0x46e4e0` (Instinct's own vftable). Allocator wrapper `FUN_00422730` (`operator_new(0x54)` then call this ctor).
- **Stream ctor:** `FUN_00422a70(this, stream, lobeList)` @ `0x422a70`. Same vftable progression and same 3-slot init. Then loads the three condition slots from the stream, then loads tail fields. This is the deserialiser used when an Instinct is read from a CreaturesArchive.
- **Type-checking serialiser wrapper:** `FUN_004227d0` @ `0x4227d0`. Calls `FUN_00436fc0(this, archive)` then `__RTtypeid(*archive, 0x47bb78)` and throws "Type mismatch during serialisation of Instinct" on failure.

### Recovered struct layout

Inferred from the stream ctor `FUN_00422a70`:

```c
struct Instinct {                             // size 0x54 (84 bytes)
  void**  vftable_PersistentObject_to_Instinct;  // +0x00, final value 0x46e4e0
  void*   lobeList;                              // +0x04, ctor arg param_2 (Brain's lobe lookup table)
  // +0x08 .. +0x43 - three 20-byte InstinctCondition slots, accessed from this+0x10 onwards;
  //                  stride 0x14 per slot, three iterations.
  InstinctCondition slots[3];                    // +0x08 .. +0x43 (60 bytes total, 0x3c)
  uint32  drive_index;                           // +0x44, raw byte mapped through FUN_0042b520
  uint32  flag_byte;                             // +0x48, raw byte
  float   strength;                              // +0x4c, computed as ((int)raw_byte / 124.0f) - 1.0f
                                                 //         range maps stream byte 0..0xf8 → ~[-1.0, +1.0]
  uint32  reserved_zero;                         // +0x50, init'd to 0
};
```

#### InstinctCondition (per-slot, 0x14 = 20 bytes)

```c
struct InstinctCondition {            // 20 bytes
  uint8   type_tag;                   // +0x00 (read from stream as byte)
  uint8   pad0[3];                    // +0x01 .. +0x03
  // +0x04 .. +0x0f: ~12 bytes that look like an inline std::string holding a name
  //                  (lobe name or neuron name, looked up via lobeList).
  // +0x10 .. +0x13: trailing 4 bytes (tail of the string struct, possibly its size cap).
};
```

The slot loader reads two bytes per condition (a count `uVar3` and a flag `uVar4`), looks up a name via `FUN_0041c580(lobeList, count - 1)`, copies the result into the slot's std::string-shaped block, and then reads two more name segments (likely lobe-then-neuron pair). Format strings used as "(empty)" placeholders during the load are at `DAT_0047bb14`, `DAT_0047bb1c`, `DAT_0047bb24`, `DAT_0047bb2c`, `DAT_0047bb34`, `DAT_0047bb3c`, `DAT_0047bb44` (per-condition keys for lobe / neuron name lookups).

So an Instinct describes "if these three (lobe, neuron) conditions fire, push this much strength into this drive", which matches the published creatures instinct semantics.

### Where Instincts come from in the Vat

The offline-mode Brain loader `FUN_0041b670` allocates Instinct objects (`operator_new(0x54)` at line 22511 and 22694) when reading a creature genome, between the Lobe and Tract loops. So Instinct is part of the genome archive, **not** the per-component brain dump that the IPC protocol delivers (`BRN: DMPB / DMPL / DMPT`). Online-mode brains do not carry instincts over the wire; offline genome loads do.

---

## 8. Genome

**RTTI Type Descriptor:** `0x47c058`  
**Mangled name:** `.?AVGenome@@` at `0x47c060`  
**Type-mismatch string:** `"Type mismatch during serialisation of Genome"` at `0x47bf1c`  
**Vftable address:** `0x46e56c`  
**Size:** **`0x40` (64) bytes**, established by `operator_new(0x40)` at `FUN_00428960` (factory) and decompiled line 2071 (Vat startup creates a Genome).

### Constructors

- **Default ctor:** `FUN_00428dd0` @ `0x428dd0`. Initialises by-name fields and calls `FUN_00428cf0(this)` to clear the std::string at `+0x1c` and the working buffer fields. Sets `*this = 0x46e56c`.
- **Filename ctor:** `FUN_00428e90` @ `0x428e90`. Two-step (PO base then derived), then reads a file from disk:
  - `OpenFile(filename, &local_94, 0)` - Win32 OpenFile.
  - 4-byte magic check: `local_ec == 0x33616e64` (= ASCII `"dna3"`). On mismatch, throws via `FUN_0042a5c0` with tag `"Genome::Genome"` / `"genome_old_dna"`.
  - On success: `GetFileSize`, `operator_new(file_size + 0x3fc)`, `ReadFile` into the buffer at `this+4`, write size to `this+0x14`, append sentinel `0xfc` at `buffer[+0x400]` and trailing magic `0x646e6567` (= ASCII `"gend"`) at `buffer[+0x400+0x3fc]`. Then `_lclose`.
  - On open failure: throws via `FUN_0042a5c0` tagged `"Genome::Genome"` / `"genome_error"`.
- **Stream ctor:** `FUN_004292e0` @ `0x4292e0`. Variant that takes a stream / filename pair (FILE*-based read via `FUN_0045aa5c`); same magic checks, same error tags. Used by Vat startup (`FUN_00408..` calls it via the lifecycle in `FUN_00404???`).

### Genome struct layout (recovered)

```c
struct Genome {                       // size 0x40 (64) bytes
  void**   vftable;                   // +0x00, final value 0x46e56c
  uint8*   buffer;                    // +0x04, allocated (file_size + 0x3fc) bytes
  uint32   ?;                         // +0x08
  uint32   ?;                         // +0x0c
  uint32   header_field_a;            // +0x10
  uint32   data_size;                 // +0x14, set to local_f4 + 0x400 after ReadFile
  uint32   ?;                         // +0x18
  uint8[?] string_inline_capacity;    // +0x1c .. +0x2b - std::string-like inline buffer
                                      //                  (set to 0 by FUN_0040a100(_,'\0') in ctor)
  uint8    age_or_flag;               // +0x1c (overlaps the std::string slot 0)
                                      //          gets bytes from local_fa via FUN_00409e10 in the
                                      //          stream ctor; resembles a "for which life stage" flag
  uint8*   path_string_data;          // +0x20 (std::string heap pointer when long-string mode)
  uint32   path_string_length;        // +0x24
  uint32   path_string_capacity;      // +0x28
  uint32   age_setting;               // +0x2c (set from param_2 in stream ctor - appears to be the
                                      //         desired age / life-stage at load time)
  void*    age_pointer_or_struct;     // +0x30 (set from param_4)
  uint8    sex_or_kind;               // +0x34 (set from param_3 in filename ctor;
                                      //         param_6 in stream ctor)
  uint8    flag_b;                    // +0x35
  uint8    sentinel_ff;               // +0x36 (init'd to 0xff in FUN_00428cf0)
  // +0x38 .. +0x3f trailing slots; uses unclear from this binary alone.
};
```

The +0x1c block is plainly a std::string holding the genome path or genome filename. The MSVC small-string optimisation makes the layout overlap with several smaller ints; we cannot fully discriminate from the decompilation.

### Constants / file format

- **Magic header:** `0x33616e64` little-endian = ASCII `"dna3"` - the C3 / Docking-Station genome magic. Files lacking it throw `"genome_old_dna"` (i.e. they are pre-C3 genomes).
- **Magic trailer:** `0x646e6567` little-endian = ASCII `"gend"` - sentinel appended at the end of the in-memory buffer after the file body.
- **Buffer pad:** `+0x3fc` extra bytes allocated past the file content (room for the sentinel and parser scratch).
- **Stop byte:** `0xfc` written to the buffer at offset `+0x400` from the start of the file body.

### Methods named in the binary

`notes/strings.txt` lists three Genome method tags used in error messages:
- `Genome::Genome` (ctor) - at `0x47bf88`, `0x47bfa8`, `0x47bfcc`, `0x47bfec`
- `Genome::Write` - at `0x47c00c`
- `Genome::CopyGene` - at `0x47c02c`

`Write` and `CopyGene` exist in the binary as code (they would have to, to make these tags reachable), but our decompilation has not yet reached them. They are not currently mapped to function addresses in this document.

### Genome exception type

- **`Genome::GenomeException`** - RTTI TD `0x47a9b0`, mangled `.?AVGenomeException@Genome@@`. **Nested inside** the Genome class (note the nested mangling `@Genome@@`). Thrown from `Genome::Genome` failures with tag-detail strings `"genome_error"`, `"genome_old_dna"`, `"genome_too_long_gene"`.
- **`GenomeInitFailedException`** - RTTI TD `0x47a988`, mangled `.?AVGenomeInitFailedException@@`. Top-level (not nested). Thrown by the Engine when offline-mode genome init fails; the Vat has the type but no caller has been recovered yet.

---

## Open questions

1. **CAOSVar layout.** Fully unknown from this binary. It must be reconstructed from the live `engine.exe` or another Engine-SDK-linked binary that actually constructs CAOSVars. The 16-byte `FUN_00422400` candidate is **definitively not** CAOSVar - it is dead-code from the Faculty+ChemicallyActive base subobject.

2. **PersistentObject vtable slot enumeration.** We know `0x46e47c` and `0x46e4d4` are the two PersistentObject vftables, but we cannot list the function pointers stored at those addresses without a data-section dump (`classes.txt` only labels the RTTI Type Descriptors, not the vftable contents). The brief asked for `Read` and `Write` virtual slot identification; this remains TBD until a `.rdata` dump is produced.

3. **Faculty primary vs ChemicallyActive primary in Brain's MI.** The combined-base ctor `FUN_00422500` writes vftables at `+0` and `+4` but does not name them. Our inference (Faculty=primary, ChemicallyActive=secondary) is based on MSVC convention for declaration order in `class Brain : public Faculty, public ChemicallyActive` and on the destructor sequence, not on direct evidence. Reversal cannot be ruled out from this binary alone.

4. **Agent → CreatureFacultyInterface relationship direction.** The single `__RTDynamicCast(Agent_TD, CFI_TD)` at `FUN_0042ae20` proves there is a runtime-checkable relationship between Agent and CFI, but does **not** tell us whether `Agent : public CFI`, `Creature : public Agent, public CFI` (cross-cast), or some virtual-base scheme. The most common Engine pattern is the cross-cast through a Creature subclass; we have not committed to that here.

5. **Agent class size.** Field accesses go to byte `0xc84` (`piVar1[0x321]`) so Agent is at least `0xc88` bytes. The full Engine class is much larger and is not reachable in the Vat.

6. **Faculty and ChemicallyActive vtable methods.** Their virtual surfaces (other than what derived classes override in Brain) are not visible. Slot-by-slot enumeration requires a data-section dump.

7. **CreatureFacultyInterface virtual surface.** Same situation as Faculty / ChemicallyActive: pure-virtual interface assumed from name + cast usage, but we cannot enumerate its slots.

8. **Genome offsets `+0x38 .. +0x3f` and the second `+0x18` field.** The default ctor `FUN_00428cf0` zeroes them; the stream ctors do not write them. They might hold a parsed gene index, a stream cursor, or scratch pointers used during `Genome::CopyGene`. Without traces from `CopyGene` or `Write` we cannot say.

9. **Genome's `Write` and `CopyGene` function addresses.** Their tag strings (`"Genome::Write"` at `0x47c00c`, `"Genome::CopyGene"` at `0x47c02c`) confirm the methods are compiled in. They have not been located in the decompilation yet - when the Vat itself never calls them, they exist as standalone PE functions but are unreferenced from any code path we have followed.

10. **Faculty serialiser wrapper address.** The `"Type mismatch during serialisation of Faculty"` string at `0x47ba8c` implies a wrapper of the `FUN_00436fc0(this); __RTtypeid(_, 0x47b8a8); throw _` shape. We have not located its function entry point. The same caveat applies to SVRule (`0x47bd60`) and Genome (`0x47bf1c`) - their wrappers exist (they have to, to reach the throw) but were not surfaced by the same `FUN_0045a41a` pattern search that found Brain / BrainComponent / Lobe / Tract / Instinct. Possibly they use a different inline form, or possibly the search missed an indirection.

---

## Summary table

| Class | RTTI TD | Vftable | Size | Status in the Vat |
|---|---|---|---|---|
| `PersistentObject` | `0x47b888` | `0x46e47c` (primary) / `0x46e4d4` (secondary) | abstract (no own size) | Base of every engine-archive class. Vftable slot list not enumerated. |
| `CAOSVar` | `0x47ac68` | not located | unknown | RTTI only. No constructor, no usage in this binary. |
| `Agent` | `0x47c618` | not located | ≥ `0xc88` bytes | Partial. One handle accessor live; rest dead-code-eliminated. Garbage flag at `+0xb78`, type bitfield at `+0xc84`. |
| `Faculty` | `0x47b8a8` | `0x46e4a8` (inferred) | abstract | Primary base of Brain. Virtual surface not enumerable. |
| `CreatureFacultyInterface` | `0x47c630` | not located | unknown | Target of one `__RTDynamicCast` from Agent. Otherwise invisible. |
| `ChemicallyActive` | `0x47b868` | `0x46e4a0` (inferred) | abstract | Secondary base of Brain. Lobe and Tract are NOT ChemicallyActive. |
| `Instinct` | `0x47bb78` | `0x46e4e0` | `0x54` (84) bytes | Fully recovered: 3 condition slots × 20 bytes + drive/flag/strength tail. |
| `Genome` | `0x47c058` | `0x46e56c` | `0x40` (64) bytes | Layout partially recovered. File-load path traced. `Write` / `CopyGene` exist but not located. |

