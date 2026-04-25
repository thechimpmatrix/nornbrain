# Mission Control Monitor: Implementation Plan


**Goal:** Rewrite norn_monitor.py as a fullscreen 4K mission control dashboard with live brain map (239 neurons, 22 tracts), chemical panel, sensory inputs, motor output distributions, and a control panel.

**Architecture:** Single-file tkinter app with three-column layout. Left: inputs (sensory bars, drives, chemicals). Centre: brain map canvas (top) + timeline/health/log (bottom). Right: output distributions (attention/decision) + control buttons + LTM. WebSocket listener thread receives tick data, GUI polls at 200ms. All drawing via Canvas primitives.

**Tech Stack:** Python 3.14, tkinter, Canvas, websocket-client

**Spec:** `docs/superpowers/specs/2026-03-31-mission-control-monitor-design.md`

**Branch:** `feature/multi-lobe-cfc` in `<PROJECT_ROOT>/`

**File:** `phase2-bridge/norn_monitor.py` (complete rewrite)

---

## WebSocket Message Fields (from bridge)

The monitor reads these fields from each tick message:

```python
# Sensory/state
msg["lobes"]           # dict: {"attn": [40], "decn": [17], "visn": [40], "smel": [40], "driv": [20], ...}
msg["drives"]          # dict: {"pain": 0.0, "hunger_protein": 0.5, ...}
msg["all_chemicals"]   # list: 256 floats
msg["neuron_activations"]  # list: 239 floats (thalamus[0:70] + amygdala[70:122] + hippocampus[122:174] + prefrontal[174:239])

# Outputs
msg["attention"]       # {"winner_index": int, "winner_label": str, "values": [40 floats]}
msg["decision"]        # {"winner_index": int, "winner_label": str, "values": [17 floats]}

# Telemetry
msg["timing"]          # {"read_ms", "brain_ms", "write_ms", "ltm_ms", "total_ms"}
msg["health"]          # {"attn_entropy", "decn_confidence", "module_variance": {}, "module_energy": {}, "action_diversity", "status"}
msg["emotional_tier"]  # str: "LOW"/"CALM"/"ALERT"/"INTENSE"/"EXTREME"
msg["ltm_count"]       # int
msg["game_tick"]       # int
msg["creature_name"]   # str
msg["posx"], msg["posy"]  # float
```

## Brain Map Neuron Layout

The 239 neurons split across 4 modules. Each module arranged as a rectangular grid:

```python
MODULES = {
    "thalamus":    {"offset": 0,   "count": 70, "cols": 10, "rows": 7,  "stage": 1},
    "amygdala":    {"offset": 70,  "count": 52, "cols": 8,  "rows": 7,  "stage": 1},
    "hippocampus": {"offset": 122, "count": 52, "cols": 8,  "rows": 7,  "stage": 1},
    "prefrontal":  {"offset": 174, "count": 65, "cols": 9,  "rows": 8,  "stage": 2},
}
```

Stage 1 modules stacked vertically on the left of the brain map. Stage 2 (prefrontal) on the right. Tracts drawn as bezier curves between them.

## 22 Tract Definitions

