# Phase 4A: Multi-Lobe CfC Brain Architecture: Specification

**Date:** 2026-03-30
**Branch:** `feature/multi-lobe-cfc`
**Depends on:** Phase 3 (complete)
**Supersedes:** Single monolithic CfC/NCP model in `norn_brain.py`

---

## 0. Document Purpose

This document specifies the refactoring of NORNBRAIN from a single monolithic CfC/NCP model into a compartmentalised multi-module architecture inspired by mammalian brain organisation. The architecture replaces the single 513→187 neuron CfC with four specialised CfC modules (Thalamus, Amygdala, Hippocampus, Prefrontal Cortex) connected by genetically-defined tract projections.

**What this document covers:**
- The four CfC module specifications (neuron counts, NCP wiring, time constant strategy)
- Inter-module tract projection system
- Information flow and causal chain
- Input/output contract (bridge compatibility)
- Training pipeline adaptation (behaviour cloning + RL)
- Genetic evolvability foundations

**What this document does NOT cover:**
- Long-Term Memory system (see Phase 4B spec)
- Emotional hierarchy and dominance system (see Phase 4C spec)
- Language output (see Phase 4D spec)

---

## 1. Goals and Success Criteria

### Primary Goal
Replace the monolithic CfC brain with four compartmentalised CfC modules that mirror mammalian brain regions, each with independent hidden states, NCP wiring, and time dynamics. The norn's brain becomes genuinely modular: attention processing is separate from emotional processing is separate from executive decision-making.

### Success Criteria
1. **SC1: Bridge compatibility:** The multi-lobe brain produces the same output contract as the monolithic brain: `attn_winner` (int 0-39), `decn_winner` (int 0-16), `BrainOutput` dataclass with motor values and activations.
2. **SC2: Independent hidden states:** Each module maintains its own hidden state vector. Resetting one module's state does not affect the others.
3. **SC3: Trainable end-to-end:** The full multi-module architecture is trainable via both behaviour cloning (supervised) and REINFORCE (online RL) with gradients flowing through inter-module connections.
4. **SC4: Comparable performance:** After training on the same observation dataset, the multi-lobe brain achieves comparable or better action prediction accuracy vs the monolithic `NornBrainFull`.
5. **SC5: Per-module introspection:** The dashboard can display per-module hidden states, per-module activations, and tract projection weights separately.
6. **SC6: Genetic parameterisation:** All architectural parameters (neuron counts, fanout, tract masks) are exposed in a genome-like config dict that can be varied per-creature.

### Non-Goals for Phase 4A
- LTM encoding/retrieval (Phase 4B)
- Emotional dominance hierarchy (Phase 4C)
- Language output (Phase 4D)
- Multi-creature support (unchanged: one creature at a time)
- C++ implementation

---

## 2. Architectural Motivation

### Why Not One Big Network?

The monolithic `NornBrainFull` (513 inputs → 80 inter → 50 command → 57 motor = 187 neurons) works but has fundamental limitations:

1. **No functional compartmentalisation.** All 80 inter neurons form a shared pool. Nothing prevents an inter neuron that "should" process drives from also encoding smell information. The network uses whatever representation minimises loss, which may bear no resemblance to the biological lobe structure.

2. **Single hidden state.** The 187-dimensional hidden vector must simultaneously encode attention state, emotional state, working memory, and decision context. These have fundamentally different time scales: attention shifts in ticks, emotional associations persist for hundreds of ticks, context should last thousands. A single hidden state forces a compromise.

3. **Not genetically evolvable.** Mutating the network means perturbing weights in a 187-dimensional space with no semantic structure. You cannot "make the drive processing stronger" or "weaken the smell pathway" because those aren't separable components.

4. **Not interpretable.** Looking at the hidden state tells you nothing about what the norn is "thinking." Is it processing a drive signal or an emotional memory? The activations are entangled.

### Why Four Modules?

The mammalian brain has dozens of regions, but for a primitive emotional creature (which is what a norn is), four functional regions capture the essential computational roles:

| Region | Biological role | Norn role |
|--------|----------------|-----------|
| **Thalamus** | Sensory relay, attention gating | What matters right now? (produces `attn_winner`) |
| **Amygdala** | Emotional tagging, fear/reward association | Is this good or bad? How do I feel? |
| **Hippocampus** | Episodic memory, spatial context | What happened recently? Where am I? |
| **Prefrontal cortex** | Executive function, decision-making | Given everything, what should I do? (produces `decn_winner`) |

This is not a metaphor: each module is a separate CfC instance with its own NCP wiring, its own hidden state, and its own time dynamics. The Thalamus is genuinely fast-reacting. The Hippocampus genuinely retains information longer. These properties emerge from the CfC time constant mechanism (see Section 4).

