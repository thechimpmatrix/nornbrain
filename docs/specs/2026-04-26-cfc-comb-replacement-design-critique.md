# Phase E.2 Spec Critique
> Date: 2026-04-26 | Author: Extension critique agent
> Subject: docs/specs/2026-04-26-cfc-comb-replacement-design.md

## Verdict: REVISE

The architectural pivot (decn → comb) is well-grounded in the genome decode and the four-layer test harness is the right shape. But the spec is marked LOCKED while carrying load-bearing internal contradictions: scale (440 vs 640), file paths that point at archived code, ablation tiers that disagree between prose and yaml, an Appendix A whose existence is contradicted by §2.2's "pending" framing, and a verifiable factual conflict with cc-ref.yaml on decn lobe size. A LOCKED spec is the contract Phase B builds against; these defects will be replicated faithfully into the implementation. Three to five focused edits in §3.E, §6, §7, and Appendix A would put the spec in shape to ship; without them, Phase E.1 will be built at 640 neurons against a non-existent `nornbrain_cfc_v2.py`. The architectural decisions A-H are mostly defensible; the document does not yet defend them well enough for "locked".

---

## 1. Heilmeier Catechism

**1. What are you trying to do?**
Replace the SVRule comb lobe with a CfC module that runs in-process via pybind11, so the actual learning substrate of a Creatures 3 norn becomes a continuous-time differentiable network while the rest of the brain (perception, reward chemistry, attn, decn argmax) stays SVRule (§1, line 14-22). Plain English; nothing missing here.

**2. How is it done today, and what are the limits?**
Stock C3 comb is a 440-neuron SVRule lobe whose learning happens through dendrite migration on 4 of its 6 input tracts (driv migrating + 3 forf migrating), driven by chemicals 204/205 (§2.1, §2.3, Appendix A.2). The limits stock comb hits aren't named in the spec. The spec asserts CfC will "match or exceed" stock SVRule on existing benchmarks (§1, line 20) but doesn't quote the failure modes of stock comb the CfC is meant to fix. **Gap:** what does stock comb fail at? Without that, "match or exceed" is unfalsifiable until Layer 3 results land.

**3. What's new, and why will it succeed?**
NCP-wired CfC with continuous hidden state, A2C eligibility-trace learning, boundary-fidelity input/output to preserve genotype provenance (§3.B). "Why succeed" rests on: prior Phase B/C debugging of the brain-wide A2C carries over (§3.C), and 440 neurons fits the compute envelope (§3.E). **Gap:** the spec defends *feasibility* (compute, code reuse) but not *capacity sufficiency* (why is 440 the right shape for the task, when prior v2 brain ran ~1100 neurons?). See red-team (e).

**4. Who cares; what difference does it make?**
This is the project's central technical bet. Implicit, never stated. **Gap:** no "Who cares" paragraph. For a LOCKED governance doc the success-criteria should anchor to a story (Layer 4 emergent behaviour, lifelong learning curve, breeding inheritance) the way Phase E.3 does, not just to benchmark deltas.

**5. What are the risks?**
§8 enumerates 9 risks with severity and mitigations. Coverage is reasonable but skewed toward implementation risks (parsing, perf, learning instability). **Gap:** strategic risks (CfC architecture is wrong inductive bias for an association lobe; mutation-fallback is too lossy in a bred population; KB / cc-ref drift breaks the sources of truth the spec depends on) are absent. See red-team (d), (h), and cross-cutting.

**6. How much will it cost (time, compute, complexity)?**
Time per phase is sized in sessions (§6: A=1-2, B=1, C=1, D=2-3, E=3-5, F=1-2, G=1; total ~10-15 sessions). Compute is dismissed in one line ("orders of magnitude under RTX 3090", §3.E line 118). Complexity is implicit. **Gap:** total wall-clock estimate not aggregated; complexity not enumerated (the C++ side touches three new surfaces - comb routing in PythonBrain.cpp, BRN: command implementation in caosVM_brn.cpp, commandinfo.json validator - without complexity sizing). Phase F is sized at 1-2 sessions for ~9 new CAOS commands plus wire-format implementation; that's optimistic.

**7. How long?**
Same answer as cost; ~10-15 sessions to G acceptance, no calendar. Adequate for an internal spec.

**8. Midterm and final exams?**
Layer 1-4 test harness (§4) is the strongest part of the spec. Layer 1 (contract) = unit, Layer 2 (behavioural equivalence vs stock baseline trace) = midterm, Layer 3 (live benchmarks) + Layer 4 (emergence) = final. Acceptance criteria in §10 are concrete and binary. **Gap:** the §10 bar "beats stock SVRule on >= 2 of 3 Layer 3 scenarios" has no defined "beats" metric; reward_rate is named in Layer 3 but the comparison threshold (10% better? statistically significant?) is unstated.

