# Phase 4B: Long-Term Memory System: Specification

**Date:** 2026-03-30
**Branch:** `feature/multi-lobe-cfc`
**Depends on:** Phase 4A (Multi-Lobe CfC Architecture)

---

## 0. Document Purpose

This document specifies the Long-Term Memory (LTM) system for NORNBRAIN. The LTM is a persistent, non-neural memory bank implemented in the Python bridge process. It encodes intense experiences as discrete memory records, retrieves them when the current context matches past experiences, and injects the emotional signal back into the brain via the 6 LTM channels defined in Phase 4A.

The LTM gives norns genuine lifetime experience. A norn that was attacked by a grendel will remember it. A norn that found reliable food in a specific location will return there. These memories persist across sessions and can be partially inherited by offspring.

**What this document covers:**
- Memory record data structure
- Encoding system (intensity threshold, context key generation)
- Two-tier retrieval system (coarse filter + cosine similarity)
- Multi-channel injection (3 slots × 2 channels)
- Sleep consolidation algorithm
- Negativity bias in consolidation
- Memory capacity management
- Persistence and serialisation
- Offspring inheritance ("instinct")
- Bridge integration

**What this document does NOT cover:**
- CfC module architecture (see Phase 4A)
- Emotional dominance hierarchy (see Phase 4C)
- Language output (see Phase 4D)

---

## 1. Goals and Success Criteria

### Primary Goal
Give norns persistent, experience-based long-term memory that survives across ticks, sessions, and (partially) generations. The memory system is event-driven: it encodes intense experiences and retrieves them when current sensory context resembles past episodes.

### Success Criteria
1. **SC1: Encoding triggers:** Intense biochemical events (pain spikes, reward surges, punishment, adrenaline) trigger memory encoding when intensity exceeds a configurable threshold.
2. **SC2: Retrieval accuracy:** When a norn encounters a context similar to a stored memory (e.g., sees a grendel after being attacked by one), the correct memory is retrieved and injected within the same tick.
3. **SC3: Behavioural impact:** Memory injection measurably affects norn decisions. A norn with a strong negative grendel memory should exhibit avoidance behaviour. A norn with positive food-location memories should navigate toward those locations.
4. **SC4: Sleep consolidation:** Similar memories merge during sleep, reducing memory count while strengthening patterns. Negative memories resist consolidation (negativity bias).
5. **SC5: Persistence:** Memory banks save to disk and reload on session restart. A norn's memories survive game restarts.
6. **SC6: Inheritance:** Offspring receive attenuated versions of their parents' strongest memories as "instincts."

### Non-Goals for Phase 4B
- Differentiable memory (the LTM is not part of the gradient computation graph)
- Spatial map building (future: the hippocampus CfC handles short-term spatial context)
- Explicit memory editing by the user (debugging tools may expose memories, but no in-game editing)

---

## 2. Architecture Overview

### Position in the System

```
┌─────────────────────────────────────────────────┐
│                 PYTHON BRIDGE                    │
│                                                  │
│  ┌──────────────┐    ┌────────────────────────┐ │
│  │ Brain Reader  │    │  LTM Bank              │ │
│  │ (DMPL reads)  │    │  memory_bank.json      │ │
│  └──────┬───────┘    │                        │ │
│         │            │  ┌──────────────────┐  │ │
│         │ raw state  │  │ Encoder          │  │ │
│         │            │  │ (intensity check) │  │ │
│         │            │  └──────────────────┘  │ │
│         │            │  ┌──────────────────┐  │ │
│         │            │  │ Retriever        │  │ │
│         │            │  │ (two-tier search) │  │ │
│         │            │  └──────────────────┘  │ │
│         │            │  ┌──────────────────┐  │ │
│         │            │  │ Consolidator     │  │ │
│         │            │  │ (sleep-triggered) │  │ │
│         │            │  └──────────────────┘  │ │
│         │            └────────┬───────────────┘ │
│         │                     │                  │
│         ▼                     ▼                  │
│  ┌──────────────────────────────────────────┐   │
│  │          Multi-Lobe CfC Brain             │   │
│  │                                           │   │
│  │  raw inputs ──→ modules ──→ decisions     │   │
│  │  ltm_injection ──→ tract_ltm_pfc ──→ PFC │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Data Flow Per Tick

```
1. Bridge reads raw state from game (DMPL + chemicals)
2. Bridge computes multi-lobe brain input
3. RETRIEVE: Compare current hidden state against memory bank
   → If matches found: populate ltm_injection channels
   → If no matches: ltm_injection = zeros
