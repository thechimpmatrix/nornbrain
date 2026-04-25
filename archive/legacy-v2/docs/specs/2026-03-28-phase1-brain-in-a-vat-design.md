# Phase 1: Brain in a Vat: Design Spec
# Date: 2026-03-28
# Project: NORNBRAIN (LNN Brain Transplant for Creatures C3/DS)
# Status: Design approved in brainstorming session

---

## 1. Purpose

Build a standalone Python prototype of an LNN (Liquid Neural Network) brain that accepts Creatures C3/DS-format sensory inputs and produces action outputs, with a real-time browser dashboard for observation and manual control.

This is Phase 1 of the NORNBRAIN project. It proves the concept before any C++ or openc2e integration work begins.

### Success Criteria

1. The LNN brain produces coherent, distinct action sequences for different sensory scenarios
2. Behaviour adapts over time (the brain responds differently after receiving reward/punishment signals)
3. No degradation after extended runtime (>2 hours continuous, 10 ticks/sec = 72,000 ticks)
4. Action distribution differs meaningfully from random
5. All six predefined scenarios produce expected behaviour patterns
6. Real-time browser dashboard shows brain state at 10-30 ticks/sec without lag

---

## 2. Brain Core

### 2.1 Architecture

A `NornBrain` class wrapping a CfC (Closed-form Continuous-time) model with NCP (Neural Circuit Policy) wiring.

**Why CfC over LTC:** CfC is 100-100,000x faster at inference (no ODE solver), preserves the "liquid" adaptive inference property, and is well within the 50ms brain tick budget. See `docs/verified-reference.md` Part V Section 1 for full rationale.

### 2.2 Input Vector

The input vector matches the C3/DS lobes that the openc2e engine actually accesses (verified from source code: see `docs/verified-reference.md` Part II Section 2):

| Group | Features | Count | Source Lobe |
|-------|----------|-------|-------------|
| Drives | pain, hunger_protein, hunger_carb, hunger_fat, coldness, hotness, tiredness, sleepiness, loneliness, crowdedness, fear, boredom, anger, sex_drive, comfort | 15 | driv |
| Vision | distance to nearest agent per category (food, norn, grendel, ettin, gadget, plant, fruit, animal, detritus, vehicle, ...) | 20 | visn |
| Verb | player verb input neurons | 16 | verb |
| Noun | player noun input neurons | 20 | noun |
| General Sense | patted, slapped, wall_bump, near_wall, in_vehicle, creature_nearby, opposite_sex_nearby, sibling_nearby | 8 | sens |
| Key Chemicals | reward, punishment, adrenaline, sleepase, comfort, grendel_nitrate, fear_toxin, tiredness_chem, loneliness_chem, crowdedness_chem | 10 | biochemistry (operand type 7 in SVRules) |

**Total input features: ~89**

All values are float in range [0.0, 1.0], matching the openc2e external input convention.

### 2.3 NCP Wiring

Custom NCP wiring structure mirroring the Creatures lobe architecture:

| Layer | Neuron Type | Count | Role | Creatures Equivalent |
|-------|-------------|-------|------|---------------------|
| Input | Sensory | (implicit: fed by input vector) | Receives all 89 input features | driv + visn + verb + noun + sens + chemicals |
| Hidden 1 | Inter | 40 | Feature combination, pattern detection | Combination lobe ("comb") |
| Hidden 2 | Command | 25 (with recurrence) | Decision integration, temporal memory | Core decision processing |
| Output | Motor | 35 (20 attention + 15 decision) | Action selection via WTA | attn + decn |

**Total neurons: 100** (40 inter + 25 command + 35 motor)

Wiring constructed with `ncps.wirings.NCP()`:
- `inter_neurons=40`
- `command_neurons=25`
- `motor_neurons=35`
- `sensory_fanout=20` (each sensory input connects to ~20 inter neurons)
- `inter_fanout=12` (each inter neuron connects to ~12 command neurons)
- `recurrent_command_synapses=25` (rich recurrence within command layer)
- `motor_fanin=12` (each motor neuron receives from ~12 command neurons)

### 2.4 Output Decoding

The 35 motor neurons are split into two groups:

**Attention outputs (first 20 motor neurons):**

