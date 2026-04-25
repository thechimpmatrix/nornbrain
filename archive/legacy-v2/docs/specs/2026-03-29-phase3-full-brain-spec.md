# Phase 3: Full Brain Model + BRN:DMP Bridge: Specification

## Goal

Scale the CfC/NCP brain from 122 neurons (simplified) to a full model matching the C3 SVRule brain's 12-lobe architecture (314 neurons). Use the BRN:DMP* CAOS commands for complete brain observability: read every neuron in every lobe via BRN:DMPL bulk reads (~60ms for entire brain). Use full 256-chemical biochemistry reads. Train the CfC to match SVRule-level behaviour by observing the original brain as ground truth.

## Architecture Overview

### Current State (Phase 2c)
- 89 inputs → 40 inter → 25 command → 57 motor (122 neurons)
- Inputs: 20 drives + 40 attention (mostly zeros) + 9 situation + 11 detail + 9 chemicals
- Attention computed via slow CAOS ENUM+CATI queries (~14 categories)
- Timer script reads drives/chems via individual GAME var writes (slow, ~0.8 tps)
- Training: supervised on 17 hand-crafted scenarios + basic RL

### Target State (Phase 3)
- Full C3 lobe-matched CfC brain with 12 lobes (314 neurons)
- All neuron state read via BRN:DMPL bulk reads (one call per lobe, ~5ms each, ~60ms total for all 12 lobes)
- BRN:DMPN available for single-neuron debugging (40 bytes/neuron)
- All 256 chemicals read via batch CAOS
- Training: behaviour cloning from observed SVRule brain decisions
- The CfC brain runs in parallel with the SVRule brain, observing and learning

## Key Technical Facts (Verified)

### BRN:DMP Commands (see docs/brn-dmpn-reference.md for full details)
- `BRN: DMPB`: returns lobe/tract counts and sizes (text, not reliable for buffer sizing)
- `BRN: DMPN lobe neuron`: returns 40 bytes: 1 float (input) + 1 uint32 (neuron ID) + 8 floats (state variables). Python: `struct.unpack('<fI8f', data)`. float[2] = variables[0] (primary output)
- `BRN: DMPL lobe`: **PRIMARY READ PATH.** Full lobe binary dump: 560-byte header + (width×height × 40 bytes). One call per lobe, ~5ms each. 12 calls = ~60ms for entire brain
- `BRN: SETN lobe neuron state value`: writes to neuron variable. Confirmed working
- `BRN: DMPT tract`: tract binary dump (untested but exists)
- `BRN: DMPD tract dendrite`: single dendrite dump (untested)
- **`BRN: GETN` does NOT exist**: absent from all CAOS references and openc2e. The only way to READ neuron state is via DMPN/DMPL binary dumps
- **All DMP commands return raw binary to shared memory**, not text. The bridge needs an `execute_binary()` path that reads raw bytes instead of decoding as latin-1

### Engine 1.162 Limitations
- SOUL, STEP, MIND, MOTR: all absent (cannot disable or manually tick SVRule brain)
- SEEN: rejected by compiler in all contexts (injection, Bootstrap, shared memory scrp)
- The SVRule brain runs autonomously every engine tick: we cannot pause it

### Lobe Structure (12 lobes, 314 neurons)
From live C3 genome analysis + verified lobe number table (docs/brn-dmpn-reference.md):

| lobe_number | Quad ID | Name | Neurons | Class |
|-------------|---------|------|---------|-------|
| 0 | attn | Attention | 40 | **Output** |
| 1 | decn | Decision | 17 | **Output** |
| 2 | verb | Verb | 17 | Input |
| 3 | noun | Noun | 40 | Input |
| 4 | visn | Vision | 40 | Input |
| 5 | smel | Smell | 40 | Input |
| 6 | driv | Drive | 20 | Input |
| 7 | sitn | Situation | 9 | Input |
| 8 | detl | Detail | 11 | Input |
| 9 | resp | Response | 20 | Input |
| 10 | prox | Proximity | 20 | Input |
| 11 | stim | Stim Source | 40 | Special |

Total: **314 neurons** across 12 lobes. The lobe_number is the tissue index from the genome: this mapping is verified and no empirical probing is needed.

