# NORNBRAIN Phase 2: Brain Bridge Design (Consolidated)
# Date: 2026-03-29
# Supersedes: 2026-03-28-phase2-caos-brain-bridge-design.md
# Status: Approved design: ready for implementation planning

---

## 0. Document Purpose and Scope

This document is the single authoritative design reference for Phase 2 of NORNBRAIN. It supersedes the previous `2026-03-28-phase2-caos-brain-bridge-design.md` and all earlier bridge-related specs.

It covers:
- The full system architecture for connecting the Phase 1 CfC brain to a live Steam Creatures 3 game
- The autonomous workflow: how the project author drives experiment → verify → build cycles without human intervention
- All three tooling layers: structured experiments, probe-mode validation, the CAOS agent, and the Python bridge client
- Complete file inventory: what gets created, modified, and deleted
- Every known technical risk, unknown, and its resolution strategy

**What this document does NOT cover:**
- Phase 1 (complete: see `2026-03-28-phase1-brain-in-a-vat-design.md`)
- Phase 2d (975-neuron scale-up: deferred until Phase 2c integration is stable)
- Phase 3 genome-driven architecture
- Phase 4 language and social behaviour

---

## 1. Goals and Success Criteria

### Primary Goal
A Norn in Steam Creatures 3 (Engine 1.162) has its SVRule brain replaced by the Phase 1 CfC/NCP brain. The creature makes decisions: eats when hungry, flees grendels, responds to the hand: driven entirely by CfC outputs.

### Success Criteria (in order)
1. **SC1: Bridge connects:** `brain_bridge_client.py` connects to C3, reads creature state, runs CfC inference, writes decisions back: all in real time
2. **SC2: Creature responds:** The creature visibly responds to CfC decisions (approaches food, retreats from grendel, etc.) with its SVRule brain disabled
3. **SC3: Biochemistry feeds the brain:** Chemical concentrations (hunger, fear, reward, punishment) modulate CfC input and measurably affect decisions
4. **SC4: Dashboard shows live data:** Phase 1 dashboard on `:8100` shows real creature state: neuron activations, drive bars, decision outputs: updated in real time from the game
5. **SC5: No game modification:** No game binary modification, no DLL injection. Only a `.cos` script installed in Bootstrap and an external Python process

### Non-Goals for Phase 2
- Multi-creature support (one creature at a time)
- Training from within the game (training stays offline in Phase 1)
- Replacing biochemistry, sensory, motor, or linguistic systems
- C++ implementation of the brain
- openc2e integration (eliminated)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Steam Creatures 3: Engine 1.162 (Windows, running)    │
│                                                         │
│  ┌──────────────────┐   ┌───────────────────────────┐  │
│  │  Target Creature  │   │  nornbrain_bridge.cos      │  │
│  │  (brain disabled) │◄──┤  CAOS agent, 1:1:200      │  │
│  │  Biochem: ON      │   │  Fires every 4 game ticks  │  │
│  │  Sensory: ON      │   │  (~200ms at normal speed)  │  │
│  │  Motor: ON        │   │                           │  │
│  └──────────────────┘   │  Per tick:                 │  │
│                         │  1. Read state → GAME vars  │  │
│                         │  2. Check nb_out_ready      │  │
│                         │  3. Apply decision (SPNL    │  │
│                         │     or ZOMB+ORDR fallback)  │  │
│                         └───────────────────────────┘  │
│                    ▲ Win32 shared memory (c2e@ buffer) ▼ │
└────────────────────┼────────────────────────────────────┘
                     │
        ┌────────────┴──────────────────────────────┐
        │  brain_bridge_client.py  (Windows Python)  │
        │                                           │
        │  ┌──────────────────────────────────────┐ │
        │  │  C2eConnection (from c2e_bridge.py)   │ │
        │  │  Win32 shared memory, mutex-protected │ │
        │  │  ~5.8ms per batched read (confirmed)  │ │
        │  └──────────────────────────────────────┘ │
        │              │ poll 20ms                  │
        │  ┌──────────────────────────────────────┐ │
        │  │  BrainBridgeClient                   │ │
        │  │  - Reads GAME vars (89 inputs)        │ │
        │  │  - Constructs BrainInput              │ │
        │  │  - Runs NornBrain.tick()              │ │
        │  │  - Writes nb_out_decn, nb_out_attn   │ │
        │  │  - Sets nb_out_ready = 1              │ │
        │  └──────────────────────────────────────┘ │
        │              │ WebSocket                  │
        │  ┌──────────────────────────────────────┐ │
        │  │  FastAPI + WebSocket (:8100)          │ │
        │  │  Streams live brain state to          │ │
        │  │  dashboard.html (Phase 1, unchanged)  │ │
        │  └──────────────────────────────────────┘ │
        └───────────────────────────────────────────┘
                     │ import
        ┌────────────┴───────────────────┐
        │  phase1-prototype/norn_brain.py │
        │  CfC/NCP brain (unchanged)      │
        │  89 inputs → 100 neurons → 35   │
        └────────────────────────────────┘