| Index | Category |
|-------|----------|
| 0 | food |
| 1 | fruit |
| 2 | plant |
| 3 | animal |
| 4 | detritus |
| 5 | norn |
| 6 | grendel |
| 7 | ettin |
| 8 | gadget |
| 9 | vehicle |
| 10 | hand (player) |
| 11-19 | reserved |

**Decision outputs (last 15 motor neurons):**

| Index | Action | Creatures Equivalent |
|-------|--------|---------------------|
| 0 | push | Push (activate 1: e.g. eat food, press button) |
| 1 | pull | Pull (activate 2) |
| 2 | approach | Move toward attention target |
| 3 | retreat | Move away from attention target |
| 4 | get | Pick up |
| 5 | drop | Put down |
| 6 | speak | Say something |
| 7 | sleep | Go to sleep |
| 8 | walk_left | Walk west |
| 9 | walk_right | Walk east |
| 10 | go_up | Go up (lift/door) |
| 11 | go_down | Go down (lift/door) |
| 12 | stop | Do nothing |
| 13 | express | Express emotion |
| 14 | wait | Wait in place |

Winner-Takes-All: `attention_winner = argmax(motor[:20])`, `decision_winner = argmax(motor[20:])`.

Combined output example: Decision=push(0), Attention=food(0) → "the Norn pushes food" = eating.

### 2.5 State Management

- Hidden state: `torch.Tensor` of shape `(1, 100)`: carried between ticks
- `wipe()`: resets hidden state to zeros (equivalent to `c2eLobe::wipe()`)
- No online weight modification: the "liquid" property provides adaptive inference through input-dependent time constants
- Chemical feedback (reward/punishment) enters through the input vector, not through weight modification

### 2.6 Training Strategy (Phase 1)

The brain starts **untrained**: random weights. Phase 1 uses a simple training loop:

1. Present scenario inputs (e.g., hungry + food nearby)
2. Compute loss: cross-entropy between output and target action (e.g., push + food)
3. Backpropagate and update weights
4. Repeat across all scenarios with variation

This is **behaviour cloning from designed targets**, not from the original SVRule brain. The goal is to prove the architecture can learn appropriate stimulus-response mappings, not to replicate the original brain's exact behaviour (that's Phase 2+).

After training, weights are frozen and the brain runs in inference mode. The "liquid" adaptive inference continues to adjust temporal dynamics based on input.

---

## 3. Sensory Scenario Simulator

### 3.1 Scenario Format

Each scenario is a Python dataclass defining input values over time:

```python
@dataclass
class Scenario:
    name: str
    description: str
    duration_ticks: int  # Default 200
    drives: dict[str, float]  # Drive name -> value
    vision: dict[str, float]  # Category -> distance (0.0=touching, 1.0=far)
    general_sense: dict[str, float]  # Sense name -> value
    chemicals: dict[str, float]  # Chemical name -> value
    expected_decision: str  # Expected action label
    expected_attention: str  # Expected attention label
```

### 3.2 Predefined Scenarios

| # | Name | Drives | Vision | Chemicals | Expected Decision + Attention |
|---|------|--------|--------|-----------|-------------------------------|
| 1 | hungry_food | hunger_protein=0.8 | food@0.2 |: | push + food |
| 2 | grendel_threat | fear=0.7, pain=0.3 | grendel@0.3 | adrenaline=0.5 | retreat + grendel |
| 3 | bored_idle | boredom=0.9 | nothing nearby |: | walk_left or walk_right + varies |
| 4 | player_pats |: | hand@0.1 | reward=0.8 | approach + hand |
| 5 | sleepy | tiredness=0.8, sleepiness=0.9 | nothing | sleepase=0.6 | sleep + (any) |
| 6 | drive_conflict | hunger_protein=0.7, fear=0.6 | food@0.2, grendel@0.3 | adrenaline=0.3 | (observed: no fixed expectation) |

Scenarios 1-5 have target behaviours for training. Scenario 6 is an observation-only test of drive competition: whatever the brain decides is interesting data.

### 3.3 Input Ramping

Scenarios don't apply inputs instantly. Over the first 20 ticks, inputs ramp linearly from 0 to target values. This models the gradual perception of stimuli and avoids shocking the network with sudden state changes.

