"""
telemetry.py - Structured tick records and health signal computations.

Computed once per tick, consumed by session_logger, WebSocket broadcast,
and the unified monitor. Single source of truth for all observability.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np


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


@dataclass
class TimingBreakdown:
    """Per-tick timing decomposition in milliseconds."""
    read_ms: float = 0.0
    brain_ms: float = 0.0
    write_ms: float = 0.0
    ltm_ms: float = 0.0
    overhead_ms: float = 0.0

    @property
    def total_ms(self) -> float:
        return self.read_ms + self.brain_ms + self.write_ms + self.ltm_ms + self.overhead_ms


@dataclass
class HealthSignals:
    """Per-tick brain health metrics."""
    attention_entropy: float = 0.0
    decision_confidence: float = 0.0
    module_variance: dict[str, float] = field(default_factory=dict)
    module_energy: dict[str, float] = field(default_factory=dict)
    action_diversity: float = 0.0
    attention_diversity: float = 0.0
    decision_flip_rate: float = 0.0
    status: str = "healthy"


def compute_health_signals(
    attn_values: np.ndarray,
    decn_values: np.ndarray,
    module_hidden: dict[str, np.ndarray],
    recent_decisions: list[int],
    recent_attentions: list[int],
) -> HealthSignals:
    """Compute all health signals from current tick data + rolling history."""
    # Attention entropy
    attn_probs = softmax(attn_values)
    attn_ent = 0.0
    for p in attn_probs:
        if p > 0:
            attn_ent -= p * math.log(p)
    max_attn_ent = math.log(len(attn_values)) if len(attn_values) > 1 else 1.0
    attention_entropy = attn_ent / max_attn_ent

    # Decision confidence
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

    # Rolling diversity
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
    tick: int = 0
    timing: TimingBreakdown = field(default_factory=TimingBreakdown)
    health: HealthSignals = field(default_factory=HealthSignals)
    attn_winner: int = 0
    attn_label: str = ""
    decn_winner: int = 0
    decn_label: str = ""
    attn_values: list[float] = field(default_factory=list)
    decn_values: list[float] = field(default_factory=list)
    drives: list[float] = field(default_factory=list)
    chemicals_key: list[float] = field(default_factory=list)
    emotional_tier: str = ""
    ltm_count: int = 0
    ltm_retrievals: int = 0
    posx: float = 0.0
    posy: float = 0.0

    def to_log_dict(self) -> dict:
        """Flatten to a dict for JSONL logging."""
        d: dict = {
            "type": "tick",
            "ts": time.time(),
            "tick": self.tick,
            "read_ms": round(self.timing.read_ms, 2),
            "brain_ms": round(self.timing.brain_ms, 2),
            "write_ms": round(self.timing.write_ms, 2),
            "ltm_ms": round(self.timing.ltm_ms, 2),
            "overhead_ms": round(self.timing.overhead_ms, 2),
            "total_ms": round(self.timing.total_ms, 2),
            "attn_entropy": self.health.attention_entropy,
            "decn_confidence": self.health.decision_confidence,
            "action_diversity": self.health.action_diversity,
            "attention_diversity": self.health.attention_diversity,
            "decision_flip_rate": self.health.decision_flip_rate,
            "status": self.health.status,
            "attn_win": self.attn_winner,
            "attn_lbl": self.attn_label,
            "decn_win": self.decn_winner,
            "decn_lbl": self.decn_label,
            "attn_values": [round(v, 4) for v in self.attn_values],
            "decn_values": [round(v, 4) for v in self.decn_values],
            "drives": [round(d, 4) for d in self.drives],
            "chemicals": [round(c, 4) for c in self.chemicals_key],
            "tier": self.emotional_tier,
            "ltm_count": self.ltm_count,
            "ltm_retrievals": self.ltm_retrievals,
            "posx": round(self.posx, 1),
            "posy": round(self.posy, 1),
        }
        for name, var in self.health.module_variance.items():
            d[f"module_var_{name}"] = var
        for name, energy in self.health.module_energy.items():
            d[f"module_energy_{name}"] = energy
        return d
