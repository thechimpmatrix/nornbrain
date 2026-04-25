# Defensive CAOS Engineering: Principles & Patterns

**READ THIS** before writing any CAOS injection code, bridge logic, or shared-memory interaction.
These principles are distilled from industry research on defensive programming, chaos engineering,
design-by-contract, game modding patterns, and architectural decision records: adapted specifically
for CAOS/Python bridge work in NORNBRAIN.

Last updated: 2026-03-31

---

## Why This Exists

CAOS has no exception handling, no return codes, no try/catch. Commands that fail often do so
silently: leaving variables unchanged, skipping execution, or producing garbage values. The
Creatures 3 engine won't tell us when things are subtly wrong. Every defensive check must live
on the Python side of the boundary.

---

## The 7 Principles

### 1. Contract at the Boundary (Design by Contract)

Every CAOS interaction has explicit preconditions, postconditions, and invariants: checked in Python.

**Preconditions** (check BEFORE injecting CAOS):
- Target agent exists (ENUM first, don't assume)
- Creature is alive (`dead targ` returns 0)
- Shared memory is connected and responsive
- World is fully loaded (agent count > 100, not just `outv 1`)

**Postconditions** (check AFTER every CAOS read):
- Chemical values in range 0.0–1.0
- Lobe IDs are valid 4-char ASCII strings
- Neuron counts match expected lobe sizes
- Decision index is 0–13 (not 14–16 which exist but are unused)

**Invariants** (assert EVERY tick):
- Creature count > 0
- World still loaded
- Shared memory still mapped
- Heartbeat counter incremented

### 2. Sentinel Heartbeat (Silent Failure Detection)

CAOS commands that fail leave GAME variables unchanged. You cannot distinguish "unchanged value"
from "read failed silently" without sentinels.

**Write-before-read sentinel**: Before a CAOS read cycle, write a known impossible value (e.g., -999)
to a designated GAME variable. After the read script runs, verify it was overwritten. If still -999,
the script didn't execute.

**Heartbeat counter**: A monotonically incrementing counter in a GAME variable, written by the CAOS
agent every tick. Python checks it incremented. Stale heartbeat = CAOS agent stalled or killed.

**Range validation**: Chemical values outside 0.0–1.0, negative neuron counts, or lobe IDs with
non-printable characters = corruption or silent failure. Flag immediately, don't process.

### 3. Never Trust a CAOS Read

All values returned from CAOS are untrusted external input. Validate before use.

- Numeric values: check type, check range, check for sentinel values
- String values: check length, check charset, check for empty
- Agent references: verify agent still exists before second access
- GAME variables: compare against expected ranges per variable

This is not paranoia: it's the only defence against a runtime with no error reporting.

### 4. Single Gateway (All CAOS Through One Door)

No raw shared-memory writes scattered across the codebase. One gateway function handles:

- Connection check (is shared memory mapped?)
- Injection (send the CAOS string)
- Timeout (with configurable limit)
- Result validation (type check, range check)
- Logging (every injection logged for debugging)
- Retry with backoff (but with max retry count: silent retries mask problems)

All Python code calls the gateway. The gateway calls shared memory. Nothing bypasses the gateway.

### 5. Align With the Engine, Don't Fight It

From game modding research: "Treat the engine as a coherent system rather than a black box.
Obstacles are architectural signals, not arbitrary restrictions."

When a CAOS command fails unexpectedly:
1. **Investigate WHY** before writing a workaround
2. **Classify the cause**: timing (script didn't flush), missing feature (DS-only command),
   state (agent killed between ENUM and access), permission (locked agent)
3. **Document the engine's reason**, not just "don't do X" but "X fails because the engine's
   internal model works like Y"

Examples from our experience:
- SEEN rejected → not "broken command" but "removed in C3-standalone because classifier system changed; ENUM+CATI is the C3 primitive"
- activate1 destroys agents → not "bug" but "agents' activate1 scripts are destructive by design; never fire on unknown agents"
- INST blocks don't always flush → timing interaction with the script scheduler, not a random failure

### 6. Edge Case Registry (ADR-Style)

Every gotcha gets a structured entry. This is what cc-handbook.md Section 5 already does informally.
The formal structure:

```
### [SHORT NAME]
- **What happened**: Concrete description of the failure
- **Why it happened**: Engine cause (not just "it broke")
- **What we do instead**: The correct approach
- **Confidence**: verified-in-live-C3 | inferred-from-openc2e | community-wiki-unverified
- **Recheck trigger**: When to re-test this assumption (e.g., "if engine version changes")
- **Status**: active | superseded-by-[entry] | unverified
```

Never delete entries: mark as superseded with a pointer to the replacement.

### 7. Steady-State Health Definition (from Chaos Engineering)

Define what "healthy bridge" looks like quantitatively, then continuously verify it.

**Healthy bridge metrics**:
- Ticks per second within expected range (0.5–2.0 given CAOS bottleneck)
- Chemical read count matches expected count per tick
- Decision output changes at least once every N ticks (stuck brain = broken brain)
- Heartbeat counter increments every tick
- At least 3 drive chemicals are non-zero (creature is alive and has needs)

**Session health hypothesis**: "If the bridge is healthy, the heartbeat increments every tick,
chemical values are non-zero for at least 3 drives, and decision outputs vary over 30 seconds."

Encode these as computable health signals in the monitor, not just visual displays.

---

## When to Read This Document

- Before writing any new CAOS injection code
- Before modifying bridge tick logic or shared memory interaction
- Before adding new GAME variable reads/writes
- When debugging a "sometimes works, sometimes doesn't" issue (likely a silent failure)
- When a CAOS command behaves differently than documented (investigate, then add to edge case registry)

---

## Sources

This document synthesises research from:
- Design by Contract (Bertrand Meyer): preconditions, postconditions, invariants
- Chaos Engineering (principlesofchaos.org): steady-state verification, hypothesis-driven testing
- Defensive Programming (Enterprise Craftsmanship): boundary validation, gateway pattern
- Architectural Decision Records (Martin Fowler, AWS): structured decision capture
- Game Modding Patterns (Lua/Zomboid/Factorio communities): engine alignment, constraint-driven design
- Sentinel Value Patterns: silent failure detection via impossible marker values

All adapted for the specific constraints of CAOS: no error handling, no return codes, no try/catch,
silent failures as the default failure mode.