### 3.4 Chemical Feedback Loop

After each tick, simple feedback rules simulate the biochemistry response:
- If decision=push and attention=food: reward += 0.1 (food is good)
- If decision=retreat and grendel nearby: reward += 0.05 (escaping is good)
- If decision=push and attention=grendel: punishment += 0.1 (attacking grendels is bad)
- All chemicals decay by 5% per tick (simple half-life approximation)

This is a simplified stand-in for the full C3/DS biochemistry system. It provides enough feedback for the brain to associate scenarios with outcomes.

---

## 4. FastAPI + WebSocket Server

### 4.1 Architecture

Single Python process: brain + tick loop + HTTP server + WebSocket.

```
server.py
  ├── FastAPI app
  │   ├── GET / → serves dashboard.html
  │   └── WS /ws → real-time brain state stream
  ├── NornBrain instance
  ├── Scenario loader
  └── Tick loop (asyncio)
```

### 4.2 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serves `dashboard.html` |
| WebSocket | `/ws` | Bidirectional real-time communication |

### 4.3 WebSocket Protocol

**Server → Client (every tick):**

```json
{
  "tick": 142,
  "running": true,
  "ticks_per_second": 10,
  "scenario": "hungry_food",
  "drives": {"pain": 0.1, "hunger_protein": 0.8, "hunger_carb": 0.0, ...},
  "vision": {"food": 0.2, "grendel": 1.0, ...},
  "general_sense": {"patted": 0.0, "slapped": 0.0, ...},
  "chemicals": {"reward": 0.0, "punishment": 0.0, "adrenaline": 0.0, ...},
  "neuron_activations": [0.3, 0.0, 0.7, ...],
  "neuron_types": ["inter", "inter", ..., "command", ..., "motor", ...],
  "attention": {"winner_index": 0, "winner_label": "food", "values": [0.7, 0.1, ...]},
  "decision": {"winner_index": 0, "winner_label": "push", "values": [0.8, 0.1, ...]},
  "stability": {"mean_activation": 0.34, "variance": 0.08, "tick_history_len": 500}
}
```

**Client → Server (commands):**

```json
{"type": "set_drive", "name": "fear", "value": 0.7}
{"type": "set_vision", "category": "grendel", "distance": 0.3}
{"type": "set_chemical", "name": "adrenaline", "value": 0.5}
{"type": "set_sense", "name": "patted", "value": 1.0}
{"type": "load_scenario", "name": "hungry_food"}
{"type": "clear_inputs"}
{"type": "set_speed", "ticks_per_second": 10}
{"type": "reset_brain"}
{"type": "pause"}
{"type": "resume"}
{"type": "train", "epochs": 100}
```

### 4.4 Tick Loop

```
every (1 / ticks_per_second) seconds:
  1. Apply current inputs (from scenario or manual overrides) to input vector
  2. Run brain forward pass: output, hx = brain(input_tensor, hx)
  3. Decode attention and decision winners
  4. Apply chemical feedback rules
  5. Apply chemical decay (5% per tick)
  6. Record stability metrics (mean activation, variance)
  7. Broadcast state to all connected WebSocket clients
```

Default speed: 10 ticks/sec. Adjustable from 1 to 60 via dashboard control.

### 4.5 Port

`localhost:8100`: avoids conflict with cc-hub (5200) and other dev servers.

---

## 5. Browser Dashboard

### 5.1 Technology

Single HTML file (`dashboard.html`) with inline CSS and JavaScript. No frameworks, no build step, no external dependencies. Dark theme.

Connects to `ws://localhost:8100/ws` on load. Renders all panels via Canvas 2D API and DOM elements.

### 5.2 Layout

3x2 grid:

```
+---------------------------+---------------------------+
|   NCP Wiring Graph        |   Drive Bars              |
|   (Canvas)                |   (DOM bars)              |
+---------------------------+---------------------------+
|   Neuron Heatmap          |   Action Output           |
|   (Canvas)                |   (DOM + Canvas bars)     |
+---------------------------+---------------------------+
|   Input Controls          |   Stability Monitor       |
|   (DOM sliders/buttons)   |   (Canvas line chart)     |
+---------------------------+---------------------------+
```

