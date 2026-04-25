# Brain in a Vat: GUI Inventory

Inventory of the dialog and viewport surface of `Vat_1.9.exe`, recovered from the headless Ghidra decompilation under `<PROJECT_ROOT>/analysis/braininavat/notes/`. Companion to `00-architecture.md`. Cross-cuts decompiled file paths under `notes/decompiled/<address>_FUN_<address>.c` and string addresses listed in `notes/strings.txt`.

## Conventions

- Addresses are RVAs in the loaded image, matching the file names under `notes/decompiled/`.
- "Offset 0xNNN" inside a class refers to a byte offset from the `this` pointer of the class as observed in decompiled code, not a documented field. Field meanings are inferred from how the offset is used.
- Win32 / MFC boilerplate is summarised, not transcribed. Vat-specific logic is cited per function.

## 1. Application shell

### 1.1 Entry chain

| Stage | Address | Notes |
|---|---|---|
| CRT entry | `0045b68c` | `entry()` shim, sets up CRT then calls WinMain |
| WinMain | `FUN_0041a7a0` | Allocates `MainFrame` (size 0x1d4), reads "Default Game" via `WhichEngine` (registry path `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine`), calls `MainFrame::Create`, `ShowWindow`, then enters a stock `GetMessageA / IsDialogMessageA / TranslateMessage / DispatchMessageA` pump |
| MainFrame ctor | `FUN_00411a80` | Sets title to `s_CyberLife_Vat_Kit_for_Creatures_3_0047aef0` ("CyberLife Vat Kit for Creatures 3 v1.8"), window style `0x020F0000` (`WS_OVERLAPPEDWINDOW | WS_VISIBLE`), registers a window class, loads icon resource 0x78, default cursor IDC_ARROW (0x7F00) |
| MainFrame init | `FUN_00411d50` | Creates the menu, status bar, toolbar (see below) |

### 1.2 Window classes registered

`RegisterClassExA` is called once via `FUN_0041acd0` with the `WNDCLASSEXA` blob held by the `Wnd` base class. RTTI-named GUI classes that derive from `Wnd` (per `notes/symbols.txt`):

- `MainFrame` (TD `0047aee0`)
- `BrainDlg` (TD `0047a3e0`)
- `BrainViewport` (TD `0047a968`, also derives from `Viewport` at `0047a958`)
- `LobeDlg` (TD `0047a448`), `TractDlg` (`0047a460`)
- `LobeGraphDlg` (`0047ad40`), `LobeInputDlg` (`0047ad90`)
- `NeuronVarDlg` (`0047b5b8`), `DendriteVarDlg` (`0047b5d8`)
- `NeuronVarGraphDlg` (`0047b6d0`), `DendriteVarGraphDlg` (`0047b6f0`)
- `ThreshHoldDlg` (`0047b3c0`), `Tips` (`0047b3e8`), `GeneAgeDlg` (`0047aca0`)
- `SVRuleDlg` (`0047a438`), `VarDlg` (`0047b418`), `VarGraphDlg` (`0047b600`), `GraphDlg` (`0047ad30`)
- `Grapher` (`0047ad18`), `TextViewport` (`0047b390`), `DlgWnd` (`0047ac88`)

Not all of these are listed in the brief. `ThreshHoldDlg`, `Tips`, `GeneAgeDlg`, `SVRuleDlg`, `VarDlg`, `VarGraphDlg`, `GraphDlg`, `Grapher`, `TextViewport`, and `DlgWnd` exist in RTTI but were outside the named-dialog scope: their behaviour is summarised below where it surfaces, not exhaustively reverse-engineered.

### 1.3 Menu

`MainFrame::Create` (`FUN_00411d50`) loads two menu resources from the executable:

| Resource ID | Use | Stored at MainFrame offset |
|---|---|---|
| `0x76` | Online menu (full File menu including the Select-a-Creature submenu) | `0x17c` |
| `0x6e` | Offline menu (no creature list) | `0x178` |

The default attached menu is `0x6e` (offline). On successful Connect-to-Creatures the code switches to `0x17c`. A submenu is built dynamically with `CreateMenu` and inserted into the File menu at index 0 with the placeholder text `"Select a Creature"` (string at `0047af2c`); this submenu is repopulated by `FUN_00412ac0` with one entry per creature returned by the CAOS `ENUM 0 0 0 DOIF TYPE TARG = 7` query.

The full View / Threshold and right-click menus belong to `BrainViewport`. `BrainViewport` holds an HMENU at offset `0x6e0` containing four sub-menus selected by hit-test type (see Section 3.5).

### 1.4 Toolbar

`FUN_00411e10` calls `CreateToolbarEx` once after `InitCommonControls`. Seven `TBBUTTON` slots, bitmap base ID `0x6c`, button size 16x15. The toolbar HWND is stored at MainFrame offset `0x19c`. Button command IDs and their handlers (cross-referenced with `FUN_00412280` and `FUN_0041a320`):

