# NORNBRAIN Mission Control Monitor: Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Replaces:** Current `phase2-bridge/norn_monitor.py` (420-line prototype)

## Purpose

Full-screen 4K mission control dashboard for observing, understanding, and controlling the CfC brain in real time. Runs on Mon2 (28" 4K, 3840x2160). No tabs: everything visible at once.

Three roles:
1. **Observation**: see what the brain is doing, why, and how well
2. **Control**: intervene in the game world and brain state via buttons
3. **Education**: by watching chemicals, neurons, and tracts animate, the user builds mental models of how the pieces connect

## Layout

Three-column layout, no tabs, all panels visible simultaneously.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ TOP BAR: status │ tick │ tps │ timing decomposition text                │
├────────────────────┬─────────────────────────────┬───────────────────────┤
│  LEFT COLUMN       │  CENTRE COLUMN              │  RIGHT COLUMN         │
│  (320px fixed)     │  (flex, largest)             │  (300px fixed)        │
│                    │                             │                       │
│  SENSORY INPUTS    │  BRAIN MAP (top 60%)        │  ATTENTION (40 bars)  │
│  10 lobe bars      │  239 neurons as dots        │  labelled, ranked     │
│                    │  22 tracts as wires         │                       │
│  DRIVES (20 bars)  │  4 module clusters          │  DECISION (14 bars)   │
│  2 columns         │  left→right flow            │  labelled, ranked     │
│                    │  glow + colour on activity  │                       │
│  CHEMICALS         │                             │  CONTROL PANEL        │
│  ~25 key chems     │  TIMELINE (bottom 15%)      │  action buttons       │
│  colour by type    │  200-tick decision strip    │                       │
│                    │                             │  LTM + HEALTH         │
│                    │  HEALTH BAR                 │  memory count, tier   │
│                    │  entropy, conf, diversity   │  encode rate, status  │
│                    │                             │                       │
│                    │  EVENT LOG (bottom 25%)     │                       │
│                    │  scrolling, newest on top   │                       │
└────────────────────┴─────────────────────────────┴───────────────────────┘
```

## Panel Specifications

### Top Bar
- Connection status (green/red/purple for sleeping)
- Tick counter
- Ticks per second
- Timing decomposition: `R=95 B=1 W=3 L=1 = 100ms` as coloured text (no bar needed at this scale)

### Left Column: Inputs

**Sensory Inputs (10 lobes):**
Each lobe as a horizontal bar showing mean activation across its neurons.
- visn(40), smel(40), driv(20), prox(20), sitn(9), detl(11), noun(40), verb(17), resp(20), stim(40)
- Bar colour: blue gradient by intensity

**Drives (20 bars):**
Two-column layout, colour-coded green→yellow→red by intensity.
- Labels truncated to 8 chars
- Same as current monitor but tighter spacing for 4K

**Chemicals (~25 key chemicals):**
Grouped by category with colour coding:
- **Reinforcement (gold):** reward(204), punishment(205)
- **Arousal (red):** adrenalin(117), fear chem(158), anger chem(160)
- **Metabolism (green):** glucose(3), glycogen(4), starch(5), fat(10), protein(12), ATP(35), ADP(36)
- **Drives (blue):** pain(148), hunger_prot(149), hunger_carb(150), hunger_fat(151), tired(154), sleepy(155), lonely(156), bored(159), sex(161), comfort(162)
- **Neurotrophin (cyan):** downatrophin(17), upatrophin(18)
- **Toxin (magenta):** any non-zero toxin (66-75) shown dynamically

Each chemical as a labelled horizontal bar, sorted within category.

### Centre Column: Brain Map

**Brain Map Canvas (top 60% of centre):**

239 neurons arranged in 4 rectangular clusters, left-to-right flow:

```
Stage 1 (parallel):              Stage 2:
┌──────────┐
│ THALAMUS │ (70 neurons, 7×10 grid)
│          │────────────────┐
└──────────┘                │
┌──────────┐                ├──→ ┌────────────┐
│ AMYGDALA │ (52 neurons, ~7×8)──→│ PREFRONTAL │ (65 neurons, ~8×8)
└──────────┘                ├──→ └────────────┘
┌──────────┐                │
│  HIPPO   │ (52 neurons, ~7×8)
│          │────────────────┘
└──────────┘
```

**Neurons:**
- Each neuron is a circle (4-6px radius at 4K)
- Fill colour = activation level: black (0) → blue (low) → cyan (mid) → white (high)
- Arranged in rectangular grids within each module boundary
- Module boundary: rounded rectangle with module name label and current variance/energy text

**Tracts (22 wires):**
- Each tract drawn as a bezier curve from source region to destination module
- Default state: thin line, dim grey (#3a3a4a)
- Active state: line thickens (1→3px), colour shifts blue→cyan→yellow→red based on mean signal magnitude
- Glow effect: semi-transparent wider line behind the main line
- Signal strength = mean absolute value of (source activations × tract mask)

**Sensory input nodes:**
- Small labelled rectangles on the far left of the brain map
- Connected to Stage 1 modules via tract wires
- Fill intensity = mean lobe activation

**Motor output nodes:**
- Small labelled rectangles on the far right
- "ATTN" node connected from thalamus output
- "DECN" node connected from prefrontal output
- Highlighted border on the winner neuron

### Centre Column: Timeline + Health + Log

**Timeline (200 ticks):**
- Horizontal strip, colour-coded by decision index (14 distinct colours)
- Legend showing recent distinct decisions
- Same as current implementation

**Health Bar:**
- Single line: `entropy=X.XX  conf=X.XX  diversity=X.XX  [status]`
- Status colour-coded: green=healthy, yellow=stuck, red=converged

**Event Log:**
- Scrolling text, newest on top, capped at 200 lines
- Format: `[HH:MM:SS] decision → attention (conf X.XX)`

### Right Column: Outputs + Controls

**Attention Distribution (40 categories):**
- Vertical list of horizontal bars, sorted by activation (highest on top)
- Only show top 10 (rest are near-zero)
- Winner highlighted with bright border
- Label + bar + value

**Decision Distribution (14 active actions):**
- Same format as attention but for decisions
- Winner highlighted
- All 14 shown (fewer items)

**Control Panel:**
Buttons that send WebSocket commands to the bridge:
- `[Pause]` / `[Resume]`: toggle brain active
- `[Wipe Hidden]`: reset CfC hidden states
- `[Force Action ▼]`: dropdown: select decision+attention to force
- `[Save Weights]` / `[Load Weights]`
- `[Switch Creature ▼]`: dropdown: creature index 0/1/2
- `[Toggle RL]`: enable/disable online reinforcement learning
- `[Capture Scenario]`: save current state as training example
- `[Unzombify]`: release creature from zombie mode

**LTM + Health Summary:**
- Memory count
- Emotional tier
- Encode rate (% of recent ticks that encoded)
- Decision flip rate

## Data Sources

All data comes from the bridge WebSocket at `ws://localhost:{port}/ws`. The monitor is read-only except for control panel buttons which send JSON commands back via the same WebSocket.

**Tick message fields used:**
- `drives` (dict of 20 float values)
- `vision`, `general_sense` (lobe activations)
- `all_chemicals` (list of 256 floats)
- `lobes` (dict of lobe_id → activation list)
- `attention.values`, `attention.winner_index`, `attention.winner_label`
- `decision.values`, `decision.winner_index`, `decision.winner_label`
- `neuron_activations` (239 floats, concatenated hidden states)
- `timing` (read_ms, brain_ms, write_ms, ltm_ms, total_ms)
- `health` (attn_entropy, decn_confidence, module_variance, module_energy, action_diversity, status)
- `emotional_tier`
- `ltm_count`

**Control commands (sent as JSON via WebSocket):**
- `{"type": "pause"}`, `{"type": "resume"}`
- `{"type": "wipe_brain"}`
- `{"type": "force_action", "decision": N, "attention": M}`
- `{"type": "save_weights"}`, `{"type": "load_weights"}`
- `{"type": "switch_creature", "index": N}` (new: needs bridge support)
- `{"type": "train_rl_toggle"}`
- `{"type": "capture_scenario", "name": "...", "decision": N, "attention": M}`
- `{"type": "unzombify"}`

## Technical Approach

- Single file: `phase2-bridge/norn_monitor.py` (complete rewrite of current 420-line version)
- Pure tkinter + Canvas: no external GUI dependencies
- WebSocket via `websocket-client` (already installed)
- Background listener thread (same pattern as current)
- Canvas refresh rate: 200ms (5fps): sufficient for real-time feel at low CPU cost
- All drawing uses Canvas primitives (create_oval, create_line, create_rectangle, create_text)
- Neuron positions computed once at startup, stored as lists
- Tract bezier curves computed once, redrawn with updated colours each tick

## What This Does NOT Include

- 3D rendering or OpenGL
- Network graph physics (positions are fixed, not force-directed)
- Sound/audio feedback
- Multi-window mode
- Recording/playback of sessions
- Direct CAOS injection (control panel uses bridge WebSocket commands only)

## Success Criteria

1. Opens fullscreen on Mon2 at 4K resolution
2. All 239 neurons visible as individual dots that change colour per tick
3. All 22 tracts visible as wires that glow based on activity
4. Chemical levels animate in real time
5. Control panel buttons work (send WebSocket commands, bridge responds)
6. No tabs: everything visible simultaneously
7. Stays alive during creature sleep/death (shows status, doesn't go blank)
8. CPU usage < 15% on one core at 5fps refresh