```

### Data Flow Per Brain Cycle

```
Game tick N (engine, inside C3):
  Bridge agent fires (every 4 ticks):
    → Read 15 drives (DRIV 0..14)
    → Read 10 chemicals (CHEM ids)
    → Read 20 vision distances (SEEN per category + POSX/POSY maths)
    → Read 8 general senses (ATTN, UNCS, ZOMB, wall proximity, etc.)
    → Pack all into GAME "nb_*" variables
    → Increment GAME "nb_tick"
    → Set GAME "nb_input_ready" = 1
    → Check GAME "nb_out_ready":
        if 1:
          Read nb_out_decn, nb_out_attn
          Apply via SPNL or ZOMB+ORDR (path selected at startup)
          Set nb_out_ready = 0

Python process (async, polling every 20ms):
    → Read GAME "nb_tick"
    → If tick > last_seen_tick:
        Batch-read all nb_* input vars (single CAOS injection)
        Construct BrainInput (89 values)
        Call NornBrain.tick(brain_input) → BrainOutput
        Write nb_out_decn = output.decision_winner
        Write nb_out_attn = output.attention_winner
        Set nb_out_ready = 1
        Broadcast state to WebSocket clients
        Update last_seen_tick
```

**Timing budget:**
- Game tick interval: ~50ms at normal speed (20 ticks/sec)
- Brain tick interval: 4 × 50ms = ~200ms
- Python poll interval: 20ms (10 polls per brain tick window)
- Batch read latency: 5.8ms avg (confirmed E9)
- CfC inference: <1ms (100-neuron CfC on CPU, confirmed Phase 1)
- Total Python latency per cycle: ~7ms
- Slack: ~193ms: no timing risk

---

## 3. CC Autonomous Workflow

### The Core Loop

the project author operates fully autonomously on this project. It can:
- Run Python scripts in the VS Code terminal and read their output
- Inject arbitrary CAOS into the running game via `c2e_bridge.py --caos`
- Read `results.json` after experiment runs
- Check whether C3 is running (check for `engine.exe` process)
- Launch C3 if it is not running
- Kill and relaunch C3 if needed for a clean state

CC surfaces decisions to the user only when genuine design choices arise (e.g. "SPNL confirmed non-functional: proceed with ZOMB fallback or investigate further?"). Everything else is autonomous.

### Phase Sequence

```
Phase 2a-fix:  Resolve open unknowns via CAOS injection + experiments.py
    ↓ (gate: unknowns resolved, decisions logged)
Phase 2b-build: Write nornbrain_bridge.cos + brain_bridge_client.py
    ↓ (gate: unit tests pass, probe mode passes)
Phase 2c-integrate: Install .cos, run live integration, observe creature
    ↓ (gate: SC1-SC5 all confirmed)
Phase 2d (deferred): Scale to 975 neurons + 243 inputs
```

### How CC Resolves Unknowns

CC does not wait for human input to run experiments. The sequence is:

1. Run targeted CAOS probe via `c2e_bridge.py --caos`
2. Parse the result directly from stdout
3. If result is conclusive: log the finding, proceed to next step
4. If result is ambiguous: run a follow-up probe
5. If multiple probes fail to resolve: present the finding to the user with specific options

---

## 4. Open Unknowns and Resolution Plan

These two unknowns must be resolved before bridge code is written. They are the first thing CC does at implementation start.

### Unknown 1: Does SPNL drive creature behaviour with brain disabled?

**What we know:**
- `SPNL "decn" N value`: accepted without error (E6 confirmed)
- SPNL sets the *input* of a neuron in the named lobe (per CAOS reference)
- SOUL 1 0 disables brain faculty (faculty 1), not motor faculty (faculty 2)
- Motor faculty reads WTA result from `decn` lobe to determine creature action
- **Unknown:** Does motor faculty still read `decn` lobe outputs when brain faculty is disabled? Or does SOUL 1 0 freeze the entire lobe processing pipeline including motor reads?

**Resolution probe sequence:**

```
Probe 1a: Baseline movement confirmation:
  targ norn soul 1 0
  (wait 500ms)
  spnl "decn" 2 1.0
  (wait 1000ms)
  outv decn
```
CC runs this, reads `decn` output, checks if it equals 2 (approach). If yes, SPNL wrote and lobe reflects it.

```
Probe 1b: Behavioural confirmation:
  targ norn soul 1 0
  spnl "decn" 8 1.0
  (wait 2000ms)
  outv posx
  (compare to pre-probe posx)