| Index | Cmd ID | Function | Handler |
|---|---|---|---|
| 0 | `0x9c52` | Zoom in (doubles `zoomFactor` at viewport offset `0x190`) | `FUN_0041a620` via `FUN_0041a320` |
| 1 | `0x9c53` | Zoom out (halves `zoomFactor`) | `FUN_0041a6d0` via `FUN_0041a320` |
| 2 | separator | (TBSTYLE_SEP, `fsState=0x04`) | n/a |
| 3 | `0x9c54` | Play (starts a 250 ms `SetTimer` loop at MainFrame offset `0x1ac`) | `FUN_00412280` case `0x9c54` |
| 4 | `0x9c55` | Single-step (one tick, no timer) | `FUN_00413330` |
| 5 | `0x9c57` | Loop toggle (sets bool at MainFrame offset `0x1b1`) | `FUN_00412280` case `0x9c57` |
| 6 | `0x9cc2` | Instinct processing toggle ("IN" button, sets bool at offset `0x1b2`, calls `FUN_00409800` on `BrainViewport`) | `FUN_00412280` case `0x9cc2` |

The Pause / Stop button (`0x9c83`) routes through the menu but is not in the toolbar table; it calls `FUN_00413240` which kills the play timer and resets the four toolbar buttons via `TB_CHECKBUTTON` (message `0x401`).

### 1.5 Status bar

`CreateStatusWindowA` once in `FUN_00411d50`, stored at MainFrame offset `0x1a0`. Status text is set with `WM_SETTEXT` (message `0x0c`) at:

- "Connecting to creatures" (`0047b050`) - start of online handshake (`FUN_004129d0`)
- "Loading genome" (`0047b200`) - start of genome open (`FUN_00412fe0`)
- "no brain loaded" (`0047b210`), "Connected to Creatures" (`0047b220`), "In a Vat" (`0047b238`) - used by `FUN_00413370` and friends
- `"%s, %s."` (`0047b244`) - formatted creature name display

## 2. BrainDlg

`BrainDlg` (TD `0047a3e0`) is the dialog that hosts a `BrainViewport` and the per-entity dialog children that float above it. The brief listed it as the "main dialog" but the constructed top-level window is `MainFrame`. `BrainDlg` is the *brain workspace* dialog, instantiated when a brain is loaded (online or offline). Evidence:

- `BrainAccess` is referenced from `BrainDlg`'s vftable area (`PTR` near `0047a3e8`): the IPC client lives here.
- `BrainDlg` dispatches the per-entity dialog factory functions (`FUN_004015f0` for LobeGraphDlg, `FUN_00401070` for NeuronVarDlg, `FUN_004011d0` for DendriteVarDlg, `FUN_00401330` for NeuronVarGraphDlg, `FUN_00401490` for DendriteVarGraphDlg, `FUN_00401a40` for LobeInputDlg). All take `(this=BrainDlg*, ...)` as `__thiscall`.
- The de-duplicating helper `FUN_00401bd0(this, target, kind)` is called by every dialog factory before `operator new`: it scans a doubly-linked list of open child dialogs (head pointer at BrainDlg offset `+4`) and surfaces an existing window if `(target, kind)` already has one. Avoids opening duplicate Variables / Graph windows.

### 2.1 Per-entity dialog factory entry points (BrainDlg methods)

| Func | Resulting dialog | Title format string | Kind id |
|---|---|---|---|
| `FUN_00401070` | `NeuronVarDlg` | "Variables Neuron:%d, %s" (`0047a330`) | (lobe-id, neuron-id) tuple |
| `FUN_004011d0` | `DendriteVarDlg` | "Variables Dendrite:%d, %s" (`0047a348`) | dendrite tuple |
| `FUN_00401330` | `NeuronVarGraphDlg` | "Graph Neuron:%d, %s" (`0047a364`) | neuron tuple |
| `FUN_00401490` | `DendriteVarGraphDlg` | "Graph Dendrite:%d, %s" (`0047a378`) | dendrite tuple |
| `FUN_004015f0` | `LobeGraphDlg` | "Graph Lobe:%s" (`0047a390`) | lobe id |
| `FUN_00401a40` | `LobeInputDlg` | format derived from "Inputs for lobe: " (`0047a3b8`) | lobe id |

All six follow the same pattern: dedupe via `FUN_00401bd0`, `operator new`, construct via per-class ctor at `FUN_0040f530` / `FUN_0040fe80` / etc., then push the new HWND into the linked list and bump `*(this+8)` (the open-child count).

### 2.2 BrainDlg-to-BrainViewport relationship

`BrainViewport` is referenced from `BrainDlg` at offset `+0x7ac` in the viewport, by being passed as `param_1` to factory functions: e.g. `FUN_004073f0` (right-click handler) is a `BrainViewport` method that calls `FUN_004015f0(*(viewport+0x7ac), ...)`, dereferencing the back-pointer to BrainDlg. So:

