# Brain in a Vat: RTTI Inheritance Hierarchy

The full class inheritance graph for `Vat_1.9.exe`, recovered by walking MSVC RTTI metadata: each Type Descriptor's Complete Object Locator → Class Hierarchy Descriptor → Base Class Array → derived Base Class Descriptors. 102 of 115 classes have CHD records (the remaining 13 are STL stub types whose RTTI was elided by the linker).

Extraction script: [scripts/DumpRttiHierarchy.java](../../../analysis/braininavat/scripts/DumpRttiHierarchy.java). Raw output: [notes/rtti_hierarchy.txt](../../../analysis/braininavat/notes/rtti_hierarchy.txt) (498 lines, every class with full BCA flattened) and [notes/rtti_inheritance_summary.tsv](../../../analysis/braininavat/notes/rtti_inheritance_summary.tsv) (per-class direct base list).

This is the authoritative inheritance map for every engine SDK and GUI class statically linked into the Vat.

## Engine SDK class hierarchy

```
PersistentObject (root for serialisable engine objects)
├── Faculty                    [+ ChemicallyActive at offset +4]
│   └── Brain                  [+ ChemicallyActive at offset +4]
├── BrainComponent
│   ├── Lobe
│   └── Tract
├── Genome
├── Instinct
└── SVRule

ChemicallyActive (mixin)
   ↑ inherited by Faculty (and therefore Brain)

Tract::ReinforcementDetails    [standalone - no virtual hierarchy]

CAOSVar                        [standalone]
File                           [standalone]
```

### Headline observations

1. **`Brain` is a `Faculty` AND `ChemicallyActive` (multiple inheritance).** The Brain participates in both the Faculty `Tick` interface (so the engine ticks every faculty uniformly) and the biochemistry simulation (so brain state can read/write chemicals directly, not just via input neurons). The `ChemicallyActive` subobject sits at offset `+4` inside the Brain.