---

## 2. Assumption Map

| # | Assumption | Status | Citation | Risk if wrong |
|---:|---|---|---|---|
| 1 | Comb is the learning substrate; replacing it captures C3's strategic learning | VERIFIED | C3 source `Tract.h:101-126` (reinforcement); cc-ref `architecture_pivot_2026_04_25_comb`; genome decode (4 of 6 tracts migrating) | Pivot wastes Phase A-G effort; revert to decn or rethink |
| 2 | Stock comb is 440 neurons (40×11) | VERIFIED | Genome decode of `norn.bondi.48.gen`; KB `lobe.comb`; tools/kb_lookup.py contract | Hidden_dim wrong; all of §3.E and §7 cfc_comb_scale wrong |
| 3 | 440 is the correct CfC capacity for strategic learning | UNVERIFIED | §3.E line 114-115 asserts "honest test"; no capacity argument | If undersized, Phase E.7 fails learning; spec falls back to "ablation" framing without principled rebuild |
| 4 | CfC input is 107-d (driv 20 + stim 40 + verb 11 + forf 36) in declaration order | VERIFIED | Genome decode; cc-ref `cfc_contract.input_layout`; Appendix A.2 | If declaration order differs from C++ tick order, every tick mis-binds inputs to projections; Layer 1 contract test must catch this |
| 5 | CfC output is 51-d (attn 40 + decn 11) | VERIFIED but INCOMPLETE | Appendix A.3; KB | The genome also wires `verb→decn[11,12]` directly (verified via `decode_norn_genome.py`); decn lobe is 13 neurons total. Spec doesn't say what happens at decn[11..12] in the CfC routing. If "decn argmax over CfC output" means argmax over [0..10] only, behaviour diverges from stock when verb activates decn[11..12]. **This needs an explicit decision.** |
| 6 | NCP standard sensory→inter→command→motor wiring is appropriate for comb | INFERRED (weakly) | §3.B line 88 "NCP internals give the CfC the inductive bias it was designed for" | NCP was designed for sensorimotor agents (Lechner et al.); comb is an association lobe. See red-team (d). If wrong, CfC underfits the task or learns slowly |
| 7 | A2C eligibility trace already debugged at brain scale carries down to comb scope | INFERRED | §3.C line 92, §8 row 7 | If brain-scale debugging masked a comb-specific failure mode, Phase E.7 surfaces it; mitigation is "re-enable value head" (§3.C) but spec also drops value head as part of the same change (axis-f problem) |
| 8 | Reward tick alignment: chemicals 204/205 read this-tick give correct policy gradient | UNVERIFIED | §9 question 3 explicitly flags this as open | If reward is read after this-tick weight update, gradient is off-by-one tick; gradient still works but learning rate is wrong |
| 9 | Stock comb output is bounded [-1, 1] | UNVERIFIED | §9 question 4 explicitly flags this | Layer 2 calibration tolerance wrong if so; Layer 1 contract test must read this |
| 10 | Opcode 35 is not exercised in stock comb's update SVRule program | UNVERIFIED | §9 question 2 explicitly flags this | Decision D may be moot or may matter; binary outcome from Phase A.4 |
| 11 | "Breed-stable across 5 sampled genomes" generalises to community/wild population | INFERRED (weak) | Appendix A header line 522 | If wrong, mutation fallback (Decision H) catches it but at the cost of CfC coverage. See red-team (h) |
| 12 | Existing `nornbrain_cfc_v2.py` is the reference implementation to inherit | UNVERIFIED-AND-WRONG | §3.C line 92, §6 E.4 line 360, §6 E.5 line 361, §4 Layer 3 line 235 reference `nornbrain_cfc_v2.py`, `pretrain_instincts_v2.py`, `multi_lobe_brain_v2.py` | All three live under `archive/legacy-v2/code/` after the 2026-04-26 v2 archival. Active equivalents are `openc2e/tools/nornbrain_cfc.py` and `pretrain_instincts.py` (no `_v2`). Builder following the spec literally hits ImportError or pulls archived code |
| 13 | cc-ref.yaml is the source of truth on locked decisions | VERIFIED but INCONSISTENT | cc-ref `decisions.architecture_pivot_2026_04_25_comb` says `status: active, locked: true`; KB lookup says `pending_verification, locked=false`; cc-ref `lobes.decn` says 17 neurons but genome decode + KB say 13 | Spec assumes cc-ref state. KB needs `python -m kb.build --force` and cc-ref needs the decn-17 fact corrected. Otherwise downstream consumers (project sessions, KB queries) get stale answers |
| 14 | Compute envelope is not the constraint | VERIFIED | §3.E line 118; cc-ref `hardware.gpu` (RTX 3090, 24GB) | Low risk; Phase C.5 ONNX numbers cited |
| 15 | openc2e PythonBrain bridge supports comb-only routing as a subset of full-brain routing | INFERRED | §8 row 9 mitigation; §3.F | Bridge currently routes the full brain (`nornbrain_cfc.py` exists and runs); narrowing path is unbuilt, treated as smaller-than-existing but not verified |
| 16 | BRN: P0 commands (DMPB/DMPL/DMPN) are sufficient for Phase D.2 + Phase E iteration | INFERRED | §5 priority table; Path A acceptance bar | If Phase E iteration also needs DMPT (tract dump) to debug projection weights, P1 work moves onto the critical path |
| 17 | Bondi.48 input declaration order matches the order PythonBrain.cpp will pass to Python | UNVERIFIED | §3.H constants `STOCK_INPUT_LAYOUT` defined as `[driv, stim, verb, forf]`; KB output of contract reorders to `[driv, forf, forf, forf, stim, verb]` (alphabetical in `tools/kb_lookup.py contract`) | If C++ tick loop iterates tracts in the order PythonBrain enumerates them (stim, verb, driv, forf, forf, forf, or some other order based on `updateAtTime`), Python receives misaligned inputs. **Layer 1 contract test must lock this from the C++ side, not just the Python side.** |

