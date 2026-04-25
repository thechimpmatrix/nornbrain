# Phase 4C: Emotional Hierarchy & Integration: Specification

**Date:** 2026-03-30
**Branch:** `feature/multi-lobe-cfc`
**Depends on:** Phase 4A (Multi-Lobe CfC), Phase 4B (LTM System)

---

## 0. Document Purpose

This document specifies the emotional hierarchy system that governs how the multi-lobe CfC brain resolves conflicts between emotional impulse and executive deliberation. The core principle: **norns are primitive, emotional creatures.** At low intensity they can exhibit something resembling deliberation; at high intensity, emotion overwhelms everything.

This phase also covers:
- The intensity-based gating mechanism between Amygdala and Prefrontal
- Habit formation as an emergent property of the Amygdala's slow-forget dynamics
- The RL training adaptation for the emotional hierarchy
- Dashboard visualisation for multi-lobe state + LTM inspection
- Personality emergence from architectural variation

**What this document does NOT cover:**
- CfC module internals (see Phase 4A)
- LTM encoding/retrieval mechanics (see Phase 4B)
- Language output (see Phase 4D)

---

## 1. Goals and Success Criteria

### Primary Goal
Implement an emotion-dominant behavioural system where the norn's current biochemical intensity determines the balance of power between reactive emotional processing (Amygdala) and deliberative executive function (Prefrontal). The norn should be visibly impulsive under stress and more varied/exploratory when calm.

### Success Criteria
1. **SC1: Observable emotional dominance:** A norn under high stress (pain, fear, adrenaline) shows reduced action diversity: it fixates on a single behaviour (flee, eat, rest) rather than exploring options.
2. **SC2: Calm exploration:** A norn with low drive pressure and no threats shows varied behaviour: it wanders, investigates objects, approaches other creatures.
3. **SC3: LTM amplification:** When a strong negative LTM is retrieved, the norn's behaviour visibly shifts toward avoidance even if current drives would suggest approach.
4. **SC4: Habit formation:** Actions that are repeatedly reinforced by positive biochemistry become more likely over time without conscious "decision": the norn develops behavioural routines.
5. **SC5: Personality variation:** Two norns with different genome parameters (amygdala size, prefrontal size, tract strengths) exhibit measurably different behavioural profiles.
6. **SC6: Dashboard visibility:** The dashboard shows per-module activation levels, current emotional intensity tier, active LTM retrievals, and a personality profile summary.

### Non-Goals
- Explicit mood system (mood emerges from Amygdala state + biochemistry)
- Social emotion (empathy, jealousy): future work
- Player-facing emotion indicators in-game (dashboard only)

---

## 2. Emotional Intensity Tiers

### Tier Definitions

The norn's current emotional intensity determines which brain modules dominate behaviour:

| Tier | Intensity range | Behavioural character | Module dominance |
|------|----------------|----------------------|-----------------|
| **EXTREME** | 0.85 - 1.0 | Panic/overwhelm. Single fixated behaviour. LTM floods input. | Amygdala + LTM completely dominate. PFC output nearly suppressed. |
| **HIGH** | 0.6 - 0.85 | Stressed, reactive, impulsive. Limited action repertoire. | Amygdala strongly dominates. PFC modulates weakly. |
| **MODERATE** | 0.3 - 0.6 | Alert but not panicked. Some deliberation possible. | Amygdala and PFC compete. Drives and context both influence. |
| **LOW** | 0.0 - 0.3 | Calm, content, exploratory. Widest action diversity. | PFC has strongest relative influence. Habits and curiosity drive behaviour. |

### Intensity Computation

Reuses the same intensity computation from Phase 4B encoding, but applied every tick (not just for encoding triggers):

