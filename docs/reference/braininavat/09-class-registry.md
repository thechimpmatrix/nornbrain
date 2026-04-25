# Brain in a Vat: Class Registry

Complete RTTI class enumeration recovered from `Vat_1.9.exe`. 114 distinct types found via MSVC RTTI Type Descriptors. This is the authoritative list of every C++ class statically linked into the binary.

Generated from `analysis/braininavat/notes/classes.txt` (entries matching `RTTI_Type_Descriptor`).

## Why this matters

The Vat tool was compiled against the original Creature Labs Creatures Engine SDK, statically linked. **Every engine class in this list is decompilable from the .exe.** The most consequential find: `SVRule` and `SVRuleDlg` - the SVRule rules engine itself is in the binary, alongside `Lobe`, `Tract`, `Brain`, `Genome`, `Instinct`, `ChemicallyActive`, and `Faculty`. We have substantially more than just an IPC client; we have a viewer that contains a working SVRule implementation.

## Engine SDK classes (Creature Labs proprietary code)

These classes are the runtime data model and engine subsystems.

### Brain subsystem

| Class | Role |
|---|---|
| `Brain` | Top-level container: holds lobes, tracts, parameters |
| `BrainComponent` | Likely the abstract base class for `Lobe` and `Tract` (matches MFC-style "component" naming and the singular-noun pattern) |
| `BrainAccess` | IPC client class; talks shared-memory protocol to the Creatures Engine |
| `Lobe` | A lobe (group of neurons) within the Brain |
| `Tract` | An inter-lobe connection (group of dendrites) |
| `ReinforcementDetails` | Nested type on `Tract`: parameters governing dendrite reinforcement |
| `SVRule` | **The SVRule rules engine itself.** Compiled rule programs that drive lobe and dendrite dynamics |

### Creature subsystems

| Class | Role |
|---|---|
| `Agent` | Game agent (creature, plant, vehicle, etc.) - the universal Creatures Engine object |
| `Faculty` | Abstract base for creature subsystems |
| `CreatureFacultyInterface` | Bridges a Faculty to the rest of the creature |
| `ChemicallyActive` | Mixin/base for objects that participate in the biochemistry simulation |
| `Instinct` | A single instinct rule |
| `Genome` | A creature genome |

### Persistence and serialisation

| Class | Role |
|---|---|
| `PersistentObject` | Base class for archive-serialisable objects (probably defines the `WriteObject` / `ReadObject` virtual methods that hit `CreaturesArchive`) |
| `File` | File handle wrapper |
| `CAOSVar` | A CAOS variable (tagged union: int / float / string / agent ref) |

### Catalogue subsystem

| Class | Role |
|---|---|
| `Catalogue` | Lookup-table system: name → ID maps shared by the engine (loaded from `*.catalogue` files) |
| `Err` | Catalogue's exception type (mangled `Err@Catalogue` in symbols) |

### Exception types

| Class | Role |
|---|---|
| `BasicException` | Engine base exception |
| `FailConstructorException` | Constructor-failure marker |
| `InitFailedException` | Subsystem init failure |
| `OnlineFailedException` | Online-mode (IPC) failure |
| `AgentHandleException` | Stale Agent reference accessed |
| `GenomeException` | Generic genome error |
| `GenomeInitFailedException` | Genome failed to initialise (offline mode) |
| `FileException` | File I/O error |
| `Exception` | Probably an alias / second base - unknown which is the root |

## GUI classes (MFC-derived)

The Vat is an MFC dialog-based application.

### Application shell

| Class | Role |
|---|---|
| `MainFrame` | Top-level window (MFC `CFrameWnd` analogue) |
| `Wnd` | Base widget - likely the MFC wrapper used by Creature Labs |
| `DlgWnd` | Dialog window |
| `Edit` | Edit-control wrapper |
| `Tips` | Tooltip / status-tip system |

### Brain visualisation

| Class | Role |
|---|---|
| `BrainDlg` | Main dialog for the brain view |
| `BrainViewport` | The brain rendering surface - paints lobes, tracts, dendrites, neurons |
| `Viewport` | Base viewport |
| `TextViewport` | Text-output viewport (probably for textual brain dumps) |

### Per-entity inspectors

| Class | Role |
|---|---|
| `LobeDlg` | Lobe details dialog |
| `LobeGraphDlg` | Plot lobe variables over time |
| `LobeInputDlg` | Manipulate lobe inputs (offline mode "drive synthetic input" feature) |
| `TractDlg` | Tract details |
| `NeuronVarDlg` | Neuron variable inspector / setter |
| `NeuronVarGraphDlg` | Graph a neuron variable over time |
| `DendriteVarDlg` | Dendrite variable inspector / setter |
| `DendriteVarGraphDlg` | Graph a dendrite variable over time |
| `VarDlg` | Probably the base class for Var*Dlg |
| `VarGraphDlg` | Probably the base class for Var*GraphDlg |
| `GraphDlg` | Base class for graph dialogs |
| `Grapher` | Plotting widget used by graph dialogs |

### SVRule editing

