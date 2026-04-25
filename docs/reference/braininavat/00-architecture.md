# Brain in a Vat: Architecture Summary

Result of headless Ghidra full analysis (3,141 functions, 3,140 decompiled, 875 strings, 1,381 namespaced symbols, 6 imported DLLs).

## Binary at a glance

| Property | Value |
|---|---|
| File | `Vat_1.9.exe` (581,689 bytes) |
| Format | PE32 i386 GUI, 6 sections |
| Compiler | Microsoft Visual C++ (matches `windows_vs12_32` archive in Ghidra; in practice this is VC++ 6.0 era, 1999-2000) |
| Symbols | RTTI intact, full C++ class names recoverable, MSVC name mangling |
| Linkage | Statically linked: MFC, zLib 1.13, Creatures Engine SDK fragments |
| Imports | KERNEL32, USER32, GDI32, COMCTL32, COMDLG32, ADVAPI32 only - no WinSock, no MFCxx.dll |

The lack of dynamic dependencies means there is no DLL boundary protecting any of the logic. Everything is local code, freely patchable.

## Class hierarchy (recovered from RTTI)

**GUI layer (MFC dialogs):**
`BrainDlg`, `LobeDlg`, `LobeGraphDlg`, `LobeInputDlg`, `TractDlg`, `DendriteVarDlg`, `DendriteVarGraphDlg`, `NeuronVarDlg`, `NeuronVarGraphDlg`, `BrainViewport`

**Engine SDK (statically linked from Creature Labs codebase):**
`Brain`, `BrainAccess`, `BrainComponent`, `Lobe`, `Tract`, `Agent`, `CAOSVar`, `Catalogue`

**Exceptions:**
`InitFailedException@BrainViewport`, `OnlineFailedException@BrainViewport`, `Err@Catalogue`, `AgentHandleException`, `BasicException`

The `BrainAccess` class is the IPC client. The `Brain`, `Lobe`, `Tract` classes are the runtime data model used in both online and offline modes.

## IPC protocol (the smoking gun)

Decompilation of `FUN_0043f8f0` reveals the complete handshake. The Vat tool opens four named Win32 kernel objects, all sharing a common name prefix derived from the game (read from registry `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine`):

| Object | Win32 API | Suffix |
|---|---|---|
| Mutex | `OpenMutexA` | `<name>_mutex` |
| Request event | `OpenEventA` | `<name>_request` |
| Result event | `OpenEventA` | `<name>_result` |
| Shared memory | `OpenFileMappingA` + `MapViewOfFile` | `<name>_mem` |

Magic bytes at offset 0 of shared memory: **`c2e@`**. If the magic mismatches, the handshake fails.

This is the original CyberLife / Creature Labs Win32 IPC mechanism. **openc2e (our NB engine) does not implement it.** That is what `cc-ref.yaml engine.retired: ["GOG engine.exe", "Win32 shared memory", "Steam"]` refers to.

## Operating modes

**Online mode:** opens the named objects above, sends a request through shared memory, waits on `<name>_result`, reads response. The engine is the server.

**Offline mode:** parses a creature genome (`CreaturesArchive` format, zLib 1.13 compressed) directly from disk. No engine required. This is why the readme says you can examine a brain "in a vat" - it is literally the offline path. Strings:
- `Creatures Evolution Engine - Archived information file. zLib 1.13 compressed.`
- `CRA0002: Not a creatures archive`
- `CreaturesArchive::ReadFloatRef`, `CreaturesArchive::WriteFloatRef`

## Brain data model (visible in strings + class symbols)

- **Lobes** identified by name; each lobe contains neurons with variables and dendrites
- **Tracts** connect source lobe to destination lobe; each tract contains directional dendrites
- **Dendrites** are addressed by index `(d:(slot)source->dest, name)` - format strings confirm this is the same model used by the engine
- **Neurons** have variables that can be graphed over time
- **Action Script To Neuron Mappings** - confirms the action-to-neuron mapping table (matches what we see in the SVRule reference)

The data model maps 1:1 onto our existing NORNBRAIN reference (`docs/reference/svrule-brain-complete-reference.md`). The Vat tool is essentially an MFC viewer over the same Lobe/Tract/Neuron/Dendrite types we already know.

## What it is, summarised

A standalone PE32 with statically-linked engine SDK code. Two paths:
1. **Online:** speaks the c2e Win32 shared-memory protocol against a running engine.
2. **Offline:** loads a CreaturesArchive blob from disk and runs the brain locally inside the Vat process.

No network, no DLL boundary, no obfuscation, RTTI intact.