```python
def compute_current_intensity(chemicals: dict, drives: list[float],
                               prev_drives: list[float],
                               ltm_arousal: float) -> float:
    """Compute the norn's current emotional intensity.

    This determines the tier and the amygdala-prefrontal balance.

    Args:
        chemicals: Current chemical concentrations
        drives: Current drive values
        prev_drives: Previous tick drive values
        ltm_arousal: Maximum arousal from retrieved LTM memories

    Returns:
        Intensity (0.0 to 1.0)
    """
    # Base intensity from biochemistry (same as LTM encoding)
    base = compute_intensity(chemicals, drives, prev_drives)

    # LTM arousal amplification
    # Retrieved memories can push intensity higher
    ltm_boost = ltm_arousal * 0.3  # LTM can add up to 0.3 intensity

    intensity = min(1.0, base + ltm_boost)
    return intensity
```

---

## 3. Amygdala-Prefrontal Gating

### The Core Mechanism

The emotional hierarchy is implemented as a **gating factor** on the `tract_amyg_pfc` projection. At high intensity, the Amygdala's signal to the Prefrontal is amplified, effectively overwhelming the PFC's own processing. At low intensity, the Amygdala signal is attenuated, giving the PFC more room to deliberate.

This is NOT an override: the Amygdala doesn't bypass the PFC. It floods the PFC with such a strong emotional signal that the PFC's output is dominated by the emotional input. The PFC still "decides," but its decision is effectively dictated by the Amygdala. This is biologically accurate: the amygdala modulates prefrontal activity, it doesn't replace it.

### Implementation

```python
class EmotionalGate(nn.Module):
    """Intensity-dependent gating of Amygdala → Prefrontal signal.

    At high intensity: amygdala signal is amplified (up to 3x)
    At low intensity: amygdala signal is attenuated (down to 0.5x)

    The gate also modulates LTM injection: strong memories at high
    intensity become overwhelming.
    """

    def __init__(self, amygdala_dim: int = 16, ltm_dim: int = 6):
        super().__init__()
        self.amygdala_dim = amygdala_dim
        self.ltm_dim = ltm_dim

        # Configurable gain curve parameters (genetic)
        self.amygdala_gain_low = 0.5    # Gain at intensity=0
        self.amygdala_gain_high = 3.0   # Gain at intensity=1
        self.ltm_gain_low = 0.3
        self.ltm_gain_high = 2.0

    def compute_gains(self, intensity: float) -> tuple[float, float]:
        """Compute amygdala and LTM gain factors from current intensity."""
        # Linear interpolation between low and high gain
        amyg_gain = (self.amygdala_gain_low +
                     (self.amygdala_gain_high - self.amygdala_gain_low) * intensity)
        ltm_gain = (self.ltm_gain_low +
                    (self.ltm_gain_high - self.ltm_gain_low) * intensity)
        return amyg_gain, ltm_gain

    def forward(self, amygdala_output: torch.Tensor,
                ltm_injection: torch.Tensor,
                intensity: float) -> tuple[torch.Tensor, torch.Tensor]:
        """Apply emotional gating.

        Args:
            amygdala_output: (1, 16) amygdala motor neuron values
            ltm_injection: (1, 6) LTM injection channels
            intensity: Current emotional intensity (0-1)

        Returns:
            Gated (amygdala_output, ltm_injection)
        """
        amyg_gain, ltm_gain = self.compute_gains(intensity)
        return amygdala_output * amyg_gain, ltm_injection * ltm_gain
```

### Integration into Brain Tick

```python
# In MultiLobeBrain.tick():

# 1. Run Thalamus, Amygdala, Hippocampus (parallel)
thal_out = self.thalamus(thalamus_input, thal_hidden)
amyg_out = self.amygdala(amygdala_input, amyg_hidden)
hipp_out = self.hippocampus(hippocampus_input, hipp_hidden)

# 2. Compute current intensity
intensity = compute_current_intensity(chemicals, drives, prev_drives, ltm_arousal)

# 3. Apply emotional gate
gated_amyg, gated_ltm = self.emotional_gate(amyg_out, ltm_injection, intensity)

# 4. Assemble PFC input with gated signals
pfc_input = concat(
    tract_thal_pfc(thal_out),        # Attention signal (ungated)
    tract_amyg_pfc(gated_amyg),      # GATED emotional signal
    tract_hipp_pfc(hipp_out),        # Context signal (ungated)
    tract_driv_pfc(drives),          # Raw drives
    tract_verb_pfc(verb),            # Action history
    tract_noun_pfc(noun),            # Category history
    tract_resp_pfc(resp),            # Response history
    tract_stim_pfc(stim),            # Stimulus
    tract_chem_pfc(chemicals_16),    # Biochemistry
    tract_ltm_pfc(gated_ltm),        # GATED LTM injection
)

# 5. Run Prefrontal
decn_out = self.prefrontal(pfc_input, pfc_hidden)
```

