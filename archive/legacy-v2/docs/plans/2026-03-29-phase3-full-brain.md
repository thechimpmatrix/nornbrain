# Phase 3: Full Brain Model: Implementation Plan


**Goal:** Scale to the full 12-lobe CfC brain (314 neurons) trained by observing the SVRule brain's actual decisions, then deploy as sole controller matching SVRule-level behaviour.

**Architecture:** Three phases: (A) build the observability infrastructure (binary shared memory reads, BRN:DMPL bulk lobe reader, full chemistry), (B) collect SVRule training data and train the CfC, (C) deploy and refine with RL. All work builds on existing Phase 2c bridge infrastructure.

**Tech Stack:** PyTorch CfC/NCP (existing), Win32 shared memory (existing), BRN:DMPL/DMPN CAOS commands (binary), FastAPI dashboard (existing).

**Key reference:** `docs/brn-dmpn-reference.md`: complete binary format, decode examples, lobe number table, SVRule semantics, performance analysis.

---

## Spec Reference

See: `docs/superpowers/specs/2026-03-29-phase3-full-brain-spec.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `phase2-bridge/brain_reader.py` | **Create** | BRN:DMPL-based brain state reader + full chemistry reader |
| `phase2-bridge/lobe_map.py` | **Create** | Verified lobe number table (from brn-dmpn-reference.md) |
| `phase2-bridge/observer.py` | **Create** | SVRule observation loop: reads brain state, records input→output pairs |
| `phase2-bridge/training_data/` | **Create (dir)** | Stored SVRule observation datasets (.pt files) |
| `phase1-prototype/norn_brain.py` | **Modify** | Scale NCP architecture to full lobe sizes |
| `phase1-prototype/scenarios.py` | **Modify** | Add SVRule-sourced scenarios from observation data |
| `phase2-bridge/c2e_bridge.py` | **Modify** | Add `execute_binary()` for raw binary shared memory reads |
| `phase2-bridge/brain_bridge_client.py` | **Modify** | Integrate brain_reader, replace GAME var reads with DMPL reads |
| `phase1-prototype/dashboard.html` | **Modify** | Add lobe-level visualization, SVRule observation view |

---

## Tasks

### Task 1: Add execute_binary() to c2e_bridge.py + encode lobe map

**Files:**
- Modify: `phase2-bridge/c2e_bridge.py` (add `execute_binary()` method)
- Create: `phase2-bridge/lobe_map.py`

**Part A: Binary shared memory read path (PREREQUISITE for all brain reading)**

The existing `execute()` method decodes shared memory responses as latin-1 text. All BRN:DMP commands return raw binary. Add `execute_binary()` that:
1. Sends the CAOS command via the same shared memory protocol
2. Reads the binary data length from shared memory offset 12 (uint32 LE)
3. Returns raw bytes from offset 24 (length from step 2), NOT text-decoded
4. Handles the "END DUMP\0" trailer (10 bytes appended after neuron data)

**Part B: Encode the known lobe map**

The lobe_number → quad ID mapping is fully documented in `docs/brn-dmpn-reference.md`. No empirical probing needed. Create `lobe_map.py` containing the verified table as a Python dict:

```python
LOBE_MAP = {
    0: {"id": "attn", "name": "attention",   "neurons": 40, "class": "output"},
    1: {"id": "decn", "name": "decision",    "neurons": 17, "class": "output"},
    2: {"id": "verb", "name": "verb",         "neurons": 17, "class": "input"},
    3: {"id": "noun", "name": "noun",         "neurons": 40, "class": "input"},
    4: {"id": "visn", "name": "vision",       "neurons": 40, "class": "input"},
    5: {"id": "smel", "name": "smell",        "neurons": 40, "class": "input"},
    6: {"id": "driv", "name": "drive",        "neurons": 20, "class": "input"},
    7: {"id": "sitn", "name": "situation",    "neurons":  9, "class": "input"},
    8: {"id": "detl", "name": "detail",       "neurons": 11, "class": "input"},
    9: {"id": "resp", "name": "response",     "neurons": 20, "class": "input"},
   10: {"id": "prox", "name": "proximity",    "neurons": 20, "class": "input"},
   11: {"id": "stim", "name": "stim source",  "neurons": 40, "class": "special"},
}
```

Add a verification function that reads BRN:DMPB from the live engine and confirms the lobe count matches (should report 12 lobes, though DMPB may report more depending on the creature's genetics: DMPB once reported 15 on a fallow norn; verify if extra entries are empty/degenerate).

---

### Task 2: Build brain_reader.py: BRN:DMPL-based full state reader

**Files:**
- Create: `phase2-bridge/brain_reader.py`

A class `BrainStateReader` that:
1. Takes a `C2eConnection` (with `execute_binary()` from Task 1) and the lobe map
2. Reads entire lobes via `BRN: DMPL lobe_number`: one binary call per lobe
3. Parses the DMPL response: 560-byte header, then neuron records at 40 bytes each
4. Extracts `variables[0]` (byte offset 8 within each 40-byte neuron record) as the primary output
5. Returns a dict of `{lobe_id: [float values]}`

Also includes a `read_all_chemicals()` method that reads all 256 chemicals in one CAOS text round-trip via `outv chem 0 outs " " outv chem 1 outs " " ...`.

**Performance targets:**
- Read all 12 lobes: 12 × ~5ms = **~60ms** (via DMPL bulk)
- Read output lobes only (attn + decn): 2 × ~5ms = **~10ms**
- Read all 256 chemicals: **<20ms** (single text CAOS round-trip)

**Key design decisions (resolved):**

1. **DMPL is the primary read path.** One shared memory round-trip per lobe, returning all neurons at once. This is 25x faster than individual DMPN calls (60ms vs 1.6s).

2. **BRN:GETN does not exist.** There is no text-mode command to read a single neuron value. Binary DMPL/DMPN are the only read paths. This was a critical unknown in earlier planning: now confirmed.

3. **DMPL header offset 560 is from LobeStudy reverse-engineering (medium confidence).** Verify empirically: read a known neuron via DMPN, then read the same lobe via DMPL and confirm the same float appears at `560 + (neuron_index × 40) + 8`. If the offset is wrong, scan the DMPL payload for the known float pattern.

4. **Neuron count cross-check:** DMPL header bytes 24-28 contain width and height (uint32 LE). `width × height` should equal the expected neuron count. Note: for stim lobe (40 neurons), DMPL previously returned width=5, height=17 (=85, not 40): investigate whether these are tile dimensions rather than neuron counts. Use the lobe_map's known neuron count as the authoritative count.

**Python decode pattern:**
```python
import struct