2. **`Faculty` itself is `PersistentObject + ChemicallyActive`.** This means *every* Creatures Engine faculty (not just Brain - also subsystems like Reproduction, Senses, etc., which the Vat doesn't ship) is automatically biochemistry-aware. The chemistry/faculty coupling is a fundamental design choice baked into the SDK, not a Brain-specific add-on.

3. **`Lobe` and `Tract` both extend `BrainComponent → PersistentObject`.** Confirms what the data-model agent suspected: `BrainComponent` is the abstract base, holds the SVRule program slots at offset `+0x10` and `+0x128` (per `04-data-model.md`), and provides the polymorphic `Read`/`Write` virtuals via PersistentObject.

4. **`SVRule` is a `PersistentObject`.** SVRule programs serialise/deserialise via CreaturesArchive's polymorphic dispatch. This is consistent with the `"Type mismatch during serialisation of SVRule"` error string at `0x0047bd60`.

5. **`Instinct` is a `PersistentObject`.** Each instinct rule is its own serialisable object (matches the SDK pattern of one-object-per-rule).

6. **`Genome` is a `PersistentObject`.** Genomes are loaded/saved as CreaturesArchive blobs.

7. **`CAOSVar`, `File`, `ChemicallyActive`, `Tract::ReinforcementDetails` are standalone** - no inheritance. `CAOSVar` is a tagged-union value type (no polymorphism). `File` is probably a thin wrapper. `ReinforcementDetails` is the parameter struct nested inside `Tract`.

## GUI class hierarchy

```
Wnd (base widget)
├── Edit
├── DlgWnd
│   ├── GeneAgeDlg
│   └── ThreshHoldDlg
├── Viewport
│   ├── BrainViewport       [+ BrainAccess at offset +428]
│   └── TextViewport
├── MainFrame
├── Tips
├── BrainDlg                [standalone - no Wnd base in BCA, see below]
├── Grapher
└── GraphDlg                [+ Grapher subobject]
    ├── LobeGraphDlg        [+ BrainAccess +736, BrainDlg +732]
    ├── VarGraphDlg
    │   ├── DendriteVarGraphDlg
    │   └── NeuronVarGraphDlg
    └── (others)

VarDlg                      [+ BrainAccess +124, BrainDlg +120, Wnd]
├── DendriteVarDlg
└── NeuronVarDlg

SVRuleDlg                   [+ BrainAccess +124, BrainDlg +120, Wnd]
├── LobeDlg
└── TractDlg

LobeInputDlg                [+ BrainAccess +124, BrainDlg +120, Wnd]
```

### Headline observations

1. **`BrainViewport` extends `Viewport + Wnd + BrainAccess`.** The viewport class is itself an IPC client (with `BrainAccess` mixed in at offset `+428`). It can issue CAOS commands directly without going through a separate IPC layer. This explains why `BrainAccess` appears in many other dialog hierarchies too - the IPC capability is mixed into anything that talks to the engine.

2. **Every `*Dlg` class that displays brain data inherits `BrainAccess`.** Specifically: `LobeDlg`, `TractDlg`, `LobeGraphDlg`, `LobeInputDlg`, `NeuronVarDlg`, `NeuronVarGraphDlg`, `DendriteVarDlg`, `DendriteVarGraphDlg`, `SVRuleDlg`, `VarDlg`, `VarGraphDlg`. This is a heavy-handed multiple-inheritance pattern - every dialog has its own copy of the IPC handles. Practically, this lets each dialog talk to the engine independently rather than routing through a shared singleton.

3. **`SVRuleDlg` is the parent of `LobeDlg` and `TractDlg`.** Both lobe and tract dialogs inherit the SVRule editor UI as their base - meaning when you open a Lobe dialog, you get the SVRule editor for that lobe's rule program automatically. The lobe-specific UI (neuron count, neuron names, etc.) is layered on top of the SVRule editor.

4. **`*GraphDlg` classes inherit `GraphDlg → Grapher`.** All time-series plots share a common Grapher widget (the circular-buffer `Polyline` plotter at `FUN_00443aa0`). A clean reusable pattern.

5. **`BrainDlg` appears as a base class with `numBases=1`** - its single base is itself, suggesting the Vat's RTTI for it doesn't include a parent. In practice the decompilation shows it acts as a window class, but its CHD records no public base. Likely the parent (probably `Wnd` or `MainFrame`) is a private base, omitted from RTTI's "public-only" view.

6. **`BrainAccess` appears as a direct base of many classes (mdisp varies).** Each `mdisp` value is the byte offset of the `BrainAccess` subobject within the derived class. For example:
   - `BrainViewport`: `BrainAccess` at `+428`
   - `LobeDlg`, `TractDlg`, `LobeInputDlg`: `BrainAccess` at `+124` (so all three have the same memory layout for the IPC handles)
   - `LobeGraphDlg`, `*GraphDlg` family: `BrainAccess` at `+736` or `+124` depending on class

This information is useful if we want to interoperate at the binary level - for example, to inject our own state into a `BrainAccess` subobject from outside the Vat process. Probably not relevant for our reimplementation work, but documented for completeness.

## Exception hierarchy

All custom exceptions in the Vat follow a uniform pattern:

```
std::exception (STL)
└── BasicException
    ├── AgentHandleException
    ├── Catalogue::Err
    ├── CreaturesArchive::Exception
    ├── File::FileException
    ├── Genome::GenomeException
    ├── GenomeInitFailedException     [bypasses BasicException, see below]
    ├── BrainViewport::InitFailedException     [also bypasses]
    ├── BrainViewport::OnlineFailedException   [also bypasses]
    └── FailConstructorException     [also bypasses]
```

**Note:** Looking at the raw dump, four exception types (`GenomeInitFailedException`, `BrainViewport::InitFailedException`, `BrainViewport::OnlineFailedException`, `FailConstructorException`) appear in the strings as `.?AV...` mangled names but were not present with full CHD records in the recovery. They are likely thin wrappers around `BasicException` whose RTTI was elided.

## STL inheritance (informational)

The MSVC C++ runtime classes also have RTTI. Their hierarchy is standard and not interesting for our purposes, but the data is in [notes/rtti_hierarchy.txt](../../../analysis/braininavat/notes/rtti_hierarchy.txt) for completeness. Notable patterns:

- `runtime_error → exception`, `logic_error → exception`, `out_of_range → logic_error → exception`, etc.
- `std::ctype<char> → ctype_base → locale::facet`
- `basic_filebuf<T> → basic_streambuf<T>`, etc.

## Per-class direct-base summary

The flat TSV at [notes/rtti_inheritance_summary.tsv](../../../analysis/braininavat/notes/rtti_inheritance_summary.tsv) gives one row per class with its direct bases comma-separated. Useful for grep/programmatic queries. Schema:

```
class<TAB>numBases<TAB>direct_bases<TAB>attrs
```

`numBases` is the count of entries in BCA (including self at index 0). `direct_bases` is the comma-separated list of names from BCA[1..n-1]. MSVC orders BCA entries depth-first, most-derived-first, which means the *first* non-self entry is the primary direct base; subsequent entries are either further ancestors or other branches in multiple-inheritance.

## What this enables

1. **Method-call attribution.** When reading decompilations, we can now attribute calls to virtual method slots to the right class. Example: a call through `BrainViewport`'s vtable slot 8 likely targets a `Viewport` virtual (because BrainViewport's vtable is layered: Wnd virtuals first, then Viewport additions, then BrainViewport additions).

2. **Memory layout reconstruction.** With `mdisp` values per base, we can fully reconstruct each derived class's memory layout. For example, `BrainViewport`'s instance has a `Wnd` subobject at `+0`, a `Viewport`-specific block, and a `BrainAccess` subobject at `+428`. Combined with the data-model agent's struct-size findings, this gives us byte-precise layouts.

3. **Confirms data-model assumptions.** The agent who wrote `04-data-model.md` correctly inferred that `BrainComponent` is the base for `Lobe` and `Tract`. The CHD walk confirms this directly.

4. **Reveals SDK design.** The `Faculty + ChemicallyActive` mixin pattern repeats everywhere. The SDK is built on a small number of base classes (`PersistentObject`, `Wnd`, `Faculty`, `ChemicallyActive`, `BrainAccess`) plus heavy multiple-inheritance to compose them. Worth keeping in mind if we ever want to build a similar object model.