```python
TRACTS = [
    # Stage 1 inputs
    {"name": "visn→thal",  "src": "visn",  "dst": "thalamus",    "src_n": 40, "dst_n": 10},
    {"name": "smel→thal",  "src": "smel",  "dst": "thalamus",    "src_n": 40, "dst_n": 10},
    {"name": "driv→thal",  "src": "driv",  "dst": "thalamus",    "src_n": 20, "dst_n": 10},
    {"name": "prox→thal",  "src": "prox",  "dst": "thalamus",    "src_n": 20, "dst_n": 10},
    {"name": "driv→amyg",  "src": "driv",  "dst": "amygdala",    "src_n": 20, "dst_n": 8},
    {"name": "stim→amyg",  "src": "stim",  "dst": "amygdala",    "src_n": 40, "dst_n": 8},
    {"name": "chem→amyg",  "src": "chem",  "dst": "amygdala",    "src_n": 16, "dst_n": 8},
    {"name": "sitn→hipp",  "src": "sitn",  "dst": "hippocampus", "src_n": 9,  "dst_n": 4},
    {"name": "detl→hipp",  "src": "detl",  "dst": "hippocampus", "src_n": 11, "dst_n": 4},
    {"name": "noun→hipp",  "src": "noun",  "dst": "hippocampus", "src_n": 40, "dst_n": 4},
    {"name": "verb→hipp",  "src": "verb",  "dst": "hippocampus", "src_n": 17, "dst_n": 4},
    {"name": "loc→hipp",   "src": "loc",   "dst": "hippocampus", "src_n": 2,  "dst_n": 4},
    # Stage 2 inputs (from Stage 1 outputs + direct sensory)
    {"name": "thal→pfc",   "src": "thalamus",    "dst": "prefrontal", "src_n": 40, "dst_n": 10},
    {"name": "amyg→pfc",   "src": "amygdala",    "dst": "prefrontal", "src_n": 16, "dst_n": 8},
    {"name": "hipp→pfc",   "src": "hippocampus", "dst": "prefrontal", "src_n": 16, "dst_n": 6},
    {"name": "driv→pfc",   "src": "driv",  "dst": "prefrontal",  "src_n": 20, "dst_n": 8},
    {"name": "verb→pfc",   "src": "verb",  "dst": "prefrontal",  "src_n": 17, "dst_n": 4},
    {"name": "noun→pfc",   "src": "noun",  "dst": "prefrontal",  "src_n": 40, "dst_n": 4},
    {"name": "resp→pfc",   "src": "resp",  "dst": "prefrontal",  "src_n": 20, "dst_n": 4},
    {"name": "stim→pfc",   "src": "stim",  "dst": "prefrontal",  "src_n": 40, "dst_n": 4},
    {"name": "chem→pfc",   "src": "chem",  "dst": "prefrontal",  "src_n": 16, "dst_n": 6},
    {"name": "ltm→pfc",    "src": "ltm",   "dst": "prefrontal",  "src_n": 6,  "dst_n": 6},
]
```

## Chemical Display Groups

```python
CHEMICAL_GROUPS = {
    "Reinforcement": [(204, "reward"), (205, "punish")],
    "Arousal":       [(117, "adrenalin"), (158, "fear_ch"), (160, "anger_ch")],
    "Metabolism":    [(3, "glucose"), (4, "glycogen"), (5, "starch"), (10, "fat"),
                      (12, "protein"), (35, "ATP"), (36, "ADP")],
    "Drives":        [(148, "pain"), (149, "hung_p"), (150, "hung_c"), (151, "hung_f"),
                      (154, "tired"), (155, "sleepy"), (156, "lonely"), (159, "bored"),
                      (161, "sex"), (162, "comfort")],
    "Neurotrophin":  [(17, "down_trph"), (18, "up_trph")],
}
GROUP_COLOURS = {
    "Reinforcement": "#e0af68",
    "Arousal": "#f7768e",
    "Metabolism": "#9ece6a",
    "Drives": "#7aa2f7",
    "Neurotrophin": "#7dcfff",
}
```

---

## Task 1: Window Framework + Three-Column Layout

Create the new norn_monitor.py with the window, three-column layout, top bar, and WebSocket listener. No panels yet: just the skeleton that other tasks fill in.

**Files:**
- Rewrite: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Create the new norn_monitor.py with framework**

