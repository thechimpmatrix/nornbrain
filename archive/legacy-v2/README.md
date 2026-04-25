# archive/legacy-v2/

This folder holds retired material from the v2 architecture phase of the project. None of the content here describes how the project works today, and nothing inside should be cited as authoritative.

## Why this folder exists

Between March and early April 2026 the project pursued a v2 architecture, which placed four CfC modules (thalamus, hippocampus, amygdala, frontal) in a 1,100-neuron sequential pipeline as a wholesale replacement for the SVRule brain. On 2026-04-25 a live brain inspection revealed that the comb (combination) lobe is the actual learning substrate in stock C3, and the decn (decision) lobe is plumbing without learning behaviour of its own. The v2 architecture was retired, and the project pivoted to a comb-replacement design that keeps all SVRule plumbing intact and substitutes only the comb lobe with a CfC module.

The current architecture is documented at `docs/specs/2026-04-26-cfc-comb-replacement-design.md` in the project root.

## What is in here

| Path | Origin |
|------|--------|
| `code/nornbrain/` | The v2 brain Python code (`multi_lobe_brain.py`, `brain_genome.py`, `norn_brain.py` and associated v2 modules) |
| `docs/roadmap-v2.md` | The v2 roadmap that governed work until the comb pivot |
| `docs/nornbrain-research-document.md` | Research document written against the v2 architecture, pending rewrite for the comb-replacement architecture |
| `docs/specs/` | All v2-era design specs (Phase 1 through 4d, monitor v2, brain architecture v2, stimulus override, test harness) |
| `docs/plans/` | All v2-era implementation plans |
| `docs/ideas/svbrain-distillation-training.md` | Distillation idea recorded during v2 study work |
| `eval/` | v2-era benchmark JSON, ONNX export, and weight snapshots |

## Reading guide

For historical context, the architectural review log is the entry point, followed by `roadmap-v2.md` and any specific spec. Nothing in this folder reflects current decisions, and the operator manual and research document in particular should be read with that warning in mind.
