# NORNBRAIN v2 Roadmap

**Created:** 2026-04-01
**Source:** Architectural review session (CC + an external reviewer + the project owner)
**Status:** Active: governs all v2 development

---

## Guiding Principle

Fix, measure, then build. No live testing without evaluation. No RL without credit assignment. No scaling without benchmarks. The monitor must tell the project owner what's happening in 3 seconds.

---

## Phase A: Fix and Measure (DONE: 2026-04-02)

Two parallel tracks. Both complete.

### Branch A1: Fix the Brain

| Task | Status | Est. | Notes |
|------|--------|------|-------|
| Modulation gate `1+0.5*tanh` | DONE |: | Committed 2026-04-01 |
| RL disabled | DONE |: | Committed 2026-04-01. Re-enable in Phase B only. |
| Add ~20 conflict instinct rules | DONE |: | 16 conflict + 5 negative added (54 total). Weighted priority scoring. 2026-04-02. |
| Add negative examples to instincts | DONE |: | 5 negative rules. 2026-04-02. |
| Re-run pre-training (800 epochs) | DONE |: | 500ep LR 0.001 + eating fix retrain (multi-tick, dense vis, eat weight). 2026-04-02. |
| Verify pre-trained weights in engine | DONE |: | Live benchmark confirms norn eats (hunger dip 0.11→0.05). 2026-04-02. |

### Branch A2: Build Evaluation Framework

| Task | Status | Est. | Notes |
|------|--------|------|-------|
| Passive metrics accumulator in brain wrapper | DONE |: | MetricsAccumulator in nornbrain_cfc_v2.py. 200-tick windows. 2026-04-01. |
| Web monitor v1 (replace Tkinter) | DONE |: | Built by parallel session (web_monitor). 2026-04-02. |
| Monitor health bars (6 bars + verdict strip) | DONE |: | In web monitor. |
| Monitor automated alerts | DONE |: | In web monitor. |
| SVRule baseline benchmark script | DONE |: | tools/svrule_baseline_benchmark.py. 2026-04-02. |
| Run SVRule baseline | DONE |: | 5 min benchmark captured. eval/svrule_baseline_2026-04-02.json. 2026-04-02. |
| Data analysis tool | DONE |: | tools/analyse_brain_data.py. HTML report + auto-archive. 2026-04-02. |

### Phase A Success Criteria
- [ ] Pre-trained brain achieves >85% attn, >80% decn on expanded instinct set
- [ ] Web monitor displays all v2 data with 6 health bars
- [ ] SVRule baseline numbers recorded
- [ ] Hippocampal autocorrelation measured for v1 and v2 (signal routing validation)

---

## Phase B: Fix RL Credit Assignment (DONE: 2026-04-02)

| Task | Status | Notes |
|------|--------|-------|
| Eligibility trace buffer (20-tick, γ=0.95) | DONE | deque in nornbrain_cfc_v2.py, stores (log_prob, entropy, value) per tick |
| Value head on frontal cortex | DONE | `nn.Linear(150, 1)`: `value_head` on MultiLobeBrainV2 |
| Switch to A2C | DONE | `forward_with_policy()` + `train_a2c_batch()` replace `train_rl_step()` |
| Entropy schedule | DONE | 0.1→0.01 linear decay over 10K ticks in wrapper |
| Re-enable RL | TODO | `_rl_enabled = True`: awaiting live verification |
| Benchmark: instinct-only vs instinct+RL | TODO | Needs live engine run |

### Phase B Success Criteria
- [ ] RL credit reaches the causal action (not just the most recent)
- [ ] Value head learns to predict reward with < 0.1 MSE
- [ ] 1-hour RL run improves at least one eval metric over instinct-only baseline

---

## Phase C: Full LTM System (DONE: 2026-04-02)

Full implementation built (not minimum viable). 943-line `phase2-bridge/ltm.py`.