- BrainDlg owns the BrainAccess and the open child-dialog list.
- BrainViewport is a child window of BrainDlg, holding a back-pointer to its parent.
- Right-click commands in the viewport invoke BrainDlg factory methods to spawn graph / variable dialogs.

The `BrainAccess` pointer lives at BrainDlg offset `+0x14` (read at `FUN_004015f0` line 38: `*(undefined4 *)((int)this + 0x14)` is passed into the LobeGraphDlg constructor).

## 3. BrainViewport widget

The rendering surface. Key entry points:

| Function | Role |
|---|---|
| `FUN_00405d00` | `OnPaint`: handles `WM_PAINT`, double-buffered |
| `FUN_00406900` | Lobe-rectangle drawer (one neuron-rectangle per call iteration) |
| `FUN_00406d80` | Tract-line drawer |
| `FUN_004070a0` | Rectangle outline helper (4x `LineTo` for a closed quad) |
| `FUN_00410ab0` | Catalogue lookup: builds the per-lobe layout from `Brain Lobe Quads`, `Brain Lobes`, `Brain Lobe Neuron Names`, `LobeNames` |
| `FUN_004073f0` | Right-click context-menu builder + `TrackPopupMenu` |
| `FUN_004054a0` | `WM_COMMAND` handler (View / right-click commands) |
| `FUN_00404d30` | Tick / update loop: sends `DBG: TOCK`, pulls fresh lobe and tract state, calls `RedrawWindow` |

### 3.1 Paint pipeline (`FUN_00405d00`)

1. `BeginPaint` to get the foreground HDC.
2. `CreateCompatibleDC` and `CreateCompatibleBitmap` sized to the viewport client area (`*(this+0x17c)` x `*(this+0x178)` plus 1). All subsequent drawing happens to the back-buffer.
3. Stock objects selected: WHITE_PEN (7) and a stock white brush (4). A solid white `Rectangle` clears the back-buffer.
4. The font handle stored at `*(this+0x76c)` is selected. Origin / extent values for the viewport scroll position are computed (offsets `0x6e4`, `0x6e8`, `0x6ec`, `0x6f0`, `0x6f4`, `0x6f8`).
5. Two rendering passes, branched on `*(this+0x700)`:
   - `0x700 == -1`: simple "all dendrites" pass: walks tracts, calls `MoveToEx` then `LineTo` for each dendrite using the colour at `*(*(this+0x70c) + lobeId*4)`.
   - `0x700 != -1`: "filtered" pass: tracts then lobes, twice. First pass draws the unfiltered set, second pass over-draws the visible-only set. This is the path used when a Threshold mode is active.
6. For each lobe, `FUN_00406900` is called with the lobe's neuron array, the colour palette pointer (`*(this+0x70c)`), and the brush palette pointer (`*(this+0x73c)`).
7. Per-neuron labels are drawn with `DrawTextA`: `SetTextColor` is computed from a packed RGB at neuron offsets `0x280`, `0x284`, `0x288` (red, green, blue bytes), or replaced with `0xC0C0C0` (light grey) if the neuron is hidden or below threshold.
8. Final composite: `BitBlt` from back-buffer DC to foreground DC with `SRCCOPY` (`0xCC0020`), `EndPaint`, restore original objects, `DeleteDC` and `DeleteObject` cleanup.

### 3.2 Threshold mode

Stored at viewport offset `0x704` (mode int) and `0x708` (threshold float):

| Mode | Meaning | Menu ID |
|---|---|---|
| 0 | None: show everything | `0x9c67` |
| 1 | Non-Zero: hide neurons whose current value is exactly zero | `0x9c68` |
| 2 | Above: hide neurons with value <= threshold | `0x9c69` |
| 3 | Below: hide neurons with value >= threshold | `0x9c6a` |
| 5 | Custom value | `0x9c6b` (likely opens `ThreshHoldDlg` to edit `0x708`) |

The View menu item for Threshold (`0x9ca2`) is checked via `CheckMenuItem(... 0x9ca2, 8)` after a mode change in `FUN_004054a0`. The threshold filter is applied inside `FUN_00406900` at lines 56-59: `iVar3 = *(int *)((int)this + 0x704)` then four-way branch on the value.

### 3.3 Lobe rendering (`FUN_00406900`)

For each neuron `i` in a lobe:

1. Compute grid position: `col = i % lobeWidth + lobeOriginX`, `row = i / lobeWidth + lobeOriginY` (lobe width at lobe-struct offset `0x278`, origin at `0x270`/`0x274`).
2. Float-to-int cast using `__ftol`, scale by `*(this+0x194)` (cell width), `*(this+0x198)` (cell height), `*(this+400)` (zoom factor).
3. `SelectObject` the matching pen and brush from the per-state palette (`param_3` and `param_4`, indexed by neuron state class).
4. `Rectangle(hdc, x0, y0, x1, y1)` for the neuron quad.

Lobe-level rectangles are drawn the same way (the helper is shared with whole-lobe dimming when the lobe is hidden via right-click "Hide").

