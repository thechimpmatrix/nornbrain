# Phase E.2: CfC Comb-Replacement Design Spec

> **Date:** 2026-04-26
> **Status:** LOCKED (decisions A-H pinned, contract verified against genome decode of norn.bondi.48.gen breed-stable across 5 sampled genomes)
> **Scope:** End-to-end build path from current state to a testable CfC comb-replacement running inside the NB engine alongside stock SVRule.
> **Predecessors:** Phase E.1 (comb contract verification, KB-resolvable now). architecture_pivot_2026_04_25_comb (currently `status=pending_verification`; flips to `active` on sign-off of this spec).
> **Successor:** Phase E.3 (live training and stress evaluation).

---

## 1. Goal and non-goals

### Goal

Replace the SVRule comb (combination) lobe with a Closed-form Continuous-depth (CfC) module that runs inside the NB engine via the existing pybind11 bridge. SVRule continues to handle perception input lobes, reward pathway, attention persistence, and the decn argmax over the CfC module's output. CfC handles the strategic learning substrate that comb previously held.

The deliverable is a creature that ticks live in openc2e with `--brain-module nornbrain_cfc_v2.py`, where:
- comb is a CfC module driven by reinforcer chemistry (chemicals 204/205) instead of dendrite migration;
- the rest of the brain remains SVRule;
- behaviour matches or exceeds the stock SVRule baseline on the existing benchmarks (eat-when-hungry, approach-then-eat, retreat-from-grendel, etc.);
- BrainViewer renders the SVRule layer correctly via openc2e BRN: commands (Path A monitor work).

### Non-goals

- Replacing decn, attn, or any input lobe (those stay SVRule).
- Genetic evolution of CfC weights across generations (deferred to Phase E.4+).
- Replicating comb's dendrite migration behaviour exactly. The CfC learns by gradient descent on a reward scalar; migration is replaced functionally, not mechanically.
- Replicating the documented opcode-35 backwards-formula bug.
- Custom monitor (Path B). Path A first; Path B is a Phase E.5 follow-on.

---

## 2. Comb contract: current state of knowledge

The KB resolves comb's contract via `python tools/kb_query_phase_e1.py`. Below is the contract distilled into spec form, plus the items that still require Phase A extraction work.

### 2.1 Settled (sourced from C3 1999 source + cc-ref + braininavat catalogue)

| Field | Value | Source |
|---|---|---|
| Lobe id (4-char tag) | `comb` | docs/reference/svrule-brain-complete-reference.md §8 |
| Role | Strategic learning substrate; "concept" lobe in C1/C2 lineage, renamed and re-mechanism-ised in C3 | cc-ref.yaml `decisions.architecture_pivot_2026_04_25_comb` |
| Stock neuron count | 640 | cc-ref.yaml `lobes.comb`; Live BrainViewer 2026-04-25 |
| Per-neuron state | 8 floats (`Neuron.states[8]`) per `c_struct.Neuron`; conventions: STATE_VAR=0 primary output, INPUT_VAR=1 per-tick input accumulator, OUTPUT_VAR=2, FOURTH_VAR=4 preserve slot, NGF_VAR=7 migration trigger | C3 source SVRule.h:19-28 |
| Per-dendrite state | 8 floats (`Dendrite.weights[8]`); WEIGHT_SHORTTERM_VAR=0 (STW), WEIGHT_LONGTERM_VAR=1 (LTW), STRENGTH_VAR=7 (migration permanence) | C3 source SVRule.h:30-39 |
| Reinforcement coupling | Chemicals 204/205 (Reward/Punishment) gate dendrite weight updates; threshold + rate per `Tract.ReinforcementDetails` | C3 source Tract.h:101-126 |
| Update schedule | One tick per SVRule update cycle, ordered by tract `updateAtTime` | C3 source BrainComponent.h, Brain.cpp |
| Decn-action mapping | Catalogue-resolved bijection: action 0→neuron 0, 1→1, 2→6, 3→7, 4→12, 5→2, 6→4, 7→13, 8→5, 9→8, 10→9, 11→10, 12→11 | C3 install Catalogue/Creatures 3.catalogue `Action Script To Neuron Mappings`; KB `catalogue.action_script_to_neuron.*` |

### 2.2 Pending Phase A extraction

| Field | Status | Extraction path |
|---|---|---|
| Input dendrite sources (which lobes wire into comb, in what order) | Genome-encoded; confirmed not in cc-ref.yaml | Decode `tools/Gene Loom v1.4.4/data/C3/default_norn.gno` brain tracts; cross-check svrule-brain-ref §8 narrative vs the actual genome bytes. Document as `docs/specs/2026-04-26-cfc-comb-replacement-design.md::appendix-A` once decoded. |
| Output tract destinations (which lobes comb feeds) | Genome-encoded | Same path |
| Dendrite topology per tract (sparse, dense, migrating, src/dst neuron ranges, connection counts) | Genome-encoded | Same path |
| Comb's init + update SVRule programs (the bytecode the genome installs on the comb lobe gene) | Genome-encoded | Decode the lobe gene's two SVRule programs (48 bytes each on disk); cross-reference against svrule-brain-ref §6 opcode reference |
| Stock reward/punishment ReinforcementDetails values per tract feeding comb (threshold, rate, supports flag, chemical index) | Genome-encoded inside each tract gene | Same path |

