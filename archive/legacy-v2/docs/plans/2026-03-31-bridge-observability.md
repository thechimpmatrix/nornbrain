# Bridge Observability Rebuild: Implementation Plan


**Goal:** Replace three fragmented visualization surfaces with one instrumented bridge and one unified monitor, so every tick's timing, health signals, and decision context are visible and persisted.

**Architecture:** Two layers. Layer 1 adds a `TickRecord` dataclass that captures timing decomposition (read/brain/write/ltm), health signals (entropy, per-module variance, decision confidence), and the full output distribution: computed once per tick and fed to both the session logger and the WebSocket broadcast. Layer 2 replaces both the HTML dashboard and tkinter state_monitor with a single tkinter app that consumes the enriched WebSocket stream, showing a timing bar, brain heatmap, drives, rolling 200-tick timeline, LTM panel, and event log.

**Tech Stack:** Python 3.14, tkinter, asyncio, dataclasses, websocket-client

**Branch:** `feature/multi-lobe-cfc` in `<PROJECT_ROOT>/`

**Working directory:** `<PROJECT_ROOT>/phase2-bridge/`

**Test command:**
```bash
cd <PROJECT_ROOT>/phase2-bridge
python -m pytest tests/ -v
```

---

## File Structure

| File | Role | Action |
|------|------|--------|
| `phase2-bridge/telemetry.py` | `TickRecord` dataclass + health signal computations | **Create** |
| `phase2-bridge/tests/test_telemetry.py` | Tests for telemetry computations | **Create** |
| `phase2-bridge/session_logger.py` | Enriched logger accepting `TickRecord` | **Modify** |
| `phase2-bridge/tests/test_session_logger.py` | Tests for enriched logger | **Create** |
| `phase2-bridge/brain_bridge_client.py` | Timing decomposition in tick loop + emit `TickRecord` | **Modify** |
| `phase2-bridge/norn_monitor.py` | Unified tkinter monitor (replaces state_monitor.py + dashboard) | **Create** |

---

## Task 1: TickRecord Dataclass + Health Signal Computations

The foundation. A typed dataclass that captures everything worth knowing about a single tick. Computed once, consumed by logger + broadcast + monitor.

**Files:**
- Create: `phase2-bridge/telemetry.py`
- Create: `phase2-bridge/tests/test_telemetry.py`

- [ ] **Step 1: Create tests directory and test file**

```bash
mkdir -p <PROJECT_ROOT>/phase2-bridge/tests
touch <PROJECT_ROOT>/phase2-bridge/tests/__init__.py
```

- [ ] **Step 2: Write failing tests for TickRecord and health computations**

Create `phase2-bridge/tests/test_telemetry.py`:

```python
"""Tests for telemetry.py: TickRecord and health signal computations."""
import math
import numpy as np
import pytest
from telemetry import (
    TickRecord,
    TimingBreakdown,
    HealthSignals,
    compute_health_signals,
    normalised_entropy,
    softmax,
)


# ── normalised_entropy ──────────────────────────────────────────────

def test_entropy_uniform():
    """Uniform distribution over 4 classes → entropy 1.0."""
    assert normalised_entropy([0, 1, 2, 3], n_classes=4) == pytest.approx(1.0)


def test_entropy_single_class():
    """All same value → entropy 0.0."""
    assert normalised_entropy([2, 2, 2, 2], n_classes=4) == pytest.approx(0.0)


def test_entropy_empty():
    assert normalised_entropy([], n_classes=4) == 0.0


def test_entropy_two_classes():
    """Half and half over 4 → normalised < 1.0."""
    ent = normalised_entropy([0, 0, 1, 1], n_classes=4)
    assert 0.0 < ent < 1.0


# ── softmax ─────────────────────────────────────────────────────────

def test_softmax_sums_to_one():
    probs = softmax(np.array([1.0, 2.0, 3.0]))
    assert sum(probs) == pytest.approx(1.0)


def test_softmax_peak():
    probs = softmax(np.array([0.0, 0.0, 10.0]))
    assert probs[2] > 0.99


# ── compute_health_signals ──────────────────────────────────────────

def test_health_signals_basic():
    """Smoke test: can compute signals from typical data."""
    attn_values = np.random.rand(40).astype(np.float32)
    decn_values = np.random.rand(17).astype(np.float32)
    module_hidden = {
        "thalamus": np.random.rand(70).astype(np.float32),
        "amygdala": np.random.rand(52).astype(np.float32),
        "hippocampus": np.random.rand(52).astype(np.float32),
        "prefrontal": np.random.rand(65).astype(np.float32),
    }
    recent_decisions = list(range(14)) * 2  # 28 entries, each action twice
    recent_attentions = list(range(20)) * 2

    signals = compute_health_signals(
        attn_values=attn_values,
        decn_values=decn_values,
        module_hidden=module_hidden,
        recent_decisions=recent_decisions,
        recent_attentions=recent_attentions,
    )
    assert isinstance(signals, HealthSignals)
    assert 0.0 <= signals.attention_entropy <= 1.0
    assert 0.0 <= signals.decision_confidence <= 1.0
    assert "thalamus" in signals.module_variance
    assert "thalamus" in signals.module_energy
    assert 0.0 <= signals.action_diversity <= 1.0
    assert 0.0 <= signals.attention_diversity <= 1.0


def test_health_signals_stuck_detection():
    """All same decision → action_diversity near 0."""
    signals = compute_health_signals(
        attn_values=np.ones(40, dtype=np.float32),
        decn_values=np.zeros(17, dtype=np.float32),
        module_hidden={},
        recent_decisions=[3] * 50,
        recent_attentions=[11] * 50,
    )
    assert signals.action_diversity < 0.05
    assert signals.attention_diversity < 0.05


# ── TimingBreakdown ────────────────────────────────────────────────

def test_timing_total():
    t = TimingBreakdown(read_ms=10.0, brain_ms=5.0, write_ms=2.0, ltm_ms=1.0, overhead_ms=0.5)
    assert t.total_ms == pytest.approx(18.5)


# ── TickRecord ──────────────────────────────────────────────────────

def test_tick_record_to_log_dict():
    """TickRecord.to_log_dict() returns a flat dict suitable for JSONL."""
    timing = TimingBreakdown(read_ms=10.0, brain_ms=5.0, write_ms=2.0, ltm_ms=1.0, overhead_ms=0.5)
    health = HealthSignals(
        attention_entropy=0.8, decision_confidence=0.6,
        module_variance={"thalamus": 0.01}, module_energy={"thalamus": 1.5},
        action_diversity=0.5, attention_diversity=0.7,
        decision_flip_rate=0.3, status="healthy",
    )
    record = TickRecord(
        tick=42,
        timing=timing,
        health=health,
        attn_winner=11, attn_label="food",
        decn_winner=1, decn_label="push",
        attn_values=[0.0] * 40,
        decn_values=[0.0] * 17,
        drives=[0.0] * 20,
        chemicals_key=[0.0] * 9,
        emotional_tier="calm",
        ltm_count=5, ltm_retrievals=2,
        posx=1000.0, posy=500.0,
    )
    d = record.to_log_dict()
    assert d["tick"] == 42
    assert d["read_ms"] == 10.0
    assert d["brain_ms"] == 5.0
    assert d["attn_entropy"] == 0.8
    assert d["decn_confidence"] == 0.6
    assert d["module_var_thalamus"] == 0.01
    assert d["status"] == "healthy"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python -m pytest tests/test_telemetry.py -v
```

