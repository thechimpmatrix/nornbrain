# Phase E.2 Open Questions Resolution

> Date: 2026-04-26
> Resolves §9 of `docs/specs/2026-04-26-cfc-comb-replacement-design.md`
> Status: All four questions resolvable from primary sources (C3 1999 source + 6 decoded genomes); none require running the engine.
> Sidecar to the spec; spec itself is unchanged.

---

## Q1: Genome variant cross-check (`civet46.txt` vs Bondi-spec contract)

### Finding

The contract holds. `civet46` is byte-identical to Bondi (and four other sampled genomes) on the comb lobe gene and on every comb-touching tract gene. The 107-d input / 51-d output / 440 hidden contract applies unchanged.

### Evidence

1. **`civet46.txt` is not a literal `.txt` file in the project tree.** Filesystem search across `i:/NORNBRAIN/` and `i:/NORNBRAIN-EXTERNAL/` returns:
   - `i:/NORNBRAIN-EXTERNAL/research-sources/Scrapes/double-nz-creatures/creatures3-civet46.txt` - a textual hex dump produced by an unknown community tool. Line 2 of that file declares its source: `norn.civet46.gen.brain.gen` (not present locally as a `.gen` file).
   - `i:/NORNBRAIN/creaturesexodusgame/Creatures Exodus/Creatures 3/Genetics/norn.expressive.civet.47.gen` - the local C3 install ships the version-47 expressive Civet, which is the closest direct equivalent.
   - The "46" / "47" / "48" suffix is the CL game-build version (Creatures 3 built ~46-48), not a generation index inside the genome.

2. **Comb lobe matches Bondi exactly across 6 sampled genomes.** Re-decoding via `tools/decode_norn_genome.py` plus a bespoke SVRule-bytecode extractor (run inline from this session) over `norn.bondi.48.gen`, `norn.harlequin.48.gen`, `norn.expressive.civet.47.gen`, `norn.zebra.48.gen`, `gren.banshee.49.gen`, `ettn.final46e.gen.brain.gen` returns identical comb lobe bytes for all six:

   | Field | Value (all 6 genomes) |
   |---|---|
   | `updatetime` | 20 (sort-key, see Q3 clarification) |
   | `x, y` | (5, 22) |
   | `width × height` | 40 × 11 = 440 neurons |
   | `RGB` | (255, 222, 203) |
   | `WTA, tissue, initrulealways` | (0, 255, 1) |
   | `initrule` (48 bytes hex) | `0b07d5340f0b180b420a0302180bc7030a000a0302030900230303340f0c010303010302030303070b31010303000303` |
   | `updaterule` (48 bytes hex) | `180bca0303011903000203000103013504000104020203023f0f03030bc70b07d5030a00060303020303420f031f0000` |

3. **`creatures3-civet46.txt` (the external scrape dump for the literal `civet46.gen.brain.gen`) shows the same comb topology.** Lobe 5 (`comb`) at X=5 Y=22 is 40 × 11 = 440 neurons (line 104 of the dump). Six input tracts to comb (driv→comb full + stim→comb full + verb→comb full + 3× forf→comb at [40-79], [200-239], [280-319]) and two output tracts (comb→attn full + comb→decn[0..10]) appear in dump lines 319, 336, 354, 371, 388, 541, 558, 575 - matching Appendix A.2 / A.3 of the spec exactly.

4. **`norn.expressive.civet.47.gen` is the same genome the Appendix A "5 sampled genomes" claim refers to** (Appendix A names "Civet (expressive variant)"). Confirmed identical to Bondi by item 2.

### Impact on spec

**No change.** Contract is locked at 107 / 51 / 440 across every official C3 1999 breed sampled. Spec's Decision E (440 neurons) and Decision H (stock-breed contract for v1) stand as written. The literal text "civet46.txt" in §9.1 should be read as "civet46-class genome" - concretely satisfied by the local `norn.expressive.civet.47.gen`.

---

## Q2: Opcode 35 (`tendToAndStoreIn`) usage in stock comb

### Finding

**Opcode 35 IS used by stock comb on every tick during normal awake/non-REM operation** (the dominant execution path). It does NOT appear in the comb's update rule, but it appears at entry 8 of the comb's INIT rule, AND `initrulealways=1` for comb causes the init rule to fire BEFORE the update rule on every tick. Opcode 35 is gated OFF only on the REM-sleep branch (`chem[213] != 0` → goto entry 11, which zeroes the comb output). Decision D's "deviation documented" stance is operationally non-trivial; Layer 2 calibration must allow for the deviation. Decision D is NOT moot.

