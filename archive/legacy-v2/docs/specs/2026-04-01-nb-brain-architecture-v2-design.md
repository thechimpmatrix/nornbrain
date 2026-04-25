# NB Brain Architecture v2: Hierarchical CfC with Signal-Type Differentiation

**Date:** 2026-04-01
**Status:** SPEC: awaiting user review
**Supersedes:** Phase 4A multi-lobe CfC design (2026-03-30)

---

## 1. Overview

Redesign the NB CfC brain from a flat 4-module feedforward architecture (239 neurons) to a hierarchical mammalian-inspired architecture (11,000 neurons) with three differentiated signal types, bidirectional inter-module flows, and ONNX Runtime inference for native-speed execution.

The architecture is derived from a user-drawn diagram of mammalian brain connectivity and validated against neuroscience principles. Each module has a distinct biological role. Information flows through specific pathways with distinct computational semantics (data, modulation, memory).

---

## 2. Design Principles

1. **Signal-type differentiation**: Three distinct input pathways per module: data inputs concatenate (information flow), modulation inputs multiply against hidden state (gain control), memory inputs go through a retrieval gate. The CfC doesn't have to learn that drives modulate rather than inform: the architecture enforces it.

2. **Hierarchical processing**: Thalamus is the sensory gateway. Hippocampus and amygdala are parallel evaluators. Frontal cortex integrates everything. Not four peers: a hierarchy.

3. **Bidirectional flows**: Hippocampus and amygdala talk to each other AND feed back to thalamus. This creates a resonance loop where sensory processing, emotional evaluation, and memory context mutually influence each other before the frontal cortex decides.

4. **Dual-speed potential**: The architecture supports future dual-speed operation: fast amygdala pathway for reactive survival behaviours, slow full-circuit pathway for deliberative decisions.

5. **ONNX inference**: Train in Python/PyTorch, export to ONNX, run inference in C++ via ONNX Runtime. ~20x speedup over pybind11, enabling 11,000 neurons at ~200ms (5 tps: matching the original C3 brain tick rate).

6. **Modular instinct system**: Pre-trained genome weights from the instincts.py rule definitions. Every norn is born knowing survival behaviours. RL refines from there.

---

## 3. Module Architecture

### 3.1 Module Sizing

| Module | Neurons | % of Brain | Biological Role |
|--------|--------:|:----------:|-----------------|
| Thalamus | 1,600 | 14.5% | Sensory relay hub with drive-based gain modulation |
| Amygdala | 1,100 | 10% | Emotional evaluation, valence tagging, LTM salience painting |
| Hippocampus | 1,600 | 14.5% | Contextual/spatial memory, LTM encoding, environment model |
| Frontal Cortex | 6,700 | 61% | Executive integration, attention selection, action decision |
| **Total** | **11,000** | **100%** | |

### 3.2 Per-Module NCP Wiring

Each module is an independent CfC instance with NCP (Neural Circuit Policy) wiring. The NCP structure within each module:

```
sensory neurons → inter neurons → command neurons → motor neurons
```

Distribution per module (approximate: tunable via genome):

| Module | Sensory | Inter | Command | Motor | Output |
|--------|--------:|------:|--------:|------:|--------|
| Thalamus | 400 | 500 | 300 | 400 | Filtered sensory (400-dim) |
| Amygdala | 250 | 350 | 250 | 250 | Emotional valence (250-dim) |
| Hippocampus | 400 | 500 | 300 | 400 | Context representation (400-dim) |
| Frontal Cortex | 1,500 | 2,200 | 1,500 | 1,500 | ATTN (40) + DECN (17) + internal |

### 3.3 Time Constant Biases

| Module | Time Bias | Rationale |
|--------|-----------|-----------|
| Thalamus | Fast | Sensory relay: quick response to input changes |
| Amygdala | Mixed (fast react, slow decay) | Quick emotional response, slow emotional recovery |
| Hippocampus | Slow | Context builds gradually, persists across events |
| Frontal Cortex | Moderate | Balanced deliberation speed |

---

## 4. Signal Types

Every input to every module is classified as exactly one of three signal types. The signal type determines HOW the input is computationally integrated: this is enforced architecturally, not learned.

### 4.1 Data (blue/red in diagram)

**Semantics:** Raw information. "What is happening."
**Computation:** Concatenated into the module's input tensor, fed through the CfC sensory layer normally.
**Example:** Vision data to thalamus: the raw pixel-level category activations.

### 4.2 Modulation (yellow in diagram)