4. Brain tick: all modules process, PFC receives ltm_injection
5. Brain outputs attention + decision
6. ENCODE: Compute intensity score from biochemistry
   → If intensity > threshold: snapshot context + valence → store
7. Bridge writes decision back to game
```

---

## 3. Memory Record Data Structure

### Single Memory Record

```python
@dataclass
class MemoryRecord:
    """A single long-term memory."""

    # Identity
    memory_id: int                    # Unique auto-incrementing ID
    tick_created: int                 # Game tick when encoded
    age_at_creation: int              # Norn's age (in ticks) when encoded

    # Context key: the CfC hidden state at encoding time, L2-normalised
    # Used for similarity-based retrieval (cosine sim = dot product when normalised)
    context_key: list[float]          # Concatenated hidden states from all modules
                                      # Length: 239 (sum of all module hidden sizes)
                                      # L2-normalised at encoding time

    # Coarse retrieval keys (for two-tier fast filter)
    attention_idx: int                # What was the norn attending to (0-39)
    action_idx: int                   # What action was it taking (0-16)
    location_zone: int                # Spatial hash of (posx, posy) into zones

    # Payload: what gets injected on retrieval
    valence: float                    # How good/bad (-1.0 to +1.0)
    intensity: float                  # How strongly encoded (0.0 to 1.0)
    arousal: float                    # How activated the norn was (0.0 to 1.0)

    # Drive snapshot at encoding time (for debugging/display)
    drive_snapshot: list[float]       # 20 drive values

    # Lifecycle
    recall_count: int                 # How many times this memory has been retrieved
    last_recall_tick: int             # Last tick this memory was retrieved
    consolidated: bool                # Whether this memory has been through consolidation
    source: str                       # "experience" or "inherited"
```

### Memory Bank

```python
@dataclass
class MemoryBank:
    """Persistent collection of long-term memories."""

    creature_id: str                  # Unique creature identifier
    memories: list[MemoryRecord]      # All stored memories
    capacity: int = 200               # Maximum number of memories
    next_id: int = 0                  # Auto-incrementing ID counter

    # Encoding parameters
    encoding_threshold: float = 0.4   # Minimum intensity to trigger encoding
    encoding_cooldown: int = 20       # Minimum ticks between encodings

    # Retrieval parameters
    coarse_filter_enabled: bool = True
    similarity_threshold: float = 0.6  # Minimum cosine similarity for retrieval
    max_retrievals: int = 3            # Top-K memories to inject

    # Consolidation parameters
    consolidation_merge_threshold: float = 0.8  # Cosine similarity to merge
    negativity_bias: float = 0.7       # Negative memories merge at this × threshold
    min_intensity_to_keep: float = 0.1 # Below this, memory is pruned

    # State
    last_encoding_tick: int = 0        # For cooldown enforcement
    is_sleeping: bool = False          # Current sleep state
    last_consolidation_tick: int = 0   # When consolidation last ran