---

## 3. Architecture Overview

### System Diagram

```
                         SENSORY INPUTS
    ┌────────────────────────────────────────────────────┐
    │  visn(40) smel(40) driv(20) prox(20) sitn(9)      │
    │  detl(11) noun(40) verb(17) resp(20) stim(40)     │
    │  chemicals(256)                                    │
    └──────┬──────────────┬──────────────┬───────────────┘
           │              │              │
    ┌──────▼──────┐  ┌────▼────┐  ┌──────▼──────┐
    │  THALAMUS   │  │ AMYGDALA│  │ HIPPOCAMPUS │
    │  CfC module │  │  CfC    │  │  CfC module │
    │             │  │ module  │  │             │
    │  Attention  │  │ Emotion │  │ Context     │
    │  gating     │  │ valence │  │ memory      │
    │             │  │         │  │             │
    │  Fast τ     │  │ Fast/   │  │ Slow τ      │
    │             │  │ Slow τ  │  │             │
    └──────┬──────┘  └────┬────┘  └──────┬──────┘
           │              │              │
           │   attn(40)   │  emo(16)     │  ctx(16)
           │              │              │
    ┌──────▼──────────────▼──────────────▼──────────┐
    │              PREFRONTAL CORTEX                 │
    │              CfC module                        │
    │                                                │
    │  Integrates: attention + emotion + context     │
    │  + drives + verb + noun + resp + stim + chem   │
    │  + LTM injection (Phase 4B: 6 channels)        │
    │                                                │
    │  Moderate τ                                    │
    └──────────────────────┬─────────────────────────┘
                           │
                    decn(17) output
                           │
              ┌────────────▼────────────┐
              │  OUTPUT ASSEMBLY        │
              │  attn_winner = argmax   │
              │  decn_winner = argmax   │
              │  → BrainOutput          │
              └─────────────────────────┘
```

### Causal Chain

The architecture enforces a two-stage causal chain matching the original C3 brain:

1. **Stage 1: Attention:** The Thalamus processes sensory inputs (primarily visn, smel, driv, prox) and produces attention output (40 neurons). This determines what the norn focuses on.

2. **Stage 1 (parallel): Emotion + Context:** The Amygdala processes drives, stim, and chemicals to produce an emotional valence vector. The Hippocampus processes spatial/contextual inputs to produce a context vector. These run in parallel with the Thalamus.

3. **Stage 2: Decision:** The Prefrontal Cortex receives the attention output, emotional state, contextual state, plus raw drive/verb/noun/resp/stim/chemical inputs. It integrates everything and produces the decision output (17 neurons).

This means attention is computed *before* the decision, and the decision has access to what the norn is attending to. This matches both the original C3 brain's information flow and the biological thalamo-cortical pathway.

---

## 4. CfC Module Specifications

### How Time Constants Work in CfC

Each CfC neuron's update is governed by (from `CfCCell.forward()`):

```python
t_interp = sigmoid(time_a(x) * ts + time_b(x))
new_hidden = ff1 * (1.0 - t_interp) + t_interp * ff2
```

Where:
- `ts` is the timespan parameter (default 1.0 per tick)
- `time_a` and `time_b` are learned linear projections (per-neuron)
- `t_interp` controls how much the hidden state changes toward the new target `ff2`

When `t_interp ≈ 1`, the neuron fully updates (fast, reactive). When `t_interp ≈ 0`, the neuron retains its old state (slow, persistent). Since `time_a` and `time_b` are **learned parameters**, each neuron learns its own time constant through training.

**Key insight:** Since each CfC module is a separate `CfC` instance, each module independently learns its time dynamics. We don't need to manually set time constants: the training process will naturally discover that the Hippocampus should be slow and the Thalamus should be fast, because those time scales produce the best behavioural outcomes.

**Initialisation bias:** We CAN bias the initial time constants by initialising `time_a` and `time_b` differently per module. For the Hippocampus, initialising `time_b` to a negative value biases `t_interp` toward 0 (slow updates). For the Thalamus, initialising `time_b` to a positive value biases toward 1 (fast updates). Training then fine-tunes from these starting points.

### Module 1: Thalamus (Attention Gating)

**Role:** Process sensory inputs and produce attention output. Determines what agent category the norn focuses on.

**Inputs (tract projections from):**
| Source | Size | Tract name |
|--------|------|------------|
| visn (vision) | 40 | `tract_visn_thal` |
| smel (smell) | 40 | `tract_smel_thal` |
| driv (drives) | 20 | `tract_driv_thal` |
| prox (proximity) | 20 | `tract_prox_thal` |