The file should contain:
- Theme constants (same Tokyo Night palette as current)
- All the data constants above (MODULES, TRACTS, CHEMICAL_GROUPS, etc.)
- Label constants (DRIVE_NAMES, ATTENTION_LABELS, DECISION_LABELS: copy from current file)
- `BridgeListener` class (same WebSocket thread as current, unchanged)
- `NornMonitor` class with:
  - `__init__`: creates root window (title "NORN MISSION CONTROL"), sets geometry to fullscreen, builds the three-column layout
  - Three-column layout using `tk.Frame` with `pack(side="left")`:
    - `self.left_frame`: width=320, fixed
    - `self.centre_frame`: flex (expands)
    - `self.right_frame`: width=300, fixed
  - Top bar frame (height=36) packed at top before columns
  - Labels in top bar: title, connection status, tick, tps, timing text
  - `_poll()` method: same pattern as current (200ms after, get state, dispatch to update)
  - `_update(msg)` method: stub that just updates top bar labels
  - `main()` entry point with argparse (--port, --rate, --fullscreen flag)
  - Fullscreen: `self.root.state('zoomed')` on Windows for maximized, or `self.root.attributes('-fullscreen', True)` if --fullscreen flag

- [ ] **Step 2: Verify it launches**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python -c "import norn_monitor; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: mission control monitor: window framework + 3-column layout"
```

---

## Task 2: Left Column: Sensory Inputs + Drives + Chemicals

Fill the left column with three stacked panels: sensory lobe activations (10 bars), drives (20 bars in 2 columns), and chemicals (~25 bars grouped by category).

**Files:**
- Modify: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Add sensory inputs panel**

Add to `_build_left_column()`:
- Section label "SENSORY INPUTS"
- Canvas (height=120) for 10 lobe bars
- `_draw_sensory(lobes_dict)` method:
  - For each lobe in `["visn","smel","driv","prox","sitn","detl","noun","verb","resp","stim"]`:
    - Get mean activation from `lobes_dict.get(lobe_id, [])`
    - Draw label (8 chars) + horizontal bar, colour blue gradient by intensity

- [ ] **Step 2: Add drives panel**

- Section label "DRIVES"
- Canvas (height=200) for 20 bars in 2 columns
- `_draw_drives(drives)` method: same as current but extract from dict or list

- [ ] **Step 3: Add chemicals panel**

- Section label "CHEMICALS"
- Canvas (height=300) for ~25 chemical bars grouped by category
- `_draw_chemicals(all_chemicals)` method:
  - For each group in CHEMICAL_GROUPS:
    - Draw group header in group colour
    - For each (index, name) in group:
      - Get value from `all_chemicals[index]`
      - Draw label + bar in group colour

- [ ] **Step 4: Wire into _update()**

In `_update(msg)`:
```python
lobes = msg.get("lobes", {})
self._draw_sensory(lobes)
drives = msg.get("drives", {})
self._draw_drives(drives)
all_chems = msg.get("all_chemicals", [0.0] * 256)
self._draw_chemicals(all_chems)
```

- [ ] **Step 5: Verify and commit**

```bash
cd <PROJECT_ROOT>/phase2-bridge && python -c "import norn_monitor; print('OK')"
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: left column: sensory inputs, drives, chemicals panels"
```

---

## Task 3: Brain Map: Neuron Dots + Module Boundaries

Draw the brain map in the centre-top canvas. 239 neurons as circles in 4 module clusters. No tracts yet: just the modules with their neurons.

**Files:**
- Modify: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Add brain map canvas**

In `_build_centre_column()`:
- Section label "BRAIN MAP"
- `self.brain_canvas` = Canvas, takes top 60% of centre column
- Compute neuron positions at init time in `_compute_brain_layout()`:
  - Brain map area: let canvas width/height be determined by frame
  - Stage 1 modules (thalamus, amygdala, hippocampus) stacked vertically on left third
  - Stage 2 module (prefrontal) on right third, centred vertically
  - Each module: compute (x, y) for each neuron in a grid layout (cols × rows)
  - Store as `self._neuron_positions`: list of 239 (x, y) tuples
  - Store module bounding boxes as `self._module_bounds`: dict of name → (x1, y1, x2, y2)
  - Also store sensory input node positions on far left, motor output positions on far right

- [ ] **Step 2: Implement _draw_brain_map()**

`_draw_brain_map(neuron_activations)`:
- Clear canvas
- Draw module boundaries: rounded rectangles with module name label + variance/energy text
- Draw each neuron as a circle (radius 4px):
  - Fill colour from activation value: `_activation_colour(val)` returns black→blue→cyan→white gradient
  - Position from `self._neuron_positions[i]`
- Draw sensory input nodes as small labelled rectangles on far left
- Draw motor output nodes on far right (ATTN, DECN) with winner highlighted

The `_activation_colour(val)` function:
```python
def _activation_colour(self, val: float) -> str:
    """Map activation 0.0-1.0 to colour: black → blue → cyan → white."""
    val = max(0.0, min(1.0, abs(val)))
    if val < 0.33:
        # black to blue
        b = int(val / 0.33 * 255)
        return f"#{0:02x}{0:02x}{b:02x}"
    elif val < 0.66:
        # blue to cyan
        t = (val - 0.33) / 0.33
        g = int(t * 255)
        return f"#{0:02x}{g:02x}#ff"
    else:
        # cyan to white
        t = (val - 0.66) / 0.34
        r = int(t * 255)
        return f"#{r:02x}#ff#ff"