```

---

## 4. Encoding System

### Intensity Score Computation

The intensity score determines whether an experience is "significant enough" to encode as a long-term memory. It's computed from the norn's current biochemistry:

```python
def compute_intensity(chemicals: dict, drives: list[float],
                      prev_drives: list[float]) -> float:
    """Compute encoding intensity from current biochemical state.

    Args:
        chemicals: Dict of chemical_id -> concentration (0.0 to 1.0)
        drives: Current drive values (20 floats)
        prev_drives: Drive values from previous tick

    Returns:
        Intensity score (0.0 to 1.0)
    """
    # Direct biochemical signals
    reward = chemicals.get(204, 0.0)
    punishment = chemicals.get(205, 0.0)
    adrenaline = chemicals.get(117, 0.0)
    pain_chem = chemicals.get(148, 0.0)

    # Drive deltas: sudden changes are significant
    drive_deltas = [abs(d - p) for d, p in zip(drives, prev_drives)]
    max_drive_delta = max(drive_deltas) if drive_deltas else 0.0

    # Drive desperation: extreme drives amplify encoding
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
```

### Valence Computation

Valence captures whether the experience was positive or negative:

```python
def compute_valence(chemicals: dict, drive_deltas: list[float]) -> float:
    """Compute emotional valence of current experience.

    Positive = good (reward, drives decreasing = needs being met)
    Negative = bad (punishment, pain, drives increasing = needs worsening)

    Returns:
        Valence (-1.0 to +1.0)
    """
    reward = chemicals.get(204, 0.0)
    punishment = chemicals.get(205, 0.0)
    pain = chemicals.get(148, 0.0)

    # Net biochemical signal
    biochem_valence = reward - punishment - pain * 0.5

    # Drive satisfaction signal
    # Negative delta = drive decreasing = need being met = positive
    avg_drive_delta = sum(drive_deltas) / len(drive_deltas) if drive_deltas else 0.0
    drive_valence = -avg_drive_delta * 2.0  # Inverted: decreasing drives = positive

    # Combined valence
    valence = max(-1.0, min(1.0, biochem_valence + drive_valence))

    return valence
```

### Arousal Computation

Arousal captures how activated/alert the norn was:

```python
def compute_arousal(chemicals: dict) -> float:
    """Compute arousal level from biochemistry.

    High arousal = alert, reactive, adrenaline-driven
    Low arousal = calm, resting, sleepy
    """
    adrenaline = chemicals.get(117, 0.0)
    sleepase = chemicals.get(112, 0.0)
    stress = chemicals.get(128, 0.0)

    arousal = min(1.0, adrenaline + stress * 0.5 - sleepase * 0.5)
    return max(0.0, arousal)
```

### Context Key Generation

The context key is the concatenated hidden state vectors from all four CfC modules at the moment of encoding. This IS the brain's processed understanding of the current moment: not the raw sensory input, but the brain's internal representation.

```python
def generate_context_key(brain: MultiLobeBrain) -> list[float]:
    """Snapshot the brain's hidden state as a memory key.

    The hidden state is the brain's compressed, abstract representation
    of "what's happening right now." Similar situations produce similar
    hidden states, enabling generalisation on retrieval.

    Returns:
        List of 239 floats (thalamus:70 + amygdala:52 + hippocampus:52 + prefrontal:65)
    """
    hidden_states = []
    for module_name in ["thalamus", "amygdala", "hippocampus", "prefrontal"]:
        h = brain.get_module_hidden_state(module_name)
        if h is not None:
            hidden_states.extend(h.squeeze().tolist())
        else:
            # Module hasn't been initialised yet
            hidden_states.extend([0.0] * brain.get_module_size(module_name))

    # L2-normalise so cosine similarity = dot product (faster retrieval)
    norm = sum(x * x for x in hidden_states) ** 0.5
    if norm > 1e-8:
        hidden_states = [x / norm for x in hidden_states]
    return hidden_states
```

### Location Zone Hashing

For the coarse retrieval filter, the norn's position is hashed into a zone grid:

```python
def compute_location_zone(posx: float, posy: float,
                           zone_width: int = 500,
                           zone_height: int = 500) -> int:
    """Hash (posx, posy) into a spatial zone index.

    The C3 world is roughly 0-58000 x 0-16000.
    With 500-pixel zones: 116 × 32 = 3712 possible zones.
    """
    zx = int(posx / zone_width)
    zy = int(posy / zone_height)
    return zx * 100 + zy  # Simple hash