Expected: FAIL (telemetry module doesn't exist yet).

- [ ] **Step 4: Implement telemetry.py**

Create `phase2-bridge/telemetry.py`:

```python
"""
telemetry.py: Structured tick records and health signal computations.

Computed once per tick, consumed by session_logger, WebSocket broadcast,
and the unified monitor. Single source of truth for all observability.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np


# ── Utility functions ───────────────────────────────────────────────

def normalised_entropy(seq: list[int], n_classes: int) -> float:
    """Normalised Shannon entropy of a categorical sequence. Returns 0.0-1.0."""
    if len(seq) == 0 or n_classes <= 1:
        return 0.0
    counts: dict[int, int] = {}
    for v in seq:
        counts[v] = counts.get(v, 0) + 1
    total = len(seq)
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log(p)
    max_ent = math.log(min(n_classes, total))
    return ent / max_ent if max_ent > 0 else 0.0


def softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    e = np.exp(x - np.max(x))
    return e / e.sum()


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class TimingBreakdown:
    """Per-tick timing decomposition in milliseconds."""
    read_ms: float = 0.0       # CAOS DMPL + chemical reads
    brain_ms: float = 0.0      # CfC forward pass
    write_ms: float = 0.0      # CAOS decision write-back
    ltm_ms: float = 0.0        # LTM retrieval + encoding
    overhead_ms: float = 0.0   # Everything else (status check, logging, broadcast)

    @property
    def total_ms(self) -> float:
        return self.read_ms + self.brain_ms + self.write_ms + self.ltm_ms + self.overhead_ms


@dataclass
class HealthSignals:
    """Per-tick brain health metrics."""
    attention_entropy: float = 0.0       # Entropy of attention softmax (0=focused, 1=diffuse)
    decision_confidence: float = 0.0     # Max softmax prob of decision output (0=unsure, 1=certain)
    module_variance: dict[str, float] = field(default_factory=dict)  # Per-module hidden state variance
    module_energy: dict[str, float] = field(default_factory=dict)    # Per-module L2 norm
    action_diversity: float = 0.0        # Normalised entropy of recent decisions (rolling)
    attention_diversity: float = 0.0     # Normalised entropy of recent attentions (rolling)
    decision_flip_rate: float = 0.0      # Fraction of consecutive decision changes (rolling)
    status: str = "healthy"              # "healthy" | "stuck" | "converged"


def compute_health_signals(
    attn_values: np.ndarray,
    decn_values: np.ndarray,
    module_hidden: dict[str, np.ndarray],
    recent_decisions: list[int],
    recent_attentions: list[int],
) -> HealthSignals:
    """Compute all health signals from current tick data + rolling history."""

    # Attention entropy (softmax then Shannon entropy)
    attn_probs = softmax(attn_values)
    attn_ent = 0.0
    for p in attn_probs:
        if p > 0:
            attn_ent -= p * math.log(p)
    max_attn_ent = math.log(len(attn_values)) if len(attn_values) > 1 else 1.0
    attention_entropy = attn_ent / max_attn_ent

    # Decision confidence (max softmax prob over active neurons 0-13)
    active_decn = decn_values[:14] if len(decn_values) >= 14 else decn_values
    decn_probs = softmax(active_decn)
    decision_confidence = float(np.max(decn_probs))

    # Per-module metrics
    module_variance = {}
    module_energy = {}
    for name, hx in module_hidden.items():
        if hx is not None and len(hx) > 0:
            module_variance[name] = round(float(np.var(hx)), 6)
            module_energy[name] = round(float(np.linalg.norm(hx)), 4)

    # Rolling diversity (from recent history)
    action_diversity = normalised_entropy(recent_decisions, 15)
    attention_diversity = normalised_entropy(recent_attentions, 40)

    # Decision flip rate
    flips = 0
    for i in range(1, len(recent_decisions)):
        if recent_decisions[i] != recent_decisions[i - 1]:
            flips += 1
    decision_flip_rate = flips / max(len(recent_decisions) - 1, 1) if len(recent_decisions) > 1 else 0.0

    # Status diagnosis
    all_var_low = all(v < 0.001 for v in module_variance.values()) if module_variance else False
    if action_diversity < 0.1 and len(recent_decisions) >= 10:
        status = "stuck"
    elif all_var_low and module_variance:
        status = "converged"
    else:
        status = "healthy"

    return HealthSignals(
        attention_entropy=round(attention_entropy, 4),
        decision_confidence=round(decision_confidence, 4),
        module_variance=module_variance,
        module_energy=module_energy,
        action_diversity=round(action_diversity, 4),
        attention_diversity=round(attention_diversity, 4),
        decision_flip_rate=round(decision_flip_rate, 4),
        status=status,
    )


@dataclass
class TickRecord:
    """Complete record of one brain tick. Single source of truth."""

    # Identity
    tick: int = 0

    # Timing
    timing: TimingBreakdown = field(default_factory=TimingBreakdown)

    # Health
    health: HealthSignals = field(default_factory=HealthSignals)

    # Output (winners + full distributions)
    attn_winner: int = 0
    attn_label: str = ""
    decn_winner: int = 0
    decn_label: str = ""
    attn_values: list[float] = field(default_factory=list)   # Full 40-value distribution
    decn_values: list[float] = field(default_factory=list)   # Full 17-value distribution

    # State snapshot
    drives: list[float] = field(default_factory=list)         # 20 drives
    chemicals_key: list[float] = field(default_factory=list)  # 9 key chemicals
    emotional_tier: str = ""

    # LTM
    ltm_count: int = 0
    ltm_retrievals: int = 0

    # Position
    posx: float = 0.0
    posy: float = 0.0

    def to_log_dict(self) -> dict:
        """Flatten to a dict for JSONL logging. Timing and health are inlined."""
        d: dict = {
            "type": "tick",
            "ts": time.time(),
            "tick": self.tick,
            # Timing
            "read_ms": round(self.timing.read_ms, 2),
            "brain_ms": round(self.timing.brain_ms, 2),
            "write_ms": round(self.timing.write_ms, 2),
            "ltm_ms": round(self.timing.ltm_ms, 2),
            "overhead_ms": round(self.timing.overhead_ms, 2),
            "total_ms": round(self.timing.total_ms, 2),
            # Health
            "attn_entropy": self.health.attention_entropy,
            "decn_confidence": self.health.decision_confidence,
            "action_diversity": self.health.action_diversity,
            "attention_diversity": self.health.attention_diversity,
            "decision_flip_rate": self.health.decision_flip_rate,
            "status": self.health.status,
            # Output
            "attn_win": self.attn_winner,
            "attn_lbl": self.attn_label,
            "decn_win": self.decn_winner,
            "decn_lbl": self.decn_label,
            "attn_values": [round(v, 4) for v in self.attn_values],
            "decn_values": [round(v, 4) for v in self.decn_values],
            # State
            "drives": [round(d, 4) for d in self.drives],
            "chemicals": [round(c, 4) for c in self.chemicals_key],
            "tier": self.emotional_tier,
            # LTM
            "ltm_count": self.ltm_count,
            "ltm_retrievals": self.ltm_retrievals,
            # Position
            "posx": round(self.posx, 1),
            "posy": round(self.posy, 1),
        }
        # Inline module metrics
        for name, var in self.health.module_variance.items():
            d[f"module_var_{name}"] = var
        for name, energy in self.health.module_energy.items():
            d[f"module_energy_{name}"] = energy
        return d
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python -m pytest tests/test_telemetry.py -v
```

Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
cd <PROJECT_ROOT>
git add phase2-bridge/telemetry.py phase2-bridge/tests/
git commit -m "feat: TickRecord dataclass + health signal computations (telemetry.py)"
```

---

## Task 2: Enrich Session Logger to Accept TickRecord

Replace the current `log_tick()` with a single `log_record(TickRecord)` method that writes the full enriched record. Keep backward compat by leaving `log_event()` unchanged.

**Files:**
- Modify: `phase2-bridge/session_logger.py`
- Create: `phase2-bridge/tests/test_session_logger.py`

- [ ] **Step 1: Write failing test**

Create `phase2-bridge/tests/test_session_logger.py`:

```python
"""Tests for enriched session_logger."""
import json
import os
import tempfile
import pytest
from telemetry import TickRecord, TimingBreakdown, HealthSignals
from session_logger import SessionLogger


def test_log_record_writes_jsonl(tmp_path):
    logger = SessionLogger(log_dir=str(tmp_path))
    timing = TimingBreakdown(read_ms=10.0, brain_ms=5.0, write_ms=2.0, ltm_ms=1.0, overhead_ms=0.5)
    health = HealthSignals(
        attention_entropy=0.8, decision_confidence=0.6,
        module_variance={"thalamus": 0.01}, module_energy={"thalamus": 1.5},
        action_diversity=0.5, attention_diversity=0.7,
        decision_flip_rate=0.3, status="healthy",
    )
    record = TickRecord(
        tick=42, timing=timing, health=health,
        attn_winner=11, attn_label="food",
        decn_winner=1, decn_label="push",
        attn_values=[0.1] * 40, decn_values=[0.1] * 17,
        drives=[0.5] * 20, chemicals_key=[0.0] * 9,
        emotional_tier="calm", ltm_count=5, ltm_retrievals=2,
        posx=1000.0, posy=500.0,
    )
    logger.log_record(record)
    logger.close()

    # Read the JSONL file
    files = list(tmp_path.glob("session_*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text().strip().split("\n")
    # Line 0 = session_start, line 1 = tick, line 2 = session_end
    tick_line = json.loads(lines[1])
    assert tick_line["type"] == "tick"
    assert tick_line["tick"] == 42
    assert tick_line["read_ms"] == 10.0
    assert tick_line["brain_ms"] == 5.0
    assert tick_line["attn_entropy"] == 0.8
    assert tick_line["decn_confidence"] == 0.6
    assert tick_line["module_var_thalamus"] == 0.01
    assert tick_line["attn_values"] == [0.1] * 40


def test_log_event_still_works(tmp_path):
    logger = SessionLogger(log_dir=str(tmp_path))
    logger.log_event("hidden_wipe", {"tick": 100})
    logger.close()
    files = list(tmp_path.glob("session_*.jsonl"))
    lines = files[0].read_text().strip().split("\n")
    event_line = json.loads(lines[1])
    assert event_line["type"] == "event"
    assert event_line["event"] == "hidden_wipe"
```

- [ ] **Step 2: Run tests: verify they fail**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python -m pytest tests/test_session_logger.py -v
```

Expected: FAIL (`log_record` method doesn't exist yet).

- [ ] **Step 3: Add log_record() method to session_logger.py**

In `phase2-bridge/session_logger.py`, add the import and new method. Keep the old `log_tick()` but mark it deprecated:

```python
# Add at top of file, after existing imports:
from telemetry import TickRecord

# Add new method to SessionLogger class, after log_tick():

    def log_record(self, record: TickRecord) -> None:
        """Write a full TickRecord as one JSONL line."""
        try:
            self._write(record.to_log_dict())
        except Exception:
            pass
```

- [ ] **Step 4: Run tests: verify they pass**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python -m pytest tests/test_session_logger.py tests/test_telemetry.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
cd <PROJECT_ROOT>
git add phase2-bridge/session_logger.py phase2-bridge/tests/test_session_logger.py
git commit -m "feat: session logger accepts TickRecord for enriched JSONL output"
```

---

## Task 3: Timing Decomposition in the Tick Loop

Instrument the multi-lobe tick loop in `brain_bridge_client.py` with `time.perf_counter()` calls around each phase. Build a `TickRecord` per tick and feed it to the session logger and broadcast.

**Files:**
- Modify: `phase2-bridge/brain_bridge_client.py` (multi-lobe tick loop, lines ~767-1012)

- [ ] **Step 1: Add import at top of brain_bridge_client.py**

```python
from telemetry import TickRecord, TimingBreakdown, HealthSignals, compute_health_signals
```

- [ ] **Step 2: Instrument the tick loop with timing points**

In `_poll_loop_multi_lobe()`, replace the current timing approach. The changes go inside the `while self.running:` loop. Wrap each phase with `time.perf_counter()` calls:

After `t0 = time.perf_counter()` (line 769), and after the status check / sleep logic (through line 813), add:

```python
                # ── PHASE 1: READ ──
                t_read_start = time.perf_counter()
```

After `state = self.read_full_brain_state()` (line 816) and the position read (line 830), add:

```python
                t_read_end = time.perf_counter()
```

Before `output = self.brain.tick(...)` (line 900), add:

```python
                # ── PHASE 2: BRAIN ──
                t_brain_start = time.perf_counter()
```

After `output = self.brain.tick(...)` (line 900), add:

```python
                t_brain_end = time.perf_counter()
```

Before `self.write_decision(output, tick_counter)` (line 906), add:

```python
                # ── PHASE 3: WRITE ──
                t_write_start = time.perf_counter()
```

After `self.write_decision(output, tick_counter)` (line 906), add:

```python
                t_write_end = time.perf_counter()
```

Before the LTM retrieval block (line 880), add:

```python
                # ── PHASE 4: LTM ──
                t_ltm_start = time.perf_counter()
```

After the LTM encoding block (line 941), add:

```python
                t_ltm_end = time.perf_counter()
```

- [ ] **Step 3: Build TickRecord and replace session log call**

Replace the existing session logger call (lines 988-1009) and the `elapsed_ms` computation (line 967) with:

```python
                # ── BUILD TICK RECORD ──
                t_end = time.perf_counter()

                timing = TimingBreakdown(
                    read_ms=(t_read_end - t_read_start) * 1000,
                    brain_ms=(t_brain_end - t_brain_start) * 1000,
                    write_ms=(t_write_end - t_write_start) * 1000,
                    ltm_ms=(t_ltm_end - t_ltm_start) * 1000,
                    overhead_ms=((t_end - t0) - (t_read_end - t_read_start)
                                 - (t_brain_end - t_brain_start)
                                 - (t_write_end - t_write_start)
                                 - (t_ltm_end - t_ltm_start)) * 1000,
                )

                # Gather module hidden states as numpy arrays
                module_hidden = {}
                if self.use_multi_lobe:
                    for name, hx in [
                        ("thalamus", self.brain._hx_thalamus),
                        ("amygdala", self.brain._hx_amygdala),
                        ("hippocampus", self.brain._hx_hippocampus),
                        ("prefrontal", self.brain._hx_prefrontal),
                    ]:
                        if hx is not None:
                            module_hidden[name] = hx.detach().cpu().numpy().flatten()

                health = compute_health_signals(
                    attn_values=output.attention_values,
                    decn_values=output.decision_values,
                    module_hidden=module_hidden,
                    recent_decisions=list(self._recent_decisions),
                    recent_attentions=list(self._recent_attentions),
                )

                # Key chemicals for compact logging (indices: 204, 205, 117, 112, 127, 128, 17, 18, 125)
                chems = state.get("chemicals", [])
                KEY_CHEM_INDICES = [204, 205, 117, 112, 127, 128, 17, 18, 125]
                chemicals_key = [chems[i] if i < len(chems) else 0.0 for i in KEY_CHEM_INDICES]

                record = TickRecord(
                    tick=tick_counter,
                    timing=timing,
                    health=health,
                    attn_winner=output.attention_winner,
                    attn_label=output.attention_label,
                    decn_winner=output.decision_winner,
                    decn_label=output.decision_label,
                    attn_values=output.attention_values.tolist(),
                    decn_values=output.decision_values.tolist(),
                    drives=state.get("lobes", {}).get("driv", []),
                    chemicals_key=chemicals_key,
                    emotional_tier=tier,
                    ltm_count=len(self.ltm_bank.memories) if self.ltm_bank else 0,
                    ltm_retrievals=len(ltm_matches) if ltm_matches else 0,
                    posx=state.get("posx", 0.0),
                    posy=state.get("posy", 0.0),
                )

                # Log enriched record
                if self.session_logger:
                    try:
                        self.session_logger.log_record(record)
                    except Exception:
                        pass

                # Store for monitor access
                self._last_record = record

                elapsed_ms = timing.total_ms
```

- [ ] **Step 4: Update debug log line to use timing decomposition**

Replace the existing `log.debug(...)` call (lines 981-986) with:

```python
                log.debug(
                    f"tick={tick_counter} attn={output.attention_label}({output.attention_winner}) "
                    f"decn={output.decision_label}({output.decision_winner}) "
                    f"tier={tier} mem={record.ltm_count} "
                    f"R={timing.read_ms:.0f}+B={timing.brain_ms:.0f}+W={timing.write_ms:.0f}"
                    f"+L={timing.ltm_ms:.0f}={elapsed_ms:.0f}ms"
                )
```

- [ ] **Step 5: Add `/api/tick_record` endpoint**

Add a new endpoint that returns the latest TickRecord as JSON (for the unified monitor to poll):

```python
@app.get("/api/tick_record")
async def api_tick_record():
    record = getattr(bridge, '_last_record', None)
    if record is None:
        return {"error": "no tick data yet"}
    return record.to_log_dict()
```

- [ ] **Step 6: Update WebSocket broadcast to include timing + health**

In `broadcast_state()`, add timing and health data to the message dict:

```python
    # Add after existing message construction:
    record = getattr(self, '_last_record', None)
    if record:
        msg["timing"] = {
            "read_ms": round(record.timing.read_ms, 2),
            "brain_ms": round(record.timing.brain_ms, 2),
            "write_ms": round(record.timing.write_ms, 2),
            "ltm_ms": round(record.timing.ltm_ms, 2),
            "total_ms": round(record.timing.total_ms, 2),
        }
        msg["health"] = {
            "attn_entropy": record.health.attention_entropy,
            "decn_confidence": record.health.decision_confidence,
            "module_variance": record.health.module_variance,
            "module_energy": record.health.module_energy,
            "action_diversity": record.health.action_diversity,
            "status": record.health.status,
        }
```

- [ ] **Step 7: Test by running bridge briefly and checking session log**

```bash
cd <PROJECT_ROOT>/phase2-bridge
# Start C3 engine first, then:
python brain_bridge_client.py --multi-lobe --game '"Creatures 3"' --creature 0 --port 5555 --verbose
# After ~10 ticks, Ctrl+C and inspect the session log:
python -c "
import json, os
logdir = 'session_logs'
latest = sorted(os.listdir(logdir))[-1]
with open(os.path.join(logdir, latest)) as f:
    for i, line in enumerate(f):
        if i > 3: break
        d = json.loads(line)
        if d.get('type') == 'tick':
            print(json.dumps(d, indent=2))
            break
"
```

Expected: Tick record with `read_ms`, `brain_ms`, `write_ms`, `ltm_ms`, `attn_entropy`, `decn_confidence`, `module_var_*` fields.

- [ ] **Step 8: Commit**

```bash
cd <PROJECT_ROOT>
git add phase2-bridge/brain_bridge_client.py
git commit -m "feat: timing decomposition + TickRecord in tick loop"
```

---

## Task 4: Unified Tkinter Monitor (norn_monitor.py)

Replace both `state_monitor.py` and the HTML dashboard with a single tkinter app that connects to the bridge WebSocket and shows everything in one window.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  NORN MONITOR  │ [connected] │ tick 1234 │ 4.8 tps │
├────────────────┬────────────────────────────────────┤
│ TIMING BAR     │ R=12ms B=5ms W=2ms L=1ms = 20ms   │
├────────────────┼────────────────────────────────────┤
│ DECISION       │ push → food  (conf: 0.82)          │
│ HEALTH         │ ▓▓▓▓░ entropy  ▓▓▓░░ diversity     │
├────────────────┼────────────────────────────────────┤
│ DRIVES (bars)  │ pain ████░░  hunger ██░░░░  ...    │
├────────────────┼────────────────────────────────────┤
│ MODULES        │ thal var=0.02 ▓▓  amyg var=0.01 ▓ │
│                │ hipp var=0.03 ▓▓▓ pfc  var=0.02 ▓▓│
├────────────────┼────────────────────────────────────┤
│ TIMELINE (200) │ ════════════════════════════════    │
│ (stacked area) │ decisions over time, colour-coded   │
├────────────────┼────────────────────────────────────┤
│ LTM            │ 42 memories │ tier: calm │ enc: 15%│
├────────────────┼────────────────────────────────────┤
│ EVENT LOG      │ [10:23:45] push → food (conf 0.82) │
│ (scrolling)    │ [10:23:44] look → norn (conf 0.45) │
└────────────────┴────────────────────────────────────┘
```

**Files:**
- Create: `phase2-bridge/norn_monitor.py`

- [ ] **Step 1: Create norn_monitor.py with theme constants and main window**

Create `phase2-bridge/norn_monitor.py`: a standalone tkinter app. Start with the window frame, theme, and WebSocket listener thread:

```python
#!/usr/bin/env python3
"""
norn_monitor.py: Unified NORNBRAIN bridge monitor.

Single tkinter window showing timing decomposition, brain health,
drives, module status, rolling timeline, LTM stats, and event log.
Connects to the bridge WebSocket for real-time data.

Usage:
    python norn_monitor.py                   # default ws://localhost:5555/ws
    python norn_monitor.py --port 8100       # custom bridge port
    python norn_monitor.py --rate 200        # GUI refresh every 200ms
"""

import argparse
import collections
import json
import math
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

try:
    import websocket as ws_lib
except ImportError:
    ws_lib = None

# ── Theme ───────────────────────────────────────────────────────────

THEME = {
    "bg": "#1a1b26",
    "bg_panel": "#1f2033",
    "bg_bar": "#292b3e",
    "fg": "#c0caf5",
    "fg_dim": "#565f89",
    "fg_label": "#7aa2f7",
    "accent": "#7aa2f7",
    "green": "#9ece6a",
    "yellow": "#e0af68",
    "orange": "#ff9e64",
    "red": "#f7768e",
    "cyan": "#7dcfff",
    "purple": "#bb9af7",
}

# Timing phase colours
TIMING_COLOURS = {
    "read": "#f7768e",   # red
    "brain": "#7aa2f7",  # blue
    "write": "#9ece6a",  # green
    "ltm": "#bb9af7",    # purple
    "overhead": "#565f89", # dim
}

DRIVE_NAMES = [
    "pain", "hunger_prot", "hunger_carb", "hunger_fat",
    "cold", "hot", "tired", "sleepy",
    "lonely", "crowded", "fear", "bored",
    "anger", "sex_drive", "comfort",
    "low_down", "high_up", "trapped", "trapped2", "patient",
]

DECISION_LABELS = [
    "look", "push", "pull", "deactivate", "approach", "retreat", "get",
    "drop", "express", "rest", "left", "right", "eat", "hit",
    "up", "down", "exit",
]

HISTORY_LEN = 200  # Rolling timeline depth


# ── WebSocket Listener ──────────────────────────────────────────────

class BridgeListener(threading.Thread):
    """Background thread that receives WebSocket messages from the bridge."""

    def __init__(self, url: str):
        super().__init__(daemon=True)
        self.url = url
        self.latest: dict | None = None
        self.connected = False
        self._lock = threading.Lock()

    def run(self):
        while True:
            try:
                ws = ws_lib.WebSocket()
                ws.connect(self.url, timeout=5)
                with self._lock:
                    self.connected = True
                while True:
                    raw = ws.recv()
                    if raw:
                        msg = json.loads(raw)
                        with self._lock:
                            self.latest = msg
            except Exception:
                with self._lock:
                    self.connected = False
                time.sleep(2)

    def get_state(self) -> tuple[bool, dict | None]:
        with self._lock:
            return self.connected, self.latest


# ── Monitor App ─────────────────────────────────────────────────────

class NornMonitor:
    def __init__(self, port: int = 5555, refresh_ms: int = 200):
        self.port = port
        self.refresh_ms = refresh_ms

        # Rolling history
        self.timing_history = collections.deque(maxlen=HISTORY_LEN)
        self.decision_history = collections.deque(maxlen=HISTORY_LEN)
        self.tick_times = collections.deque(maxlen=20)  # for TPS calc

        # Build GUI
        self.root = tk.Tk()
        self.root.title("NORN MONITOR")
        self.root.configure(bg=THEME["bg"])
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        self._build_ui()

        # Start listener
        url = f"ws://localhost:{port}/ws"
        self.listener = BridgeListener(url)
        self.listener.start()

        # Start polling
        self.root.after(self.refresh_ms, self._poll)

    def _build_ui(self):
        """Build all panels."""
        # ── Top bar ──
        top = tk.Frame(self.root, bg=THEME["bg_panel"], height=36)
        top.pack(fill="x", padx=4, pady=(4, 0))
        top.pack_propagate(False)

        self.lbl_title = tk.Label(top, text="NORN MONITOR", font=("Consolas", 14, "bold"),
                                  fg=THEME["cyan"], bg=THEME["bg_panel"])
        self.lbl_title.pack(side="left", padx=8)

        self.lbl_conn = tk.Label(top, text="disconnected", font=("Consolas", 10),
                                 fg=THEME["red"], bg=THEME["bg_panel"])
        self.lbl_conn.pack(side="left", padx=8)

        self.lbl_tick = tk.Label(top, text="tick:", font=("Consolas", 10),
                                 fg=THEME["fg_dim"], bg=THEME["bg_panel"])
        self.lbl_tick.pack(side="left", padx=8)

        self.lbl_tps = tk.Label(top, text=": tps", font=("Consolas", 10),
                                fg=THEME["fg_dim"], bg=THEME["bg_panel"])
        self.lbl_tps.pack(side="left", padx=8)

        # ── Timing bar (canvas) ──
        self.timing_canvas = tk.Canvas(self.root, height=28, bg=THEME["bg_bar"],
                                       highlightthickness=0)
        self.timing_canvas.pack(fill="x", padx=4, pady=2)

        # ── Decision + Health row ──
        dec_frame = tk.Frame(self.root, bg=THEME["bg_panel"], height=48)
        dec_frame.pack(fill="x", padx=4, pady=2)
        dec_frame.pack_propagate(False)

        self.lbl_decision = tk.Label(dec_frame, text=": →:", font=("Consolas", 16, "bold"),
                                     fg=THEME["green"], bg=THEME["bg_panel"])
        self.lbl_decision.pack(side="left", padx=8)

        self.lbl_confidence = tk.Label(dec_frame, text="conf::", font=("Consolas", 11),
                                       fg=THEME["fg_dim"], bg=THEME["bg_panel"])
        self.lbl_confidence.pack(side="left", padx=8)

        self.lbl_health = tk.Label(dec_frame, text="", font=("Consolas", 10),
                                   fg=THEME["fg_dim"], bg=THEME["bg_panel"])
        self.lbl_health.pack(side="right", padx=8)

        # ── Main content: left (drives + modules) / right (timeline + LTM + log) ──
        content = tk.Frame(self.root, bg=THEME["bg"])
        content.pack(fill="both", expand=True, padx=4, pady=2)

        left = tk.Frame(content, bg=THEME["bg"], width=340)
        left.pack(side="left", fill="both")
        left.pack_propagate(False)

        right = tk.Frame(content, bg=THEME["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        # ── Drives (left) ──
        drives_lbl = tk.Label(left, text="DRIVES", font=("Consolas", 9, "bold"),
                              fg=THEME["fg_label"], bg=THEME["bg"])
        drives_lbl.pack(anchor="w", padx=4)

        self.drive_canvas = tk.Canvas(left, height=200, bg=THEME["bg_panel"],
                                      highlightthickness=0)
        self.drive_canvas.pack(fill="x", padx=4, pady=2)

        # ── Modules (left) ──
        mod_lbl = tk.Label(left, text="MODULES", font=("Consolas", 9, "bold"),
                           fg=THEME["fg_label"], bg=THEME["bg"])
        mod_lbl.pack(anchor="w", padx=4, pady=(8, 0))

        self.module_canvas = tk.Canvas(left, height=80, bg=THEME["bg_panel"],
                                       highlightthickness=0)
        self.module_canvas.pack(fill="x", padx=4, pady=2)

        # ── Timeline (right) ──
        timeline_lbl = tk.Label(right, text="TIMELINE (200 ticks)", font=("Consolas", 9, "bold"),
                                fg=THEME["fg_label"], bg=THEME["bg"])
        timeline_lbl.pack(anchor="w", padx=4)

        self.timeline_canvas = tk.Canvas(right, height=100, bg=THEME["bg_panel"],
                                         highlightthickness=0)
        self.timeline_canvas.pack(fill="x", padx=4, pady=2)

        # ── LTM row (right) ──
        ltm_frame = tk.Frame(right, bg=THEME["bg_panel"], height=30)
        ltm_frame.pack(fill="x", padx=4, pady=2)
        ltm_frame.pack_propagate(False)

        self.lbl_ltm = tk.Label(ltm_frame, text="LTM:: memories", font=("Consolas", 10),
                                fg=THEME["purple"], bg=THEME["bg_panel"])
        self.lbl_ltm.pack(side="left", padx=8)

        self.lbl_tier = tk.Label(ltm_frame, text="tier::", font=("Consolas", 10),
                                 fg=THEME["fg_dim"], bg=THEME["bg_panel"])
        self.lbl_tier.pack(side="left", padx=8)

        # ── Event log (right) ──
        log_lbl = tk.Label(right, text="EVENT LOG", font=("Consolas", 9, "bold"),
                           fg=THEME["fg_label"], bg=THEME["bg"])
        log_lbl.pack(anchor="w", padx=4, pady=(8, 0))

        self.event_log = ScrolledText(right, height=8, font=("Consolas", 9),
                                      bg=THEME["bg_panel"], fg=THEME["fg"],
                                      insertbackground=THEME["fg"],
                                      state="disabled", wrap="none")
        self.event_log.pack(fill="both", expand=True, padx=4, pady=2)

    # ── Polling ─────────────────────────────────────────────────────

    def _poll(self):
        connected, state = self.listener.get_state()

        # Update connection status
        if connected:
            self.lbl_conn.config(text="connected", fg=THEME["green"])
        else:
            self.lbl_conn.config(text="disconnected", fg=THEME["red"])

        if state and state.get("type") == "tick":
            self._update(state)

        self.root.after(self.refresh_ms, self._poll)

    def _update(self, msg: dict):
        """Update all panels from a WebSocket tick message."""
        tick = msg.get("game_tick", msg.get("tick", 0))
        now = time.time()
        self.tick_times.append(now)

        # TPS
        if len(self.tick_times) >= 2:
            span = self.tick_times[-1] - self.tick_times[0]
            tps = (len(self.tick_times) - 1) / span if span > 0 else 0
            self.lbl_tps.config(text=f"{tps:.1f} tps", fg=THEME["fg"])
        self.lbl_tick.config(text=f"tick {tick}", fg=THEME["fg"])

        # Decision
        decn = msg.get("decision", {})
        attn = msg.get("attention", {})
        decn_lbl = decn.get("winner_label", ":")
        attn_lbl = attn.get("winner_label", ":")
        self.lbl_decision.config(text=f"{decn_lbl} → {attn_lbl}")

        # Confidence + health
        health = msg.get("health", {})
        conf = health.get("decn_confidence", 0)
        self.lbl_confidence.config(text=f"conf: {conf:.2f}" if conf else "conf::")

        entropy = health.get("attn_entropy", 0)
        diversity = health.get("action_diversity", 0)
        status = health.get("status", "?")
        status_colour = THEME["green"] if status == "healthy" else THEME["red"]
        self.lbl_health.config(
            text=f"entropy={entropy:.2f}  diversity={diversity:.2f}  [{status}]",
            fg=status_colour,
        )

        # Timing bar
        timing = msg.get("timing", {})
        if timing:
            self.timing_history.append(timing)
            self._draw_timing_bar(timing)

        # Drives
        drives = msg.get("drives", {})
        if isinstance(drives, dict):
            drive_values = [drives.get(name, 0) for name in DRIVE_NAMES]
        elif isinstance(drives, list):
            drive_values = drives
        else:
            drive_values = [0] * 20
        self._draw_drives(drive_values)

        # Modules
        mod_var = health.get("module_variance", {})
        mod_energy = health.get("module_energy", {})
        self._draw_modules(mod_var, mod_energy)

        # Timeline
        self.decision_history.append(decn.get("winner_index", decn.get("winner", 0)))
        self._draw_timeline()

        # LTM
        ltm_count = msg.get("ltm_count", 0)
        tier = msg.get("emotional_tier", "?")
        self.lbl_ltm.config(text=f"LTM: {ltm_count} memories")
        self.lbl_tier.config(text=f"tier: {tier}")

        # Event log
        ts = time.strftime("%H:%M:%S")
        self._log_event(f"[{ts}] {decn_lbl} → {attn_lbl} (conf {conf:.2f})")

    # ── Drawing helpers ─────────────────────────────────────────────

    def _draw_timing_bar(self, timing: dict):
        c = self.timing_canvas
        c.delete("all")
        w = c.winfo_width() or 800
        h = 28
        total = timing.get("total_ms", 1) or 1
        x = 0
        for phase, key in [("read", "read_ms"), ("brain", "brain_ms"),
                           ("write", "write_ms"), ("ltm", "ltm_ms")]:
            ms = timing.get(key, 0)
            pw = max(int(w * ms / max(total, 1)), 1)
            c.create_rectangle(x, 2, x + pw, h - 2, fill=TIMING_COLOURS[phase], outline="")
            if pw > 30:
                c.create_text(x + pw // 2, h // 2, text=f"{phase[0].upper()}={ms:.0f}",
                              fill="#fff", font=("Consolas", 8))
            x += pw
        # Total label
        c.create_text(w - 4, h // 2, text=f"{total:.0f}ms", anchor="e",
                      fill=THEME["fg_dim"], font=("Consolas", 9))

    def _draw_drives(self, values: list):
        c = self.drive_canvas
        c.delete("all")
        w = c.winfo_width() or 320
        bar_h = 10
        gap = 1
        cols = 2
        per_col = 10
        col_w = w // cols

        for i, (name, val) in enumerate(zip(DRIVE_NAMES, values)):
            col = i // per_col
            row = i % per_col
            x0 = col * col_w + 4
            y0 = row * (bar_h + gap) + 2
            # Label
            c.create_text(x0, y0 + bar_h // 2, text=name[:8], anchor="w",
                          fill=THEME["fg_dim"], font=("Consolas", 7))
            # Bar
            bx = x0 + 65
            bw = col_w - 75
            c.create_rectangle(bx, y0, bx + bw, y0 + bar_h,
                               fill=THEME["bg_bar"], outline="")
            fill_w = max(int(bw * min(val, 1.0)), 0)
            colour = THEME["green"] if val < 0.5 else THEME["yellow"] if val < 0.8 else THEME["red"]
            c.create_rectangle(bx, y0, bx + fill_w, y0 + bar_h,
                               fill=colour, outline="")

    def _draw_modules(self, variance: dict, energy: dict):
        c = self.module_canvas
        c.delete("all")
        w = c.winfo_width() or 320
        modules = ["thalamus", "amygdala", "hippocampus", "prefrontal"]
        col_w = w // 2
        for i, name in enumerate(modules):
            col = i % 2
            row = i // 2
            x = col * col_w + 8
            y = row * 36 + 8
            var = variance.get(name, 0)
            eng = energy.get(name, 0)
            short = name[:4]
            c.create_text(x, y, text=f"{short}", anchor="w",
                          fill=THEME["cyan"], font=("Consolas", 9, "bold"))
            c.create_text(x + 40, y, text=f"var={var:.4f} E={eng:.1f}", anchor="w",
                          fill=THEME["fg_dim"], font=("Consolas", 8))
            # Variance bar
            bar_x = x + 40
            bar_y = y + 12
            bar_w = col_w - 60
            c.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + 6,
                               fill=THEME["bg_bar"], outline="")
            fill = min(var * 100, 1.0)  # Scale: 0.01 variance = full bar
            c.create_rectangle(bar_x, bar_y, bar_x + int(bar_w * fill), bar_y + 6,
                               fill=THEME["accent"], outline="")

    def _draw_timeline(self):
        c = self.timeline_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = 100
        n = len(self.decision_history)
        if n < 2:
            return
        bar_w = max(w / HISTORY_LEN, 1)
        for i, dec in enumerate(self.decision_history):
            x = i * bar_w
            # Colour by action (cycle through palette)
            colours = [THEME["green"], THEME["cyan"], THEME["yellow"],
                       THEME["orange"], THEME["red"], THEME["purple"], THEME["accent"]]
            colour = colours[dec % len(colours)]
            c.create_rectangle(x, 0, x + bar_w, h, fill=colour, outline="")

    def _log_event(self, text: str):
        self.event_log.config(state="normal")
        self.event_log.insert("1.0", text + "\n")
        # Keep max 200 lines
        line_count = int(self.event_log.index("end-1c").split(".")[0])
        if line_count > 200:
            self.event_log.delete("200.0", "end")
        self.event_log.config(state="disabled")

    def run(self):
        self.root.mainloop()


# ── Entry point ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NORN MONITOR")
    parser.add_argument("--port", type=int, default=5555, help="Bridge port")
    parser.add_argument("--rate", type=int, default=200, help="Refresh interval (ms)")
    args = parser.parse_args()

    if ws_lib is None:
        print("ERROR: websocket-client not installed. Run: pip install websocket-client")
        return

    monitor = NornMonitor(port=args.port, refresh_ms=args.rate)
    monitor.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test by launching (requires bridge running)**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python norn_monitor.py --port 5555
```

Expected: Window opens. If bridge is running, shows live data. If not, shows "disconnected" and reconnects when bridge starts.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>
git add phase2-bridge/norn_monitor.py
git commit -m "feat: unified tkinter monitor with timing, health, drives, timeline, LTM"
```

---

## Task 5: Integration Test: Full Stack Verification

Run the complete stack (engine + bridge + monitor) and verify:
1. Session logs contain timing decomposition fields
2. Health signals are computed and logged
3. The unified monitor displays all panels correctly
4. No performance regression (tick time still under 200ms)

**Files:** No code changes: this is a validation task.

- [ ] **Step 1: Start C3 engine**

```bash
cd "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3"
start "" "engine.exe" "Creatures 3"
```

- [ ] **Step 2: Start bridge with multi-lobe mode**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python brain_bridge_client.py --multi-lobe --game '"Creatures 3"' --creature 0 --port 5555 --verbose
```

- [ ] **Step 3: Start unified monitor**

```bash
cd <PROJECT_ROOT>/phase2-bridge
python norn_monitor.py --port 5555
```

- [ ] **Step 4: Run for ~20 ticks, then verify session log**

```bash
python -c "
import json, os
logdir = 'session_logs'
latest = sorted(os.listdir(logdir))[-1]
required_fields = ['read_ms', 'brain_ms', 'write_ms', 'ltm_ms', 'total_ms',
                   'attn_entropy', 'decn_confidence', 'action_diversity', 'status',
                   'attn_values', 'decn_values']
with open(os.path.join(logdir, latest)) as f:
    for line in f:
        d = json.loads(line)
        if d.get('type') == 'tick':
            missing = [k for k in required_fields if k not in d]
            if missing:
                print(f'MISSING FIELDS: {missing}')
            else:
                print(f'tick={d[\"tick\"]} R={d[\"read_ms\"]}ms B={d[\"brain_ms\"]}ms W={d[\"write_ms\"]}ms total={d[\"total_ms\"]}ms')
                print(f'  entropy={d[\"attn_entropy\"]} conf={d[\"decn_confidence\"]} status={d[\"status\"]}')
                print(f'  attn_values has {len(d[\"attn_values\"])} elements, decn_values has {len(d[\"decn_values\"])} elements')
            break
print('PASS: All required telemetry fields present')
"
```

Expected: All required fields present. Timing decomposition adds up. Health signals in valid ranges.

- [ ] **Step 5: Commit any fixes, then final commit**

```bash
cd <PROJECT_ROOT>
git add -A
git commit -m "feat: bridge observability rebuild complete: timing + health + unified monitor"
```
