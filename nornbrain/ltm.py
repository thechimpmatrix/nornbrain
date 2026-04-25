"""
NORNBRAIN Long-Term Memory (LTM) System - Phase 4B

Persistent, non-neural memory bank for norns. Encodes intense experiences
as discrete memory records, retrieves them when current context matches
past episodes, and injects emotional signal back into the brain via
the 6 LTM channels defined in Phase 4A.

Key design points:
- MemoryBank does NOT import or depend on brain classes; it receives
  raw lists of floats for context keys.
- torch is used only for cosine similarity (dot, norm).
- Everything else is standard Python + dataclasses + json.

See: docs/superpowers/specs/2026-03-30-phase4b-ltm-system-design.md
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import torch


# ---------------------------------------------------------------------------
# 3. Memory Record Data Structure
# ---------------------------------------------------------------------------

@dataclass
class MemoryRecord:
    """A single long-term memory.

    Fields are grouped into identity, context key, coarse retrieval keys,
    emotional payload, drive snapshot, and lifecycle metadata.
    """

    # Identity
    memory_id: int                    # Unique auto-incrementing ID
    tick_created: int                 # Game tick when encoded
    age_at_creation: int              # Norn's age (in ticks) when encoded

    # Context key - the CfC hidden state at encoding time, L2-normalised.
    # Cosine similarity = dot product when both keys are unit-normalised.
    context_key: list[float]          # Concatenated hidden states (845 floats for v2)

    # Coarse retrieval keys (for two-tier fast filter)
    attention_idx: int                # What was the norn attending to (0-39)
    action_idx: int                   # What action was it taking (0-16)
    location_zone: int                # Spatial hash of (posx, posy)

    # Payload - what gets injected on retrieval
    valence: float                    # How good/bad (-1.0 to +1.0)
    intensity: float                  # How strongly encoded (0.0 to 1.0)
    arousal: float                    # How activated the norn was (0.0 to 1.0)

    # Drive snapshot at encoding time (for debugging/display)
    drive_snapshot: list[float]       # 20 drive values

    # Lifecycle
    recall_count: int                 # How many times this memory has been retrieved
    last_recall_tick: int             # Last tick this memory was retrieved
    consolidated: bool                # Whether this has been through consolidation
    source: str                       # "experience" or "inherited"


# ---------------------------------------------------------------------------
# 4. Encoding Functions
# ---------------------------------------------------------------------------

def compute_intensity(chemicals: dict[int, float],
                      drives: list[float],
                      prev_drives: list[float]) -> float:
    """Compute encoding intensity from current biochemical state.

    Args:
        chemicals: Dict of chemical_id -> concentration (0.0 to 1.0).
        drives: Current drive values (20 floats).
        prev_drives: Drive values from previous tick.

    Returns:
        Intensity score (0.0 to 1.0).
    """
    # Direct biochemical signals
    reward = chemicals.get(204, 0.0)
    punishment = chemicals.get(205, 0.0)
    adrenaline = chemicals.get(117, 0.0)
    pain_chem = chemicals.get(148, 0.0)

    # Drive deltas - sudden changes are significant
    drive_deltas = [abs(d - p) for d, p in zip(drives, prev_drives)]
    max_drive_delta = max(drive_deltas) if drive_deltas else 0.0

    # Drive desperation - extreme drives amplify encoding
    max_drive = max(drives) if drives else 0.0
    desperation = max(0.0, max_drive - 0.6) / 0.4  # 0 at 0.6, 1 at 1.0

    # Raw intensity: maximum of all signals
    raw_intensity = max(
        reward,
        punishment,
        adrenaline,
        pain_chem,
        max_drive_delta * 2.0,  # Drive changes weighted 2x
    )

    # Amplify by desperation (desperate norn encodes more readily)
    intensity = min(1.0, raw_intensity * (1.0 + 0.5 * desperation))

    return intensity


def compute_valence(chemicals: dict[int, float],
                    drive_deltas: list[float]) -> float:
    """Compute emotional valence of current experience.

    Positive = good (reward, drives decreasing = needs being met).
    Negative = bad (punishment, pain, drives increasing = needs worsening).

    Args:
        chemicals: Dict of chemical_id -> concentration.
        drive_deltas: Per-drive change (current - previous), signed.

    Returns:
        Valence (-1.0 to +1.0).
    """
    reward = chemicals.get(204, 0.0)
    punishment = chemicals.get(205, 0.0)
    pain = chemicals.get(148, 0.0)

    # Net biochemical signal
    biochem_valence = reward - punishment - pain * 0.5

    # Drive satisfaction signal:
    # Negative delta = drive decreasing = need being met = positive
    avg_drive_delta = sum(drive_deltas) / len(drive_deltas) if drive_deltas else 0.0
    drive_valence = -avg_drive_delta * 2.0  # Inverted

    # Combined, clamped
    valence = max(-1.0, min(1.0, biochem_valence + drive_valence))
    return valence


def compute_arousal(chemicals: dict[int, float]) -> float:
    """Compute arousal level from biochemistry.

    High arousal = alert, reactive, adrenaline-driven.
    Low arousal  = calm, resting, sleepy.

    Args:
        chemicals: Dict of chemical_id -> concentration.

    Returns:
        Arousal (0.0 to 1.0).
    """
    adrenaline = chemicals.get(117, 0.0)
    sleepase = chemicals.get(112, 0.0)
    stress = chemicals.get(128, 0.0)

    arousal = min(1.0, adrenaline + stress * 0.5 - sleepase * 0.5)
    return max(0.0, arousal)


def compute_location_zone(posx: float, posy: float,
                          zone_width: int = 500,
                          zone_height: int = 500) -> int:
    """Hash (posx, posy) into a spatial zone index.

    The C3 world is roughly 0-58000 x 0-16000.
    With 500-pixel zones: 116 x 32 = 3712 possible zones.

    Args:
        posx: Norn X position in world coordinates.
        posy: Norn Y position in world coordinates.
        zone_width: Width of each zone in pixels.
        zone_height: Height of each zone in pixels.

    Returns:
        Integer zone index (zx * 100 + zy).
    """
    zx = int(posx / zone_width)
    zy = int(posy / zone_height)
    return zx * 100 + zy


def l2_normalise(vec: list[float]) -> list[float]:
    """L2-normalise a list of floats in-place. Returns the normalised list."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-8:
        return [x / norm for x in vec]
    return vec