```
Decision 8 = walk_left. If creature moved left, motor faculty is reading SPNL writes. This is the definitive test: position change is unambiguous.

If creature does not move: fallback to ZOMB+ORDR is confirmed necessary.

### Unknown 2: Does `SOUL(integer)` work as rvalue in C3 Engine 1.162?

**What we know:**
- E5 failed with: `"Expected numeric rvalue at token 'soul'"` when using `setv va00 soul 1`
- CAOS reference documents `SOUL(integer)` as a valid rvalue for C3 and DS
- Hypothesis: `setv va00 soul 1` may be invalid syntax; `outv soul 1` may work

**Resolution probe:**
```
targ norn outv soul 1
```
Expected: returns `1` (brain enabled). If this works, E5 test code was simply wrong (used `setv` instead of `outv`) and SOUL read is fine. If this also errors, C3 Engine 1.162 does not support SOUL as rvalue and we use write-only (sufficient: we disable brain at startup and never need to query state mid-run).

**Impact on bridge design:** Low regardless of outcome. We only need to disable the brain once at bridge startup (`soul 1 0`). We don't need to read brain state during normal operation.

### Resolution Gate

CC will not write `nornbrain_bridge.cos` until both probes have definitive answers. The answers are written into a `phase2-bridge/probe_results.json` file that the implementation plan references.

---

## 5. GAME Variable Namespace

GAME variables are the shared data bus between the CAOS agent and the Python process. They persist in game memory as long as the game is running. Both sides can read and write them at any time: no synchronisation beyond the flag protocol below.

### Input Variables (bridge → Python)

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `nb_driv_0` .. `nb_driv_14` | float | 0.0–1.0 | 15 drive values |
| `nb_chem_0` .. `nb_chem_9` | float | 0.0–1.0 | 10 chemical concentrations |
| `nb_visn_0` .. `nb_visn_19` | float | 0.0–1.0 | 20 vision distances (0=touching, 1=absent) |
| `nb_sens_0` .. `nb_sens_7` | float | 0.0–1.0 | 8 general sense values |
| `nb_attn` | int | 0–19 | Current attention target category |
| `nb_posx` | float | 0–8000 | Creature X position (world coords) |
| `nb_posy` | float | 0–4000 | Creature Y position (world coords) |
| `nb_tick` | int | 0–∞ | Bridge tick counter (monotonically increasing) |
| `nb_input_ready` | int | 0/1 | 1 = new input written, Python should process |

### Output Variables (Python → bridge)

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `nb_out_decn` | int | 0–14 | CfC decision winner (argmax of 15 decision neurons) |
| `nb_out_attn` | int | 0–19 | CfC attention winner (argmax of 20 attention neurons) |
| `nb_out_ready` | int | 0/1 | 1 = new output written, bridge should apply |
| `nb_out_tick` | int | 0–∞ | Which nb_tick this output corresponds to |

### Control Variables

| Variable | Type | Description |
|----------|------|-------------|
| `nb_active` | int | 1 = bridge running, 0 = paused |
| `nb_brain_path` | int | 0 = SPNL path, 1 = ZOMB+ORDR path (set by Python at startup) |
| `nb_soul_off` | int | 1 = creature's brain has been disabled (set by .cos) |
| `nb_version` | int | Protocol version (currently 1): allows future upgrades |
| `nb_target` | agent | The creature being controlled (set by Python before `nb_active = 1`) |

**Note on `nb_target`:** GAME variables can hold agent references as well as numbers. Python sets this by injecting CAOS: `targ norn seta game "nb_target" targ`. The `.cos` timer script then retrieves it with `targ agnt game "nb_target"` each tick to re-establish the creature context. If the creature is deleted or dies, `agnt` returns null, which the guard check catches.

### Synchronisation Protocol

The tick counter (`nb_tick`) is the primary synchronisation signal. Python polls `nb_tick` every 20ms. When `nb_tick` increases, Python reads all input variables and processes them. There is no need for `nb_input_ready` to be the synchronisation point: the tick counter is sufficient and race-condition-free (Python only writes output variables, CAOS agent only writes input variables and reads output variables; their write domains do not overlap).

`nb_input_ready` and `nb_out_ready` are retained as secondary signals for explicitness and for probe/debug tooling. They are not relied upon for correctness.

---

## 6. Chemical ID Mapping

The following chemical IDs are used by the bridge. They are sourced from community documentation and the `verified-reference.md`. **They must be verified against the actual Steam C3 catalogue files** at `I:\SteamLibrary\steamapps\common\Creatures Docking Station\Creatures 3\Catalogue\` before the first live integration run. CC will do this verification as part of Phase 2a-fix.

| Brain Input Index | CHEM id | Chemical Name | Drive Relevance | Source |
|-------------------|---------|---------------|-----------------|--------|
| 0 | 49 | Reward | Positive reinforcement signal | biochem-wiki confirmed |
| 1 | 50 | Punishment | Negative reinforcement signal | biochem-wiki confirmed |
| 2 | 69 | Adrenaline | Fight-or-flight arousal | biochem-wiki confirmed |
| 3 | 212 | Sleepase (Pre-REM) | Sleep pressure | verified-reference (openc2e) |
| 4 | 127 | Injury | Physical damage state | verified-reference (openc2e ATP=35 correction applied) |
| 5 | 6 | Tiredness drive chemical | Fatigue | biochem-wiki drive level |
| 6 | 7 | Sleepiness drive chemical | Drowsiness | biochem-wiki drive level |
| 7 | 8 | Loneliness drive chemical | Social drive | biochem-wiki drive level |
| 8 | 10 | Fear drive chemical | Fear arousal | biochem-wiki drive level |
| 9 | 12 | Anger drive chemical | Aggression arousal | biochem-wiki drive level |

**IMPORTANT: Previous spec error corrected:** The old spec used CHEM IDs 35 and 36 for reward/punishment. These are **ATP and ADP** (energy metabolism) per `verified-reference.md` cross-reference: "ATP=35, ADP=36". Correct reward/punishment IDs are 49 and 50 per `biochem-wiki.md`. Similarly, adrenaline is 69, not 163. The IDs 148–165 referenced in the old spec appear to be DS-specific or openc2e-specific: they need catalogue verification.

**Note on drive-level chemicals (indices 5–9):** These are the drive level chemicals (IDs 1–14 in biochem-wiki correspond to drive levels 0–13). Reading CHEM 6 gives tiredness level as a chemical concentration. This overlaps with DRIV 6 but provides a slightly different signal: DRIV is the normalised drive value, CHEM is the raw chemical concentration. Both are useful; the spec uses CHEM for the chemical input slots and DRIV for the drive input slots.

**Catalogue verification method:** CC will read the Steam C3 catalogue files at `I:\SteamLibrary\steamapps\common\Creatures Docking Station\Creatures 3\Catalogue\` and cross-reference chemical IDs 49, 50, 69, 212, 127 against the catalogue definitions. Any discrepancy is flagged before integration. This is Experiment E15.

---

## 7. Drive Mapping (DRIV indices)

The 15 drive indices used by DRIV correspond to these drive names (verified from openc2e source in `verified-reference.md`):

| DRIV index | Drive name | Input vector position |
|------------|------------|----------------------|
| 0 | pain | 0 |
| 1 | hunger_for_protein | 1 |
| 2 | hunger_for_carbohydrate | 2 |
| 3 | hunger_for_fat | 3 |
| 4 | coldness | 4 |
| 5 | hotness | 5 |
| 6 | tiredness | 6 |
| 7 | sleepiness | 7 |
| 8 | loneliness | 8 |
| 9 | crowdedness | 9 |
| 10 | fear | 10 |
| 11 | boredom | 11 |
| 12 | anger | 12 |
| 13 | sex_drive | 13 |
| 14 | comfort | 14 |

These are confirmed working from E3 (all 15 drives read successfully in live C3).

---

## 8. Vision Input via SEEN

`SEEN category_id` returns the agent the creature currently has in mind for that category: the same perceptual pipeline the original brain uses. This is the correct approach: we are not trying to replicate the creature's visual system, we are tapping into it.

**Distance calculation:**
1. Get creature position: `POSX`, `POSY`
2. For each of 20 vision categories: `SETA va00 SEEN cat_id`
3. If `va00 NE NULL`: get `va00.POSX`, `va00.POSY`, compute Euclidean distance, normalise to [0, 1] using world width 8616 pixels as reference
4. If `va00 EQ NULL`: distance = 1.0 (absent/far)

**World coordinate reference:** C3 world width is 8616 pixels (confirmed from world file metadata). This is used as the normalisation denominator. A creature touching an object has distance ~0.0; an object at maximum world distance has distance ~1.0.

**The 20 vision categories** (matching `ATTENTION_LABELS` in `norn_brain.py`):

| SEEN id | Label | Notes |
|---------|-------|-------|
| 0 | food | Edible objects (vendor-dispensed food) |
| 1 | fruit | Natural food items |
| 2 | plant | Detritus plants |
| 3 | animal | Non-creature animals |
| 4 | detritus | Dead/decaying matter |
| 5 | norn | Other norns |
| 6 | grendel | Grendels |
| 7 | ettin | Ettins |
| 8 | gadget | Interactive devices |
| 9 | vehicle | Lifts, vehicles |
| 10 | hand | The player's hand |
| 11–19 | reserved | Unused in C3; distance defaults to 1.0 |

Categories 11–19 will always return NULL in C3. Their input values are clamped to 1.0 (absent). This is correct: they map to unused attention labels in `norn_brain.py` (`reserved_11` through `reserved_19`).

---

## 9. General Senses Input

8 general sense inputs feed the brain beyond drives and vision. These map to `GENERAL_SENSE_NAMES` in `norn_brain.py`:

| Index | nb_sens_N | Name | CAOS source | Phase 2b status |
|-------|-----------|------|-------------|-----------------|
| 0 | nb_sens_0 | patted | Stimulus event counter (script 14) | Implemented |
| 1 | nb_sens_1 | slapped | Stimulus event counter (script 14) | Implemented |
| 2 | nb_sens_2 | wall_bump | POSX < 50 or POSX > world_width - 50 | Implemented |
| 3 | nb_sens_3 | near_wall | POSX < 200 or POSX > world_width - 200 | Implemented |
| 4 | nb_sens_4 | in_vehicle | `CREA VEHI`: returns vehicle agent or null | Implemented |
| 5 | nb_sens_5 | creature_nearby | SEEN 5, 6, 7 distance < 0.035 (300px / 8616) | Implemented |
| 6 | nb_sens_6 | opposite_sex_nearby | Requires SEX rvalue + SEEN 5 scan | **Deferred to Phase 2c: always 0.0** |
| 7 | nb_sens_7 | sibling_nearby | Requires moniker comparison across creatures | **Deferred to Phase 2c: always 0.0** |

**Implementation notes:**

*Patted/slapped (indices 0–1):* Cannot be read as rvalues in CAOS. The `.cos` agent must handle creature stimulus event scripts. Script number for stimulus receipt needs verification against the C3 script table. The bridge will install additional script handlers on the target creature at activation time. Python decays these counters by multiplying by 0.9 each brain tick (exponential decay, half-life ~2 ticks).

*Wall proximity (indices 2–3):* Computed from POSX relative to world width 8616. The distance thresholds (50px wall_bump, 200px near_wall) match the Phase 1 `Arena` implementation.

*In vehicle (index 4):* `CREA VEHI` returns the vehicle the creature is in, or null. Convert to 1.0/0.0.

*Creature nearby (index 5):* Check if SEEN 5 (norn), SEEN 6 (grendel), or SEEN 7 (ettin) returns non-null and distance < 0.035 (≈300px in 8616-wide world).

*Opposite-sex and sibling (indices 6–7):* These require cross-creature queries that add significant CAOS complexity. Deferred to Phase 2c. Defaulting to 0.0 is safe: the brain will operate without these signals initially.

---

## 10. CAOS Agent Design (`nornbrain_bridge.cos`)

### Agent Classification
- Family: 1 (SimpleObject)
- Genus: 1
- Species: 200 (user-reserved range, avoids conflicts)

### Bootstrap Script

Installed as `Bootstrap/010 Docking Station/nornbrain_bridge.cos` in the C3 game directory. On world load, this:
1. Removes any existing bridge agent (allows hot-reload)
2. Creates a new invisible agent with a 4-tick timer
3. Initialises all GAME variables to safe defaults
4. Sets `nb_version` = 1
5. Does NOT activate immediately: activation happens when Python sets `nb_active = 1`

```caos
* NornBrain Bridge Agent -- bootstrap
* NORNBRAIN Phase 2 / 2026-03-29