**Effective input size:** Sum of tract output dimensions (configurable, default 40: each tract projects to 10).

**NCP Wiring:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| inter_neurons | 20 | Moderate: attention is a selection task, not deep processing |
| command_neurons | 10 | Integration before motor output |
| motor_neurons | 40 | One per agent category (attention output) |
| sensory_fanout | 8 | Each input reaches ~8 inter neurons |
| inter_fanout | 6 | Each inter reaches ~6 command neurons |
| recurrent_command_synapses | 10 | Recurrence for temporal attention stability |
| motor_fanin | 6 | Each motor neuron receives from ~6 command neurons |

**Total neurons:** 70 (20 + 10 + 40)

**Time constant bias:** Fast (initialise `time_b` with positive mean). Attention should shift quickly in response to new sensory input.

**Output:** 40-dimensional attention vector. `attn_winner = argmax(output)`.

### Module 2: Amygdala (Emotional Processing)

**Role:** Evaluate emotional valence of current situation. Fast reactive assessment ("is this good or bad?") combined with slow emotional memory ("I've been scared a lot lately").

**Inputs (tract projections from):**
| Source | Size | Tract name |
|--------|------|------------|
| driv (drives) | 20 | `tract_driv_amyg` |
| stim (stimulus) | 40 | `tract_stim_amyg` |
| chemicals (selected) | 16 | `tract_chem_amyg` |

Chemical selection: reward(204), punishment(205), adrenaline(117), fear(161), anger(160), pain(148), hunger_protein(149), hunger_carb(150), hunger_fat(151), loneliness(156), boredom(159), sex_drive(162), comfort(163), stress(128), injury(127), life(125).

**Effective input size:** Sum of tract outputs (default 24).

**NCP Wiring:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| inter_neurons | 24 | Needs enough capacity for nuanced emotional states |
| command_neurons | 12 | Integration of drive+stim+chem signals |
| motor_neurons | 16 | Emotional state vector (output) |
| sensory_fanout | 8 | |
| inter_fanout | 6 | |
| recurrent_command_synapses | 12 | Strong recurrence: emotions persist |
| motor_fanin | 6 | |

**Total neurons:** 52 (24 + 12 + 16)

**Time constant bias:** Mixed: fast reaction (initialise some `time_b` positive) for immediate emotional responses, but strong recurrence for persistence. The slow-forget property comes from the recurrent command synapses and learned time constants.

**Output:** 16-dimensional emotional state vector. Not argmax'd: passed as continuous values to the Prefrontal Cortex.

### Module 3: Hippocampus (Contextual Memory)

**Role:** Maintain medium-term contextual memory. Encodes "what's been happening recently" and "where am I." This is NOT the LTM system (Phase 4B): this is the CfC's intrinsic hidden-state memory operating at a longer time scale than the other modules.

**Inputs (tract projections from):**
| Source | Size | Tract name |
|--------|------|------------|
| sitn (situation) | 9 | `tract_sitn_hipp` |
| detl (detail) | 11 | `tract_detl_hipp` |
| noun (category) | 40 | `tract_noun_hipp` |
| verb (action) | 17 | `tract_verb_hipp` |
| location (posx, posy) | 2 | `tract_loc_hipp` |

**Effective input size:** Sum of tract outputs (default 20).

**NCP Wiring:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| inter_neurons | 24 | Needs capacity to encode episodic context |
| command_neurons | 12 | |
| motor_neurons | 16 | Context state vector (output) |
| sensory_fanout | 6 | Sparser: context is lower-dimensional |
| inter_fanout | 6 | |
| recurrent_command_synapses | 16 | Very strong recurrence: context must persist |
| motor_fanin | 6 | |

**Total neurons:** 52 (24 + 12 + 16)

**Time constant bias:** Slow (initialise `time_b` with negative mean). Context should persist across many ticks. The Hippocampus should be the slowest-changing module.

**Output:** 16-dimensional context vector. Passed as continuous values to the Prefrontal Cortex.

### Module 4: Prefrontal Cortex (Executive Decision-Making)

**Role:** Integrate all information: attention output, emotional state, contextual memory, raw drives, action/category history, stimulus, and biochemistry: to produce a decision. This is the norn's "executive function," weak and easily overwhelmed by strong emotional signals (by design: these are primitive creatures).

**Inputs (tract projections from):**
| Source | Size | Tract name |
|--------|------|------------|
| Thalamus output (attention) | 40 | `tract_thal_pfc` |
| Amygdala output (emotion) | 16 | `tract_amyg_pfc` |
| Hippocampus output (context) | 16 | `tract_hipp_pfc` |
| driv (drives) | 20 | `tract_driv_pfc` |
| verb (last action) | 17 | `tract_verb_pfc` |
| noun (last category) | 40 | `tract_noun_pfc` |
| resp (response history) | 20 | `tract_resp_pfc` |
| stim (stimulus) | 40 | `tract_stim_pfc` |
| chemicals (selected) | 16 | `tract_chem_pfc` |
| LTM injection (Phase 4B) | 6 | `tract_ltm_pfc` (zeroed until 4B) |