### 5.3 Panel Specifications

**Panel 1: NCP Wiring Graph (top-left)**
- Canvas-drawn directed graph
- 4 rows: sensory inputs (top) → inter → command → motor (bottom)
- Nodes: circles, sized by neuron type, coloured by activation (blue=0.0 → white=0.5 → red=1.0)
- Edges: lines connecting neurons per NCP wiring, opacity = abs(signal strength)
- Command neuron recurrent connections shown as curved self-loops
- Updates every tick

**Panel 2: Drive Bars (top-right)**
- 15 horizontal bars, one per C3/DS drive
- Label on left, value on right
- Colour gradient: green (0.0) → yellow (0.5) → red (1.0)
- Sorted by value (highest drive at top) for quick visual scanning
- Updates every tick

**Panel 3: Neuron Heatmap (middle-left)**
- Grid of coloured rectangles, one per neuron (10 columns x 10 rows for 100 neurons)
- Colour = activation level (same blue→white→red scale)
- Border colour indicates type: green=inter, blue=command, orange=motor
- Tooltip on hover: neuron ID, type, current value
- Updates every tick

**Panel 4: Action Output (middle-right)**
- Large text showing current decision and attention: "PUSH → FOOD"
- Below: two bar charts showing all motor neuron values
  - Top bar chart: 20 attention neurons with category labels
  - Bottom bar chart: 15 decision neurons with action labels
- Winner bars highlighted
- History log: scrolling list of last 50 decision+attention pairs with tick numbers
- Updates every tick

**Panel 5: Input Controls (bottom-left)**
- Scenario dropdown + "Load" button
- Speed slider (1-60 ticks/sec)
- Pause / Resume / Reset buttons
- "Train" button (runs training epochs)
- Collapsible sections for manual overrides:
  - Drive sliders (15 sliders, 0.0-1.0)
  - Vision distance sliders (per category, 0.0-1.0)
  - Chemical sliders (10 key chemicals, 0.0-1.0)
  - General sense toggles
- "Clear All Inputs" button

**Panel 6: Stability Monitor (bottom-right)**
- Rolling line chart, X = tick (last 500), Y = value
- Two lines: mean neuron activation (blue) and activation variance (orange)
- Horizontal reference lines at normal ranges
- If variance drops below 0.01 or exceeds 0.5, the background flashes red (OHSS-like warning)
- Updates every tick

---

## 6. File Structure

```
phase1-prototype/
├── norn_brain.py          # NornBrain class: CfC + NCP wiring, train(), forward(), wipe()
├── scenarios.py           # Scenario dataclass + 6 predefined scenarios + chemical feedback
├── server.py              # FastAPI app, WebSocket handler, tick loop, entry point
├── dashboard.html         # Single-file browser dashboard (HTML + CSS + JS)
├── requirements.txt       # fastapi, uvicorn[standard], torch, ncps, websockets
└── tests/
    ├── test_brain.py      # Brain produces valid outputs, state persists between ticks
    ├── test_scenarios.py  # Each scenario produces distinct behaviour after training
    └── test_stability.py  # Extended runtime (10k+ ticks), no degradation
```

### 6.1 Dependencies

```
torch>=2.0
ncps>=1.0.0
fastapi>=0.100
uvicorn[standard]>=0.20
websockets>=11.0
```

No GPU required. CPU inference for a 100-neuron CfC is sub-millisecond.

---

## 7. What This Design Does NOT Include

- No C++ code or openc2e integration (that's Phase 2)
- No genome parsing or genetic encoding (Phase 3)
- No full biochemistry simulation (simplified chemical feedback only)
- No language learning or social behaviour (Phase 4)
- No persistent brain saves (stretch goal for later)
- No 2D world simulation (stretch goal B: noted but not in this spec)

---

## 8. Reference Documents

- `docs/verified-reference.md`: 3,666-line cross-verified reference (all four research domains)
- `reference/c3ds-brain-architecture.md`: Creatures C3/DS brain details
- `reference-liquid-neural-networks.md`: LNN/LTC/CfC theory
- `research/ncps-reference.md`: ncps package API
- `research/openc2e-brain-reference.md`: openc2e source code interface
- `LNN-CREATURES-CC-SPEC.md`: Original project specification