### 3.4 Tract rendering (`FUN_00406d80`)

For each dendrite in a tract: compute source-neuron centre, dest-neuron centre, `MoveToEx` to source, `LineTo` to dest. The pen is selected from `*(*(this+0x70c) + srcLobeId*4)` (one pen per source lobe colour).

### 3.5 Right-click hit-type discriminator

`FUN_004073f0` is called from the `WM_RBUTTONDOWN` handler (not located in detail; standard MFC routing) with click coordinates `(param_3, param_4)`. The hit-test result is stored at viewport offset `0x784` and selects which of the four pre-loaded sub-menus (from HMENU at `0x6e0`) is shown:

| `*(this+0x784)` | Sub-menu | What was clicked |
|---|---|---|
| 1 | `GetSubMenu(hMenu, 2)` | Neuron |
| 2 | `GetSubMenu(hMenu, 0)` | Lobe |
| 3 | `GetSubMenu(hMenu, 1)` | Tract |
| 4 | `GetSubMenu(hMenu, 3)` | Dendrite |
| default | dynamic submenu of "Show lobe X" / "Show tract Y" entries | Background (no entity hit) |

The default branch walks the per-lobe and per-tract hidden-flag arrays at offsets `0x79c` and `0x798` (each entry is a 3-byte struct with the third byte being the hidden flag). For every hidden entity, an `AppendMenuA` entry of the form "Show lobe %s" or "Show tract %s" is added with command id `1000 + index`. If nothing is hidden, "No Hidden Objects" (`0047a84c`) is appended as a disabled item.

`EnableMenuItem(hMenu_00, 0x9ca4, ...)` greys out the "Variables" right-click item conditionally. `0x9ca4` is the right-click "Variables" command which routes through `FUN_004054a0` and opens `NeuronVarDlg` or `DendriteVarDlg` depending on the saved hit type.

### 3.6 Tick (`FUN_00404d30`)

Called by the play timer (`SetTimer` at MainFrame offset `0x1ac`, 250 ms period from `FUN_00412280`). For each tick:

1. Sends `execute\nDBG: TOCK\n` (string at `0047a80c`/`0047a820`) to the engine via the BrainAccess client.
2. Walks each lobe, calls per-lobe state pull (`FUN_00409160`) to repopulate neuron values.
3. Walks each tract, calls `FUN_004092c0` for tract state.
4. For each dendrite, compares pulled `srcId/destId` against the cached values at viewport offset `0x7a8` and animates if they differ (the migrating-dendrite animation the readme refers to).
5. `RedrawWindow(hwnd, NULL, NULL, 0x121)` → `RDW_INVALIDATE | RDW_UPDATENOW | RDW_ERASE`.

In offline mode (`DAT_0048128d == '\0'`) the engine path is bypassed; the brain runs locally inside the Vat process via `FUN_00401ca0` and the `Brain` SDK call at vftable offset `0x1c`.

### 3.7 Init / Online failure

`InitFailedException@BrainViewport` (TD `0047a9e0`) and `OnlineFailedException@BrainViewport` (TD `0047aac8`) are thrown when:

- Catalogue lookup in `FUN_00410ab0` cannot find a tag (e.g. lobe name in `Brain Lobe Quads`): `InitFailedException`. Title bar: "Brain Initialization Error" (`0047aa08`).
- IPC fetch in tick fails (the message "Could not download brain.\nDisconnected." at `0047aaf4` and title "Brain Update Error" at `0047ab1c`): `OnlineFailedException`.

## 4. Per-entity dialogs

All inherit from `DlgWnd` and follow the standard MFC template-loaded pattern (resource ID + `CreateDialogParamA` indirectly via `Wnd::Create`). Common controls used (string IDs in `notes/strings.txt`): `static`, `button`, `listbox`, `msctls_trackbar32`, `graph`, `MS Sans Serif` font face.

The factory functions cited in 2.1 instantiate these. Internal layout has not been traced for every dialog: where construction internals are not in the searched call graph, the table says "constructor only".

### 4.1 LobeDlg (TD `0047a448`)

Title format observed: "Lobe: %s " (`0047b310`) and `"(L:%s) Lobe: %s"` (`0047b2f4`). Sets a lobe-level value via the engine command `execute\nTARG AGNT %d BRN: SETL %d %d %f` (`0047b310`). A trackbar (`msctls_trackbar32`) edits a value, two static labels show key and value (formats `%s%1.3f` at `0047b2d4`, `0047b2ec`). Slider wiring not traced past the dialog template.

### 4.2 LobeGraphDlg (TD `0047ad40`)

Spawned by `FUN_004015f0` (BrainDlg method). Title: `"Graph Lobe:%s"` (`0047a390`). Uses the `Grapher` (TD `0047ad18`) helper; see Section 7. Plot title format `"(L:%s, V:%d, Lobe:%s Variable: %d"` (`0047ad6c`).

### 4.3 LobeInputDlg (TD `0047ad90`)