* Remove old bridge if present (allows hot-reload)
enum 1 1 200
    kill targ
next

* Create bridge agent: invisible, persistent, timer-driven
new: simp 1 1 200 "blnk" 1 0 0
attr 198
tick 4

* Initialise all GAME variables to safe defaults
setv game "nb_version"      1
setv game "nb_active"       0
setv game "nb_brain_path"   0
setv game "nb_soul_off"     0
setv game "nb_tick"         0
setv game "nb_input_ready"  0
setv game "nb_out_ready"    0
setv game "nb_out_decn"     0
setv game "nb_out_attn"     0
setv game "nb_out_tick"     0
setv game "nb_attn"         0
setv game "nb_posx"         0
setv game "nb_posy"         0

* Input vars: drives, chemicals, vision, senses all initialise to 0
* The timer script overwrites them on the first active tick
* Python reads 0 for all inputs until the first bridge tick fires
* nb_target is set to null initially; Python sets it before activating
```

### Timer Script (scrp 1 1 200 9: fires every 4 ticks)

The timer script is the heart of the bridge. It runs synchronously inside the engine tick loop. Each execution:

**Phase A: Guard checks:**
- If `nb_active` ≠ 1: stop (bridge not yet activated by Python)
- Target the creature stored in `nb_target`
- If creature is null or dead: set `nb_active = 0`, stop (creature gone)

**Phase B: Disable brain on first tick:**
- If `nb_soul_off` = 0: execute `soul 1 0`, set `nb_soul_off = 1`
- This only runs once per activation: brain stays disabled until Python disconnects

**Phase C: Read creature state:**
- 15 drives via `DRIV 0` .. `DRIV 14` → `nb_driv_0` .. `nb_driv_14`
- 10 chemicals via `CHEM id` → `nb_chem_0` .. `nb_chem_9`
- Position via `POSX`, `POSY` → `nb_posx`, `nb_posy`
- Attention via `ATTN` → `nb_attn`
- 20 vision distances via SEEN + distance maths → `nb_visn_0` .. `nb_visn_19`
- 6 general senses via direct queries → `nb_sens_0` .. `nb_sens_5`
- 2 general senses (sibling, opposite_sex) → `nb_sens_6` = 0.0, `nb_sens_7` = 0.0 (deferred)
- Increment `nb_tick`
- Set `nb_input_ready` = 1

**Phase D: Apply previous CfC output:**
- If `nb_out_ready` = 1:
  - Read `nb_out_decn`, `nb_out_attn`
  - If `nb_brain_path` = 0 (SPNL path): `spnl "decn" nb_out_decn 1.0` / `spnl "attn" nb_out_attn 1.0`
  - If `nb_brain_path` = 1 (ZOMB path): decode nb_out_decn to ORDR string, execute `ordr writ creature string`
  - Set `nb_out_ready` = 0

### ORDR Fallback Lookup Table (only used if SPNL path fails)

Decision index to ORDR command string:

| Index | Decision | ORDR WRIT string | Notes |
|-------|----------|-----------------|-------|
| 0 | push | "push" | Creature pushes attended object |
| 1 | pull | "pull" | Creature pulls attended object |
| 2 | approach | "come" | Creature moves toward attended object |
| 3 | retreat | "run" | Creature moves away from attended object |
| 4 | get | "get" | Creature picks up attended object |
| 5 | drop | "drop" | Creature drops held object |
| 6 | speak | "what" | Nearest equivalent; creature vocalises |
| 7 | sleep | "rest" | Creature lies down to sleep |
| 8 | walk_left | "left" | Creature walks left |
| 9 | walk_right | "right" | Creature walks right |
| 10 | go_up | "up" | Creature moves upward (lifts etc.) |
| 11 | go_down | "down" | Creature moves downward |
| 12 | stop | "stop" | Creature stops current action |
| 13 | express | "look" | Nearest equivalent; creature looks around |
| 14 | wait | "stop" | Same as stop |

**ORDR WRIT syntax:** `ordr writ <creature_agent> "string"` where the first argument is the creature as an agent reference (not just TARG context). The `.cos` timer script stores the target creature reference in `va99` at the start of each tick so it can be passed as the `ordr writ` first argument.

**Vocabulary verification:** These word strings must match the vocabulary installed in the target norn's genome. Standard C3 norns understand the words above. If using a non-standard genome (e.g. Creatures Village cross), vocabulary may differ. CC will verify via `VOIS` and blackboard queries in Experiment E18.

**ZOMB path limitation:** ORDR WRIT maps 15 CfC decisions to 13 distinct commands (speak→what, express→look, wait→stop share words). This coarsening is acceptable for Phase 2b: the creature will still exhibit the full range of meaningful behaviours.

---

## 11. Python Bridge Client Design (`brain_bridge_client.py`)

### Module Relationships

```
brain_bridge_client.py
  ├── imports C2eConnection from phase2-bridge/c2e_bridge.py
  ├── imports NornBrain, BrainInput, BrainOutput from phase1-prototype/norn_brain.py
  └── serves phase1-prototype/dashboard.html on :8100