### Behavioural Effects by Tier

**EXTREME (0.85-1.0):**
- Amygdala gain: ~2.8x. The emotional signal is nearly 3x its normal strength.
- LTM gain: ~1.7x. Retrieved trauma memories hit with amplified force.
- PFC receives overwhelming emotional input. Its decision output is effectively determined by the Amygdala's valence: negative emotion → flee/freeze, positive → approach/consume.
- Action diversity collapses to 1-2 actions.
- Example: Grendel attack. Pain + fear + adrenaline spike. Amygdala screams "DANGER." PFC output: retreat. Every tick. Until intensity drops.

**HIGH (0.6-0.85):**
- Amygdala gain: ~2.0x.
- PFC can weakly modulate: if drives are extreme enough (hunger > 0.9), the PFC might produce "eat" despite moderate fear.
- Action diversity: 2-4 actions.
- Example: Moderately hungry near a known food source. The norn approaches food but startles easily if anything unexpected happens.

**MODERATE (0.3-0.6):**
- Amygdala gain: ~1.2x. Emotional signal is present but not overwhelming.
- PFC and Amygdala roughly balance. Drives, context, and emotion all contribute to decisions.
- Action diversity: 5-8 actions.
- Example: Mildly bored, walking around. The norn investigates nearby objects, occasionally eats, sometimes approaches other creatures.

**LOW (0.0-0.3):**
- Amygdala gain: ~0.5x. Emotional signal is subdued.
- PFC dominates relative to Amygdala. Behaviour is driven by habits, mild drives, and curiosity.
- Action diversity: maximum. The norn explores, plays, interacts.
- Example: Well-fed, safe, comfortable norn. It wanders, pushes buttons, looks at things, occasionally rests.

---

## 4. Habit Formation

### Mechanism

Habits are NOT a separate module. They emerge from two properties of the existing architecture:

1. **Amygdala's slow-forget time constants:** The Amygdala CfC is initialised with slow-forgetting dynamics (high recurrent_command_synapses, negative time_b bias). When a state-action pair is repeatedly reinforced (positive reward), the Amygdala's hidden state develops a persistent activation pattern for that context. The Amygdala "remembers" that this situation calls for this action.

2. **RL reinforcement of Amygdala-PFC pathway:** Through REINFORCE training, the tract weights from Amygdala to PFC strengthen for repeatedly-rewarded state-action pairs. The Amygdala signal for "I've done this before and it felt good" becomes a strong input to the PFC, biasing the decision without explicit deliberation.

### Observable Habit Behaviour

- **Early life:** The norn takes varied actions, explores. Each action is somewhat random, driven by initial weights.
- **After repeated reinforcement:** The norn develops routines. It reliably eats when hungry, retreats from threats, approaches friendly creatures. These behaviours emerge faster and with less "hesitation" (fewer ticks of fluctuating outputs before settling on an action).
- **Habit inertia:** Well-established habits resist change. A norn that has learned "push button → good" will continue pushing buttons even after the reward stops, until enough unrewarded attempts weaken the association.

### Habit Strength Indicator

For the dashboard, habit strength can be estimated by measuring the Amygdala's output consistency:

```python
def estimate_habit_strength(amygdala_history: list[np.ndarray],
                            window: int = 50) -> float:
    """Estimate habit strength from recent Amygdala output consistency.

    High consistency = strong habits (same emotional response every time)
    Low consistency = no established habits (emotional response varies)

    Args:
        amygdala_history: Last N amygdala output vectors
        window: Number of recent outputs to consider

    Returns:
        Habit strength (0.0 to 1.0)
    """
    recent = amygdala_history[-window:]
    if len(recent) < 10:
        return 0.0

    # Compute variance across recent outputs
    stacked = np.stack(recent)
    mean_variance = np.mean(np.var(stacked, axis=0))

    # Low variance = strong habits, high variance = no habits
    # Map through inverse sigmoid
    strength = 1.0 / (1.0 + mean_variance * 10.0)
    return float(strength)
```