```

### Encoding Trigger

```python
def maybe_encode(self, brain: MultiLobeBrain, chemicals: dict,
                 drives: list[float], prev_drives: list[float],
                 attn_winner: int, decn_winner: int,
                 posx: float, posy: float, tick: int) -> bool:
    """Check if current experience should be encoded as LTM.

    Returns True if a memory was encoded.
    """
    # Cooldown check: don't encode too frequently
    if tick - self.last_encoding_tick < self.encoding_cooldown:
        return False

    # Compute intensity
    intensity = compute_intensity(chemicals, drives, prev_drives)

    # Below threshold: not significant enough to remember
    if intensity < self.encoding_threshold:
        return False

    # Encode!
    valence = compute_valence(chemicals,
                              [d - p for d, p in zip(drives, prev_drives)])
    arousal = compute_arousal(chemicals)
    context_key = generate_context_key(brain)
    location_zone = compute_location_zone(posx, posy)

    record = MemoryRecord(
        memory_id=self.next_id,
        tick_created=tick,
        age_at_creation=tick,  # Simplified: real age from game
        context_key=context_key,
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
```

---

## 5. Retrieval System

### Two-Tier Retrieval

Retrieval runs every tick and is designed to be fast (~1-2ms for 200 memories).

**Tier 1: Coarse filter:** Reduce the candidate set using cheap categorical matches.

```python
def coarse_filter(self, attn_winner: int,
                  location_zone: int) -> list[MemoryRecord]:
    """Fast pre-filter: select memories that roughly match current context.

    Match criteria (OR logic: any match passes):
    - Same attention category (seeing the same type of thing)
    - Same location zone (being in the same place)

    Returns a shortlist of candidate memories.
    """
    candidates = []
    for mem in self.memories:
        if mem.attention_idx == attn_winner:
            candidates.append(mem)
        elif mem.location_zone == location_zone:
            candidates.append(mem)
    return candidates
```

**Tier 2: Fine similarity matching:** Cosine similarity on context keys.

```python
def retrieve(self, brain: MultiLobeBrain,
             attn_winner: int, location_zone: int) -> list[tuple[MemoryRecord, float]]:
    """Retrieve top-K matching memories for injection.

    Returns list of (memory, similarity_score) tuples, sorted by
    similarity × intensity (strongest match first).
    """
    current_key = generate_context_key(brain)
    current_key_tensor = torch.tensor(current_key)
    current_norm = torch.norm(current_key_tensor)

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
    matches = []
    for mem in candidates:
        mem_key = torch.tensor(mem.context_key)
        mem_norm = torch.norm(mem_key)
        if mem_norm < 1e-8:
            continue

        similarity = torch.dot(current_key_tensor, mem_key) / (current_norm * mem_norm)
        similarity = similarity.item()

        if similarity >= self.similarity_threshold:
            # Score combines similarity with memory intensity
            score = similarity * mem.intensity
            matches.append((mem, score))

    # Sort by score descending, take top K
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:self.max_retrievals]
```

### Injection

Retrieved memories are injected into the 6 LTM channels that feed into the Prefrontal via `tract_ltm_pfc`:

```python
def inject(self, matches: list[tuple[MemoryRecord, float]],
           tick: int) -> dict[str, float]:
    """Convert retrieved memories to injection channels.

    Returns dict with 6 float values for the LTM input channels.
    Updates recall_count and last_recall_tick on retrieved memories.
    """
    injection = {
        "mem1_valence": 0.0, "mem1_arousal": 0.0,
        "mem2_valence": 0.0, "mem2_arousal": 0.0,
        "mem3_valence": 0.0, "mem3_arousal": 0.0,
    }

    for i, (mem, score) in enumerate(matches):
        if i >= 3:
            break

        # Scale by similarity score (stronger match = stronger injection)
        injection[f"mem{i+1}_valence"] = mem.valence * score
        injection[f"mem{i+1}_arousal"] = mem.arousal * score

        # Update memory lifecycle
        mem.recall_count += 1
        mem.last_recall_tick = tick

    return injection
```

---

## 6. Sleep Consolidation

### Trigger

Consolidation runs once, atomically, when the norn enters a sleep state:

```python
def check_sleep_state(self, chemicals: dict) -> bool:
    """Detect sleep onset from biochemistry.

    The norn is sleeping when sleepase (chem 112) is high
    and Pre-REM sleep (chem 212) is present.
    """
    sleepase = chemicals.get(112, 0.0)
    pre_rem = chemicals.get(212, 0.0)
    return sleepase > 0.5 or pre_rem > 0.3
```

The bridge monitors sleep state transitions:

```python
# In the bridge poll loop
is_sleeping = self.ltm.check_sleep_state(chemicals)
if is_sleeping and not self.ltm.is_sleeping:
    # Sleep onset detected: run consolidation
    self.ltm.consolidate(current_tick)
