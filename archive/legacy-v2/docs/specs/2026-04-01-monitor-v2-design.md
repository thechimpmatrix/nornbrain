# Mission Control Monitor v2: Design Specification

**Date:** 2026-04-01
**Status:** SPEC: approved via brainstorming
**Supersedes:** v1 monitor layout (retained as `norn_monitor_v1_backup.py`)

---

## 1. Overview

Full rewrite of the NORNBRAIN mission control monitor to support the v2 brain architecture (1,100 neurons, 4 hierarchical CfC modules, 3 signal types, bidirectional inter-module flows). The v1 monitor is preserved as a backup; the new monitor replaces it entirely.

The monitor runs on a near-4K display (~3840×2160), uses Tkinter with DPI-aware scaling (carried from v1), and receives telemetry via UDP from the v2 brain wrapper (`nornbrain_cfc_v2.py`) plus creature state via TCP CAOS from openc2e.

---

## 2. Key Differences from v1

| Aspect | v1 | v2 |
|--------|-----|-----|
| Neurons | 239 (70+52+52+65) | 1,100 (160+110+160+670) |
| Modules | thalamus, amygdala, hippocampus, prefrontal | thalamus, amygdala, hippocampus, frontal |
| Brain map layout | Stage 1 left, Stage 2 right (feedforward) | Hierarchical: thalamus top, hipp/amyg middle, frontal bottom |
| Tracts | 22, all drawn same color | 32, color-coded by signal type |
| Signal types | None (all tracts identical) | Data (blue), Modulation (yellow), Memory (purple) |
| Bidirectional flows | None | 4 feedback tracts drawn with upward arrows |
| Per-module detail | Variance/energy labels only | Full detail panels with signal type breakdown, neuron grids |
| Telemetry version field | None | `"version": "v2"` in UDP packets |

---

## 3. Layout

Three columns on near-4K canvas, Tokyo Night dark theme.

### 3.1 Left Column (~20% width)

Carried from v1 with no structural changes:

- **Sensory Input Panel:** 10 lobe bars (visn, smel, driv, prox, sitn, detl, noun, verb, resp, stim) showing mean activation. Horizontal bars, same color ramp as v1.
- **Drive Panel:** 20 drives in 2-column grid. Color-coded green→yellow→red by intensity. Labels: pain, hunger_prot, hunger_carb, hunger_fat, cold, hot, tired, sleepy, lonely, crowded, fear, bored, anger, sex_drive, comfort, + 5 navigation drives.
- **Chemical Panel:** Grouped display: Reinforcement (reward 204, punishment 205), Arousal (adrenalin 117, fear 158, anger 160), Metabolism (glucose 3, energy 34, ATP 35), key drive chemicals (148-162). Same grouping as v1.

### 3.2 Center Column (~50% width)

#### Top: Brain Map (hierarchical layout)

```
    ┌─ visn ─ smel ─ prox ─ sitn ─ loc ─ stim ─ detl ─ driv ─┐
    │                  EXTERNAL INPUTS                          │
    │                                                           │
    │            ┌──────────────────────┐                       │
    │            │     THALAMUS (160)   │                       │
    │            │     ■■■■■■■■■■■■■■   │ ← fast τ             │
    │            └──────────┬───────────┘                       │
    │              DATA ↓   ↑ MEM (hipp)   ↑ MOD (amyg)        │
    │         ┌─────────────┴──────────────────┐                │
    │   ┌─────┴──────────┐    ┌────────────────┴───┐           │
    │   │ HIPPOCAMPUS    │◄──►│     AMYGDALA       │           │
    │   │ (160) slow τ   │MEM │     (110) mixed τ  │           │
    │   └──────┬─────────┘DATA└────────┬───────────┘           │
    │          │ DATA                  │ DATA                   │
    │          └──────────┬────────────┘                        │
    │            ┌────────▼─────────────────────────┐           │
    │  noun ──►  │       FRONTAL CORTEX (670)       │           │
    │  verb ──►  │       ■■■■■■■■■■■■■■■■■■■■■■■   │           │
    │  chem ──MOD│       moderate τ                 │ ← ltm MEM│
    │            └──────────┬───────────────────────┘           │
    │                  ATTN(40)  DECN(14)                       │
    └───────────────────────────────────────────────────────────┘
```