### Evidence

1. **Opcode 35 = `tendToAndStoreIn` (decimal 35, not hex 0x35).** Source: `C3sourcecode/engine/Creature/Brain/SVRule.h:63-117` `OpCodes` enum, counted from 0. Hex 0x35 = 53 = `ifLessThanStop`, which is a different (unrelated) opcode and appears in the comb update rule but is not the "backwards-formula" opcode.

2. **The "backwards-formula" implementation.** `SVRule.h:280-285`:

   ```cpp
   case tendToAndStoreIn:
       *pointerOperand = BoundIntoMinusOnePlusOne(
           accumulator*(1.0f-tendRate) +
           (*pointerOperand)*tendRate
       );
   ```

   With `tendRate=r`, the new value is `accumulator*(1-r) + old*r`. Standard convention is `accumulator*r + old*(1-r)`, so the role of `r` is inverted: a high `tendRate` means SLOW tracking of new (most weight on old), not FAST tracking. This is the documented bug recorded in `cc-ref.yaml gotchas.svrule_opcode_35_backwards_warning`.

3. **Comb's init rule entry 8 IS opcode 35.** From the per-genome bytecode decode (this session, all 6 genomes identical):

   ```
   INIT rule entry 8: op=35 (tendToAndStoreIn) var=3 (neuron) val=3 (THIRD_VAR)
   ```

   Surrounding context (init rule entries 0-12). **Conditional semantics per `SVRule.h:383-388`:**
   - `ifNonZero X` → `if (operand==0.0f) i++;` → execute next instruction IF X is nonzero (skip when zero).
   - `ifZero X` → `if (operand!=0.0f) i++;` → execute next instruction IF X is zero (skip when nonzero).

   ```
   [ 0] ifNonZero chemical[213]      (execute next IF chem 213 != 0; else skip entry 1)
   [ 1] gotoLine 11                  (jump to entry 10; reached only on REM branch - see note)
   [ 2] setTendRate 66               (rate ≈ 66/248 = 0.266)
   [ 3] ifZero neuron OUTPUT         (execute next IF OUTPUT == 0; else skip entry 4)
   [ 4] setTendRate 199              (rate ≈ 199/248 = 0.802)
   [ 5] loadAccumulatorFrom one      (acc = 1)
   [ 6] ifZero neuron OUTPUT         (execute next IF OUTPUT == 0; else skip entry 7)
   [ 7] loadAccumulatorFrom zero     (acc = 0)
   [ 8] tendToAndStoreIn neuron THIRD     ← OPCODE 35 (reached on the chem[213]==0 path)
   [ 9] gotoLine 12                  (jump to entry 11; bypasses entry 10)
   [10] blankOperand neuron THIRD    (only reached on REM branch via entry 1 → THIRD = 0)
   [11] blankOperand neuron OUTPUT   (zeroes OUTPUT before update rule runs)
   [12] loadAccumulatorFrom neuron THIRD
   ```

   **`gotoLine N` lands on entry N-1**, per `SVRule.h:478-491`: `int newLoc = Map::FastFloatToInteger(operand) - 1; ... if (newLoc > i) i = newLoc - 1;` - and the `for` loop's `i++` then steps to `newLoc`. So `gotoLine 11` resumes at entry 10, and `gotoLine 12` resumes at entry 11. The simulator implementer should code this from `SVRule.h:478-491` directly rather than by analogy.

   **Control flow:**
   - `chem[213] != 0` (creature in REM sleep): entry 0 lets entry 1 run → `gotoLine 11` resumes at entry 10 → entry 10 zeroes THIRD → entry 11 zeroes OUTPUT → fall into entries 12-15. **Opcode 35 NOT reached on the REM branch.**
   - `chem[213] == 0` (awake or non-REM sleep): entry 0 skips entry 1 → fall through entries 2-7 (all of which set up acc and tendRate based on OUTPUT) → **entry 8 (opcode 35) executes**, blending acc into THIRD with the buggy rate. Then entry 9 `gotoLine 12` resumes at entry 11 → zero OUTPUT → fall into 12-15. **The init rule always zeroes OUTPUT before the update rule runs.** The update rule (entries 0-7) is what then recomputes OUTPUT from INPUT - so stock comb's nonzero outputs come from the update rule, not from the init rule's tend-and-store on THIRD.

   **Chemical 213 identity (KB lookup):** `chem[213]` is the **REM sleep flag** for instinct-dreaming (`kb chemical 213` → "REM sleep / brain_chemical / REM sleep flag for instinct-dreaming"). Creatures spend the dominant fraction of their life NOT in REM sleep, so the chem[213]==0 branch (with opcode 35) is the typical execution path. During REM sleep / instinct-dreaming the comb output is force-zeroed (entry 11) and the slow-tracker THIRD is NOT updated by opcode 35.