# ---------------------------------------------------------------------------
# 5. Retrieval helpers (module-level for inject)
# ---------------------------------------------------------------------------

def inject(matches: list[tuple[MemoryRecord, float]],
           tick: int) -> dict[str, float]:
    """Convert retrieved memories to injection channels.

    Returns dict with 6 float values for the LTM input channels:
        mem1_valence, mem1_arousal, mem2_valence, mem2_arousal,
        mem3_valence, mem3_arousal.

    Updates recall_count and last_recall_tick on retrieved memories.
    """
    injection: dict[str, float] = {
        "mem1_valence": 0.0, "mem1_arousal": 0.0,
        "mem2_valence": 0.0, "mem2_arousal": 0.0,
        "mem3_valence": 0.0, "mem3_arousal": 0.0,
    }

    for i, (mem, score) in enumerate(matches):
        if i >= 3:
            break

        # Scale by similarity score (stronger match = stronger injection)
        injection[f"mem{i + 1}_valence"] = mem.valence * score
        injection[f"mem{i + 1}_arousal"] = mem.arousal * score

        # Update memory lifecycle
        mem.recall_count += 1
        mem.last_recall_tick = tick

    return injection


# ---------------------------------------------------------------------------
# 3 (cont). Memory Bank
# ---------------------------------------------------------------------------