```

`sys.path` manipulation or a `pyproject.toml` install is needed to import across the `phase1-prototype/` boundary. The cleanest approach: add `phase1-prototype/` to `sys.path` at the top of `brain_bridge_client.py`. This is a dev-environment script, not a package: the pragmatic approach is correct here.

### Class Structure

```python
class BrainBridgeClient:
    """
    Connects to C3 via CAOS shared memory, runs CfC brain, writes decisions back.
    Also serves the Phase 1 dashboard fed with live game data.
    """
    conn: C2eConnection       # shared memory connection
    brain: NornBrain          # CfC/NCP brain instance
    probe_results: dict       # loaded from probe_results.json
    brain_path: int           # 0 = SPNL, 1 = ZOMB+ORDR
    last_tick: int            # last nb_tick value seen
    ws_clients: set           # connected WebSocket clients
```

### Startup Sequence

1. Parse args: `--game "Creatures 3"`, `--creature 0`, `--probe`, `--port 8100`
2. Connect to game via `C2eConnection`
3. If `--probe` or no `probe_results.json`: run probe suite (see Section 12)
4. Load `probe_results.json`, set `brain_path`
5. Find target creature (TOTL + NORN selection)
6. Write `nb_active = 0` (ensure bridge starts clean)
7. Inject `nb_brain_path` = selected path
8. Inject creature reference via CAOS (`nb_target`)
9. Activate bridge: `nb_active = 1`
10. Start async tasks: poll loop + WebSocket server

### Poll Loop

```python
async def poll_loop(self):
    while self.running:
        tick = self.conn.execute_int('outv game "nb_tick"')
        if tick > self.last_tick:
            state = self.read_game_state()      # single batched CAOS read
            brain_input = self.build_brain_input(state)
            output = self.brain.tick(brain_input)
            self.write_decision(output, tick)   # write nb_out_decn, nb_out_attn, nb_out_ready
            await self.broadcast_state(brain_input, output, state)
            self.last_tick = tick
        await asyncio.sleep(0.020)              # 20ms poll