| Task | Status | Notes |
|------|--------|-------|
| LTM MemoryBank + MemoryRecord | DONE | 200 capacity, intensity-gated encoding, 20-tick cooldown |
| Write trigger: biochemistry threshold | DONE | Encodes when max(reward, punishment, adrenaline, pain, drive_delta) > 0.4 |
| Two-tier retrieval (coarse + cosine) | DONE | Coarse: attention category OR location zone. Fine: cosine sim > 0.6 on 845-dim context key |
| 3-slot injection (6 channels) | DONE | valence + arousal per slot, wired to ltm_to_frontal_mem tract |
| Sleep consolidation | DONE | Greedy clustering, negativity bias (neg memories resist merging), capacity eviction |
| JSON persistence | DONE | Auto-save every 500 ticks + on shutdown. Per-creature files. |
| Offspring inheritance | DONE | Attenuated parent memories (30% intensity) as instincts |
| Engine wrapper integration | DONE | Retrieve before brain tick, encode after, consolidate on sleep onset |

### Phase C Success Criteria
- [x] `ltm_to_frontal_mem` carries non-zero values (wired, active when memories match)
- [ ] Hippocampal autocorrelation increases after LTM implementation (needs live measurement)
- [ ] Novel adaptive behaviour observed requiring memory (needs live testing)

---

## Phase C.5: ONNX Benchmark (DONE: 2026-04-02, from Challenge 8)

| Task | Status | Notes |
|------|--------|-------|
| Export frontal CfC to ONNX | DONE | 2.7 MB, legacy TorchScript exporter (dynamo fails on CfC) |
| ONNX Runtime benchmark | DONE | Frontal: 0.07ms. Est full 1100: 0.11ms. 27.6x speedup over PyTorch |
| 11,000 neuron feasibility | CONFIRMED | Conservative est: 2.2ms (455 TPS). 100x under 200ms target |
| Optimal neuron count analysis | DONE | 4,000-7,000 optimal for C3 constraints. 5,500 recommended sweet spot |

---

## Phase D: Full Evaluation and Live Testing

Depends on A+B+C (all DONE). This is the first time we declare "v2 works."

| Task | Est. | Notes |
|------|------|-------|
| Structured benchmark: SVRule vs v2-instinct vs v2-RL vs v2-RL+LTM | 2 hrs | Full protocol with comparison table. |
| Overnight training run (with working RL + LTM) | 10 hrs | Watchdog script, weight snapshots every hour. |
| Post-overnight benchmark | 1 hr | Compare pre-overnight vs post-overnight metrics. |
| Write results into research document | 2 hrs | Section 17: v2 evaluation results. |

### Phase D Success Criteria
- [ ] v2 with RL+LTM beats SVRule on at least 3 of 6 eval metrics
- [ ] Novel adaptive behaviour count > 0 (CfC does something SVRules can't)
- [ ] Overnight training improves metrics (evidence of learning)
- [ ] Results documented with numbers, not vibes

---

## Phase E: Scale and Optimise (Future)

Only after Phase D proves v2 works at 1,100 neurons.

| Task | Notes |
|------|-------|
| ONNX export + C++ benchmark | DONE (2026-04-02): 27.6x speedup, 11K neurons at ~2.2ms conservative. |
| Scale to 5,500 neurons | Optimal neuron count for C3 constraints (4,000-7,000 range). User chose 5,500. |
| OnnxBrain.cpp | c2eBrain subclass, `--brain-onnx` flag. Eliminates Python from runtime. |
| Genetic evolution: breed norns | Evolve instinct rules, time biases, tract configs across generations. |
| Full LTM with sleep consolidation | DONE (2026-04-02): 943-line ltm.py with full Phase 4B spec. |
| Language system | Phase 4D. Natural language output via local LLM. |

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-01 | RL disabled until eligibility trace | Single-tick attribution corrupts instinct weights |
| 2026-04-01 | Modulation gate: `1+0.5*tanh` [0.5, 1.5] | Sigmoid centred at 0.5 starves thalamus |
| 2026-04-01 | Monitor moving to web (HTML/JS/CSS) | Tkinter is monolithic, hard to iterate, can't hot-reload |
| 2026-04-01 | Evaluation required before live testing | Can't distinguish learning from observer bias without metrics |
| 2026-04-01 | Instinct rules: weighted priority, not thresholds | Continuous trade-offs are more realistic than rigid hierarchies |
| 2026-04-01 | Evolve genome (rules), not weights | Dense weight crossover is dimensionally incompatible |
| 2026-04-01 | "Novel adaptive behaviour" replaces "instinct compliance" | Measures CfC capability, not memorisation |
| 2026-04-01 | Entropy bonus: 0.1 decaying to 0.01 | 0.01 is insufficient to escape BC local minimum |