**Semantics:** Gain control. "How much to amplify or dampen." Does not carry content: scales existing processing.
**Computation:** Multiplied element-wise against the module's hidden state after the CfC update step. A modulation value of 1.0 = no effect. >1.0 = amplify. <1.0 = dampen. 0.0 = suppress.
**Example:** Drives modulating thalamus: hunger amplifies food-related sensory processing.

Implementation:
```python
# After CfC forward pass:
h_new = cfc_step(data_inputs, h_old, dt)
# Apply modulation:
mod_gate = sigmoid(W_mod @ modulation_inputs + b_mod)  # [0, 1] range
h_new = h_new * mod_gate  # element-wise gain control
```

### 4.3 Memory (purple in diagram)

**Semantics:** Contextual/experiential information. "What has been remembered about this."
**Computation:** Passed through a gating mechanism that controls how much memory influences the current state. The gate is learned: the module learns when to trust memory vs current sensory input.
**Example:** LTM feeding frontal cortex: recalled past experience about this situation.

Implementation:
```python
# Memory gating:
mem_gate = sigmoid(W_mem_gate @ torch.cat([h_new, memory_inputs]) + b_gate)
mem_contribution = tanh(W_mem_val @ memory_inputs + b_val)
h_new = h_new + mem_gate * mem_contribution
```

---

## 5. Complete Wiring Map

### 5.1 External Inputs to Modules

| Source | Thalamus | Hippocampus | Amygdala | Frontal Cortex | Signal Type |
|--------|:--------:|:-----------:|:--------:|:--------------:|-------------|
| visn (40) | DATA | | DATA | | Raw vision categories |
| smel (40) | DATA | | DATA | | Raw smell categories |
| prox (20) | DATA | MOD | MOD | | Proximity: data to thal, modulates hipp+amyg |
| sitn (9) | DATA | MOD | MOD | | Situation: data to thal, modulates hipp+amyg |
| driv (20) | MOD | | MOD | | Drives modulate thalamus and amygdala |
| loc (2) | DATA | MEM | | | Location: data to thal, memory-context to hipp |
| stim (40) | DATA | MEM | | | Stimulus source: data to thal, memory-context to hipp |
| detl (11) | DATA | MEM | | | Detail: data to thal, memory-context to hipp |
| chem (16) | | | MOD | MOD | Biochemistry modulates amygdala and FC |
| noun (40) | | | | DATA | Language noun: direct to FC |
| verb (17) | | | | DATA | Language verb: direct to FC |
| ltm (varies) | | | | MEM | Long-term memory recall: memory to FC |

### 5.2 Inter-Module Flows

| From | To | Signal Type | Meaning |
|------|-----|-------------|---------|
| Thalamus | Hippocampus | DATA | Filtered sensory feeds context building |
| Thalamus | Amygdala | DATA | Filtered sensory feeds emotional evaluation |
| Thalamus | Frontal Cortex | DATA | Fast pathway: sensory direct to decisions |
| Hippocampus | Amygdala | MEM | Context informs emotional evaluation |
| Amygdala | Hippocampus | DATA | Emotional state informs context building |
| Hippocampus | Thalamus | MEM | Memory context re-gates sensory processing |
| Amygdala | Thalamus | MOD | Emotional arousal modulates sensory gain |
| Hippocampus | Frontal Cortex | DATA | Context understanding for decisions |
| Amygdala | Frontal Cortex | DATA | Emotional evaluation for decisions |

### 5.3 LTM Integration

| From | To | Signal Type | Meaning |
|------|-----|-------------|---------|
| Hippocampus | LTM (write) | DATA | Encodes new memories from context state |
| Amygdala | LTM (paint) | MOD | Emotional salience modulates memory strength |
| LTM | Frontal Cortex | MEM | Recalled memories gate FC processing |

### 5.4 Outputs

| From | Output | Signal Type | Meaning |
|------|--------|-------------|---------|
| Frontal Cortex | ATTN (40) | Output | Attention winner: what to focus on |
| Frontal Cortex | DECN (14 active) | Output | Decision winner: what action to do |
| Frontal Cortex | resp (20) | Output | Response/expressive state (if output in engine) |

---

## 6. Processing Order

Because of bidirectional flows, processing order matters. Each brain tick executes in this order:

```
1. Gather external inputs (lobes + chemicals from C++)
2. THALAMUS tick
   - Data inputs: visn, smel, prox, sitn, loc, stim, detl
   - Modulation: driv, amygdala_feedback (from previous tick)
   - Memory: hippocampus_feedback (from previous tick)
   → produces: thalamus_output
3. HIPPOCAMPUS tick
   - Data inputs: thalamus_output, amygdala_output (from previous tick)
   - Modulation: prox, sitn
   - Memory: loc, stim, detl
   → produces: hippocampus_output
   → writes to LTM
4. AMYGDALA tick
   - Data inputs: visn, smel, thalamus_output, hippocampus_output
   - Modulation: driv, prox, sitn, chem
   → produces: amygdala_output
   → paints LTM (modulates memory strength)
5. FRONTAL CORTEX tick
   - Data inputs: thalamus_output, hippocampus_output, amygdala_output, noun, verb
   - Modulation: chem
   - Memory: ltm_recall
   → produces: ATTN winner, DECN winner
6. Store inter-module outputs for next tick's feedback paths
```

Note: hippocampus and amygdala use each other's PREVIOUS tick output, not current. This avoids circular dependency within a single tick while maintaining bidirectional influence across ticks. This matches biological neural transmission delays.

---

## 7. ONNX Runtime Integration

### 7.1 Architecture

```
Training (offline, Python):
  instincts.py rules → synthetic data → PyTorch MultiLobeBrainV2 → train → save .pt weights

Export (one-time, Python):
  Load .pt weights → torch.onnx.export() → brain_v2.onnx

Inference (runtime, C++):
  NB engine → OnnxBrain.cpp loads brain_v2.onnx → ONNX Runtime session
  Each tick: gather inputs → ort::Session::Run() → read ATTN/DECN outputs
```

### 7.2 C++ Integration

Replace PythonBrain with OnnxBrain: same interface (subclass of c2eBrain), same virtual methods (init, tick, processGenes), but calls ONNX Runtime instead of Python.

```cpp
class OnnxBrain : public c2eBrain {
    Ort::Session session_;
    std::vector<float> input_buffer_;
    std::vector<float> output_buffer_;

    void tick() override {
        gather_inputs(input_buffer_);
        auto result = session_.Run(input_buffer_);
        apply_outputs(result);
    }
};
```

No Python interpreter at runtime. No GIL. No pybind11. No tensor marshalling.

### 7.3 Engine Flag

```bash
# Python brain (development/training):
openc2e.exe --brain-module nornbrain_cfc.py

# ONNX brain (production/performance):
openc2e.exe --brain-onnx brain_v2.onnx
```

Both flags supported simultaneously. Python for development, ONNX for performance.

### 7.4 Performance Target

| Metric | Python/PyTorch | ONNX Runtime |
|--------|---------------:|-------------:|
| 11,000 neurons | ~4 seconds | ~200ms |
| TPS | 0.25 | **5.0** |
| Game feel | Unplayable | Original C3 speed |

---

## 8. Instinct Pre-Training (Existing System, Scaled)

The instinct pre-training system (instincts.py, pretrain_instincts.py) already works. For v2:

1. Same instinct rules (33 rules, human-readable, tweakable)
2. Scale `samples_per_weight` from 50 to 500+ (more data for larger model)
3. Generate additional synthetic diversity:
   - Multiple drive levels per rule (not just above-threshold)
   - Compound drives (hungry AND tired: which wins?)
   - Distractor-heavy scenarios (food visible but grendel also visible)
4. Pre-train all 4 modules simultaneously via the existing `train_on_observations()` interface
5. Export to ONNX after training

### 8.1 Weight Lifecycle

```
genome_weights.onnx    : born with (from instinct pre-training)
     ↓ RL experience
learned_weights.pt     : accumulated experience (PyTorch, for further training)
     ↓ export
learned_weights.onnx   : deployed for fast inference
```

---

## 9. LTM System Integration

The LTM system (designed in Phase 4B spec) integrates with the new architecture:

| Component | Writer | Reader | Modulator |
|-----------|--------|--------|-----------|
| LTM bank | Hippocampus | Frontal Cortex | Amygdala |

**Hippocampus writes:** After each tick, if hippocampus output exceeds an intensity threshold, encode the current context (thalamus output + drives + location) as a memory record.

**Amygdala paints:** The amygdala's emotional output at encoding time sets the memory's salience weight. High emotional arousal = stronger memory. Fear-associated memories are weighted more heavily than neutral ones.

**Frontal Cortex reads:** At each tick, the FC's current input state is used as a retrieval key against LTM. Top-K most similar memories are returned as the `ltm` memory input, gated through the memory signal pathway.