**Effective input size:** Sum of tract outputs (default 60).

**NCP Wiring:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| inter_neurons | 32 | Largest module: must integrate many signals |
| command_neurons | 16 | Complex integration task |
| motor_neurons | 17 | Decision output (one per action) |
| sensory_fanout | 12 | Wide fanout: many input sources |
| inter_fanout | 8 | |
| recurrent_command_synapses | 16 | Moderate recurrence: decisions shouldn't be too sticky |
| motor_fanin | 8 | |

**Total neurons:** 65 (32 + 16 + 17)

**Time constant bias:** Moderate (initialise `time_b` near zero). Deliberation speed sits between attention (fast) and context (slow).

**Output:** 17-dimensional decision vector. `decn_winner = argmax(output)`.

### Total Architecture Summary

| Module | Inter | Command | Motor | Total | Output |
|--------|-------|---------|-------|-------|--------|
| Thalamus | 20 | 10 | 40 | 70 | attn (40) |
| Amygdala | 24 | 12 | 16 | 52 | emotion (16) |
| Hippocampus | 24 | 12 | 16 | 52 | context (16) |
| Prefrontal | 32 | 16 | 17 | 65 | decn (17) |
| **Total** | **100** | **50** | **89** | **239** | **89** |

239 total CfC neurons across 4 modules (vs 187 in the monolithic brain). The increase is modest and well within real-time inference budget.

---

## 5. Tract Projection System

### What is a Tract?

A tract is a learnable linear projection that transforms one input source's values for a target module. Tracts are the inter-module wiring: they replace the dense input layer of the monolithic CfC with structured, genetically-parameterised connections.

### Tract Implementation

```python
class Tract(nn.Module):
    """Learnable sparse projection between an input source and a CfC module.

    Mirrors the C3 brain's tract genes: each tract connects a source lobe
    to a destination lobe with a specific number of connections per neuron.
    The connection mask is genetic (fixed per creature, heritable).
    The weights are learned through training.
    """

    def __init__(self, src_size: int, dst_size: int,
                 n_connections: int, seed: int = 42):
        super().__init__()
        self.src_size = src_size
        self.dst_size = dst_size

        # Learnable weight matrix
        self.weight = nn.Parameter(torch.zeros(dst_size, src_size))
        nn.init.xavier_uniform_(self.weight)

        # Genetic connection mask (not learned: fixed per creature)
        rng = np.random.RandomState(seed)
        mask = np.zeros((dst_size, src_size), dtype=np.float32)
        for dst in range(dst_size):
            src_indices = rng.choice(src_size,
                                     size=min(n_connections, src_size),
                                     replace=False)
            mask[dst, src_indices] = 1.0
        self.register_buffer('mask', torch.from_numpy(mask))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Project input through masked weights."""
        return F.linear(x, self.weight * self.mask)

    @property
    def active_connections(self) -> int:
        return int(self.mask.sum().item())
```

### Tract Configuration Table

Each tract has a genetic specification:

| Tract name | Source | Src size | Dest module | Dst size | Connections/neuron | Notes |
|-----------|--------|----------|-------------|----------|-------------------|-------|
| `tract_visn_thal` | visn | 40 | Thalamus | 10 | 8 | Primary visual attention |
| `tract_smel_thal` | smel | 40 | Thalamus | 10 | 8 | Smell-guided attention |
| `tract_driv_thal` | driv | 20 | Thalamus | 10 | 6 | Drive-modulated attention |
| `tract_prox_thal` | prox | 20 | Thalamus | 10 | 6 | Proximity-based attention |
| `tract_driv_amyg` | driv | 20 | Amygdala | 8 | 6 | Drive→emotion |
| `tract_stim_amyg` | stim | 40 | Amygdala | 8 | 8 | Stimulus→emotion |
| `tract_chem_amyg` | chemicals | 16 | Amygdala | 8 | 6 | Biochemistry→emotion |
| `tract_sitn_hipp` | sitn | 9 | Hippocampus | 4 | 4 | Situation→context |
| `tract_detl_hipp` | detl | 11 | Hippocampus | 4 | 4 | Detail→context |
| `tract_noun_hipp` | noun | 40 | Hippocampus | 4 | 8 | Category→context |
| `tract_verb_hipp` | verb | 17 | Hippocampus | 4 | 6 | Action→context |
| `tract_loc_hipp` | location | 2 | Hippocampus | 4 | 2 | Position→context |
| `tract_thal_pfc` | Thalamus out | 40 | Prefrontal | 10 | 10 | Attention→decision |
| `tract_amyg_pfc` | Amygdala out | 16 | Prefrontal | 8 | 8 | Emotion→decision |
| `tract_hipp_pfc` | Hippocampus out | 16 | Prefrontal | 6 | 6 | Context→decision |
| `tract_driv_pfc` | driv | 20 | Prefrontal | 8 | 6 | Direct drive→decision |
| `tract_verb_pfc` | verb | 17 | Prefrontal | 4 | 6 | Action history→decision |
| `tract_noun_pfc` | noun | 40 | Prefrontal | 4 | 8 | Category history→decision |
| `tract_resp_pfc` | resp | 20 | Prefrontal | 4 | 6 | Response→decision |
| `tract_stim_pfc` | stim | 40 | Prefrontal | 4 | 8 | Stimulus→decision |
| `tract_chem_pfc` | chemicals | 16 | Prefrontal | 6 | 6 | Biochemistry→decision |
| `tract_ltm_pfc` | LTM injection | 6 | Prefrontal | 6 | 6 | Memory→decision (Phase 4B) |

