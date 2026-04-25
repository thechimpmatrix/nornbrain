# The SVRule Brain: Complete Technical Reference

**Project:** NORNBRAIN: Creatures 3 Brain Architecture Study
**Purpose:** Authoritative reference for the Creatures 3 SVRule brain implementation
**Sources:** openc2e C++ source code, Creatures Wiki, CDR (Chris Double), game genome files, firecrawl research archive
**Primary verifier (added 2026-04-26):** 1999 Cyberlife C3 source code at `<PROJECT_ROOT>/C3sourcecode/engine/` (Internet Archive: `creatures-3-1999-cyberlife-source-code.-7z`). Where openc2e and C3 1999 source disagree, the C3 source is canonical. Inline citations of the form `(C3 source: <file>:<line>)` indicate facts cross-checked against the original.
**Date:** 2026-04-03 (corrections applied 2026-04-26)

---

## Table of Contents

1. [Overview & Design Philosophy](#1-overview--design-philosophy)
2. [Architecture: Lobes and Tracts](#2-architecture-lobes-and-tracts)
3. [The Neuron](#3-the-neuron)
4. [The Dendrite](#4-the-dendrite)
5. [The SVRule Register Machine](#5-the-svrule-register-machine)
6. [Complete C3/DS SVRule Opcode Reference](#6-complete-c3ds-svrule-opcode-reference)
7. [Complete Operand Type Reference](#7-complete-operand-type-reference)
8. [Lobe Specifications](#8-lobe-specifications)
9. [The Tract System](#9-the-tract-system)
10. [Weight Dynamics: STW/LTW Bidirectional Learning](#10-weight-dynamics-stwltw-bidirectional-learning)
11. [Winner-Takes-All: The Spare Neuron Mechanism](#11-winner-takes-all-the-spare-neuron-mechanism)
12. [Instinct Gene System](#12-instinct-gene-system)
13. [Brain Tick Algorithm](#13-brain-tick-algorithm)
14. [Dendrite Migration](#14-dendrite-migration)
15. [Chemical Integration](#15-chemical-integration)
16. [The Decision Pipeline: From Inputs to Action](#16-the-decision-pipeline-from-inputs-to-action)
17. [C1/C2 vs C3/DS Differences](#17-c1c2-vs-c3ds-differences)
18. [Unimplemented Features in openc2e](#18-unimplemented-features-in-openc2e)
19. [Appendix A: C1 Lobe Map](#appendix-a-c1-lobe-map)
20. [Appendix B: C1/C2 SVRule Opcodes](#appendix-b-c1c2-svrule-opcodes)
21. [Appendix C: Source File Index](#appendix-c-source-file-index)

---

## 1. Overview & Design Philosophy

The SVRule brain is the neural network system used in the Creatures game series (Creatures 1 through Creatures 3 / Docking Station). It was designed by Steve Grand and the Cyberlife team with several key constraints:

1. **Efficiency for mid-1990s hardware**: had to run on consumer PCs of the era
2. **Engineered first-generation brains**: developers needed to hand-craft viable starting brains
3. **Mutation-robustness**: any random mutation to the genome should produce a legal (if possibly non-functional) brain. Every possible SVRule program is syntactically valid.
4. **Evolvability**: mutations should have a decent chance of producing equal or better brains in later generations

The name "SVRule" stands for **State Value Rule**: a small program that operates on state values stored in neurons and dendrites.

### Key Design Insight

From the original programmer (Digitalgod): SVRules were designed so that **every possible statement is legal and meaningful**, even if not biologically useful. If a mutation changes a command to one that doesn't need operands, the operand byte is simply reinterpreted as a new command or variable. This biology-inspired robustness is what makes the brain evolvable through random genetic mutation.

---

## 2. Architecture: Lobes and Tracts

The SVRule brain is organised into **lobes** (groups of neurons) connected by **tracts** (bundles of dendrites).

### Lobes

A lobe is a brain region dedicated to a specific function. Each lobe is defined by a genome gene containing:

- A **4-character ID** (e.g., "driv", "verb", "attn", "decn")
- **X, Y position** (uint16 each): screen display coordinates
- **Width × height** (uint8 each): defines the neuron grid (total neurons = width × height; engine cap is `MAX_NEURONS_PER_LOBE = 255*255 = 65,025` per C3 source: `Creature/Brain/BrainConstants.h:10`. The project's previous "max 1024" figure was incorrect; corrected 2026-04-26)
- **RGB colour** (3 × uint8): display colour for brain visualisation
- **Update time**: how often the lobe ticks (0 = never). Note: stored as uint16 in the genome but **truncated to uint8 at runtime** in openc2e, so values > 255 are lost.
- **Tissue ID**: for chemical receptor/emitter mapping
- **WTA flag**: Winner-Takes-All (unused in C3 final game; see Section 11)
- **Initialiser SVRule** (48 bytes): runs once at creation, optionally every tick
- **Update SVRule** (48 bytes): runs every tick on every neuron
- **initrulealways flag**: if set, the initialiser rule runs every tick before the update rule
- **spare[7]**: 7 reserved bytes

### Tracts (C3/DS)

A tract is a bundle of dendrites connecting neurons in a source lobe to neurons in a destination lobe. Tracts replaced the simpler two-dendrite-type system from C1/C2. Each tract is defined by:

- **Source and destination lobe IDs** (4-char each)
- **Neuron bounds**: four separate uint16 fields: `srclobe_lowerbound`, `srclobe_upperbound`, `destlobe_lowerbound`, `destlobe_upperbound`
- **Connection counts**: two separate uint16 fields: `src_noconnections` and `dest_noconnections`
- **Migration flag**: whether dendrites can dynamically rewire
- **Update time**: tick frequency
- **Initialiser SVRule** (48 bytes): runs on each dendrite at creation
- **Update SVRule** (48 bytes): runs on each dendrite every tick
- **srcvar / destvar**: which neuron variable indices to use for migration decisions (tracking which neurons are most active; sometimes called "nerve growth factor" by analogy with real neuroscience, though this is not an in-game term)
- **spare[5]**: 5 reserved bytes

---

## 3. The Neuron

### C3/DS Neuron Structure

```
struct c2eNeuron {
    float variables[8];   // 8 general-purpose state variables
    float input;          // Input accumulator (cleared each tick)
};
```

Source: `openc2e/src/openc2e/creatures/c2eBrain.h:74-77`

### The 8 State Variables

Each neuron has 8 float state variables (`variables[0]` through `variables[7]`). The C3 1999 source explicitly names these indices in `Creature/Brain/SVRule.h:19-28` (`enum NeuronVariableNames`). Behavioural meaning still depends on the SVRules in each lobe's genome, but the canonical C3-engine names are:

| Index | C3 Source Name | Notes |
|-------|----------------|-------|
| 0 | `STATE_VAR` | Neuron's primary state; read by tracts as `source->variables[0]`; the accumulator initialises to this for tract SVRules |
| 1 | `INPUT_VAR` | Input accumulator slot; opcodes 50/51 write to `neuron[INPUT_VAR]`; cleared each tick |
| 2 | `OUTPUT_VAR` | Output value (canonical) |
| 3 | `THIRD_VAR` | General-purpose; lobe-specific by SVRule |
| 4 | `FOURTH_VAR` | Used by opcodes 63/64 (`preserveVariable`/`restoreVariable`) as the save slot |
| 5 | `FIFTH_VAR` | General-purpose |
| 6 | `SIXTH_VAR` | General-purpose |
| 7 | `NGF_VAR` | "Neural Growth Factor": controls dendrite migration (C3 source comment, SVRule.h:27) |

### The Input Accumulator

The `input` field accumulates signals from all dendrites targeting this neuron during the current tick. When the lobe ticks, each neuron's SVRule receives `input` as its initial accumulator value. After the SVRule runs, `input` is reset to 0.0.

### C1/C2 Neuron (for comparison)

```
struct oldNeuron {
    uint8_t state;       // Current state (0-255)
    uint8_t output;      // Current output (0-255)
    uint8_t leakage_state; // Memorised state for leakage calc
    uint8_t x, y;        // Display position
    uint8_t is_percept;  // True if receiving perception input
};
```

C1/C2 neurons used 8-bit integer values (0-255). C3/DS upgraded to 32-bit floats.

---

## 4. The Dendrite

### C3/DS Dendrite Structure

```
struct c2eDendrite {
    float variables[8];       // 8 general-purpose state variables
    c2eNeuron *source;        // Pointer to source neuron
    c2eNeuron *dest;          // Pointer to destination neuron
};
```

Source: `openc2e/src/openc2e/creatures/c2eBrain.h:79-82`

### The 8 Dendrite Variables

C3 1999 source names these in `Creature/Brain/SVRule.h:30-39` (`enum DendriteVariableNames`):

| Index | C3 Source Name | Notes |
|-------|----------------|-------|
| 0 | `WEIGHT_SHORTTERM_VAR` | Short-Term Weight (STW); used by opcode 44 |
| 1 | `WEIGHT_LONGTERM_VAR` | Long-Term Weight (LTW); STW relaxes toward this |
| 2 | `SECOND_DENDRITE_VAR` | Tract-specific |
| 3 | `THIRD_DENDRITE_VAR` | Tract-specific |
| 4 | `FOURTH_DENDRITE_VAR` | Tract-specific |
| 5 | `FIFTH_DENDRITE_VAR` | Tract-specific |
| 6 | `SIXTH_DENDRITE_VAR` | Tract-specific |
| 7 | `STRENGTH_VAR` | "Determines how 'permanent' the dendrite is (i.e. unwilling to migrate)" (C3 source comment, SVRule.h:38). If 0.0, dendrite is loose and eligible for migration. |

### SVRule Context for Dendrites

When a tract's SVRule runs on a dendrite, the parameters are mapped as:

| SVRule Parameter | Maps To |
|------------------|---------|
| `acc` (accumulator) | `dendrite.source->variables[0]` (source neuron's primary output) |
| `srcneuron[0..7]` | `dendrite.source->variables[0..7]` (all source neuron state) |
| `neuron[0..7]` | `dendrite.dest->variables[0..7]` (all destination neuron state) |
| `spareneuron[0..7]` | `dummyValues` (not used for tracts) |
| `dendrite[0..7]` | `dendrite.variables[0..7]` (the dendrite's own state) |

### C1/C2 Dendrite (for comparison)

```
struct oldDendrite {
    uint8_t source;          // Source neuron index
    uint8_t stw;             // Short-term weight (0-255)
    uint8_t ltw;             // Long-term weight (0-255)
    uint8_t strength;        // Connection strength (0-255)
    uint8_t stw_leakage;     // STW leakage state
    uint8_t susceptibility;  // To reinforcement (0-255)
};
```

C1/C2 dendrites had fixed, named fields. C3/DS generalised to 8 float variables.

---

## 5. The SVRule Register Machine

### Overview

In C3/DS, each neuron and each dendrite is a fully functional **register machine**. The machine has:

- An **accumulator**: the working register (float)
- Access to **neuron variables** (the current neuron's 8 floats)
- Access to **source neuron variables** (for dendrite SVRules)
- Access to **spare neuron variables** (for lobe SVRules)
- Access to **dendrite variables** (for dendrite SVRules)
- Access to **creature chemicals** (read-only via operand type 7)
- A **tend rate** register (for interpolation operations)
- A static **STW relaxation rate** register (persists across calls: see Section 10)

### Program Format

Each SVRule program is **48 bytes** encoding **16 instructions**. Each instruction is 3 bytes:

```
Byte 0: Opcode      (0-68)
Byte 1: Operand type (0-15)
Byte 2: Operand data (0-255)
```

### Execution Model

1. The accumulator is initialised with a starting value (neuron input for lobes, source neuron output for tracts)
2. Instructions execute sequentially (0 through 15)
3. Conditional opcodes (4-15) set a `skip_next` flag that skips the following instruction
4. Goto opcodes (48-49, 52, 67-68) can jump forward (never backward)
5. Stop opcodes (0, 46-47, 53-56) terminate execution early
6. The function returns a boolean: `true` if opcode 31 ("register as spare") was executed

### Value Binding

Most store operations clamp values to [-1.0, 1.0] via `bindFloatValue()`:

```cpp
float bindFloatValue(float v, float base = -1.0f) {
    return std::clamp(v, base, 1.0f);
}
```

When `base = 0.0f` (opcode 32), values are clamped to [0.0, 1.0].

---

## 6. Complete C3/DS SVRule Opcode Reference

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:604-967`

### Flow Control

| Op | Name | Description |
|----|------|-------------|
| 0 | **stop** | Terminate SVRule execution |
| 30 | **no operation** | Do nothing |
| 46 | **stop if zero** | If operand == 0, stop |
| 47 | **stop if non-zero** | If operand != 0, stop |
| 48 | **if zero goto** | If accumulator == 0, jump forward to line (operand) |
| 49 | **if non-zero goto** | If accumulator != 0, jump forward to line (operand) |
| 52 | **goto line** | Unconditional forward jump to line (operand) |
| 53 | **stop if <** | If accumulator < operand, stop |
| 54 | **stop if >** | If accumulator > operand, stop |
| 55 | **stop if <=** | If accumulator <= operand, stop |
| 56 | **stop if >=** | If accumulator >= operand, stop |
| 67 | **if negative goto** | If accumulator < 0, jump forward |
| 68 | **if positive goto** | If accumulator > 0, jump forward |

### Conditionals (skip next instruction if condition is FALSE)

| Op | Name | Condition |
|----|------|-----------|
| 4 | **if =** | accumulator == operand |
| 5 | **if <>** | accumulator != operand |
| 6 | **if >** | accumulator > operand |
| 7 | **if <** | accumulator < operand |
| 8 | **if >=** | accumulator >= operand |
| 9 | **if <=** | accumulator <= operand |
| 10 | **if zero** | operand == 0 |
| 11 | **if non-zero** | operand != 0 |
| 12 | **if positive** | operand > 0 |
| 13 | **if negative** | operand < 0 |
| 14 | **if non-positive** | operand <= 0 (note: openc2e comment says "should be non-negative?") |
| 15 | **if non-negative** | operand >= 0 (note: openc2e comment says "should be non-positive?") |

### Load / Store

| Op | Name | Description |
|----|------|-------------|
| 1 | **blank** | Set operand destination to 0.0 |
| 2 | **store in** | `*operand = clamp(accumulator, -1, 1)` |
| 3 | **load from** | `accumulator = operand` |
| 26 | **load negation of** | `accumulator = -operand` |
| 27 | **load abs of** | `accumulator = |operand|` |
| 45 | **store abs in** | `*operand = |accumulator|` |

### Arithmetic

| Op | Name | Description |
|----|------|-------------|
| 16 | **add** | `accumulator += operand` |
| 17 | **subtract** | `accumulator -= operand` |
| 18 | **subtract from** | `accumulator = operand - accumulator` |
| 19 | **multiply by** | `accumulator *= operand` |
| 20 | **divide by** | `accumulator /= operand` (safe: no-op if operand == 0) |
| 21 | **divide into** | `accumulator = operand / accumulator` (safe: no-op if acc == 0) |
| 22 | **minimum with** | `accumulator = min(accumulator, operand)` |
| 23 | **maximum with** | `accumulator = max(accumulator, operand)` |
| 28 | **distance to** | `accumulator = |accumulator - operand|` |
| 29 | **flip around** | `accumulator = operand - accumulator` |

### Interpolation (Tend-To)

| Op | Name | Description |
|----|------|-------------|
| 24 | **set tend rate** | `tend_rate = operand` (0.0 to 1.0) |
| 25 | **tend to** | `accumulator += tend_rate * (operand - accumulator)` |
| 34 | **add and store in** | `*operand = clamp(accumulator + operand)` |
| 35 | **tend to and store in** | `*operand = clamp(accumulator + tend_rate * (operand - accumulator))` |

### Threshold and Bounding

| Op | Name | Description |
|----|------|-------------|
| 32 | **bound in [0,1]** | `accumulator = clamp(operand, 0.0, 1.0)` |
| 33 | **bound in [-1,1]** | `accumulator = clamp(operand, -1.0, 1.0)` |
| 36 | **nominal threshold** | `if (accumulator < operand) accumulator = 0.0` |

### Neuron Input Injection

| Op | Name | Description |
|----|------|-------------|
| 50 | **divide by, add to neuron input** | `if (operand != 0) neuron[1] += clamp(accumulator / operand)`: no-op on divide by zero |
| 51 | **multiply by, add to neuron input** | `neuron[1] += clamp(accumulator * operand)` |

These opcodes directly inject computed values into the destination neuron's variable[1], bypassing the normal input accumulator. This is how dendrite SVRules deliver weighted signals to destination neurons. Note: the `clamp` (bindFloatValue) applies to the operation result before addition, but does NOT clamp the final `neuron[1]` value: so repeated additions can push `neuron[1]` beyond [-1.0, 1.0].

### Special: Spare Neuron (WTA)

| Op | Name | Description |
|----|------|-------------|
| 31 | **register as spare** | Mark current neuron as spare. The calling lobe updates its spare index. |

### Learning: STW/LTW Relaxation

| Op | Name | Description |
|----|------|-------------|
| 43 | **short-term relax rate** | `stw_rate = operand`: **WARNING: static variable, persists across ALL SVRule calls** |
| 44 | **long-term relax rate** | Bidirectional relaxation (see Section 10 for full formula) |

### State Variable Preservation

| Op | Name | Description |
|----|------|-------------|
| 63 | **preserve neuron SV** | `neuron[4] = neuron[(int)operand]` |
| 64 | **restore neuron SV** | `neuron[(int)operand] = neuron[4]` |
| 65 | **preserve spare neuron** | `spareneuron[4] = spareneuron[(int)operand]` |
| 66 | **restore spare neuron** | `spareneuron[(int)operand] = spareneuron[4]` |

### Opcodes implemented in stock C3 but TODO in openc2e

**Important correction (2026-04-26):** all opcodes in this table ARE implemented in the 1999 Cyberlife C3 source (verified in `Creature/Brain/SVRule.h:621-652`). The "TODO" label refers to openc2e's port status, not the stock engine. NORNBRAIN running openc2e will encounter these as no-ops; running on stock C3 they execute the listed semantics.

| Op | C3 Source Name | Description (verified in SVRule.h `ProcessGivenVariables`) |
|----|----------------|--------------------------------------------------------|
| 36 | `doNominalThreshold` | `if (neuron[INPUT_VAR] < operand) neuron[INPUT_VAR] = 0.0` (SVRule.h:621-624) |
| 37 | `doLeakageRate` | `tendRate = operand` (SVRule.h:625-627) |
| 38 | `doRestState` | `neuron[INPUT_VAR] = neuron[INPUT_VAR]*(1-tendRate) + operand*tendRate` (SVRule.h:628-632) |
| 39 | `doInputGainLoHi` | `neuron[INPUT_VAR] *= operand` (SVRule.h:633-635) |
| 40 | `doPersistence` | `neuron[STATE_VAR] = neuron[INPUT_VAR]*(1-operand) + neuron[STATE_VAR]*operand` (SVRule.h:637-641) |
| 41 | `doSignalNoise` | `neuron[STATE_VAR] += operand * RndFloat()` (SVRule.h:642-645) |
| 42 | `doWinnerTakesAll` | If `neuron[STATE_VAR] >= spareNeuron[STATE_VAR]`: `spareNeuron[OUTPUT_VAR]=0; neuron[OUTPUT_VAR]=neuron[STATE_VAR]; returnCode=setSpareNeuronToCurrent` (SVRule.h:236-243) |
| 57 | `setRewardThreshold` | Calls `HandleSetRewardThreshold(myOwner, operand)` on the owning BrainComponent (SVRule.h:508-510) |
| 58 | `setRewardRate` | `HandleSetRewardRate(...)` (SVRule.h:511-513) |
| 59 | `setRewardChemicalIndex` | `HandleSetRewardChemicalIndex(...)` (SVRule.h:514-516) |
| 60 | `setPunishmentThreshold` | `HandleSetPunishmentThreshold(...)` (SVRule.h:517-519) |
| 61 | `setPunishmentRate` | `HandleSetPunishmentRate(...)` (SVRule.h:520-522) |
| 62 | `setPunishmentChemicalIndex` | `HandleSetPunishmentChemicalIndex(...)` (SVRule.h:523-525) |

---

## 7. Complete Operand Type Reference

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:423-480, 540-602`

Each instruction specifies an operand type (byte 1) and operand data (byte 2). The type determines how the data byte is interpreted:

### Runtime-Resolved Types (resolved each execution)

| Type | Name | Resolution | Read/Write |
|------|------|------------|------------|
| 0 | **accumulator** | `operandvalue = accumulator` (no pointer) | Read-only via value |
| 1 | **input neuron** | `&srcneuron[data]`: source neuron's variable at index `data` | Read/Write |
| 2 | **dendrite** | `&dendrite[data]`: dendrite's variable at index `data` | Read/Write |
| 3 | **neuron** | `&neuron[data]`: current neuron's variable at index `data` | Read/Write |
| 4 | **spare neuron** | `&spareneuron[data]`: spare neuron's variable at index `data` | Read/Write |
| 5 | **random** | Random float in [0.0, 1.0] | Read-only |
| 6 | **source chemical** | Stock C3 (`SVRule.h:321-323`): `chemicals[(arrayIndex + srcNeuronId) % NUMCHEM]`. openc2e: UNIMPLEMENTED, returns 0.0 | Read-only (in C3) |
| 7 | **chemical** | Stock C3 (`SVRule.h:324-326`): `chemicals[arrayIndex % NUMCHEM]`. openc2e: `creature->getChemical(data)` (matches) | Read-only |
| 8 | **destination chemical** | Stock C3 (`SVRule.h:327-329`): `chemicals[(arrayIndex + dstNeuronId) % NUMCHEM]`. openc2e: UNIMPLEMENTED, returns 0.0 | Read-only (in C3) |

### Constant Types (precalculated at init)

| Type | Name | Formula |
|------|------|---------|
| 9 | **zero** | `0.0` |
| 10 | **one** | `1.0` |
| 11 | **value** | `data × (1.0 / 248)`: maps 0-248 to 0.0-1.0 |
| 12 | **negative value** | `data × (-1.0 / 248)`: maps 0-248 to 0.0 to -1.0 |
| 13 | **value × 10** | `data × (10.0 / 248)`: maps 0-248 to 0.0-10.0 |
| 14 | **value / 10** | `data × (0.1 / 248)`: maps 0-248 to 0.0-0.1 |
| 15 | **value integer** | `(float)data`: raw integer as float (0-255) |

### Data Byte Sanitisation

For types 1-4, the data byte is clamped to 0-7 (there are only 8 variables per neuron/dendrite). Values > 7 are reduced to 7 with a debug warning.

---

## 8. Lobe Specifications

### C3/DS Standard Lobes (12 lobes)

| ID | Name | Neurons | Class | Role |
|----|------|---------|-------|------|
| `driv` | Drive | 20 | Input | Chemical drive levels (15 drives + 4 navigation + 1 spare) |
| `visn` | Vision | 40 | Input | Distance-to-agent sensory data per category |
| `smel` | Smell | 40 | Input | Olfactory sensory data per category |
| `noun` | Noun | 40 | Input | Player language input (agent categories) |
| `verb` | Verb | 17 | Input | Player language input (creature actions) |
| `sitn` | Situation | 9 | Input | Environmental situation neurons |
| `detl` | Detail | 11 | Input | Detail neurons |
| `prox` | Proximity | 20 | Input | Proximity/object distance |
| `stim` | Stim Source | 40 | Special | Which agent category caused last stimulus |
| `resp` | Response | 20 | Input | Reinforcement response signals |
| `attn` | Attention | 40 | **Output** | Agent category focus: winner selects attended object |
| `decn` | Decision | 17* | **Output** | Action selection: winner selects action to perform |

*Decision lobe neuron count: The lobe gene defines 17 neurons in the standard C3 genome (from game file analysis). Only indices 0-13 are active for decision-making. Neurons 14-16 are unused. Note: community wiki sources often state 13 neurons (the active count). The discrepancy arises because wikis count functional neurons while the genome defines the full lobe grid.

### Drive Neurons (20)

| Index | Drive | Chemical Slot |
|-------|-------|---------------|
| 0 | Pain | 148 |
| 1 | Hunger (Protein) | 149 |
| 2 | Hunger (Starch/Carb) | 150 |
| 3 | Hunger (Fat) | 151 |
| 4 | Cold | 152 |
| 5 | Hot | 153 |
| 6 | Tiredness | 154 |
| 7 | Sleepiness | 155 |
| 8 | Loneliness | 156 |
| 9 | Crowdedness | 157 |
| 10 | Fear | 158 |
| 11 | Boredom | 159 |
| 12 | Anger | 160 |
| 13 | Sex Drive | 161 |
| 14 | Comfort | 162 |
| 15-18 | Navigation (Up/Down/Exit/Enter) | 199-202 |
| 19 | Wait | 203 |

Drive backup chemicals exist at slots 131-145, allowing drives to be temporarily suppressed.

### Decision Neurons (17, 14 active)

| Index | Action | CAOS Event | Description |
|-------|--------|------------|-------------|
| 0 | Look | 16 | Quiescent/idle: look at attended object |
| 1 | Push | 17 | Activate1 on target (push, press) |
| 2 | Pull | 18 | Activate2 on target |
| 3 | Deactivate | 19 | Deactivate target |
| 4 | Approach | 20 | Walk toward attended object |
| 5 | Retreat | 21 | Walk away from attended object |
| 6 | Get | 22 | Pick up target |
| 7 | Drop | 23 | Put down carried object |
| 8 | Express | 24 | Show emotional expression |
| 9 | Rest | 25 | Sleep (WARNING: locks creature script) |
| 10 | Walk Left | 26 | Walk in left direction |
| 11 | Walk Right | 27 | Walk in right direction |
| 12 | Eat | 28 | Eat attended object |
| 13 | Hit/Attack | 29 | Hit attended creature |
| 14-16 | (unused) |: | Reserved, not connected |

The decision neuron → CAOS event mapping shown above is the openc2e convention (`event = 16 + neuron_index`). Stock C3 does this via runtime catalogue lookup: `Creature/Brain/BrainScriptFunctions.cpp:24-32` reads `theCatalogue.Get("Action Script To Neuron Mappings", i)` to populate `myScriptMappings[neuronId] = scriptOffset`. Stock and openc2e produce the same effective mapping if the catalogue file matches the `+16` convention; verify by inspecting `Catalogue/Action Script To Neuron Mappings.catalogue` from the C3 install. Until that catalogue read is done, treat `event = 16 + neuron_index` as openc2e-canonical and stock-likely-equivalent. (See also cc-ref.yaml `gotchas.decn_action_dual_layer`.)

### Attention Neurons (40)

Each of the 40 attention neurons corresponds to one of the 40 agent categories in the game. The winning neuron (determined by spare neuron mechanism) tells the engine which category of object the creature is paying attention to. The engine then selects the nearest visible agent of that category as the creature's focus.

### Perception Lobe

**Eliminated in C3/DS.** In C1/C2, the Perception lobe was a 112-neuron aggregation layer that combined Drive, Verb, General Sense, and Attention lobe inputs into a single addressable space. This was necessary because C1/C2 lobes could only connect to 2 source lobes (type 0 and type 1 dendrites). C3's tract system allows arbitrary connectivity, making the aggregation layer redundant.

### Concept Lobe (C1/C2) / Combination Lobe (C3)

**In C1/C2:** The Concept lobe is the largest lobe in the brain (640 neurons in C1). It forms memories by combining inputs with **logical AND** logic: each neuron can bind up to 3 input signals via the `anded 0` and `anded 1` SVRule operands. "I am hungry AND I see food" or "There is a creature AND it is a Grendel AND it is approaching." Its output passes to the Decision lobe. Dendrite strength is increased by reward chemical (204) and decreased by punishment chemical (205). Dendrites near zero strength may migrate to form new random connections: this is a key learning mechanism.

**In C3/DS:** The Concept lobe was renamed to the **Combination lobe** and its mechanism changed. Rather than strict AND gates, it uses weighted sums with reinforcement learning through the tract SVRule system. The principle is similar (combining multiple inputs into situation representations) but the implementation is more flexible. Note: the Creatures Wiki states "There are no concept lobes in Creatures 3": this refers to the renaming and mechanism change, not the elimination of the function.

---

## 9. The Tract System

### Purpose

Tracts replaced the fixed two-dendrite-type system from C1/C2. A tract is a bundle of dendrites connecting a range of neurons in a source lobe to a range of neurons in a destination lobe.

### Tract Gene Structure

Source: `openc2e/src/fileformats/genomeFile.h:294-323`

```
Field                  Type      Description
──────────────────────────────────────────────────────
updatetime             uint16    Tick frequency (0 = never). Truncated to uint8 at runtime.
srclobe[4]             char[4]   Source lobe ID (e.g., "attn")
srclobe_lowerbound     uint16    First neuron in source range
srclobe_upperbound     uint16    Last neuron in source range
src_noconnections      uint16    Connections per source neuron
destlobe[4]            char[4]   Destination lobe ID
destlobe_lowerbound    uint16    First neuron in dest range
destlobe_upperbound    uint16    Last neuron in dest range
dest_noconnections     uint16    Connections per dest neuron
migrates               uint8     Enable dynamic rewiring (0/1)
norandomconnections    uint8     Randomize connection count
srcvar                 uint8     Neuron variable index for activity tracking (src)
destvar                uint8     Neuron variable index for activity tracking (dst)
initrulealways         uint8     Run init rule every tick
spare[5]               uint8[5]  Reserved
initialiserule[48]     uint8[48] SVRule bytecode for initialization
updaterule[48]         uint8[48] SVRule bytecode for per-tick update
```

### Dendrite Creation

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:65-179`

When a tract is created from its genome gene:

**Non-migratory tracts:** A methodical distribution algorithm creates all dendrites during initialization. Source neurons are distributed evenly across destination neurons (or vice versa), ensuring full coverage.

**Migratory tracts:** Dendrites are created with optional randomness in connection count per neuron, and start with zero or near-zero strength (making them "loose" and eligible for migration).

### Tract Tick

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:226-239`

Each tick:
1. If migration is enabled, run `doMigration()` (see Section 14)
2. For each dendrite, run the initialiser SVRule (if `initrulealways`)
3. For each dendrite, run the updater SVRule

The SVRule context for dendrites uses the source neuron's `variables[0]` as the accumulator starting value, giving the dendrite access to the source neuron's output.

---

## 10. Weight Dynamics: STW/LTW Bidirectional Learning

This is the core learning mechanism of the SVRule brain. It implements a two-level weight system:

### The Two Weight Levels

- **STW (Short-Term Weight)**: stored in `dendrite[0]`. This is the active connection weight that determines signal strength. Changes quickly in response to reinforcement.
- **LTW (Long-Term Weight)**: stored in `dendrite[1]`. This is the steady-state weight that STW relaxes toward over time. Changes slowly, representing long-term memory.

### The Relaxation Algorithm (Opcode 44)

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:811-821`

**IMPORTANT:** The code saves the original `dendrite[0]` before modifying it. Step 2 uses the **original** value, not the updated one. The two relaxation steps are independent, not cascaded.

```
// Actual C++ implementation:
float weight = dendrite[0];                               // save original STW
dendrite[0] = weight + (dendrite[1] - weight) * stw;     // Step 1: STW relaxes toward LTW
dendrite[1] = dendrite[1] + (weight - dendrite[1]) * operandvalue;  // Step 2: LTW moves toward ORIGINAL STW
```

Where:
- `weight` = the original `dendrite[0]` before modification (saved to local variable)
- `dendrite[0]` = STW (short-term weight)
- `dendrite[1]` = LTW (long-term weight)
- `stw` = short-term relaxation rate (set by opcode 43; **static variable: see warning below**)
- `operandvalue` = long-term relaxation rate (the operand value of opcode 44 itself)

### Bidirectional Dynamics

The two relaxation steps create a push-pull dynamic:

1. **STW → LTW direction:** STW constantly decays toward LTW at `stw_rate`. Without reinforcement, any learned weight change fades back to the long-term baseline. This is forgetting.

2. **LTW → STW direction:** LTW slowly shifts toward STW at `ltw_rate` (typically much smaller than `stw_rate`). If STW is consistently reinforced to a new value, LTW gradually follows, making the change permanent. This is consolidation.

### Reinforcement (C1/C2 model)

In C1/C2, STW is updated by:
```
STW = LTW + (susceptibility / 255) × reinforcement
```

Where `susceptibility` is a per-dendrite value representing how open the connection is to change, and `reinforcement` is derived from reward/punishment chemicals (204/205).

In C3/DS, this same mechanism is encoded in the tract's SVRules rather than being hardcoded.

### Critical Implementation Note

**The `stw` variable in openc2e is `static`**: it persists across ALL SVRule calls, not just within one dendrite's processing. This means opcode 43 (set STW relax rate) sets a rate that applies to ALL subsequent opcode 44 calls until changed again. This may be a bug or an intentional design choice for efficiency.

```cpp
static float stw = 0.0f;  // declared in runRule(), persists across calls
```

---

## 11. Winner-Takes-All: The Spare Neuron Mechanism

### C3/DS Implementation

In C3/DS, Winner-Takes-All is NOT implemented as a dedicated sweep. Instead, it uses the **spare neuron** mechanism built into the SVRule system:

1. Each lobe maintains a `spare` index: the index of the last neuron to execute opcode 31 ("register as spare")
2. When a lobe's SVRule iterates over neurons (0 through N-1), each neuron's update rule runs. The rule can compare the current neuron against the spare neuron using operand type 4.
3. If the current neuron "wins" (its value exceeds the spare neuron's value), the SVRule executes opcode 31, and the lobe updates `spare` to the current neuron's index.
4. After all neurons have been processed, `spare` holds the index of the winning neuron.

The SVRule for a WTA lobe might look conceptually like:
```
LOAD neuron[0]              // Load current neuron's output
IF > spare_neuron[0]        // Compare against current winner
  REGISTER AS SPARE         // I'm the new winner
```

### How the Engine Reads the Winner

Source: The engine calls `lobe->getSpareNeuron()` to get the winner index:
- For the attention lobe (`attn`): the spare neuron index = the category of object the creature attends to
- For the decision lobe (`decn`): the spare neuron index = the action to perform, mapped to CAOS event via `event = 16 + spare_index`

### C1/C2 Implementation (for comparison)

In C1/C2, WTA was a simple flag in the lobe gene (`flags & 1`). After all neurons were processed, a sweep found the highest output and zeroed all others:

```cpp
if (ourGene->flags & 1) {  // WTA flag
    uint8_t bestvalue = 0;
    uint8_t* bestoutput = NULL;
    for (auto& neuron : neurons) {
        if (neuron.output > bestvalue) {
            bestvalue = neuron.output;
            bestoutput = &neuron.output;
        }
        neuron.output = 0;  // Zero everyone
    }
    if (bestoutput) *bestoutput = bestvalue;  // Restore winner
}
```

Source: `openc2e/src/openc2e/creatures/oldBrain.cpp:572-586`

---

## 12. Instinct Gene System

### Purpose

Instinct genes provide innate behaviours by setting initial dendrite weights during brain initialization. They simulate "dreaming": the brain is put into a special REM chemical state and ticked with instinct-specified inputs, causing the dendrite learning rules to set weights as if the creature had actually experienced those situations.

### Instinct Gene Structure

Source: `openc2e/src/fileformats/genomeFile.h:565-582`

```
Field                    Type    Description
──────────────────────────────────────────────────
lobes[3]                 uint8   Up to 3 source lobe tissue IDs (255 = unused)
neurons[3]               uint8   Neuron index in each source lobe
action                   uint8   Verb/action number to associate
drive                    uint8   Which drive/response neuron to reinforce
level                    uint8   Reinforcement level:
                                   128 = neutral
                                   >128 = positive reinforcement
                                   <128 = negative reinforcement
```

### Instinct Processing Algorithm

Source: `openc2e/src/openc2e/creatures/CreatureAI.cpp:207-331`

Instincts are processed during creature initialization (and periodically during sleep). The algorithm:

**Step 0: Preparation:**
```
Pop instinct gene from unprocessed queue
Reverse-map action number to verb neuron index
Validate verb/resp lobes exist, check neuron bounds
```

**Step 1: Wipe and prepare REM state:**
```
Wipe ALL lobes (reset all neuron states to zero)
Set chemical 212 (pre-REM) = 1.0
Set chemical 213 (REM) = 0.0
Tick brain once (resets brain into pre-dreaming state)
```

**Step 2: Enter REM:**
```
Set chemical 212 = 0.0
Set chemical 213 (REM) = 1.0
```

**Step 3: First dream tick (set inputs):**
```
For each of the 3 instinct input slots:
    If lobes[i] != 255 (slot is used):
        Find the lobe at tissue (lobes[i] - 1)   ← note the -1 offset
        Set neuron neurons[i] input = 1.0
        EXCEPTION: if lobe tissue == 3 (vision), set input = 0.1 instead
Also set the verb neuron for the specified action = 1.0
Tick brain
```

**Step 4: Second dream tick (set reinforcement):**
```
Set response lobe neuron[drive] input = (level - 128) / 128.0
Tick brain again
```

**Step 5: Clean up:**
```
Set chemical 213 = 0.0
Wipe ALL lobes again (full reset after dreaming)
```

Note: The vision lobe special case (0.1 instead of 1.0) prevents vision signals from dominating during instinct processing. The initial and final lobe wipes ensure clean state isolation between instinct processing and normal brain operation.

### How This Sets Weights

The key insight: **weights are not set directly by instinct genes.** Instead, the instinct processing ticks the brain in a controlled scenario. During these ticks, the normal dendrite SVRules run. If the SVRules include learning operations (opcodes 43/44), the dendrite weights are updated through the normal learning mechanism, as if the creature had actually experienced the instinct scenario.

This means the same learning rules that handle real-time reinforcement also handle instinct initialization. The instinct system bootstraps the weights, and the same mechanism refines them during the creature's life.

### Example Instinct

"When hungry and see food, eating is good":
```
lobes[0] = drive_tissue     neurons[0] = 1  (hunger protein)
lobes[1] = visn_tissue      neurons[1] = 7  (food category)
lobes[2] = 255 (unused)     neurons[2] = 0
action = 12 (eat)
drive = 1 (hunger)
level = 200 (strong positive reinforcement)
```

---

## 13. Brain Tick Algorithm

### Processing Order

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:1031-1037`

All brain components (lobes and tracts) are stored in a `multiset` sorted by their `updatetime` field. Each tick:

```
for each component in components (sorted by updatetime ascending):
    if component.updatetime != 0:
        component.tick()
```

Components with `updatetime == 0` are never ticked. The updatetime determines both the frequency and order of processing: lower updatetime = processes first.

**Implementation note:** The genome stores updatetime as uint16 (0-65535), but openc2e's `c2eBrainComponent` base class stores it as uint8 (0-255). Values > 255 in the genome are silently truncated at construction. In practice, standard C3 genomes use small updatetime values, so this truncation rarely matters.

### Lobe Tick Detail

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:366-376`

```
for each neuron in lobe:
    if initrulealways:
        run initrule(neuron.input, _, neuron.vars, spare.vars, _, creature)
        if returned true: spare = this_neuron_index
    run updaterule(neuron.input, _, neuron.vars, spare.vars, _, creature)
    if returned true: spare = this_neuron_index
    neuron.input = 0.0   // clear for next tick
```

### Tract Tick Detail

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:226-239`

```
if tract.migrates:
    doMigration()
for each dendrite in tract:
    if initrulealways:
        run initrule(source.vars[0], source.vars, dest.vars, _, dendrite.vars, creature)
    run updaterule(source.vars[0], source.vars, dest.vars, _, dendrite.vars, creature)
```

### Signal Flow Within a Tick

1. **Tracts execute first** (if they have lower updatetime): dendrite SVRules read source neuron outputs and inject signals into destination neuron inputs (via opcodes 50/51 or by writing to `neuron[1]`).
2. **Lobes execute after**: neuron SVRules process accumulated inputs and update neuron state variables.
3. **Lobe clears input**: after processing, each neuron's input is zeroed for the next tick.

This means there's a one-tick delay between a source neuron changing its output and a destination neuron seeing that change through dendrites.

---

## 14. Dendrite Migration

### Purpose

Migration allows dendrites to dynamically rewire: disconnecting from inactive neurons and reconnecting to active ones. This enables the brain to discover new associations and form new memories.

### Mechanism

Source: `openc2e/src/openc2e/creatures/c2eBrain.cpp:262-315`

A dendrite is considered "loose" when its `variables[7]` (strength) equals 0.0. Loose dendrites are available for migration.

The migration algorithm each tick:

```
for each dendrite in tract:
    if dendrite.variables[7] == 0.0:   // loose
        // Find source neuron with highest NGF (Nerve Growth Factor)
        // NGF is stored in source_neuron.variables[srcvar]
        highestsrc = source neuron with max variables[srcvar] (must be > 0)

        // Find dest neuron with highest NGF not already connected
        // NGF is stored in dest_neuron.variables[destvar]
        highestdest = dest neuron with max variables[destvar]
                      AND no existing dendrite from highestsrc to this neuron

        // Reconnect
        if both found:
            dendrite.source = highestsrc
            dendrite.dest = highestdest
            // Re-run init rule to reset dendrite variables
```

### Activity Tracking (srcvar / destvar) and NGF

The migration algorithm reads neuron state variables at the indices specified by the tract gene's `srcvar` and `destvar` fields to determine which neurons are most active. Active neurons have higher values at these indices, attracting loose dendrites.

**Correction (2026-04-26):** A previous revision of this document removed the NGF (Neural Growth Factor) terminology, claiming it was a descriptive analogy not used in the game's code. The 1999 Cyberlife C3 source code disproves this. `Creature/Brain/SVRule.h:27` explicitly defines `NGF_VAR` as neuron variable index 7 with the comment "Neural Growth Factor - controls dendrite migration". The term is canonical in the engine source, not just an external analogy. By convention in stock genomes the migration `srcvar`/`destvar` indices target slot 7 (NGF_VAR) on each side of the tract.

### Implementation Limitations

In openc2e, only the `src_noconnections != 0` migration path is fully implemented. The `dest_noconnections != 0` path (migrating based on destination neuron activity) prints a warning and does nothing. After a dendrite is reconnected, it is either wiped (if `initrulealways` is true) or re-initialized by running the init SVRule.

A duplicate-connection check (`getDendriteFromTo`) prevents two dendrites from connecting the same source-destination pair.

### Biological Analogy

This mimics the biological process where unused synaptic connections are pruned (dendrite strength decays to zero) and new connections form toward active neurons. It's the mechanism behind "neurons that fire together wire together": if two lobes are consistently active at the same time, loose dendrites migrate to connect them.

### C1/C2 Migration (for comparison)

C1/C2 had two migration modes:
- **Mode 1**: Migrate any loose dendrite individually to a random firing source neuron
- **Mode 2**: Migrate ALL dendrites of a fully-loose neuron at once, with uniqueness checking (no two dendrites from the same neuron connect to the same source)

---

## 15. Chemical Integration

### Overview

The SVRule brain interfaces with the creature's biochemistry system in several ways:

### Chemical Access in SVRules

- **Operand type 7 (chemical):** SVRules can read any chemical level from the creature's biochemistry. The data byte specifies which chemical slot (0-255). This is read-only: SVRules cannot directly modify chemical levels.
- **Operand types 6, 8 (source/destination chemical):** Intended for reading chemicals at the source or destination of a neural signal. **UNIMPLEMENTED in openc2e.**

### Key Brain Chemicals

| Slot | Name | Role in Brain |
|------|------|---------------|
| 117 | Adrenalin | Modulates learning rate and arousal |
| 125 | Life | Brain organ health |
| 127 | Injury | Affects pain drive |
| 128 | Stress | Modulates emotional responses |
| 148-162 | Drive chemicals | Feed into drive lobe neurons (see Section 8) |
| 199-203 | Navigation drives | Feed into drive lobe neurons 15-19 |
| 204 | **Reward** | Positive reinforcement: strengthens dendrite weights |
| 205 | **Punishment** | Negative reinforcement: weakens dendrite weights |
| 212 | Pre-REM | Triggers brain reset before dreaming |
| 213 | REM | Enables instinct processing during sleep |

**Critical correction:** Reward = chemical 204, Punishment = chemical 205. These are NOT at slots 49/50 (a common error in older documentation).

### Chemical Emitters

Neurons can trigger chemical emitters: when a specific neuron fires, a small amount of a chemical is released. Standard C3 norn neuroemitters release adrenalin, fear, and crowdedness when the norn sees a grendel.

### Chemical Receptors

Chemical receptors monitor chemical levels and write values into lobe neurons. This is how drive chemical levels (148-162) reach the drive lobe: receptors read the chemical values and inject them as neuron input.

### Brain Organ

Post-C2, the brain is an organ with lifeforce. If brain organ lifeforce drops too low (insufficient ATP), the creature dies. This means brain function degrades with poor health.

---

## 16. The Decision Pipeline: From Inputs to Action

### Complete Signal Flow

This describes how a raw sensory event becomes a creature action:

**Step 1: Sensory Input:**
The engine updates input lobe neurons each tick:
- Vision lobe: distance-to-nearest-agent for each of 40 categories
- Smell lobe: olfactory strength for each of 40 categories
- Situation lobe: 9 environmental state neurons
- Detail lobe: 11 detail neurons
- Drive lobe: current drive chemical levels via receptors
- Proximity lobe: distance measurements

**Step 2: Tract Processing (dendrites fire):**
Tracts connecting input lobes to processing lobes run their SVRules. Each dendrite reads its source neuron's output, processes it through the tract's SVRule (applying weights, thresholds, learning), and injects the result into the destination neuron's input accumulator.

**Step 3: Processing Lobes Update:**
Processing lobes (concept/combination, attention, decision) run their neuron SVRules on the accumulated inputs:

- **Concept lobe:** Each neuron ANDs its dendrite inputs. If all inputs are firing, the neuron fires. If any input is zero, the neuron doesn't fire. This creates situation-specific activation: "hungry AND food visible."
- **Attention lobe:** Neurons accumulate weighted inputs from concept/sensory lobes. The SVRule includes a WTA mechanism: each neuron compares against the current spare and registers as spare if it wins. The neuron with the highest accumulated value becomes the spare (winner).
- **Decision lobe:** Same WTA mechanism. Neurons accumulate weighted inputs from concept, verb, and drive connections. The winning neuron determines the action.

**Step 4: Engine Reads Outputs:**
```
attn_category = attn_lobe.getSpareNeuron()  // which object category
decn_action = decn_lobe.getSpareNeuron()    // which action
event_number = 16 + decn_action             // CAOS script number
```

**Step 5: Action Execution:**
The engine finds the nearest visible agent of `attn_category`, then fires CAOS script `event_number` on it (or on the creature itself for self-directed actions like rest/express).

### Temporal Dynamics

The persistence of attention and decisions comes from the SVRule update rules:
- Neurons with high relaxation rates retain their state across ticks
- STW/LTW relaxation provides long-term stability to dendrite weights
- The one-tick delay between dendrite processing and lobe processing creates smooth transitions

In the original game, attention typically persists for 5-10 seconds because:
1. The attention lobe's update SVRule includes persistence terms
2. STW/LTW relaxation prevents rapid weight changes
3. The concept lobe's AND logic means complex situations sustain attention (as long as ALL conditions remain true)

---

## 17. C1/C2 vs C3/DS Differences

### Major Architectural Changes

| Feature | C1/C2 | C3/DS |
|---------|-------|-------|
| **Neuron values** | 8-bit integers (0-255) | 32-bit floats |
| **Dendrite connections** | 2 types per lobe, each to one source lobe | Arbitrary tracts (any lobe to any lobe) |
| **SVRules** | Simple conditional expressions (12 bytes) | Full register machine (48 bytes, 16 instructions) |
| **WTA mechanism** | Flag in lobe gene → post-tick sweep | Spare neuron mechanism via SVRule opcode 31 |
| **Perception lobe** | 112 neurons, aggregates 4 input lobes | Eliminated (tracts allow direct connectivity) |
| **Weight system** | Fixed STW/LTW/susceptibility/strength fields | General-purpose 8 float variables per dendrite |
| **Learning rules** | Separate strgain/strloss/suscept/relax SVRules | Single init + update SVRule per tract |
| **Back/forward propagation** | C2 only, dedicated SVRules per dendrite type | Can be encoded in tract SVRules |
| **Migration** | 2 modes (individual vs bulk) | NGF-based, single algorithm |
| **Chemical access** | 4-6 chemicals via named SVRule tokens | Any chemical via operand type 7 |

### What Was Gained

- **Flexibility:** Any lobe can connect to any other lobe via tracts
- **Expressiveness:** 48-byte SVRules with 68+ opcodes vs 12-byte rules with ~40 opcodes
- **Precision:** Float arithmetic eliminates integer overflow/underflow issues
- **Extensibility:** General-purpose variable arrays allow new algorithms without code changes

### What Was Lost or Degraded

- **Simplicity:** The register machine is harder to reason about than C1/C2's pattern-match rules
- **Guaranteed features:** Several opcodes are unimplemented in openc2e (see Section 18)
- **Explicit learning phases:** C1/C2 had separate strength gain/loss/susceptibility/relaxation rules per dendrite type; C3/DS encodes everything in a single SVRule which may be less structured

---

## 18. Unimplemented Features in openc2e

The following features exist in the C3/DS genome specification but are not implemented in the openc2e engine.

**Critical clarification (2026-04-26):** every opcode and operand type listed below IS implemented in the 1999 Cyberlife C3 stock source code (`Creature/Brain/SVRule.h:236-243, 321-329, 508-525, 621-652`). "Unimplemented" here means openc2e port did not carry them across; running on stock C3, they execute the documented semantics. See Section 6 for the per-opcode behaviour as defined in the C3 source.

### Unimplemented SVRule Opcodes

| Op | Name | Intended Purpose |
|----|------|-----------------|
| 37 | Leakage rate | Neuron state decay toward rest state |
| 38 | Rest state | Baseline resting value |
| 39 | Input gain hi-lo | Input signal scaling |
| 40 | **Persistence** | `S(1) = S(0) + ((1-P) × (I(0) - S(0)))`: temporal smoothing. **This is significant: persistence is a key contributor to attention stability.** |
| 41 | Signal noise | Random noise injection |
| 42 | **Winner Takes All** | Formal WTA sweep. The spare neuron mechanism (opcode 31) provides equivalent functionality. |
| 57-62 | Reward/Punish threshold/rate/use | Structured reinforcement learning opcodes |

### Unimplemented Operand Types

| Type | Name | Intended Purpose |
|------|------|-----------------|
| 6 | Source chemical | Chemical at the source of a neural signal |
| 8 | Destination chemical | Chemical at the destination of a neural signal |

### Known Implementation Issues

1. **Static `stw` variable:** The short-term relaxation rate (`stw`) is declared as `static` inside `runRule()`, meaning it persists across ALL SVRule calls for ALL dendrites. This may cause cross-contamination between different tracts' learning rates.

2. **Opcodes 14/15 may be swapped:** Comments in the source code note uncertainty about whether opcode 14 should be "non-positive" or "non-negative" (and vice versa for opcode 15).

3. **Reward/punishment in tracts:** The tract tick function has a TODO comment: `"// TODO: reward/punishment? anything else? scary brains!"`: suggesting that reward/punishment processing in tract dendrites may be incomplete.

4. **Lobe WTA flag:** The `WTA` field exists in `c2eBrainLobeGene` but is commented as "unused in final game?": confirming that C3/DS relies on SVRule-based WTA via opcode 31 rather than the lobe flag.

---

## Appendix A: C1 Lobe Map

The original Creatures 1 brain had 9 lobes with 952 neurons:

| # | Name | X | Y | W | H | Neurons | Role |
|---|------|---|---|---|---|---------|------|
| 0 | Perception | 4 | 13 | 7 | 16 | 112 | Aggregate input container |
| 1 | Drive | 34 | 30 | 8 | 2 | 16 | Emotional state (one per drive) |
| 2 | Source | 15 | 24 | 8 | 5 | 40 | Stimulus source categorisation |
| 3 | Verb | 37 | 24 | 8 | 2 | 16 | Language action input |
| 4 | Noun | 21 | 3 | 20 | 2 | 40 | Language object input |
| 5 | General Sense | 32 | 34 | 8 | 4 | 32 | Environmental sensation |
| 6 | Decision | 53 | 15 | 1 | 16 | 16 | Action selection (WTA) |
| 7 | Attention | 44 | 30 | 5 | 8 | 40 | Object focus (WTA) |
| 8 | Concept | 12 | 6 | 40 | 16 | 640 | Memory/association (AND logic) |

Total: ~952 neurons, ~5000 dendrite connections.

---

## Appendix B: C1/C2 SVRule Opcodes

For historical comparison and understanding the evolution of the system:

### C1 Opcodes (22 total)

| Op | Token | Description |
|----|-------|-------------|
| 0 | end | End of SVRule |
| 1 | 0 | Integer zero |
| 2 | 1 | Integer one |
| 3 | 64 | Integer 64 |
| 4 | 255 | Integer 255 |
| 5-8 | chem 0-3 | Chemical amount in brain lobe |
| 9 | state | Current cell state |
| 10 | output | Current cell output |
| 11 | thres | Nominal threshold |
| 12 | type 0 | Sum of type 0 dendrites: `value = source_cell × (stw/255)` |
| 13 | type 1 | Sum of type 1 dendrites |
| 14 | anded 0 | AND of type 0 dendrites (0 if any source is 0) |
| 15 | anded 1 | AND of type 1 dendrites |
| 16 | input | Dendrite input signal |
| 17 | conduct | Not hooked up |
| 18 | suscept | Susceptibility to reinforcement |
| 19 | STW | Short term weight |
| 20 | LTW | Long term weight |
| 21 | strength | Dendrite strength |
| 22 | TRUE | If previous != 0, execute rest; else state=0 and stop |
| 23 | PLUS | Add following to previous |
| 24 | MINUS | Subtract following from previous |
| 25 | TIMES | `left × right / 256` |
| 26 | INCR | Previous + 1 |
| 27 | DECR | Previous - 1 |

### Additional C2 Opcodes

| Op | Token | Description |
|----|-------|-------------|
| 22 | 32 | Integer 32 |
| 23 | 128 | Integer 128 |
| 24 | rnd const | Random constant |
| 25-26 | chem 4-5 | Additional chemicals |
| 27 | leak in | Back propagation from dest dendrites |
| 28 | leak out | Forward propagation |
| 29 | curr src leak in | Source neuron leak in charge |
| 36 | FALSE | If previous == 0, execute rest; else state=0 and stop |
| 37 | multiply | Actual multiplication |
| 38 | average | Average of two values |
| 39 | move twrds | Move toward: `prev + (arg1 - prev) / (256/arg2)` |
| 40 | random | Random between two arguments |

### Dendrite Signal Calculation (C1/C2)

```
dendrite_value = source_neuron_output × (STW / 255)
```

For a lobe, `type 0` = sum of all type 0 dendrite values, `type 1` = sum of all type 1 values. `anded 0` = same sum but returns 0 if ANY source neuron has output 0.

The result is scaled by `inputgain/255` before use. An empty dendrite list returns 255 (full signal).

---

## Appendix C: Source File Index

### Primary Implementation Files

| File | Contents |
|------|----------|
| `openc2e/src/openc2e/creatures/c2eBrain.h` | c2eNeuron, c2eDendrite, c2eSVRule, c2eLobe, c2eTract, c2eBrain class definitions |
| `openc2e/src/openc2e/creatures/c2eBrain.cpp` | Full SVRule interpreter, lobe/tract tick, dendrite migration, brain tick ordering |
| `openc2e/src/fileformats/genomeFile.h` | c2eBrainLobeGene, c2eBrainTractGene, creatureInstinctGene struct definitions |
| `openc2e/src/openc2e/creatures/CreatureAI.cpp` | processInstinct(): instinct gene processing with REM simulation |

### Legacy Implementation (C1/C2)

| File | Contents |
|------|----------|
| `openc2e/src/openc2e/creatures/oldBrain.h` | oldNeuron, oldDendrite, oldLobe struct definitions |
| `openc2e/src/openc2e/creatures/oldBrain.cpp` | C1/C2 SVRule interpreter, WTA flag implementation, dendrite migration |

### Research Archive (Firecrawl)

| File | Contents |
|------|----------|
| `.firecrawl/brain-wiki.md` | Creatures Wiki: main Brain article with full opcode tables |
| `.firecrawl/double-nz-svrules.md` | CDR: experimentally verified C1/C2 SVRule reference |
| `.firecrawl/attention-lobe.md` | Creatures Wiki: Attention lobe (40 neurons, WTA, engine integration) |
| `.firecrawl/decision-lobe.md` | Creatures Wiki: Decision lobe (13 neurons, WTA, CAOS scripts) |
| `.firecrawl/concept-lobe.md` | Creatures Wiki: Concept lobe (640 neurons, AND logic, migration) |
| `.firecrawl/drive-lobe.md` | Creatures Wiki: Drive lobe (one neuron per drive chemical) |
| `.firecrawl/oldBrain.cpp.md` | Scraped C1/C2 brain source with dendrite sum, WTA, migration |

### Reference Documents

| File | Contents |
|------|----------|
| `docs/reference/verified-reference.md` | Cross-verified lobe specs, opcode tables, weight dynamics |
| `docs/reference/game-files-analysis.md` | Game genome analysis: lobes, chemicals, decision mapping |

---

*End of SVRule Brain Complete Reference*