**Module rendering:**
- Each module drawn as a rounded rectangle containing a neuron grid
- Neurons as small circles (radius scales with DPI), color mapped 0.0→1.0: black→blue→cyan→white (same ramp as v1)
- Module label above: name, neuron count, time bias
- Module stats below: variance, energy, mean activation

**Neuron grid sizing:**
- Thalamus 160: 16×10 grid
- Amygdala 110: 11×10 grid
- Hippocampus 160: 16×10 grid
- Frontal 670: 34×20 grid (spans full width, neurons will be small but visible at 4K)

**Tract rendering (32 tracts):**
- Drawn as curved paths (quadratic Bezier or S-curves) between module rectangles
- Color-coded by signal type:
  - **Data:** `#7AA2F7` (blue): information flow
  - **Modulation:** `#E0AF68` (yellow/amber): gain control
  - **Memory:** `#BB9AF7` (purple): context injection
- Line thickness proportional to tract signal strength (from telemetry)
- Forward tracts (downward): solid lines with downward arrowhead
- Feedback tracts (upward): dashed lines with upward arrowhead
- External input tracts: thin lines from input nodes along top edge to thalamus

**Feedback tracts (visually distinct):**
- `hippocampus_to_thalamus_mem`: upward, purple, dashed
- `amygdala_to_thalamus_mod`: upward, yellow, dashed
- `hippocampus_to_amygdala_mem`: horizontal, purple, dashed
- `amygdala_to_hippocampus_data`: horizontal, blue, dashed

**External input nodes:**
- Drawn along the top edge of the brain map
- Labels: visn, smel, prox, sitn, loc, stim, detl, driv
- Lines connect down to thalamus (their primary target)
- noun, verb enter from the left side directly into frontal
- chem enters from the left side into amygdala and frontal
- ltm enters from the right side into frontal

#### Bottom: Timeline

Decision history as color bars: 200-tick rolling window. Each bar colored by decision action. Legend shows last 4 unique actions. Carried from v1 unchanged.

### 3.3 Right Column (~30% width)

#### Per-Module Detail Panels (NEW)

Four stacked panels, one per module (thalamus, hippocampus, amygdala, frontal: in processing order). Each panel contains:

**Header row:** Module name | neuron count | time bias | variance | energy

**Signal type input breakdown (3 sub-rows):**
- DATA inputs: list of tract names with live strength values, blue accent
- MOD inputs: list of tract names with live strength values, yellow accent  
- MEM inputs: list of tract names with live strength values, purple accent
- Only show input types that the module actually receives (e.g., hippocampus has no external data inputs)

**Neuron mini-grid:** Compact version of the module's neuron grid (same color ramp). Smaller than the brain map version: serves as a zoomed-out heatmap. For frontal (670 neurons), render as a 67×10 strip.

**Module output summary:** Mean activation of motor neurons, top-3 most active neurons

#### Attention Panel

Top 10 of 40 attention categories, sorted descending by activation. Winner highlighted green. Carried from v1.

#### Decision Panel

14 actions with activation bars. Winner highlighted yellow. Action-specific colors. Carried from v1.

#### Controls

Row of buttons: Pause | Resume | Wipe Hidden | Save Weights | Toggle RL | Capture Scenario. Carried from v1.

#### Status Bar

- Connection status (green/yellow/red)
- Creature name and genus
- Game tick, TPS
- RL status: enabled/disabled, steps, loss, reward
- Brain version: "v2 (1,100 neurons)"

---

## 4. Telemetry Format

### 4.1 UDP Packet (from nornbrain_cfc_v2.py)

```json
{
    "type": "brain_telemetry",
    "version": "v2",
    "tick": 1234,
    "neuron_activations": [0.0, 0.1, ...],  // 255 values (all module outputs concatenated)
    "attention_values": [0.0, ...],           // 40 values
    "decision_values": [0.0, ...],            // 17 values (14 active)
    "attention_winner": 11,
    "decision_winner": 4,
    "module_variance": {"thalamus": 0.05, "amygdala": 0.03, "hippocampus": 0.04, "frontal": 0.06},
    "module_energy": {"thalamus": 1.2, "amygdala": 0.8, "hippocampus": 1.1, "frontal": 3.5},
    "lobe_inputs": {"visn": [...], "driv": [...], ...},
    "attn_entropy": 2.3,
    "decn_confidence": 0.7,
    "rl_enabled": true,
    "rl_steps": 45,
    "rl_loss": -0.02,
    "rl_reward": 0.5
}
```

