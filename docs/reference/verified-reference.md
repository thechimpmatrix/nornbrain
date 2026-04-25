# NORNBRAIN Verified Reference Document
# Compiled: 2026-03-28
# Status: Cross-verified from 4 independent research agents
# Project: LNN Brain Transplant for Creatures (openc2e C3/DS)
# Re-verified: 2026-04-26 against 1999 Cyberlife C3 source code at <PROJECT_ROOT>/C3sourcecode/engine/
# (Internet Archive: creatures-3-1999-cyberlife-source-code.-7z)
# Critical clarification: every "UNIMPLEMENTED" claim in this document refers to
# openc2e's port status, NOT the stock C3 engine. The 1999 stock source implements
# all SVRule opcodes 0-68, including 37-42 (doNominalThreshold, doLeakageRate,
# doRestState, doInputGainLoHi, doPersistence, doSignalNoise, doWinnerTakesAll)
# and 57-62 (setReward/Punishment Threshold/Rate/ChemicalIndex), and operand types
# 6 and 8 (chemicalIndexedBySourceNeuronIdCode, chemicalIndexedByDestinationNeuronIdCode).
# See svrule-brain-complete-reference.md Section 6 for the per-opcode formulas
# read from C3 source SVRule.h:236-243, 321-329, 508-525, 621-652.

---

## Table of Contents

