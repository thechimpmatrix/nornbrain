# Brain in a Vat: PE Resources

Inventory of the Win32 PE resource section embedded in `Vat_1.9.exe`. These are the static UI assets the binary ships: dialog templates, menu structures, toolbar layout, bitmaps, icons, version info. Extracted via `analysis/braininavat/scripts/dump_resources.py` (uses Python `pefile`). Raw resources at [analysis/braininavat/notes/resources/](../../../analysis/braininavat/notes/resources/).

## Inventory

| Type | ID | Lang | Size | Purpose |
|---|---|---|---|---|
| BITMAP | 108 | 1033 (en-US) | 824 B | Toolbar strip, 96×15 px, 4-bit colour, 6 buttons of 16×15 each |
| ICON | 1 | 2057 (en-GB) | 744 B | Application icon (small) |
| ICON | 2 | 2057 | 2,216 B | Application icon (large) |
| ICON | 3 | 2057 | 296 B | Probably file-type icon |
| GROUP_ICON | 120 | 2057 | 48 B | Icon group descriptor |
| MENU | 110 | 2057 | 770 B | Default offline-mode menu (File · View · Windows) |
| MENU | 111 | 2057 | 126 B | Minimal File menu (used by sub-windows in offline mode) |
| MENU | 116 | 1033 | 1,284 B | **Right-click context menus + viewport View menu** |
| MENU | 117 | 2057 | 158 B | Minimal File menu (online sub-window variant) |
| MENU | 118 | 2057 | 802 B | Online-mode main menu (File · View · Windows) |
| MENU | 119 | 2057 | 182 B | File menu with Reconnect option |
| DIALOG | 118 | 2057 | 446 B | `ThreshHoldDlg` dialog template |
| DIALOG | 121 | 2057 | 182 B | `GeneAgeDlg` dialog template |
| STRING | 1 | 1033 | 448 B | Window-class name table (15 entries) |
| 241 (RT_TOOLBAR) | 108 | 1033 | 22 B | MFC toolbar layout descriptor |
| VERSION | 1 | 1033 | 892 B | VS_VERSIONINFO block |

Notable absence: only 2 RT_DIALOG templates. The `BrainDlg`, `LobeDlg`, `LobeGraphDlg`, `LobeInputDlg`, `TractDlg`, `NeuronVarDlg`, `NeuronVarGraphDlg`, `DendriteVarDlg`, `DendriteVarGraphDlg`, and `SVRuleDlg` classes do **not** ship with RT_DIALOG templates. They are constructed programmatically via `CreateWindowExA` calls in the code, with controls instantiated and positioned at runtime. This means the layout for those dialogs is in the decompilation, not in the resources. For reimplementation we must read the per-dialog constructor to recover the layout.

## Toolbar (RT_TOOLBAR id 108)

Format is the MFC `CToolBar`-style binary layout: `[u16 version=1][u16 btnWidth=16][u16 btnHeight=15][u16 numItems=7][u16 cmdID × 7]`. Confirms the GUI inventory's toolbar reading.

| Index | Cmd ID | Mnemonic | Notes |
|---|---|---|---|
| 0 | `0x9C52` | Zoom-In | Increases viewport magnification |
| 1 | `0x9C53` | Zoom-Out | Decreases viewport magnification |
| 2 | `0x0000` | (separator) | Visual gap |
| 3 | `0x9C54` | Play | Starts a 250 ms tick timer |
| 4 | `0x9C55` | Step | Single-tick advance (`DBG: TOCK`) |
| 5 | `0x9C57` | Loop | Continuous loop mode |
| 6 | `0x9CC2` | IN (instinct) | Toggles instinct-processing pass |

The toolbar bitmap (`BITMAP id 108`, 96×15 px, 4-bit) is the strip of 6 button glyphs. Saved as a real `.bmp` at [resources/bitmaps/bitmap_108.bmp](../../../analysis/braininavat/notes/resources/bitmaps/bitmap_108.bmp). Useful as visual reference if reproducing the toolbar.

## Menus

### Menu 110: offline-mode main menu

```
&File
  &Open                    0x9C8C
  &Close                   0x9C83 (disabled)
  ---
  Connect to Creatures     0x9CA9
  ---
  &Exit                    0x9C5A
&View
  Neuron var 0..7          0x9C67-0x9C6A, 0x9C77, 0x9C6B, 0x9C6D-0x9C6E (radio group)
  ---
  Dendrite var 0..7        0x9C6F-0x9C76 (radio group)
  ---
  Hide Details             0x9CA2 (toggle)
  Set Threshold View       0x9CC1 → opens dialog 118
&Windows
  None                     0x9CA8 (placeholder)
```