```

### Batched Read (single CAOS injection, ~90 values)

The read is issued as one `execute()` call. All values are space-separated in the response. One mutex acquisition, one shared memory round-trip, one parse.

```caos
targ norn
outv driv 0 outs " " outv driv 1 outs " " ... outv driv 14 outs " "
outv chem 35 outs " " outv chem 36 outs " " ... (10 chemicals)
outv posx outs " " outv posy outs " "
outv attn outs " "
seta va00 seen 0 doif va00 ne null targ va00 outv subv posx game "nb_posx" else outv 9999.0 endi targ norn outs " "
... (20 vision categories)
```

Vision distance calculation happens inside the CAOS script to avoid extra round-trips. The result is a normalised float (0.0–1.0) written directly to the output string. Python parses the flat space-separated float list.

### Graceful Shutdown

On `SIGINT` / `SIGTERM` / `KeyboardInterrupt`:
1. Set `nb_active = 0`
2. Re-enable brain: `targ norn soul 1 1` (SPNL path) or `targ norn zomb 0` (ZOMB path)
3. Clear `nb_soul_off = 0`
4. Close WebSocket connections
5. Call `conn.disconnect()`

The creature must never be left with its brain disabled when the Python process exits. This is both a correctness requirement (creature would be frozen) and a usability requirement (the game must remain playable after the bridge stops).

### Dashboard Integration

`brain_bridge_client.py` serves the same `dashboard.html` as Phase 1. The WebSocket message format is identical to `server.py`'s `build_state_message()` output, with one addition:

```json
{
  "type": "tick",
  "source": "live_c3",         // NEW: "live_c3" vs "simulation"
  "game_tick": 4821,           // NEW: raw nb_tick from game
  "brain_path": "spnl",        // NEW: "spnl" or "zomb_ordr"
  ... (all existing fields unchanged)
}
```

`dashboard.html` does not need to be modified for Phase 2: it will work as-is and simply show live data. A "Connected to C3" status indicator is deferred to Phase 2c polish.

---

## 12. Probe Mode (`experiments.py`)

### Purpose

`experiments.py` is the authoritative experiment harness for the entire Phase 2 workflow. It:
- Resolves pre-build unknowns (Unknowns 1 and 2 from Section 4)
- Provides the `--probe` subset used by `brain_bridge_client.py` at startup
- Replaces `validate_experiments.py` (which is deleted: it used the obsolete TCP relay)

### Probe Suite (subset run at bridge startup)

| ID | Test | Gate |
|----|------|------|
| P0 | Connection + game name | Must pass |
| P1 | Creature present | Must pass |
| P2 | GAME var round-trip | Must pass |
| P3 | DRIV read (all 15) | Must pass |
| P4 | CHEM read (10 key) | Must pass |
| P5 | SOUL disable + restore | Determines brain_path |
| P6 | SPNL write + behavioural confirmation | Determines brain_path |
| P7 | Timing (batch read) | Warn if >20ms avg |

P5 and P6 together determine `brain_path`. If P5 fails (SOUL write fails), that is a hard blocker: stop and report. If P6 fails (SPNL accepted but creature doesn't move), `brain_path = 1` (ZOMB+ORDR). If P6 passes, `brain_path = 0` (SPNL).

### Full Experiment Suite

Extends the existing E0–E12 suite with new experiments:

| ID | Experiment | Purpose |
|----|------------|---------|
| E0–E12 | (existing) | Already validated on live C3 (11/13 pass) |
| E13 | SOUL rvalue probe (`targ norn outv soul 1`) | Resolve Unknown 2 |
| E14 | SPNL behavioural test (walk_left + position delta) | Resolve Unknown 1 |
| E15 | Chemical ID verification (compare CHEM reads to catalogue) | Verify chem IDs |
| E16 | Vision distance calibration (place food at known location, read SEEN distance) | Verify normalisation |
| E17 | Stimulus event detection (pat creature, read nb_sens_0 update) | Verify patted/slapped sense |
| E18 | ORDR WRIT test (send walk_left command, verify position delta) | Verify ZOMB fallback |
| E19 | Full bridge cycle test (write all GAME vars, read back, check round-trip fidelity) | Integration smoke test |

### Output Format

`results.json` is extended with per-experiment structured data:

```json
{
  "timestamp": "2026-03-29T...",
  "game": "Creatures 3",
  "pid": 36760,
  "passed": 17,
  "total": 19,
  "brain_path_recommendation": "spnl",
  "probe_results": {
    "P5_soul_disable": {"passed": true, "detail": "..."},
    "P6_spnl_behavioural": {"passed": true, "detail": "creature moved 47px left"}
  },
  "tests": [...]
}
```

`probe_results.json` is a separate file written only by the probe suite, read by `brain_bridge_client.py` at startup.

---

## 13. File Inventory

### Files Created

```
phase2-bridge/
├── experiments.py              NEW: full experiment + probe harness
├── brain_bridge_client.py      NEW: Python bridge client (poll loop + dashboard)
├── nornbrain_bridge.cos        NEW: CAOS agent (installed into game Bootstrap)
└── probe_results.json          NEW: written by experiments.py, read by bridge client
```

### Files Modified

```
phase2-bridge/
└── c2e_bridge.py               MODIFIED: C2eConnection stays, test runner stays,
                                 but module-level exports are cleaned up so
                                 `from c2e_bridge import C2eConnection` works cleanly

