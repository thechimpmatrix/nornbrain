# Idea: SVRule Brain Distillation for CfC Baseline Training

**Date:** 2026-04-01
**Status:** PARKED: revisit when v2 architecture is built and ready to train
**Related:** [NB Brain Architecture v2](../superpowers/specs/2026-04-01-nb-brain-architecture-v2-design.md)

---

## Concept

Instead of (or in addition to) hand-coded instinct rules, use the original SVRule brain as a **teacher network**. Record what the C3 brain actually does in real game situations, then train the CfC to replicate those decisions as its baseline.

This distils 25 years of tuned C3 brain behaviour into the new architecture. RL refines from there.

---

## Experimental Setup

1. **Hatch N norn babies** in openc2e (default SVRule brain, no `--brain-module`)
2. **Lock aging**: zero life-stage chemicals each tick via CAOS so they stay babies (no growth, no death)
3. **Trap in terrarium**: contained environment with food, toys, critters. Safe from grendels
4. **Record every tick**: log full input state + SVRule decisions to CSV
5. **Run for hours**: thousands of (input, decision) pairs per norn

## Data Format (per tick, per creature)

| Field | Dimensions | Source |
|-------|-----------|--------|
| drives | 20 | DRIV 0..19 |
| key chemicals | 16+ | CHEM (selected subset) |
| visn lobe | 40 | vision categories |
| smel lobe | 40 | smell categories |
| prox lobe | 20 | proximity |
| sitn lobe | 9 | situation |
| detl lobe | 11 | detail |
| stim lobe | 40 | stimulus source |
| loc | 2 | creature location |
| **ATTN target** | 1 (of 40) | attention winner (label) |
| **DECN action** | 1 (of 14) | decision winner (label) |

## Implementation: Option B (recommended): C++ Recording Hook

Add `--brain-record output.csv` flag to openc2e. Small change in `c2eBrain::tick()` that logs the full input vector + attention/decision outputs each tick. No behaviour change: SVRule runs normally, data is just captured.

- Perfect data (no missed ticks)
- Small C++ change + rebuild
- One CSV per creature, or unified with creature ID column

## Why This Beats Synthetic Instincts Alone

- Real sensory distributions from actual gameplay
- Real drive dynamics (hunger rising, being satisfied by eating)
- Compound situations the 33 hand-coded rules don't cover (hungry + scared + near toy)
- Edge cases you'd never think to write
- SVRule brain community-tuned for decades
- Could combine: instinct pre-training first, then SVRule distillation as fine-tuning

## Steps When Ready

1. Add `--brain-record` flag to openc2e C++ (instrument `c2eBrain::tick()`)
2. Rebuild openc2e
3. Write CAOS script: hatch N babies, lock age, teleport to terrarium
4. Run recording session (hours)
5. Write training script: CSV → MultiLobeBrainV2 supervised training
6. Compare behaviour: instinct-only vs distilled vs both