self.ltm.is_sleeping = is_sleeping
```

### Consolidation Algorithm

```python
def consolidate(self, current_tick: int):
    """Run memory consolidation. Atomic: completes in one call.

    Steps:
    1. Group similar memories by context_key similarity
    2. Merge each group (with negativity bias)
    3. Prune weak memories
    4. Enforce capacity limit
    """
    if not self.memories:
        return

    # Step 1: Find similar memory groups
    # Use greedy clustering: pick an unassigned memory,
    # find all similar unassigned memories, form a group
    assigned = set()
    groups = []

    for i, mem_i in enumerate(self.memories):
        if i in assigned:
            continue

        group = [i]
        assigned.add(i)
        key_i = torch.tensor(mem_i.context_key)
        norm_i = torch.norm(key_i)

        if norm_i < 1e-8:
            continue

        for j, mem_j in enumerate(self.memories):
            if j in assigned or j <= i:
                continue

            key_j = torch.tensor(mem_j.context_key)
            norm_j = torch.norm(key_j)
            if norm_j < 1e-8:
                continue

            similarity = torch.dot(key_i, key_j) / (norm_i * norm_j)
            similarity = similarity.item()

            # Negativity bias: negative memories require higher
            # similarity to merge (they resist consolidation)
            threshold = self.consolidation_merge_threshold
            if mem_i.valence < 0 or mem_j.valence < 0:
                threshold = threshold / self.negativity_bias
                # e.g., 0.8 / 0.7 = 1.14: effectively can never merge
                # unless almost identical

            if similarity >= threshold:
                group.append(j)
                assigned.add(j)

        if len(group) > 1:
            groups.append(group)

    # Step 2: Merge each group
    for group_indices in groups:
        group_memories = [self.memories[i] for i in group_indices]
        merged = self._merge_memories(group_memories)

        # Remove originals (in reverse order to preserve indices)
        for i in sorted(group_indices, reverse=True):
            self.memories.pop(i)

        # Add merged memory
        self.memories.append(merged)

    # Step 3: Prune weak memories
    self.memories = [
        m for m in self.memories
        if m.intensity >= self.min_intensity_to_keep
        or m.recall_count > 0  # Never prune a recalled memory
        or m.source == "inherited"  # Never prune inherited instincts
    ]

    # Step 4: Enforce capacity
    while len(self.memories) > self.capacity:
        self._evict_weakest()

    self.last_consolidation_tick = current_tick