### Menu 116: viewport context menus + View menu

This single MENU resource holds **six** popup sub-menus, indexed 0-5. The right-click handler at `FUN_004073f0` (per GUI inventory) reads the hit-type at offset `0x784` (1=neuron, 2=lobe, 3=tract, 4=dendrite) and pops the corresponding sub-menu via `TrackPopupMenu`.

| Sub-menu | Title | Items |
|---|---|---|
| 0 | `neuron` | Graph Neuron `9CAF`, Neuron Variables `9CAE`, SV Rule `9CA4`, Graph Lobe `9CAD`, Hide Lobe `9CA5` |
| 1 | `dendrite` | Graph Dendrite `9CAF`, Dendrite Variables `9CAE`, SV Rule `9CA4`, Hide Tract `9CA5` |
| 2 | `lobe` | SV Rule `9CA4`, Graph Lobe `9CAD`, Hide Lobe `9CA5` |
| 3 | `tract` | SV Rule `9CA4`, Hide Tract `9CA5` |
| 4 | `&View` | Same Neuron/Dendrite var picker as menu 110 (so the View menu is duplicated here for sub-windows) |
| 5 | `Vars` | Variable 0..7 `9CB3-9CBA` (radio group) |

Note the Cmd ID reuse: `0x9CAF` is "Graph X" generically (X = neuron or dendrite, depending on which sub-menu), and the dispatch in the `WM_COMMAND` handler discriminates by current hit-type. This is how a single Cmd ID can drive different actions depending on context.

### Menu 118: online-mode main menu