Spawned by `FUN_00401a40`. Title prefix from "Inputs for lobe: " (`0047a3b8`). Caption "Input Dlg" (`0047adac`). Per-row, the dialog dynamically adds a slider plus a label using `CreateWindowExA` against `s_msctls_trackbar32_0047b464` and `s_static_0047b478`: see `FUN_00418730` lines 18-30 for the pattern (the same row factory the readme calls out: "Moving the slider on neuron 3"). Constructor calls `FUN_0040fe80` at offset `+0x1a8`. The slider WM_HSCROLL / WM_VSCROLL → engine-write path was not traced fully; the `BRN: SETN` command at `0047b490` is reachable from this dialog.

### 4.4 TractDlg (TD `0047a460`)

Title formats: `"Tract: %s "` (`0047b5a8`) and `"(T:%s) Tract: %s"` (`0047b338`). Trackbar plus static labels following the same pattern as LobeDlg. Engine-write command: `execute\nTARG AGNT %d BRN: SETT %d %d %f` (`0047b35c`).

### 4.5 NeuronVarDlg (TD `0047b5b8`)

Spawned by `FUN_00401070`. Title: `"Variables Neuron:%d, %s"`. Detailed header: `"(N%d, %s) Neuron: %s in Lobe: %s"` (`0047b4bc`). Engine-write command: `execute\nTARG AGNT %d BRN: SETN %d %d %d %f` (`0047b490`). Slider rows created by `FUN_00418730`; range 0 to 25 (the trackbar-set messages at lines 23-25: `TBM_SETRANGE`, page-size 1, line-size 0x19).

### 4.6 NeuronVarGraphDlg (TD `0047b6d0`)

Spawned by `FUN_00401330`. Title: `"Graph Neuron:%d, %s"`. Plot title (`0047b664`) reuses `"(N%d, %s) Neuron: %s in Lobe: %s"`. Uses `Grapher`.

### 4.7 DendriteVarDlg (TD `0047b5d8`)

Spawned by `FUN_004011d0`. Title: `"Variables Dendrite:%d, %s"`. Detailed header: `"(D:(%d)%d->%d, %s) Dendrite: (%d) from %s to %s in Tract: %s"` (`0047b52c`). Engine-write: `execute\nTARG AGNT %d BRN: SETD %d %d %d %f` (`0047b4f8`). Slider rows from `FUN_00418730`.

### 4.8 DendriteVarGraphDlg (TD `0047b6f0`)

Spawned by `FUN_00401490`. Title: `"Graph Dendrite:%d, %s"`. Plot title format reuses the dendrite header above.

### 4.9 GeneAgeDlg (TD `0047aca0`)

Mentioned in the readme: "Click on Adult and then OK". Constructor at `FUN_0040d5a0`. Loads dialog resource ID `0x79`. Populates list box (control id `0x3F3`) with the strings "Child" (`0047acbc`), "Adolescent" (`0047acc4`), "Youth" (`0047acd0`), "Adult" (`0047acd8`), "Senile" (`0047ace4`) via `LB_ADDSTRING` (`0x180`). Returns the chosen age to the genome-open path.

## 5. Menu and toolbar command map

Menu commands are dispatched in `FUN_00412280` (MainFrame WM_COMMAND), `FUN_004054a0` (BrainViewport WM_COMMAND), and `FUN_0041a320` (zoom). Consolidated:

| Cmd ID | Source | Action | Handler |
|---|---|---|---|
| `0x9c52` | toolbar | Zoom in | `FUN_0041a620` |
| `0x9c53` | toolbar | Zoom out | `FUN_0041a6d0` |
| `0x9c54` | toolbar / menu | Play (start 250 ms timer) | `FUN_00412280` case `0x9c54` |
| `0x9c55` | toolbar / menu | Step | `FUN_00413330` |
| `0x9c57` | toolbar / menu | Loop toggle | `FUN_00412280` case `0x9c57` |
| `0x9c5a` | menu | Exit | `FUN_00412280` case `0x9c5a` |
| `0x9c67` | View > Threshold > None | Set mode 0 | `FUN_004054a0` |
| `0x9c68` | View > Threshold > Non-Zero | Set mode 1 (readme highlight) | `FUN_004054a0` |
| `0x9c69` | View > Threshold > Above | Set mode 2 | `FUN_004054a0` |
| `0x9c6a` | View > Threshold > Below | Set mode 3 | `FUN_004054a0` |
| `0x9c6b` | View > Threshold > Custom | Set mode 5, edit `*(viewport+0x708)` (likely opens `ThreshHoldDlg`) | `FUN_004054a0` |
| `0x9c83` | menu | Pause / Stop | `FUN_00413240` |
| `0x9c8c` | File > Open | Open genome (offline path) | `FUN_00412fe0` |
| `0x9ca4` | View / right-click | Show variables for selected entity | `FUN_004054a0` case `0x9ca4` |
| `0x9ca5` | right-click | Hide selected lobe / tract | `FUN_004054a0` case `0x9ca5` |
| `0x9ca9` | File > Connect to Creatures | Run online handshake | `FUN_004129d0` |
| `0x9cad` | right-click | Graph Lobe (route to `FUN_004015f0`) | `FUN_004054a0` case `0x9cad` |
| `0x9cae` | right-click | Graph Dendrite (route to `FUN_004011d0`) | `FUN_004054a0` case `0x9cae` |
| `0x9cb2` | menu | Disconnect / transfer brain back, sends `DBG: PLAY` | `FUN_00412280` case `0x9cb2` |
| `0x9cbd` | menu | Refresh creature list (re-runs `FUN_00412ac0`) | `FUN_00412280` case `0x9cbd` |
| `0x9cc0` | File > (creature submenu) | Select a creature | `FUN_00412280` case `0x9cc0` |
| `0x9cc1` | menu | (calls `FUN_00409700` on viewport) | `FUN_00412280` case `0x9cc1` |
| `0x9cc2` | toolbar / menu | Instinct processing toggle ("IN") | `FUN_00412280` case `0x9cc2` |
| `0x9c77` | View / right-click | Show all hidden | `FUN_004054a0` (resets `0x798` / `0x79c` flag arrays) |
| `1000+i` | dynamic submenu | Show specific hidden lobe / tract by index | `FUN_00412280` default case (treats as creature index) and `FUN_004054a0` default case |