4. **Comb's update rule does NOT use opcode 35.** Disassembly (this session) of the 48-byte update rule shows opcodes 24, 3, 25, 2, 1, 53, 1, 2, 63, 3, 11, 3, 6, 2, 66, 31. Opcode 35 absent.

5. **Why opcode 35 still fires per tick: `initrulealways=1`.** The "init rule runs once at neuron creation" reading is wrong for stock comb. Two pieces of source confirm:

   - `Lobe.cpp:68`: `myRunInitRuleAlwaysFlag = genome.GetCodon(0,1) > 0 ? true : false;` - read directly from the genome's `initrulealways` byte.
   - `Lobe.cpp:240-253` (inside `DoUpdate()`, which runs every brain tick):

     ```cpp
     if( myRunInitRuleAlwaysFlag )
     {
         returnCode = myInitRule.ProcessGivenVariables(...);
         ...
     }
     returnCode = myUpdateRule.ProcessGivenVariables(...);
     ```

   Comb's `initrulealways=1` (verified across all 6 genomes - see Q1 evidence). So the init rule (with its opcode 35 at entry 8) runs every tick on every comb neuron, BEFORE the update rule.

6. **Functional role of THIRD_VAR (the variable opcode 35 writes to).** THIRD_VAR is read and modified by the update rule:

   - update entry 8: `preserveVariable 3` (saves THIRD_VAR into FOURTH_VAR scratch slot)
   - update entry 12: `ifGreaterThan neuron THIRD` (gates winner-detection)
   - update entry 13: `storeAccumulatorInto neuron THIRD` (writes new tracking value)
   - update entry 14: `restoreSpareVariable 3` (restores THIRD on the spare/winning neuron)

   THIRD_VAR is used as a slow-tracking "have we recently been a winner" memory, modulated each tick by the init rule's opcode-35 tend (chemical-213-gated reset to 0 or 1). The "backwards-rate" bug means the persistence of this memory differs from the obvious reading of the genome's tendRate=199 codon.

### Impact on spec

**Decision D: clarification required, decision unchanged.** Decision D's text "the CfC's weight update step uses standard (1-r)*old + r*new blending, not the operand-side store the stock SVRule opcode 35 produces" remains correct, but the affected surface is broader than the spec's wording implies - opcode 35 fires in comb's per-tick init pass, on every neuron, on the THIRD_VAR slow-tracking slot.

**Layer 2 calibration**:
- The CfC has no direct analogue of THIRD_VAR. Behavioural equivalence at the per-neuron-state level cannot be expected even before opcode 35 enters the picture; opcode 35 just adds another reason why per-neuron trajectories will diverge.
- At the lobe-output level (the level Layer 2 actually compares - output vector + decn argmax), the impact of THIRD_VAR's slow-tracking on the output `storeAccumulatorInto OUTPUT_VAR` (update entry 7) is the relevant signal. Layer 2's per-element MSE threshold should be calibrated against an empirical baseline that includes the bug's effect, not against a corrected-blending counterfactual.
- Recommend Phase D.2 add a sanity check: replay a section of the Phase B trace through both an opcode-35-correct and an opcode-35-buggy SVRule simulator; the difference quantifies the tolerance budget Layer 2 must absorb. This is cheap (Python sim, no engine rebuild) and gives a defensible per-element MSE bound. **Critical for the simulator: implement the conditional gating per the corrected control-flow trace above** (`ifNonZero` = "execute next IF nonzero", `ifZero` = "execute next IF zero"); a sim that inverts this will compute the wrong bound.
- Consider also logging `chem[213]` alongside comb state in the Phase B reference trace, to empirically confirm the awake-vs-REM execution-path split and quantify the fraction of ticks on which opcode 35 actually fires under the chosen feed-eat-rest cycle. If the cycle includes any napping, the REM branch will be exercised and provide ground truth for both branches.