---

## 3. Pre-Mortem (failure modes ranked by likelihood × impact)

### 3.1 Spec self-contradiction propagates into Phase E build (HIGH × HIGH)

**Mechanism:** Phase E builder reads §6 E.1 ("640 neurons") and ships a 640-neuron CfC against a 440-d input projection, while §3.E (440), §7 yaml (640), and Appendix A (440) all disagree. Same builder reads §6 E.4 and tries to import `openc2e/tools/nornbrain_cfc_v2.py` which has been archived; gets ImportError or worse, edits the wrong file. cc-ref says `lobes.decn = 17` while spec Appendix A.3 says 13; whichever the builder believes determines output projection size and argmax target.

**Evidence:** §3.E line 112 vs §7 line 454 (440 vs 640); §3.E line 112 vs §7 line 456 (ablation tiers (110, 220) vs [160, 320]); §6 E.1 line 357 ("640 neurons") vs Appendix A; §3.C line 92, §6 E.4 line 360, §6 E.5 line 361 (`*_v2.py` files all under `archive/legacy-v2/code/`); §2.2 lists 5 fields as "pending Phase A extraction" while Appendix A is filled; cc-ref `lobes.decn.neurons=17` vs genome decode = 13.

**Mitigation gap:** §8 has no row for "spec internal inconsistencies"; the spec is marked LOCKED, so the normal review-before-lock check did not happen or did not catch these. **Fix before Phase B**, see §5 below.

### 3.2 Phase A binary genome parsing breaks on civet46 or other genomes (MEDIUM × HIGH)