CLAUDE.md                       UPDATED: reflects:
                                 - Target is Steam C3 (Engine 1.162), NOT openc2e
                                 - Project location is <PROJECT_ROOT> (Windows native)
                                 - Windows Python required (not WSL2)
                                 - Correct phase roadmap
                                 - CC is fully autonomous (can run scripts, probe game)
                                 - Key file locations updated
```

### Files Deleted

```
phase2-bridge/
└── validate_experiments.py     DELETED: dead code (WSL2 TCP relay approach,
                                 superseded by experiments.py + c2e_bridge.py)
```

### Files Unchanged

```
phase1-prototype/
├── norn_brain.py               UNCHANGED: CfC/NCP brain, 89 inputs, 100 neurons
├── server.py                   UNCHANGED: Phase 1 standalone server
├── scenarios.py                UNCHANGED: offline training scenarios
├── dashboard.html              UNCHANGED: works with live data as-is
├── caos_client.py              UNCHANGED: openc2e TCP client (Phase 1 only)
└── requirements.txt            UNCHANGED

phase2-bridge/
├── run_tests.bat               UNCHANGED
└── results.json                UNCHANGED (overwritten by next test run)

docs/
└── verified-reference.md       UNCHANGED: authoritative reference
```

---

## 14. Risks and Mitigations

| Risk | Severity | Status | Mitigation |
|------|----------|--------|------------|
| SPNL doesn't drive behaviour with brain off | **HIGH** | Unknown: E14 will resolve | ZOMB+ORDR fallback designed and ready |
| SOUL rvalue not supported in C3 Engine 1.162 | **LOW** | Unknown: E13 will resolve | Write-only SOUL is sufficient; rvalue not needed |
| Chemical IDs wrong in Steam C3 release | **MEDIUM** | Unverified: E15 will resolve | Cross-reference against catalogue files |
| SEEN returns NULL for all categories | **MEDIUM** | E8 confirmed SEEN works | Defaulting to 1.0 (absent) is safe |
| `nb_target` agent reference invalidated mid-run | **LOW** | Mitigated by design | Timer script checks null each tick; deactivates cleanly |
| Game process crashes during bridge run | **LOW** | Mitigated by design | Reconnection loop in client; GAME vars persist across soft restart |
| Multiple norns confuse creature selection | **LOW** | Mitigated by design | `--creature N` arg; defaults to first norn |
| torch/ncps not installed | **LOW** | Known issue | `pip install -r requirements.txt` before running |
| Vision distance normalisation wrong | **MEDIUM** | Unverified: E16 will calibrate | Worst case: distances are wrong scale but relative ranking is preserved |

---

## 15. Revised Project Roadmap

```
Phase 1:  Python prototype (Brain in a Vat)                     ✓ DONE
Phase 2a: CAOS validation on Steam C3 (E0–E12)                  ✓ 11/13 DONE
Phase 2a-fix: Resolve unknowns (E13–E19), fix E5/E11 tests      ← NEXT
Phase 2b: Bridge implementation (.cos agent + Python client)    ← After 2a-fix
Phase 2c: Live integration testing (creature on CfC in C3)      ← After 2b
Phase 2d: Scale to 975 neurons + 243 inputs                     DEFERRED
Phase 3:  Genome-driven architecture (CfC wiring from genetics)  FUTURE
Phase 4:  Language and social behaviour                          FUTURE
```

---

## 16. Reference Documents

- `docs/verified-reference.md`: 3,666-line cross-verified reference (brain architecture, biochemistry, CAOS interface)
- `docs/superpowers/specs/2026-03-28-phase1-brain-in-a-vat-design.md`: Phase 1 spec
- `.firecrawl/caoschaos-docs.md`: 27,950-line CAOS command reference (authoritative)
- `phase2-bridge/c2e_bridge.py`: Win32 shared memory client (working, tested)
- `phase2-bridge/results.json`: Last validation run results (11/13 pass, E5/E11 fail)
- `phase1-prototype/norn_brain.py`: The CfC/NCP brain class
- `I:\SteamLibrary\steamapps\common\Creatures Docking Station\Creatures 3\`: Game install
- `I:\SteamLibrary\steamapps\common\Creatures Docking Station\Creatures 3\Catalogue\`: Catalogue files (chemical IDs)