Several menu IDs have no observed handler beyond their toolbar-state echo (`0x9c6d`, `0x9c6e`, `0x9c6f`, `0x9c70` ... `0x9c76` are reset-to-unchecked in `FUN_004054a0` line 176-186, so they exist as menu items but their handler bodies were not located in the searched files). Mark as "exists but body not traced" rather than guessing.

## 6. Modes

### 6.1 Offline mode (default at startup)

- Menu attached: resource `0x6e` (no Connect-to-Creatures submenu items).
- Genome-open path: File > Open (`0x9c8c` → `FUN_00412fe0`):
  1. Looks up "Genetics Directory" registry value (`0047b1d0`) for the file dialog initial directory.
  2. `GetOpenFileNameA` with file filter at `0047b1e8` and flags `0x1800` (`OFN_HIDEREADONLY | OFN_PATHMUSTEXIST`).
  3. Sets the status bar to "Loading genome".
  4. `FUN_00411fc0` reads and decompresses the CreaturesArchive and instantiates a local `Brain`.
  5. Opens GeneAgeDlg to choose Child / Adolescent / Youth / Adult / Senile.
  6. Forces the IN button on (`0x9cc2` set to 1) and refreshes the viewport via `FUN_00413370`.

In offline mode, `DAT_0048128d == '\0'` and `BrainViewport::Tick` (`FUN_00404d30`) takes the local-Brain branch instead of the IPC branch.

### 6.2 Online mode

- Menu attached: resource `0x76` (full File menu including Connect-to-Creatures and Disconnect).
- Connect path: File > Connect (`0x9ca9` → `FUN_004129d0`):
  1. Status bar set to "Connecting to creatures".
  2. `FUN_00442240(&DAT_00481278)` opens the four named Win32 IPC objects (mutex, request event, result event, file mapping). On failure, `MessageBoxA` "Failed to connect to game." (`0047b0c4`) with title "Connect to Creatures" (`0047b0ac`).
  3. On success, sends `execute\nDBG: PAWS\n` (`0047b068`) to pause the engine.
  4. Calls `FUN_00412ac0` to enumerate creatures via `ENUM 0 0 0 DOIF TYPE TARG = 7 ...` (`0047b0e0`), parses the response, and populates the File menu submenu with one item per creature.
  5. If no creatures, MessageBox "Could not find any creatures or perhaps some other problem." (`0047b168`) with retry / cancel.
- Once a creature is picked (cmd `0x9cc0`), `FUN_00412e10` downloads the brain via `BRN: DMPB` / `BRN: DMPL` / `BRN: DMPT` (strings `0047a5f0`, `0047a704`, `0047a748`) and instantiates a `BrainViewport` on the result. Status bar becomes "Connected to Creatures" (`0047b220`).
- Disconnect (`0x9cb2`): sends `execute\nDBG: PLAY\n` (`0047afe8`), drops the IPC mutex, switches the menu back to `0x6e`, resets all four toolbar buttons to unchecked.

## 7. Graphing

`Grapher` (TD `0047ad18`) is the time-series helper used by `*GraphDlg` classes. Its draw routine is `FUN_00443aa0`:

- Allocates a `POINT[bufferLen]` (size at offset `0x68` of `Grapher`).
- Indices: `head` at `0x6c`, `windowLen` at `0x70` (inferred from arithmetic at lines 21-24).
- For each visible sample, calls a value-fetch function (`FUN_00442b50`) on the underlying value-source object (`param_2`), maps to (x, y) using `param_3` (a `RECT`-like four-int layout: x0, y0, w, h-1), then `Polyline(hdc, points, count)` if at least two points are present.