**Spec text suggestion (for next spec revision, not for this sidecar):** §3.D currently phrases the deviation as "where the deviation manifests: the CfC's weight update step". More precisely, the deviation manifests in **how the stock comb's THIRD_VAR slow-tracker integrates the chemical-213-gated reward signal each tick** (init rule opcode 35), and the CfC by replacing the entire mechanism does not reproduce this slow-tracking dynamic.

---

## Q3: Reward chemistry (chemicals 204 / 205) tick alignment with comb update

### Finding

The CfC reads chemicals 204/205 from a shared chemical array that may be modified at any point during the game tick. Within one creature tick (every 4 game ticks), the brain faculty (where the CfC weight-update step would run via the bridge) executes BEFORE the biochemistry faculty's metabolic update. So the CfC sees:

- **This-tick** values for any chemical adjustments written before the brain step (synchronous STIM macros from CAOS scripts: food being eaten, ORDR commands, ESL events, sensory triggers - all of which can fire from arbitrary script invocations earlier in the same game tick).
- **Last-tick** values for any chemical changes coming from biochemistry's own metabolic pass (chemical reactions, half-life decay) - those run AFTER the brain step within the same creature tick, so the brain sees them next creature tick (4 game ticks later).

Stock C3 comb does not read chemicals 204/205 directly. It reads them indirectly via `Tract::ProcessRewardAndPunishment()` which fires inside each tract's per-tick `DoUpdate()`. The reward chemicals are sampled at THAT moment - the same tick semantics apply. So the spec's "reward chemistry tick" framing matches stock behaviour at the level of which-game-tick-the-value-was-written, but the CfC's bridge-side read happens at the START of the brain faculty step (when the bridge hands inputs to Python) rather than per-tract during the brain's internal sort order.

### Evidence

1. **Per-creature-tick faculty ordering.** `Creature.cpp:211-251`:

   ```cpp
   if ((myUpdateTick%4)!=myUpdateTickOffset) { ...; return; }   // tick every 4 game ticks
   ...
   for (int i=0; i<noOfFaculties; i++)
   {
       myFaculties[i]->Update();
   }
   ```

   Faculty index assignments (verified at `Creature.cpp:336-344`): `0=Sensory, 1=Brain, 2=Motor, 3=Linguistic, 4=Biochemistry, 5=Reproductive, 6=Expressive, 7=Music, 8=Life`. Brain runs at slot 1, Biochemistry at slot 4 - Brain reads chemicals BEFORE Biochemistry recomputes them.

2. **Synchronous STIM-driven chemical writes.** `SensoryFaculty::Stimulate()` (`SensoryFaculty.cpp:624-724`) is invoked synchronously from CAOS script handlers (the `STIM SHOU`, `STIM TACT`, `STIM WRIT`, etc. macros are routed here). It calls `AdjustChemicalLevel()` (`SensoryFaculty.cpp:754-759`) which immediately calls `Biochemistry::AddChemical(whichChemical, adjustment)` - a direct write to the chemical array, no buffering. So a food agent's eat-script that fires `STIM SHOU 80 ...` (where stim 80 maps to chemical 204 reward emission via the genome's stimulus library) writes to chemical 204 right at the moment that script runs. If that happens before the creature's brain faculty step in the same game tick, the brain sees the new value.

3. **Stock comb does NOT read chemicals 204/205 directly.** It reads through the `Tract::ReinforcementDetails` indirection. `Tract.cpp:1080-1102`:

   ```cpp
   void Tract::ProcessRewardAndPunishment( Dendrite &d )
   {
       if( !(myReward.IsSupported()||myPunishment.IsSupported()) ) return;
       if( d.dstNeuron->states[OUTPUT_VAR] == 0.0f ) return;
       if( myReward.IsSupported() )
           myReward.ReinforceAVariable( myPointerToChemicals[myReward.GetChemicalIndex()],
                                        d.weights[WEIGHT_SHORTTERM_VAR] );
       if( myPunishment.IsSupported() )
           myPunishment.ReinforceAVariable( myPointerToChemicals[myPunishment.GetChemicalIndex()],
                                            d.weights[WEIGHT_SHORTTERM_VAR] );
   }
   ```

   Called per-dendrite from `Tract::DoUpdate()` (`Tract.cpp:404-444`, line 436). The chemical index is set per-tract via SVRule opcodes 59 (`setRewardChemicalIndex`) and 62 (`setPunishmentChemicalIndex`) at brain init. For stock C3 comb-touching tracts (driv→comb, forf→comb regional tracts) the index is 204/205.

