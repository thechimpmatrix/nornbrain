# NORNBRAIN

NORNBRAIN replaces the stock Creatures 3 SVRule combination (comb) lobe with a Closed-form Continuous-depth (CfC) module wired according to a Neural Circuit Policy (NCP). The replacement runs inside a modified openc2e 64-bit engine via pybind11, which means the Python brain ticks within the C++ engine loop and there is no external bridge to maintain.

The companion engine fork lives at [`thechimpmatrix/openc2e-nb`](https://github.com/thechimpmatrix/openc2e-nb).

---

## A note on the project's state and collaboration

This project is a heavy work-in-progress. I am in the process of designing a new CfC-based brain architecture that will mimic the original game's mechanics and be neurobiologically informed and rooted, with the hope that eventually a system can be created which will allow for increased learning and decision-making capacity for Norns in-game.

Please do not be angry about broken code. I am an occupational therapist and human biology graduate by trade, with a career in mental health and neuroscience. I am not a coder.

The documentation in this repository was written with substantial AI assistance for expediency, and AI tools have a tendency to overstate a project's state. Please read accordingly. I work full-time and do not have the capacity to write thirty-plus technical documents manually, so I leveraged the expediency of AI to get the scaffolding down.

The brain as it stands is not yet functional to the point of replicating normal SVRule brain behaviour. I do believe it has the bones to one day reach that point, and beyond it.

This started as a passion project, because I began playing Creatures 1 when I was nine years old, which sparked a lifetime interest in artificial life, neuroscience, and neural networks. With the advent of Claude Code, an avenue to really learn the coding and mathematical components of those fields opened up, and I grabbed it with two hands.

I know the limits of my knowledge and capacity, and my hope is that by publicising the project, more knowledgeable people than me could put heads together with me to make this really work. I am aware there may be severely impactful decisions I have made, or baseline assumptions which could become failure modes for the project, which is why I would value more experienced eyes joining the project.

Please consider joining the team.

---

## Status

Phase E.2 is the active design. The locked specification is at [`docs/specs/2026-04-26-cfc-comb-replacement-design.md`](docs/specs/2026-04-26-cfc-comb-replacement-design.md). Implementation of the engine-side wrapper is the current work item.

---

## The journey

This project did not arrive at the comb-replacement architecture in a straight line. The course corrections matter, and the archive preserves them for reference.

### v1 - phase 1 prototype (March 2026)

The first prototype was a small CfC module sitting outside the engine, talking to openc2e over CAOS. It demonstrated that a Python brain could shape Norn behaviour at all, which was the question that needed answering before any deeper integration. The prototype was retired once the architecture moved inside the engine.

### v2 - four-module CfC, March to early April 2026

The v2 architecture replaced the SVRule brain wholesale with four CfC and NCP modules (thalamus, hippocampus, amygdala, frontal), totalling 1,100 neurons. The intent was a complete brain transplant in which the SVRule layer was removed entirely.

Two structural problems emerged through training and live observation. The attention head and the decision head were both `nn.Linear` layers reading from the same frontal output, which left attention with no architectural reason to persist and decisions with no reason to sequence coherently. Reinforcement learning was attributing reward to whatever action happened on the same tick, which biochemistry timing made unreliable: the reward chemicals peak ten to twenty ticks after the causal action.

Eligibility-trace A2C with twenty-tick attribution and a value head fixed the credit assignment problem, and the gain was measurable in pre-training accuracy. The structural attention-versus-decision problem was harder to address because it sat in the architecture itself rather than in the training rule.

### Pivot 1 - April 3: SVRule layer 1, CfC layer 2

The first pivot kept the SVRule brain as a brainstem layer (perception, attention persistence, survival behaviours) and replaced only the SVRule decision lobe with a CfC module as a proof of concept. The reasoning was that SVRule already handles attention persistence well, which would allow the CfC to focus on emergent decision-making.

This pivot was incorrect. It was retired before any code shipped, due to a fact about the SVRule brain that visual inspection later made obvious.

### Pivot 2 - April 25: comb, not decn

A live SVRule brain inspection through the openc2e BrainViewer (Ctrl-left-click, Brain Viewer in the menu) surfaced a fact that both the v2 design and the first pivot had missed. The decn lobe is a thin argmax column with no learning behaviour of its own: it is plumbing. The comb (combination) lobe is the dense, fully connected layer with migrating dendrites, which is the only lobe in stock C3 that genuinely learns from experience.

Replacing decn with a CfC was therefore cosmetic, due to decn doing no learning to replace. Replacing comb substitutes the actual learning substrate while preserving every other piece of SVRule plumbing, which retains perception lobes, the reward pathway, attention persistence, and the decn argmax in their original form.

### Lock - April 26: contract verified breed-stable

The comb contract was verified through genome decoding of `norn.bondi.48.gen` and cross-checked against five sampled standard genomes (Bondi, Harlequin, Civet, Zebra, Banshee Grendel, and Final46 Ettin). All five produce an identical comb section: 440 neurons (40 columns by 11 rows), six input tracts, and two output tracts.

The locked contract is a 107-dimension input vector (driv 20 + stim 40 + verb 11 + forf 36), a 51-dimension output vector (attn 40 + decn 11), and a 440-dimension hidden state. The full contract is queryable via `python tools/kb_lookup.py contract`.

---

## Architecture at a glance

The CfC module sits inside the openc2e engine via pybind11 and replaces only the comb lobe. Every other lobe and pathway stays SVRule.

| Element | Source | Role |
|---|---|---|
| Perception lobes (driv, stim, verb, forf) | SVRule | Sense the environment, drive state, verbs, and forfeit signals |
| Comb lobe (440 neurons) | CfC, replaces SVRule | Strategic learning substrate; produces attention and decision outputs |
| attn lobe | SVRule | Attention persistence, sticky over roughly five to ten seconds |
| decn lobe (13 neurons) | SVRule | Argmax over the CfC-supplied decn outputs (neurons 0 to 10); verb wiring drives neurons 11 and 12 directly |
| Reward pathway | SVRule biochemistry | Chemicals 204 (reward) and 205 (punishment), which the bridge reads each tick and supplies as a scalar to the CfC weight-update step |
| Learning rule | A2C with eligibility trace | Twenty-tick window, gamma=0.95, entropy bonus 0.1 to 0.01 over 10K ticks linear |

The CfC learns through gradient descent on the reinforcer scalar, which functionally replaces genome-driven dendrite migration. The bridge keeps reward as a separate channel, and does not concatenate reward into the input vector.

---

## Repository layout

```
nornbrain/                Core Python package (signal_types, tract, ltm, telemetry)
kb/                       Self-contained knowledge base (kb.sqlite + genome decoder)
tools/                    Analysis and operator scripts (kb_lookup, decode_norn_genome,
                          analyse_brain_data, svrule_baseline_benchmark, control_panel,
                          test_harness, overnight_training, fetch_papers, ...)
tests/                    Tests
docs/
  reference/              Verified reference material:
                          caos-dictionary, svrule-brain-complete-reference,
                          verified-reference, wildlife,
                          and the 16-doc Brain in a Vat decompilation catalogue
  specs/                  Active design specifications (dated)
  plans/                  Active implementation plans (dated)
  logs/                   Project logs (KB acceptance, reconciliation, audits)
  manuals/                Operator-facing manuals
archive/
  legacy-v2/              Retired v2 architecture (code, docs, eval data); see README inside
```

---

## Knowledge base

The KB at `kb/kb.sqlite` (3.09 MB) holds the project's facts in a single queryable file. The `attr` table contains 6,219 denormalised key-value rows (such as `lobe.comb.neuron_count = 440`), the `reference_material` table carries the full body text of 32 ingested markdown reference docs, and an FTS5 index runs over that body text for prose search.

Quick lookups:

```bash
python tools/kb_lookup.py contract         # locked CfC comb contract
python tools/kb_lookup.py lobe comb        # one lobe with full attrs
python tools/kb_lookup.py tract driv comb  # tracts between two lobes
python tools/kb_lookup.py actions          # action to decn-neuron mapping
python tools/kb_lookup.py drives           # drive index to chemical mapping
python tools/kb_lookup.py opcode 35        # one SVRule opcode
python tools/kb_lookup.py chemical 204     # one chemical
python tools/kb_lookup.py search "comb"    # FTS5 prose search
python tools/kb_lookup.py decisions        # locked decisions and supersession
python tools/kb_lookup.py gotchas          # all gotchas
```

Decode any C3 genome:

```bash
python tools/decode_norn_genome.py path/to/your.gen
```

The shared parser lives at `kb/genome_decoder.py` and reads big-endian uint16 values per `Genome.h GetInt()`.

---

## Build and run

The openc2e fork builds with CMake. The brain module is loaded by passing its Python file path to `--brain-module`.

```bash
# Start openc2e with the default SVRule brain
openc2e.exe --data-path "<path-to-Creatures-3-data>" --gamename "Creatures 3"

# Inject CAOS via TCP (port 20001, terminate with rscr\n)
python -c "
import socket; s = socket.socket()
s.connect(('127.0.0.1', 20001))
s.sendall(b'outv totl 0 0 0\nrscr\n')
print(s.recv(4096).decode().strip()); s.close()
"
```

The Phase E.2 comb-replacement Python wrapper is pending implementation per the active design spec. Until then, the SVRule default invocation is what runs.

---

## Reading order

The recommended order for a first read of this repository:

1. This README
2. `docs/specs/2026-04-26-cfc-comb-replacement-design.md` (the active design)
3. `docs/reference/svrule-brain-complete-reference.md` (the SVRule layer that surrounds the CfC)
4. `docs/reference/braininavat/` (decompilation catalogue of the original Brain in a Vat tool)
5. `docs/reference/verified-reference.md` (cross-verified reference for lobes, biochemistry, and CAOS)
6. `archive/legacy-v2/README.md` (the retired v2 architecture, for context on how the comb-replacement design came about)

---

## Project conventions

The project favours many small files over few large files, which keeps cohesion high and coupling low; 200 to 400 lines per file is typical, and 800 lines is the hard ceiling. Immutability is preferred, which means new objects are built rather than existing ones mutated. Errors are handled explicitly at every level, and inputs are validated at system boundaries.

The repository root carries only the boilerplate already present (`README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, `requirements.txt`, `setup.sh`, `setup.ps1`); new top-level files are not added casually. New brain code goes under `nornbrain/`, engine wrappers go in the openc2e fork, new tests go under `tests/`, specs under `docs/specs/` (dated), and plans under `docs/plans/`. Retired code goes under `archive/`, and is never deleted.

---

## License

See `LICENSE`.