```

- [ ] **Step 3: Wire into _update() and test**

```python
activations = msg.get("neuron_activations", [0.0] * 239)
self._draw_brain_map(activations)
```

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: brain map: 239 neuron dots in 4 module clusters"
```

---

## Task 4: Brain Map: Tract Wires with Glow

Add the 22 tract wires to the brain map. Each wire is a bezier curve that glows based on signal strength.

**Files:**
- Modify: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Compute tract wire paths at init**

In `_compute_brain_layout()`, after neuron positions:
- For each tract in TRACTS:
  - Compute start point (right edge of source module or sensory node)
  - Compute end point (left edge of destination module)
  - Store as `self._tract_paths`: list of (name, x1, y1, x2, y2, cx1, cy1, cx2, cy2) for bezier control points
  - Sensory source tracts: start from the sensory input node position
  - Inter-module tracts (thal→pfc, amyg→pfc, hipp→pfc): start from source module right edge

- [ ] **Step 2: Compute tract signal strength**

`_compute_tract_strengths(msg)`:
- For sensory tracts: use mean absolute activation of the source lobe from `msg["lobes"]`
- For inter-module tracts (thal→pfc, amyg→pfc, hipp→pfc): use mean absolute activation of the source module's motor neurons from `msg["neuron_activations"]`
- Return dict of tract_name → float (0.0-1.0)

- [ ] **Step 3: Draw tracts with glow**

