# Stimulus-Driven Attention Override

**Date:** 2026-04-01
**Status:** Approved
**Scope:** PythonBrain C++ + nornbrain_cfc_v2.py

---

## Problem

The CfC brain's attention system doesn't respond to external stimuli. In the SVRule brain, when the hand pats a norn or a creature interacts with it, `handleStimulus()` writes directly to the noun lobe, and SVRule dendrites wire noun → attention: so attention snaps to whatever caused the stimulus. The CfC brain receives noun lobe data but doesn't use it to drive attention, resulting in a norn that never visibly focuses on things interacting with it (no green arrow on the hand, no attention shift on creature contact).

## Solution: Hard Override (Phase A)

### C++ Changes (PythonBrain)

**PythonBrain.h**: add stimulus queue:

```cpp
struct PendingStimulus {
    int noun_id;     // agent category that caused stimulus (-1 = none)
    int verb_id;     // action that was performed (-1 = none)
    float strength;  // stimulus strength (0.0–1.0)
};
std::vector<PendingStimulus> pending_stimuli_;
```

**PythonBrain.cpp**: two changes:

1. Add `handleStimulus(c2eStim&)` override that pushes to queue, then calls base:
   ```cpp
   void PythonBrain::handleStimulus(c2eStim& stim) {
       if (stim.noun_id >= 0) {
           pending_stimuli_.push_back({stim.noun_id, stim.verb_id, stim.noun_amount});
       }
       // Base class handles biochemistry (drive chemicals, resp lobe)
   }
   ```
   Note: `handleStimulus` is on `c2eCreature`, not `c2eBrain`. PythonBrain cannot override it directly. Instead, PythonBrain exposes a `pushStimulus()` method, and `c2eCreature::handleStimulus()` calls it when the brain is a PythonBrain. Alternatively, gather stimulus data from the noun lobe state that `handleStimulus` already writes.

   **Revised approach:** Since `handleStimulus()` already writes to the noun lobe (`nounlobe->setNeuronInput(stim.noun_id, stim.noun_amount)`), and `gather_inputs()` already reads all lobe neuron inputs: the noun signal IS already delivered. The problem is Python ignores it. However, noun lobe inputs are transient (only set for the tick the stimulus fires). To avoid timing issues, we add an explicit stimulus event queue on PythonBrain that `c2eCreature` can push to.

   **Final approach:** Add a public `pushStimulus(int noun_id, int verb_id, float strength)` method on PythonBrain. In `c2eCreature::handleStimulus(c2eStim&)`, after the existing logic, check if the brain is a PythonBrain and call `pushStimulus()`. `gather_inputs()` drains the queue into `inputs["stimuli"]`.

2. `gather_inputs()`: drain queue into inputs dict:
   ```cpp
   py::list stim_list;
   for (auto& s : pending_stimuli_) {
       py::dict sd;
       sd["noun"] = s.noun_id;
       sd["verb"] = s.verb_id;
       sd["strength"] = s.strength;
       stim_list.append(sd);
   }
   pending_stimuli_.clear();
   inputs["stimuli"] = stim_list;
   ```

### Python Changes (nornbrain_cfc_v2.py)

Add stimulus override state:

```python
_stimulus_attn_category = -1   # Category to force attention to
_stimulus_ttl = 0              # Ticks remaining for override
STIMULUS_OVERRIDE_TICKS = 5    # Duration of hard lock
```

In `tick()`, after CfC brain processes but before final attention selection:

```python
stimuli = inputs.get("stimuli", [])
if stimuli:
    latest = stimuli[-1]  # Most recent stimulus wins
    if latest["noun"] >= 0 and latest["noun"] < 40:
        _stimulus_attn_category = latest["noun"]
        _stimulus_ttl = STIMULUS_OVERRIDE_TICKS

if _stimulus_ttl > 0:
    attn_win = _stimulus_attn_category
    _stimulus_ttl -= 1
```

### Telemetry

Add to UDP telemetry packet:
```python
"stimulus_override": _stimulus_ttl > 0,
"stimulus_category": _stimulus_attn_category if _stimulus_ttl > 0 else -1,
```

## Future Goal: Soft Bias (Phase B: not implemented now)

Instead of a hard TTL cutoff, Phase B would:

1. Track per-category stimulus recency as a float array (40 entries, one per category)
2. When a stimulus fires, set `stimulus_recency[category] = 1.0`
3. Each tick, decay all entries: `stimulus_recency *= 0.85` (configurable)
4. Add decayed values as weighted boost to attention scores: `final_attn[i] += STIMULUS_BIAS_WEIGHT * stimulus_recency[i]`
5. This lets the CfC brain "remember" recent interactions without being locked: the bias fades naturally over ~20 ticks

Phase B would replace Phase A's hard override entirely: the TTL mechanism becomes unnecessary when soft decay handles both the immediate snap and the gradual release.

## Files Modified

| File | Change |
|------|--------|
| `openc2e/src/openc2e/creatures/PythonBrain.h` | Add `PendingStimulus` struct, `pending_stimuli_` vector, `pushStimulus()` method |
| `openc2e/src/openc2e/creatures/PythonBrain.cpp` | Implement `pushStimulus()`, drain queue in `gather_inputs()` |
| `openc2e/src/openc2e/creatures/CreatureAI.cpp` | In `handleStimulus(c2eStim&)`, push to PythonBrain if active |
| `openc2e/tools/nornbrain_cfc_v2.py` | Add stimulus override logic in `tick()`, telemetry fields |

## What Doesn't Change

- Decision system (decn output): untouched
- RL training: untouched
- Drive-gated visibility (Layer 1): still active, stimulus override takes priority when TTL > 0
- CfC network weights/architecture: untouched
- Existing telemetry fields: preserved, new fields added