4. **The CfC bridge will read chemicals once per brain tick at the start of Brain::Update.** Per Decision G, the bridge reads `(chem[204], chem[205])` at the moment the bridge hands input to Python. This is roughly equivalent to "what stock comb tracts see when they fire", because `Brain::UpdateComponents()` (`Brain.cpp:363-378`) iterates components in `updateAtTime` order - and stock comb's input tracts and comb itself all run inside the brain step. Within that brain step the chemical pointer is shared; intra-step writes don't happen because no SVRule write opcode targets `myPointerToChemicals` directly.

5. **`updateAtTime` is a sort key, not a frequency** (this clarification matters for the spec wording - see "Spec wording flag" below). `BrainComponent.cpp:59-61`:

   ```cpp
   bool BrainComponent::xIsProcessedBeforeY(BrainComponent* x, BrainComponent* y) {
       return x->myUpdateAtTime < y->myUpdateAtTime;
   }
   ```

   `Lobe::DoUpdate()` (`Lobe.cpp:222`): `if (myUpdateAtTime==0) return;` - only gating is "skip if zero". openc2e (`c2eBrain.cpp:1031-1037`) ticks the same way; no modulo on `updatetime`. The 20 in comb's `updatetime` byte is a sort key positioning comb relatively late in the brain step - after low-`updatetime` components (input lobes, perception tracts). It does NOT mean "every 20 ticks".

### Impact on spec

**Decision G: clarification required, decision unchanged.** The "explicit reward channel separate from data signals" choice is correct and matches stock behaviour at the chemical-array level. The bridge needs only to:

- Read `chem[204]` and `chem[205]` once at the start of each brain step (inside the bridge entry point that PythonBrain.cpp will gain in Phase E.3).
- Treat the read as "this game-tick's effective reward signal" - it correctly captures synchronous STIM-induced chemicals from earlier in the same game tick, and (one creature tick of) lag from biochemistry's own dynamics.

**Spec wording flag (for next spec revision, not for this sidecar):** Appendix A.1 says "Update time | every 20 ticks" - this should be "Update time (sort key) | 20 (positions comb late in the brain step; non-zero so it actually ticks; the brain ticks every creature tick = every 4 game ticks)". The current wording invites the misreading "comb only updates once per 20 ticks", which is wrong by both stock C3 source (`Lobe.cpp:222`) and openc2e (`c2eBrain.cpp:1034`).

**No engine experiment required.** Q3 is fully resolvable from source.

---

## Q4: Stock comb output norm (clamp to [-1, +1] vs unbounded)

### Finding

**Stock comb output activations are clamped to [-1, +1].** The CfC's output projection should match this convention (e.g., `tanh` activation on the output projection, or explicit clamp), so Layer 2 behavioural equivalence comparison is on the same numerical range.

### Evidence

1. **Comb update rule entry 7 writes OUTPUT_VAR via `storeAccumulatorInto`.** From the per-genome bytecode decode (this session, all 6 genomes identical):

   ```
   UPDATE rule entry 7: op=2 (storeAccumulatorInto) var=3 (neuron) val=2 (OUTPUT_VAR)
   ```

   This is the operation that writes the output value the downstream tracts will read.

2. **`storeAccumulatorInto` clamps to [-1, +1].** `SVRule.h:271-273`:

   ```cpp
   case storeAccumulatorInto:
       *pointerOperand = BoundIntoMinusOnePlusOne(accumulator);
       break;
   ```

3. **`BoundIntoMinusOnePlusOne` is a hard clamp.** `Maths.h:23-25`:

   ```cpp
   inline float BoundIntoMinusOnePlusOne(float x) {
       return x>1.0f ? 1.0f : x<-1.0f ? -1.0f : x;
   }
   ```

4. **All operand-write opcodes that could touch OUTPUT_VAR clamp similarly.** `SVRule.h:269-294` shows `storeAccumulatorInto`, `addAndStoreIn`, `tendToAndStoreIn`, `blankOperand` all use `BoundIntoMinusOnePlusOne` (or implicit zero for `blankOperand`); only `storeAbsInto` uses `BoundIntoZeroOne` (which is a tighter constraint, [0, +1]). Comb's update rule writes OUTPUT_VAR only through `storeAccumulatorInto` (entry 7) and `blankOperand` (init entry 11); both yield values in [-1, +1].