Font setup is done once per Grapher in `FUN_00443cb0`: `CreateFontIndirectA` for "MS Sans Serif" 10pt weight 9 (FW_MEDIUM), stored at `*(this+0x88)`. Failure path: MessageBox "Could not create font for graph" (`0047d160`) with title "Graph Initialisation Error" (`0047d144`).

Sample rate is implicit: `Grapher::AddSample` is called once per `BrainViewport::Tick` (no explicit timer of its own). The window length defaults to whatever the buffer size at construction provides; not parameterised through the menu in the traced code.

## 8. Right-click context menus

Already covered in 3.5: the BrainViewport intercepts `WM_RBUTTONDOWN`, runs a hit-test on the viewport coordinates against lobe quads (lobe-rect array at `*(this+0x73c)` indexed by lobe id) and dendrite endpoints. The hit-test result (1=neuron, 2=lobe, 3=tract, 4=dendrite) is written to `*(this+0x784)` and `FUN_004073f0` is then invoked with the cursor position. The four sub-menus pre-loaded into `*(this+0x6e0)` provide the per-entity command set. `TrackPopupMenu` returns; the user pick generates a `WM_COMMAND` to BrainViewport which is dispatched by `FUN_004054a0`.

The most-used right-click commands are:

- "Variables" (`0x9ca4`): opens NeuronVarDlg / DendriteVarDlg / LobeDlg / TractDlg depending on hit type.
- "Graph" (`0x9cad` for lobe, `0x9cae` for dendrite): opens corresponding `*GraphDlg`.
- "Hide" (`0x9ca5`): sets the per-entity hidden flag at `*(this+0x798)+2+i*3` (tracts) or `*(this+0x79c)+2+i*3` (lobes), then triggers redraw.
- "Show all hidden" (`0x9c77`): clears all hidden flags.

## 9. What we can lift, what we rebuild, what's dead

Classified for the next-phase build of an openc2e-side viewer.

### 9.1 Data we should lift verbatim

These are not code, they are content the engine SDK encoded and the Vat consumes via the catalogue. They define how the brain is laid out on screen and are the only non-trivial lookups the Vat does that we cannot regenerate without primary research:

- **`Brain Lobe Quads`** (catalogue tag, accessed at `FUN_00410ab0`): per-lobe rectangle (x, y, width, height) in viewport-grid coordinates.
- **`Brain Lobes`** (display names of lobes).
- **`Brain Lobe Neuron Names`** (per-neuron labels; falls back to `"Neuron %d"` from `0047ae90` when missing).
- **`LobeNames`** (lobe-id-to-name lookup).

These tags are present in the C3 game catalogue files and should be re-used directly. Cross-reference with `docs/reference/svrule-brain-complete-reference.md` and `cc-ref.yaml`: the same tags drive the SVRule brain's introspection.

### 9.2 Algorithms worth porting (re-implement in any toolkit)

The structure is non-obvious and the Vat got it right. Port the *logic*, write fresh code in our chosen UI stack:

- **BrainViewport paint pipeline** (`FUN_00405d00`): double-buffered, two-pass when any threshold filter is active (background pass first, then over-draw the visible set in colour). Extracts cleanly to any retained-mode or immediate-mode toolkit.
- **Threshold modes** (None / Non-Zero / Above / Below / Custom; offset `0x704` and `0x708`): copy the four-mode enum, the menu structure, and the per-neuron inclusion test.
- **Right-click hit-type discriminator** (`FUN_004073f0` plus offset `0x784`): the four-way switch (neuron / lobe / tract / dendrite) for context menus is the right factoring. Re-implement with a scene-graph hit-test.
- **Open-child dialog dedup** (`FUN_00401bd0`): the doubly-linked list keyed by (entity-kind, entity-id) is the right pattern for "don't open two graphs for the same neuron". Worth re-implementing.
- **Hidden-entity flag arrays** (offsets `0x798` / `0x79c`, three bytes per entity): the dynamic "Show lobe X" / "Show tract Y" submenu construction in `FUN_004073f0` (default branch) is a nice UX. Port it.
- **Tick / pull / redraw cycle** (`FUN_00404d30`): the "send TOCK, pull state for each lobe and tract, diff against cached, animate, invalidate" loop is the right shape. We will replace the `DBG: TOCK` IPC with an in-process pybind11 call into the Python brain, but the pull-and-diff structure stands.
- **Grapher circular-buffer plot** (`FUN_00443aa0`): trivial Polyline over a ring buffer. Re-implement in 30 lines.

### 9.3 Boilerplate, rebuild from scratch

Pure Win32 / MFC. Use whatever is idiomatic in the chosen UI stack (Dear ImGui, Qt, web, ...):