---

## 5. Personality Emergence

### Architectural Personality Axes

Different genome configurations produce different behavioural profiles. These are not "personality types" applied from outside: they emerge from the norn's brain architecture:

| Genome parameter | Low value → personality | High value → personality |
|-----------------|------------------------|-------------------------|
| Amygdala inter_neurons | Emotionally muted, calm | Emotionally rich, reactive |
| Amygdala recurrent_command_synapses | Quick to forget emotions | Lingers on feelings |
| Prefrontal inter_neurons | Impulsive, reactive | More deliberative |
| tract_amyg_pfc connections | Emotions weakly influence decisions | Emotions strongly drive decisions |
| tract_hipp_pfc connections | Context-blind (lives in the moment) | Context-aware (considers situation) |
| LTM encoding_threshold (Phase 4B) | Encodes only extreme events | Encodes many events (rich memory) |
| LTM negativity_bias (Phase 4B) | Balanced memory | Vivid negative memories, anxious |
| EmotionalGate amygdala_gain_high | Moderate emotional peaks | Extreme emotional peaks (panic-prone) |

### Example Personality Profiles

**"The Anxious Norn":**
- Large Amygdala (inter=32), high recurrence
- Small Prefrontal (inter=24)
- Strong tract_amyg_pfc (connections=12)
- Low LTM encoding_threshold (0.3): remembers everything
- High negativity_bias (0.9): negative memories never fade
- Result: Jumpy, avoidant, strong trauma responses, slow to explore

**"The Bold Explorer":**
- Small Amygdala (inter=16), low recurrence
- Large Prefrontal (inter=40)
- Weak tract_amyg_pfc (connections=4)
- High LTM encoding_threshold (0.6): only remembers extreme events
- Low negativity_bias (0.5): negative memories consolidate normally
- Result: Curious, exploratory, approaches novel objects, recovers quickly from scares

**"The Creature of Habit":**
- Medium Amygdala with very high recurrence (recurrent_command_synapses=20)
- Medium Prefrontal
- Strong tract_amyg_pfc
- Result: Develops strong routines quickly, resistant to behavioural change, reliable but inflexible

These profiles are not assigned: they emerge from the genome and life experience. Two norns with identical genomes but different life experiences will still differ, because their LTM banks and learned weights will diverge.

---

## 6. Training Adaptation

### RL with Emotional Hierarchy

The REINFORCE training step needs adaptation for the gated architecture:

```python
def train_rl_step(self, brain_input, reward: float,
                  intensity: float, lr: float = 0.001) -> float:
    """One step of online RL with emotional gating.

    The reward signal is modulated by intensity:
    - At high intensity, RL updates are stronger (emotional experiences
      are more impactful on learning)
    - At low intensity, RL updates are weaker (calm experiences
      produce gentler learning)

    This mirrors biological learning: emotionally charged events
    produce stronger synaptic changes (via noradrenaline/cortisol).
    """
    # Intensity-modulated learning rate
    effective_lr = lr * (0.5 + intensity)  # Range: 0.5x to 1.5x base lr

    # ... standard REINFORCE with effective_lr ...
```

### Per-Module Gradient Scaling

During RL training, different modules should learn at different rates:

```python
# After loss.backward(), scale gradients per module
gradient_scales = {
    "thalamus": 1.0,       # Normal learning for attention
    "amygdala": 1.5,       # Faster emotional learning
    "hippocampus": 0.5,    # Slower contextual learning
    "prefrontal": 1.0,     # Normal decision learning
    "tracts": 0.8,         # Slightly conservative tract updates
}

for name, module in self.named_modules():
    for key, scale in gradient_scales.items():
        if key in name:
            for param in module.parameters():
                if param.grad is not None:
                    param.grad *= scale
```