### 2.3 Functional contract for the CfC replacement

Translation rules (independent of the genome decode):

- **Inputs:** the CfC's input layer accepts the same activations stock comb's neurons would receive on a tick, packed in the order Phase A locks. CfC tract-internal weights replace SVRule dendrite weights.
- **Output:** the CfC produces an output vector of the same dimensionality as stock comb's output (one float per output-side neuron, value range bounded). The output flows downstream into decn the same way stock comb's output would.
- **State:** the CfC carries its own continuous hidden state across ticks (this is the core CfC-NCP property and what differentiates it from SVRule's per-tick stateless register-machine evaluation).
- **Reward channel:** chemicals 204 and 205 are exposed as scalar inputs to the CfC's weight-update step, not concatenated into the CfC's data input. Eligibility trace + A2C drive weight updates.
- **Tick alignment:** one CfC forward pass per SVRule update cycle. Bridge cost is one Python call per SVRule tick that touches comb (typically every tick).

---

## 3. Architectural decisions (locked on sign-off)

Each decision below is presented as `(option, rationale, alternative-considered)`. Sign-off updates `cc-ref.yaml decisions.*` with `locked: true`.

### A. Replacement scope

**Decision: functional substitution.** CfC sized for compute budget (default 640 to match stock; subscale for ablations). Learned input and output projections at the boundary; SVRule plumbing on every other lobe stays intact.

**Why not drop-in:** strict drop-in would force the CfC to use stock dendrite topology one-for-one, which constrains the CfC to suboptimal compute spending and makes the CfC's strength (continuous time, expressive dynamics) harder to exploit.

**Why not hybrid co-existence:** A/B blending is a useful diagnostic but a poor production architecture. Deferred unless functional substitution stalls in benchmarks.

### B. Wiring fidelity

**Decision: boundary-fidelity wiring with NCP internals.** External tract endpoints (which lobes feed into comb, which lobes comb feeds) match stock C3 exactly per Phase A genome decode. Internal CfC wiring is NCP standard sensory→inter→command→motor with `ncps` library defaults.

**Why:** boundary fidelity preserves genotype provenance (the genome's tract genes still find a target where they expect one) and gives BrainViewer a coherent rendering. NCP internals give the CfC the inductive bias it was designed for.

### C. Learning rule translation

**Decision: A2C with eligibility trace narrowed to the comb module.** Already implemented at the brain level in `openc2e/tools/nornbrain_cfc_v2.py`; this decision narrows it to comb only.

**Specifics:**
- Eligibility trace: 20-tick window, γ=0.95 (inherited from existing code).
- Entropy bonus: 0.1 → 0.01 linear decay over 10K ticks (inherited).
- Value head: **dropped initially, pending reward-stability check.** The full-brain CfC currently has a value head; with comb scoped narrower, baseline reward variance may be small enough that the policy gradient alone suffices. Re-enable value head only if benchmark reward variance exceeds a threshold determined empirically in Phase D Layer 3.
- Reward signal: chemicals 204 and 205 read once per tick; difference (`reward - punishment`) is the scalar.

**Why:** existing A2C implementation has been debugged through Phase B (eligibility trace fix) and Phase C (drive data tracts fix). Reusing it for comb-only is the lowest-risk path. Dropping value head is a deliberate scope cut to surface whether comb-narrow training needs it.

### D. Opcode-35 (backwards-formula gotcha) policy

**Decision: corrected behaviour, deviation documented.** The CfC is not bound to SVRule semantics. Behavioural authenticity rests on chemistry, instincts, and overall lobe connectivity, not on a maths bug.

**Where the deviation manifests:** the CfC's weight update step uses standard `(1-r)*old + r*new` blending, not the operand-side store the stock SVRule opcode 35 produces.

**Why:** corrected blending makes gradient flow predictable. Replicating the bug for behavioural fidelity would only matter if behavioural traces fail Layer 2 equivalence in a way attributable to opcode 35 specifically; if that happens, this decision is revisited.

### E. Scale

**Decision: 440 neurons (stock comb scale, BE-decoded from norn.bondi.48.gen and verified breed-stable across 5 genomes).** Subscale tiers (110, 220) supported as ablation knobs, NOT as the default.

**Why:** the architecture pivot is grounded in "comb is the actual learning substrate". A scale-matched CfC is the honest test of whether CfC can replace it. The earlier 640 figure was a C1 Concept lobe value misattributed to C3 comb; corrected against genome decode 2026-04-26.

**Genome layout:** 40 columns × 11 rows = 440 neurons. RGB (255, 222, 203). Update every 20 ticks. tissue_id = 0.

**Compute envelope:** 440-neuron CfC fits the RTX 3090 envelope by orders of magnitude. Phase C.5 ONNX benchmark established 11K-neuron feasibility at 2.2ms conservative; 440 is well within budget.

### F. Bridge mechanics

**Decision: pybind11 bridge through the existing PythonBrain path. One CfC forward pass per SVRule tick that touches comb.**

**Specifics:**
- C++ side (PythonBrain.cpp) supplies comb's input vector to Python every tick.
- Python side returns the comb output vector to C++ which routes it into decn argmax.
- Tick alignment: comb fires once per SVRule update cycle; CfC integrates one timestep per call.
- Profile early: the per-tick boundary crossing is the obvious cost; baseline measurement on a 10-minute live run before any optimisation work.

**Why:** the bridge already exists for the full-brain CfC. Narrowing it to comb-only is a simpler integration than building a new transport. Performance risk is bounded by Phase C.5 ONNX numbers.

### G. Reward path

**Decision: explicit reward channel separate from data signals.** Chemicals 204 (Reward) and 205 (Punishment) read directly by the bridge each tick and passed into the CfC's weight-update step as a scalar `reward - punishment`. Not concatenated into the CfC's input vector.

**Why:** reinforcement signals are a learning-time concern, not an inference-time concern. Mixing them into the data input would force the CfC to learn a separation that the architecture should provide for free. Separation also allows reward-channel ablations cleanly.

### H. Stock-breed contract for v1

**Decision: lock CfC input/output dimensions to the Bondi-spec genome.** 107-d input (driv 20 + stim 40 + verb 11 + forf 36 concatenated in genome-declaration order), 51-d output (attn[0..39] = 40 + decn[0..10] = 11), 440-d hidden. Verified breed-stable across Bondi, Harlequin, Civet, Zebra, Banshee Grendel, Final46 Ettin (sampled 2026-04-26).

**Why:** the standard Cyberlife brain is one shared block of genes across all official breeds. Hardcoding the dimensions from the actual genome decode is the right v1 scope.

**Mutation handling:** mutated or non-standard genomes that do not match the Bondi-spec shape fall back to stock SVRule comb (no CfC routing). The bridge verifies the genome shape at brain init and emits a warning + fallback if mismatched. Genome-aware projection resizing is **Phase E.4+** scope, deferred.

**Why not genome-aware now:** auto-resizing input/output projections at runtime requires the bridge to decode the genome on every brain init and instantiate a sized CfC, which is significant additional engineering. Stock-only is the smallest scope that delivers a working build; genome-aware is a clean follow-on once stock-only is proven.

**Forward-compatibility pattern (v1 design that makes v2 cheap).** The v1 implementation must NOT hardcode 107 / 51 / 440 throughout the code. Use module-level constants derived from genome decode, and parameterise `CfCComb.__init__` so v2 can pass per-genome layouts:

```python
# nornbrain/cfc_comb.py (v1)
STOCK_INPUT_LAYOUT = [
    ("driv", 20),  # genome-declaration order from norn.bondi.48.gen
    ("stim", 40),
    ("verb", 11),  # neurons 0..10 only
    ("forf", 36),
]
STOCK_OUTPUT_LAYOUT = [
    ("attn", 40),  # neurons 0..39
    ("decn", 11),  # neurons 0..10
]
STOCK_INPUT_DIM  = sum(n for _, n in STOCK_INPUT_LAYOUT)   # 107
STOCK_OUTPUT_DIM = sum(n for _, n in STOCK_OUTPUT_LAYOUT)  # 51
HIDDEN_DIM = 440

class CfCComb(nn.Module):
    def __init__(self,
                 input_layout=STOCK_INPUT_LAYOUT,
                 output_layout=STOCK_OUTPUT_LAYOUT,
                 hidden_dim=HIDDEN_DIM):
        super().__init__()
        in_dim  = sum(n for _, n in input_layout)
        out_dim = sum(n for _, n in output_layout)
        self.input_proj  = nn.Linear(in_dim, hidden_dim)
        self.cfc         = ncps.torch.CfC(hidden_dim, ...)
        self.output_proj = nn.Linear(hidden_dim, out_dim)
```

Bridge side:

```python
# openc2e/tools/nornbrain_cfc_v2.py (v1)
def init_creature_brain(genome_bytes):
    summary = parse_genome_from_bytes(genome_bytes)
    if matches_stock_bondi(summary):
        return CfCComb()  # default args = stock dims
    return None  # signal SVRule fallback
```

For v2 the change is small: `derive_layout_from_genome(summary)` returns `(input_layout, output_layout)` tuples sized to the actual creature, and `CfCComb(input_layout, output_layout)` instantiates a per-creature projection. The CfC core (NCP wiring at HIDDEN_DIM=440, training loop, reward coupling) stays unchanged. Persistence: v1 saves one weight file; v2 saves one shared-core file plus per-creature projection files.

---

## 4. Test harness (4 layers; built BEFORE implementation)

The harness is the contract that catches regressions. Each layer is a separate file or pytest module. Build them all in Phase D before Phase E starts.

### Layer 1: Contract tests

**Path:** `tests/test_cfc_comb_contract.py`

**What it asserts (cheap, fast, deterministic):**
- Input vector dimensionality matches the Phase A contract.
- Output vector dimensionality matches the Phase A contract.
- Weight save / load round-trip bit-equal.
- Fixed-seed determinism: same input + same weights = same output across runs.
- Reward channel correctly decoupled from data input (calling forward with vs without reward produces the same forward output; only the weight-update step differs).

**Run cost:** seconds. Run on every commit.

### Layer 2: Behavioural equivalence

**Path:** `tests/test_cfc_comb_behavioural.py` plus `eval/comb_baseline_trace_<date>.json` reference fixture.

**Setup:** instrumented PythonBrain.cpp build that logs comb's input vector + dendrite states + output vector each tick during a stock C3 norn run. Run a feed-eat-rest cycle under BrainViewer; persist as the reference trace (the Phase B deliverable).

**What it asserts:**
- Replay the reference trace's input vectors through both stock comb (via instrumented C++ path) and CfC-comb. Compare output distributions per tick (KL divergence or per-element MSE under threshold).
- Compare action selection downstream (the decn argmax winner) over the trace.
- Compare learning curves: feed N ticks of reinforcement, measure weight change magnitude in stock vs CfC.

**Tolerance:** the CfC is not stock-identical, so equivalence is statistical not bit-equal. Per-element MSE threshold pinned during Phase D.2 calibration.

**Run cost:** minutes. Run pre-merge.

### Layer 3: Live simulation

**Path:** extend `tools/svrule_baseline_benchmark.py` with `--brain` flag accepting `svrule`, `cfc-comb`, `cfc-v2-prior` (the old pure-CfC for historical comparison). Reuse the metrics accumulator in `nornbrain_cfc_v2.py`.

**Five-minute scenarios (Phase D.3 baselines):**
- Hungry-norn-with-food: starts at hunger 0.8, food in scene; reward_rate, hunger_trend, time_to_first_eat
- Multi-drive-mix: hunger + tiredness + boredom; homeostasis_index over time
- Reward-burst: external reward injection at t=120s; weight drift before/after

**Comparison table:** stock SVRule, SVRule-with-CfC-comb, prior pure-CfC v2 (the experimental code in `nornbrain/multi_lobe_brain_v2.py`).

**Overnight scenarios (Phase G acceptance):**
- 8-hour run with watchdog; weight snapshots every hour; learning_curve_stable check.

**Run cost:** 5 min per scenario; 8h for overnight. Run after Phase E.

### Layer 4: Stress and emergence

**Path:** `tests/test_cfc_comb_emergence.py` + scripted scenarios.

**Scenarios:**
- Starvation (no food for 30 min, observe creature reactions)
- Fight-or-flight (introduce grendel; norn should retreat)
- Mating (two norns of opposite sex, both adult, drives compatible)
- Breeding inheritance (offspring's CfC weights initialised from parents)
- Multi-norn social (5 norns in close quarters; observe emergent grouping)
- 24-hour horizon (life cycle stability test)

**What this layer measures:** "novel adaptive behaviour count" per roadmap-v2.md Phase A success criterion. Not pass/fail; descriptive plus benchmarked.

**Run cost:** hours-to-days. Phase E.3 territory.

---

## 5. Monitor strategy

### Path A: openc2e BRN: command implementation (this spec's deliverable)

**Goal:** stock Brain in a Vat tool connects to openc2e and renders the SVRule layer correctly.

**Why this matters now:** during Phase D.2 (behavioural equivalence) and Phase E iteration, having a working brain visualiser is the difference between "gradient descended somewhere" and "the right neurons activate at the right times". The Vat tool already does this; openc2e just lacks the BRN: backend.

**Wire format:** `docs/reference/braininavat/12-brn-dmp-wire-format.md` is reconstructed from the Vat decompile and the C3 source. Authoritative.

**Transport decision:** **extend the existing TCP 20001 path, not add shared memory.** Stock C3 used Win32 shared memory; openc2e standardised on TCP. Adding a second transport doubles the surface area for no benefit.

**Commands to implement (priority order):**

| Command | Purpose | Priority |
|---|---|---|
| `BRN: DMPB` | Brain dump basic (lobes + tracts list with metadata) | P0 |
| `BRN: DMPL` | Lobe dump (neuron states for one lobe) | P0 |
| `BRN: DMPN` | Neuron dump (single neuron's full state) | P0 |
| `BRN: DMPT` | Tract dump (dendrite states for one tract) | P1 |
| `BRN: DMPD` | Dendrite dump (single dendrite's full state) | P1 |
| `BRN: SETL` | Set lobe-wide value | P2 |
| `BRN: SETN` | Set single neuron state | P2 |
| `BRN: SETT` | Set tract-wide value | P2 |
| `BRN: SETD` | Set single dendrite state | P2 |

P0 unblocks read-only inspection (the immediate need). P1 enables tract-level visualisation. P2 enables write paths for debug poking. P0 is the Path A acceptance bar; P1 and P2 are nice-to-haves before Phase E.3.

**Implementation location:** new file `openc2e/src/openc2e/caos/caosVM_brn.cpp` plus dispatch table entries. Update `commandinfo.json` so the openc2e CAOS validator recognises the commands.

### Path B: custom monitor (deferred follow-on)

**Goal:** render SVRule and CfC together, with CfC neurons as a separate visual section. Stock Vat tool has no concept of CfC neurons; a custom monitor reuses the wire format on the inside but shows both layers.

**Why deferred:** Path A is small (P0 commands) and unblocks the original tool. Path B is a UI build; valuable but not on the critical path. Slot it into Phase E.5 after Path A and the CfC are both shipped.

**Existing monitor (`web_monitor.py` on port 8088):** continues running for runtime metrics (telemetry, accumulator dumps, alerts). Path A and Path B are complementary surfaces.

---

## 6. Implementation sequence

### Phase A: Contract extraction (1-2 sessions, Extension)

| Step | Output | Acceptance |
|---|---|---|
| A.1 | Read svrule-brain-complete-reference.md §8 with comb-as-cortex lens | Notes captured |
| A.2 | Cross-verify against C3 source `Lobe.h`, `Tract.h`, `SVRule.h` | C3 source citations per claim |
| A.3 | Decode `default_norn.gno` brain tracts: which lobes feed comb, which lobes comb feeds, neuron range bounds, connection counts, migration flags | New `kb/loaders/brain_tracts_default_norn.py` plus rebuild |
| A.4 | Decode comb's init + update SVRule programs (16 entries each, 48 bytes on disk per program) into a human-readable opcode list | Appendix A of this spec, plus KB ingestion |
| A.5 | Decode each tract gene's `ReinforcementDetails` block (threshold, rate, chemical index, supports flag) | Same KB loader |
| A.6 | Write Appendix A to this spec with the decoded contract | Spec status flips to LOCKED |

**Deliverable:** Appendix A of this spec; KB rebuild includes the new genome-decoded data.

**Risk:** binary genome parsing. Mitigation: openc2e source has a `genomeFile.h` / `genomeFile.cpp` parser already; can use it as reference, or invoke openc2e's C++ parser via a thin Python wrapper, or hand-decode using the format spec at lisdude `cdn/25.html` (size 121 for lobe gene, size 128 for tract gene).

### Phase B: Reference capture (1 session, CLI)

| Step | Output | Acceptance |
|---|---|---|
| B.1 | Add comb-state instrumentation to `openc2e/src/openc2e/creatures/PythonBrain.cpp`: per-tick log of comb's input vector, neuron states, output vector | New code path behind a `--log-comb` flag |
| B.2 | Build openc2e | clean build |
| B.3 | Run stock C3 norn under `--log-comb` for one feed-eat-rest cycle (15 min real time) | JSON or NDJSON file at `eval/comb_baseline_trace_2026-04-26.json` |
| B.4 | Verify trace integrity: every tick has matching input/output dims; no NaN; reward signal arrives | smoke check |
| B.5 | Commit trace as a fixture | git tracked under `eval/` (P1 Law: archived before any future overwrite) |

**Deliverable:** baseline trace fixture used by Layer 2 tests.

**Risk:** instrumentation touching the hot tick loop. Mitigation: gated by flag; unconditional path is unchanged.

### Phase C: Architectural commit (1 session, Extension)

| Step | Output |
|---|---|
| C.1 | Update `cc-ref.yaml decisions.architecture_pivot_2026_04_25_comb` status to `active`, locked: true, with `next_step` pointing at Phase D |
| C.2 | Add new `cc-ref.yaml decisions.cfc_comb_replacement_scope` (=functional_substitution), `.cfc_comb_wiring` (=boundary_fidelity_ncp_internal), `.cfc_comb_learning` (=a2c_eligibility_trace_value_head_off_initially), `.cfc_comb_opcode35_policy` (=corrected_documented), `.cfc_comb_scale` (=640_neurons), `.cfc_comb_bridge` (=pybind11_per_tick), `.cfc_comb_reward_path` (=explicit_channel) |
| C.3 | KB rebuild absorbs the new decisions |
| C.4 | Commit |

**Deliverable:** locked decisions queryable from the KB.

### Phase D: Test harness (2-3 sessions, CLI; harness BEFORE code)

| Step | Output |
|---|---|
| D.1 | `tests/test_cfc_comb_contract.py` (Layer 1) - see §4. Skeleton CfC stub emits zeros so tests can run before the real implementation. |
| D.2 | `tests/test_cfc_comb_behavioural.py` (Layer 2) - replay harness + tolerance calibration. Initial run will fail until Phase E ships; the harness exists to receive the implementation. |
| D.3 | `tools/svrule_baseline_benchmark.py` extension (Layer 3) - `--brain` flag, three-way comparison table |
| D.4 | `tests/test_cfc_comb_emergence.py` (Layer 4) - stub skeleton with one scenario implemented (starvation) so the test runner has something to find. Other scenarios filled in Phase E.3 |

**Deliverable:** working harness with the CfC stub returning zeros; all four layers run and report.

### Phase E: Implementation (3-5 sessions, CLI)

| Step | Output |
|---|---|
| E.1 | `nornbrain/cfc_comb.py`: CfC module proper. 640 neurons, NCP wiring, boundary-fidelity input/output projections, eligibility-trace A2C narrowed, no value head |
| E.2 | Reinforcement coupling: chemicals 204/205 → CfC weight update step. Use existing reward-handler in `nornbrain_cfc_v2.py` as reference; narrow scope |
| E.3 | Bridge updates: `openc2e/src/openc2e/creatures/PythonBrain.cpp` - comb-routing path that hands comb's inputs to Python and routes outputs back into SVRule decn |
| E.4 | `openc2e/tools/nornbrain_cfc_v2.py` updated to instantiate the comb-only CfC instead of the full brain v2 |
| E.5 | Pretrain on instinct rules using `openc2e/tools/pretrain_instincts_v2.py`, narrowed to comb. Capture pretrain accuracy |
| E.6 | Layer 1 contract tests pass |
| E.7 | Layer 2 behavioural equivalence baseline run; calibrate tolerance; iterate |
| E.8 | Profile bridge cost on a 10-min live run; document per-tick overhead |
| E.9 | Apply opcode-35 correction policy in CfC weight update; document deviation in the spec appendix |

**Deliverable:** running `--brain-module nornbrain_cfc_v2.py` with comb-replacement live, Layer 1 + Layer 2 tests green.

### Phase F: Monitor Path A (parallel with Phase E, 1-2 sessions, CLI)

| Step | Output |
|---|---|
| F.1 | `openc2e/src/openc2e/caos/caosVM_brn.cpp` skeleton + dispatch entries |
| F.2 | Implement BRN: DMPB, DMPL, DMPN (P0) per wire format spec |
| F.3 | Update `commandinfo.json` |
| F.4 | Build openc2e; smoke test via TCP 20001 with hand-crafted CAOS request |
| F.5 | Connect Brain in a Vat .exe; verify it renders lobes + neuron states correctly |
| F.6 | Implement BRN: DMPT, DMPD (P1) for full visualisation |
| F.7 | (Optional, P2) Implement SETL/SETN/SETT/SETD for write paths |

**Deliverable:** Brain in a Vat tool connects to openc2e and shows the SVRule layer live.

### Phase G: Acceptance (1 session, CLI + Extension)

| Step | Output |
|---|---|
| G.1 | Layer 3 live benchmark on all three scenarios; comparison table written to research doc |
| G.2 | Overnight 8-hour run with watchdog; learning_curve_stable check |
| G.3 | Brain in a Vat smoke test |
| G.4 | Layer 4 emergence scenarios (at least starvation, fight-or-flight, mating); document observed behaviours |
| G.5 | Update research doc Section 17 with Phase E.2 results |
| G.6 | Update `cc-ref.yaml decisions.architecture_pivot_2026_04_25_comb` notes with empirical findings |

**Acceptance criteria (all required):**
- Layer 1 + Layer 2 + Layer 3 all green or within tolerance.
- CfC-comb beats stock SVRule on at least 2 of 3 Layer 3 scenarios.
- Overnight run shows monotonic-or-stable reward trajectory; no creature death from CfC misbehaviour.
- Brain in a Vat connects and renders.
- At least one observed novel adaptive behaviour in Layer 4 (not present in stock SVRule).

### Phase H: Path B custom monitor (deferred follow-on)

Out of scope for this spec. Spec for Phase H written after Phase G acceptance.

### Phase I: Genome-aware projection layer (deferred follow-on, addresses Decision H v2)

Out of scope for this spec. Spec for Phase I written after Phase G acceptance, to extend the CfC bridge with per-creature projection layers so non-stock genomes (mutated breeds, evolved populations, hand-edited norns) can run CfC instead of falling back to SVRule.

Scope when written:
- Modify `derive_layout_from_genome(summary)` in the bridge to compute per-creature (input_layout, output_layout) tuples from the actual genome decode.
- Bridge instantiates `CfCComb(input_layout, output_layout)` per creature at hatch.
- Per-creature projection weights initialised (zero or small random); CfC core weights inherited from the trained shared model.
- Persistence: shared-core weight file plus per-creature projection files keyed by creature UNID.
- Training: per-creature projection layers train alongside the shared core via standard backprop; opt-in per-creature loss tracking.
- Acceptance: a heavily-mutated norn (W or H of comb shifted by ±5) hatches with a CfC that runs and learns at not-much-worse-than-stock performance for the first lifetime.

---

## 7. cc-ref.yaml changes on sign-off

```yaml
decisions:
  architecture_pivot_2026_04_25_comb:
    status: active           # was pending_verification
    locked: true             # was false
    contract: "see docs/specs/2026-04-26-cfc-comb-replacement-design.md Appendix A"

  cfc_comb_replacement_scope:
    choice: functional_substitution
    reason: "CfC sized for compute budget with learned input/output projections; SVRule plumbing on every other lobe stays intact"
    alternative_considered: "drop_in (rejected: forces stock topology), hybrid_co_existence (rejected: A/B blending is diagnostic not production)"
    locked: true

  cfc_comb_wiring:
    choice: boundary_fidelity_ncp_internal
    reason: "External tract endpoints match stock; internal wiring is NCP standard sensory>inter>command>motor. Boundary fidelity preserves genotype provenance and gives BrainViewer a coherent rendering"
    locked: true

  cfc_comb_learning:
    choice: a2c_eligibility_trace_value_head_off_initially
    reason: "Reuse Phase B-debugged A2C, narrow to comb. Drop value head pending reward-stability check in Phase D Layer 3"
    eligibility_trace: "20 ticks, gamma=0.95"
    entropy_bonus: "0.1 -> 0.01 over 10K ticks linear"
    reward_chemical: 204
    punishment_chemical: 205
    locked: true

  cfc_comb_opcode35_policy:
    choice: corrected_documented
    reason: "CfC is not bound to SVRule semantics. Correct blending makes gradient flow predictable. Revisit only if behavioural equivalence fails attributable to opcode 35"
    locked: true

  cfc_comb_scale:
    choice: 640
    reason: "Stock comb scale; honest test of replaceability"
    subscale_ablation_tiers: [160, 320]
    locked: true

  cfc_comb_bridge:
    choice: pybind11_per_tick
    reason: "Existing PythonBrain bridge; one CfC forward pass per SVRule tick. Profile early per Phase E.8"
    locked: true

  cfc_comb_reward_path:
    choice: explicit_channel_separate_from_data
    reason: "Reinforcement is a learning-time concern; mixing into data input forces CfC to learn separation that the architecture should provide"
    locked: true
```

---

## 8. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Phase A genome decode harder than expected (binary parsing, undocumented edge cases) | High (blocks everything) | Use openc2e's existing `genomeFile.h` parser as ground truth; fall back to lisdude CDN spec; failing both, hand-decode the first norn lobe + tract genes by hex |
| CfC learning unstable at 640 neurons with comb-narrow scope | Medium | Phase E.7 calibration; if unstable, re-enable value head; if still unstable, drop scale to 320 as ablation; if still unstable, revisit Decision A (consider hybrid) |
| Bridge cost exceeds budget (per-tick overhead too high) | Medium | Phase E.8 measurement; if budget exceeded, batch multiple ticks per Python call (this is a sub-optimisation that matters only at scale) |
| Layer 2 behavioural equivalence fails because the CfC behaves too differently from stock comb | Medium-Low | The CfC is meant to behave differently (better, not identically). Layer 2 tolerance is calibrated to detect "wrong direction" not "non-identical". If the failure is qualitative, the CfC is doing the wrong thing; if quantitative within reasonable bounds, that is success |
| BRN: command implementation is more work than estimated | Low | P0 subset only for Phase F; P1 and P2 deferrable |
| Opcode 35 correction causes hidden behavioural regressions | Low | Decision D logged the deviation; if Layer 4 stress scenarios surface a regression attributable to opcode 35, revisit |
| Reward signal noisy enough that A2C without value head diverges | Low-Medium | Existing Phase B fix already handles this at brain scale; comb-narrow should be no worse. Re-enable value head as the standard remediation |
| Default genome decoding reveals that the project's lobe assumptions (12 standard lobes, comb=640) differ from what civet46 actually encodes | Low | Phase A decode would surface this. Mitigation: this spec is grounded in the standard genome; per-genome variation is a Phase E.4 concern |
| openc2e's PythonBrain bridge has implicit assumptions that break under comb-only routing | Low-Medium | The bridge already supports full-brain routing; comb-only is a subset. If something breaks, the bridge code is in our repo, not stock C3 |

---

## 9. Open questions (must resolve before Phase E)

1. **Genome variant question:** Phase A decodes `default_norn.gno`. Is `civet46.txt` (the project's analysis genome) close enough that the same contract applies, or does it diverge? Cross-check during A.3.
2. **Opcode 35 in stock comb:** does stock comb's update SVRule actually USE opcode 35? If no, decision D is moot. If yes, the deviation is real and Layer 2 calibration needs to allow for it.
3. **Reward chemistry tick alignment:** chemicals 204 and 205 are written by stim genes processing earlier in the brain tick. Confirm the read order: do they update before or after comb's update tick? This determines whether the CfC sees this-tick reward or last-tick reward at weight-update time.
4. **`norm` of stock comb output:** does stock comb output activations clamp into [-1, 1] (per the SVRule `bindFloatValue` convention) or unbounded? The CfC needs to match for Layer 2 to make sense.

These are the Phase A.4 / A.5 follow-up questions; resolution unblocks Phase D.

---

## 10. Acceptance criteria summary

A **first-generation stock norn** (hatched from `norn.bondi.48.gen`, no mutations, no breeding) ticking under `--brain-module nornbrain_cfc_v2.py` where:

- [ ] Layer 1 contract tests green
- [ ] Layer 2 behavioural equivalence within calibrated tolerance
- [ ] Layer 3 live benchmark beats stock SVRule on >= 2 of 3 scenarios
- [ ] Overnight 8-hour run is stable
- [ ] Brain in a Vat connects and renders the SVRule layer
- [ ] At least one Layer 4 emergent behaviour observed
- [ ] Phase A appendix written and KB-ingested
- [ ] All Phase C decisions locked in cc-ref.yaml
- [ ] Documented results in research doc Section 17
- [ ] Bridge falls back to SVRule cleanly for any non-stock-shape genome

Mutated norns and bred offspring fall back to SVRule per Decision H. Their behavioural correctness with CfC is **Phase I scope** and not part of v1 acceptance.

When all are checked, Phase E.2 is complete. Phase E.3 (training and stress horizons) and Phase H (Path B custom monitor) are the next active work.

---

## Appendix A: Comb's input/output contract (FILLED BY GENOME DECODE 2026-04-26)

Decoded from `creaturesexodusgame/Creatures Exodus/Creatures 3/Genetics/norn.bondi.48.gen` using `tools/decode_norn_genome.py` (big-endian uint16 per `Genome.h GetInt()`). Verified breed-stable across 5 sampled genomes: Bondi, Harlequin, Civet (expressive variant), Zebra, Banshee Grendel, Final46 Ettin. All 5 produce identical comb section.

### A.1 Comb lobe gene

| Field | Value | Source |
|---|---|---|
| Token (4-char) | `comb` | bondi.48.gen offset 19145 |
| Neuron count | 440 (40 columns × 11 rows) | gene body W=40, H=11 |
| Display position | (5, 22) | gene body x, y |
| RGB | (255, 222, 203) | gene body r, g, b |
| Tissue ID | 0 | gene body tissue |
| Update time | every 20 ticks | gene body update_time |

### A.2 Input dendrite sources (6 tracts)

In genome declaration order. `mig` = migrating. Connection counts: BE-decoded uint16 from tract gene `srcnoconnections` / `destnoconnections`; whichever is non-zero is genome-specified, the other is 0 (engine reads from the specified side).

| # | Source | src range | dst range (in comb) | src_conn | dst_conn | mig |
|---:|---|---|---|---:|---:|:-:|
| 1 | driv | [0..19] | [0..439] | 4 | 0 | **Y** |
| 2 | stim | [0..39] | [0..439] | 1 | 1 | N |
| 3 | verb | [0..10] | [0..439] | 1 | 40 | N |
| 4 | forf | [0..35] | [40..79] | 1 | 0 | **Y** |
| 5 | forf | [0..35] | [200..239] | 1 | 0 | **Y** |
| 6 | forf | [0..35] | [280..319] | 1 | 0 | **Y** |

**Concatenated input vector for the CfC (107 units):** `[driv(20), stim(40), verb(11), forf(36)]`.

The four migrating tracts (driv→comb full + 3× forf→comb regional) are where stock C3 learning happens. Static tracts (stim→comb full + verb→comb full) are pre-wired feature passes.

### A.3 Output tract destinations (2 tracts)

| Dest | src range (in comb) | dst range | src_conn | dst_conn |
|---|---|---|---:|---:|
| attn | [0..439] | [0..39] | 1 | 1 |
| decn | [0..439] | [0..10] | 40 | 1 |

**Concatenated output vector from the CfC (51 units):** `[attn(40), decn(11)]`.

The decn output is to neurons [0..10] (11 of the 13-neuron decn lobe). Action mapping per the catalogue-resolved bijection in `cc-ref.yaml gotchas.decn_action_dual_layer` and the KB's `catalogue.action_script_to_neuron.*`.

### A.4 Comb's init + update SVRule programs

Each lobe gene includes two embedded 48-byte SVRule programs (16 entries × 3 bytes each). The programs are at fixed offsets in the lobe gene body (lobe gene total size 121 bytes; the two SVRule blocks fill the trailing 96 bytes).

For comb specifically the init and update programs are the bytecode that controls per-neuron state updates. The CfC replacement does NOT execute SVRule bytecode; it replaces it with continuous-time gradient-driven dynamics. Decoding the comb-specific bytecode for behavioural reference is a future Phase A.4-extension activity (not blocking the build).

### A.5 Reinforcement details per tract

Each tract gene has `myReward` and `myPunishment` ReinforcementDetails embedded. Per `Tract.cpp:46-90` the chemical index, threshold, and rate fields are set at runtime via SVRule opcodes 59 (`setRewardChemicalIndex`) and 62 (`setPunishmentChemicalIndex`) from each tract's update program - NOT from genome bytes directly. The shipping C3 source has the genome-read code commented out.

For the CfC replacement, this whole indirection is bypassed: the bridge reads chemicals 204 (Reward) and 205 (Punishment) directly each tick and uses `(reward - punishment)` as the policy-gradient scalar. The CfC's weight updates flow from end-to-end loss against this scalar, eligibility-trace-modulated per Decision C.

### A.6 KB query

After the genome decode loader ships (Phase D-equivalent already done):

```bash
python tools/kb_query_phase_e1.py        # multi-hop comb context
```

Returns lobe.comb with all attrs (440 neurons, 40×11 grid, RGB, update_time, tissue), all 8 incoming + outgoing tract entities with their full attr sets (src/dst ranges, connection counts, migration flag), the architecture pivot decision trail, and FTS5 prose snippets across reference docs.

The genome decoder itself is at `tools/decode_norn_genome.py` and `kb/genome_decoder.py`. Run on any .gen file to produce the same kind of contract output for an arbitrary genome.