> **Note:** Wiki references to "comb" (combination), "forf" (friend-or-foe), and "sens" (general sense) lobes exist but these are NOT present in the default C3 genome's Brain.catalogue. They may be C2-era lobes or optional genetics. The live C3 brain has exactly 12 lobes.

### Training Strategy: Observe-then-Replace

Since we cannot disable the SVRule brain:

1. **Phase 3a: Observe:** Run the bridge in SPNL mode. Every tick, read the SVRule brain's attn and decn output neurons (via BRN:DMPN) AND read all input lobes. Build a dataset: `{input_state} → {attn_winner, decn_winner}`. This is the SVRule brain's "behaviour" in structured form.

2. **Phase 3b: Clone:** Train the CfC brain offline on this dataset via supervised learning (behaviour cloning). The CfC learns to produce the same outputs as the SVRule brain given the same inputs.

3. **Phase 3c: Replace:** Switch to ZOMB+ORDR mode. The CfC brain now controls the norn solo. Its behaviour should match the SVRule brain because it was trained on SVRule outputs.

4. **Phase 3d: Refine:** Enable online RL. The game's biochemistry (reward/punishment from decision scripts) provides natural reinforcement. The CfC brain improves beyond SVRule baseline.

## Workstreams

### WS1: Brain State Reader (BRN:DMPL-based)
Build a `BrainStateReader` class that reads all 12 lobes via BRN:DMPL bulk calls (one per lobe). Each DMPL response contains a 560-byte header + all neuron records (40 bytes each). Returns a complete brain state snapshot in ~60ms. Also requires an `execute_binary()` method on the bridge to read raw bytes from shared memory instead of latin-1 text decoding.

### WS2: Full Chemistry Reader
Batch-read all 256 chemicals in one CAOS round-trip. Currently reading 9.

### WS3: Lobe Mapping (RESOLVED)
The lobe_number → quad ID mapping is now fully documented in `docs/brn-dmpn-reference.md`. No empirical probing needed. The mapping (0=attn, 1=decn, 2=verb, ..., 11=stim) is verified from LobeStudy and cross-checked against game-files-analysis.md. This workstream reduces to simply encoding the known table into the code.

### WS4: Full CfC Architecture
Design and implement the full NCP/CfC model matching the 12-lobe structure (314 neurons). Input size expands from 89 to 513 (all 10 input lobes + stim + 256 chemicals).

### WS5: SVRule Observation Dataset
Collect thousands of ticks of SVRule brain input/output pairs. Store as training dataset.

### WS6: Behaviour Cloning Training
Train the full CfC on the SVRule dataset. Validate on held-out ticks.

### WS7: Dashboard Updates
Update dashboard to show all 12 lobes, full chemistry, training progress on SVRule cloning.

### WS8: Live Deployment + RL
Deploy trained CfC via ZOMB+ORDR, enable RL for refinement.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DMPL header offset unverified | Neuron data at wrong offset | The 560-byte header is from LobeStudy reverse-engineering (medium confidence). Verify empirically by reading a known neuron via both DMPN and DMPL and comparing values. Width/height at header offsets 24/28 provide neuron count cross-check |
| Binary shared memory path missing | Can't read any DMP data | c2e_bridge.py currently decodes responses as latin-1 text. Must add `execute_binary()` returning raw bytes. This is a prerequisite for ALL brain reading |
| CfC hidden state convergence | Brain settles to fixed output | Periodic hidden state wipe (already implemented); reduce recurrent synapses; train on sequences |
| SVRule brain overwrites SPNL writes | CfC decisions ignored in SPNL mode | This is fine for observation phase; ZOMB+ORDR for sole control |
| ORDR WRIT vocabulary limitation | Newborn norns don't know words | Teach vocabulary via `vocb` command before switching to ZOMB+ORDR; or use SPNL path only |
| 256-chemical batch too large for shared memory | Buffer overflow | 1MB buffer fits ~4000 float values easily; 256 chemicals is fine |
| Norn dies during observation | Lost creature | Save world frequently; can restart from save |
| DMPB sizes unreliable for buffer prediction | Buffer under-allocation | DMPB "sizes" don't match actual DMPL byte counts (confirmed: DMPB said 512 for a lobe that returned 2171 bytes). Always allocate generously or read the actual response length from shared memory offset 12 |