### Genetic Parameterisation

Each tract's specification is a genome entry:

```python
tract_gene = {
    "name": "tract_visn_thal",
    "src_id": "visn",
    "src_size": 40,
    "dst_module": "thalamus",
    "dst_size": 10,
    "connections_per_neuron": 8,
    "seed": 42,           # Controls which specific connections exist
    "enabled": True,       # Can be toggled by mutation
}
```

**Mutations can:**
- Change `connections_per_neuron` (sparser or denser connections)
- Change `dst_size` (how much information passes through)
- Change `seed` (rewires which specific neurons connect)
- Toggle `enabled` (add or remove entire pathways)
- All NCP wiring parameters per module are similarly genetic

**Mutations cannot:**
- Change `src_size` (fixed by the game's lobe structure)
- Create connections to non-existent inputs

---

## 6. Input Assembly

### Sensory Input Sources

The multi-lobe brain receives the same raw data as the monolithic brain (from `BrainStateReader` DMPL reads + chemical reads), but routes it to different modules via tracts rather than concatenating into a flat vector.

**Input routing:**

```python
# Raw inputs from bridge (same as NornBrainFull)
raw_inputs = {
    "driv": tensor(20),    # Drive lobe values
    "verb": tensor(17),    # Verb lobe values
    "noun": tensor(40),    # Noun lobe values
    "visn": tensor(40),    # Vision lobe values
    "smel": tensor(40),    # Smell lobe values
    "sitn": tensor(9),     # Situation lobe values
    "detl": tensor(11),    # Detail lobe values
    "resp": tensor(20),    # Response lobe values
    "prox": tensor(20),    # Proximity lobe values
    "stim": tensor(40),    # Stim source lobe values
    "chemicals": tensor(256),  # Full 256-chemical array
    "location": tensor(2),     # posx, posy (normalised 0-1)
}
```

**Chemical selection for tracts:**
The full 256-chemical array is indexed to extract the 16 behaviourally-relevant chemicals:

```python
AMYGDALA_CHEM_INDICES = [
    204,  # reward
    205,  # punishment
    117,  # adrenaline
    161,  # fear (drive chemical)
    160,  # anger (drive chemical)
    148,  # pain (drive chemical)
    149,  # hunger_protein (drive chemical)
    150,  # hunger_carb (drive chemical)
    151,  # hunger_fat (drive chemical)
    156,  # loneliness (drive chemical)
    159,  # boredom (drive chemical)
    162,  # sex_drive (drive chemical)
    163,  # comfort (drive chemical)
    128,  # stress
    127,  # injury
    125,  # life
]

# Same indices used for PFC chemical tract
PFC_CHEM_INDICES = AMYGDALA_CHEM_INDICES
```

### LTM Injection Channels (Phase 4B placeholder)

Six input channels reserved for LTM memory injection, zeroed until Phase 4B:

```python
ltm_injection = {
    "mem1_valence": 0.0,   # Top matching memory valence
    "mem1_arousal": 0.0,   # Top matching memory arousal
    "mem2_valence": 0.0,   # Second matching memory valence
    "mem2_arousal": 0.0,   # Second matching memory arousal
    "mem3_valence": 0.0,   # Third matching memory valence
    "mem3_arousal": 0.0,   # Third matching memory arousal
}
```

---

## 7. Output Assembly

### From Module Outputs to BrainOutput

The final output assembly is simple:

```python
# Thalamus produces attention motor neurons
attn_values = thalamus.output      # (40,)
attn_winner = argmax(attn_values)  # int 0-39

# Prefrontal produces decision motor neurons
decn_values = prefrontal.output    # (17,)
decn_winner = argmax(decn_values)  # int 0-16

# Assemble BrainOutput (same dataclass as monolithic brain)
output = BrainOutput(
    attention_values=attn_values,
    decision_values=decn_values,
    attention_winner=attn_winner,
    decision_winner=decn_winner,
    attention_label=ATTENTION_LABELS[attn_winner],
    decision_label=DECISION_LABELS[decn_winner],
    all_activations=concat(thal_hidden, amyg_hidden, hipp_hidden, pfc_hidden),
    tick=tick_count,
)
```

### Bridge Compatibility

The bridge client (`brain_bridge_client.py`) calls `brain.tick(input)` and receives a `BrainOutput`. This interface is unchanged. The bridge does not need to know whether the brain is monolithic or multi-lobe. The only change is:

1. Input grows from 513 to 519 dimensions (6 LTM channels, zeroed in 4A)
2. `all_activations` grows from 187 to 239 dimensions (sum of all module hidden states)
3. `get_wiring_info()` returns per-module wiring info instead of a single wiring

---

## 8. Training Pipeline

### Behaviour Cloning (Supervised)

The training pipeline (`train.py`) requires minimal changes:

1. **Data format:** Unchanged. Observation dicts from `observer.py` still contain `{lobes, chemicals, attn_winner, decn_winner}`.

2. **Forward pass:** Instead of one `model(input_seq, hx)` call, the multi-lobe brain:
   a. Routes raw inputs through tracts to assemble per-module inputs
   b. Runs Thalamus, Amygdala, Hippocampus in parallel (no data dependency)
   c. Runs Prefrontal with outputs from step (b) plus additional raw inputs
   d. Returns attention output from Thalamus, decision output from Prefrontal

3. **Loss function:** Same: cross-entropy on attention and decision outputs:
   ```python
   loss = CE(thalamus_output, attn_target) + CE(prefrontal_output, decn_target)
   ```

4. **Gradient flow:** Gradients from the decision loss flow back through the Prefrontal, through the inter-module tracts, and into the Thalamus/Amygdala/Hippocampus. All modules are updated end-to-end. The tract projections are part of the computation graph and receive gradients.

5. **Optimiser:** Single Adam optimiser over all parameters (all modules + all tracts). Per-module learning rates can be achieved via parameter groups:
   ```python
   optimizer = Adam([
       {"params": thalamus.parameters(), "lr": 0.005},
       {"params": amygdala.parameters(), "lr": 0.003},
       {"params": hippocampus.parameters(), "lr": 0.002},
       {"params": prefrontal.parameters(), "lr": 0.005},
       {"params": tracts.parameters(), "lr": 0.005},
   ])
   ```

### Online Reinforcement Learning (REINFORCE)

Same algorithm as the monolithic brain, but applied to the multi-module architecture:

1. **Reward signal:** `reward = chem_204 - chem_205` (unchanged)
2. **Policy gradient:** Applied to both Thalamus (attention) and Prefrontal (decision) outputs
3. **All modules updated:** Gradients flow through the entire graph. The Amygdala and Hippocampus receive gradient signal even though they don't directly produce the RL-trained outputs: their contribution to the Prefrontal input is part of the policy.
4. **Gradient clipping:** Applied per-module to prevent catastrophic updates:
   ```python
   for module in [thalamus, amygdala, hippocampus, prefrontal]:
       clip_grad_norm_(module.parameters(), max_norm=1.0)
   ```
5. **Baseline subtraction:** Subtract a running average of recent rewards to reduce REINFORCE variance:
   ```python
   self._reward_baseline = 0.99 * self._reward_baseline + 0.01 * reward
   advantage = reward - self._reward_baseline
   loss = -advantage * (log_prob_attn + log_prob_decn)
   ```
6. **Entropy bonus:** Add action distribution entropy to prevent premature convergence:
   ```python
   entropy = -(attn_probs * torch.log(attn_probs + 1e-8)).sum()
   entropy += -(decn_probs * torch.log(decn_probs + 1e-8)).sum()
   loss = loss - 0.01 * entropy  # Encourage exploration
   ```

### Pre-training Strategy (Optional)

For faster initial convergence, modules can be pre-trained independently:

1. **Thalamus pre-training:** Train on `(visn+smel+driv+prox) → attn_winner` alone. This teaches basic attention before the decision module exists.
2. **Prefrontal pre-training:** With a frozen Thalamus, train on `(all inputs) → decn_winner`. This teaches decision-making with a stable attention signal.
3. **End-to-end fine-tuning:** Unfreeze all modules, fine-tune jointly.

This mirrors how the biological brain develops: sensory processing matures before executive function.

---

## 9. Inference Performance

### Per-tick Compute Budget

The bridge poll loop runs at 20ms intervals. CfC inference must complete well within this.

**Monolithic brain:** Single forward pass through 187-neuron CfC = ~0.5ms (measured).

**Multi-lobe brain estimate:**
- 4 CfC forward passes (70 + 52 + 52 + 65 neurons) = ~4 × 0.3ms = ~1.2ms
- 22 tract projections (small linear layers) = ~0.2ms
- Input routing + output assembly = ~0.1ms
- **Total estimate: ~1.5ms**: well within the 20ms budget

### Memory

- 4 hidden state vectors: 70 + 52 + 52 + 65 = 239 floats = ~1KB
- Tract parameters: ~22 small weight matrices = ~10KB
- Model parameters total: comparable to monolithic (~50K parameters)

---

## 10. File Structure

### New Files

```
phase1-prototype/
    multi_lobe_brain.py          # MultiLobeBrain class (main)
    tract.py                     # Tract projection class
    brain_genome.py              # Genome config for genetic variation
    tests/
        test_multi_lobe.py       # Unit tests for multi-lobe architecture
```

### Modified Files

```
phase2-bridge/
    brain_bridge_client.py       # Import MultiLobeBrain, use same interface
    train.py                     # Support multi-lobe training mode
```

### Unchanged Files

```
phase2-bridge/
    c2e_bridge.py               # No changes
    brain_reader.py             # No changes (same DMPL reads)
    observer.py                 # No changes (same observation format)
    nornbrain_bridge.cos        # No changes (same CAOS protocol)
    lobe_map.py                 # No changes
phase1-prototype/
    norn_brain.py               # Kept as-is (monolithic brain still available)
    scenarios.py                # No changes
    server.py                   # Dashboard updates (separate task)
```

---

## 11. Genome Configuration

The multi-lobe brain's architecture is fully parameterised by a genome dict:

```python
DEFAULT_GENOME = {
    "version": 1,
    "seed": 42,

    # Module specifications
    "modules": {
        "thalamus": {
            "inter_neurons": 20,
            "command_neurons": 10,
            "motor_neurons": 40,
            "sensory_fanout": 8,
            "inter_fanout": 6,
            "recurrent_command_synapses": 10,
            "motor_fanin": 6,
            "time_bias": "fast",       # Initialisation bias
        },
        "amygdala": {
            "inter_neurons": 24,
            "command_neurons": 12,
            "motor_neurons": 16,
            "sensory_fanout": 8,
            "inter_fanout": 6,
            "recurrent_command_synapses": 12,
            "motor_fanin": 6,
            "time_bias": "mixed",
        },
        "hippocampus": {
            "inter_neurons": 24,
            "command_neurons": 12,
            "motor_neurons": 16,
            "sensory_fanout": 6,
            "inter_fanout": 6,
            "recurrent_command_synapses": 16,
            "motor_fanin": 6,
            "time_bias": "slow",
        },
        "prefrontal": {
            "inter_neurons": 32,
            "command_neurons": 16,
            "motor_neurons": 17,
            "sensory_fanout": 12,
            "inter_fanout": 8,
            "recurrent_command_synapses": 16,
            "motor_fanin": 8,
            "time_bias": "moderate",
        },
    },

    # Tract specifications
    "tracts": {
        "tract_visn_thal": {"src": "visn", "src_size": 40, "dst_module": "thalamus", "dst_size": 10, "connections": 8, "enabled": True},
        "tract_smel_thal": {"src": "smel", "src_size": 40, "dst_module": "thalamus", "dst_size": 10, "connections": 8, "enabled": True},
        "tract_driv_thal": {"src": "driv", "src_size": 20, "dst_module": "thalamus", "dst_size": 10, "connections": 6, "enabled": True},
        "tract_prox_thal": {"src": "prox", "src_size": 20, "dst_module": "thalamus", "dst_size": 10, "connections": 6, "enabled": True},
        "tract_driv_amyg": {"src": "driv", "src_size": 20, "dst_module": "amygdala", "dst_size": 8, "connections": 6, "enabled": True},
        "tract_stim_amyg": {"src": "stim", "src_size": 40, "dst_module": "amygdala", "dst_size": 8, "connections": 8, "enabled": True},
        "tract_chem_amyg": {"src": "chemicals", "src_size": 16, "dst_module": "amygdala", "dst_size": 8, "connections": 6, "enabled": True},
        "tract_sitn_hipp": {"src": "sitn", "src_size": 9, "dst_module": "hippocampus", "dst_size": 4, "connections": 4, "enabled": True},
        "tract_detl_hipp": {"src": "detl", "src_size": 11, "dst_module": "hippocampus", "dst_size": 4, "connections": 4, "enabled": True},
        "tract_noun_hipp": {"src": "noun", "src_size": 40, "dst_module": "hippocampus", "dst_size": 4, "connections": 8, "enabled": True},
        "tract_verb_hipp": {"src": "verb", "src_size": 17, "dst_module": "hippocampus", "dst_size": 4, "connections": 6, "enabled": True},
        "tract_loc_hipp":  {"src": "location", "src_size": 2, "dst_module": "hippocampus", "dst_size": 4, "connections": 2, "enabled": True},
        "tract_thal_pfc":  {"src": "thalamus_out", "src_size": 40, "dst_module": "prefrontal", "dst_size": 10, "connections": 10, "enabled": True},
        "tract_amyg_pfc":  {"src": "amygdala_out", "src_size": 16, "dst_module": "prefrontal", "dst_size": 8, "connections": 8, "enabled": True},
        "tract_hipp_pfc":  {"src": "hippocampus_out", "src_size": 16, "dst_module": "prefrontal", "dst_size": 6, "connections": 6, "enabled": True},
        "tract_driv_pfc":  {"src": "driv", "src_size": 20, "dst_module": "prefrontal", "dst_size": 8, "connections": 6, "enabled": True},
        "tract_verb_pfc":  {"src": "verb", "src_size": 17, "dst_module": "prefrontal", "dst_size": 4, "connections": 6, "enabled": True},
        "tract_noun_pfc":  {"src": "noun", "src_size": 40, "dst_module": "prefrontal", "dst_size": 4, "connections": 8, "enabled": True},
        "tract_resp_pfc":  {"src": "resp", "src_size": 20, "dst_module": "prefrontal", "dst_size": 4, "connections": 6, "enabled": True},
        "tract_stim_pfc":  {"src": "stim", "src_size": 40, "dst_module": "prefrontal", "dst_size": 4, "connections": 8, "enabled": True},
        "tract_chem_pfc":  {"src": "chemicals", "src_size": 16, "dst_module": "prefrontal", "dst_size": 6, "connections": 6, "enabled": True},
        "tract_ltm_pfc":   {"src": "ltm", "src_size": 6, "dst_module": "prefrontal", "dst_size": 6, "connections": 6, "enabled": True},
    },
}
```

This genome dict is serialisable to JSON. Two creatures with different genomes will have different brain architectures: different neuron counts, different tract wiring, different time constant biases. This is the foundation for Phase 5 genetic evolution.

---

## 12. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Multi-module training doesn't converge | High | Medium | Pre-training strategy (Section 8). Fall back to larger learning rates. Monolithic brain remains available as baseline. |
| Time constant initialisation doesn't produce desired module-specific dynamics | Medium | Low | The `timespans` parameter can also be varied per-module at inference time (pass different `ts` values to different CfC forward calls). |
| Tract projections bottleneck information | Medium | Medium | Monitor tract output dimensionality. If a tract's dst_size is too small, important information is lost. Increase dst_size in genome. |
| 239 neurons too slow for real-time | Low | Very Low | Estimated 1.5ms per tick (Section 9). Monolithic 187-neuron brain runs in 0.5ms. Even 3x slowdown is well within 20ms budget. |
| Dashboard incompatibility | Low | Low | `all_activations` format changes but is still a flat numpy array. Dashboard needs per-module labelling but this is a display change, not a data change. |

---

## 13. Forward Compatibility

### Phase 4B (LTM System)
The `tract_ltm_pfc` is defined and zeroed. Phase 4B fills in the 6 LTM injection channels. No architectural changes needed: just populate the values.

### Phase 4C (Emotional Hierarchy)
The Amygdala module's output already feeds into the Prefrontal. Phase 4C adds the intensity-based dominance system that modulates how strongly the Amygdala signal affects the Prefrontal's decision. This can be implemented as a gating mechanism on `tract_amyg_pfc` without changing the module architecture.

### Phase 4D (Language)
Language output would add a 5th output head (speech) to the Prefrontal module, or a separate small module receiving Prefrontal hidden state. The multi-lobe architecture accommodates this cleanly: adding a module or output head doesn't require restructuring existing modules.

### Phase 5 (Genetic Evolution)
The genome dict (Section 11) is already structured for mutation and crossover. Each parameter is independently mutable. Tract `enabled` flags allow pathway addition/removal. Module neuron counts allow brain size variation. This is the primary architectural foundation for genetic evolution.