def _merge_memories(self, memories: list[MemoryRecord]) -> MemoryRecord:
    """Merge a group of similar memories into one consolidated memory.

    Strategy:
    - context_key: weighted average by intensity
    - valence: intensity-weighted average (strongest memory dominates)
    - intensity: max of group (consolidated memories are stronger)
    - arousal: intensity-weighted average
    - attention_idx, action_idx: mode (most common)
    - recall_count: sum
    """
    total_intensity = sum(m.intensity for m in memories)

    # Weighted average of context keys
    merged_key = [0.0] * len(memories[0].context_key)
    for m in memories:
        weight = m.intensity / total_intensity
        for k in range(len(merged_key)):
            merged_key[k] += m.context_key[k] * weight

    # Intensity-weighted averages
    merged_valence = sum(m.valence * m.intensity for m in memories) / total_intensity
    merged_arousal = sum(m.arousal * m.intensity for m in memories) / total_intensity

    # Consolidated intensity = max × boost (merging strengthens memory)
    merged_intensity = min(1.0, max(m.intensity for m in memories) * 1.1)

    # Mode for categorical fields
    from collections import Counter
    attn_mode = Counter(m.attention_idx for m in memories).most_common(1)[0][0]
    action_mode = Counter(m.action_idx for m in memories).most_common(1)[0][0]
    location_mode = Counter(m.location_zone for m in memories).most_common(1)[0][0]

    return MemoryRecord(
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
```

### Negativity Bias Detail

The negativity bias operates by raising the merge threshold for negative memories:

- **Positive memories (valence > 0):** Merge threshold = 0.8 (normal). Five "food was good here" memories easily consolidate into one "food is good here" memory.
- **Negative memories (valence < 0):** Merge threshold = 0.8 / 0.7 = ~1.14. Since cosine similarity maxes at 1.0, this means negative memories **almost never merge**: each negative experience stays as a distinct, vivid episode. The norn remembers each grendel attack separately.
- **Mixed groups (some positive, some negative):** The negative threshold applies if ANY memory in the pair is negative. Negative memories don't get "averaged out" by nearby positive ones.

This mirrors human psychology: pleasant days blur together, but you remember each individual bad experience in detail.

---

## 7. Memory Capacity Management

### Eviction Strategy

When the memory bank exceeds capacity, the weakest memory is evicted:

```python
def _evict_weakest(self):
    """Remove the single weakest memory.

    Weakness score = intensity × recency_factor × recall_factor
    Lower score = more likely to be evicted.
    """
    if not self.memories:
        return

    weakest_idx = 0
    weakest_score = float('inf')

    for i, mem in enumerate(self.memories):
        # Inherited instincts are protected
        if mem.source == "inherited":
            continue

        # Recency: memories that haven't been recalled recently are weaker
        ticks_since_recall = (self.last_consolidation_tick - mem.last_recall_tick
                              if mem.last_recall_tick > 0
                              else self.last_consolidation_tick - mem.tick_created)
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
```

---

## 8. Persistence

### Save Format

The memory bank serialises to JSON for human readability and debugging:

```python
def save(self, path: str):
    """Save memory bank to JSON file."""
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
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load(self, path: str):
    """Load memory bank from JSON file."""
    with open(path) as f:
        data = json.load(f)
    self.creature_id = data["creature_id"]
    self.capacity = data.get("capacity", 200)
    self.next_id = data.get("next_id", 0)
    self.encoding_threshold = data.get("encoding_threshold", 0.4)
    self.encoding_cooldown = data.get("encoding_cooldown", 20)
    self.similarity_threshold = data.get("similarity_threshold", 0.6)
    self.consolidation_merge_threshold = data.get("consolidation_merge_threshold", 0.8)
    self.negativity_bias = data.get("negativity_bias", 0.7)
    self.memories = [MemoryRecord(**m) for m in data["memories"]]
```

### File Location

```
phase2-bridge/
    memory_banks/
        {creature_id}_memories.json     # Per-creature memory bank
```

### Auto-save

The memory bank auto-saves every N ticks (configurable, default 500) and on bridge shutdown.

---

## 9. Offspring Inheritance

### Instinct Transfer

When a new norn is born, it can inherit attenuated versions of its parents' strongest memories as "instincts":

```python
def create_offspring_memories(parent_banks: list[MemoryBank],
                               inheritance_factor: float = 0.3,
                               max_inherited: int = 10) -> list[MemoryRecord]:
    """Create inherited instinct memories for a new norn.

    Args:
        parent_banks: Memory banks of parent creatures
        inheritance_factor: Attenuation factor (0.3 = 30% of original intensity)
        max_inherited: Maximum number of inherited memories

    Returns:
        List of attenuated MemoryRecords marked as "inherited"
    """
    # Collect all parent memories, sorted by intensity
    all_parent_memories = []
    for bank in parent_banks:
        all_parent_memories.extend(bank.memories)

    # Sort by intensity × |valence| (strongest emotional memories inherited)
    all_parent_memories.sort(
        key=lambda m: m.intensity * abs(m.valence),
        reverse=True
    )

    inherited = []
    for mem in all_parent_memories[:max_inherited]:
        instinct = MemoryRecord(
            memory_id=-1,  # Will be reassigned
            tick_created=0,
            age_at_creation=0,
            context_key=list(mem.context_key),  # Same context key
            attention_idx=mem.attention_idx,
            action_idx=mem.action_idx,
            location_zone=mem.location_zone,
            valence=mem.valence,                 # Same emotional charge
            intensity=mem.intensity * inheritance_factor,  # Attenuated
            arousal=mem.arousal * inheritance_factor,
            drive_snapshot=[0.0] * 20,           # No drive context
            recall_count=0,
            last_recall_tick=0,
            consolidated=True,                   # Already consolidated
            source="inherited",
        )
        inherited.append(instinct)

    return inherited
```

### Instinct Behaviour

Inherited memories function identically to experiential memories during retrieval. The key difference:

- **Lower intensity** (30% of parent's): the instinct is a vague feeling, not a vivid memory
- **Protected from eviction**: instincts are never evicted by capacity management
- **Can be reinforced**: if the norn's own experience produces a similar memory, the inherited instinct's intensity increases (the instinct was "confirmed" by experience)
- **Can be overridden**: if the norn has many positive experiences where the instinct predicted danger, the positive memories will outnumber and outscore the inherited warning

This is biologically faithful: instinctive fear of snakes can be overridden by repeated safe exposure, but never fully eliminated.

---

## 10. Performance Budget

### Per-tick Retrieval Cost

With 200 memories and the two-tier system:

| Operation | Estimated time |
|-----------|---------------|
| Coarse filter (scan 200 records, compare 2 ints each) | ~0.05ms |
| Fine matching (cosine similarity on ~30 candidates × 239-dim vectors) | ~0.5ms |
| Injection (populate 6 floats) | ~0.01ms |
| **Total retrieval** | **~0.6ms** |

### Per-tick Encoding Cost

| Operation | Estimated time |
|-----------|---------------|
| Intensity computation (arithmetic on ~10 values) | ~0.01ms |
| Context key generation (read 4 hidden state tensors) | ~0.1ms |
| Memory creation + capacity check | ~0.05ms |
| **Total encoding (when triggered)** | **~0.2ms** |

### Consolidation Cost (at sleep onset)

| Operation | Estimated time |
|-----------|---------------|
| Pairwise similarity (200² = 40,000 comparisons × 239-dim) | ~30ms |
| Merging + pruning | ~1ms |
| **Total consolidation** | **~31ms** |

Consolidation is a one-time cost at sleep onset, not per-tick. 31ms is acceptable for an event that happens a few times per norn lifetime.

### Optimisation: Pre-computed Norms

To speed up cosine similarity, pre-compute and cache the L2 norm of each memory's context key:

```python
# At encoding time
mem.context_key_norm = torch.norm(torch.tensor(mem.context_key)).item()

# At retrieval time (avoid recomputing)
similarity = dot(current_key, mem_key) / (current_norm * mem.context_key_norm)
```

---

## 11. File Structure

### New Files

```
phase2-bridge/
    ltm.py                          # MemoryRecord, MemoryBank, encoding, retrieval,
                                    #   consolidation, persistence, inheritance
    memory_banks/                    # Directory for per-creature memory files
        .gitkeep
    tests/
        test_ltm.py                 # Unit tests for LTM system
```

### Modified Files

```
phase2-bridge/
    brain_bridge_client.py          # Integrate LTM encode/retrieve into poll loop
```

---

## 12. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Context keys don't generalise well (too specific, misses relevant matches) | High | Medium | Monitor retrieval hit rate. If too low, reduce similarity_threshold or increase coarse filter breadth. Can also use PCA-reduced keys for retrieval. |
| Encoding triggers too frequently, filling bank with low-value memories | Medium | Medium | Tune encoding_threshold and encoding_cooldown. Start conservative (high threshold, long cooldown), relax as system proves stable. |
| Cosine similarity too expensive at scale | Low | Low | 200 memories × 239 dims is small. If needed: quantise keys to int8, use numpy batch matmul, or add spatial indexing. |
| Sleep consolidation merges memories that shouldn't be merged | Medium | Low | Negativity bias already protects negative memories. Monitor via dashboard memory inspector. Raise merge_threshold if over-merging observed. |
| Inherited instincts too strong/weak | Low | Medium | inheritance_factor is tunable. Start at 0.3, adjust based on observed offspring behaviour. |

---

## 13. Forward Compatibility

### Phase 4C (Emotional Hierarchy)
The Amygdala's output already modulates the Prefrontal's decisions. Phase 4C adds intensity-based gating that determines how much the Amygdala dominates vs. the Prefrontal deliberates. The LTM injection interacts with this: a strong memory injection amplifies the Amygdala's influence, making the norn more reactive. This is implemented as a scaling factor on `tract_amyg_pfc`, not a change to the LTM system.

### Phase 4D (Language)
Memories could be expressed through language: "scared grendel" when a negative grendel memory is retrieved. The bridge-side LLM translator can access the current LTM retrieval results to generate contextual speech. No LTM changes needed.

### Phase 5 (Genetic Evolution)
The MemoryBank parameters (encoding_threshold, similarity_threshold, capacity, negativity_bias) are all candidates for genetic parameterisation. A norn born with low encoding_threshold encodes more memories (more sensitive, better memory, but bank fills faster). A norn with high negativity_bias has more vivid trauma memories. These become heritable personality traits.