Same as menu 110 except the File menu is "Refresh Online Creature List" / "Disconnect from Creatures" / "Exit" (no Open / Close / Connect because we're already connected).

### Menus 111, 117, 119

Smaller File-only menus used by sub-windows. Menu 119 has a "Reconnect to Creatures" item (`0x9CC0`) - useful for resuming after a connection drop.

### Menu cmd IDs (referenced)

This is the authoritative list of menu/toolbar Cmd IDs. The decompilation references them in `WM_COMMAND` handlers, mostly inside `BrainDlg::OnCommand`-equivalent dispatchers.

| Cmd ID | Symbol (inferred) | Function |
|---|---|---|
| `0x9C52` | ID_TOOLBAR_ZOOMIN | Toolbar |
| `0x9C53` | ID_TOOLBAR_ZOOMOUT | Toolbar |
| `0x9C54` | ID_TOOLBAR_PLAY | Toolbar |
| `0x9C55` | ID_TOOLBAR_STEP | Toolbar |
| `0x9C57` | ID_TOOLBAR_LOOP | Toolbar |
| `0x9C5A` | ID_FILE_EXIT | File menu |
| `0x9C67`-`0x9C6E` (no `0x9C6C`), `0x9C77` | ID_VIEW_NEURON_VAR_0..7 | View / Neuron var radio |
| `0x9C6F`-`0x9C76` | ID_VIEW_DENDRITE_VAR_0..7 | View / Dendrite var radio |
| `0x9C83` | ID_FILE_CLOSE | File / Close |
| `0x9C8C` | ID_FILE_OPEN | File / Open |
| `0x9CA2` | ID_VIEW_HIDE_DETAILS | View toggle |
| `0x9CA4` | ID_CONTEXT_SVRULE | Right-click → SV Rule |
| `0x9CA5` | ID_CONTEXT_HIDE_LOBE_OR_TRACT | Right-click → Hide |
| `0x9CA8` | ID_WINDOWS_NONE | Windows menu placeholder |
| `0x9CA9` | ID_FILE_CONNECT | File / Connect |
| `0x9CAD` | ID_CONTEXT_GRAPH_LOBE | Right-click → Graph Lobe |
| `0x9CAE` | ID_CONTEXT_VARIABLES | Right-click → Variables |
| `0x9CAF` | ID_CONTEXT_GRAPH | Right-click → Graph (polymorphic) |
| `0x9CB2` | ID_FILE_DISCONNECT | File / Disconnect |
| `0x9CB3`-`0x9CBA` | ID_VARS_VAR_0..7 | Variable radio group |
| `0x9CBD` | ID_FILE_REFRESH_ONLINE | File / Refresh |
| `0x9CC0` | ID_FILE_RECONNECT | File / Reconnect |
| `0x9CC1` | ID_VIEW_THRESHOLD | View / Threshold... |
| `0x9CC2` | ID_TOOLBAR_INSTINCT | Toolbar / "IN" |

## Dialog 118: ThreshHoldDlg

```
DIALOG 146x98 dlu, "Threshold View"
font: MS Sans Serif 8pt
items:
  [ 0] OK button         id=0x0001 (IDOK)         pos=(89,77)  size=(50,14)
  [ 1] No Threshold      id=0x03E9 radiobutton    pos=( 7, 7)  size=(132,10)
  [ 2] Non Zero Values   id=0x03EA radiobutton    pos=( 7,17)  size=(132,10)
  [ 3] Above Threshold   id=0x03EB radiobutton    pos=( 7,26)  size=(132,10)
  [ 4] Below Threshold   id=0x03EC radiobutton    pos=( 7,35)  size=(132,10)
  [ 5] Slider1           id=0x03ED msctls_trackbar32  pos=(7,48) size=(107,18)
  [ 6] Static            id=0x03EE static         pos=(115,50) size=( 24,13)
```

This is the threshold view dialog. The slider sets the threshold value used by the BrainViewport's filter pass. Static control 0x03EE shows the current numeric threshold (updated as the slider moves). Radio buttons select threshold mode: None / NonZero / Above / Below.

The View menu's "Set Threshold View" item (Cmd `0x9CC1`) opens this dialog. The threshold mode and value are stored on the viewport at offsets `0x704` (mode) and `0x708` (value) per the GUI inventory.

## Dialog 121: GeneAgeDlg

```
DIALOG 167x108 dlu, "Gene Expression Age"
font: MS Sans Serif 8pt
items:
  [ 0] OK button   id=0x0001  pos=(110, 7) size=( 50,14)
  [ 1] "Age" label id=0xFFFF  pos=(  7, 7) size=( 14, 8)
  [ 2] Listbox     id=0x03F3  cls=#131 (LISTBOX)  pos=(7,19) size=(95,82) style=0x50A10101
```

The age picker shown when opening a genome in offline mode. List entries are populated programmatically (likely "Embryo / Adolescent / Adult / etc.").

## Window class name table (STRING id 1)

These are the strings registered with `RegisterClassExA` for the MFC sub-windows.

| ID | Class name |
|---|---|
| 1 | `Vat and Zone Tool` |
| 3 | `Viewport` |
| 4 | `Brain Viewport` |
| 5 | `Input Neuron Viewport` |
| 6 | `lobe Input Dialog` |
| 7 | `List View` |
| 8 | `Input Neuron List View` |
| 9 | `Variable Dialog` |
| 10 | `SV Rule Dialog` |
| 11 | `Variable Graph Dialog` |
| 13 | `Graph Dialog Window` |
| 14 | `Text Viewport Window` |
| 15 | `Tips Window` |

The "Vat and Zone Tool" string at ID 1 is interesting: it suggests the Vat tool was originally part of (or shared a codebase with) a "Zone Tool" - likely a world-zone editor. Only the Vat features ship in this binary, but the framework string remained.

`Input Neuron Viewport` and `Input Neuron List View` are the sub-windows for `LobeInputDlg` (offline-mode input drive feature mentioned in the readme).

## Version info (RT_VERSION id 1)

Standard `VS_VERSIONINFO` block. Inspecting the raw bytes confirms the banner string `CyberLife Vat Kit for Creatures 3 v1.8` and CyberLife company info. Not catalogued in detail; raw at [resources/raw/version_1.bin](../../../analysis/braininavat/notes/resources/raw/version_1.bin).

## What this gives our viewer

For a from-scratch reimplementation:

1. **Toolbar layout is fully specified** - 6 buttons of 16×15 px in a known order with known Cmd IDs. We can reproduce it 1:1 in any toolkit.
2. **Right-click context menus are fully specified** - 4 hit-type-discriminated popups; the dispatch logic is documented.
3. **Threshold dialog is fully specified** - even the dlu coordinates of every control. Useful if we want to ship the same threshold UX.
4. **GeneAge dialog is offline-mode-only and probably not worth reproducing** in our viewer (we don't load genomes into the viewer; openc2e does that separately).
5. **The other 8+ programmatic dialogs (`LobeDlg`, `TractDlg`, var/graph dialogs, SVRuleDlg) have no resource templates.** Their layouts must be read from decompilation (or reimagined for our toolkit). Not a hard blocker; the dialogs are simple control collections.
6. **The toolbar bitmap is salvageable** - at 96×15 px it would not look great upscaled, but we can use it as visual reference for designing modern equivalents.