**Mechanism:** Phase A.3 reads `default_norn.gno`. Spec then assumes this generalises. Bondi.48 was decoded successfully but `default_norn.gno` (the spec's stated input, line 308) is a different artifact. If `.gno` parsing differs from `.gen` (different format spec, version skew, or `tools/decode_norn_genome.py` not extended to handle `.gno`), Phase A stalls.

**Evidence:** §6 E.1 says decode `default_norn.gno`. cc-ref `cfc_contract.contract_source` says `norn.bondi.48.gen`. Different file extension, different binary layout (`.gno` is the Gene Loom-edited format, `.gen` is the genome export format). The decoder at `tools/decode_norn_genome.py` is documented for `.gen`.

**Mitigation gap:** §8 row 1 mitigations name "openc2e's `genomeFile.h` parser" and "lisdude CDN spec" but don't address `.gno` vs `.gen` divergence. §6 A.3 should explicitly say which file the contract is decoded from and confirm parser coverage.

### 3.3 NCP wiring inductive bias is wrong for an association lobe (MEDIUM × HIGH)

**Mechanism:** NCP topology was designed for sensorimotor control (Lechner & Hasani, "Liquid Time-constant Networks", "Neural Circuit Policies"). Comb in C3 takes [drives, stims, verbs, smells] and emits [attention focus, decision]. The IO ports look sensorimotor but the *internal computation* is association/concept-binding. With NCP defaults the inter and command layers are sized for motor planning, not for a 107→51 association map. Phase E.7 (Layer 2 calibration) returns "matches stock outputs only on simple cases, drifts on multi-drive scenes". Phase G acceptance fails Layer 3 multi-drive-mix.

**Evidence:** Decision B (§3.B line 86-88) chooses NCP standard with one sentence of justification. No analysis of why sensorimotor inductive bias is right for association substrate. Prior v2 brain at ~1100 neurons used custom multi-module wiring (now archived) - the team chose NOT to use NCP defaults at brain level; spec doesn't explain why NCP defaults are right at lobe level.

**Mitigation gap:** §8 row 2 ("CfC learning unstable at 640 neurons") covers stability, not topology. **Add an ablation:** Layer 3 should compare NCP-standard against fully-connected RNN or random-sparse with same hidden_dim, before locking the topology choice.

### 3.4 Mutation fallback dominates real bred populations (MEDIUM × MEDIUM)

**Mechanism:** Decision H falls back to SVRule when genome shape doesn't match Bondi-spec exactly. Stock C3 mutation rates apply to brain genes too; bred-generation 2+ creatures have non-trivial probability of having one or more brain-gene mutations that change comb's W/H or tract counts. If 50%+ of a 24-hour-run population ends up on the SVRule fallback path, the CfC is not really "the brain" of the project.

**Evidence:** Acceptance §10 line 514 explicitly puts mutated norns out of v1 scope. Spec doesn't quantify expected fallback rate in a normal world tick. Phase I (genome-aware projection) is deferred without timeline or trigger.

**Mitigation gap:** §8 row 8 acknowledges "per-genome variation is a Phase E.4 concern" but does not commit to measuring fallback rate. **Add to §10 acceptance:** record `fallback_fraction` metric in Layer 3 + Layer 4 runs; if it exceeds (e.g.) 30% of the population at hour 8 of the overnight run, flag for Phase I prioritisation.

### 3.5 Reward signal off-by-one tick corrupts learning silently (MEDIUM × MEDIUM)

**Mechanism:** §9 question 3 flags this as open. If chemicals 204/205 are written by stim genes that fire after comb's update tick, the CfC's weight-update step reads last-tick reward instead of this-tick reward. Gradient still descends, but the credit assignment is shifted by one tick. Eligibility trace (20 ticks, γ=0.95) absorbs this, so failure mode is "learns slower than it should" not "doesn't learn". This is the worst kind of silent bug - never visible in Layer 1, possibly never visible in Layer 2, only shows up in Layer 3 against well-tuned baselines.

**Evidence:** §9 explicitly open question; no Layer 1 test asserts tick alignment.

**Mitigation gap:** Layer 1 should add a test: "spawn a test creature, inject a known reward at tick T, verify CfC weight-update step at tick T sees the injection." This should be an automated assertion, not a manual Phase A check.

### 3.6 Bridge per-tick overhead exceeds budget at scale (MEDIUM × MEDIUM)

**Mechanism:** §3.F + §6 E.8 measure overhead at 10 minutes single-creature. Multi-norn worlds (Layer 4 multi-norn social, 5 norns) multiply per-tick Python crossings by population. ONNX numbers cited are for single-creature inference, not for multi-norn pybind11 marshalling. Phase G acceptance overnight 8h test could miss this if it runs single-creature.

**Evidence:** §8 row 3 names overhead but mitigation is "batch multiple ticks per call" which is non-trivial (changes tick semantics); not a small fix.

**Mitigation gap:** Phase G should specify multi-norn run as part of overnight, not just single-creature. **Add to §6 G.2:** "8-hour overnight run, 5 norns, watchdog check per-tick overhead at 1h/4h/8h."

### 3.7 cc-ref.yaml drift makes the lock meaningless (LOW × HIGH)

**Mechanism:** Spec §7 commits cc-ref edits at sign-off. cc-ref currently has `lobes.decn.neurons = 17` (wrong; should be 13) and KB still serves `architecture_pivot_2026_04_25_comb` as `pending_verification` (wrong; should be `active`). If cc-ref is not corrected as part of sign-off and KB is not rebuilt, future project sessions querying the KB get stale state and re-derive incorrect contract details.

**Evidence:** Verified by tool output: `python tools/kb_lookup.py decisions` returns stale state; cc-ref line 44 has wrong decn count; KB still carries v2-era stale entries (`attn_decn_same_source`, `mod_gate`, `split_commitment`, `drives_as_data_not_mod`) that cc-ref says were removed 2026-04-26.

**Mitigation gap:** §7 lists yaml edits but does not include "fix cc-ref `lobes.decn.neurons`" or "rebuild KB". **Add Phase C.3.5:** correct decn count, rebuild KB with `python -m kb.build --force`, run reconciliation report.

### 3.8 Layer 2 baseline trace fixture rots before Phase E ships (LOW × MEDIUM)

**Mechanism:** Phase B captures a baseline trace early (1 session). Phase D builds Layer 2 harness against that trace. Phase E iterates 3-5 sessions. If openc2e is rebuilt during E with any change to PythonBrain.cpp (which Phase E.3 explicitly does), the baseline trace was captured on the old build and the comparison may be apples-to-oranges if any non-comb tick behaviour shifted.

**Evidence:** Phase B B.1 adds instrumentation to PythonBrain.cpp; Phase E E.3 modifies the same file. No spec language addresses re-capture or trace versioning.

**Mitigation gap:** Define a baseline-trace re-capture trigger (e.g., if `PythonBrain.cpp` changes outside the comb-routing additions, re-capture). Layer 2 fixture filename already includes a date, which helps.

---

## 4. Adversarial Red Team (axes a-h)

### a) The pivot from decn to comb is the wrong target

Strongest counter: the project's genome decode evidence is solid (driv + 3 forf are migrating, comb is where reinforcement lands), so the pivot is right *if* the goal is "replace the lobe that does C3's learning". But there's a different framing the spec doesn't engage: maybe the goal should be "replace the lobe whose decisions matter behaviourally", which is decn. Stock C3 famously has hand-coded decn priorities baked into the SVRule; replacing comb leaves those intact. If the project's actual user-visible quality bar is "the norn does smarter things", replacing the decision-making lobe might give faster perceived improvement than replacing the upstream learner. **Weak critique, but worth flagging:** the spec asserts comb is the right target (§3 line 80) without quantifying user-visible payoff vs decn replacement.

### b) The CfC architecture cannot beat SVRule on Layer 3 benchmarks

Stock SVRule has been hand-tuned over years by the original Cyberlife team specifically for the Bondi-spec genome on the Bondi-spec scenarios. CfC starts from random init + 10K-tick A2C. The benchmarks (`hungry-norn-with-food`, `multi-drive-mix`, `reward-burst`) are short-horizon: 5 minutes of wall time. CfC's strength is long-horizon credit assignment via continuous time and eligibility trace; in 5 minutes the eligibility trace barely fills. **Real teeth here.** Acceptance §10 demands beating stock on 2 of 3 - likely failure mode is "CfC ties or marginally beats on 1, loses on 2 because SVRule was bespoke-tuned and the time horizon is too short to exploit CfC's advantage." Mitigation absent in spec: **Layer 3 should include at least one long-horizon scenario** (e.g., 1-hour partial-day learning curve) where CfC's credit assignment can express itself.

### c) Phase A genome decode (5 sampled genomes) is insufficient evidence to lock the v1 contract

5 genomes, all Cyberlife-shipped breeds (Bondi, Harlequin, Civet, Zebra, Banshee Grendel, Final46 Ettin - Appendix A header says 5 but lists 6, an inconsistency). These all descend from the same standard Cyberlife brain genome family. Wild community archives (the 9.8 GB firecrawl corpus) contain genomes that have been hand-edited by the community for decades; many are non-standard. The "breed-stable" claim is evidence about the *Cyberlife shipped variants*, not about the *population the engine actually has to handle*. **Real teeth.** The lock is fine for *v1 scope* (Decision H deliberately limits to stock), but the spec's framing oversells: "Verified breed-stable across 5 sampled genomes" sounds like population-level evidence; it's family-level evidence. Mitigation: rephrase Appendix A header to "Verified across the Cyberlife shipped genome family"; add explicit acknowledgement that community breeds are out-of-distribution.

### d) Boundary fidelity + NCP-internal wiring is the wrong combination

Boundary fidelity preserves stock IO contract, which is good for tract-gene survival and BrainViewer rendering. NCP internals impose a sensorimotor inductive bias on a substrate that is not sensorimotor - it's strategic association. The combination has a hidden assumption: that the *boundary* and the *internals* should obey different design principles. This is unusual for neural net design; typically architecture is end-to-end-coherent. The spec's defense (§3.B line 88) is one sentence asserting NCP gives "the inductive bias it was designed for". **Real teeth.** A fully-connected RNN at 440 hidden, or a sparse random graph with NCP-style sparsity but no sensory→inter→command→motor structure, would be a more honest architectural match for an association lobe. Add to §6 D.3 or §6 G.1: ablation comparing NCP-standard vs RNN vs random-sparse, decided empirically not asserted theoretically.

### e) 440 neurons is the wrong scale (too small)

The project's prior v2 brain ran ~1100 neurons across 4 CfC modules (now archived). Comb-only at 440 is a *capacity reduction* relative to the architecture the project had been operating on. The spec defends 440 as "stock comb scale, honest test of replaceability" (§3.E line 114) - but stock comb is an SVRule lobe with dendrite migration; the SVRule semantics use 440 neurons + 8 state vars/neuron + 8 weights/dendrite + migration, an effective parameter count vastly larger than 440 floats. A CfC with 440 hidden units has roughly `440² ≈ 200K` recurrent parameters plus projections - comparable in raw count but with wholly different inductive bias. The "fits RTX 3090 by orders of magnitude" defense (§3.E line 118) answers a question nobody asked; compute was never the constraint. **Real teeth.** Capacity sufficiency is not argued; it's asserted by analogy to stock count. Mitigation: Layer 3 should include an upscale tier (e.g., 880, 1320) alongside the named subscale tiers (110, 220), so the experimental design tests whether 440 is undersized as well as oversized.

### f) A2C with eligibility trace is the wrong learning rule for this substrate

A2C has well-known instability at small batch / on-policy. Comb-narrow scope means the policy gradient is computed over comb's 51-d output space rather than a full-brain action space. This is *narrower* than the brain-scale A2C that was already debugged (Decision C asserts the existing A2C carries over). Narrowing the output space typically increases gradient variance per parameter (fewer dimensions to spread the variance across), which is exactly when value head matters most. **Real teeth.** Decision C does TWO things at once: narrows scope AND drops value head. Standard experimental hygiene says change one at a time. If Phase E.7 fails learning, the spec offers no way to tell whether the failure is from (i) narrower scope, (ii) dropped value head, or (iii) both. Mitigation: Phase E.7 should run two configurations - A2C-narrow with value head, A2C-narrow without - to cleanly isolate the value-head decision.

### g) Reward as separate scalar (not concatenated) is the wrong call

Decision G argues reinforcement is a learning-time concern, not inference-time, so it shouldn't enter the data input. This is sound for standard RL setups. **Weak critique:** the case for concatenating reward into input is mostly relevant when the policy needs to condition behaviour on recent reward history (e.g., "explore more after low reward"), and that's what the eligibility trace + entropy bonus (§3.C) is meant to handle structurally. The spec's reasoning here is correct. Worth flagging only as: "the concatenated alternative is fine as a Phase E.4+ ablation if Layer 3 reveals exploration pathology."

### h) Mutated-genome SVRule fallback (Decision H) is brittle in production

In production a "world" runs many norns over many generations, not one stock norn. Stock C3 has non-zero brain-gene mutation rates per breeding event. After a few generations, the population is a mix of stock-shape and mutant-shape. Decision H means the CfC is silently absent from a fraction of the world's brains, and that fraction grows with time. **Real teeth.** Spec deferral to Phase I is reasonable scope discipline, but the *acceptance criteria* should record fallback rate as a measurable. Without a measured fallback rate, "CfC running the brain" is unverifiable in any non-stock-only scenario. Mitigation: add to §10 a metric `cfc_population_fraction` recorded during Layer 4 multi-norn social and Layer 4 24-hour horizon scenarios.

---

## 5. Recommended Spec Changes

Each edit cites spec section and line numbers.

### 5.1 Lock the scale consistently (CRITICAL - blocks Phase E.1)

**§3.E line 112:** retain "440 neurons" - this is the genome-decoded value and matches Appendix A.

**§3.E line 116:** "Genome layout: 40 columns × 11 rows = 440 neurons" - keep.

**§6 line 357 (Phase E.1 row):** change `640 neurons, NCP wiring` to `440 neurons, NCP wiring` because 640 is the C1 Concept-lobe value the spec explicitly corrects against in §3.E line 114.

**§7 line 454-456:** change
```yaml
cfc_comb_scale:
  choice: 640
  reason: "Stock comb scale; honest test of replaceability"
  subscale_ablation_tiers: [160, 320]
```
to
```yaml
cfc_comb_scale:
  choice: 440
  reason: "Stock comb scale per genome decode of norn.bondi.48.gen, 40 columns x 11 rows; honest test of replaceability"
  subscale_ablation_tiers: [110, 220]
  upscale_ablation_tiers: [880, 1320]
```
because 440 matches §3.E and Appendix A and adding upscale tiers addresses red-team (e).

### 5.2 Fix archived-file references (CRITICAL - blocks Phase E build)

**§3.C line 92:** change `Already implemented at the brain level in openc2e/tools/nornbrain_cfc_v2.py` to `Already implemented at the brain level in openc2e/tools/nornbrain_cfc.py (the v2 module was archived 2026-04-26 as part of the v2 architecture retirement; the surviving wrapper is the active reference)` because the v2 file is under `archive/legacy-v2/code/`.

**§4 Layer 3 line 235:** change `nornbrain/multi_lobe_brain_v2.py` to `archive/legacy-v2/code/nornbrain/multi_lobe_brain_v2.py (archived; load read-only for historical comparison)` because the file is no longer in `nornbrain/`.

**§6 Phase E.4 line 360:** change `openc2e/tools/nornbrain_cfc_v2.py updated to instantiate the comb-only CfC` to `openc2e/tools/nornbrain_cfc.py updated to instantiate the comb-only CfC (the *_v2 wrapper was archived; comb-only routing builds on the surviving non-v2 module)`.

**§6 Phase E.5 line 361:** change `openc2e/tools/pretrain_instincts_v2.py` to `openc2e/tools/pretrain_instincts.py (the *_v2 variant was archived with the v2 brain)`.

**Reason across all four:** `archive/legacy-v2/code/openc2e-tools/nornbrain_cfc_v2.py`, `archive/legacy-v2/code/openc2e-tools/pretrain_instincts_v2.py`, and `archive/legacy-v2/code/nornbrain/multi_lobe_brain_v2.py` confirmed via Glob; active equivalents are the non-`_v2` siblings.

### 5.3 Resolve cc-ref decn-lobe size conflict (CRITICAL - affects output projection sizing)

**Out-of-spec change required:** correct `cc-ref.yaml lobes.decn` from `{id: "decn", neurons: 17}` to `{id: "decn", neurons: 13, grid: "1x13"}` because `python tools/kb_lookup.py lobe decn` returns 13, `python tools/decode_norn_genome.py norn.bondi.48.gen` returns `decn 13 1 13`, and spec Appendix A.3 line 561 explicitly says "11 of the 13-neuron decn lobe". cc-ref.yaml is wrong; the spec is right; cc-ref must be fixed.

**§3 add new sub-section after §3.H:** "Decn[11..12] handling: Appendix A.3 records that comb writes only to decn[0..10] and the genome wires `verb→decn[11..12]` directly. The CfC's output projection covers decn[0..10] only; decn[11..12] continues to be driven by stock SVRule. The decn argmax operates over all 13 neurons (CfC-driven [0..10] plus SVRule-driven [11..12])." Reason: spec currently leaves decn[11..12] semantics implicit; without an explicit decision, builder may either zero them, exclude them from argmax, or pass them through, producing three different action-selection behaviours.

### 5.4 Sync §2.2 with Appendix A (HIGH - eliminates "is this still pending?" ambiguity)

**§2.2 lines 50-58:** rewrite from "Pending Phase A extraction" to "Resolved by Phase A extraction (see Appendix A)". The Appendix is filled; §2.2's "pending" framing is stale. Specifically the table heading and the five rows should be flipped to "extraction completed; see Appendix A.X for value" with cross-references.

**Reason:** spec is LOCKED with Appendix A populated; §2.2 left in pre-decode form is internally contradictory.

### 5.5 Fix Appendix A header genome count (LOW)

**Appendix A line 522:** "Verified breed-stable across 5 sampled genomes:" lists 6 genomes. Change "5" to "6" or remove one genome from the list. Reason: arithmetic.

### 5.6 Add explicit decn[11..12] + verb→decn handling (HIGH)

Already covered in 5.3; flagged again because it's both a contract issue (output dim) and a semantics issue (argmax target).

### 5.7 Add reward tick-alignment Layer 1 test (MEDIUM)

**§4 Layer 1 list (lines 202-208):** add bullet "Reward signal tick alignment: inject known reward at tick T via test fixture, assert CfC weight-update step at tick T reads the injected value (not tick T-1, not tick T+1)." Reason: §9 question 3 is exactly this concern; making it a Layer 1 unit test takes the ambiguity out of the open-question pile.

### 5.8 Add C++-side input ordering Layer 1 test (MEDIUM)

**§4 Layer 1 list:** add bullet "C++ tick-loop input ordering: with `--log-comb` enabled, dump the order in which `PythonBrain.cpp` enumerates comb's input tracts on a tick, assert it matches `STOCK_INPUT_LAYOUT` declaration order from `nornbrain/cfc_comb.py`." Reason: §3.H constants pin Python-side order; nothing pins C++-side order; misalignment fails silently as garbage activations.

### 5.9 Decouple value-head decision from scope-narrowing decision (MEDIUM)

**§3.C line 96-97:** change "Value head: dropped initially..." to "Value head: BOTH configurations evaluated in Phase E.7 (with-value-head and without-value-head). Default for Phase G acceptance is whichever shows lower reward variance after 10K-tick training. Decision C narrows scope from full-brain to comb-only; the value-head decision is a separate experimental knob to avoid confounding the two changes." Reason: red-team (f).

### 5.10 Add Layer 3 long-horizon scenario (MEDIUM)

**§4 Layer 3 (lines 232-238):** add fourth scenario "Long-horizon learning curve: 60-minute partial-day run, hunger and tiredness drives, periodic food spawning. Metric: reward_rate at minute 10 vs minute 50 (positive slope = learning)." Reason: red-team (b) - 5-minute scenarios are too short for CfC's continuous-time advantage to express.

### 5.11 Add fallback-rate metric to acceptance (MEDIUM)

**§10 acceptance list (after line 512):** add "[ ] Layer 4 multi-norn social and 24-hour horizon scenarios record `cfc_population_fraction` (fraction of live norns running CfC vs SVRule fallback at each hour); fraction at hour-end >= 0.7 for stock-seeded world, with rationale documented if lower." Reason: red-team (h).

### 5.12 Add Phase C.3.5 KB rebuild + cc-ref decn correction (HIGH)

**§6 Phase C add row C.3.5:** "Correct cc-ref.yaml `lobes.decn` from 17 to 13. Run `python -m kb.build --force` and confirm KB serves locked decisions matching cc-ref. Run `python -m kb.report > docs/logs/2026-04-26-kb-reconciliation-phase-c.md`." Reason: KB drift verified by `python tools/kb_lookup.py decisions` - KB still has stale v2 entries (`attn_decn_same_source`, `mod_gate`, `split_commitment`, `drives_as_data_not_mod`) and serves `architecture_pivot_2026_04_25_comb` as `pending_verification`.

### 5.13 Specify Phase A input file (LOW)

**§6 Phase A.3 line 308:** spec says decode `default_norn.gno`. Change to `norn.bondi.48.gen` (the file the contract was actually decoded from per cc-ref `cfc_contract.contract_source` and Appendix A line 522). Reason: Bondi.48.gen is the verified source; `default_norn.gno` is a different format and a different artifact.

### 5.14 Define "beats" metric in acceptance (LOW)

**§10 line 505:** "Layer 3 live benchmark beats stock SVRule on >= 2 of 3 scenarios" → define "beats" as "reward_rate, hunger_trend, or homeostasis_index improved by >= 10% relative to stock SVRule, statistically significant over 5 random seeds". Reason: unfalsifiable as written.

---

## 6. Cross-cutting concerns

### 6.1 KB and cc-ref are out of sync

The KB still serves four v2-era entries that cc-ref says were removed 2026-04-26 (`attn_decn_same_source`, `mod_gate`, `split_commitment`, `drives_as_data_not_mod`), and serves `architecture_pivot_2026_04_25_comb` as `pending_verification` while cc-ref says `active, locked: true`. cc-ref itself has at least one wrong fact (`lobes.decn.neurons = 17`; verified-correct value is 13). The spec assumes both are reliable. Phase C.3.5 (recommended in 5.12) rebuilds the KB; cc-ref decn correction is required at sign-off.

### 6.2 Surviving nornbrain modules aren't addressed

The spec doesn't mention `nornbrain/signal_types.py`, `nornbrain/tract.py`, `nornbrain/ltm.py`, `nornbrain/telemetry.py` - the surviving infrastructure listed in CLAUDE.md Tier 2. CLAUDE.md says these are "surviving infrastructure" retained from v2. Spec §6 Phase E sequence implies a clean build of `nornbrain/cfc_comb.py` but doesn't say whether/how it integrates with the surviving modules (especially `tract.py` for sparse projections and `telemetry.py` for tick records). **Add to §6 E.1:** explicit "uses `nornbrain/tract.py` for sparse projection helpers; emits `TickRecord`s via `nornbrain/telemetry.py`" or "does not depend on surviving v2 infrastructure", whichever is true.

### 6.3 Phase F is sized too tight

§6 Phase F estimates 1-2 sessions for: implementing `caosVM_brn.cpp` skeleton, dispatch, P0 commands (DMPB, DMPL, DMPN), wire-format implementation, `commandinfo.json` updates, build, smoke test, BiV connection, plus optional P1 commands (DMPT, DMPD). Wire format reconstruction alone (per §5 reference to `docs/reference/braininavat/12-brn-dmp-wire-format.md`) is non-trivial because it's reconstructed-from-decompile. **Either expand the estimate to 3-4 sessions or scope F to P0-only with P1 as Phase F.5.**

### 6.4 No rollback procedure

Spec assumes Phase E lands successfully. There's no language for "if Phase E fails Layer 2, revert to..." paths. Stock C3 can revert by removing `--brain-module`; that should be explicit in §10 ("rollback: omit `--brain-module` flag, engine runs stock SVRule end-to-end"). Phase G has no acceptance gate definition for "what happens if we miss".

### 6.5 The "LOCKED" label is doing too much work

A spec marked LOCKED with the defects listed in §3.1 is a contradiction. Either (i) revise the spec and re-lock, or (ii) define LOCKED-with-known-amendments and list them. Recommended: do (i) - make the §5 edits, then the LOCKED label is honest.

### 6.6 Decision A's "subscale for ablations" is contradicted by §3.E

§3.A line 78 says "CfC sized for compute budget (default 640 to match stock; subscale for ablations)". §3.E line 112 says default is 440. §7 yaml says 640. **Three different defaults in three places.** This is the single highest-priority defect; it determines hidden_dim, projection sizes, training compute, and weight-file shape. The §5.1 fix takes care of §3.E and §7; §3.A line 78 also needs the same correction (440 not 640).

### 6.7 No review trail for the lock

cc-ref has a `wrapup_local_only` rule and a corrections law requiring "code + cc-ref.yaml + WM memory in ONE commit". A LOCKED governance spec arguably deserves the same standard: spec change must update cc-ref + KB + project diary in one commit. This isn't in the spec itself; recommended cross-cutting practice for Phase C sign-off.