| Class | Role |
|---|---|
| `SVRuleDlg` | **SVRule program editor / inspector.** Probably mirrors what the original Creatures genetic-engineer tools showed for SVRule programs |

### Misc dialogs

| Class | Role |
|---|---|
| `GeneAgeDlg` | Set creature age (offline mode, before loading the brain at adult/baby/etc.) |
| `ThreshHoldDlg` | View > Threshold > Non-Zero (per the readme) |

### Errors specific to Viewport

| Class | Role |
|---|---|
| `InitFailedException@BrainViewport` | Brain viewport couldn't initialise (offline mode failure) |
| `OnlineFailedException@BrainViewport` | Online-mode handshake failure |

## STL / MSVC runtime classes (40+ types)

Statically-linked from the MSVC C++ runtime (~6.0 era based on the type set). These are not interesting for our purposes but documented here for completeness so future analyses can ignore them quickly:

- **String/stream:** `basic_string`, `basic_streambuf`, `basic_istream`, `basic_ostream`, `basic_iostream`, `basic_filebuf`, `basic_ifstream`, `basic_ofstream`, `basic_ios`, `ios_base`, `strstream`, `strstreambuf`, `istrstream`, `ostrstream`
- **Locale:** `_Locimp`, `facet`, `ctype`, `ctype_base`, `codecvt`, `codecvt_base`, `collate`, `numpunct`, `num_get`, `num_put`, `messages`, `messages_base`, `time_base`, `time_get`, `time_put`, `money_base`, `money_get`, `money_put`, `moneypunct`, `_Mpunct`
- **Exceptions:** `exception`, `bad_alloc`, `bad_cast`, `bad_typeid`, `__non_rtti_object`, `runtime_error`, `logic_error`, `out_of_range`, `length_error`, `failure`
- **Other:** `type_info`

Each STL type is templated for both `char` and `unsigned_short`, hence the duplication seen in raw `classes.txt`.

## Cross-reference: classes vs documents

| Class | Documented in |
|---|---|
| `BrainAccess`, IPC | [03-ipc-protocol.md](03-ipc-protocol.md) |
| `Brain`, `Lobe`, `Tract`, `ReinforcementDetails`, `BrainComponent` | [04-data-model.md](04-data-model.md) |
| `BrainDlg`, `BrainViewport`, all `*Dlg`, `MainFrame`, `Viewport` | [05-gui-inventory.md](05-gui-inventory.md) |
| `CreaturesArchive`*, `Catalogue`, `Err`, `File`, `FileException` | [06-file-formats.md](06-file-formats.md) |
| `SVRule`, `SVRuleDlg`, `Tract::ReinforcementDetails` | [10-svrule-engine.md](10-svrule-engine.md) |
| `Agent`, `Faculty`, `CreatureFacultyInterface`, `ChemicallyActive`, `Instinct`, `Genome`, `PersistentObject`, `CAOSVar` | [13-engine-sdk-classes.md](13-engine-sdk-classes.md) |
| Full inheritance graph for all 102 RTTI classes with CHDs | [15-rtti-inheritance.md](15-rtti-inheritance.md) |
| `PersistentObject`, `CAOSVar` | _(supporting types - see [04-data-model.md](04-data-model.md))_ |

\* `CreaturesArchive` is not in the RTTI list because it likely doesn't have virtual methods (it's the archive *implementation*, not a polymorphic type).

## Open questions (resolved)

All seven open questions from earlier passes are now resolved:

1. ~~`SVRule` class~~ → [10-svrule-engine.md](10-svrule-engine.md). Interpreter at `FUN_00421830`; programs are 16 lines × 16 bytes in memory.
2. ~~`Faculty` / `CreatureFacultyInterface`~~ → [13-engine-sdk-classes.md](13-engine-sdk-classes.md). Brain inherits from Faculty (and ChemicallyActive). Faculty's vftable is at `0x46e4a8`.
3. ~~`ChemicallyActive`~~ → [13-engine-sdk-classes.md](13-engine-sdk-classes.md). Lobes/Tracts/Dendrites are *not* ChemicallyActive - only the Brain (via Faculty) is.
4. ~~`Instinct`~~ → [13-engine-sdk-classes.md](13-engine-sdk-classes.md). 84-byte object, three 20-byte condition slots, drive/strength tail.
5. ~~`PersistentObject` virtual methods~~ → [13-engine-sdk-classes.md](13-engine-sdk-classes.md). Polymorphic `Read`/`Write` are inherited by Brain/Lobe/Tract/Genome/Instinct/SVRule.
6. ~~`CAOSVar`~~ → [13-engine-sdk-classes.md](13-engine-sdk-classes.md). RTTI present but unused in this binary; layout requires a different binary or runtime capture to confirm.
7. ~~`Err@Catalogue` / `Exception` / `BasicException`~~ → [15-rtti-inheritance.md](15-rtti-inheritance.md). All custom exceptions follow `<Custom> → BasicException → std::exception`.

The remaining gaps (BrainViewport hardcoded lobe coordinates, SVRule opcode mnemonics, openc2e BRN: command implementation) are tracked in the [README status table](README.md#status).