### 4.2 TCP CAOS (unchanged from v1)

Creature state polled via CAOS commands on port 20001. Drives, chemicals, position, alive/dead, life stage. No changes needed.

### 4.3 Tract Signal Strength Computation

For each tract, compute signal strength from the source module's output activations or the source lobe's input activations. The monitor uses the `neuron_activations` array with module offsets:

| Module | Offset | Count |
|--------|--------|-------|
| thalamus | 0 | 40 (motor output) |
| amygdala | 40 | 25 (motor output) |
| hippocampus | 65 | 40 (motor output) |
| frontal | 105 | 150 (motor output) |

Note: `neuron_activations` contains motor outputs only (not full hidden states). Total = 40+25+40+150 = 255.

For external input tracts, use `lobe_inputs` dict values to compute mean activation.

---

## 5. Module Configuration (Data-Driven)

All module metadata in a single `MODULES_V2` dict: no hardcoded names scattered through the code:

```python
MODULES_V2 = {
    "thalamus": {
        "neurons": 160, "motor": 40, "offset": 0,
        "grid": (16, 10), "time_bias": "fast",
        "position": "top_center",  # brain map placement
        "color": "#7DCFFF",        # module accent color
    },
    "hippocampus": {
        "neurons": 160, "motor": 40, "offset": 40,
        "grid": (16, 10), "time_bias": "slow",
        "position": "mid_left",
        "color": "#BB9AF7",
    },
    "amygdala": {
        "neurons": 110, "motor": 25, "offset": 65,
        "grid": (11, 10), "time_bias": "mixed",
        "position": "mid_right",
        "color": "#E0AF68",
    },
    "frontal": {
        "neurons": 670, "motor": 150, "offset": 105,
        "grid": (34, 20), "time_bias": "moderate",
        "position": "bottom_full",
        "color": "#9ECE6A",
    },
}
```

And a `TRACTS_V2` list generated from the genome or hardcoded to match `brain_genome_v2.py`'s 32 tracts, each with `src`, `dst`, `signal_type`, and `name`.

---

## 6. Signal Type Color Scheme

| Signal Type | Color | Hex | Meaning |
|-------------|-------|-----|---------|
| Data | Blue | `#7AA2F7` | Raw information flow |
| Modulation | Amber/Yellow | `#E0AF68` | Gain control |
| Memory | Purple | `#BB9AF7` | Context injection |

These colors are used for:
- Tract lines in the brain map
- Signal type labels in the per-module detail panels
- Accent colors on the input breakdown rows

---

## 7. Preserved from v1 (No Changes)

- Tkinter framework with DPI-aware scaling (`self.S()`, `self.F()`)
- Tokyo Night dark theme colors
- UDP reception thread with port fallback (20002-20004)
- TCP CAOS polling thread with exponential backoff
- Thread-safe data merging with locks
- Error-boundary wrapped panel drawing (try-catch per panel)
- `_safe_get()` helper for nested dict access
- `_activation_colour()` ramp: black→blue→cyan→white
- Timeline canvas (200-tick decision history)
- Sensory lobe bars, drive grid, chemical groups
- Attention top-10, decision 14-bar panel
- Control buttons (pause, resume, wipe, save, RL toggle, capture)
- Connection status indicator
- Event log (rolling 200-line buffer)

---

## 8. Files

| File | Action |
|------|--------|
| `phase2-bridge/norn_monitor_v1_backup.py` | Create (copy of current norn_monitor.py) |
| `phase2-bridge/norn_monitor.py` | Rewrite (v2 monitor) |
| `phase2-bridge/telemetry.py` | Update module names (prefrontal → frontal) |

---

## 9. Success Criteria

1. Monitor displays 1,100 neurons across 4 modules in hierarchical brain map layout
2. 32 tracts color-coded by signal type (blue/yellow/purple) with directional arrows
3. Feedback tracts visually distinct (dashed, upward arrows)
4. Per-module detail panels show live signal type input breakdown
5. All carried-from-v1 panels (drives, chemicals, attention, decision) work identically
6. Status bar shows "v2 (1,100 neurons)"
7. Refreshes at 5 Hz on 4K display without lag
8. Gracefully degrades on missing data (no crashes)