5. **In practice the comb output is mostly [0, +1].** The update rule path that writes OUTPUT_VAR (entries 5-7) gates on `ifLessThanStop` against `spareNeuronCode STATE_VAR` (entry 5), then `blankOperand spareNeuron OUTPUT` (entry 6), then `storeAccumulatorInto neuron OUTPUT` (entry 7). The accumulator at this point is the result of `tendAccumulatorToOperandAtTendRate neuron STATE` (entry 2) which blends INPUT and STATE - both of which themselves are clamped to [-1, +1] by upstream tracts. Negative outputs are reachable but uncommon for stock comb under normal stimulus patterns. The CfC's output projection should still target the full [-1, +1] range, not [0, +1].

### Impact on spec

**No change to decisions; clarification for the implementation in §3.A and §6.E.1.** The CfC module proper (Phase E.1) should:

- Apply a `tanh` activation on the output projection (or explicit `torch.clamp(x, -1, 1)`) so its output range matches stock comb. Either is acceptable; `tanh` is smooth and gradient-friendly, `clamp` is bit-identical to the stock semantic.
- Layer 1 contract test (Phase D.1) should assert the CfC's output is in [-1, +1] for any input.
- Layer 2 (Phase D.2) compares output vectors element-wise; same range on both sides means MSE thresholds are interpretable.

