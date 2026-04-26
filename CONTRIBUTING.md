# Contributing to NORNBRAIN

Thank you for your interest in contributing. The project is an active single-developer
research effort, and contributions that are scoped, documented, and tested are
most likely to land cleanly.

---

## Development setup

```bash
git clone https://github.com/thechimpmatrix/nornbrain.git
cd nornbrain

# Linux / macOS / Git Bash on Windows
./setup.sh

# Windows PowerShell
.\setup.ps1

# Activate the environment
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

# Verify the test suite passes
pytest tests/
```

The openc2e engine is not required for Python-only work. If your contribution
touches the engine integration layer (the Phase E.2 brain wrapper, pending
implementation per the active design spec, or `PythonBrain.cpp`), you will
also need to build the engine. See
`https://github.com/thechimpmatrix/openc2e-nb` for build instructions.

---

## Where to start

Read the [README](README.md) for project context, then the active design
spec at [docs/specs/2026-04-26-cfc-comb-replacement-design.md](docs/specs/2026-04-26-cfc-comb-replacement-design.md)
before starting any architectural work. The spec records the locked decisions
which are not up for re-litigation without strong evidence.

The project is in **Phase E.2**: CfC comb-replacement. The architecture
substitutes only the SVRule comb (combination) lobe with a CfC module, and
keeps every other piece of SVRule plumbing intact. Contributions which advance
the comb-replacement design and its bridge into the openc2e fork are the
highest priority.

---

## Branch and pull request workflow

1. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-description
   ```
2. Write tests before writing implementation code. The test suite lives in
   `tests/`. Coverage target is 80%.
3. Run the full test suite before submitting:
   ```bash
   pytest tests/
   ```
4. Open a pull request against `main`. Include in the PR description:
   - What the change does.
   - What it does not do (scope boundaries matter on a research project).
   - How you verified it (test output, benchmark results, or live observation).

Pull requests that add architecture-level changes without discussion are unlikely
to merge. Open an issue first so the approach can be agreed before implementation
begins.

---

## Code style

**Language.** All prose: commit messages, docstrings, comments, and
documentation: uses Australian English spelling: behaviour, organisation,
colour, optimise, analyse, centre, favour, recognise. No contractions. No
exclamation marks.

**Python.** Pythonic idioms. Small, focused functions (aim for under 50 lines).
Immutable data patterns where practical: return new objects rather than
mutating in place. Errors handled explicitly at every level; no silent
swallowing.

**Files.** Aim for under 400 lines per file. If a module is growing past 600
lines, consider whether it has more than one responsibility.

**Constants over magic numbers.** Any threshold, weight, or count that might
need tuning belongs in a named constant or configuration variable.

---

## Data and weights

The project observes a strict **P1 Law: never destroy data.** If your
contribution writes to `runtime/` or `eval/`, it must archive the prior
version with a timestamped filename before overwriting. Training runs should
call `python tools/analyse_brain_data.py` to generate an HTML report in
`eval/archive/` after completing.

Do not commit large weight files (`.pt`, `.onnx`) unless they are the canonical
working weights for `runtime/`. Training checkpoints belong in
`eval/weights/`, which is gitignored.

---

## Numerical claims

Any numerical claim in a commit message, docstring, or documentation (tensor
shapes, parameter counts, timing measurements) must be verified by running code,
not estimated from first principles. If a benchmark is relevant, include the
JSON output or link to the HTML report.

---

## Areas where outside expertise is most valuable

- **CfC decision-lobe architecture**: input/output specification, integration
  with SVRule dendrite dynamics, training loss design.
- **Continuous-control RL in noisy, low-sample regimes**: the A2C and 20-tick
  eligibility trace mechanism works in principle and has not had a clean
  uninterrupted live training run.
- **Agent evaluation design**: a sharper evaluation framework for the metrics
  (action diversity, drive homeostasis, hippocampal autocorrelation, novel
  behaviour count, threat-response latency) would improve every downstream
  decision.
- **C++ and pybind11 interface design**: the `openc2e/src/PythonBrain.cpp`
  boundary works and was not designed by a specialist.

---

## Reporting issues

Use the issue templates in `.github/ISSUE_TEMPLATE/`. For bugs, include:

- Your operating system and Python version.
- Whether you are running with the live engine or in unit-test-only mode.
- The full stack trace, if one is available.

For feature requests, describe the problem the feature solves and how you
would verify that it has been solved.

---

## On AI-assisted contributions

AI-assisted contributions are welcome. Numerical and architectural claims generated by AI assistance should be verified empirically before they appear in a pull request.