def read_lobe(bridge, lobe_number, expected_neurons):
    raw = bridge.execute_binary(f"targ norn brn: dmpl {lobe_number}")
    # Strip "END DUMP\0" trailer if present
    neuron_base = 560  # verify empirically
    neurons = []
    for i in range(expected_neurons):
        offset = neuron_base + (i * 40)
        input_val, nid, *states = struct.unpack_from('<fI8f', raw, offset)
        neurons.append(states[0])  # variables[0] = primary output
    return neurons
```

---

### Task 3: Build observer.py: SVRule observation data collector

**Files:**
- Create: `phase2-bridge/observer.py`

The observer:
1. Connects to C3
2. Every N seconds (configurable, default 1s: feasible since full brain read is ~60ms via DMPL):
   a. Reads all 12 lobes via BrainStateReader (DMPL bulk, ~60ms)
   b. Identifies attn and decn WTA winners from lobe 0 and 1 outputs
   c. Reads all 256 chemicals (~20ms)
   d. Stores the tuple: `{inputs: {...}, attn_winner: int, decn_winner: int, chemicals: [...], timestamp: float}`
3. Saves accumulated observations to a .pt file periodically
4. Runs for a configurable duration or until stopped

This generates the training dataset. Run it while the norn lives its life: the SVRule brain makes decisions, we record input→output pairs.

Target: collect 1000+ observations over ~30 minutes of norn life. With DMPL bulk reads, observation rate is ~10 samples/second (limited by bridge round-trip, not parsing).

---

### Task 4: Scale NornBrain to full architecture

**Files:**
- Modify: `phase1-prototype/norn_brain.py`

Expand the CfC/NCP model. All 12 lobes are accounted for: no unknown lobes:
- Input size: all 10 input lobes + stim lobe + 256 chemicals = driv 20 + verb 17 + noun 40 + visn 40 + smel 40 + sitn 9 + detl 11 + resp 20 + prox 20 + stim 40 + chem 256 = **513 inputs**
- Output: attn 40 + decn 17 = **57 outputs** (unchanged)
- Inter/command neurons: scale proportionally (e.g. 80 inter, 50 command)
- Total: ~187+ NCP neurons

Key decision: include ALL 256 chemicals as inputs, or just the ~20 most relevant? Start with all 256: the NCP wiring's sparsity will handle irrelevant inputs.

Add a `NornBrainFull` class alongside the existing `NornBrain` (keep the old one for backward compatibility).

---

### Task 5: Train CfC on SVRule observation data

**Files:**
- Modify: `phase1-prototype/norn_brain.py` (add `train_on_observations()` method)
- Modify: `phase2-bridge/brain_bridge_client.py` (add observation training commands)

Add a training method that:
1. Loads observation .pt files
2. For each observation: build input tensor from lobe values + chemicals, target = attn_winner + decn_winner
3. Train via cross-entropy loss (same as scenario training but on real data)
4. Report accuracy on held-out test set

This replaces hand-crafted scenarios with real SVRule behaviour.

---

### Task 6: Integrate and deploy

**Files:**
- Modify: `phase2-bridge/brain_bridge_client.py`

Wire everything together:
1. On startup, check for saved observation-trained weights
2. If available, load them
3. Run the full CfC brain with expanded input reads
4. Support switching between SPNL (overlay) and ZOMB+ORDR (sole control)

---

### Task 7: Dashboard updates

**Files:**
- Modify: `phase1-prototype/dashboard.html`

Add:
1. Lobe-level view: show all 12 lobes' neuron activations
2. SVRule vs CfC comparison: show what the SVRule brain decided vs what the CfC decided
3. Observation data collection status
4. Training on observation data

---

### Task 8: Integration test

1. Start C3 with new world
2. Run observer for 30 minutes collecting SVRule data
3. Train CfC on observation data
4. Deploy CfC in ZOMB+ORDR mode
5. Compare behaviour to SVRule baseline
6. Enable RL for refinement

---

## Anticipated Potholes

### P1: DMPL header offset unverified (560 bytes)
**Problem:** The 560-byte lobe header offset is from LobeStudy reverse-engineering ("worked out by guesswork"). If wrong, neuron data will be parsed at the wrong byte position.
**Mitigation:** Verify empirically in Task 2: write a known value via BRN:SETN lobe 6 neuron 0, read back via DMPN (confirmed format), then read same lobe via DMPL and scan for the matching float. Also cross-check width×height from header offsets 24/28. Note: stim lobe previously returned width=5, height=17 (=85) for 40 neurons: these may be tile dimensions, not neuron counts.

### P2: Binary shared memory read path missing (BLOCKER)
**Problem:** c2e_bridge.py currently decodes all shared memory responses as latin-1 text, which corrupts binary DMP data. Nothing in Phase 3 works without raw binary reads.
**Mitigation:** Implement `execute_binary()` in Task 1 as the very first step. Read binary data length from shared memory offset 12, return raw bytes from offset 24. Handle "END DUMP\0" trailer (10 bytes appended after payload).

### P3: SVRule brain overwrites during observation
**Problem:** Between reading input lobes and output lobes, the SVRule ticks and changes state.
**Mitigation:** With DMPL bulk reads (~60ms total for all 12 lobes), temporal skew is much smaller than with individual DMPN calls. Read output lobes (attn, decn) first since they're the training targets.

### P4: ZOMB+ORDR vocabulary issue
**Problem:** Newborn norns haven't learned vocabulary, ORDR WRIT commands are ignored
**Mitigation:** Teach vocabulary via `vocb` CAOS command before switching to ZOMB. Or use SPNL path exclusively (CfC biases the SVRule decision rather than replacing it).

### P5: CfC architecture too large for real-time inference
**Problem:** 513 inputs + 187 NCP neurons might be slow
**Mitigation:** CfC inference on CPU is still sub-1ms for this size. PyTorch overhead is the bottleneck, not the model size. If needed, reduce input dimensionality (PCA on chemicals).

### P5b: DMPB reports 15 lobes but only 12 are documented
**Problem:** BRN:DMPB on a fallow norn reported 15 lobes and 29 tracts. game-files-analysis.md and Brain.catalogue only document 12 lobes. The 3 extra entries may be comb/forf/sens from the genome (present as genes but not in Brain.catalogue naming), or they could be empty/degenerate.
**Mitigation:** In Task 1, after encoding the known 12-lobe map, probe lobes 12-14 via DMPL to check if they contain neurons. If they do, investigate what they are and decide whether to include them as inputs. If they're empty/zero-neuron, ignore them.

### P6: Observation data distribution skewed
**Problem:** Norn spends 80% of time idle (look → self), training data dominated by one class
**Mitigation:** Undersample idle observations, oversample active decisions. Weight rare actions higher in loss function. Engineer situations (inject hunger chemicals, spawn grendels) to get diverse observations.

### P7: Saving/loading full model weights incompatible with old model
**Problem:** NornBrainFull has different architecture than NornBrain
**Mitigation:** Separate weight files. `brain_weights.pt` for old model, `brain_weights_full.pt` for new. Bridge client checks which model is active.

### P8: 256-chemical read might include many zeros
**Problem:** Most chemicals are 0 most of the time: wasted input dimensions
**Mitigation:** Include all 256 as inputs but the NCP's sparse wiring will ignore irrelevant ones. Alternatively, pre-filter to non-zero chemicals from the chemical table analysis (game-files-analysis.md section 5).