**Consolidation:** During creature sleep (chem 213 > threshold), memories are replayed and strengthened/pruned. This matches C3's dream-state instinct processing.

---

## 10. Future: Genetics

The instinct rule system in `instincts.py` is the foundation for genetic evolution:

| Genetic Operation | What it does |
|-------------------|-------------|
| **Mutation** | Tweaks thresholds (0.15 → 0.20), swaps categories (food → fruit), flips actions (eat → approach), adjusts weights |
| **Crossover** | Blends parent instinct lists: child gets some rules from each parent |
| **Expression** | Each norn gets a personal copy of rules → pre-train → unique genome weights |
| **Selection** | Norns that survive and reproduce pass their instinct lists to offspring |

The genome is the instinct rule list. The phenotype is the pre-trained weight matrix. Evolution operates on the rules, not the weights.

---

## 11. Migration Path

### Phase 1: Python Prototype (this plan)
- Implement MultiLobeBrainV2 in Python with 3 signal types, bidirectional flows, new sizing
- Test with instinct pre-training at reduced scale (1,100 neurons = 1/10 for fast iteration)
- Validate in live engine via existing pybind11 path
- Verify architecture produces diverse, drive-appropriate behaviour

### Phase 2: Scale and Export
- Scale to full 11,000 neurons
- Train with expanded instinct dataset (500+ samples per weight)
- Export to ONNX
- Validate ONNX output matches PyTorch output (numerical equivalence test)

### Phase 3: C++ ONNX Integration
- Implement OnnxBrain.cpp (c2eBrain subclass)
- Add ONNX Runtime dependency to CMake
- Add `--brain-onnx` CLI flag
- Live test at 11,000 neurons / 5 tps

### Phase 4: RL and LTM
- Online RL via Python (training) with periodic ONNX re-export
- LTM write/read/paint integration
- Sleep consolidation

---

## 12. Files

| File | Action | Responsibility |
|------|--------|----------------|
| `phase1-prototype/multi_lobe_brain_v2.py` | Create | New brain class with 3 signal types, bidirectional flows |
| `phase1-prototype/signal_types.py` | Create | DataInput, ModulationInput, MemoryInput processing |
| `phase1-prototype/brain_genome_v2.py` | Create | V2 genome with new module sizes, signal routing |
| `openc2e/tools/nornbrain_cfc_v2.py` | Create | V2 brain wrapper for pybind11 (development) |
| `openc2e/tools/export_onnx.py` | Create | PyTorch → ONNX export script |
| `openc2e/src/openc2e/creatures/OnnxBrain.h` | Create | C++ ONNX Runtime brain subclass header |
| `openc2e/src/openc2e/creatures/OnnxBrain.cpp` | Create | C++ ONNX Runtime brain implementation |
| `openc2e/CMakeLists.txt` | Modify | Add ONNX Runtime dependency |
| `openc2e/src/openc2e/Engine.h/.cpp` | Modify | Add `--brain-onnx` CLI flag |
| `openc2e/src/openc2e/creatures/Creature.cpp` | Modify | OnnxBrain construction path |

---

## 13. Success Criteria

1. 11,000 neurons running at 5 tps via ONNX Runtime
2. Norn born with instinct-trained genome weights exhibits drive-appropriate behaviour from tick 0
3. Three signal types produce measurably different effects (modulation amplifies, memory gates, data informs)
4. Bidirectional flows create observable resonance (amygdala fear → thalamus amplifies threat sensory → stronger amygdala response)
5. Frontal cortex integrates all 7 input streams to produce diverse actions (diversity > 0.3 from birth)
6. RL reward/punishment signal trains the brain in real-time
7. Monitor displays all 11,000 neurons with module boundaries and signal-type colour coding

---

## 14. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| ONNX export fails for custom CfC architecture | High | LibTorch fallback; worst case keep pybind11 at reduced neuron count |
| 11,000 neurons overfit on 33 instinct rules | Medium | Scale synthetic data generation; add noise; RL provides ongoing data |
| Modulation signal type doesn't produce meaningful gain control | Medium | Fall back to concatenation if multiply doesn't train well |
| Bidirectional flows cause oscillation/instability | Medium | Previous-tick feedback (not current-tick) prevents tight loops |
| ONNX Runtime CMake integration on Windows | Low | Well-documented, NuGet package available |
| Training time for 11,000 neurons | Medium | Train at 1/10 scale first, validate, then scale up |