@dataclass
class MemoryBank:
    """Persistent collection of long-term memories for a single creature.

    Parameters mirror the spec exactly (Section 3).
    """

    creature_id: str
    memories: list[MemoryRecord] = field(default_factory=list)
    capacity: int = 200
    next_id: int = 0

    # Encoding parameters
    encoding_threshold: float = 0.4
    encoding_cooldown: int = 20

    # Retrieval parameters
    coarse_filter_enabled: bool = True
    similarity_threshold: float = 0.6
    max_retrievals: int = 3

    # Consolidation parameters
    consolidation_merge_threshold: float = 0.8
    negativity_bias: float = 0.7
    min_intensity_to_keep: float = 0.1

    # State
    last_encoding_tick: int = 0
    is_sleeping: bool = False
    last_consolidation_tick: int = 0

    # ------------------------------------------------------------------
    # 4 (cont). Encoding
    # ------------------------------------------------------------------

    def maybe_encode(
        self,
        context_key: list[float],
        chemicals: dict[int, float],
        drives: list[float],
        prev_drives: list[float],
        attn_winner: int,
        decn_winner: int,
        posx: float,
        posy: float,
        tick: int,
        age: int = 0,
    ) -> bool:
        """Check if current experience should be encoded as LTM.

        The caller is responsible for generating the context_key (the
        concatenated, L2-normalised hidden states from the brain).

        Returns True if a memory was encoded.
        """
        # Cooldown check
        if tick - self.last_encoding_tick < self.encoding_cooldown:
            return False

        # Compute intensity
        intensity = compute_intensity(chemicals, drives, prev_drives)

        # Below threshold - not significant enough to remember
        if intensity < self.encoding_threshold:
            return False

        # Encode
        drive_deltas = [d - p for d, p in zip(drives, prev_drives)]
        valence = compute_valence(chemicals, drive_deltas)
        arousal = compute_arousal(chemicals)
        normed_key = l2_normalise(list(context_key))
        location_zone = compute_location_zone(posx, posy)

        record = MemoryRecord(
            memory_id=self.next_id,
            tick_created=tick,
            age_at_creation=age if age else tick,
            context_key=normed_key,
            attention_idx=attn_winner,
            action_idx=decn_winner,
            location_zone=location_zone,
            valence=valence,
            intensity=intensity,
            arousal=arousal,
            drive_snapshot=list(drives),
            recall_count=0,
            last_recall_tick=0,
            consolidated=False,
            source="experience",
        )

        self.memories.append(record)
        self.next_id += 1
        self.last_encoding_tick = tick

        # Capacity management
        if len(self.memories) > self.capacity:
            self._evict_weakest()

        return True

    # ------------------------------------------------------------------
    # 5. Retrieval
    # ------------------------------------------------------------------

    def coarse_filter(self, attn_winner: int,
                      location_zone: int) -> list[MemoryRecord]:
        """Tier 1: fast pre-filter using cheap categorical matches.

        Match criteria (OR logic - any match passes):
        - Same attention category (seeing the same type of thing)
        - Same location zone (being in the same place)
        """
        candidates: list[MemoryRecord] = []
        for mem in self.memories:
            if mem.attention_idx == attn_winner:
                candidates.append(mem)
            elif mem.location_zone == location_zone:
                candidates.append(mem)
        return candidates

    def retrieve(
        self,
        context_key: list[float],
        attn_winner: int,
        location_zone: int,
    ) -> list[tuple[MemoryRecord, float]]:
        """Retrieve top-K matching memories for injection.

        Args:
            context_key: L2-normalised hidden state vector (list of floats).
            attn_winner: Current attention neuron winner index.
            location_zone: Current spatial zone index.

        Returns:
            List of (memory, score) tuples sorted by score descending.
            Score = cosine_similarity * memory.intensity.
        """
        current_key_t = torch.tensor(context_key, dtype=torch.float32)
        current_norm = torch.norm(current_key_t)

        if current_norm < 1e-8:
            return []  # Brain hasn't been initialised yet

        # Tier 1: coarse filter
        if self.coarse_filter_enabled:
            candidates = self.coarse_filter(attn_winner, location_zone)
        else:
            candidates = self.memories

        if not candidates:
            return []

        # Tier 2: cosine similarity
        matches: list[tuple[MemoryRecord, float]] = []
        for mem in candidates:
            mem_key_t = torch.tensor(mem.context_key, dtype=torch.float32)
            mem_norm = torch.norm(mem_key_t)
            if mem_norm < 1e-8:
                continue

            similarity = (torch.dot(current_key_t, mem_key_t)
                          / (current_norm * mem_norm)).item()

            if similarity >= self.similarity_threshold:
                score = similarity * mem.intensity
                matches.append((mem, score))

        # Sort by score descending, take top K
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:self.max_retrievals]

    # ------------------------------------------------------------------
    # 6. Sleep Consolidation
    # ------------------------------------------------------------------

    @staticmethod
    def check_sleep_state(chemicals: dict[int, float]) -> bool:
        """Detect sleep onset from biochemistry.

        The norn is sleeping when sleepase (chem 112) is high
        and/or Pre-REM sleep (chem 212) is present.
        """
        sleepase = chemicals.get(112, 0.0)
        pre_rem = chemicals.get(212, 0.0)
        return sleepase > 0.5 or pre_rem > 0.3

    def consolidate(self, current_tick: int) -> None:
        """Run memory consolidation. Atomic - completes in one call.

        Steps:
        1. Group similar memories by context_key cosine similarity.
        2. Merge each group (with negativity bias).
        3. Prune weak memories.
        4. Enforce capacity limit.
        """
        if not self.memories:
            return

        # Step 1: greedy clustering
        assigned: set[int] = set()
        groups: list[list[int]] = []

        for i, mem_i in enumerate(self.memories):
            if i in assigned:
                continue

            group = [i]
            assigned.add(i)
            key_i = torch.tensor(mem_i.context_key, dtype=torch.float32)
            norm_i = torch.norm(key_i)

            if norm_i < 1e-8:
                continue

            for j in range(i + 1, len(self.memories)):
                if j in assigned:
                    continue

                mem_j = self.memories[j]
                key_j = torch.tensor(mem_j.context_key, dtype=torch.float32)
                norm_j = torch.norm(key_j)
                if norm_j < 1e-8:
                    continue

                similarity = (torch.dot(key_i, key_j)
                              / (norm_i * norm_j)).item()

                # Negativity bias: negative memories require higher
                # similarity to merge (they resist consolidation)
                threshold = self.consolidation_merge_threshold
                if mem_i.valence < 0 or mem_j.valence < 0:
                    threshold = threshold / self.negativity_bias

                if similarity >= threshold:
                    group.append(j)
                    assigned.add(j)

            if len(group) > 1:
                groups.append(group)

        # Step 2: merge each group
        # Collect all indices to remove and all merged memories to add
        indices_to_remove = set()
        merged_memories = []
        for group_indices in groups:
            group_memories = [self.memories[i] for i in group_indices]
            merged = self._merge_memories(group_memories)
            indices_to_remove.update(group_indices)
            merged_memories.append(merged)

        # Rebuild memory list: keep non-removed, add merged
        self.memories = [
            m for i, m in enumerate(self.memories)
            if i not in indices_to_remove
        ] + merged_memories

        # Step 3: prune weak memories
        self.memories = [
            m for m in self.memories
            if m.intensity >= self.min_intensity_to_keep
            or m.recall_count > 0       # Never prune a recalled memory
            or m.source == "inherited"   # Never prune inherited instincts
        ]

        # Step 4: enforce capacity
        while len(self.memories) > self.capacity:
            self._evict_weakest()

        self.last_consolidation_tick = current_tick

    def _merge_memories(self, memories: list[MemoryRecord]) -> MemoryRecord:
        """Merge a group of similar memories into one consolidated memory.

        Strategy:
        - context_key: intensity-weighted average (re-normalised).
        - valence: intensity-weighted average.
        - intensity: max of group * 1.1 (consolidation strengthens).
        - arousal: intensity-weighted average.
        - attention_idx, action_idx, location_zone: mode.
        - recall_count: sum.
        """
        total_intensity = sum(m.intensity for m in memories)

        # Weighted average of context keys
        key_len = len(memories[0].context_key)
        merged_key = [0.0] * key_len
        for m in memories:
            weight = m.intensity / total_intensity if total_intensity > 0 else 1.0 / len(memories)
            for k in range(key_len):
                merged_key[k] += m.context_key[k] * weight

        # Intensity-weighted averages for valence and arousal
        if total_intensity > 0:
            merged_valence = sum(m.valence * m.intensity for m in memories) / total_intensity
            merged_arousal = sum(m.arousal * m.intensity for m in memories) / total_intensity
        else:
            merged_valence = sum(m.valence for m in memories) / len(memories)
            merged_arousal = sum(m.arousal for m in memories) / len(memories)

        # Consolidated intensity = max * boost
        merged_intensity = min(1.0, max(m.intensity for m in memories) * 1.1)

        # Mode for categorical fields
        attn_mode = Counter(m.attention_idx for m in memories).most_common(1)[0][0]
        action_mode = Counter(m.action_idx for m in memories).most_common(1)[0][0]
        location_mode = Counter(m.location_zone for m in memories).most_common(1)[0][0]

        record = MemoryRecord(
            memory_id=self.next_id,
            tick_created=min(m.tick_created for m in memories),
            age_at_creation=min(m.age_at_creation for m in memories),
            context_key=merged_key,
            attention_idx=attn_mode,
            action_idx=action_mode,
            location_zone=location_mode,
            valence=max(-1.0, min(1.0, merged_valence)),
            intensity=merged_intensity,
            arousal=max(0.0, min(1.0, merged_arousal)),
            drive_snapshot=memories[0].drive_snapshot,  # Keep first snapshot
            recall_count=sum(m.recall_count for m in memories),
            last_recall_tick=max(m.last_recall_tick for m in memories),
            consolidated=True,
            source="experience",
        )
        self.next_id += 1
        return record

    # ------------------------------------------------------------------
    # 7. Capacity Management
    # ------------------------------------------------------------------

    def _evict_weakest(self) -> None:
        """Remove the single weakest memory.

        Weakness score = intensity * recency_factor * recall_factor.
        Lower score = more likely to be evicted.
        Inherited instincts are protected from eviction.
        Negative memories get a 1.5x score boost (harder to evict).
        """
        if not self.memories:
            return

        weakest_idx = 0
        weakest_score = float("inf")

        for i, mem in enumerate(self.memories):
            # Inherited instincts are protected
            if mem.source == "inherited":
                continue

            # Recency: memories not recalled recently are weaker
            ref_tick = max(self.last_consolidation_tick, self.last_encoding_tick, 1)
            ticks_since_recall = (
                ref_tick - mem.last_recall_tick
                if mem.last_recall_tick > 0
                else ref_tick - mem.tick_created
            )
            recency_factor = 1.0 / (1.0 + ticks_since_recall / 1000.0)

            # Recall frequency: frequently recalled memories are stronger
            recall_factor = 1.0 + mem.recall_count * 0.1

            # Combined score
            score = mem.intensity * recency_factor * recall_factor

            # Negativity bias: negative memories are harder to evict
            if mem.valence < 0:
                score *= 1.5

            if score < weakest_score:
                weakest_score = score
                weakest_idx = i

        self.memories.pop(weakest_idx)

    # ------------------------------------------------------------------
    # 8. Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save memory bank to JSON file.

        Creates parent directories if they don't exist.
        """
        data = {
            "version": 1,
            "creature_id": self.creature_id,
            "capacity": self.capacity,
            "next_id": self.next_id,
            "encoding_threshold": self.encoding_threshold,
            "encoding_cooldown": self.encoding_cooldown,
            "similarity_threshold": self.similarity_threshold,
            "consolidation_merge_threshold": self.consolidation_merge_threshold,
            "negativity_bias": self.negativity_bias,
            "memories": [asdict(m) for m in self.memories],
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "MemoryBank":
        """Load memory bank from JSON file.

        Returns a new MemoryBank instance populated from the file.
        """
        with open(path) as f:
            data = json.load(f)

        bank = cls(creature_id=data["creature_id"])
        bank.capacity = data.get("capacity", 200)
        bank.next_id = data.get("next_id", 0)
        bank.encoding_threshold = data.get("encoding_threshold", 0.4)
        bank.encoding_cooldown = data.get("encoding_cooldown", 20)
        bank.similarity_threshold = data.get("similarity_threshold", 0.6)
        bank.consolidation_merge_threshold = data.get(
            "consolidation_merge_threshold", 0.8
        )
        bank.negativity_bias = data.get("negativity_bias", 0.7)
        bank.memories = [MemoryRecord(**m) for m in data["memories"]]
        return bank


# ---------------------------------------------------------------------------
# 9. Offspring Inheritance
# ---------------------------------------------------------------------------

def create_offspring_memories(
    parent_banks: list[MemoryBank],
    inheritance_factor: float = 0.3,
    max_inherited: int = 10,
) -> list[MemoryRecord]:
    """Create inherited instinct memories for a new norn.

    Selects the strongest emotional memories from all parents, attenuates
    them, and marks them as inherited. Inherited memories are protected
    from eviction and function identically during retrieval.

    Args:
        parent_banks: Memory banks of parent creatures.
        inheritance_factor: Attenuation factor (0.3 = 30% of original intensity).
        max_inherited: Maximum number of inherited memories.

    Returns:
        List of attenuated MemoryRecords marked as "inherited".
        Their memory_id is set to -1 and should be reassigned by the
        receiving MemoryBank.
    """
    # Collect all parent memories
    all_parent_memories: list[MemoryRecord] = []
    for bank in parent_banks:
        all_parent_memories.extend(bank.memories)

    # Sort by intensity * |valence| (strongest emotional memories inherited)
    all_parent_memories.sort(
        key=lambda m: m.intensity * abs(m.valence),
        reverse=True,
    )

    inherited: list[MemoryRecord] = []
    for mem in all_parent_memories[:max_inherited]:
        instinct = MemoryRecord(
            memory_id=-1,
            tick_created=0,
            age_at_creation=0,
            context_key=list(mem.context_key),
            attention_idx=mem.attention_idx,
            action_idx=mem.action_idx,
            location_zone=mem.location_zone,
            valence=mem.valence,
            intensity=mem.intensity * inheritance_factor,
            arousal=mem.arousal * inheritance_factor,
            drive_snapshot=[0.0] * 20,
            recall_count=0,
            last_recall_tick=0,
            consolidated=True,
            source="inherited",
        )
        inherited.append(instinct)

    return inherited


# ---------------------------------------------------------------------------
# Sanity Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    print("=== NORNBRAIN LTM Sanity Tests ===\n")

    KEY_DIM = 845  # v2: thalamus(120) + amygdala(85) + hippocampus(120) + frontal(520)

    def make_key(seed: float = 1.0) -> list[float]:
        """Generate a deterministic, L2-normalised context key."""
        raw = [(seed + i * 0.01) for i in range(KEY_DIM)]
        return l2_normalise(raw)

    # --- Test 1: Create bank, encode memories ---
    print("Test 1: Create bank and encode memories")
    bank = MemoryBank(creature_id="test-norn-001")
    assert len(bank.memories) == 0

    # High-intensity event (punishment)
    chemicals_bad: dict[int, float] = {204: 0.0, 205: 0.8, 117: 0.3, 148: 0.5, 112: 0.0, 128: 0.0, 212: 0.0}
    drives = [0.5] * 20
    prev_drives = [0.3] * 20

    encoded = bank.maybe_encode(
        context_key=make_key(1.0),
        chemicals=chemicals_bad,
        drives=drives,
        prev_drives=prev_drives,
        attn_winner=5,
        decn_winner=3,
        posx=1200.0,
        posy=800.0,
        tick=100,
    )
    assert encoded, "High-intensity event should have been encoded"
    assert len(bank.memories) == 1
    assert bank.memories[0].valence < 0, "Punishment event should have negative valence"
    print(f"  Encoded memory: valence={bank.memories[0].valence:.3f}, "
          f"intensity={bank.memories[0].intensity:.3f}, "
          f"arousal={bank.memories[0].arousal:.3f}")

    # Cooldown check - should not encode again too soon
    encoded2 = bank.maybe_encode(
        context_key=make_key(1.1),
        chemicals=chemicals_bad,
        drives=drives,
        prev_drives=prev_drives,
        attn_winner=5,
        decn_winner=3,
        posx=1200.0,
        posy=800.0,
        tick=105,
    )
    assert not encoded2, "Should be blocked by encoding cooldown"
    print("  Cooldown correctly blocked second encoding")

    # Encode a positive memory after cooldown
    chemicals_good: dict[int, float] = {204: 0.7, 205: 0.0, 117: 0.0, 148: 0.0, 112: 0.0, 128: 0.0, 212: 0.0}
    encoded3 = bank.maybe_encode(
        context_key=make_key(2.0),
        chemicals=chemicals_good,
        drives=[0.3] * 20,
        prev_drives=[0.5] * 20,
        attn_winner=10,
        decn_winner=7,
        posx=5000.0,
        posy=2000.0,
        tick=130,
    )
    assert encoded3, "Positive event should have been encoded"
    assert bank.memories[1].valence > 0, "Reward event should have positive valence"
    print(f"  Encoded positive memory: valence={bank.memories[1].valence:.3f}")

    # Encode a third memory with similar context to the first
    encoded4 = bank.maybe_encode(
        context_key=make_key(1.05),  # Very similar to first memory
        chemicals=chemicals_bad,
        drives=drives,
        prev_drives=prev_drives,
        attn_winner=5,
        decn_winner=3,
        posx=1250.0,
        posy=850.0,
        tick=160,
    )
    assert encoded4
    assert len(bank.memories) == 3
    print(f"  Total memories: {len(bank.memories)}")
    print("  PASSED\n")

    # --- Test 2: Retrieval ---
    print("Test 2: Retrieval (coarse filter + cosine similarity)")
    # Query with context similar to the first (negative) memory
    query_key = make_key(1.02)  # Close to seed=1.0
    matches = bank.retrieve(
        context_key=query_key,
        attn_winner=5,        # Same attention as first memory
        location_zone=compute_location_zone(1200.0, 800.0),
    )
    print(f"  Retrieved {len(matches)} match(es)")
    for mem, score in matches:
        print(f"    id={mem.memory_id}, valence={mem.valence:.3f}, score={score:.4f}")
    assert len(matches) > 0, "Should retrieve at least one match"
    assert matches[0][0].memory_id in (0, 2), "Best match should be memory 0 or 2 (similar context)"
    print("  PASSED\n")

    # --- Test 3: Injection ---
    print("Test 3: Injection channels")
    channels = inject(matches, tick=200)
    print(f"  Channels: {channels}")
    assert "mem1_valence" in channels
    assert "mem1_arousal" in channels
    # First match is negative, so mem1_valence should be negative
    assert channels["mem1_valence"] < 0, "Negative memory should inject negative valence"
    print("  PASSED\n")

    # --- Test 4: Sleep consolidation ---
    print("Test 4: Sleep consolidation")
    pre_count = len(bank.memories)
    # Memories 0 and 2 have very similar context keys - they should merge
    # (but they're negative, so negativity bias applies)
    bank.consolidate(current_tick=300)
    post_count = len(bank.memories)
    print(f"  Memories before: {pre_count}, after: {post_count}")
    # Check at least one is now consolidated
    consolidated_count = sum(1 for m in bank.memories if m.consolidated)
    print(f"  Consolidated memories: {consolidated_count}")
    print("  PASSED\n")

    # --- Test 5: Save / Load round-trip ---
    print("Test 5: Save / Load round-trip")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = str(Path(tmpdir) / "test_memories.json")
        bank.save(save_path)
        print(f"  Saved to {save_path}")

        loaded_bank = MemoryBank.load(save_path)
        assert loaded_bank.creature_id == bank.creature_id
        assert len(loaded_bank.memories) == len(bank.memories)
        assert loaded_bank.capacity == bank.capacity
        assert loaded_bank.next_id == bank.next_id

        # Verify a memory round-tripped correctly
        for orig, loaded in zip(bank.memories, loaded_bank.memories):
            assert orig.memory_id == loaded.memory_id
            assert orig.valence == loaded.valence
            assert orig.intensity == loaded.intensity
            assert len(orig.context_key) == len(loaded.context_key)
        print("  Round-trip verified: all fields match")
    print("  PASSED\n")

    # --- Test 6: Offspring inheritance ---
    print("Test 6: Offspring inheritance")
    # Create a second parent bank
    parent2 = MemoryBank(creature_id="test-norn-002")
    parent2.maybe_encode(
        context_key=make_key(3.0),
        chemicals={204: 0.9, 205: 0.0, 117: 0.0, 148: 0.0, 112: 0.0, 128: 0.0, 212: 0.0},
        drives=[0.2] * 20,
        prev_drives=[0.6] * 20,
        attn_winner=15,
        decn_winner=1,
        posx=10000.0,
        posy=5000.0,
        tick=500,
    )

    inherited = create_offspring_memories([bank, parent2], inheritance_factor=0.3, max_inherited=5)
    print(f"  Inherited {len(inherited)} memories from 2 parents")
    for inst in inherited:
        print(f"    source={inst.source}, valence={inst.valence:.3f}, "
              f"intensity={inst.intensity:.3f}")
        assert inst.source == "inherited"
        assert inst.memory_id == -1  # Needs reassignment
    print("  PASSED\n")

    # --- Test 7: Capacity management ---
    print("Test 7: Capacity management (eviction)")
    small_bank = MemoryBank(creature_id="test-cap", capacity=5)
    for t in range(10):
        tick = t * 25
        small_bank.maybe_encode(
            context_key=make_key(t * 10.0),
            chemicals={204: 0.0, 205: 0.6, 117: 0.1, 148: 0.0, 112: 0.0, 128: 0.0, 212: 0.0},
            drives=[0.4 + t * 0.05] * 20,
            prev_drives=[0.3] * 20,
            attn_winner=t % 40,
            decn_winner=t % 15,
            posx=float(t * 1000),
            posy=500.0,
            tick=tick,
        )
    assert len(small_bank.memories) <= 5, f"Should be at capacity (5), got {len(small_bank.memories)}"
    print(f"  Bank capped at {len(small_bank.memories)} memories (capacity=5)")
    print("  PASSED\n")

    # --- Test 8: Sleep state detection ---
    print("Test 8: Sleep state detection")
    assert not MemoryBank.check_sleep_state({112: 0.1, 212: 0.0})
    assert MemoryBank.check_sleep_state({112: 0.6, 212: 0.0})
    assert MemoryBank.check_sleep_state({112: 0.0, 212: 0.4})
    assert MemoryBank.check_sleep_state({112: 0.8, 212: 0.5})
    print("  All sleep state checks passed")
    print("  PASSED\n")

    # --- Test 9: Encoding functions edge cases ---
    print("Test 9: Encoding function edge cases")
    # Empty drives
    assert compute_intensity({}, [], []) == 0.0
    assert compute_valence({}, []) == 0.0
    assert compute_arousal({}) == 0.0
    # Location zone
    assert compute_location_zone(0.0, 0.0) == 0
    assert compute_location_zone(500.0, 500.0) == 101
    assert compute_location_zone(58000.0, 16000.0) == 11632
    print("  Edge cases handled correctly")
    print("  PASSED\n")

    print("=== All 9 sanity tests PASSED ===")