In `_draw_brain_map()`, BEFORE drawing neurons (so neurons are on top):
- For each tract:
  - Get signal strength
  - If strength < 0.01: draw thin dim line (#2a2a3a), width=1
  - Else:
    - Colour: interpolate dim_blue→cyan→yellow→red based on strength
    - Width: 1 + strength * 3
    - Draw glow: wider semi-transparent line behind (width + 4, 30% opacity via stipple)
    - Draw main line
  - Use `create_line` with `smooth=True` for bezier effect (pass multiple points along the curve)

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: brain map: 22 tract wires with glow + colour by signal strength"
```

---

## Task 5: Right Column: Output Distributions + Control Panel + LTM

Fill the right column with attention/decision bar charts, control buttons, and LTM/health summary.

**Files:**
- Modify: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Add attention distribution panel**

In `_build_right_column()`:
- Section label "ATTENTION"
- Canvas (height=200) for top-10 attention bars (sorted by activation)
- `_draw_attention(attn_dict)`:
  - Get values list, pair with labels, sort descending
  - Draw top 10 as horizontal bars with label + value
  - Winner gets bright highlight border

- [ ] **Step 2: Add decision distribution panel**

- Section label "DECISION"
- Canvas (height=160) for all 14 active decisions
- `_draw_decision(decn_dict)`:
  - All 14 bars, winner highlighted
  - Use the 14-colour DECISION_COLOURS palette

- [ ] **Step 3: Add control panel**

- Section label "CONTROLS"
- Frame with buttons:
  - `[Pause]` sends `{"type": "pause"}`
  - `[Resume]` sends `{"type": "resume"}`
  - `[Wipe Hidden]` sends `{"type": "wipe_brain"}`
  - `[Save Weights]` sends `{"type": "save_weights"}`
  - `[Toggle RL]` sends `{"type": "train_rl_toggle"}`
  - `[Capture]` sends `{"type": "capture_scenario", "name": "manual", "decision": current_decn, "attention": current_attn}`

- Each button calls `_send_command(cmd_dict)` which sends JSON via the WebSocket.

- For sending commands back, add a `send(msg)` method to `BridgeListener` that uses a separate WebSocket connection or queues the message.

    Actually simpler: use `urllib.request` to POST to the bridge's HTTP endpoint, or open a second sync WebSocket. But the bridge's WebSocket handler already accepts JSON commands on the same connection. The BridgeListener receives on one ws: we need a separate send ws or use the same one with a lock.

    Simplest approach: `BridgeListener` gets a `send_command(cmd_dict)` method that opens a short-lived WebSocket, sends one message, closes. This avoids threading issues with the receive loop.

```python
def send_command(self, cmd: dict):
    """Send a command to the bridge via a short-lived WebSocket."""
    try:
        ws = ws_lib.WebSocket()
        ws.connect(self.url, timeout=3)
        ws.send(json.dumps(cmd))
        ws.close()
    except Exception:
        pass
```

- [ ] **Step 4: Add LTM + health summary**

- Section label "STATUS"
- Labels: LTM count, emotional tier, encode rate, decision flip rate, brain status
- Updated each tick from `msg["ltm_count"]`, `msg["emotional_tier"]`, `msg["health"]`

- [ ] **Step 5: Wire into _update() and commit**

```bash
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: right column: attention/decision distributions, controls, LTM"
```

---

## Task 6: Centre Bottom: Timeline + Health + Event Log

Fill the bottom portion of the centre column.

**Files:**
- Modify: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Add timeline, health bar, and event log**

- Timeline: same as current (200-tick colour strip with legend), canvas height=80
- Health bar: single-line label with entropy, confidence, diversity, status
- Event log: ScrolledText, height=6, same as current

- [ ] **Step 2: Wire all into _update() and handle heartbeat messages**

Heartbeat handling (sleeping/dead/etc): same as current: update connection label with status colour, keep last tick data visible.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT> && git add phase2-bridge/norn_monitor.py
git commit -m "feat: centre bottom: timeline, health, event log"
```

---

## Task 7: Integration Test: Full Stack Verification

Run the complete stack and verify every panel works.

**Files:** No code changes: validation only.

- [ ] **Step 1: Start engine + bridge + monitor**

```bash
cd "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" && start "" "engine.exe" "Creatures 3"
# Load world, then:
cd <PROJECT_ROOT>/phase2-bridge
start "" python brain_bridge_client.py --multi-lobe --game "\"Creatures 3\"" --creature 0 --port 5555 --verbose
start "" python norn_monitor.py --port 5555
```

- [ ] **Step 2: Verify each panel**

Checklist:
- [ ] Top bar shows connected, tick counting, tps updating, timing text
- [ ] Left: sensory bars animate, drives update, chemicals grouped and colour-coded
- [ ] Centre: brain map shows 239 dots lighting up, 22 tracts with glow/colour
- [ ] Centre: timeline fills with decision colours, health bar updates, event log scrolls
- [ ] Right: attention shows top-10 sorted, decision shows all 14, winner highlighted
- [ ] Right: control buttons send commands (test Pause/Resume)
- [ ] Right: LTM count and tier update
- [ ] Monitor survives creature sleep (shows SLEEPING, keeps last data)
- [ ] Window fills Mon2 at 4K resolution

- [ ] **Step 3: Fix any issues found, commit**

```bash
cd <PROJECT_ROOT> && git add -A
git commit -m "feat: mission control monitor complete: all panels verified live"
```