This reflects biological learning rates: the amygdala forms associations quickly (one-trial learning for threats), while the hippocampus learns more gradually.

---

## 7. Dashboard Visualisation

### Multi-Lobe Display

The Phase 1 dashboard (`dashboard.html` + `server.py`) needs updates to show the multi-lobe architecture:

**New panels:**

1. **Module Activation View:**
   - Four stacked horizontal bars showing activation magnitude per module
   - Colour-coded: Thalamus (blue), Amygdala (red), Hippocampus (green), Prefrontal (purple)
   - Each bar shows the mean absolute activation of the module's hidden state

2. **Emotional Intensity Gauge:**
   - Vertical gauge showing current intensity (0-1)
   - Colour bands for tiers: LOW (green), MODERATE (yellow), HIGH (orange), EXTREME (red)
   - Current tier label displayed

3. **LTM Retrieval Panel:**
   - Shows the 0-3 currently active memory retrievals
   - Per memory: valence (colour bar red/green), intensity, attention label, similarity score
   - "No memories" displayed when no retrievals active

4. **Personality Profile:**
   - Radar chart with axes: Emotional Reactivity, Deliberation, Memory Richness, Habit Strength, Negativity Bias
   - Updated slowly (every 100 ticks) from genome params + observed behaviour

5. **Memory Bank Overview:**
   - Total memory count / capacity
   - Breakdown: positive vs negative vs inherited
   - Last encoding event details
   - Last consolidation stats

### WebSocket Data Extension

The existing WebSocket protocol sends a JSON payload per tick. Add:

```python
ws_data = {
    # ... existing fields ...

    # Multi-lobe additions
    "module_activations": {
        "thalamus": float,      # Mean |activation|
        "amygdala": float,
        "hippocampus": float,
        "prefrontal": float,
    },
    "emotional_intensity": float,
    "emotional_tier": str,          # "LOW" / "MODERATE" / "HIGH" / "EXTREME"
    "amygdala_gain": float,
    "ltm_retrievals": [
        {"valence": float, "arousal": float, "attention_label": str,
         "similarity": float} | null,
        ...  # 3 slots
    ],
    "memory_count": int,
    "memory_capacity": int,
    "habit_strength": float,
}
```

---

## 8. File Structure

### New Files

```
phase2-bridge/
    emotional_gate.py               # EmotionalGate class, intensity computation,
                                    #   tier classification
    tests/
        test_emotional_gate.py      # Unit tests for emotional gating
```

### Modified Files

```
phase1-prototype/
    multi_lobe_brain.py             # Integrate EmotionalGate into tick()
    server.py                       # Add new WebSocket data fields
    dashboard.html                  # Add multi-lobe panels
```

---

## 9. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Emotional gating too aggressive: norn is always in "panic mode" | High | Medium | Start with conservative gain curve (amygdala_gain_high=2.0 instead of 3.0). Monitor intensity distribution over time. Adjust if >50% of ticks are HIGH/EXTREME. |
| Habits form too quickly: norn gets stuck in loops | Medium | Medium | The RL gradient scaling (amygdala=1.5x) can be reduced. Monitor action diversity metric over time. |
| Personality emergence not measurable | Low | Medium | Define quantitative personality metrics (action entropy, fear response latency, exploration rate). Measure across norns with different genomes. |
| Dashboard performance degradation from additional data | Low | Low | New data fields are small (< 200 bytes per tick). WebSocket bandwidth is not a concern. |

---

## 10. Forward Compatibility

### Phase 4D (Language)
The emotional intensity tier directly influences speech output. At EXTREME intensity, the norn's speech should be fragmented, repetitive ("no no no!"). At LOW intensity, speech is more varied and descriptive. The language system can read the current tier to adjust utterance generation.

### Phase 5 (Genetic Evolution)
All EmotionalGate parameters (gain curves), gradient scaling factors, and the personality-relevant genome parameters are already structured for genetic inheritance. Crossover and mutation on these parameters produces offspring with naturally varied personality profiles. Selection pressure (survival rate) will favour personality profiles suited to the game environment.