- [PART I: CREATURES C3/DS BRAIN ARCHITECTURE](#part-i-creatures-c3ds-brain-architecture)
  - [1. C3/DS Brain Architecture](#1-c3ds-brain-architecture)
  - [2. SVRule System](#2-svrule-system)
  - [3. Dendrite System](#3-dendrite-system)
  - [4. Biochemistry System (C3/DS)](#4-biochemistry-system-c3ds)
  - [5. Genome Format (C3/DS)](#5-genome-format-c3ds)
  - [6. Known Failure Modes](#6-known-failure-modes)
  - [7. CAOS Neural Interface](#7-caos-neural-interface)
  - [8. Source Bibliography (Part I)](#8-source-bibliography-part-i)
- [PART II: openc2e ENGINE -- BRAIN MODULE SOURCE CODE](#part-ii-openc2e-engine----brain-module-source-code)
  - [1. Repository Structure](#1-repository-structure)
  - [2. Brain Class Interface](#2-brain-class-interface)
  - [3. Lobe Implementation](#3-lobe-implementation)
  - [4. SVRule Implementation](#4-svrule-implementation)
  - [5. Dendrite/Tract Implementation](#5-dendritetract-implementation)
  - [6. Biochemistry Implementation](#6-biochemistry-implementation)
  - [7. Genome Parser -- Brain-Relevant Genes](#7-genome-parser----brain-relevant-genes)
  - [8. "Brain in a Vat" Tool](#8-brain-in-a-vat-tool)
  - [9. Key Data Structures Summary](#9-key-data-structures-summary)
  - [10. Interface Contract for Brain Replacement](#10-interface-contract-for-brain-replacement)
  - [11. Implementation Completeness Notes](#11-implementation-completeness-notes)
- [PART III: LIQUID NEURAL NETWORKS -- THEORY & ARCHITECTURE](#part-iii-liquid-neural-networks----theory--architecture)
  - [1. Liquid Time-Constant (LTC) Networks -- Core Theory](#1-liquid-time-constant-ltc-networks----core-theory)
  - [2. Closed-form Continuous-depth (CfC) Models](#2-closed-form-continuous-depth-cfc-models)
  - [3. Neural Circuit Policies (NCP)](#3-neural-circuit-policies-ncp)
  - [4. Mathematical Foundations](#4-mathematical-foundations)
  - [5. Key Properties Relevant to Game AI](#5-key-properties-relevant-to-game-ai)
  - [6. Liquid AI Company and Ecosystem](#6-liquid-ai-company-and-ecosystem)
  - [7. Source Bibliography (Part III)](#7-source-bibliography-part-iii)
- [PART IV: ncps PACKAGE -- API REFERENCE](#part-iv-ncps-package----api-reference)
  - [1. Package Overview](#1-package-overview)
  - [2. API Surface -- PyTorch Backend (Primary)](#2-api-surface----pytorch-backend-primary)
  - [3. Wiring System Detail](#3-wiring-system-detail)
  - [4. Training Patterns](#4-training-patterns)
  - [5. Inference and Adaptation](#5-inference-and-adaptation)
  - [6. Code Examples from Official Sources](#6-code-examples-from-official-sources)
  - [7. Known Limitations and Gotchas](#7-known-limitations-and-gotchas)
  - [8. Stacking and Composition](#8-stacking-and-composition)
- [PART V: CROSS-DOMAIN MAPPING NOTES](#part-v-cross-domain-mapping-notes)
- [PART VI: VERIFICATION SUMMARY](#part-vi-verification-summary)
- [APPENDIX A: COMPLETE SOURCE BIBLIOGRAPHY](#appendix-a-complete-source-bibliography)

---

# PART I: CREATURES C3/DS BRAIN ARCHITECTURE

*Source document: `/reference/c3ds-brain-architecture.md`*
*Research compiled: 2026-03-28*
*Sources verified via web fetch (firecrawl)*

---

## 1. C3/DS Brain Architecture

### 1.1 Overview

The Creatures brain is built from approximately 10 **lobes**, ~900 **neurons**, and many thousands of **dendrites**. The brain works in conjunction with the creature's biochemistry system to drive behaviour. Each neuron is a register that stores a floating-point value (in C3/DS, values range from -1.0 to 1.0). Neurons lose their stored values over time via leakage/decay mechanisms.

**Source:** https://creatures.wiki/Brain [VERIFIED - fetched 2026-03-28]
**Source:** https://www.alanzucconi.com/2020/07/27/the-ai-of-creatures/ [VERIFIED - fetched 2026-03-28]

### 1.2 Key Architectural Difference: C3/DS vs C1/C2

In C1/C2, each lobe could contain only **two dendrite types** (type 0 and type 1), each connecting to a single other lobe. This meant each lobe could receive input from at most 2 other lobes.

In C3/DS (the Creatures Evolution Engine), dendrites are organised into **tracts** -- arbitrary groupings that connect any two lobes. This removed the two-source limitation and allowed far more complex connectivity patterns. Each tract is defined by its own gene (Brain Tract gene, type 0 subtype 2).

**Source:** https://creatures.wiki/Brain [VERIFIED]

### 1.3 C1 Lobe List (Baseline Reference)

The C1/C2 lobe structure forms the basis of the C3/DS architecture. The standard C1 norn brain has 9 lobes:

| # | Name | Width | Height | Neurons | Role |
|---|------|-------|--------|---------|------|
| 0 | Perception | 7 | 16 | 112 | Aggregate input container -- copies values from Drive, Verb, General Sense, and Attention lobes into a single addressable space |
| 1 | Drive | 8 | 2 | 16 | Chemical drives (pain, hunger, fear, etc.) -- 13 used in C1, expanded to 17 in C2, 15+ in C3 |
| 2 | Stimulus Source | 8 | 5 | 40 | Fires based on which objects are perceived (seen/heard) -- "what is in the environment" |
| 3 | Verb | 8 | 2 | 16 | Activates when user types verb commands -- player language input for actions |
| 4 | Noun | 20 | 2 | 40 | Activates when user types noun words -- player language input for objects |
| 5 | General Sense | 8 | 4 | 32 | Miscellaneous sensory inputs: patted, slapped, wall bump, vehicle state, creature relationship flags, etc. |
| 6 | Decision | 1 | 16 | 16 | Output lobe -- each neuron = one possible action. Winner-Takes-All selects the action to perform |
| 7 | Attention | 5 | 8 | 40 | Output lobe -- each neuron = one object category. Winner-Takes-All selects what to focus on |
| 8 | Concept | 40 | 16 | 640 | Combination/association lobe -- each neuron represents a "situation" combining up to 3 perception inputs via AND logic. Also called "Combination lobe" in C3 |

**Total neurons:** 952 (C1 standard norn)
**Total connections:** ~5,000 (C1, managed via reinforcement/atrophy/migration)

**Source:** https://creatures.wiki/Brain [VERIFIED]
**Source:** https://www.alanzucconi.com/2020/07/27/the-ai-of-creatures/ [VERIFIED]

### 1.4 C3/DS Lobe Architecture

C3/DS retains the same fundamental lobe concepts but reorganises them using the tract system. Key changes:

- **Perception lobe eliminated** -- In C1/C2, the Perception lobe existed solely to aggregate inputs from Drive, Verb, General Sense, and Attention lobes (because lobes could only connect to 2 sources). With tracts allowing arbitrary connectivity, this aggregation lobe is no longer necessary.
- **Concept lobe renamed** to "Combination lobe" -- reflects its AND-combining function more accurately.
- **ForF (Friend or Foe) lobe added** -- A new C3/DS-specific lobe that tracks how a creature feels about other specific creatures. Neurons represent individual creatures the norn has encountered.
- **Drive lobe expanded** -- C3 drives include: Pain, Hunger for Protein, Hunger for Carbohydrate, Hunger for Fat, Coldness, Hotness, Tiredness, Sleepiness, Loneliness, Crowdedness, Fear, Boredom, Anger, Sex Drive, Comfort Drive (15 drives vs C1's 13).
- **Lobe IDs** changed from numeric indices to 4-character string identifiers (e.g., "driv", "verb", "noun", "detn", "attn", "comb").

**Standard C3/DS Lobes (from genome analysis):**

| Lobe ID | Name | Role | Notes |
|---------|------|------|-------|
| driv | Drive | Drive chemical levels | 15+ neurons for C3 drives |
| verb | Verb | Player verb input | Language processing |
| noun | Noun | Player noun input | Language processing |
| stim | Stimulus Source | Environmental perception | Object categories |
| sens | General Sense | Misc sensory flags | Patted, slapped, relationships, etc. |
| comb | Combination | Situation representation (AND logic) | Formerly "Concept lobe" |
| detn | Decision | Action selection (Winner-Takes-All) | Output: which action to perform |
| attn | Attention | Object focus (Winner-Takes-All) | Output: what to attend to |
| forf | Friend or Foe | Creature relationship tracking | New in C3/DS |

[NEEDS VERIFICATION: The exact 4-character lobe IDs are inferred from genome format documentation and community sources. The precise list should be confirmed against an actual C3/DS genome file.]

[CROSS-REFERENCE: See Part II Section 10 for lobe IDs confirmed from openc2e source code: "driv", "verb", "noun", "visn", "smel", "attn", "decn", "resp". Note discrepancies flagged in Part VI.]

**Source:** https://creatures.wiki/Brain [VERIFIED]
**Source:** https://creatures.fandom.com/wiki/ForF_lobe [VERIFIED]
**Source:** https://creatures.fandom.com/wiki/Concept_lobe [VERIFIED]
**Source:** https://creatures.wiki/GEN_files (version 3 brain lobe gene uses char[4] lobe id) [VERIFIED]

### 1.5 The Attention/Decision System

The brain's output is determined by two Winner-Takes-All lobes:

1. **Decision lobe** -- each neuron corresponds to an action (push, pull, approach, retreat, get, drop, speak, sleep, walk left, walk right, etc.). At each brain tick, the neuron with the highest activation determines the creature's current action.

2. **Attention lobe** -- each neuron corresponds to an object category. The neuron with the highest value determines what the creature focuses on.

Combined, these produce behaviour like "push food" (Decision=push, Attention=food category) which causes the creature to eat.

The Decision lobe receives input from the Combination/Concept lobe. In C1, each Decision neuron had 256 connections from the Concept lobe -- 128 excitatory (type 0) and 128 inhibitory (type 1). The SVRule for Decision neurons summed type 0 dendrites and subtracted type 1 dendrites: `state:PLUS:type 0:MINUS:type 1:`.

In C3/DS, with tracts replacing the two-type dendrite system, the connectivity is more flexible but follows the same principle: some tracts carry excitatory signals and others inhibitory.

[CROSS-REFERENCE: See Part II Section 2 for how getSpareNeuron() implements Winner-Takes-All via the "register as spare" SVRule opcode (opcode 31).]

**Source:** https://www.alanzucconi.com/2020/07/27/the-ai-of-creatures/ [VERIFIED]
**Source:** https://creatures.wiki/Brain [VERIFIED]

### 1.6 Brain Tick Processing

Each brain update cycle ("tick") processes all lobes. The default tick interval is 50 milliseconds.

**Per tick, the processing order is:**
1. **Sensory inputs** are written to input lobes (Stimulus Source, Drive, General Sense, Noun, Verb) by the Sensory Faculty.
2. **Each lobe** executes its neurons' update SVRules in order.
3. **Each tract** executes its dendrite update SVRules.
4. **Decision and Attention lobes** use Winner-Takes-All to select outputs.
5. **Motor Faculty** reads the Decision/Attention outputs and initiates the corresponding action/focus.

In C3/DS, each lobe and tract has an `updatetime` field in its gene, controlling how often it updates (measured in some unit relative to brain ticks). The SOUL command can enable/disable individual faculties: Sensory (0), Brain (1), Motor (2), Linguistic (3), Biochemistry (4), Reproductive (5), Expressive (6), Music (7), Life (8).

[CROSS-REFERENCE: See Part II Section 2 for the actual tick implementation -- `c2eBrain::tick()` iterates components sorted by `updatetime`, and components with `updatetime == 0` are skipped. Brain ticks every 4 game ticks per `CreatureAI.cpp` line 98.]

**Source:** https://www.ghostfishe.net/bbw/tutorials/categorical.html [VERIFIED - CAOS docs]
**Source:** https://creatures.wiki/GEN_files [VERIFIED]

---

## 2. SVRule System

### 2.1 What SVRules Are

**State Variable Rules (SVRules)** are the micro-programs that define how each neuron and dendrite processes its inputs. Every neuron has an "init rule" (run once at creation) and an "update rule" (run every tick). Every tract/dendrite also has init and update rules.

In C1/C2, SVRules were simple 8-opcode (C1) or 12-opcode (C2) sequences using a postfix-like notation. They operated on named variables like `state`, `type 0`, `type 1`, `thres`, `chem 0`-`chem 3`, etc.

In C3/DS, SVRules became **full register machines** with:
- 48 bytes per rule (a significant increase from C1's 8 or C2's 12)
- An **accumulator** (working register)
- Multiple **operand types** (input neuron, dendrite, neuron, spare neuron, chemicals, random, literals)
- 68+ opcodes including arithmetic, conditionals, flow control, and specialised neural operations
- Values are floating-point in the range [-1.0, 1.0]

[CROSS-REFERENCE: See Part II Section 4 for the complete opcode implementation in openc2e, including which opcodes are actually implemented vs. UNIMPLEMENTED stubs.]

### 2.2 Design Philosophy

From the original programmer (credited as "Digitalgod" on the wiki, likely a Cyberlife developer):

> "This SVRule system was designed to deal with an interesting problem: How could I specify arbitrary behaviours for my neurons in a way that evolution could freely change, without it generating endless syntax errors in the process? [...] I designed the SVRule system in such a way that EVERY statement you can write in it is legal and meaningful, even if it is not biologically useful."

This is a critical design constraint: the SVRule bytecode is **mutation-safe**. Any random byte sequence is a valid program. If a command mutates to lose its operand, the former operand is reinterpreted as a new command or variable. This robustness enables genetic evolution of neural processing rules.

**Source:** https://creatures.wiki/Brain [VERIFIED]

### 2.3 C1/C2 SVRule Opcodes

| Opcode | C1 | C2 | Name | Description |
|--------|----|----|------|-------------|
| 0 | Y | Y | `<end>` | End of rule |
| 1-4 | Y | Y | `0`, `1`, `64`, `255` | Integer constants |
| 5-8 | Y | Y | `chem 0`-`chem 3` | Brain lobe chemicals (set by receptors) |
| 9 | Y | Y | `state` | Current neuron state |
| 10 | Y | Y | `output` | Current neuron output |
| 11 | Y | Y | `thres` | Threshold |
| 12-13 | Y | Y | `type 0`, `type 1` | Sum of dendrite inputs (weighted: `source * stw/255`) |
| 14-15 | Y | Y | `anded 0`, `anded 1` | AND-gated dendrite sum (0 if any source is 0) |
| 16 | Y | Y | `input` | Current dendrite input signal |
| 17 | Y | Y | `conduct` | Not connected in C1 |
| 18 | Y | Y | `suscept` | Susceptibility to reinforcement |
| 19 | Y | Y | `STW` | Short-term weight |
| 20 | Y | Y | `LTW` | Long-term weight |
| 21 | Y | Y | `strength` | Dendrite strength |
| 22 | Y | Y | `TRUE` | Conditional: execute rest only if previous != 0 |
| 23-27 | Y | Y | `PLUS`, `MINUS`, `TIMES`, `INCR`, `DECR` | Arithmetic ops |
| 22-23 | - | Y | `32`, `128` | Additional constants |
| 25-26 | - | Y | `chem 4`, `chem 5` | Additional brain chemicals |
| 27-29 | - | Y | `leak in`, `leak out`, `curr src leak in` | Back/forward propagation |
| 36 | - | Y | `FALSE` | Conditional: execute rest only if previous == 0 |
| 37-40 | - | Y | `multiply`, `average`, `move twrds`, `random` | Advanced operations |

**Source:** https://creatures.wiki/Brain [VERIFIED]

### 2.4 C3/DS SVRule Opcodes (68+ opcodes)

The C3/DS SVRule system is dramatically more powerful. Key opcodes:

| Opcode | Name | Description |
|--------|------|-------------|
| 0 | `stop` | Halt rule execution |
| 1 | `blank` | Zero the destination |
| 2 | `store in` | Copy accumulator to destination |
| 3 | `load from` | Copy source to accumulator |
| 4-15 | `if` commands | Conditional execution based on accumulator |
| 16-21 | Arithmetic | add, subtract, multiply, divide, etc. |
| 22-23 | `min/max with` | Clamp accumulator |
| 24 | `set tend rate` | Set the rate for `tend to` operations |
| 25 | `tend to` | Move accumulator toward operand at tend rate |
| 26-27 | `load neg/abs` | Load negation or absolute value |
| 28 | `get distance to` | Absolute difference |
| 31 | `register as spare` | Mark neuron as spare (used by Decision/Attention WTA) |
| 32-33 | `bound in [0,1]` / `bound in [-1,1]` | Clamp to range |
| 36 | `Nominal Threshold` | Zero accumulator if below operand |
| 37 | `Leakage Rate` | Set decay rate |
| 38 | `Rest State` | Set rest state |
| 40 | `Persistence` | S(1) = S(0) + ((1-P) * (I(0) - S(0))) |
| 42 | `Winner Takes All` | WTA selection |
| 43-44 | `ST/LT Relax Rate` | Short/long-term weight relaxation |
| 46-49 | `stop/goto if zero/nonzero` | Flow control |
| 50-51 | `divide/multiply, add to neuron input` | Complex arithmetic to neuron input var |
| 52 | `goto line` | Jump |
| 57-62 | Reward/Punish ops | `Reward Threshold`, `Reward Rate`, `Use Reward With`, `Punish Threshold`, `Punish Rate`, `Use Punish With` |
| 63-66 | Preserve/Restore SV | Save/load neuron state variables |

[CROSS-REFERENCE: See Part II Section 4 for the complete implemented opcode table from openc2e source code, which provides the definitive list including opcodes up to 68 and marks several (37-42, 57-62) as UNIMPLEMENTED.]

### 2.5 C3/DS SVRule Operand Types

| Code | Type | Description |
|------|------|-------------|
| 0 | accumulator | The working register itself |
| 1 | input neuron | Source neuron for current dendrite |
| 2 | dendrite | Current dendrite being processed |
| 3 | neuron | Current neuron (or dest neuron for dendrites) |
| 4 | spare neuron | Spare neuron register |
| 5 | random | Random float [0.0, 1.0] |
| 6 | source chemical | Chemical from source context |
| 7 | chemical | A specific chemical level (chemical# specified) |
| 8 | destination chemical | Chemical from destination context |
| 9 | zero | Literal 0.0 |
| 10 | one | Literal 1.0 |
| 11 | value | Literal [0.0, 1.0] |
| 12 | negative value | Literal [0.0, -1.0] |
| 13 | value x 10 | Literal [0.0, 10.0] |
| 14 | value / 10 | Literal [0.0, 0.1] |
| 15 | value integer | Literal integer [0, 248] |

[CROSS-REFERENCE: See Part II Section 4 for how openc2e resolves these operand types, including that types 6 (source chemical) and 8 (destination chemical) are UNIMPLEMENTED.]

**Source:** https://creatures.wiki/Brain [VERIFIED]

### 2.6 SVRule Encoding in Genome

In C3/DS genome files (version 3):
- Brain Lobe genes contain two 48-byte SVRule arrays: `initrule` and `updaterule`
- Brain Tract genes also contain two 48-byte SVRule arrays: `initrule` and `updaterule`
- Each SVRule byte pair encodes an opcode and its operand

[CROSS-REFERENCE: See Part II Section 4 for the binary format detail: each SVRule = 48 bytes = 16 operations x 3 bytes (opcode, operand type, operand data).]

**Source:** https://creatures.wiki/GEN_files [VERIFIED]

---

## 3. Dendrite System

### 3.1 C1/C2 Dendrites (Type 0 and Type 1)

In C1/C2, dendrites live inside lobes. Each lobe defines two **dendrite types**:
- **Type 0** -- connects to one source lobe
- **Type 1** -- connects to another source lobe

Each dendrite has:
- **Source lobe** and neuron range (min/max)
- **Spread** and **fanout** (how connections are distributed)
- **Long-Term Weight (LTW)** -- baseline weight, initialised from gene (minltw to maxltw range)
- **Short-Term Weight (STW)** -- current effective weight, relaxes toward LTW
- **Strength** -- determines if dendrite survives or atrophies
- **Migration** flag -- whether weak dendrites detach and reattach elsewhere
- **Susceptibility** -- how sensitive to reinforcement signals

The dendrite signal value is calculated as: `value = source_neuron_output * (STW / 255)`

The `type 0` and `type 1` SVRule operands return the **sum** of all dendrites of that type.

### 3.2 Weight Dynamics

STW is updated according to: `stw = ltw + (susceptibility/255) * reinforcement`

STW and LTW relax toward each other over time, with STW moving faster. This creates a system where:
- Short-term learning adjusts STW rapidly
- LTW gradually shifts to reflect long-term patterns
- STW decays back toward LTW if not reinforced

[CROSS-REFERENCE: See Part II Section 4 "Long-term Relax Rate (Opcode 44)" for the actual Hebbian learning implementation in openc2e.]

### 3.3 Atrophy and Migration

Dendrites have a **strength** value. Unused/unreinforced dendrites lose strength over time. When strength drops to zero, the dendrite dies. If the **migration** flag is set, instead of dying, the dendrite detaches and reattaches to a different source neuron -- this is how the brain self-organises.

The brain chemicals **ConASH** (Concept layer Atrophy Suppressing Hormone) and **DecASH1/DecASH2** (Decision layer ASH for type 0 and type 1 dendrites) are emitted by "loose" (unallocated) neurons/dendrites. These chemicals suppress further atrophy, maintaining a reserve of unallocated connections for learning new associations.

[CROSS-REFERENCE: See Part II Section 5 for the migration implementation in openc2e, where loose dendrites (strength `variables[7] == 0.0`) seek new connections by finding the neuron with the highest NGF value.]

### 3.4 C3/DS Tracts

In C3/DS, dendrites are organised into **tracts** rather than the two-type system. Each tract gene defines:

| Field | Type | Description |
|-------|------|-------------|
| updatetime | uint16be | How often the tract updates |
| srclobe | char[4] | Source lobe ID |
| srclobe_lowerbound | uint16be | First neuron in source range |
| srclobe_upperbound | uint16be | Last neuron in source range |
| srclobe_numconnections | uint16be | Number of connections per source neuron |
| destlobe | char[4] | Destination lobe ID |
| destlobe_lowerbound | uint16be | First neuron in dest range |
| destlobe_upperbound | uint16be | Last neuron in dest range |
| destlobe_numconnections | uint16be | Number of connections per dest neuron |
| migrates | uint8 | Whether dendrites can migrate |
| num_random_connections | uint8 | Number of random initial connections |
| srcvar | uint8 | Which source neuron variable to read |
| destvar | uint8 | Which dest neuron variable to write |
| initrulealways | uint8 | Whether init rule runs always or once |
| initrule | uint8[48] | SVRule for initialisation |
| updaterule | uint8[48] | SVRule for per-tick update |

This is far more expressive than C1/C2's hardcoded two-dendrite-type system.

**Source:** https://creatures.wiki/GEN_files [VERIFIED]
**Source:** https://creatures.wiki/Brain [VERIFIED]

---

## 4. Biochemistry System (C3/DS)

### 4.1 Chemical System Overview

C3/DS has **256 chemical slots** (numbered 0-255). Chemicals are arbitrary -- they have no innate properties. Their effects are entirely determined by genetics (reactions, receptors, emitters). Chemical concentrations are floating-point values that decay over time according to genetically-defined half-lives.

[CROSS-REFERENCE: See Part II Section 6 for the openc2e implementation: `float chemicals[256]` in `c2eCreature`, with chemical 0 always ignored (null chemical).]

### 4.2 C3/DS Chemical Groups

| Range | Category | Examples |
|-------|----------|----------|
| 1-13 | Digestive | Lactate, Pyruvate, Glucose, Glycogen, Starch, Fatty acid, Cholesterol, Triglyceride, Adipose tissue, Fat, Muscle tissue, Protein, Amino acid |
| 17-18 | Movement | Downatrophin, Upatrophin (gait chemicals) |
| 24-26 | Waste | Dissolved CO2, Urea, Ammonia |
| 29-36 | Respiratory | Air, Oxygen, Water, Energy, ATP, ADP |
| 39-54 | Reproductive | Arousal potential, Libido lowerer, Opposite sex pheromone, Oestrogen, Progesterone, Testosterone, Inhibin |
| 66-81 | Toxins | Heavy metals, Cyanide, Belladonna, Geddonase, Glycotoxin, Sleep toxin, Fever toxin, Histamine A/B, Alcohol, ATP decoupler, Carbon monoxide, Fear toxin, Muscle toxin |
| 82-89 | Antigens | Antigen 0-7 (bacterial infections) |
| 90 | Wounded | Injury measure (lethal at high levels) |
| 92-100 | Medicinal | Medicine one, Anti-oxidant, Prostaglandin, EDTA, Sodium thiosulphate, Arnica, Vitamin E, Vitamin C, Antihistamine |
| 102-109 | Antibodies | Antibody 0-7 |
| 112-129 | Regulatory | Anabolic steroid, Pistle, Insulin, Glycolase, Dehydrogenase, Adrenaline, Grendel nitrate, Ettin nitrate, Protease, Activase, Life, Injury, Stress, Sleepase |
| 131-145 | Drive backups | Backup copies of all 15 drives (for suppression) |
| 148-162 | Drive chemicals | Pain, Hunger(P/C/F), Coldness, Hotness, Tiredness, Sleepiness, Loneliness, Crowded, Fear, Boredom, Anger, Sex Drive, Comfort |
| 165-184 | CA smell gradients | Sound, Light, Heat, Water, Nutrient, Protein, Carb, Fat, Flowers, Machinery, Egg, Norn/Grendel/Ettin smell, Home smells, Gadget |
| 187-195 | Stress chemicals | Per-drive stress indicators |
| 198-213 | Brain chemicals | Disappointment, Up/Down/Exit/Enter/Wait (navigation), Reward, Punishment, unused 206-211, Pre-REM, REM |

**Total actively used:** approximately 150+ chemicals (many slots unused/reserved)

[CROSS-REFERENCE: See Part II Section 6 for hardcoded chemical references in openc2e: ATP=35, ADP=36, Injury=127, Pre-REM=212, REM=213, drives at drive_id+148.]

**Source:** https://creatures.fandom.com/wiki/C3_Chemical_List [VERIFIED]

### 4.3 Half-Life / Decay System

Every chemical has a genetically-defined **half-life** -- the time for its concentration to decay to half. The half-life gene (type 1, subtype 3) is the longest gene in a creature, containing 256 uint8 values (one per chemical slot).

The decay values map to discrete time periods (not linear). As of C2+, values between defined steps are treated as the nearest lower defined value. Common mutations in the half-life gene (particularly for "Life" chemical #125 or "Ageing" chemicals) produce longer-lived creatures.

[CROSS-REFERENCE: See Part II Section 6 for the actual half-life formula in openc2e: `rate = 1.0 - pow(0.5, 1.0 / pow(2.2, (halflives[x] * 32.0) / 255.0))`.]

**Source:** https://creatures.wiki/Biochemistry [VERIFIED]

### 4.4 Receptors

**Receptors** monitor chemical levels and alter brain/organ behaviour in response. Each receptor gene defines:
- **Organ/tissue/locus** -- what to modify
- **Chemical** -- what to monitor
- **Threshold** -- minimum chemical level before receptor activates
- **Nominal** -- baseline value when chemical is below threshold
- **Gain** -- scaling factor
- **Flags** -- analog vs digital; output reduces or increases with stimulation

**Brain receptor loci** (what chemicals can modify in the brain):

| Locus | What it controls |
|-------|-----------------|
| 0 | Threshold |
| 1 | Leakage rate |
| 2 | Rest state |
| 3 | Type 0 relax susceptibility |
| 4 | Type 0 relax STW |
| 5 | Type 0 relax LTW |
| 6 | Type 0 strength gain rate |
| 7 | Type 0 strength loss rate |
| 8-12 | Type 1 equivalents of 3-7 |
| 13-16 | Brain chemicals 0-3 (in C1) |
| 17+ | Individual neuron states |

In C3, receptors were extended to bind to **reaction rate** and **organ clock rate** loci.

**Source:** https://creatures.wiki/Biochemistry [VERIFIED]

### 4.5 Emitters

**Emitters** (chemoemitters) release chemicals into the bloodstream based on **locus** values. Processing occurs at intervals defined by a sample rate.

**Brain emitter loci:**

| Locus | Description |
|-------|-------------|
| Activity (0) | Number of neurons firing in a lobe |
| Numloose0 (1) | Number of loose type-0 dendrites/neurons |
| Numloose1 (2) | Number of loose type-1 dendrites/neurons |
| Output (n-3) | Output of specific neuron n |

Two types:
- **Analog** emitters: release chemical proportional to signal: `(signal - threshold) * (gain/255)` if signal > threshold, else 0
- **Digital** emitters: release fixed amount when signal exceeds threshold: `gain` if signal > threshold, else 0

**Source:** https://creatures.wiki/Biochemistry [VERIFIED]

### 4.6 Neuroemitters (C3/DS only)

**Neuroemitters** are a C3/DS addition. They release up to 4 chemicals when specific neurons in specific lobes fire. Unlike standard emitters (which monitor loci), neuroemitters are triggered directly by neuron activation.

Gene format: specifies 3 lobe/neuron pairs as triggers, a rate, and 4 chemical/amount pairs.

The standard C3 norn genome has one neuroemitter: it releases Adrenaline, Fear, and Crowded when the norn perceives a Grendel.

**Source:** https://creatures.wiki/Brain [VERIFIED]
**Source:** https://creatures.wiki/Biochemistry [VERIFIED]

### 4.7 Drives and Their Chemical Basis

C3/DS drives are represented as chemicals (slots 148-162). The Drive lobe neurons mirror these chemical concentrations. Drive chemicals produce **stress** chemicals (slots 187-195) when sustained at high levels for too long.

**C3/DS Drives:**

| Chemical # | Drive | Notes |
|-----------|-------|-------|
| 148 | Pain | |
| 149 | Hunger for Protein | C3 split hunger into 3 (vs C1's single hunger) |
| 150 | Hunger for Carbohydrate | |
| 151 | Hunger for Fat | |
| 152 | Coldness | |
| 153 | Hotness | |
| 154 | Tiredness | |
| 155 | Sleepiness | |
| 156 | Loneliness | |
| 157 | Crowdedness | |
| 158 | Fear | |
| 159 | Boredom | |
| 160 | Anger | |
| 161 | Sex Drive | |
| 162 | Comfort Drive | New in C3 |

**Drive backup chemicals** (131-145) allow drives to be temporarily suppressed for higher-priority actions.

### 4.8 How Hormones/Neurotransmitters Modulate Neural Activity

The brain-biochemistry interaction is bidirectional:

**Biochemistry -> Brain:**
- Receptors modify brain lobe parameters (threshold, leakage, rest state, susceptibility, weight rates) based on chemical levels
- Drive chemicals are directly read into Drive lobe neurons
- Brain chemicals (chem 0-5 in SVRules) can be set by receptors and read by SVRules
- Adrenaline modulates fight-or-flight behaviour
- Grendel/Ettin nitrate influences friend-or-foe decisions

**Brain -> Biochemistry:**
- Emitters release chemicals based on neural activity
- Neuroemitters release chemicals based on specific neuron activations
- The Decision lobe output triggers motor actions which may cause stimuli
- Stimuli inject chemicals via stimulus genes

[CROSS-REFERENCE: See Part II Section 6 "Brain-Biochemistry Interface" for the locus system that provides `float*` pointers into neuron variables, enabling receptors/emitters to directly modify brain state.]

### 4.9 Reward and Punishment (Learning Chemicals)

The core learning mechanism depends on two chemicals:

| Chemical # | Name | Role |
|-----------|------|------|
| 204 | Reward | Strengthens connections that led to current action |
| 205 | Punishment | Weakens connections that led to current action |

These chemicals are produced by:
- Player patting (reward) or slapping (punishment)
- Stimulus genes triggered by actions (e.g., eating when hungry produces reward)
- Instinct processing during sleep (REM chemicals #212-213)

Both chemicals decay to produce **reinforcement** signal that is read by dendrite SVRules to modify weights.

**Source:** https://creatures.fandom.com/wiki/C3_Chemical_List [VERIFIED]
**Source:** https://creatures.wiki/Biochemistry [VERIFIED]

---

## 5. Genome Format (C3/DS)

### 5.1 File Format

C3/DS genome files use version 3 format:
- **Magic header:** `dna3`
- **Body:** sequence of genes, each prefixed with `gene` marker
- **Footer:** `gend` end marker
- All numbers little-endian unless otherwise specified

### 5.2 Gene Header (Version 3)

| Field | Type | Description |
|-------|------|-------------|
| marker | char[4] | `gene` |
| gene type | uint8 | 0=brain, 1=biochemistry, 2=creature, 3=organ |
| gene subtype | uint8 | Specific gene type |
| gene id | uint8 | Identifier for Genetics Kit |
| generation | uint8 | Generation count |
| switchontime | uint8 | Life stage when gene activates |
| flags | uint8 | Bitfield: 0x1=mutable, 0x2=dupable, 0x4=deletable, 0x8=maleonly, 0x10=femaleonly, 0x20=notexpressed |
| mutability weighting | uint8 | How likely to mutate |
| variant | uint8 | Species variant selector (C3/DS) |

### 5.3 Brain Gene Types

**Brain Lobe Gene (type 0, subtype 0) -- Version 3:**

| Field | Type | Description |
|-------|------|-------------|
| lobe id | char[4] | 4-character lobe identifier |
| updatetime | uint16be | Update frequency |
| x, y | uint16be each | Position in brain grid |
| width, height | uint8 each | Dimensions (neurons = width * height) |
| red, green, blue | uint8 each | Display colour |
| WTA | uint8 | Winner-Takes-All flag |
| tissue | uint8 | Tissue ID for biochemistry |
| initrulealways | uint8 | Whether init rule reruns |
| padding | uint8[7] | Reserved |
| initrule | uint8[48] | SVRule for neuron initialisation |
| updaterule | uint8[48] | SVRule for per-tick neuron update |

[CROSS-REFERENCE: See Part II Section 7 for the C++ struct `c2eBrainLobeGene` that matches this layout exactly.]

**Brain Organ Gene (type 0, subtype 1) -- Version 3 only:**

| Field | Type | Description |
|-------|------|-------------|
| clockrate | uint8 | Processing speed |
| damagerate | uint8 | How fast organ degrades |
| lifeforce | uint8 | Starting health |
| biotickstart | uint8 | When to start ticking |
| atpdamagecoefficient | uint8 | ATP sensitivity |

**Brain Tract Gene (type 0, subtype 2) -- Version 3 only:**

(See section 3.4 for full field list)

### 5.4 Biochemistry Gene Types

| Type | Subtype | Name | Key Fields |
|------|---------|------|------------|
| 1 | 0 | Receptor | organ, tissue, locus, chemical, threshold, nominal, gain, flags |
| 1 | 1 | Emitter | organ, tissue, locus, chemical, threshold, rate, gain, flags |
| 1 | 2 | Reaction | r1_amount, r1_chem, r2_amount, r2_chem, p1_amount, p1_chem, p2_amount, p2_chem, rate |
| 1 | 3 | Half-lives | uint8[256] -- one decay rate per chemical |
| 1 | 4 | Initial Concentration | chemical, amount |
| 1 | 5 | Neuroemitter | 3x(lobe,neuron) triggers, rate, 4x(chem,amount) outputs |

### 5.5 Creature Gene Types (Brain-Relevant)

**Stimulus Gene (type 2, subtype 0):**

| Field | Type | Description |
|-------|------|-------------|
| stimulus | uint8 | Which stimulus number |
| significance | uint8 | How significant |
| input | uint8 | Input source |
| intensity | uint8 | Strength |
| features | uint8 | Flags |
| chemical0-3 | uint8 | 4 chemicals to inject |
| amount0-3 | uint8 | 4 amounts |

**Instinct Gene (type 2, subtype 5):**

| Field | Type | Description |
|-------|------|-------------|
| lobe0, cell0 | uint8 | First input condition (lobe + neuron) |
| lobe1, cell1 | uint8 | Second input condition |
| lobe2, cell2 | uint8 | Third input condition |
| action | uint8 | Required action |
| reinforcement_chemical | uint8 | What chemical to inject |
| reinforcement_amount | uint8 | How much |

Instincts are processed during sleep (REM). They inject reinforcement chemicals when the creature dreams of the specified conditions while performing the specified action.

### 5.6 Mutation Mechanics

Gene flags control which mutations are possible:
- **0x1 (mutable):** Point mutations can alter individual bytes
- **0x2 (dupable):** Gene can be duplicated during reproduction
- **0x4 (deletable):** Gene can be deleted during reproduction

The **mutability weighting** byte (added in version 2+) provides fine-grained control over mutation probability per gene.

**Key note:** In C3/DS, brain structure genes (lobe genes) reportedly do not mutate in standard norn genomes -- "Creatures 3 norns' brains do not mutate." This is a design choice, not an engine limitation. The flags on brain lobe genes are set to prevent mutation.

**Crossover** during reproduction: genes from both parents are interleaved. The genome format supports tracking parent monikers (32 bytes each in version 3) and generation numbers.

**Source:** https://creatures.wiki/GEN_files [VERIFIED]
**Source:** https://creatures.wiki/Brain (re: C3 mutation suppression) [VERIFIED]
**Source:** https://creatures.fandom.com/wiki/Mutation [VERIFIED for general mutation mechanics]

### 5.7 Key Differences from C1/C2 Genome Format

| Feature | C1 | C2 | C3/DS |
|---------|----|----|-------|
| File header | None | `dna2` | `dna3` |
| Brain lobe gene | Fixed fields + 2 dendrite types | Same | Lobe ID (char[4]), tracts separate |
| SVRule size | 8 bytes | 12 bytes | 48 bytes |
| Dendrites | Embedded in lobe gene | Same | Separate Brain Tract genes |
| Brain organ gene | N/A | N/A | New gene type |
| Neuroemitter gene | N/A | N/A | New gene type |
| Variant field | N/A | N/A | Per-gene species variant |
| Mutability weight | N/A | Present | Present |
| Moniker length | 4 bytes | 4 bytes | 32 bytes |

**Source:** https://creatures.wiki/GEN_files [VERIFIED]

---

## 6. Known Failure Modes

### 6.1 One Hour Stupidity Syndrome (OHSS)

**Game:** Creatures 2 (original release)
**Confidence:** HIGH (multiple corroborating community sources)

**Symptoms:** After approximately one hour of play, affected norns' brains "turn to mush." They wallbonk (walk into walls repeatedly), forget how to eat and sleep, and generally become non-functional.

**Root Cause (Lis Morris's analysis):**
An imbalance of **Reward** and **Punishment** brain chemicals. Too much of these chemicals were being generated by norn actions and accumulating in the brain. The net effect was that the brain was being rewarded constantly regardless of whether it was doing something "right." As Lis Morris stated: *"since decisions were being rewarded more or less randomly, any decision was valid in any situation."*

**Contributing Factor (Chris Double's analysis):**
The attention system was also deficient -- norns had no mechanism to prioritise attention based on actual needs. They could not ignore a bouncing ball or disregard player speech in order to go eat when hungry. The attention mechanism lacked drive-based filtering.

**Additional Factor (LummoxJR's analysis):**
The Concept lobe was too small relative to the Perception lobe, limiting the creature's ability to form distinct situational memories.

**Fixes:**
- **Canny Norns** (Lis Morris + Chris Double) -- rebalanced reward/punishment chemistry and improved attention-drive coupling
- **Nova Subterra** (LummoxJR + Chris Double) -- enlarged concept lobe, fixed tiredness/pregnancy issues
- **Washu genome** (LilWashu) -- based partly on Canny Norns
- **Boney Grendels** -- incorporated Canny Norn fixes

**Critical note:** These fix genomes were generally **incompatible** with each other and with the original C2 genome for interbreeding. Crossing different fix genomes typically produced broken offspring due to brain structure mismatches.

**Source:** https://creatures.fandom.com/wiki/OHSS [VERIFIED]

### 6.2 Other Documented Failure Modes

**Wallbonking** -- Creatures walk repeatedly into walls. Can be caused by:
- OHSS (C2)
- Positive reinforcement loop mutations where wallbonking generates reward
- General sense lobe or decision lobe dysfunction
- **Confidence:** HIGH

**Import Deaths** -- Creatures dying upon import. Possibly related to emitter processing: "when a norn is born the emitter is processed at least twice. So even if the sample rate is set to almost never the emitter will be processed [...] Sometimes the emitter is processed when importing a norn."
- **Confidence:** MEDIUM (Chris Double's observation, mechanism not fully confirmed)

**ATP Brain Death** -- In C2/C3/DS, the brain exists as an organ with its own lifeforce. If a creature runs out of ATP, the brain organ's lifeforce drops rapidly (brain lifeforce "decreases to low [...] in seconds"), causing death. This is the primary mechanism of starvation death.
- **Source:** https://creatures.wiki/Biochemistry [VERIFIED]
- **Confidence:** HIGH

**Alcohol Emitter Mutation** -- A common C1 mutation where a DecASH (Atrophy Suppressing Hormone) emitter mutates to emit Alcohol instead, producing a permanently drunk creature.
- **Source:** https://creatures.wiki/Biochemistry [VERIFIED]
- **Confidence:** HIGH

**Glycotoxin Reaction Mutation** -- Chemical reactions can mutate to convert Energy into Glycotoxin (a lethal poison that destroys Glycogen/life force).
- **Source:** https://creatures.wiki/Biochemistry [VERIFIED]
- **Confidence:** HIGH

**C3 Brain Non-Mutation** -- C3/DS norn brain lobe genes are flagged as non-mutable. While this prevents structural brain mutations, it also prevents the kind of brain evolution seen in C1/C2. Multi-lobed creatures (with 36+ lobes observed in C1) cannot occur in C3.
- **Source:** https://creatures.wiki/Brain [VERIFIED]
- **Confidence:** HIGH

---

## 7. CAOS Neural Interface

### 7.1 Brain Commands (BRN: family)

| Command | Syntax | Description |
|---------|--------|-------------|
| BRN: DMPB | `BRN: DMPB` | Dump sizes of binary data for all lobes and tracts |
| BRN: DMPL | `BRN: DMPL lobe_number` | Dump a lobe as binary data |
| BRN: DMPN | `BRN: DMPN lobe_number neuron_number` | Dump a specific neuron as binary data |
| BRN: DMPT | `BRN: DMPT tract_number` | Dump a tract as binary data |
| BRN: DMPD | `BRN: DMPD tract_number dendrite_number` | Dump a specific dendrite as binary data |
| BRN: SETL | `BRN: SETL lobe_number line_number new_value(float)` | Set a lobe SVRule float value |
| BRN: SETN | `BRN: SETN lobe_number neuron_number state_number new_value(float)` | Set a neuron weight/state |
| BRN: SETT | `BRN: SETT tract_number line_number new_value(float)` | Set a tract SVRule float value |
| BRN: SETD | `BRN: SETD tract_number dendrite_number weight_number new_value(float)` | Set a dendrite weight |

### 7.2 Creature Brain Control Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| MIND | `MIND state(int)` | Enable (1) or disable (0) brain processing. Freezes output on current noun/verb. |
| MIND | `MIND` (integer return) | Returns whether brain is being processed |
| MOTR | `MOTR state(int)` | Enable/disable motor faculty (IT object + script firing) |
| ZOMB | `ZOMB state(int)` | Zombify: sever brain-to-motor link (brain runs but output ignored) |
| SOUL | `SOUL facultyId(int) on(int)` | Enable/disable specific faculty: 0=Sensory, 1=Brain, 2=Motor, 3=Linguistic, 4=Biochemistry, 5=Reproductive, 6=Expressive, 7=Music, 8=Life |
| STEP | `STEP facultyId(int)` | Manually step one update of specified faculty |
| SPNL | `SPNL lobe_moniker(str) neuron_id(int) value(float)` | Set input of a specific neuron in a named lobe |
| UNCS | `UNCS state(int)` | Make creature conscious (0) or unconscious (1) |
| VOCB | `VOCB` | Teach creature all vocabulary instantly |

### 7.3 Instinct Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| ADIN | `ADIN verb(int) noun(int) qualifier(float) drive(int)` | Add instinct to brain queue (processed during sleep). Example: `ADIN 3 4 0.5 7` encourages action 3 on category 4 when drive 7 is high |
| DOIN | `DOIN n(int)` | Process N instincts immediately |

### 7.4 Stimulus System

**Stimulus commands** send sensory/chemical signals to creatures:

| Command | Syntax | Description |
|---------|--------|-------------|
| STIM WRIT | `STIM WRIT creature(agent) stimulus(int) strength(float)` | Send stimulus to specific creature. Strength multiplies default. 0=no learning, 1=normal. |
| STIM SHOU | `STIM SHOU stimulus(int) strength(float)` | Stimulus to all creatures hearing OWNR |
| STIM SIGN | `STIM SIGN stimulus(int) strength(float)` | Stimulus to all creatures seeing OWNR |
| STIM TACT | `STIM TACT stimulus(int) strength(float)` | Stimulus to all creatures touching OWNR |
| SWAY WRIT | `SWAY WRIT creature drive adj drive adj drive adj drive adj` | Directly adjust 4 drives of a specific creature |
| URGE WRIT | `URGE WRIT creature noun_id noun_stim verb_id verb_stim` | Urge creature to perform action on noun. Stim >1 forces action (mind control). Use -1 and >1 to unforce. |

**Stimulus numbers** (key ones):

| # | Name | When emitted |
|---|------|-------------|
| 0 | Disappoint | Failed/pointless action |
| 1 | Pointer pat | Player pats creature |
| 3 | Pointer slap | Player slaps creature |
| 7 | Bump | Hit a wall |
| 12 | Quiescent | Periodically while idle |
| 13-15 | Activate1/2, Deactivate | After push/pull/stop actions |
| 16 | Approach | While watching after approach |
| 22 | Sleep | Periodically while sleeping |
| 26 | Eat | After eating |
| 40-43 | Yes/No (pointer/creature) | After hearing yes/no |
| 44 | Aggression | After hitting another creature |
| 45 | Mate | After mating |
| 48-54 | Navigation | Go nowhere/in/out/up/down/left/right |
| 55-74 | Smell peaks | Reached peak of CA smell 0-19 |
| 77-81 | Food type consumed | Plant/fruit/food/animal/detritus |

### 7.5 How External Systems Send Signals to the Brain

1. **Player hand** -- Patting/slapping sends stimulus 1/3. Typing words activates Noun/Verb lobe neurons. ORDR WRIT sends spoken commands.

2. **Agents (machines, food, toys)** -- Scripts emit STIM/SWAY/URGE commands when creatures interact with them. The `stim writ from` C1 pattern and `STIM WRIT`/`STIM SIGN`/`STIM SHOU`/`STIM TACT` C3 commands inject chemicals via stimulus genes.

3. **Other creatures** -- Can pat, slap, speak to, and mate with each other. ORDR SHOU/SIGN/TACT send spoken commands between creatures.

4. **Cellular Automata (CA)** system -- The C3/DS map uses CA for environmental properties (heat, light, nutrients, smells). Creatures sense these through smell gradient chemicals (#165-184) which are written to their brain's sensory inputs.

5. **Engine game variables** -- `engine_synchronous_learning` controls whether creatures learn from all stimuli (default, asynchronous) or only from stimuli caused by the action they're performing on their attention target (synchronous).

**Source:** https://www.ghostfishe.net/bbw/tutorials/categorical.html [VERIFIED]

---

## 8. Source Bibliography (Part I)

### VERIFIED Sources (fetched and read 2026-03-28)

| Source | URL | Covers |
|--------|-----|--------|
| Creatures Wiki - Brain | https://creatures.wiki/Brain | Full brain architecture, SVRules, opcodes |
| Creatures Wiki - Biochemistry | https://creatures.wiki/Biochemistry | Chemical system, emitters, receptors, organs |
| Creatures Wiki - GEN files | https://creatures.wiki/GEN_files | Complete genome binary format |
| Creatures Wiki (Fandom) - C3 Chemical List | https://creatures.fandom.com/wiki/C3_Chemical_List | All C3/DS chemicals with descriptions |
| Creatures Wiki (Fandom) - OHSS | https://creatures.fandom.com/wiki/OHSS | One Hour Stupidity Syndrome |
| Creatures Wiki (Fandom) - Concept lobe | https://creatures.fandom.com/wiki/Concept_lobe | Combination/concept lobe details |
| Creatures Wiki (Fandom) - Decision lobe | https://creatures.fandom.com/wiki/Decision_lobe | Decision/action selection |
| Creatures Wiki (Fandom) - ForF lobe | https://creatures.fandom.com/wiki/ForF_lobe | Friend-or-Foe lobe (C3/DS) |
| Alan Zucconi - The AI of Creatures | https://www.alanzucconi.com/2020/07/27/the-ai-of-creatures/ | Brain architecture overview, learning |
| Creatures Developer Resource (double.nz) | http://double.nz/creatures/brainlobes/differences.htm | C1 vs C2 brain differences |
| CAOS Documentation (ghostfishe.net) | https://www.ghostfishe.net/bbw/tutorials/categorical.html | Full C3/DS CAOS command reference |

### HIGH Confidence Sources (training data, multiple corroborating sources)

| Source | Covers |
|--------|--------|
| Grand, S., Cliff, D., Malhotra, A. (1997) "Creatures: Artificial Life Autonomous Software Agents for Home Entertainment" | Original academic paper on Creatures architecture |
| openc2e project (open-source Creatures engine) | Implementation details of brain/biochemistry |
| Steve Grand's writings/talks | Design philosophy and intent |

### Items Requiring Further Verification

- Exact 4-character lobe IDs in the standard C3/DS norn genome (inferred from format docs, not confirmed against actual genome)
- Complete list of C3/DS lobes and their exact neuron counts (not found in any single source; would require genome analysis)
- Precise details of C3/DS reward/punishment chemical integration with dendrite learning rules (documented for C1, less clear for C3)
- Whether C3/DS uses the same ConASH/DecASH atrophy suppression system as C1, or has a different mechanism via tract genes
- The exact behaviour of several ?? opcodes in the C3/DS SVRule table (44-49, 53-56, etc.)

---

# PART II: openc2e ENGINE -- BRAIN MODULE SOURCE CODE

*Source document: `/research/openc2e-brain-reference.md`*
*Date: 2026-03-28*
*Status: VERIFIED from direct source code reading*

All information in this document was obtained by fetching and reading the actual source files from the openc2e GitHub repository at `https://github.com/openc2e/openc2e` (main branch, commit 2f91af70). Confidence levels are noted inline.

---

## 1. Repository Structure

### Overall Layout [VERIFIED]

```
openc2e/
  CMakeLists.txt              # Root build file (CMake)
  src/
    common/                   # Shared utilities (image, audio, backend, IO, math)
    fileformats/              # File format parsers (genome, pray, sprites, SFC)
      genomeFile.h/.cpp       # <<< GENOME PARSER
      sfc/                    # SFC (C1/C2 save file) format
        CBiochemistry.h       # C1/C2 save biochem struct
        CBrain.h              # C1/C2 save brain struct
        CGenome.h             # C1/C2 save genome struct
        Creature.h            # C1/C2 save creature struct
    openc2e/                  # Main C2e engine code
      creatures/              # <<< ALL CREATURE/BRAIN CODE LIVES HERE
        c2eBrain.h/.cpp       # C3/DS brain implementation
        c2eCreature.h         # C3/DS creature (biochem + brain + loci)
        Creature.h/.cpp       # Base creature class
        CreatureAgent.h/.cpp  # Agent wrapper for creatures
        CreatureAI.cpp        # Brain tick logic, sensory input, decision output
        Biochemistry.cpp      # ALL biochemistry (c1, c2, c2e) in one file
        oldBrain.h/.cpp       # C1/C2 brain implementation
        oldCreature.h         # C1/C2 creature classes
        CompoundCreature.h/.cpp
        SkeletalCreature.h/.cpp
        lifestage.h           # Lifestage enum
      openc2eimgui/
        BrainViewer.h/.cpp    # ImGui brain visualization tool
        CreatureGrapher.h/.cpp
      caos/
        caosVM_creatures.cpp  # CAOS commands for creatures
        caosVM_genetics.cpp   # CAOS commands for genetics
    opencreatures1/           # Separate C1-specific engine (alternative implementation)
      Biochemistry.h/.cpp     # C1-only biochemistry
      objects/Creature.h/.cpp # C1-only creature
    tools/                    # Command-line utilities
      creaturesarchivedumper.cpp
  externals/                  # Third-party deps (SDL2, fmt, imgui, googletest)
```

**Source:** https://github.com/openc2e/openc2e (repo tree API)

### Build System [VERIFIED]

- CMake-based (minimum 3.25)
- C++14 standard
- Key build targets: `openc2e` (main engine), `opencreatures1` (C1 engine), tools
- Dependencies: SDL2, SDL2_mixer, fmt, imgui, googletest, cxxopts, ghc_filesystem, nativefiledialog, zlib, libpng

### How C3/DS Differs from C1/C2 in the Codebase [VERIFIED]

The codebase has a clear split:

| Feature | C1/C2 ("old") | C3/DS ("c2e") |
|---------|---------------|----------------|
| Brain | `oldBrain` class | `c2eBrain` class |
| Creature | `oldCreature` -> `c1Creature` / `c2Creature` | `c2eCreature` |
| Neuron values | `unsigned char` (0-255) | `float` (0.0-1.0) |
| Chemical values | `unsigned char` (0-255) | `float` (0.0-1.0) |
| Lobe connectivity | Fixed 2 dendrite types per lobe | Separate `c2eTract` genes |
| SVRules | 8 or 12 byte rules | 48 byte rules (16 operations) |
| Lobe IDs | Numeric index | 4-char string IDs (e.g., "driv", "verb", "attn") |
| Genome version | `cversion == 1` or `2` | `cversion == 3` |

[CROSS-REFERENCE: Part I Section 1.2 describes the same architectural split from the community documentation perspective. The openc2e codebase confirms and implements those differences.]

---

## 2. Brain Class Interface

### c2eBrain -- Main Brain Class [VERIFIED]

**File:** `src/openc2e/creatures/c2eBrain.h` (lines 126-143)
**Source:** https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/c2eBrain.h

```cpp
class c2eBrain {
protected:
    class c2eCreature* parent;
    std::multiset<c2eBrainComponent*, c2ebraincomponentorder> components;

public:
    std::map<std::string, c2eLobe*> lobes;   // Keyed by 4-char lobe ID
    std::vector<c2eTract*> tracts;

    c2eBrain(c2eCreature* p);
    void processGenes();   // Parse genome, create lobes and tracts
    void tick();           // Update all brain components in order
    void init();           // Initialize all components
    c2eLobe* getLobeById(std::string id);         // e.g., "driv", "verb"
    c2eLobe* getLobeByTissue(unsigned int id);    // By tissue number
    c2eCreature* getParent() { return parent; }
};
```

### Instantiation [VERIFIED]

From `Creature.cpp` (line 314):
```cpp
// In c2eCreature constructor:
brain = new c2eBrain(this);
finishInit();      // calls processGenes() which calls brain->processGenes()
brain->init();     // initializes all lobes and tracts
```

### Brain Tick -- Game Cycle Update [VERIFIED]

From `c2eBrain.cpp` (lines 1029-1035):
```cpp
void c2eBrain::tick() {
    for (auto component : components) {
        if (component->getUpdateTime() != 0)
            component->tick();
    }
}
```

Components are sorted by `updatetime` via the `c2ebraincomponentorder` comparator. Components with `updatetime == 0` are skipped (never updated). Both lobes and tracts are brain components.

### Brain Tick Timing [VERIFIED]

From `CreatureAI.cpp` (line 98):
```cpp
// Brain is ticked every 4 game ticks
if ((ticks % 4) != 0) return;
```

### Input Interface -- Sensory Data Flow [VERIFIED]

From `CreatureAI.cpp` (`c2eCreature::tickBrain`), the input flow is:

1. **Drive lobe ("driv")** receives drive values (hunger, pain, etc.):
   ```cpp
   c2eLobe* drivlobe = brain->getLobeById("driv");
   for (unsigned int i = 0; i < 20 && i < drivlobe->getNoNeurons(); i++) {
       drivlobe->setNeuronInput(i, drives[i]);  // float 0.0-1.0
   }
   ```

2. **Vision lobe ("visn")** receives distance to categorized agents:
   ```cpp
   c2eLobe* visnlobe = brain->getLobeById("visn");
   visnlobe->setNeuronInput(i, distance / parentagent->range);
   ```

3. **Stimulus handling** sets verb, noun, and response lobe inputs:
   ```cpp
   // From handleStimulus():
   verblobe->setNeuronInput(stim.verb_id, stim.verb_amount);
   nounlobe->setNeuronInput(stim.noun_id, stim.noun_amount);
   resplobe->setNeuronInput(stim.drive_id[i], stim.drive_amount[i]);
   ```

**Key input method on lobes:**
```cpp
void c2eLobe::setNeuronInput(unsigned int i, float input);
// Sets neurons[i].input = input
```

### Output Interface -- Decision Extraction [VERIFIED]

From `CreatureAI.cpp` (lines 162-171):
```cpp
// Attention (which category of agent to focus on):
c2eLobe* attnlobe = brain->getLobeById("attn");
attn = attnlobe->getSpareNeuron();  // "spare" = winner neuron index

// Decision (which action to perform):
c2eLobe* decnlobe = brain->getLobeById("decn");
decn = mappinginfo[decnlobe->getSpareNeuron()];  // Mapped via catalogue
```

The `getSpareNeuron()` method returns the index of the neuron that was marked as "spare" by the SVRule's "register as spare" opcode (opcode 31) during the most recent tick. This implements a **winner-takes-all** mechanism -- the neuron whose SVRule triggered "register as spare" becomes the brain's output decision.

The `mappinginfo` vector maps neuron indices to CAOS script numbers via the "Action Script To Neuron Mappings" catalogue tag.

[CROSS-REFERENCE: Part I Section 1.5 describes this WTA mechanism from community docs. The openc2e source confirms the mechanism uses the "register as spare" SVRule opcode.]

### Connection to Creature Class [VERIFIED]

```
Agent (base)
  +-- CreatureAgent (agent wrapper, manages rendering/physics)
       +-- CompoundCreature / SkeletalCreature (visual body)
            +-- Creature (base creature logic)
                 +-- c2eCreature (C3/DS creature with brain + biochemistry)
                      +-- c2eBrain* brain
                      +-- float chemicals[256]
                      +-- float drives[20]
                      +-- std::vector<shared_ptr<c2eOrgan>> organs
                      +-- bioHalfLivesGene* halflives
```

`c2eCreature::tick()` calls:
1. `tickBrain()` -- feeds sensory data, ticks brain, reads decisions
2. `tickBiochemistry()` -- ticks organs, applies half-lives

---

## 3. Lobe Implementation

### c2eLobe Data Structure [VERIFIED]

**File:** `src/openc2e/creatures/c2eBrain.h`

```cpp
struct c2eNeuron {
    float variables[8];   // State variables (SV0-SV7)
    float input;          // Input value, reset to 0.0 after each tick
};

class c2eLobe : public c2eBrainComponent {
protected:
    c2eBrainLobeGene* ourGene;
    c2eSVRule initrule, updaterule;    // Two SVRules per lobe
    std::vector<c2eNeuron> neurons;    // width * height neurons
    unsigned int spare;                // Index of current "spare" neuron

public:
    c2eLobe(c2eBrain* b, c2eBrainLobeGene* g);
    void tick();
    void init();
    void wipe();
    c2eBrainLobeGene* getGene();
    unsigned int getNoNeurons();
    c2eNeuron* getNeuron(unsigned int i);
    unsigned int getSpareNeuron();              // Winner neuron index
    void setNeuronInput(unsigned int i, float input);
    std::string getId();                        // 4-char lobe ID
};
```

### Neuron State Variables [VERIFIED]

Each neuron has 8 float state variables (`variables[0]` through `variables[7]`), plus a float `input`. The meaning of each variable is determined by the SVRules -- the engine does not assign fixed semantics. However, conventionally:

- `variables[0]` is often used as the neuron's primary output/state
- `input` is the external input signal, reset to 0.0f after processing

### Lobe Tick [VERIFIED]

From `c2eBrain.cpp` (lines 367-376):
```cpp
void c2eLobe::tick() {
    for (unsigned int i = 0; i < neurons.size(); i++) {
        if (ourGene->initrulealways && initrule.runRule(
            neurons[i].input, dummyValues, neurons[i].variables,
            neurons[spare].variables, dummyValues, parent->getParent()))
            spare = i;
        if (updaterule.runRule(
            neurons[i].input, dummyValues, neurons[i].variables,
            neurons[spare].variables, dummyValues, parent->getParent()))
            spare = i;
        neurons[i].input = 0.0f;  // Reset input after processing
    }
}
```

**SVRule parameter mapping for lobe ticks:**
- `acc` (accumulator init) = `neurons[i].input`
- `srcneuron[8]` = `dummyValues` (all zeros -- lobes have no "source" neuron)
- `neuron[8]` = `neurons[i].variables` (current neuron's state)
- `spareneuron[8]` = `neurons[spare].variables` (spare neuron's state)
- `dendrite[8]` = `dummyValues` (no dendrites for lobe updates)

### Lobe Initialization [VERIFIED]

```cpp
void c2eLobe::init() {
    inited = true;
    wipe();  // Zero all neuron variables
    for (auto& neuron : neurons) {
        if (!ourGene->initrulealways)
            initrule.runRule(0.0f, dummyValues, neuron.variables,
                           dummyValues, dummyValues, parent->getParent());
        neuron.input = 0.0f;
    }
}
```

---

## 4. SVRule Implementation

### c2eSVRule -- State Variable Rule Engine [VERIFIED]

**File:** `src/openc2e/creatures/c2eBrain.h` (lines 57-71)

```cpp
struct c2erule {
    uint8_t opcode;         // Operation to perform
    uint8_t operandtype;    // Where to get the operand
    uint8_t operanddata;    // Index/data for the operand
    float operandvalue;     // Pre-calculated constant value
};

class c2eSVRule {
protected:
    std::vector<c2erule> rules;   // Up to 16 rules

public:
    void init(uint8_t ruledata[48]);  // Parse from 48 bytes (16 * 3 bytes)
    bool runRule(float acc,
                 float srcneuron[8],
                 float neuron[8],
                 float spareneuron[8],
                 float dendrite[8],
                 c2eCreature* creature);
    // Returns true if "register as spare" was executed
};
```

### SVRule Binary Format [VERIFIED]

Each SVRule is stored as 48 bytes in the genome = 16 operations, each 3 bytes:
- Byte 0: opcode (operation)
- Byte 1: operand type (where to get value)
- Byte 2: operand data (index or constant)

[CROSS-REFERENCE: Part I Section 2.6 describes the same 48-byte, 16-operation format. This confirms consistency between community documentation and the openc2e implementation.]

### Operand Types [VERIFIED]

| Type | Name | Source |
|------|------|--------|
| 0 | Accumulator | Current accumulator value |
| 1 | Input neuron | `srcneuron[operanddata]` (source neuron in tract context) |
| 2 | Dendrite | `dendrite[operanddata]` |
| 3 | Neuron | `neuron[operanddata]` (current neuron's state variable) |
| 4 | Spare neuron | `spareneuron[operanddata]` |
| 5 | Random | `rand_float(0.0, 1.0)` |
| 6 | Source chemical | [UNIMPLEMENTED] |
| 7 | Chemical | `creature->getChemical(operanddata)` (read-only) |
| 8 | Dest chemical | [UNIMPLEMENTED] |
| 9 | Zero | `0.0f` |
| 10 | One | `1.0f` |
| 11 | Value | `operanddata * (1.0 / 248)` |
| 12 | Negative value | `operanddata * (-1.0 / 248)` |
| 13 | Value * 10 | `operanddata * (10.0 / 248)` |
| 14 | Value / 10 | `operanddata * (0.1 / 248)` |
| 15 | Value integer | `(float)operanddata` |

[CROSS-REFERENCE: Part I Section 2.5 lists the same 16 operand types. The descriptions match between community docs and the openc2e implementation. Note that openc2e has types 6 and 8 UNIMPLEMENTED.]

### Opcodes [VERIFIED]

Complete list from `c2eBrain.cpp` (lines 604-967):

| Code | Name | Operation |
|------|------|-----------|
| 0 | Stop | Halt execution |
| 1 | Blank | `*operandpointer = 0.0` |
| 2 | Store in | `*operandpointer = clamp(accumulator)` |
| 3 | Load from | `accumulator = operandvalue` |
| 4-5 | If =, If <> | Conditional (skip next if false) |
| 6-9 | If >, <, >=, <= | Conditional |
| 10-15 | If zero/nonzero/pos/neg/nonpos/nonneg | Operand conditionals |
| 16 | Add | `accumulator += operandvalue` |
| 17 | Subtract | `accumulator -= operandvalue` |
| 18 | Subtract from | `accumulator = operandvalue - accumulator` |
| 19 | Multiply by | `accumulator *= operandvalue` |
| 20 | Divide by | `accumulator /= operandvalue` (safe) |
| 21 | Divide into | `accumulator = operandvalue / accumulator` |
| 22 | Minimum with | `min(accumulator, operandvalue)` |
| 23 | Maximum with | `max(accumulator, operandvalue)` |
| 24 | Set tend rate | `tendrate = operandvalue` |
| 25 | Tend to | `accumulator += tendrate * (operandvalue - accumulator)` |
| 26 | Load negation of | `accumulator = -operandvalue` |
| 27 | Load abs of | `accumulator = abs(operandvalue)` |
| 28 | Distance to | `accumulator = abs(accumulator - operandvalue)` |
| 29 | Flip around | `accumulator = operandvalue - accumulator` |
| 30 | No operation | -- |
| 31 | **Register as spare** | Sets the spare flag (return value) |
| 32 | Bound in [0,1] | `accumulator = clamp(operandvalue, 0.0, 1.0)` |
| 33 | Bound in [-1,1] | `accumulator = clamp(operandvalue, -1.0, 1.0)` |
| 34 | Add and store in | `*operandpointer = clamp(accumulator + operandvalue)` |
| 35 | Tend to and store in | `*operandpointer = clamp(acc + tendrate * (val - acc))` |
| 36 | Nominal threshold | If `acc < operandvalue`: `acc = 0.0` |
| 37-41 | Leakage/rest/gain/persistence/noise | [UNIMPLEMENTED in openc2e; **implemented in stock C3 source SVRule.h:625-645** as doLeakageRate (37), doRestState (38), doInputGainLoHi (39), doPersistence (40), doSignalNoise (41)] |
| 42 | Winner takes all | [UNIMPLEMENTED in openc2e; **implemented in stock C3 source SVRule.h:236-243** as doWinnerTakesAll: per-neuron self-vs-spare comparison] |
| 43 | Short-term relax rate | `stw = operandvalue` |
| 44 | Long-term relax rate | Hebbian-style weight update |
| 45 | Store abs in | `*operandpointer = abs(accumulator)` |
| 46-47 | Stop if zero/nonzero | Conditional halt |
| 48-49 | If zero/nonzero goto | Conditional jump (forward only) |
| 50 | Divide by, add to neuron input | `neuron[1] += clamp(acc / operandvalue)` |
| 51 | Multiply by, add to neuron input | `neuron[1] += clamp(acc * operandvalue)` |
| 52 | Goto line | Forward jump |
| 53-56 | Stop if </>/<=/>= | Conditional halts |
| 57-62 | Reward/punish threshold/rate/use | [UNIMPLEMENTED] |
| 63-66 | Preserve/restore neuron/spare SV | Save/restore variable to slot 4 |
| 67-68 | If negative/positive goto | Conditional jumps |

**Values are clamped to [-1.0, 1.0] on store operations.**

[CROSS-REFERENCE: Part I Section 2.4 lists "68+ opcodes" from community documentation. The openc2e source implements opcodes 0-68, with several marked UNIMPLEMENTED. The opcode descriptions are consistent between sources. See Part VI for verification detail.]

### Long-term Relax Rate (Opcode 44) -- Hebbian Learning [VERIFIED]

```cpp
case 44: // long-term relax rate
    float weight = dendrite[0];
    // Short-term: push weight toward steady state
    dendrite[0] = weight + (dendrite[1] - weight) * stw;
    // Long-term: pull steady state toward weight
    dendrite[1] = dendrite[1] + (weight - dendrite[1]) * operandvalue;
    break;
```

This is the core learning mechanism: `dendrite[0]` is the short-term weight, `dendrite[1]` is the long-term weight. Short-term relaxes toward long-term at rate `stw`, long-term moves toward short-term at the operand rate.

[CROSS-REFERENCE: Part I Section 3.2 describes the same STW/LTW relaxation dynamic from community documentation. The openc2e implementation confirms the mechanism.]

---

## 5. Dendrite/Tract Implementation

### c2eTract [VERIFIED]

```cpp
struct c2eDendrite {
    float variables[8];        // 8 dendrite state variables
    c2eNeuron *source, *dest;  // Pointers to connected neurons
};

class c2eTract : public c2eBrainComponent {
protected:
    c2eBrainTractGene* ourGene;
    c2eSVRule initrule, updaterule;
    std::vector<c2eDendrite> dendrites;
    std::vector<c2eNeuron*> src_neurons, dest_neurons;

    void setupTract();           // Create dendrites after lobes exist
    c2eDendrite* getDendriteFromTo(c2eNeuron*, c2eNeuron*);
    void doMigration();          // Reconnect loose dendrites

public:
    c2eTract(c2eBrain* b, c2eBrainTractGene* g);
    void tick();
    void init();
    void wipe();
    c2eBrainTractGene* getGene();
    unsigned int getNoDendrites();
    c2eDendrite* getDendrite(unsigned int i);
};
```

### Tract Tick [VERIFIED]

```cpp
void c2eTract::tick() {
    if (ourGene->migrates)
        doMigration();

    for (auto& dendrite : dendrites) {
        if (ourGene->initrulealways)
            initrule.runRule(dendrite.source->variables[0],
                           dendrite.source->variables,
                           dendrite.dest->variables,
                           dummyValues,
                           dendrite.variables,
                           parent->getParent());
        updaterule.runRule(dendrite.source->variables[0],
                          dendrite.source->variables,
                          dendrite.dest->variables,
                          dummyValues,
                          dendrite.variables,
                          parent->getParent());
    }
}
```

**SVRule parameter mapping for tract ticks:**
- `acc` = `dendrite.source->variables[0]` (source neuron's first state variable)
- `srcneuron[8]` = `dendrite.source->variables` (source neuron's state)
- `neuron[8]` = `dendrite.dest->variables` (destination neuron's state)
- `spareneuron[8]` = `dummyValues` (unused in tracts)
- `dendrite[8]` = `dendrite.variables` (this dendrite's state)

### Tract Setup -- Dendrite Distribution [VERIFIED]

Tracts connect neurons from a source lobe to a destination lobe. The connectivity pattern depends on gene settings:

1. **Migratory tracts** (`g->migrates`): Dendrites can rewire. One side is constrained (`src_noconnections` or `dest_noconnections` must be non-zero, but not both). Dendrites are randomly distributed.

2. **Non-migratory tracts**: Both sides must have non-zero connection counts. Dendrites are distributed in a round-robin pattern, cycling through source and destination neurons.

### Dendrite Migration [VERIFIED]

Loose dendrites (strength `variables[7] == 0.0`) seek new connections by finding the neuron with the highest NGF (Nerve Growth Factor) value at the variable index specified by `ourGene->srcvar` / `ourGene->destvar`.

---

## 6. Biochemistry Implementation

### Chemical System [VERIFIED]

**C3/DS uses float chemicals (0.0-1.0):**

```cpp
class c2eCreature {
    float chemicals[256];   // 256 chemicals, float 0.0f to 1.0f

    void adjustChemical(unsigned char id, float value);  // Add/subtract, clamped
    float getChemical(unsigned char id);                  // Direct read
};
```

Chemical 0 is always ignored (null chemical). Key hardcoded chemicals:
- **Chemical 35**: ATP (energy)
- **Chemical 36**: ADP (energy waste)
- **Chemical 127**: Injury
- **Chemical 212**: Pre-REM (used in instinct processing)
- **Chemical 213**: REM (used in instinct/dreaming)
- **Chemicals 148+**: Drive chemicals (drive_id + 148)

### Organ System [VERIFIED]

```cpp
class c2eOrgan {
protected:
    c2eCreature* parent;
    organGene* ourGene;
    std::vector<shared_ptr<c2eReaction>> reactions;
    std::vector<c2eReceptor> receptors;
    std::vector<c2eEmitter> emitters;

    float lifeforce, shorttermlifeforce, longtermlifeforce;
    float biotick, clockrate, damagerate, repairrate;
    float energycost, atpdamagecoefficient, injurytoapply;
    unsigned int clockratereceptors, repairratereceptors, injuryreceptors;

public:
    c2eOrgan(c2eCreature* p, organGene* g);
    void tick();
    void processGenes();
    float* getLocusPointer(bool receptor, unsigned char o, unsigned char t,
                           unsigned char l, unsigned int** receptors);
};
```

### Organ Tick Cycle [VERIFIED]

From `Biochemistry.cpp` (lines 604-679):

1. Check if lifeforce > 0.5 (dead organs don't tick)
2. Increment `biotick` by `clockrate`
3. When `biotick >= 1.0f`:
   - Consume ATP (chemical 35), produce ADP (chemical 36)
   - If enough ATP: tick emitters, tick reactions
   - If not enough ATP: apply ATP damage coefficient injury
   - Apply long-term damage (lifeforce decay)
   - Repair injuries
4. Tick receptors (every tick, not just on biotick)
5. Decay short/long-term lifeforce

### Biochemistry Tick Timing [VERIFIED]

From `Biochemistry.cpp` (line 148):
```cpp
void c2eCreature::tickBiochemistry() {
    if ((ticks % 4) != 0) return;  // Only every 4 game ticks
    // tick organs, then process half-lives
}
```

### Receptors [VERIFIED]

```cpp
struct c2eReceptor {
    bioReceptorGene* data;
    bool processed;
    float lastvalue;
    float* locus;            // Pointer to creature locus to write to
    unsigned int* receptors;  // Pointer to receptor count (for averaging)
    float nominal, threshold, gain;  // Pre-calculated from gene
};
```

Processing (simplified):
```
if (digital): f = (chemval > threshold) ? gain : 0.0
else:         f = (chemval - threshold) * gain
if (inverted): f *= -1.0
f += nominal
*locus = clamp(f, 0.0, 1.0)
```

### Emitters [VERIFIED]

```cpp
struct c2eEmitter {
    bioEmitterGene* data;
    unsigned char sampletick;  // Counter for emission rate
    float* locus;              // Pointer to creature locus to read from
    float threshold, gain;     // Pre-calculated from gene
};
```

Processing: read locus value, optionally clear/invert, apply threshold and gain, adjust chemical.

### Reactions [VERIFIED]

```cpp
struct c2eReaction {
    bioReactionGene* data;
    float rate;              // Reversed from gene: 1.0 - (gene_rate / 255.0)
    unsigned int receptors;  // For receptor-controlled rate averaging
};
```

Reactions consume 2 reactant chemicals and produce 2 product chemicals, scaled by a ratio based on the lowest available reactant quantity divided by its required quantity. The rate uses the formula:

```
rate = 1.0 - pow(0.5, 1.0 / pow(2.2, (1.0 - stored_rate) * 32.0))
```

### Half-Lives [VERIFIED]

From `Biochemistry.cpp` (lines 157-170):
```cpp
void c2eCreature::tickBiochemistry() {
    // ... organ ticking ...
    for (unsigned int x = 0; x < 256; x++) {
        if (halflives->halflives[x] == 0) {
            chemicals[x] = 0.0f;  // Special case: instant decay
        } else {
            float rate = 1.0 - powf(0.5, 1.0 / powf(2.2,
                (halflives->halflives[x] * 32.0) / 255.0));
            chemicals[x] -= chemicals[x] * rate;
        }
    }
}
```

### Brain-Biochemistry Interface [VERIFIED]

The interface between brain and biochemistry works through:

1. **Locus system**: Receptors/emitters read/write to `float*` pointers obtained via `getLocusPointer()`. Brain lobe neuron variables are accessible as loci:
   ```cpp
   // From c2eCreature::getLocusPointer(), organ 0 = brain:
   case 0: // brain
       c2eLobe* lobe = brain->getLobeByTissue(t);
       return &lobe->getNeuron(neuronid)->variables[stateno];
   ```

2. **Chemical reads in SVRules**: Operand type 7 reads chemicals directly:
   ```cpp
   case 7: // chemical
       operandvalue = creature->getChemical(rule.operanddata);
   ```

3. **Drive loci** (organ 1, tissue 5): `drives[0..19]` are directly readable/writable.

4. **Sensorimotor loci** (organ 1, tissue 4): Senses (emitters) and involuntary actions (receptors).

---

## 7. Genome Parser -- Brain-Relevant Genes

### Gene Type Hierarchy [VERIFIED]

From `genomeFile.h`:

```
gene (base)
  +-- brainGene (type 0)
  |   +-- c2eBrainLobeGene (type 0, subtype 0, cversion 3)
  |   +-- oldBrainLobeGene (type 0, subtype 0, cversion 1/2)
  |   +-- c2eBrainTractGene (type 0, subtype 2)
  +-- organGene (type 0 subtype 1 for brain, type 3 subtype 0 for biochem)
  +-- bioGene (type 1)
  |   +-- bioReceptorGene (subtype 0)
  |   +-- bioEmitterGene (subtype 1)
  |   +-- bioReactionGene (subtype 2)
  |   +-- bioHalfLivesGene (subtype 3)
  |   +-- bioInitialConcentrationGene (subtype 4)
  |   +-- bioNeuroEmitterGene (subtype 5)
  +-- creatureGene (type 2)
      +-- creatureStimulusGene (subtype 0)
      +-- creatureInstinctGene (subtype 5)
      +-- ... (appearance, pose, gait, etc.)
```

### c2eBrainLobeGene -- C3/DS Lobe Gene [VERIFIED]

```cpp
class c2eBrainLobeGene : public brainGene {
public:
    uint8_t id[4];              // 4-char lobe ID (e.g., "driv", "verb")
    uint16_t updatetime;        // 0 = never update
    uint16_t x, y;              // Position in brain view
    uint8_t width, height;      // Lobe dimensions (neurons = width * height)
    uint8_t red, green, blue;   // Display color
    uint8_t WTA;                // Winner-Takes-All (unused in final game?)
    uint8_t tissue;             // Tissue ID for locus system
    uint8_t initrulealways;     // Flag: run init rule every tick?
    uint8_t spare[7];           // Reserved
    uint8_t initialiserule[48]; // Init SVRule (16 ops * 3 bytes)
    uint8_t updaterule[48];     // Update SVRule (16 ops * 3 bytes)
};
```

[CROSS-REFERENCE: Part I Section 5.3 describes the identical gene layout from community format documentation. The C++ struct matches the documented binary format.]

### c2eBrainTractGene -- C3/DS Tract Gene [VERIFIED]

```cpp
class c2eBrainTractGene : public brainGene {
public:
    uint16_t updatetime;
    uint8_t srclobe[4];             // Source lobe 4-char ID
    uint16_t srclobe_lowerbound;    // First source neuron index
    uint16_t srclobe_upperbound;    // Last source neuron index
    uint16_t src_noconnections;     // Connections per source neuron
    uint8_t destlobe[4];            // Destination lobe 4-char ID
    uint16_t destlobe_lowerbound;   // First dest neuron index
    uint16_t destlobe_upperbound;   // Last dest neuron index
    uint16_t dest_noconnections;    // Connections per dest neuron
    uint8_t migrates;               // Flag: dendrites can rewire
    uint8_t norandomconnections;    // Flag: random connection counts
    uint8_t srcvar;                 // NGF variable index for migration
    uint8_t destvar;                // NGF variable index for migration
    uint8_t initrulealways;         // Flag: run init rule every tick
    uint8_t spare[5];               // Reserved
    uint8_t initialiserule[48];     // Init SVRule
    uint8_t updaterule[48];         // Update SVRule
};
```

### Genome Version Detection [VERIFIED]

```cpp
// File header: "dna" + ASCII version char
// cversion 1 = C1 genome, cversion 2 = C2, cversion 3 = C3/DS
// C1 files can also start with "gene" directly (no "dna" header)
```

### Gene Header [VERIFIED]

Every gene has:
```cpp
struct geneHeader {
    geneFlags flags;       // mutable, dupable, delable, male/female only, etc.
    uint8_t generation;
    lifestage switchontime; // baby=0, child=1, adolescent=2, youth=3, adult=4, old=5, senile=6
    uint8_t mutweighting;   // c2/c2e only
    uint8_t variant;        // c2e only
};
```

The `switchontime` controls when the gene activates during the creature's life. Brain lobe genes with `switchontime = baby` create lobes at birth; genes with later stages add new lobes or modify existing structure at that lifestage.

### How the Genome Builds a Brain at Creature Creation [VERIFIED]

From `Creature.cpp` (lines 276-317):

```
1. c2eCreature constructor:
   - Zero all chemicals, loci, drives
   - Load "Action Script To Neuron Mappings" from catalogue
   - Allocate chosenagents[40]
   - Create brain: brain = new c2eBrain(this)

2. finishInit() -> processGenes():
   - brain->processGenes()  [FIRST -- creates lobes and tracts]
     - Iterates genome->genes
     - For each c2eBrainLobeGene: creates c2eLobe, adds to components + lobes map
     - For each c2eBrainTractGene: creates c2eTract, adds to components + tracts vector
     - Skips genes not matching current lifestage/gender/etc.
   - Creature::processGenes() [creates instincts, sets genus, etc.]
   - For each organ: organ->processGenes() [creates receptors/emitters/reactions]

3. brain->init():
   - Iterates components in update-time order
   - Lobes: wipe neurons, run init SVRule on each neuron
   - Tracts: setupTract() creates dendrites between lobes, run init SVRule on each dendrite
```

---

## 8. "Brain in a Vat" Tool

### What It Is [VERIFIED -- source code + Creatures Wiki]

The original "Brain in a Vat" (BIV) was a Windows tool by Creature Labs for viewing and testing creature brains in isolation -- either connected to a running game or standalone with a genome file.

**In openc2e**, this is implemented through the `_CREATURE_STANDALONE` preprocessor define. When this is defined, the brain-related code compiles without dependencies on the game world (agents, rooms, etc.), allowing standalone brain testing.

### Evidence in Source Code [VERIFIED]

From `CreatureAI.cpp`, the `_CREATURE_STANDALONE` guards:

```cpp
#ifndef _CREATURE_STANDALONE
    chooseAgents();           // Requires game world
    // ... vision lobe input ...
#endif

    brain->tick();            // Always runs

#ifndef _CREATURE_STANDALONE
    // ... attention/decision extraction ...
    // ... script firing ...
#endif
```

### BrainViewer (ImGui) [VERIFIED]

There is also a built-in brain viewer at `src/openc2e/openc2eimgui/BrainViewer.h`:
```cpp
namespace Openc2eImgui {
    void SetBrainViewerOpen(bool);
    void DrawBrainViewer();
}
```
This provides real-time brain visualization within the running engine using Dear ImGui.

### Leveraging for LNN Prototype

The `_CREATURE_STANDALONE` mechanism is directly useful for building a standalone brain test harness. The key code that runs without the game world:

1. Parse a genome file (`genomeFile`)
2. Create a `c2eCreature` (needs mocking of `CreatureAgent` parent)
3. Call `brain->processGenes()` + `brain->init()`
4. Set neuron inputs via `setNeuronInput()`
5. Call `brain->tick()`
6. Read outputs via `getSpareNeuron()` and neuron variable access

---

## 9. Key Data Structures Summary

### Complete Type Reference

```cpp
// === BRAIN TYPES ===

struct c2eNeuron {
    float variables[8];    // State variables SV0-SV7
    float input;           // External input, reset each tick
};

struct c2eDendrite {
    float variables[8];    // State variables (SV0 = weight, SV1 = LTW, SV7 = strength)
    c2eNeuron *source;     // Source neuron pointer
    c2eNeuron *dest;       // Destination neuron pointer
};

struct c2erule {
    uint8_t opcode;        // SVRule operation (0-68)
    uint8_t operandtype;   // Operand source (0-15)
    uint8_t operanddata;   // Index or raw data
    float operandvalue;    // Pre-calculated constant
};

// === BIOCHEMISTRY TYPES ===

struct c2eReaction {
    bioReactionGene* data;
    float rate;            // 1.0 - (gene_rate / 255.0)
    unsigned int receptors;
};

struct c2eReceptor {
    bioReceptorGene* data;
    bool processed;
    float lastvalue;
    float* locus;          // Pointer into creature's loci
    unsigned int* receptors;
    float nominal, threshold, gain;
};

struct c2eEmitter {
    bioEmitterGene* data;
    unsigned char sampletick;
    float* locus;
    float threshold, gain;
};

struct c2eStim {
    int noun_id, verb_id;
    float noun_amount, verb_amount;
    int drive_id[4];
    float drive_amount[4];
    bool drive_silent[4];
};

// === GENOME GENE TYPES (brain-relevant) ===

class c2eBrainLobeGene {
    uint8_t id[4];
    uint16_t updatetime;
    uint16_t x, y;
    uint8_t width, height;
    uint8_t red, green, blue;
    uint8_t WTA, tissue, initrulealways;
    uint8_t spare[7];
    uint8_t initialiserule[48];
    uint8_t updaterule[48];
};

class c2eBrainTractGene {
    uint16_t updatetime;
    uint8_t srclobe[4], destlobe[4];
    uint16_t srclobe_lowerbound, srclobe_upperbound, src_noconnections;
    uint16_t destlobe_lowerbound, destlobe_upperbound, dest_noconnections;
    uint8_t migrates, norandomconnections, srcvar, destvar, initrulealways;
    uint8_t spare[5];
    uint8_t initialiserule[48], updaterule[48];
};

class bioReceptorGene {
    uint8_t organ, tissue, locus, chemical;
    uint8_t threshold, nominal, gain;
    bool inverted, digital;
};

class bioEmitterGene {
    uint8_t organ, tissue, locus, chemical;
    uint8_t threshold, rate, gain;
    bool clear, digital, invert;
};

class bioReactionGene {
    uint8_t reactant[4], quantity[4];
    uint8_t rate;
};

class bioHalfLivesGene {
    uint8_t halflives[256];
};

class bioNeuroEmitterGene {
    uint8_t lobes[3], neurons[3];
    uint8_t rate;
    uint8_t chemical[4], quantity[4];
};

class organGene {
    bool brainorgan;
    uint8_t clockrate, damagerate, lifeforce, biotickstart, atpdamagecoefficient;
};
```

---

## 10. Interface Contract for Brain Replacement

An LNN brain replacement would need to implement this interface to be a drop-in:

### Minimum Required Interface

```cpp
class IBrain {
public:
    // Construction and lifecycle
    IBrain(c2eCreature* parent);
    void processGenes();     // Called at creation and each lifestage change
    void init();             // Called after processGenes()
    void tick();             // Called every 4 game ticks

    // Lobe access (needed by CreatureAI.cpp and stimulus handling)
    ILobe* getLobeById(std::string id);       // "driv", "verb", "noun", "visn",
                                               // "smel", "attn", "decn", "resp"
    ILobe* getLobeByTissue(unsigned int id);  // For locus system

    // Public data (accessed directly by BrainViewer and other code)
    std::map<std::string, ILobe*> lobes;
    std::vector<ITract*> tracts;

    c2eCreature* getParent();
};

class ILobe {
public:
    void setNeuronInput(unsigned int i, float input);  // Range: 0.0-1.0
    unsigned int getSpareNeuron();     // Winner index
    unsigned int getNoNeurons();
    INeuron* getNeuron(unsigned int i);
    void wipe();                       // Reset all neuron state to zero
    std::string getId();               // 4-char lobe ID
    c2eBrainLobeGene* getGene();       // Needed for tissue ID, display coords
};
```

[CROSS-REFERENCE: This interface must be compatible with the ncps API described in Part IV. See Part V for the detailed mapping between this C++ interface and ncps Python objects.]

### Critical Lobe IDs Used by the Engine [VERIFIED]

| ID | Name | Role |
|----|------|------|
| `"driv"` | Drive | Receives 20 drive values as input |
| `"verb"` | Verb | Receives verb stimuli |
| `"noun"` | Noun | Receives noun stimuli |
| `"visn"` | Vision | Receives distance-to-agent data |
| `"smel"` | Smell | Receives smell data [UNIMPLEMENTED input] |
| `"attn"` | Attention | Output: spare neuron = attended category |
| `"decn"` | Decision | Output: spare neuron = chosen action |
| `"resp"` | Response | Receives reinforcement signals (drive changes) |

[CONTRADICTION: Part I Section 1.4 lists lobe IDs as "detn" for Decision and "stim" for Stimulus Source and "sens" for General Sense. The openc2e source code uses "decn" for Decision (Part II Section 2). The engine code also references "visn" (vision), "smel" (smell), and "resp" (response) lobes which are NOT listed in Part I's lobe table. See Part VI for resolution.]

### Chemical Access Needed by Brain [VERIFIED]

The brain reads chemicals through SVRule operand type 7:
```cpp
creature->getChemical(rule.operanddata)
```
This is read-only from the brain's perspective. The biochemistry system is the writer.

### Key Timing [VERIFIED]

- **Game tick**: base unit
- **Brain tick**: every 4 game ticks
- **Biochem tick**: every 4 game ticks
- **Brain components**: sorted by `updatetime`, each ticked in order
- **Components with `updatetime == 0`**: never ticked

---

## 11. Implementation Completeness Notes

### What openc2e Has Implemented [VERIFIED]

- Core lobe/tract/dendrite structure
- SVRule execution (most opcodes)
- Dendrite migration (basic implementation, marked as "guesswork")
- Biochemistry: reactions, receptors, emitters, half-lives, organs
- Instinct processing during dreaming
- Locus system connecting brain to biochemistry
- Gene parsing for all C1/C2/C3/DS gene types

### What Is Marked TODO/Unimplemented [VERIFIED]

**Scope (corrected 2026-04-26):** these gaps are openc2e-specific. Stock C3 1999 source implements all of the following; the missing functionality only manifests when running on openc2e.

- SVRule opcodes 37-42 (leakage rate, rest state, input gain, persistence, signal noise, winner takes all). Stock C3: SVRule.h:625-645, 236-243.
- SVRule opcodes 57-62 (reward/punish threshold/rate/chemicalIndex). Stock C3: SVRule.h:508-525.
- Operand types 6 and 8 (source/destination chemical). Stock C3: SVRule.h:321, 327.
- Smell lobe input
- Situation and detail lobe inputs
- Proper agent selection algorithm (currently random)
- Brain organ handling (creates but doesn't specially process the brain organ gene)
- Various timing details marked with "TODO: correct?"

### Source Citations

All file contents were fetched directly from:
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/c2eBrain.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/c2eBrain.cpp`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/c2eCreature.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/Creature.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/Creature.cpp`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/CreatureAI.cpp`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/Biochemistry.cpp`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/oldBrain.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/oldCreature.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/fileformats/genomeFile.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/fileformats/genomeFile.cpp`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/creatures/lifestage.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/src/openc2e/openc2eimgui/BrainViewer.h`
- `https://raw.githubusercontent.com/openc2e/openc2e/main/CMakeLists.txt`
- `https://api.github.com/repos/openc2e/openc2e/git/trees/main?recursive=1`
- `https://creatures.fandom.com/wiki/Openc2e`
- `https://creatures.fandom.com/wiki/Brain_in_a_Vat`

Confidence: VERIFIED for all source code (fetched and read directly). Creatures Wiki content cross-referenced against source.

---

# PART III: LIQUID NEURAL NETWORKS -- THEORY & ARCHITECTURE

*Source document: `/reference-liquid-neural-networks.md`*
*Research compiled: 2026-03-28*
*Sources verified via web fetch (firecrawl) and academic search (Scholar Gateway)*

---

## 1. Liquid Time-Constant (LTC) Networks -- Core Theory

### 1.1 Origin and Biological Inspiration

LTC Networks were introduced by Ramin Hasani, Mathias Lechner, Alexander Amini, Daniela Rus, and Radu Grosu. The work was published at AAAI 2021 (Thirty-Fifth AAAI Conference on Artificial Intelligence).

**Source:** Hasani et al., "Liquid Time-constant Networks," AAAI 2021, arXiv:2006.04439
**Confidence:** VERIFIED (fetched arxiv abstract and MIT News article directly)

The biological inspiration comes directly from the nervous system of **Caenorhabditis elegans (C. elegans)**, a microscopic nematode worm with exactly **302 neurons** in its nervous system. Despite this tiny neuron count, C. elegans generates "unexpectedly complex dynamics" -- it can navigate, forage, mate, and respond to environmental stimuli. Hasani "coded his neural network with careful attention to how C. elegans neurons activate and communicate with each other via electrical impulses."

**Source:** MIT News, "Liquid machine-learning system adapts to changing conditions," Jan 28, 2021
**Confidence:** VERIFIED (fetched https://news.mit.edu/2021/machine-learning-adapts-0128)

### 1.2 The ODE Formulation of an LTC Cell

An LTC neuron's state x_i(t) evolves according to the following ordinary differential equation (ODE):

```
dx_i/dt = -(1/tau_i + SUM_j[ w_ij / C_m_i * sigma(x_j) ]) * x_i
          +(x_leak_i / tau_i + SUM_j[ w_ij / C_m_i * sigma(x_j) * E_ij ])
```

Where:
- `x_i(t)` = state (membrane potential) of neuron i at time t
- `tau_i` = base time constant of neuron i (passive membrane time constant)
- `w_ij` = synaptic weight from neuron j to neuron i
- `C_m_i` = membrane capacitance of neuron i
- `sigma(x_j)` = sigmoidal synapse activation: `1 / (1 + exp(-gamma_ij * (x_j - mu_ij)))`
- `gamma_ij` = slope parameter of the sigmoid for the synapse from j to i
- `mu_ij` = threshold/shift parameter of the sigmoid for the synapse from j to i
- `x_leak_i` = resting potential (leak potential) of neuron i
- `E_ij` = reversal synaptic potential from neuron j to neuron i

**Source:** Hugo Cisneros's notes on Lechner et al. 2020, which present the ODE directly from the paper
**Confidence:** VERIFIED (fetched https://hugocisneros.com/notes/lechnerneuralcircuitpolicies2020/)

This can be rewritten more compactly. Defining the effective input-dependent time constant:

```
tau_eff_i = 1 / (1/tau_i + SUM_j[ w_ij / C_m_i * sigma(x_j) ])
```

The ODE becomes:

```
dx_i/dt = (-x_i + f_i(x, I)) / tau_eff_i
```

where `f_i` represents the driving function incorporating leak potential and reversal potentials. The key insight is that **tau_eff depends on the input** -- it is "liquid" (varying).

[CROSS-REFERENCE: See Part IV Section 2.4 for how the ncps LTCCell implements this ODE with learnable parameters `gleak`, `vleak`, `cm`, `w`, `sigma`, `mu`, `erev`. The ODE formulation in Part III matches the implementation parameters in Part IV -- confirmed consistent.]

### 1.3 How Time Constants Work

**What they represent:** The time constant tau controls how quickly a neuron responds to input. A large tau means slow response (long memory), a small tau means fast response (quick forgetting). In biological neurons, this corresponds to the RC time constant of the membrane (resistance times capacitance).

**How they are computed:** In LTC networks, the effective time constant is NOT fixed -- it is modulated by the incoming synaptic activity. When other neurons are strongly active (large sigma(x_j)), the effective time constant decreases (faster response). When inputs are weak, the effective time constant is dominated by the base tau_i (slower, more passive behavior).

```
tau_effective = 1 / (1/tau_base + input_dependent_term)
```

This means:
- Strong input --> smaller effective tau --> neuron responds faster
- Weak input --> tau approaches tau_base --> neuron responds slowly
- The network adaptively adjusts its temporal dynamics based on input content

**Source:** ncps.readthedocs.io quickstart documentation; Hasani et al. 2021 abstract
**Confidence:** VERIFIED (fetched ncps docs) + HIGH (corroborated across multiple sources)

### 1.4 Input-Dependent Time Constant Mechanism

The "liquid" in Liquid Time-Constant refers specifically to this mechanism. From the ncps documentation:

> "The term liquid time-constant comes from the property of LTCs that their timing behavior is adaptive to the input (how fast or slow they respond to some stimulus can depend on the specific input)."

This is fundamentally different from standard RNNs where temporal dynamics are fixed after training. In LTCs:

1. The sigmoidal synapses sigma(x_j) gate the influence of presynaptic neurons
2. These gated signals directly modulate the time constant in the denominator
3. As inputs change, the speed of the dynamical system changes
4. This creates a form of **continuous-time attention** -- the network allocates different temporal resolution to different inputs

**Source:** ncps.readthedocs.io quickstart
**Confidence:** VERIFIED (fetched directly)

### 1.5 How LTC Differs from Standard RNNs, LSTMs, GRUs

| Property | Standard RNN | LSTM | GRU | LTC |
|---|---|---|---|---|
| Time model | Discrete steps | Discrete steps | Discrete steps | Continuous-time ODE |
| Time constant | None (implicit) | Learned gates (fixed after training) | Learned gates (fixed after training) | Input-dependent, varies at inference |
| Dynamics | Fixed nonlinearity | Fixed gate structure | Fixed gate structure | ODE with liquid time constants |
| Solver needed | No | No | No | Yes (numerical ODE solver) |
| Biological basis | Loose analogy | No direct basis | No direct basis | Direct from C. elegans neuroscience |
| Post-training adaptation | No | No | No | Yes (time constants adapt to input) |
| Bounded behavior | Not guaranteed | Partially (cell state can grow) | Partially | Provably stable and bounded |
| Interpretability | Black box | Somewhat (gate inspection) | Somewhat | Higher (individual neuron dynamics inspectable) |

Key differentiators:
1. **Continuous-time:** LTCs are defined by ODEs, not discrete update rules. They can handle irregular time intervals natively.
2. **Adaptive after training:** The dynamics change based on input at inference time, not just during training.
3. **Provably bounded:** The bounded weight property prevents unbounded state growth.
4. **Small and expressive:** "Everyone talks about scaling up their network. We want to scale down, to have fewer but richer nodes." -- Hasani, MIT News

**Source:** MIT News article; paper abstracts; ncps documentation
**Confidence:** HIGH (multiple corroborating sources)

### 1.6 Bounded Weight Property and Gradient Stability

From the AAAI 2021 paper abstract: "These neural networks exhibit stable and bounded behavior."

The bounded behavior arises from the structure of the ODE. The key mathematical property is:

1. The effective time constant is always positive (sum of positive terms in denominator)
2. The sigmoid activation sigma() is bounded in [0, 1]
3. The reversal potentials E_ij bound the equilibrium points of the system
4. The system is a **linear first-order dynamical system modulated by nonlinear gates** -- the linearity in x_i ensures the state cannot explode

The state x_i is attracted toward a weighted combination of E_ij values (reversal potentials), which are bounded learned parameters. This means:
- The hidden state cannot grow unboundedly (unlike vanilla RNNs)
- Gradient explosion is structurally prevented
- Long-term stability is guaranteed by construction, not by gradient clipping or other heuristics

**Source:** Paper abstract (VERIFIED from arxiv); structural analysis from ODE form
**Confidence:** HIGH (paper claims verified; mathematical argument follows from ODE structure)

### 1.7 Key Claims and Results from the AAAI 2021 Paper

From the paper abstract and MIT News:

1. **Superior expressivity:** LTCs "yield superior expressivity within the family of neural ordinary differential equations" as measured by trajectory length in latent space
2. **Universal approximation:** "LTCs are universal approximators and implement causal dynamical models" (ncps docs)
3. **Improved time-series prediction:** "It edged out other state-of-the-art time series algorithms by a few percentage points in accurately predicting future values in datasets, ranging from atmospheric chemistry to traffic patterns" (MIT News)
4. **Small computational footprint:** The network's small size means it completed tests "without a steep computing cost"
5. **Noise robustness:** "more resilient to unexpected or noisy data, like if heavy rain obscures the view of a camera on a self-driving car"
6. **Interpretability:** "Thanks to Hasani's small number of highly expressive neurons, it's easier to peer into the 'black box' of the network's decision making"

**Source:** MIT News (VERIFIED); arxiv abstract (VERIFIED)
**Confidence:** VERIFIED

---

## 2. Closed-form Continuous-depth (CfC) Models

### 2.1 Motivation: The ODE Solver Bottleneck

The major practical limitation of LTC networks is that computing their output requires a numerical ODE solver at each timestep. From the CfC paper abstract:

> "Continuous-time neural processes are performant sequential decision-makers that are built by differential equations (DE). However, their expressive power when they are deployed on computers is bottlenecked by numerical DE solvers."

The CfC paper directly addresses this: "Here, we show it is possible to closely approximate the interaction between neurons and synapses -- the building blocks of natural and artificial neural networks -- constructed by liquid time-constant networks (LTCs) efficiently in closed-form."

**Source:** Hasani et al., "Closed-form Continuous-time Neural Models," Nature Machine Intelligence 4, 992-1003 (2022), arXiv:2106.13898
**Confidence:** VERIFIED (fetched arxiv abstract)

### 2.2 How CfC Relates to LTC

CfC is a **closed-form approximation** of the LTC ODE. The key insight is that the integral appearing in the LTC dynamics can be tightly bounded and approximated without requiring an iterative numerical solver.

From the abstract: "We compute a tightly-bounded approximation of the solution of an integral appearing in LTCs' dynamics, that has had no known closed-form solution so far."

The relationship:
- LTC = the full ODE-based model, solved numerically
- CfC = a closed-form approximation of the same dynamics
- CfC preserves the "liquid" property (input-dependent time constants)
- CfC eliminates the ODE solver dependency

**Source:** CfC arxiv abstract (VERIFIED)
**Confidence:** VERIFIED

### 2.3 The CfC Cell Equations (Implementation-Ready)

The CfC cell computes the hidden state update as follows. Based on the SignalPop programmer's walkthrough and the paper's Figure 4:

**Architecture of a CfC Cell:**

```
Inputs: x (current input concatenated with previous hidden state h_{t-1})
        ts (elapsed time since last update)

Step 1 -- Backbone:
    backbone_input = concat(input, h_{t-1})
    x1 = backbone_input
    for each backbone layer:
        x1 = activation(Linear(x1))

Step 2 -- Head Networks:
    ff1 = tanh(Linear_h(x1))       # "h" head -- represents one solution extreme
    ff2 = tanh(Linear_g(x1))       # "g" head -- represents the other solution extreme
    t_a = Linear_timeA(x1)         # time coefficient A
    t_b = Linear_timeB(x1)         # time coefficient B

Step 3 -- Time-Gated Interpolation:
    t_interp = sigmoid(t_a * ts + t_b)    # sigmoid time gate
    h_new = (1 - t_interp) * ff1 + t_interp * ff2
```

**The key equation is:**

```
h(t) = (1 - sigma(A*t + B)) * h_gate(x) + sigma(A*t + B) * g_gate(x)
```

Where:
- `sigma` = sigmoid function
- `A` = learned time coefficient (Linear_timeA applied to backbone output)
- `B` = learned time bias (Linear_timeB applied to backbone output)
- `t` = elapsed time (ts)
- `h_gate(x)` = tanh of a linear projection of backbone output (ff1)
- `g_gate(x)` = tanh of a linear projection of backbone output (ff2)

**Interpretation:** The CfC cell interpolates between two nonlinear functions (ff1 and ff2) using a sigmoid gate that depends on time. The "liquid" property is preserved because A and B are functions of the input (computed through the backbone), making the time-gating input-dependent.

[CROSS-REFERENCE: See Part IV Section 2.1 and 2.3 for how the ncps CfCCell implements this. The three modes ("default", "pure", "no_gate") correspond to different variants of this equation.]

**Source:** SignalPop "Closed-form Continuous-time Liquid Neural Net Models -- A Programmer's Perspective" (VERIFIED, fetched full article)
**Confidence:** VERIFIED

### 2.4 CfC Variants

The CfC implementation supports several modes (from the raminmh/CfC GitHub README):

| Flag | Variant | Description |
|---|---|---|
| (none) | Full CfC | Complete model with both sigmoid gates |
| `--no_gate` | No-gate CfC | Runs without the (1-sigmoid) interpolation part |
| `--minimal` | Direct solution | Runs the CfC direct (minimal) solution approximation |
| `--use_ltc` | LTC mode | Uses LTC with semi-implicit ODE solver instead of CfC |
| `--use_mixed` | Mixed memory | Augments CfC's RNN state with an LSTM to avoid vanishing gradients |

In the ncps library API:
- `mode='default'` = Full CfC
- `mode='pure'` = Direct solution approximation (minimal)
- `mode='no_gate'` = Without second gate

[CROSS-REFERENCE: Part IV Section 2.1 confirms these three mode strings and provides the exact implementation for each. Consistent.]

**Source:** GitHub raminmh/CfC README (VERIFIED); ncps API docs (VERIFIED)
**Confidence:** VERIFIED

### 2.5 Performance Comparison: CfC vs LTC

From the CfC paper:

| Metric | CfC vs LTC |
|---|---|
| Training speed | CfC is **1 to 5 orders of magnitude faster** (100x to 100,000x) |
| Inference speed | CfC is **100x+ faster** (no ODE solver needed) |
| Accuracy | Comparable to LTC on time-series tasks |
| Scalability | CfC "can scale remarkably well compared to other deep learning instances" -- LTC scaling is bottlenecked by ODE solver cost |
| Expressivity | CfC is described as a "tightly-bounded approximation" -- close to LTC |
| Time-series performance | "Remarkable performance in time series modeling, compared to advanced recurrent models" |

**When to use CfC vs LTC:**
- **Use CfC** in almost all practical scenarios -- it is dramatically faster with comparable accuracy
- **Use LTC** when you need the exact ODE dynamics for theoretical reasons, or when you are studying the continuous-time dynamical system properties directly
- **Use CfC with mixed_memory=True** when dealing with very long sequences where vanishing gradients are a concern (augments with LSTM)

**Source:** CfC paper abstract (VERIFIED); raminmh/CfC README (VERIFIED)
**Confidence:** VERIFIED for speed claims; HIGH for accuracy equivalence

### 2.6 Nature Machine Intelligence 2022 -- Key Findings

Published: Nature Machine Intelligence, Volume 4, pp. 992-1003, November 2022

Key findings:
1. The closed-form solution eliminates the ODE solver bottleneck entirely
2. CfC models are 1-5 orders of magnitude faster than Neural ODE counterparts
3. Since time appears explicitly in the closed form, the models handle irregular time series natively
4. CfC networks scale to sizes comparable to standard deep learning models (LTCs could not due to solver cost)
5. State-of-the-art results on multiple time-series benchmarks

**Source:** Nature Machine Intelligence 4, 992-1003 (2022); DOI: 10.1038/s42256-022-00556-7
**Confidence:** VERIFIED (publication details confirmed from arxiv and research-explorer.ista.ac.at)

---

## 3. Neural Circuit Policies (NCP)

### 3.1 What NCP Wiring Is

Neural Circuit Policies define a **structured sparse wiring pattern** for connecting neurons in an LTC or CfC network. Rather than using fully-connected layers (as in LSTM/GRU), NCP imposes a biologically-inspired connectivity structure.

From the ncps documentation:

> "The Neural Circuit Policy (NCP) is the most interesting wiring paradigm provided in this package and comprises of a 4-layer recurrent connection principle of sensory, inter, command, and motor neurons."

**Source:** ncps.readthedocs.io quickstart (VERIFIED); Lechner et al. 2020 Nature Machine Intelligence
**Confidence:** VERIFIED

### 3.2 The Four Neuron Types

| Layer | Type | Role | Analogous to |
|---|---|---|---|
| Layer 1 | **Sensory** neurons | Receive input from the environment | Input layer; C. elegans sensory neurons |
| Layer 2 | **Inter** neurons | Process and relay information between sensory and command | Hidden processing; C. elegans interneurons |
| Layer 3 | **Command** neurons | Integrate information and make decisions; have **recurrent connections** among themselves | Decision layer; C. elegans command interneurons |
| Layer 4 | **Motor** neurons | Produce output actions | Output layer; C. elegans motor neurons |

[CROSS-REFERENCE: See Part V for the mapping between these NCP neuron types and the Creatures lobe architecture.]

The wiring is **sparse** -- not every neuron connects to every other. The connectivity is controlled by several parameters:

From the NCP API:
```
NCP(
    inter_neurons,                    # Number of inter neurons (layer 2)
    command_neurons,                  # Number of command neurons (layer 3)
    motor_neurons,                    # Number of motor neurons (layer 4 = output size)
    sensory_fanout,                   # Average outgoing synapses: sensory -> inter
    inter_fanout,                     # Average outgoing synapses: inter -> command
    recurrent_command_synapses,       # Average recurrent connections within command layer
    motor_fanin,                      # Average incoming synapses to motor from command
    seed                              # Random seed for reproducible wiring
)
```

The simplified `AutoNCP` class requires only:
```
AutoNCP(units, output_size, sparsity_level=0.5, seed=22222)
```

Where `output_size` should typically be about 0.3 times the total units.

[CROSS-REFERENCE: See Part IV Section 3.2 and 3.3 for the full NCP and AutoNCP API with allocation algorithms.]

**Source:** ncps.readthedocs.io API reference for wirings (VERIFIED)
**Confidence:** VERIFIED

### 3.3 How NCP Wiring Constrains and Structures the Network

The NCP wiring creates a directed information flow:

```
Input --> Sensory --> Inter --> Command (with recurrence) --> Motor --> Output
```

Key structural constraints:
1. **Information flows in one direction** through the layers (sensory -> inter -> command -> motor)
2. **Recurrence is concentrated** in the command layer -- this is where temporal memory and decision-making happens
3. **Connections are sparse** -- controlled by fanout/fanin parameters, not fully connected
4. **Synapse polarity** is defined -- connections can be excitatory (+1) or inhibitory (-1), matching biological reality
5. **Reversal potentials (E_rev)** are initialized based on polarity -- excitatory synapses have positive E_rev, inhibitory have negative

This structure means:
- The network has far fewer parameters than a fully-connected equivalent
- Information bottlenecks force efficient representation
- The command layer recurrence creates a compact decision-making module
- The overall architecture mirrors biological neural circuit organization

**Source:** ncps API wirings docs (VERIFIED); ncps quickstart (VERIFIED)
**Confidence:** VERIFIED

### 3.4 Why NCP Matters for Interpretability

NCP wiring makes the network interpretable because:

1. **Traceable information flow:** You can follow signals from sensory input through inter neurons to command decisions to motor output
2. **Neuron role assignment:** Each neuron has a defined type and position in the processing hierarchy
3. **Sparse connections:** Fewer connections means fewer pathways to analyze
4. **Inspectable wiring diagram:** The `wiring.draw_graph()` method visualizes the entire network structure as a directed graph
5. **Small scale:** Practical NCP networks use 20-50 neurons total, making exhaustive inspection feasible

From the NCP paper (Lechner et al. 2020): The system was demonstrated to be "auditable" -- meaning a human can inspect and understand what the network is doing and why, unlike transformer-based black boxes.

**Source:** Lechner et al. 2020; ncps documentation
**Confidence:** HIGH (paper title itself is "Neural circuit policies enabling auditable autonomy")

### 3.5 The Nature Machine Intelligence 2020 Paper

**Full citation:** Lechner, M., Hasani, R., Amini, A., Henzinger, T.A., Rus, D., & Grosu, R. (2020). "Neural circuit policies enabling auditable autonomy." Nature Machine Intelligence, 2(10), 642-652.

Key results:
- Demonstrated autonomous driving (lane keeping) with only **19 neurons** (compared to hundreds of thousands in typical deep learning)
- The 19-neuron NCP achieved competitive performance with much larger networks
- The network was fully interpretable -- individual neurons could be mapped to specific driving behaviors
- Robust to noise and distribution shift (e.g., different weather conditions, unseen road types)
- The wiring diagram directly inspired by C. elegans connectome

**Source:** Lechner et al. 2020 (citation confirmed from multiple sources); ncps GitHub bibtex entry (VERIFIED)
**Confidence:** VERIFIED (multiple independent confirmations of paper details)

---

## 4. Mathematical Foundations

### 4.1 ODE Solver Requirements

LTC networks require a numerical ODE solver to compute their state at each timestep. The implementation in the ncps library uses a **semi-implicit Euler method** with configurable ODE unfolds.

From the LTC API: `ode_unfolds=6` (default)

This means at each discrete timestep, the ODE is integrated using 6 sub-steps of a semi-implicit solver. The semi-implicit approach provides better stability than explicit Euler for stiff systems.

**Available solver approaches (general Neural ODE literature):**

| Solver | Order | Steps per evaluation | Stability | Cost |
|---|---|---|---|---|
| Forward Euler | 1st | 1 | Poor for stiff systems | Cheapest |
| Semi-implicit Euler | 1st | 1 (but more stable) | Good | Low |
| RK4 (Runge-Kutta) | 4th | 4 | Good | Moderate |
| Adaptive (Dormand-Prince) | 4/5th | Variable | Excellent | Variable (can be expensive) |

The ncps implementation uses semi-implicit Euler with multiple unfolds rather than higher-order methods, trading accuracy per step for simplicity and predictable cost.

**CfC eliminates the need for any ODE solver** -- this is its primary advantage.

[CROSS-REFERENCE: Part IV Section 2.4 provides the complete ODE solver implementation from the LTCCell source code, confirming the semi-implicit Euler method.]

**Source:** ncps API docs (VERIFIED: ode_unfolds parameter); general Neural ODE knowledge
**Confidence:** VERIFIED for ncps implementation; HIGH for solver comparison table

### 4.2 Numerical Stability Considerations

**For LTC:**
- The bounded weight property ensures the state remains bounded regardless of input
- Semi-implicit integration improves stability over explicit Euler
- The `ode_unfolds` parameter controls accuracy vs. speed tradeoff (more unfolds = more accurate but slower)
- The `epsilon=1e-8` parameter prevents division by zero in time constant computation
- `implicit_param_constraints` can enforce parameter positivity at the implementation level
- `apply_weight_constraints()` method on LTCCell ensures weights stay in valid ranges

**For CfC:**
- The sigmoid time gate is inherently bounded in [0, 1]
- The tanh activations on ff1 and ff2 bound the output in [-1, 1]
- The interpolation `(1-sigma)*ff1 + sigma*ff2` is always bounded
- No risk of numerical instability from ODE solvers since there are none
- The backbone uses standard activations (lecun_tanh, silu, relu) -- standard stability properties

**Source:** ncps API docs (VERIFIED); CfC architecture analysis
**Confidence:** VERIFIED for parameter details; HIGH for stability analysis

### 4.3 Time Discretisation

**The core challenge:** The LTC ODE describes continuous-time dynamics, but computation happens in discrete steps.

**For LTC:**
The continuous ODE `dx/dt = f(x, t)` is discretised as:

```
# Semi-implicit Euler, unfolded N times within one timestep delta_t
sub_dt = delta_t / N_unfolds

for k in range(N_unfolds):
    dx = f(x, input, t + k * sub_dt) * sub_dt
    x = x + dx
```

The `timespans` parameter in the forward() method allows passing actual elapsed time between observations, enabling **irregular time series** processing. If timespans is None, uniform spacing of 1.0 is assumed.

**For CfC:**
Time appears explicitly in the closed form:
```
t_interp = sigmoid(A * elapsed_time + B)
```

This means CfC handles arbitrary time spacing naturally -- you just pass the actual elapsed time. No discretisation error accumulates because there is no iterative solver.

**Source:** ncps API docs (VERIFIED: timespans parameter, elapsed_time parameter)
**Confidence:** VERIFIED

### 4.4 Computational Cost Per Timestep

**LTC cost per timestep:**
```
Cost = N_unfolds * (synapse_computation + ODE_step)
     = ode_unfolds * O(N_neurons * N_synapses)
```

With default `ode_unfolds=6` and sparse NCP wiring, this is manageable but still significantly more expensive than a single matrix multiply.

**CfC cost per timestep:**
```
Cost = backbone_forward + 4_linear_heads + sigmoid + interpolation
     = O(backbone_layers * backbone_units^2) + O(4 * hidden_size * backbone_output_size) + O(hidden_size)
```

With default `backbone_layers=1, backbone_units=128`, this is comparable to a single LSTM step.

**Comparison:**

| Model | Ops per timestep (approximate) | Relative to LSTM |
|---|---|---|
| LSTM | ~4 * hidden^2 (gates) | 1x |
| GRU | ~3 * hidden^2 (gates) | 0.75x |
| LTC (6 unfolds, fully connected) | ~6 * N^2 per unfold | 2-10x |
| LTC (6 unfolds, NCP sparse) | ~6 * sparse_N | 0.5-3x |
| CfC (1 backbone layer) | ~backbone + 4*linear | ~1x |

**Source:** Architecture analysis from VERIFIED source code structure and API docs
**Confidence:** HIGH (derived from verified architecture; approximate)

### 4.5 How to Set/Initialise Time Constants

In the LTC implementation, the parameters are initialised as learnable weights:

- **tau (time constants):** Initialised as learnable parameters, typically starting around 1.0. Constrained to be positive (via softplus or absolute value constraints).
- **C_m (membrane capacitance):** Learnable, positive-constrained
- **w (synaptic weights):** Learnable, can be positive or negative
- **E_rev (reversal potentials):** Initialised based on synapse polarity from the wiring diagram:
  - Excitatory synapses (polarity +1): E_rev initialised positive
  - Inhibitory synapses (polarity -1): E_rev initialised negative
- **gamma, mu (sigmoid parameters):** Learnable parameters controlling synapse activation curves
- **x_leak (resting potential):** Learnable

The `implicit_param_constraints` flag controls whether constraints are applied via reparameterisation (implicit) or via explicit clamping after each update.

[CROSS-REFERENCE: Part IV Section 2.4 provides the complete parameter table with exact init ranges from the LTCCell source code. The descriptions here match.]

**Source:** ncps API docs (VERIFIED: LTCCell parameters); ncps wirings docs (VERIFIED: erev_initializer)
**Confidence:** VERIFIED

---

## 5. Key Properties Relevant to Game AI

### 5.1 Post-Training Adaptation

This is arguably the most important property of LNN/CfC for game AI applications.

From MIT News:
> "MIT researchers have developed a type of neural network that learns on the job, not just during its training phase. These flexible algorithms, dubbed 'liquid' networks, change their underlying equations to continuously adapt to new data inputs."

**What this means concretely:**
- After training, the network's behavior is NOT fixed
- The input-dependent time constants mean the network's temporal dynamics adapt to whatever input it is currently receiving
- This is NOT continued learning (the weights are frozen) -- it is **adaptive inference**
- The same trained network behaves differently (more appropriately) in different input regimes
- Example: a driving network trained in clear weather still adapts its temporal processing when it encounters rain, even if rain was not in the training set

**For game AI:** This means a creature trained on a set of scenarios can exhibit appropriate behavior in novel situations because its temporal dynamics self-adjust.

**Source:** MIT News (VERIFIED)
**Confidence:** VERIFIED

### 5.2 Small Network Expressivity

The C. elegans inspiration is directly relevant: **302 neurons produce complex, adaptive behavior**.

Demonstrated results with small networks:
- **19 neurons:** Autonomous lane-keeping (Lechner et al. 2020 NCP paper)
- **28-50 neurons:** Common sizes in ncps library examples
- **50-300 neurons:** Sufficient for complex time-series tasks

From the paper's expressivity analysis: LTCs have "superior expressivity within the family of neural ordinary differential equations" as measured by **trajectory length** in latent space -- meaning a small LTC network can represent longer, more complex trajectories than equivalent-sized standard neural ODEs.

**What can emerge from 50-300 neurons with NCP wiring:**
- Temporal pattern recognition and generation
- Adaptive motor control behaviors
- Multi-modal integration (combining different sensor streams)
- Decision-making under uncertainty
- Context-dependent response switching

**Source:** MIT News (VERIFIED); Lechner et al. 2020 results; ncps examples
**Confidence:** HIGH (results demonstrated in papers; extrapolation to game AI is inference)

### 5.3 Interpretability -- How to Inspect Individual Neurons

The combination of small network size + NCP wiring + biologically-meaningful neuron types enables several inspection approaches:

1. **Wiring diagram visualization:**
```python
wiring = AutoNCP(28, 4)
wiring.draw_graph(draw_labels=True)
```

2. **Neuron type identification:**
```python
wiring.get_type_of_neuron(neuron_id)  # Returns 'sensory', 'inter', 'command', or 'motor'
```

3. **Layer inspection:**
```python
wiring.get_neurons_of_layer(layer_id)  # Returns neuron IDs in each layer
```

4. **Activation analysis:** Record hidden states during inference and analyze which neurons activate for which inputs. With only 20-50 neurons, exhaustive analysis is feasible.

5. **Causal tracing:** Because information flow is structured (sensory -> inter -> command -> motor), you can trace which sensory inputs activate which command neurons, and how that maps to motor outputs.

6. **Synapse counting:**
```python
wiring.synapse_count          # Internal synapses
wiring.sensory_synapse_count  # Input-to-network synapses
```

**Source:** ncps API docs (VERIFIED)
**Confidence:** VERIFIED

### 5.4 Real-Time Inference Feasibility

**CfC is the recommended choice for real-time inference.**

- CfC per-timestep cost is comparable to a single LSTM step
- With 50-128 hidden units and 1 backbone layer, inference takes microseconds on modern hardware
- No ODE solver overhead (unlike LTC)
- The ncps library provides both PyTorch and TensorFlow implementations that can be deployed on GPU or CPU
- Batch processing is supported for parallel evaluation of multiple agents

**For game AI at 30-60 FPS:**
- A CfC with 64 hidden units and NCP wiring: sub-millisecond per inference step on CPU
- Can easily handle hundreds of agents with batch processing on GPU
- The small parameter count (hundreds to low thousands) means minimal memory footprint

**LTC is NOT recommended for real-time inference** due to ODE solver overhead (6+ sub-steps per timestep).

**Source:** Architecture analysis from VERIFIED docs; CfC speed claims from paper (VERIFIED)
**Confidence:** HIGH (architecture-based inference; specific benchmarks not fetched)

### 5.5 Stability Over Extended Runtime

LNN/CfC networks are structurally stable for long runs:

1. **Bounded states:** The ODE structure (LTC) and sigmoid interpolation (CfC) both ensure states remain bounded
2. **No gradient issues at inference:** Gradient explosion/vanishing only matters during training, not inference
3. **No numerical drift:** CfC has no iterative solver, so no accumulated numerical error. LTC's semi-implicit solver is stable.
4. **No memory leak:** Hidden state is fixed-size; no growing buffers
5. **Deterministic behavior:** Given the same input sequence, output is identical (no random sampling)

The mixed_memory mode (LSTM augmentation) can help if very long-term dependencies are needed, though this adds LSTM's standard hidden state management.

**Source:** Architecture analysis from VERIFIED implementation details
**Confidence:** HIGH (follows from verified architecture properties)

---

## 6. Liquid AI Company and Ecosystem

### 6.1 Company Overview

**Liquid AI, Inc.** is an MIT spinoff founded by the core LNN research team:
- **Ramin Hasani** (CEO) -- MIT CSAIL research affiliate, lead author of LTC paper
- **Mathias Lechner** -- ISTA, lead author of NCP paper
- **Alexander Amini** -- MIT PhD
- **Daniela Rus** -- MIT CSAIL Director, Andrew and Erna Viterbi Professor

Founded: 2023 (announced December 2023)
Headquarters: 314 Main St, Cambridge, MA 02142

From TechCrunch: "Liquid AI offers more capital efficient, reliable, explainable and capable machine learning models for both domain-specific and generative AI applications."

**Source:** MIT News press mentions (VERIFIED); Liquid AI website (VERIFIED)
**Confidence:** VERIFIED

### 6.2 Open-Source Implementations

| Repository | URL | Description | Stars | Last Updated |
|---|---|---|---|---|
| **ncps** (primary) | github.com/mlech26l/ncps | PyTorch + TensorFlow: NCP, LTC, CfC | 2.3k | Aug 2024 (v1.0.1) |
| **CfC** (original) | github.com/raminmh/CfC | Original CfC paper code (PyTorch + TF) | 1.0k | Dec 2022 |
| **liquid_time_constant_networks** | github.com/raminmh/liquid_time_constant_networks | Original LTC paper code | -- | Legacy |
| **keras-ncp** | github.com/mlech26l/keras-ncp | Keras/TF NCP implementation (older) | -- | Legacy |

**The recommended library is `ncps`** (pip install ncps).

### 6.3 Known Limitations of LNN Approach

1. **Sequential processing only:** LTC/CfC are RNNs -- they process data sequentially. They cannot be parallelised across the time dimension like Transformers can.
2. **ODE solver cost (LTC only):** CfC resolves this.
3. **Not a general-purpose architecture:** LTC/CfC excel at time-series and sequential decision-making. Not competitive with transformers on language modeling or image classification.
4. **Limited scale demonstrated:** Original papers demonstrate 19-256 neurons.
5. **Relatively small community.**
6. **NCP wiring randomness:** Different seeds produce different wirings.
7. **No native attention mechanism.**
8. **Training can be sensitive** to hyperparameters.

**Source:** Architectural analysis from VERIFIED sources; community discussions
**Confidence:** HIGH

---

## 7. Source Bibliography (Part III)

### Primary Papers

1. **Hasani, R., Lechner, M., Amini, A., Rus, D., & Grosu, R.** (2021). "Liquid Time-constant Networks." *Proceedings of the AAAI Conference on Artificial Intelligence*, 35(9), 7657-7666. ArXiv: https://arxiv.org/abs/2006.04439. Confidence: VERIFIED

2. **Hasani, R., Lechner, M., Amini, A., Liebenwein, L., Ray, A., Tschaikowski, M., Teschl, G., & Rus, D.** (2022). "Closed-form continuous-time neural networks." *Nature Machine Intelligence*, 4(11), 992-1003. DOI: https://doi.org/10.1038/s42256-022-00556-7. Confidence: VERIFIED

3. **Lechner, M., Hasani, R., Amini, A., Henzinger, T.A., Rus, D., & Grosu, R.** (2020). "Neural circuit policies enabling auditable autonomy." *Nature Machine Intelligence*, 2(10), 642-652. DOI: https://doi.org/10.1038/s42256-020-00237-3. Confidence: VERIFIED

### Technical Resources

4. **MIT News** -- "Liquid machine-learning system adapts to changing conditions" (Jan 28, 2021). https://news.mit.edu/2021/machine-learning-adapts-0128. Confidence: VERIFIED

5. **SignalPop** -- "Closed-form Continuous-time Liquid Neural Net Models -- A Programmer's Perspective" (Aug 11, 2023). https://www.signalpop.com/2023/08/11/closed-form-continuous-time-liquid-neural-net-models-a-programmers-perspective/. Confidence: VERIFIED

6. **Hugo Cisneros** -- Notes on NCP paper with LTC ODE equations. https://hugocisneros.com/notes/lechnerneuralcircuitpolicies2020/. Confidence: VERIFIED

---

# PART IV: ncps PACKAGE -- API REFERENCE

*Source document: `/research/ncps-reference.md`*
*Date: 2026-03-28*

## Source Verification Key

| Tag | Meaning |
|-----|---------|
| **VERIFIED** | Fetched and read directly from source code or official docs |
| **HIGH** | Multiple corroborating sources |
| **MEDIUM** | Single credible source |
| **LOW** | Uncorroborated, from training data only |

---

## 1. Package Overview

### What ncps Provides

Neural Circuit Policies (NCPs) are **designed sparse recurrent neural networks** loosely inspired by the nervous system of the nematode *C. elegans*. The `ncps` Python package provides: [VERIFIED -- GitHub README, ncps.readthedocs.io]

- **LTC (Liquid Time-Constant)** -- An RNN neuron model based on ordinary differential equations (ODEs) with adaptive time constants. Uses numerical ODE solvers (slower but fully differentiable).
- **CfC (Closed-form Continuous-time)** -- An approximation of the LTC closed-form solution that avoids the numerical ODE solver, yielding significantly faster training and inference while maintaining expressive power.
- **NCP Wiring** -- A structured sparse wiring system with 4 neuron layers (sensory, inter, command, motor) that constrains connectivity patterns, inspired by the *C. elegans* connectome.

Both models are **recurrent neural networks** with temporal state, applicable only to sequential or time-series data. [VERIFIED -- readthedocs quickstart]

### Installation

```bash
pip install ncps
```

**Hard dependencies** (from `setup.py`): [VERIFIED -- fetched setup.py]
- `packaging`
- `future`

**Optional dependencies** (not installed automatically): [VERIFIED -- setup.py comments]
- `torch` (PyTorch) -- for `ncps.torch` backend
- `tensorflow` -- for `ncps.tf` backend
- `networkx` -- required only for `wiring.get_graph()` and `wiring.draw_graph()`
- `matplotlib` -- required only for `wiring.draw_graph()`

### Current Version and Maintenance Status

| Field | Value | Confidence |
|-------|-------|------------|
| Latest PyPI version | **1.0.1** | VERIFIED -- PyPI page |
| Release date | **Aug 14, 2024** | VERIFIED -- PyPI page |
| Previous version | 1.0.0 (Jun 19, 2024) | VERIFIED -- PyPI page |
| GitHub stars | ~2,300 | VERIFIED -- GitHub |
| Open issues | 25 | VERIFIED -- GitHub issues page |
| Last commit | "Bump version to 1.0.1" -- Aug 14, 2024 | VERIFIED -- GitHub |
| Python support | 3.6+ | VERIFIED -- setup.py classifiers |
| License | **Apache License 2.0** | VERIFIED -- PyPI + GitHub |
| Author | **Mathias Lechner** (mlech26l@gmail.com) | VERIFIED -- setup.py |
| Co-author | **Ramin Hasani** (source file headers) | VERIFIED -- source headers |

**Maintenance note:** The last commit was Aug 2024. The package is in a **stable but low-maintenance** state. [VERIFIED -- PyPI]

### Supported Backends

| Backend | Module | Status |
|---------|--------|--------|
| PyTorch | `ncps.torch` | Primary, most complete | VERIFIED |
| TensorFlow/Keras | `ncps.tf` | Supported, tf.keras.layers | VERIFIED |
| JAX | Not available | VERIFIED -- not present in source |

---

## 2. API Surface -- PyTorch Backend (Primary)

### Module Structure

```
ncps/
    torch/
        __init__.py     # Exports: CfC, CfCCell, LTC, LTCCell, WiredCfCCell
        cfc.py          # CfC sequence model
        cfc_cell.py     # CfCCell single-step cell
        wired_cfc_cell.py  # WiredCfCCell (CfC with NCP wiring)
        ltc.py          # LTC sequence model
        ltc_cell.py     # LTCCell single-step cell
        lstm.py         # Internal LSTM cell for mixed_memory
    tf/                 # TensorFlow backend
    wirings/
        __init__.py
        wirings.py      # Wiring, FullyConnected, Random, NCP, AutoNCP
```

[VERIFIED -- fetched `__init__.py` and all source files]

### Import Patterns

```python
# Sequence models (most common usage)
from ncps.torch import CfC, LTC

# Single-step cells
from ncps.torch import CfCCell, LTCCell

# Wiring configurations
from ncps.wirings import AutoNCP, NCP, FullyConnected, Random

# All exports from ncps.torch
from ncps.torch import CfC, CfCCell, LTC, LTCCell, WiredCfCCell
```

[VERIFIED -- source `__init__.py`]

---

### 2.1 `ncps.torch.CfC` -- Closed-form Continuous-time RNN

**Inherits from:** `torch.nn.Module`

```python
class CfC(nn.Module):
    def __init__(
        self,
        input_size: Union[int, ncps.wirings.Wiring],
        units,
        proj_size: Optional[int] = None,
        return_sequences: bool = True,
        batch_first: bool = True,
        mixed_memory: bool = False,
        mode: str = "default",
        activation: str = "lecun_tanh",
        backbone_units: Optional[int] = None,
        backbone_layers: Optional[int] = None,
        backbone_dropout: Optional[int] = None,
    )
```

[VERIFIED -- fetched cfc.py source]

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_size` | `int` | *required* | Number of input features (C dimension) |
| `units` | `int` or `Wiring` | *required* | Number of hidden units, OR a `ncps.wirings.Wiring` object for structured wiring |
| `proj_size` | `int` or `None` | `None` | If set, adds an implicit linear output projection layer to this dimension |
| `return_sequences` | `bool` | `True` | If `True`, returns output at every timestep; if `False`, returns only the final output |
| `batch_first` | `bool` | `True` | If `True`, input shape is (B,L,C); if `False`, input shape is (L,B,C) |
| `mixed_memory` | `bool` | `False` | Augments with an LSTM memory cell for learning long-term dependencies |
| `mode` | `str` | `"default"` | One of: `"default"`, `"pure"` (direct solution approximation), `"no_gate"` (without second gate) |
| `activation` | `str` | `"lecun_tanh"` | Backbone activation function. Options: `"lecun_tanh"`, `"silu"`, `"relu"`, `"tanh"`, `"gelu"` |
| `backbone_units` | `int` or `None` | `128` (effective) | Hidden units in the backbone MLP layers |
| `backbone_layers` | `int` or `None` | `1` (effective) | Number of backbone MLP layers |
| `backbone_dropout` | `float` or `None` | `0.0` (effective) | Dropout rate in backbone layers |

**Critical constraint:** When `units` is a `Wiring` object (wired mode), `backbone_units`, `backbone_layers`, and `backbone_dropout` MUST be `None` -- they will raise `ValueError` if set. The backbone is only used in fully-connected mode. [VERIFIED -- source code]

#### Forward Method

```python
def forward(self, input, hx=None, timespans=None):
    """
    :param input: (L,C) unbatched, (B,L,C) if batch_first=True, (L,B,C) if batch_first=False
    :param hx: Initial hidden state (B,H) or tuple ((B,H),(B,H)) if mixed_memory=True. None = zeros.
    :param timespans: Optional tensor of elapsed times between timesteps, same shape as input minus feature dim.
    :return: (output, hx) -- output is sequence or final step; hx is final hidden state
    """
```

[VERIFIED -- source code]

#### Input/Output Tensor Shapes

| Tensor | Shape (batch_first=True) | Notes |
|--------|--------------------------|-------|
| `input` | `(B, L, C)` | B=batch, L=sequence length, C=input features |
| `hx` (no mixed_memory) | `(B, H)` | H = state_size = units (FC) or wiring.units (wired) |
| `hx` (mixed_memory) | `((B,H), (B,H))` | Tuple of (h_state, c_state) |
| `timespans` | `(B, L, 1)` or `(B, L)` | Elapsed time per step. Default 1.0 |
| `output` (return_sequences=True) | `(B, L, O)` | O = output_size |
| `output` (return_sequences=False) | `(B, O)` | Only last timestep |

Where:
- **Fully-connected mode:** `state_size = units`, `output_size = units` (or `proj_size` if set)
- **Wired mode:** `state_size = wiring.units`, `output_size = wiring.output_dim` (or `proj_size` if set)

[VERIFIED -- source code analysis]

#### CfC Modes

| Mode | Description | Implementation |
|------|-------------|----------------|
| `"default"` | Full gated CfC with time interpolation | `new_hidden = ff1 * (1.0 - t_interp) + t_interp * ff2` |
| `"pure"` | Direct closed-form solution approximation | `new_hidden = -A * exp(-ts * (abs(w_tau) + abs(ff1))) * ff1 + A` |
| `"no_gate"` | Additive (no gating) | `new_hidden = ff1 + t_interp * ff2` |

[VERIFIED -- CfCCell source code]

---

### 2.2 `ncps.torch.LTC` -- Liquid Time-Constant RNN

**Inherits from:** `torch.nn.Module`

```python
class LTC(nn.Module):
    def __init__(
        self,
        input_size: int,
        units,
        return_sequences: bool = True,
        batch_first: bool = True,
        mixed_memory: bool = False,
        input_mapping="affine",
        output_mapping="affine",
        ode_unfolds=6,
        epsilon=1e-8,
        implicit_param_constraints=True,
    )
```

[VERIFIED -- fetched ltc.py source]

**Key difference from CfC:** LTC does NOT have backbone parameters. When you pass an int for units, LTC always internally creates a `FullyConnected` wiring. The LTC cell uses a biologically-inspired ODE model with synaptic weights, conductances, and reversal potentials -- there is no backbone MLP. [VERIFIED -- source code]

---

### 2.3 `ncps.torch.CfCCell` -- Single-step CfC Cell

```python
class CfCCell(nn.Module):
    def __init__(
        self,
        input_size,
        hidden_size,
        mode="default",
        backbone_activation="lecun_tanh",
        backbone_units=128,
        backbone_layers=1,
        backbone_dropout=0.0,
        sparsity_mask=None,
    )
```

[VERIFIED -- fetched cfc_cell.py source]

**Note:** CfCCell returns `(new_hidden, new_hidden)` -- the output and new state are the same tensor. [VERIFIED -- source code]

---

### 2.4 `ncps.torch.LTCCell` -- Single-step LTC Cell

```python
class LTCCell(nn.Module):
    def __init__(
        self,
        wiring,
        in_features=None,
        input_mapping="affine",
        output_mapping="affine",
        ode_unfolds=6,
        epsilon=1e-8,
        implicit_param_constraints=False,
    )
```

[VERIFIED -- fetched ltc_cell.py source]

**Important:** Unlike CfCCell, LTCCell **requires** a `Wiring` object (not just an integer).

**Note:** Unlike CfCCell, LTCCell returns `(outputs, next_state)` where outputs != next_state. Outputs are the mapped motor neuron outputs (potentially smaller dimension than full state). [VERIFIED -- source code]

#### LTC Biological Parameters

The LTCCell allocates these learnable parameters: [VERIFIED -- source code `_allocate_parameters`]

| Parameter | Shape | Init Range | Description |
|-----------|-------|------------|-------------|
| `gleak` | `(units,)` | [0.001, 1.0] | Leak conductance per neuron |
| `vleak` | `(units,)` | [-0.2, 0.2] | Leak reversal potential per neuron |
| `cm` | `(units,)` | [0.4, 0.6] | Membrane capacitance per neuron |
| `w` | `(units, units)` | [0.001, 1.0] | Synaptic weight matrix |
| `sigma` | `(units, units)` | [3, 8] | Sigmoid synapse slope |
| `mu` | `(units, units)` | [0.3, 0.8] | Sigmoid synapse threshold |
| `erev` | `(units, units)` | From adjacency matrix | Reversal potential (excitatory/inhibitory) |
| `sensory_w` | `(input_dim, units)` | [0.001, 1.0] | Sensory synaptic weights |
| `sensory_sigma` | `(input_dim, units)` | [3, 8] | Sensory sigmoid slope |
| `sensory_mu` | `(input_dim, units)` | [0.3, 0.8] | Sensory sigmoid threshold |
| `sensory_erev` | `(input_dim, units)` | From sensory adjacency | Sensory reversal potential |
| `sparsity_mask` | `(units, units)` | `abs(adjacency_matrix)` | Non-trainable binary mask |
| `sensory_sparsity_mask` | `(input_dim, units)` | `abs(sensory_adjacency)` | Non-trainable binary mask |

[CROSS-REFERENCE: These parameters map directly to the ODE formulation in Part III Section 1.2. The parameter names correspond: `gleak` = 1/tau_i, `vleak` = x_leak_i, `cm` = C_m_i, `w` = w_ij, `sigma` = gamma_ij, `mu` = mu_ij, `erev` = E_ij.]

#### LTC ODE Solver

The core computation is an implicit Euler ODE solver that unfolds `ode_unfolds` times per timestep: [VERIFIED -- `_ode_solver` in ltc_cell.py]

```
For each unfold step:
    w_activation = w * sigmoid(v_pre, mu, sigma) * sparsity_mask
    numerator = (cm/dt) * v_pre + gleak * vleak + sum(w_activation * erev) + sensory_terms
    denominator = (cm/dt) + gleak + sum(w_activation) + sensory_activation_sum
    v_pre = numerator / (denominator + epsilon)
```

The `apply_weight_constraints()` method should be called during training to clamp weights to non-negative values (when `implicit_param_constraints=False`). [VERIFIED -- source code]

---

### 2.5 `ncps.torch.WiredCfCCell` -- CfC with NCP Wiring

```python
class WiredCfCCell(nn.Module):
    def __init__(self, input_size, wiring, mode="default")
```

This is an internal class that layers multiple CfCCells according to the NCP wiring structure. It is automatically created when you pass a `Wiring` object to `CfC()`. [VERIFIED -- wired_cfc_cell.py source]

**Key implementation details:**
- Creates one `CfCCell` per wiring layer (NCP has 3 layers: inter, command, motor)
- Each layer's CfCCell has `backbone_layers=0` (no backbone MLP) and uses a `sparsity_mask` from the adjacency matrix
- The forward method splits the hidden state by layer, processes each layer sequentially, then concatenates

```python
def forward(self, input, hx, timespans):
    h_state = torch.split(hx, self.layer_sizes, dim=1)
    new_h_state = []
    inputs = input
    for i in range(self.num_layers):
        h, _ = self._layers[i].forward(inputs, h_state[i], timespans)
        inputs = h
        new_h_state.append(h)
    new_h_state = torch.cat(new_h_state, dim=1)
    return h, new_h_state  # h is the last layer output (motor neurons)
```

[VERIFIED -- source code]

---

## 3. Wiring System Detail

### 3.1 Base Class: `ncps.wirings.Wiring`

```python
class Wiring:
    def __init__(self, units):
        self.units = units                    # Total number of internal neurons
        self.adjacency_matrix = np.zeros([units, units], dtype=np.int32)
        self.sensory_adjacency_matrix = None  # Set during build()
        self.input_dim = None                 # Set during build()
        self.output_dim = None                # Set during set_output_dim()
```

[VERIFIED -- wirings source code]

#### Key Properties and Methods

| Method/Property | Description |
|----------------|-------------|
| `units` | Total number of neurons in the wiring |
| `input_dim` | Number of sensory (input) neurons. Set by `build()` |
| `output_dim` | Number of motor (output) neurons. Set by `set_output_dim()` |
| `adjacency_matrix` | `np.ndarray` shape `(units, units)`, dtype `int32`. Values: `-1` (inhibitory), `0` (no connection), `+1` (excitatory) |
| `sensory_adjacency_matrix` | `np.ndarray` shape `(input_dim, units)`, dtype `int32`. Same value scheme |
| `num_layers` | Number of processing layers (1 for base Wiring, 3 for NCP) |
| `build(input_dim)` | Initializes the wiring for a given input dimension |
| `add_synapse(src, dest, polarity)` | Add an internal synapse. polarity must be -1 or +1 |
| `add_sensory_synapse(src, dest, polarity)` | Add a sensory-to-internal synapse |
| `get_type_of_neuron(neuron_id)` | Returns `"motor"` if `neuron_id < output_dim`, else `"inter"` |
| `erev_initializer()` | Returns copy of adjacency_matrix (used for reversal potential init) |
| `get_graph(include_sensory_neurons=True)` | Returns `networkx.DiGraph` |
| `draw_graph(layout, neuron_colors, synapse_colors, draw_labels)` | Renders matplotlib visualization |

[VERIFIED -- wirings source code]

### 3.2 `ncps.wirings.AutoNCP`

```python
class AutoNCP(NCP):
    def __init__(
        self,
        units,            # Total number of neurons
        output_size,      # Number of motor neurons (= output dimension)
        sparsity_level=0.5,  # 0.0 (very dense) to 0.9 (very sparse)
        seed=22222,       # Random seed for reproducible wiring
    )
```

[VERIFIED -- wirings source code]

#### How AutoNCP Decides Neuron Allocation

```python
# Step 1: Motor neurons are the output_size
motor_neurons = output_size

# Step 2: Remaining neurons split 40/60 between command and inter
inter_and_command_neurons = units - output_size
command_neurons = max(int(0.4 * inter_and_command_neurons), 1)
inter_neurons = inter_and_command_neurons - command_neurons

# Step 3: Density determines fanout/fanin
density_level = 1.0 - sparsity_level
sensory_fanout = max(int(inter_neurons * density_level), 1)
inter_fanout = max(int(command_neurons * density_level), 1)
recurrent_command_synapses = max(int(command_neurons * density_level * 2), 1)
motor_fanin = max(int(command_neurons * density_level), 1)
```

[VERIFIED -- `AutoNCP.__init__` source]

### 3.3 `ncps.wirings.NCP`

```python
class NCP(Wiring):
    def __init__(
        self,
        inter_neurons,
        command_neurons,
        motor_neurons,
        sensory_fanout,
        inter_fanout,
        recurrent_command_synapses,
        motor_fanin,
        seed=22222,
    )
```

[VERIFIED -- wirings source code]

**Total units = inter_neurons + command_neurons + motor_neurons**

#### NCP Neuron ID Layout

```
[0..motor_neurons-1] = motor neurons
[motor_neurons..motor_neurons+command_neurons-1] = command neurons
[motor_neurons+command_neurons..total-1] = inter neurons
```

[VERIFIED -- source code]

#### NCP Layer Structure

| Layer | ID | Contains | Receives From | Sends To |
|-------|-----|----------|---------------|----------|
| Layer 0 | Inter | `inter_neurons` neurons | Sensory (input) | Command |
| Layer 1 | Command | `command_neurons` neurons | Inter + self (recurrent) | Motor |
| Layer 2 | Motor | `motor_neurons` neurons | Command | Output |

### 3.4 Adjacency Matrix Format

| Value | Meaning |
|-------|---------|
| `+1` | Excitatory synapse (positive reversal potential) |
| `-1` | Inhibitory synapse (negative reversal potential) |
| `0` | No connection |

- `adjacency_matrix[src, dest]` = connection from neuron `src` to neuron `dest`
- `sensory_adjacency_matrix[src, dest]` = connection from sensory neuron `src` to internal neuron `dest`

[VERIFIED -- source code]

### 3.5 `ncps.wirings.FullyConnected`

Creates all-to-all connections. Polarity is randomly assigned with a 2:1 excitatory:inhibitory ratio (`rng.choice([-1, 1, 1])`). [VERIFIED -- source code]

### 3.6 `ncps.wirings.Random`

Creates random connections with controllable sparsity. Number of synapses = `round(units^2 * (1 - sparsity_level))`. [VERIFIED -- source code]

---

## 4. Training Patterns

### 4.1 Training Recommendations

| Aspect | Recommendation | Source |
|--------|---------------|--------|
| **Optimizer** | Adam | VERIFIED -- official example uses `Adam(lr=0.01)` |
| **Learning rate** | 0.005 to 0.01 | VERIFIED -- official examples use 0.005-0.01 |
| **Gradient clipping** | `gradient_clip_val=1` or `clip_grad_norm_(max_norm=1.0)` | VERIFIED -- official example explicitly uses clipping |
| **Loss function** | MSE for regression; standard losses work | VERIFIED |
| **LTC weight constraints** | Call `model.rnn_cell.apply_weight_constraints()` after each optimizer step if using `implicit_param_constraints=False` | VERIFIED -- LTCCell source |

### 4.2 How Time Constants Are Learned

**For LTC:** The biological parameters `gleak`, `vleak`, `cm`, `w`, `sigma`, `mu` are all learnable `nn.Parameter`s. The effective time constant emerges from the interplay of `cm` (capacitance), `gleak` (leak conductance), and input-dependent synaptic activation. [VERIFIED -- ltc_cell.py source code]

**For CfC:** The time-dependent behavior is parameterized through `time_a` and `time_b` linear layers that produce a time interpolation gate: `t_interp = sigmoid(time_a(x) * ts + time_b(x))`. [VERIFIED -- cfc_cell.py source code]

---

## 5. Inference and Adaptation

### 5.1 Step-by-Step Inference (Using Cells Directly)

```python
from ncps.torch import CfCCell

cell = CfCCell(input_size=20, hidden_size=50)
hx = torch.zeros(1, 50)  # (batch=1, hidden_size)

for observation in stream:
    x = torch.tensor(observation).unsqueeze(0)  # (1, input_size)
    output, hx = cell(x, hx, ts=1.0)
    action = output  # Use for control/decision
```

### 5.2 Irregular Time Intervals (Timespans)

```python
timespans = torch.tensor([[0.1, 0.5, 0.2, 1.0, 0.3]])  # (1, 5) for 5 timesteps
output, hx = model(x, timespans=timespans)
```

When `timespans=None` (default), elapsed time is assumed to be 1.0 for every step. [VERIFIED]

### 5.3 Saving and Loading Models

Standard PyTorch save/load works. **Important for wiring:** You need to recreate the same wiring object with the same parameters (including seed) before loading state_dict. [HIGH]

---

## 6. Code Examples from Official Sources

### 6.1 Minimal CfC Example

```python
import torch
from ncps.torch import CfC

rnn = CfC(20, 50)  # (input, hidden units)
x = torch.randn(2, 3, 20)  # (batch, time, features)
h0 = torch.zeros(2, 50)    # (batch, units)
output, hn = rnn(x, h0)
```

[VERIFIED -- GitHub README]

### 6.2 CfC with NCP Wiring

```python
from ncps.torch import CfC, LTC
from ncps.wirings import AutoNCP

wiring = AutoNCP(28, 4)  # 28 neurons, 4 outputs
input_size = 20
rnn = CfC(input_size, wiring)
# or: rnn = LTC(input_size, wiring)
```

[VERIFIED -- GitHub README]

---

## 7. Known Limitations and Gotchas

1. **Wiring must match:** When using `CfC` with a wiring object, backbone parameters MUST be `None`. [VERIFIED]

2. **LTC `implicit_param_constraints` default mismatch:** In the `LTC` wrapper defaults to `True`; in standalone `LTCCell` defaults to `False`. [VERIFIED]

3. **Output dimension difference:** FC mode output = state_size; wired mode output = wiring.output_dim. [VERIFIED]

4. **CfCCell returns identical output and state:** `(new_hidden, new_hidden)`. LTCCell returns `(outputs, next_state)` where outputs can be smaller. [VERIFIED]

5. **NCP neuron ID ordering is unintuitive:** Motor neurons come first (IDs 0..motor-1), then command, then inter. Opposite of processing order. [VERIFIED]

6. **`mixed_memory` LSTM state:** Must pass tuple `(h0, c0)` or `None`. [VERIFIED]

7. **No bidirectional support** built in. [VERIFIED]

8. **Fixed polarity ratio:** `FullyConnected` uses 2:1 excitatory:inhibitory. NCP uses 1:1. [VERIFIED]

9. **`timespans` parameter has known bugs** (GitHub issues #81, #82) with broadcasting when `batch_first=True`. [VERIFIED]

### Known Open Issues

| Issue | Summary | Status |
|-------|---------|--------|
| #82 | `RuntimeError` with batched timespans + LTC + batch_first=True | Open |
| #81 | `RuntimeError` in CfCCell timespans broadcasting | Open |
| #80 | `AttributeError` WiredCfCCell register_module | Open |
| #76 | bidirectional.py KeyError | Open |

[VERIFIED -- GitHub issues page]

---

## 8. Stacking and Composition

CfC and LTC are standard `nn.Module`s and compose with other PyTorch modules:

```python
class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Linear(raw_features, 20)
        self.rnn = CfC(20, AutoNCP(28, 4))
        self.decoder = nn.Linear(4, num_classes)

    def forward(self, x):
        encoded = self.encoder(x)
        rnn_out, _ = self.rnn(encoded)
        return self.decoder(rnn_out)
```

[HIGH -- standard PyTorch composition]

---

# PART V: CROSS-DOMAIN MAPPING NOTES

*New analysis section -- synthesised from all four source documents.*
*Compiled: 2026-03-28*

---

## 1. How Creatures Lobes Map to NCP Neuron Types

The Creatures C3/DS brain and the NCP wiring architecture share a fundamental design principle: **structured, layered information processing with sparse connectivity**. The mapping is not 1:1 but reveals strong structural parallels:

### Structural Mapping

| Creatures Lobe | Function | NCP Neuron Type | Rationale |
|---|---|---|---|
| Drive ("driv") | Input: internal chemical state | **Sensory** | Drive chemicals are sensory inputs to the brain |
| Vision ("visn") | Input: environmental perception | **Sensory** | Visual distances are sensory inputs |
| Smell ("smel") | Input: CA smell gradients | **Sensory** | Olfactory signals are sensory inputs |
| Stimulus Source ("stim") | Input: object categories | **Sensory** | Object recognition signals are sensory inputs |
| Verb ("verb") | Input: language commands | **Sensory** | Language inputs are sensory inputs |
| Noun ("noun") | Input: language objects | **Sensory** | Language inputs are sensory inputs |
| General Sense ("sens") | Input: misc status flags | **Sensory** | Status signals are sensory inputs |
| Response ("resp") | Input: reinforcement signals | **Sensory** | Reinforcement is a form of sensory input |
| Combination ("comb") | Hidden: situation representation | **Inter** + **Command** | Combines inputs via AND logic; most analogous to inter neurons for feature combination and command neurons for recurrent state |
| Friend or Foe ("forf") | Hidden: creature relationships | **Inter** | Relational state is intermediate processing |
| Attention ("attn") | Output: WTA focus selection | **Motor** | Produces the "what to attend to" output |
| Decision ("decn") | Output: WTA action selection | **Motor** | Produces the "what to do" output |

### Key Architectural Observations

1. **Input dimensionality**: The Creatures brain has multiple input lobes with distinct neuron counts. For an NCP replacement, these would all feed into the sensory layer. The total sensory input dimension = sum of all input lobe neuron counts (drives:20 + vision:~40 + verb:~16 + noun:~40 + general_sense:~32 + stimulus:~40 + response:~20) = approximately **200+ input features**.

2. **Output dimensionality**: The brain has two output lobes -- Attention (~40 neurons) and Decision (~16 neurons). In NCP terms, this means the motor layer needs approximately **56 output neurons** (though the actual decision is a WTA argmax, not all 56 values simultaneously).

3. **The Combination lobe is the critical mapping challenge**: In the original Creatures brain, the Combination lobe uses AND logic to represent "situations" (compound perceptions). In an NCP, this functionality would be distributed across the inter and command layers. The inter neurons perform nonlinear combination through sigmoid synapses, and the command neurons maintain recurrent state -- together they can approximate the Combination lobe's function, but through learned nonlinear dynamics rather than explicit AND gates.

4. **The WTA mechanism must be preserved at the output**: The openc2e engine reads outputs via `getSpareNeuron()`, which returns the index of the neuron marked as "spare" by SVRule opcode 31. The LNN replacement must produce a clear winner in both the attention and decision outputs. This maps naturally to NCP motor neurons -- the motor neuron with the highest activation for each output group becomes the winner.

---

## 2. How Biochemistry Modulation Maps to LTC Time Constants

The Creatures biochemistry system modulates brain behavior through chemical receptors that alter neuron parameters. The LTC architecture has a remarkably similar modulation mechanism through its input-dependent time constants.

### Parameter Mapping

| Creatures Brain Parameter | How Biochemistry Modulates It | LTC Equivalent | How It Is Modulated |
|---|---|---|---|
| **Neuron threshold** | Receptors set threshold based on chemical levels | **mu (sigmoid threshold)** | Learned parameter; could be made chemical-dependent |
| **Neuron leakage rate** | Receptors set decay rate from chemicals | **gleak (leak conductance)** | Learned parameter; higher gleak = faster leak toward vleak |
| **Neuron rest state** | Receptors set rest potential from chemicals | **vleak (leak reversal potential)** | Learned parameter; the equilibrium state when no input |
| **Dendrite susceptibility** | Receptors modulate susceptibility to reinforcement | **w (synaptic weights)** + **erev (reversal potentials)** | Weights and reversal potentials are the learned connection parameters |
| **STW/LTW relax rates** | Receptors control how fast weights drift | **No direct equivalent** | LTC weights are fixed after training; there is no online weight modification (this is a key gap) |
| **Brain chemicals (chem 0-5)** | Set by receptors, read by SVRules | **Additional inputs** | Could be passed as extra sensory inputs to the network |

### The "Liquid" Parallel

The most striking parallel is between the Creatures receptor system and LTC's input-dependent time constants:

- **Creatures**: Chemical levels (external to the brain) modulate brain parameters (threshold, leakage, rest state) via receptors. A creature with high Adrenaline has a different brain dynamic than one that is calm.
- **LTC**: Input signals modulate the effective time constant. A network receiving strong inputs has different temporal dynamics than one with weak inputs.

Both systems achieve **context-dependent neural dynamics through external modulation**. The key difference is:
- In Creatures, the modulation is via the biochemistry system (a separate subsystem with its own dynamics)
- In LTC, the modulation is via the input signal itself (the same data flowing through the network)

### Design Decision: How to Handle Biochemistry

Three approaches for the LNN replacement:

1. **Treat biochemistry as additional sensory input**: Feed chemical concentrations as extra features into the NCP sensory layer. The network learns to use these signals. Simple to implement. The biochemistry system continues to run as before.

2. **Map chemicals to LTC parameters directly**: Create a custom cell where specific chemicals modulate `gleak`, `vleak`, or `mu` of specific neurons. More biologically faithful but harder to train and requires a custom cell implementation.

3. **Hybrid**: Use approach 1 for most chemicals but hardcode critical chemicals (Reward/Punishment, Adrenaline) as direct modulators of specific parameters.

**Recommendation**: Start with approach 1 (chemicals as sensory input). It requires no custom cell modifications, is easiest to train, and the network can learn whatever chemical-dependent dynamics are useful. The biochemistry system already feeds into the brain through the locus system, so this is architecturally consistent.

---

## 3. How the openc2e Interface Contract Maps to ncps API

### Input Mapping

| openc2e Interface | ncps API |
|---|---|
| `setNeuronInput(i, float)` on each input lobe | Construct input tensor `x` with feature dimension = total input neurons |
| Drive lobe gets `drives[0..19]` | Features 0-19 of input tensor = drive values |
| Vision lobe gets distance values | Features 20-N = vision distances |
| Verb/Noun/Response lobe gets stimulus values | Features N-M = stimulus values |
| `brain->tick()` called every 4 game ticks | `model.forward(x, hx, timespans=dt)` called every 4 game ticks |
| `getSpareNeuron()` on attn/decn lobes | `torch.argmax(output[:, attn_range])` and `torch.argmax(output[:, decn_range])` |

### State Mapping

| openc2e State | ncps State |
|---|---|
| `c2eNeuron.variables[8]` per neuron | `hx` hidden state tensor `(1, state_size)` |
| Neuron states persist between ticks | `hx` is carried forward between calls |
| `wipe()` zeroes all state | `hx = torch.zeros(1, state_size)` |

### Lifecycle Mapping

| openc2e Lifecycle | ncps Equivalent |
|---|---|
| `processGenes()` -- build brain from genome | Create `Wiring` + `CfC` model; load trained weights |
| `init()` -- initialize state | Zero-initialize `hx` |
| `tick()` -- process one brain step | `output, hx = model(x, hx, timespans=elapsed)` |
| Lifestage changes (baby->child->adult) | Could swap models or fine-tune; or train a single model that handles all stages |

---

## 4. Key Design Decisions for the LNN Brain Replacement

### Decision 1: CfC over LTC

**Choice: Use CfC (Closed-form Continuous-time).**

Rationale:
- CfC is 100-100,000x faster than LTC at inference
- The Creatures brain ticks every 4 game ticks -- real-time performance is essential
- CfC preserves the "liquid" adaptive inference property
- The ODE solver in LTC adds unnecessary computational cost for a game AI application
- CfC with NCP wiring provides structured, interpretable architecture

### Decision 2: NCP Wiring Structure

**Choice: Use custom NCP wiring that mirrors the Creatures lobe architecture.**

Rather than `AutoNCP`, use `NCP` with parameters tuned to match the Creatures brain structure:
- **Sensory neurons**: Map to input lobes (Drives + Vision + Verb + Noun + Senses + Response)
- **Inter neurons**: Map to combination/processing function (replaces Combination lobe)
- **Command neurons**: Core decision-making with recurrence (replaces part of Combination + hidden processing)
- **Motor neurons**: Map to output lobes (Attention + Decision)

### Decision 3: Chemical Integration

**Choice: Biochemistry chemicals as additional sensory inputs (approach 1 from Section 2).**

Feed relevant chemical concentrations as additional features in the input vector. The network learns how to use them during training. This preserves the existing biochemistry subsystem without modification.

### Decision 4: Output Mechanism

**Choice: Winner-Takes-All via argmax on motor neuron outputs.**

The motor neurons are split into two groups (attention outputs and decision outputs). After each tick, `argmax` over each group determines the creature's attention target and chosen action. This mimics the `getSpareNeuron()` mechanism.

### Decision 5: Training Strategy

**Choice: Behavior cloning from the existing SVRule brain, then reinforcement learning refinement.**

1. Run the original openc2e brain and record input-output pairs (sensory inputs, chemical state, attention/decision outputs)
2. Train the CfC model to replicate these input-output mappings (supervised behavior cloning)
3. Optionally refine with RL using the Creatures reward/punishment chemical signals

---

## 5. Compatibility Considerations

### What Must Be Preserved

1. **The lobe ID interface**: The engine calls `getLobeById("driv")`, `getLobeById("attn")`, etc. The LNN wrapper must expose these as virtual lobes with the correct IDs.

2. **The `setNeuronInput()` interface**: Input lobes must accept float inputs at specific neuron indices.

3. **The `getSpareNeuron()` output**: Attention and Decision lobes must return a winner index.

4. **The neuron state interface**: `getNeuron(i)->variables[j]` is used by BrainViewer and the locus system. The LNN wrapper must expose interpretable state variables.

5. **The locus system**: Receptors and emitters need `float*` pointers into brain neuron variables. This requires mapping LNN hidden state entries to locus-addressable memory.

6. **Brain tick timing**: Every 4 game ticks, matching the existing `(ticks % 4) != 0` check.

### What Can Change

1. **Internal processing**: The SVRule system is entirely replaced by the CfC forward pass.
2. **Dendrite/tract structure**: Replaced by NCP wiring.
3. **Number of neurons**: Can differ from the original ~900 (NCP networks typically use 20-200 neurons).
4. **Learning mechanism**: Online STW/LTW weight modification is replaced by fixed trained weights with adaptive inference.

---

## 6. Performance Considerations

### Inference Cost Budget

The Creatures brain ticks every 4 game ticks. At the original design's 50ms per brain tick:
- A CfC with ~100 neurons and NCP wiring: **sub-millisecond** per inference on CPU
- This is well within the 50ms budget, even accounting for multiple creatures
- PyTorch inference on CPU for networks this small is extremely fast

### Memory Footprint

- CfC with 100 hidden units, NCP wiring: ~10,000-50,000 parameters
- Hidden state per creature: ~400 bytes (100 floats)
- This is comparable to or smaller than the original brain's memory footprint (~900 neurons x 8 state variables x 4 bytes = ~28KB + dendrite state)

### Batch Processing

If running multiple creatures simultaneously, their brain forward passes can be batched:
```python
# Batch all creatures' inputs
all_inputs = torch.stack([creature.input_tensor for creature in creatures])  # (N, C)
all_hx = torch.stack([creature.hidden_state for creature in creatures])      # (N, H)

# Single batched forward pass
all_outputs, all_new_hx = model(all_inputs.unsqueeze(1), all_hx)  # Add seq_len=1 dim
```

---

# PART VI: VERIFICATION SUMMARY

*Compiled: 2026-03-28*

---

## 1. Cross-Verification Results

### Contradictions Found

**[CONTRADICTION 1] Decision Lobe ID: "detn" vs "decn"**
- Part I (community docs) lists the Decision lobe ID as **"detn"**
- Part II (openc2e source) shows the engine uses **"decn"** in `brain->getLobeById("decn")`
- **Resolution**: The openc2e source code is authoritative for the actual implementation. The lobe ID used by the engine is **"decn"**. The "detn" in Part I is likely an inference from community documentation that was not verified against a real genome.
- **Impact**: The LNN wrapper MUST use "decn", not "detn".

**[CONTRADICTION 2] Lobe Names and Additional Lobes**
- Part I lists 9 standard C3/DS lobes: driv, verb, noun, stim, sens, comb, detn, attn, forf
- Part II reveals the engine also references lobes **"visn"** (Vision), **"smel"** (Smell), **"resp"** (Response), and uses **"decn"** (not "detn")
- **Resolution**: Part I's lobe list is incomplete for the C3/DS standard genome. The openc2e source shows at minimum 8 lobes accessed by the engine: driv, verb, noun, visn, smel, attn, decn, resp. Additional lobes (comb, stim, sens, forf) may exist in the genome but are not directly accessed by name in CreatureAI.cpp.
- **Impact**: The LNN brain must expose at minimum: driv, verb, noun, visn, attn, decn, resp. Support for additional lobes is needed for full compatibility.

**[CONTRADICTION 3] SVRule Opcode Count**
- Part I states "68+ opcodes"
- Part II implements opcodes 0-68 in the switch statement (69 opcodes), with several UNIMPLEMENTED
- **Resolution**: Consistent. "68+" in Part I aligns with the 69 opcodes (0 through 68) in Part II. No actual contradiction, just imprecise phrasing in Part I.

**[CONTRADICTION 4] Neuron Value Range**
- Part I states neuron values range from **-1.0 to 1.0** for C3/DS
- Part II shows openc2e clamps to **[-1.0, 1.0]** on store operations, and `setNeuronInput()` accepts **0.0-1.0** (no negative inputs documented)
- Part II also shows the drives are **0.0-1.0** (from `drives[i]`)
- **Resolution**: Internally, neurons CAN have values in [-1.0, 1.0] (the clamp range). Externally, inputs from the engine (drives, vision, stimulus) are always [0.0, 1.0]. Both documents are correct within their scope.

### Verified Consistencies

1. **SVRule binary format**: 48 bytes = 16 operations x 3 bytes. Consistent between Part I and Part II.
2. **4-character lobe IDs**: Confirmed in both community docs (Part I) and openc2e gene structs (Part II).
3. **Brain tick every 4 game ticks**: Confirmed in Part I (CAOS docs) and Part II (CreatureAI.cpp line 98).
4. **256 chemical slots**: Confirmed in Part I (community docs) and Part II (`float chemicals[256]`).
5. **NCP four neuron types** (sensory, inter, command, motor): Consistent between Part III (theory) and Part IV (ncps API). The ncps docs and the theory paper use identical terminology.
6. **LTC ODE formulation**: The ODE in Part III Section 1.2 maps directly to the learnable parameters in Part IV Section 2.4 (gleak=1/tau, vleak=x_leak, cm=C_m, w=w_ij, sigma=gamma, mu=mu, erev=E_ij). Fully consistent.
7. **CfC modes**: Part III Section 2.4 and Part IV Section 2.1 describe the same three modes with matching names and descriptions.
8. **Semi-implicit Euler solver**: Part III Section 4.1 describes it; Part IV Section 2.4 provides the implementation. Consistent.

---

## 2. Source Quality Assessment (CRAAP Evaluation)

### Part I: Creatures C3/DS Brain Architecture

| Criterion | Rating | Notes |
|---|---|---|
| **Currency** | B | Community wiki sources are maintained but reflect 20+ year old game knowledge. Last significant edits vary. |
| **Relevance** | A | Directly describes the system being replaced. |
| **Authority** | B+ | Creatures Wiki (community-maintained), Alan Zucconi (professional game dev/academic), Chris Double (original community developer). Not official Creature Labs documentation. |
| **Accuracy** | B+ | Cross-verified against openc2e source code (Part II). Minor discrepancies found (lobe IDs). Most claims confirmed. |
| **Purpose** | A | Community reference documentation with no commercial bias. |
| **Overall** | B+ | Reliable for architecture understanding; specific details (exact lobe IDs, opcode behavior) should be verified against source code. |

### Part II: openc2e Source Code

| Criterion | Rating | Notes |
|---|---|---|
| **Currency** | A | Fetched directly from current main branch (commit 2f91af70). |
| **Relevance** | A+ | IS the implementation that the LNN brain must interface with. |
| **Authority** | A+ | Primary source: the actual code. |
| **Accuracy** | A | Direct source code reading. Some features marked UNIMPLEMENTED. |
| **Purpose** | N/A | Source code, no interpretation bias. |
| **Overall** | A | The definitive reference for the interface contract. |

### Part III: Liquid Neural Networks -- Theory

| Criterion | Rating | Notes |
|---|---|---|
| **Currency** | A | Papers from 2020-2022; company info current to 2026. |
| **Relevance** | A | Core technology for the brain replacement. |
| **Authority** | A+ | Nature Machine Intelligence, AAAI conference, MIT News. Top-tier venues. |
| **Accuracy** | A | Equations verified from multiple sources. Paper claims confirmed from abstracts. |
| **Purpose** | A | Academic research. |
| **Overall** | A | Highly reliable. |

### Part IV: ncps Package API

| Criterion | Rating | Notes |
|---|---|---|
| **Currency** | B+ | Package v1.0.1, Aug 2024. Stable but low maintenance (25 open issues, no recent commits as of Mar 2026). |
| **Relevance** | A+ | IS the implementation library being used. |
| **Authority** | A | Direct source code reading + official docs. |
| **Accuracy** | A | All claims verified from source code. Known bugs documented. |
| **Purpose** | N/A | Source code + official documentation. |
| **Overall** | A | Definitive for the API. The staleness of maintenance (no commits since Aug 2024) is a risk factor for bugs. |

---

## 3. Items Still Marked NEEDS VERIFICATION

1. **Exact 4-character lobe IDs for ALL lobes in the standard C3/DS norn genome** -- Part I's list is incomplete; Part II shows the engine-accessed subset but not the full genome contents. Would require parsing an actual `.gen` file.

2. **Complete neuron counts per lobe in C3/DS** -- Not available in any source. Would require genome analysis.

3. **C3/DS reward/punishment integration with dendrite learning** -- Documented for C1 in detail; C3 mechanism is less clear. SVRule opcodes 57-62 (reward/punish) are UNIMPLEMENTED in openc2e.

4. **ConASH/DecASH atrophy system in C3/DS** -- Whether C3 uses the same system as C1 or has a different mechanism.

5. **Several SVRule opcodes' exact behavior** -- Opcodes 37-42 (leakage, rest state, input gain, persistence, noise, WTA) are UNIMPLEMENTED in openc2e. **Resolved 2026-04-26:** stock C3 1999 source implements them at SVRule.h:236-243, 621-652 with documented formulas; intent and behaviour now known. See svrule-brain-complete-reference.md Section 6 for the per-opcode formulas.

6. **ncps timespans broadcasting bug fix status** -- GitHub issues #81 and #82 are open as of March 2026. May need workaround for batched timespans.

7. **Performance benchmarks for CfC at Creatures-scale** -- The sub-millisecond inference claim is based on architectural analysis, not measured benchmarks with the specific input/output dimensions of a Creatures brain.

---

## 4. Confidence Matrix by Topic Area

| Topic | Confidence | Primary Source | Cross-Verification |
|---|---|---|---|
| Creatures brain lobe architecture | HIGH | Part I + Part II | Consistent (with noted contradictions) |
| Creatures SVRule system | HIGH | Part I + Part II | Consistent on format; openc2e has gaps |
| Creatures biochemistry system | HIGH | Part I + Part II | Consistent |
| Creatures genome format | HIGH | Part I + Part II | Consistent |
| openc2e interface contract | VERIFIED | Part II (source code) | N/A (primary source) |
| LTC ODE formulation | VERIFIED | Part III + Part IV | Consistent |
| CfC architecture | VERIFIED | Part III + Part IV | Consistent |
| NCP wiring system | VERIFIED | Part III + Part IV | Consistent |
| ncps API details | VERIFIED | Part IV (source code) | N/A (primary source) |
| Cross-domain mapping (Part V) | MEDIUM-HIGH | Analysis from verified sources | Novel analysis, not independently verified |
| Performance estimates | MEDIUM | Architecture analysis | Not benchmarked |
| Training strategy | MEDIUM | Standard ML practice | Not tested for this specific application |

---

# APPENDIX A: COMPLETE SOURCE BIBLIOGRAPHY

*Deduplicated from all 4 source documents.*

---

## Primary Academic Papers

1. **Hasani, R., Lechner, M., Amini, A., Rus, D., & Grosu, R.** (2021). "Liquid Time-constant Networks." *Proceedings of the AAAI Conference on Artificial Intelligence*, 35(9), 7657-7666.
   - ArXiv: https://arxiv.org/abs/2006.04439
   - AAAI: https://ojs.aaai.org/index.php/AAAI/article/view/16936

2. **Hasani, R., Lechner, M., Amini, A., Liebenwein, L., Ray, A., Tschaikowski, M., Teschl, G., & Rus, D.** (2022). "Closed-form continuous-time neural networks." *Nature Machine Intelligence*, 4(11), 992-1003.
   - ArXiv: https://arxiv.org/abs/2106.13898
   - DOI: https://doi.org/10.1038/s42256-022-00556-7

3. **Lechner, M., Hasani, R., Amini, A., Henzinger, T.A., Rus, D., & Grosu, R.** (2020). "Neural circuit policies enabling auditable autonomy." *Nature Machine Intelligence*, 2(10), 642-652.
   - DOI: https://doi.org/10.1038/s42256-020-00237-3
   - Open Access PDF: https://publik.tuwien.ac.at/files/publik_292280.pdf

4. **Grand, S., Cliff, D., Malhotra, A.** (1997). "Creatures: Artificial Life Autonomous Software Agents for Home Entertainment." Proceedings of the First International Conference on Autonomous Agents.

## Code Repositories

5. **ncps library** -- https://github.com/mlech26l/ncps (Apache 2.0, v1.0.1, Aug 2024)
   - Documentation: https://ncps.readthedocs.io/en/latest/
   - PyPI: `pip install ncps`

6. **CfC original** -- https://github.com/raminmh/CfC (Apache 2.0)

7. **LTC original** -- https://github.com/raminmh/liquid_time_constant_networks

8. **openc2e** -- https://github.com/openc2e/openc2e (main branch, commit 2f91af70)

## Creatures Community Documentation (VERIFIED, fetched 2026-03-28)

9. **Creatures Wiki - Brain** -- https://creatures.wiki/Brain
10. **Creatures Wiki - Biochemistry** -- https://creatures.wiki/Biochemistry
11. **Creatures Wiki - GEN files** -- https://creatures.wiki/GEN_files
12. **Creatures Wiki (Fandom) - C3 Chemical List** -- https://creatures.fandom.com/wiki/C3_Chemical_List
13. **Creatures Wiki (Fandom) - OHSS** -- https://creatures.fandom.com/wiki/OHSS
14. **Creatures Wiki (Fandom) - Concept lobe** -- https://creatures.fandom.com/wiki/Concept_lobe
15. **Creatures Wiki (Fandom) - Decision lobe** -- https://creatures.fandom.com/wiki/Decision_lobe
16. **Creatures Wiki (Fandom) - ForF lobe** -- https://creatures.fandom.com/wiki/ForF_lobe
17. **Creatures Wiki (Fandom) - Brain in a Vat** -- https://creatures.fandom.com/wiki/Brain_in_a_Vat
18. **Creatures Wiki (Fandom) - Openc2e** -- https://creatures.fandom.com/wiki/Openc2e

## Technical Articles and Resources

19. **Alan Zucconi** -- "The AI of Creatures" (2020) -- https://www.alanzucconi.com/2020/07/27/the-ai-of-creatures/
20. **MIT News** -- "Liquid machine-learning system adapts to changing conditions" (Jan 28, 2021) -- https://news.mit.edu/2021/machine-learning-adapts-0128
21. **SignalPop** -- "Closed-form Continuous-time Liquid Neural Net Models -- A Programmer's Perspective" (Aug 11, 2023) -- https://www.signalpop.com/2023/08/11/closed-form-continuous-time-liquid-neural-net-models-a-programmers-perspective/
22. **Hugo Cisneros** -- Notes on NCP paper with LTC ODE equations -- https://hugocisneros.com/notes/lechnerneuralcircuitpolicies2020/
23. **Chris Double / Creatures Developer Resource** -- http://double.nz/creatures/brainlobes/differences.htm
24. **CAOS Documentation (ghostfishe.net)** -- https://www.ghostfishe.net/bbw/tutorials/categorical.html
25. **Liquid AI Research Page** -- https://www.liquid.ai/research

## openc2e Source Files Directly Fetched

26. `src/openc2e/creatures/c2eBrain.h` and `c2eBrain.cpp`
27. `src/openc2e/creatures/c2eCreature.h`
28. `src/openc2e/creatures/Creature.h` and `Creature.cpp`
29. `src/openc2e/creatures/CreatureAI.cpp`
30. `src/openc2e/creatures/Biochemistry.cpp`
31. `src/openc2e/creatures/oldBrain.h` and `oldCreature.h`
32. `src/fileformats/genomeFile.h` and `genomeFile.cpp`
33. `src/openc2e/creatures/lifestage.h`
34. `src/openc2e/openc2eimgui/BrainViewer.h`
35. `CMakeLists.txt`

## ncps Source Files Directly Fetched

36. `ncps/torch/cfc.py` -- CfC sequence model
37. `ncps/torch/cfc_cell.py` -- CfCCell implementation
38. `ncps/torch/ltc.py` -- LTC sequence model
39. `ncps/torch/ltc_cell.py` -- LTCCell with ODE solver
40. `ncps/torch/wired_cfc_cell.py` -- WiredCfCCell layered architecture
41. `ncps/torch/__init__.py` -- Public exports
42. `ncps/wirings/wirings.py` -- Complete wiring system
43. `setup.py` -- Package metadata and dependencies