**Recommend `tanh` over hard clamp.** The CfC trains via gradient descent through the output projection; hard clamp produces zero gradient outside [-1, +1] which can stall learning early in pretraining. `tanh` saturates softly. The stock SVRule clamp is post-write (it doesn't propagate into a learning rule), so the CfC isn't required to bit-match the clamp shape - only the output range.

**No engine experiment required.** Q4 is fully resolvable from source.

---

## Summary table

| Q | Status | Spec impact |
|---|---|---|
| Q1 - Genome variant | Resolved (no engine run) | None. Contract holds across 6 sampled genomes including civet-class. Spec §9.1 reference to "civet46.txt" is satisfied by the local `norn.expressive.civet.47.gen` and verified against the external `creatures3-civet46.txt` scrape dump. |
| Q2 - Opcode 35 in stock comb | Resolved (no engine run) | Clarification required, decision unchanged. Opcode 35 fires per-tick on the awake/non-REM branch (the dominant execution path) via init rule entry 8 under `initrulealways=1`; it is gated OFF only during REM sleep (`chem[213] != 0`). Decision D's documented deviation is operationally significant; Layer 2 calibration must allow for it. Recommend Phase D.2 add an opcode-35 correct-vs-buggy delta sanity check (with corrected `ifZero`/`ifNonZero` semantics) to size the tolerance budget, and that Phase B trace also logs `chem[213]` to ground-truth the branch split. |
| Q3 - Reward chemistry tick alignment | Resolved (no engine run) | Clarification required, Decision G unchanged. Bridge reads `chem[204]/chem[205]` once at the start of the brain step. Sees this-tick values for synchronous STIM macros that fired before the brain step; sees (one creature tick = 4 game ticks of) lag for biochemistry's own metabolic changes. Spec wording flag: Appendix A.1's "every 20 ticks" should be "sort key 20" - `updatetime` is order, not frequency. |
| Q4 - Stock comb output norm | Resolved (no engine run) | Decision unchanged; implementation guidance for Phase E.1. Stock comb output is clamped to [-1, +1] by `BoundIntoMinusOnePlusOne` inside `storeAccumulatorInto`. CfC output projection should use `tanh` (preferred) or explicit clamp to match. |

---

## Phase E readiness

**Phase B (instrumentation) and Phase E (CfC implementation) are unblocked.** All four §9 questions are resolved from primary sources without needing an engine run.

Pre-implementation deltas to capture (do not require spec edits, but should be carried into the implementing CLI session's notes):

0. **Phase B trace additions:**
   - Log `chem[213]` (REM-sleep flag) per tick alongside comb input/state/output. Lets the Layer 2 calibrator partition trace ticks by opcode-35-fired vs opcode-35-skipped and quantify each branch's contribution to per-element output drift. Cheap (1 extra float per tick).

1. **Layer 1 contract test additions:**
   - Assert CfC output ∈ [-1, +1] for arbitrary input (Q4 evidence).
   - Assert reward channel decoupled from data input (already in spec).

2. **Layer 2 behavioural-equivalence calibration:**
   - Run an opcode-35-correct vs opcode-35-buggy SVRule simulator delta on the Phase B trace (Q2 finding). The resulting per-element MSE delta sets a defensible lower bound on the Layer 2 tolerance - anything tighter would reject the corrected CfC for behaviour the buggy stock implementation also doesn't reproduce. **Implement the conditional gating per the corrected `ifNonZero`/`ifZero` semantics in Q2 evidence item 3** - a sim with the conditionals inverted will produce a wrong tolerance bound.
   - Compare output vectors element-wise on the [-1, +1] range; tanh-output CfC should match this naturally.

3. **Bridge implementation (Phase E.3):**
   - Read `chem[204]` and `chem[205]` once at the entry to the bridge call (Q3 finding). No need to read multiple times within the brain step; the chemical array isn't mutated between component updates inside `Brain::UpdateComponents()`.
   - Surface `(reward, punishment)` as separate scalars to Python; do not pre-subtract on the C++ side. Python performs `r = reward - punishment` after smoothing/clipping if needed.

4. **CfC architecture (Phase E.1):**
   - Output projection ends in `tanh` or explicit clamp to [-1, +1] (Q4).
   - Internal state has no direct equivalent of THIRD_VAR (Q2 implication); accept this as architectural divergence and rely on NCP hidden state to subsume the slow-tracking memory role.

5. **Spec text deltas to fold into the next spec revision** (sidecar records these; spec is unchanged in this session):
   - Appendix A.1 "every 20 ticks" → "sort key 20 (positions comb late in the brain step; brain ticks every creature tick = every 4 game ticks; non-zero `updatetime` means actually-ticking, not modulo-frequency)".
   - §3.D phrasing tightened to mention the per-tick init-rule-fires-every-tick semantics under `initrulealways=1` and that opcode 35 fires on the THIRD_VAR slow-tracker, not on the output value directly.

---

## Source citations summary

- `C3sourcecode/engine/Creature/Brain/SVRule.h:63-117` - opcode enum
- `C3sourcecode/engine/Creature/Brain/SVRule.h:269-294` - operand-write opcode handlers
- `C3sourcecode/engine/Creature/Brain/SVRule.h:280-285` - `tendToAndStoreIn` formula (the documented bug)
- `C3sourcecode/engine/Creature/Brain/Lobe.cpp:41-100` - Lobe genome reader (line 68 = `myRunInitRuleAlwaysFlag` source)
- `C3sourcecode/engine/Creature/Brain/Lobe.cpp:215-271` - `Lobe::DoUpdate()` (line 240 = init rule fires before update rule when flag is true)
- `C3sourcecode/engine/Creature/Brain/Brain.cpp:134-135, 363-378` - brain component sort + tick loop
- `C3sourcecode/engine/Creature/Brain/BrainComponent.cpp:59-61` - sort comparator (proves `updatetime` is sort key)
- `C3sourcecode/engine/Creature/Brain/Tract.cpp:404-444, 1075-1111` - `Tract::DoUpdate()` and `ProcessRewardAndPunishment()`
- `C3sourcecode/engine/Creature/Creature.cpp:211-251, 336-344` - per-creature-tick faculty ordering
- `C3sourcecode/engine/Creature/CreatureConstants.h:33` - "TaskHandleBrainWave() ... currently every 4 ticks"
- `C3sourcecode/engine/Creature/SensoryFaculty.cpp:624-759` - synchronous STIM → `Biochemistry::AddChemical` write path
- `C3sourcecode/engine/Maths.h:23-25` - `BoundIntoMinusOnePlusOne` clamp
- `openc2e/src/openc2e/creatures/c2eBrain.cpp:1031-1037` - openc2e tick loop (matches stock semantics)
- `openc2e/src/fileformats/genomeFile.h:195-223` - `c2eBrainLobeGene` byte layout (used to decode 6 genomes this session)
- 6 genome files at `creaturesexodusgame/Creatures Exodus/Creatures 3/Genetics/`: `norn.bondi.48.gen`, `norn.harlequin.48.gen`, `norn.expressive.civet.47.gen`, `norn.zebra.48.gen`, `gren.banshee.49.gen`, `ettn.final46e.gen.brain.gen`
- `i:/NORNBRAIN-EXTERNAL/research-sources/Scrapes/double-nz-creatures/creatures3-civet46.txt` - external community hex dump of `norn.civet46.gen.brain.gen` (used for Q1 cross-check)