- The `WinMain` + message pump (`FUN_0041a7a0`).
- `RegisterClassExA` + `MainFrame` window class plumbing.
- `CreateToolbarEx` + `TBBUTTON` array. Replace with native toolbar widgets.
- `CreateStatusWindowA` status bar.
- `LoadMenuA` / `AppendMenuA` / `CheckMenuItem` menu plumbing.
- `BeginPaint` / `EndPaint` and the `CreateCompatibleDC` + `BitBlt` double-buffer (modern toolkits handle this for free).
- `MessageBoxA` error dialogs, `GetOpenFileNameA` file dialogs, the `WhichEngine` registry-key lookup.
- The trackbar-row factory (`FUN_00418730`): trivial label + slider, two lines in any modern toolkit.

### 9.4 Dead, do not port

These exist in the Vat but our engine has no need:

- `BrainAccess` and the four-named-object Win32 IPC (mutex, request, result, file mapping). Already declared retired in `cc-ref.yaml engine.retired: ["GOG engine.exe", "Win32 shared memory", "Steam"]`.
- `DBG: TOCK`, `DBG: PAWS`, `DBG: PLAY`, `BRN: DMPB`, `BRN: DMPL`, `BRN: DMPT`, `BRN: DMPN`, `BRN: DMPD`, `BRN: SETL`, `BRN: SETT`, `BRN: SETN`, `BRN: SETD` CAOS commands. openc2e does not implement `DBG:` and we drive the brain in-process via pybind11.
- `GenomeOpen` via `CreaturesArchive` + zLib 1.13. We have our own genome path; the Vat's offline genome loader is interesting as a reference but not load-bearing.
- The `Connect to Creatures` flow (`FUN_004129d0`). Replaced by direct pybind11 attach to the running brain.
- `GeneAgeDlg`. Our brains do not have the same age-stage gating; we read whatever the engine has loaded.

### 9.5 Open questions for the next phase

- Custom-threshold dialog (`ThreshHoldDlg`, TD `0047b3c0`): the menu wires it but the dialog body was not traced. Likely a single edit-control + OK/Cancel; trivial to replace, but worth noting we have not seen the field validation.
- `Tips` (TD `0047b3e8`): not exercised in the searched paths. Possibly a tooltips helper; not load-bearing.
- `SVRuleDlg` (TD `0047a438`): the format strings `"SV Rule %s"` (`0047a3a0` / `0047a3ac`) suggest a per-SV-rule editor, but the entry path was not located. Probably reachable from a deeper right-click submenu.
- `TextViewport` (TD `0047b390`): may be a debug-output panel; not located in the searched paths.
- LobeInputDlg slider-to-engine wiring beyond `FUN_00418730`: the row factory is clear, the change-handler is not. Trace `WM_HSCROLL` routing on a follow-up pass before re-implementing the input panel.

These are the "reverse-engineer one more level if needed" items, not blockers for the bucket-9.1 / 9.2 lift.

## Source map

| Section | Primary functions | Primary string addresses |
|---|---|---|
| 1 Application shell | `FUN_0041a7a0`, `FUN_00411a80`, `FUN_00411d50`, `FUN_00411e10`, `FUN_0041acd0` | `0047aef0`, `0047af2c`, `0047b210`, `0047b220`, `0047b238` |
| 2 BrainDlg | `FUN_00401070`, `FUN_004011d0`, `FUN_00401330`, `FUN_00401490`, `FUN_004015f0`, `FUN_00401a40`, `FUN_00401bd0` | `0047a330`, `0047a348`, `0047a364`, `0047a378`, `0047a390`, `0047a3b8` |
| 3 BrainViewport | `FUN_00405d00`, `FUN_00406900`, `FUN_00406d80`, `FUN_004070a0`, `FUN_00410ab0`, `FUN_004073f0`, `FUN_004054a0`, `FUN_00404d30` | `0047ae34`, `0047ae48`, `0047ae5c`, `0047ae68`, `0047ae90`, `0047a834`, `0047a840`, `0047a80c` |
| 4 Per-entity dialogs | `FUN_0040d5a0`, `FUN_0040f530`, `FUN_0040fe80`, `FUN_00418730` | `0047b310`, `0047b35c`, `0047b490`, `0047b4f8`, `0047b464`, `0047b478`, `0047acbc`-`0047ace4` |
| 5 Menu / toolbar | `FUN_00412280`, `FUN_004054a0`, `FUN_0041a320`, `FUN_0041a620`, `FUN_0041a6d0` | n/a |
| 6 Modes | `FUN_004129d0`, `FUN_00412fe0`, `FUN_00412ac0`, `FUN_00412e10`, `FUN_00413240`, `FUN_00413370` | `0047b050`, `0047b068`, `0047b0ac`, `0047b0c4`, `0047b144`, `0047b150`, `0047b168`, `0047b1d0`, `0047b1e8`, `0047b200`, `0047afe8` |
| 7 Graphing | `FUN_00443aa0`, `FUN_00443cb0`, `FUN_00442b50` | `0047d134`, `0047d144`, `0047d160`, `0047ad18` |
| 8 Right-click | `FUN_004073f0`, `FUN_004054a0` | `0047a834`, `0047a840`, `0047a84c` |
