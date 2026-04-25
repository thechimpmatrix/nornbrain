# NB Instinct System: Modular Pre-Training from Genome Definitions


**Goal:** Replace the hardcoded additive-bias instinct hack with a modular instinct definition system that pre-trains the CfC brain weights, so norns are born knowing how to eat when hungry, retreat when scared, and rest when tired: encoded in the neural network itself, not bolted on top.

**Architecture:** A standalone `instincts.py` module defines instinct rules as structured data (drive → attention → decision mappings). A `pretrain_instincts.py` script generates synthetic training observations from these rules (varying drive levels, randomising inactive inputs) and feeds them through the existing `MultiLobeBrain.train_on_observations()`. The output is a `genome_weights.pt` file: the default weights every norn is born with. The additive bias hack in `nornbrain_cfc.py` is removed; instincts live in the weights themselves. Later, this instinct list becomes the foundation for a genetic mutation/crossover system.

**Tech Stack:** Python 3.14, PyTorch, ncps (CfC/NCP)

**Key constraint:** The existing `MultiLobeBrain.train_on_observations()` accepts `{lobes: {lobe_id: [floats]}, chemicals: [256 floats], attn_winner: int, decn_winner: int}`. We generate synthetic dicts in exactly this format: no changes to the brain class needed.

---

## Label Maps (reference for all tasks)

```python
# Drive indices (driv lobe, 20 neurons)
DRIVES = {
    "pain": 0, "hunger_prot": 1, "hunger_carb": 2, "hunger_fat": 3,
    "cold": 4, "hot": 5, "tired": 6, "sleepy": 7,
    "lonely": 8, "crowded": 9, "fear": 10, "bored": 11,
    "anger": 12, "sex_drive": 13, "comfort": 14,
}

# Attention categories (attn lobe, 40 neurons)
CATEGORIES = {
    "self": 0, "hand": 1, "door": 2, "seed": 3, "plant": 4, "weed": 5,
    "leaf": 6, "flower": 7, "fruit": 8, "manky": 9, "detritus": 10,
    "food": 11, "button": 12, "bug": 13, "pest": 14, "critter": 15,
    "beast": 16, "nest": 17, "animal_egg": 18, "weather": 19, "bad": 20,
    "toy": 21, "incubator": 22, "dispenser": 23, "tool": 24, "potion": 25,
    "elevator": 26, "teleporter": 27, "machinery": 28, "creature_egg": 29,
    "norn_home": 30, "grendel_home": 31, "ettin_home": 32,
    "gadget": 33, "something": 34, "vehicle": 35, "norn": 36,
    "grendel": 37, "ettin": 38, "something2": 39,
}

# Decision actions (decn lobe, 14 active neurons)
ACTIONS = {
    "look": 0, "push": 1, "pull": 2, "deactivate": 3, "approach": 4,
    "retreat": 5, "get": 6, "drop": 7, "express": 8, "rest": 9,
    "left": 10, "right": 11, "eat": 12, "hit": 13,
}
```

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `openc2e/tools/instincts.py` | **Create** | Instinct definitions as structured data + synthetic observation generator |
| `openc2e/tools/pretrain_instincts.py` | **Create** | Script: loads instincts, generates training data, trains brain, saves genome_weights.pt |
| `openc2e/tools/nornbrain_cfc.py` | **Modify** | Remove additive bias hack, load genome_weights.pt as default |
| `openc2e/tools/test_instincts.py` | **Create** | Tests for instinct system |

---

## Task 1: Create Instinct Definitions Module

**Files:**
- Create: `openc2e/tools/instincts.py`

- [ ] **Step 1: Create instincts.py with label maps and instinct rules**

```python
"""NB Instinct System: modular genome definitions for CfC pre-training.

Each instinct rule defines: when a drive exceeds a threshold AND a category
is visible, the correct action is X. These rules are the norn's genetic
knowledge: what it knows at birth before any experience.

This module is the foundation for future genetic mutation/crossover.
Modify these rules to change what a norn is born knowing.
"""

# ── Label Maps ──────────────────────────────────────────────────────

DRIVES = {
    "pain": 0, "hunger_prot": 1, "hunger_carb": 2, "hunger_fat": 3,
    "cold": 4, "hot": 5, "tired": 6, "sleepy": 7,
    "lonely": 8, "crowded": 9, "fear": 10, "bored": 11,
    "anger": 12, "sex_drive": 13, "comfort": 14,
}

CATEGORIES = {
    "self": 0, "hand": 1, "door": 2, "seed": 3, "plant": 4, "weed": 5,
    "leaf": 6, "flower": 7, "fruit": 8, "manky": 9, "detritus": 10,
    "food": 11, "button": 12, "bug": 13, "pest": 14, "critter": 15,
    "beast": 16, "nest": 17, "animal_egg": 18, "weather": 19, "bad": 20,
    "toy": 21, "incubator": 22, "dispenser": 23, "tool": 24, "potion": 25,
    "elevator": 26, "teleporter": 27, "machinery": 28, "creature_egg": 29,
    "norn_home": 30, "grendel_home": 31, "ettin_home": 32,
    "gadget": 33, "something": 34, "vehicle": 35, "norn": 36,
    "grendel": 37, "ettin": 38, "something2": 39,
}

ACTIONS = {
    "look": 0, "push": 1, "pull": 2, "deactivate": 3, "approach": 4,
    "retreat": 5, "get": 6, "drop": 7, "express": 8, "rest": 9,
    "left": 10, "right": 11, "eat": 12, "hit": 13,
}

N_DRIVES = 20
N_CATEGORIES = 40
N_ACTIONS = 14
N_CHEMICALS = 256


# ── Instinct Rules ──────────────────────────────────────────────────
# Each rule: {drive, threshold, category, action, weight}
#   drive:     name from DRIVES: which need triggers this instinct
#   threshold: drive level (0.0-1.0) above which the instinct activates
#   category:  name from CATEGORIES: what to attend to (None = any visible)
#   action:    name from ACTIONS: what to do
#   weight:    how many synthetic samples to generate (higher = stronger instinct)
#
# These mirror C3 genome instinct genes but are human-readable and tweakable.
# Later: mutation changes thresholds/actions, crossover blends parent instincts.

INSTINCT_RULES = [
    # ── Hunger → food sources → eat ──
    {"drive": "hunger_prot",  "threshold": 0.15, "category": "food",      "action": "eat",      "weight": 3},
    {"drive": "hunger_prot",  "threshold": 0.15, "category": "food",      "action": "approach",  "weight": 2},
    {"drive": "hunger_carb",  "threshold": 0.15, "category": "fruit",     "action": "eat",      "weight": 3},
    {"drive": "hunger_carb",  "threshold": 0.15, "category": "fruit",     "action": "approach",  "weight": 2},
    {"drive": "hunger_fat",   "threshold": 0.15, "category": "seed",      "action": "eat",      "weight": 3},
    {"drive": "hunger_fat",   "threshold": 0.15, "category": "seed",      "action": "approach",  "weight": 2},
    # Secondary food sources (cross-hunger)
    {"drive": "hunger_prot",  "threshold": 0.30, "category": "fruit",     "action": "eat",      "weight": 1},
    {"drive": "hunger_carb",  "threshold": 0.30, "category": "food",      "action": "eat",      "weight": 1},
    {"drive": "hunger_fat",   "threshold": 0.30, "category": "detritus",  "action": "eat",      "weight": 1},

    # ── Dispensers and buttons → push (activate) ──
    {"drive": "hunger_prot",  "threshold": 0.20, "category": "dispenser", "action": "push",     "weight": 2},
    {"drive": "hunger_carb",  "threshold": 0.20, "category": "dispenser", "action": "push",     "weight": 2},
    {"drive": "hunger_prot",  "threshold": 0.20, "category": "button",    "action": "push",     "weight": 1},

    # ── Fear → dangerous things → retreat ──
    {"drive": "fear",         "threshold": 0.20, "category": "beast",     "action": "retreat",  "weight": 4},
    {"drive": "fear",         "threshold": 0.20, "category": "pest",      "action": "retreat",  "weight": 3},
    {"drive": "fear",         "threshold": 0.20, "category": "bad",       "action": "retreat",  "weight": 3},
    {"drive": "fear",         "threshold": 0.20, "category": "grendel",   "action": "retreat",  "weight": 4},

    # ── Pain → retreat from anything ──
    {"drive": "pain",         "threshold": 0.20, "category": "beast",     "action": "retreat",  "weight": 3},
    {"drive": "pain",         "threshold": 0.20, "category": "grendel",   "action": "retreat",  "weight": 3},

    # ── Tiredness/sleepiness → rest ──
    {"drive": "tired",        "threshold": 0.30, "category": "self",      "action": "rest",     "weight": 3},
    {"drive": "sleepy",       "threshold": 0.30, "category": "self",      "action": "rest",     "weight": 3},

    # ── Boredom → interact with toys/machines ──
    {"drive": "bored",        "threshold": 0.25, "category": "toy",       "action": "push",     "weight": 2},
    {"drive": "bored",        "threshold": 0.25, "category": "button",    "action": "push",     "weight": 1},
    {"drive": "bored",        "threshold": 0.25, "category": "machinery", "action": "push",     "weight": 1},

    # ── Loneliness → approach norns ──
    {"drive": "lonely",       "threshold": 0.25, "category": "norn",      "action": "approach", "weight": 3},
    {"drive": "lonely",       "threshold": 0.40, "category": "norn",      "action": "push",     "weight": 1},
    {"drive": "lonely",       "threshold": 0.30, "category": "hand",      "action": "approach", "weight": 1},

    # ── Sex drive → approach norns ──
    {"drive": "sex_drive",    "threshold": 0.30, "category": "norn",      "action": "approach", "weight": 2},
    {"drive": "sex_drive",    "threshold": 0.50, "category": "norn",      "action": "push",     "weight": 2},

    # ── Crowded → move away ──
    {"drive": "crowded",      "threshold": 0.30, "category": "norn",      "action": "retreat",  "weight": 2},

    # ── Cold → approach warm things ──
    {"drive": "cold",         "threshold": 0.30, "category": "machinery", "action": "approach", "weight": 1},
    {"drive": "cold",         "threshold": 0.30, "category": "norn_home", "action": "approach", "weight": 1},

    # ── Idle/exploration (low drives) ──
    {"drive": "bored",        "threshold": 0.10, "category": "critter",   "action": "look",     "weight": 1},
    {"drive": "bored",        "threshold": 0.10, "category": "plant",     "action": "look",     "weight": 1},
]


def get_instinct_rules():
    """Return the instinct rules list. Entry point for future genetics."""
    return INSTINCT_RULES
```

- [ ] **Step 2: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/instincts.py
git commit -m "nb: instinct definitions module: modular genome rules for CfC pre-training"
```

---

## Task 2: Create Synthetic Observation Generator

**Files:**
- Modify: `openc2e/tools/instincts.py` (add generator function)

- [ ] **Step 1: Add generate_training_data() to instincts.py**

Append to `instincts.py`:

```python
import random


def generate_training_data(rules=None, samples_per_weight=50, noise=0.05):
    """Generate synthetic observations from instinct rules.

    For each rule, generates (weight * samples_per_weight) training observations.
    Each observation is a dict matching MultiLobeBrain.train_on_observations() format:
      {lobes: {lobe_id: [floats]}, chemicals: [256 floats],
       attn_winner: int, decn_winner: int}

    The drive specified by the rule is set above threshold. The target category
    is set visible in the visn lobe. Other inputs get random noise (so the brain
    learns to respond to the signal, not memorise a fixed pattern).

    Parameters
    ----------
    rules : list[dict] or None
        Instinct rules to generate from. Defaults to INSTINCT_RULES.
    samples_per_weight : int
        Base number of samples per weight unit.
    noise : float
        Magnitude of random noise on non-signal inputs.

    Returns
    -------
    list[dict]
        Synthetic observations ready for train_on_observations().
    """
    if rules is None:
        rules = INSTINCT_RULES

    observations = []

    for rule in rules:
        drive_idx = DRIVES[rule["drive"]]
        category_idx = CATEGORIES[rule["category"]]
        action_idx = ACTIONS[rule["action"]]
        threshold = rule["threshold"]
        n_samples = rule["weight"] * samples_per_weight

        for _ in range(n_samples):
            # Drive level: random between threshold and 1.0
            drive_level = random.uniform(threshold, min(threshold + 0.5, 1.0))

            # Build lobe inputs
            driv = [random.uniform(0, noise) for _ in range(N_DRIVES)]
            driv[drive_idx] = drive_level

            # Vision: target category is visible, plus 2-5 random others
            visn = [0.0] * N_CATEGORIES
            visn[category_idx] = random.uniform(0.3, 1.0)
            n_distractors = random.randint(2, 5)
            for _ in range(n_distractors):
                d = random.randint(0, N_CATEGORIES - 1)
                if d != category_idx:
                    visn[d] = random.uniform(0.05, 0.3)

            # Other lobes: low noise
            smel = [random.uniform(0, noise) for _ in range(N_CATEGORIES)]
            noun = [random.uniform(0, noise) for _ in range(N_CATEGORIES)]
            verb = [random.uniform(0, noise) for _ in range(17)]
            sitn = [random.uniform(0, noise) for _ in range(9)]
            detl = [random.uniform(0, noise) for _ in range(11)]
            resp = [random.uniform(0, noise) for _ in range(N_DRIVES)]
            prox = [random.uniform(0, noise) for _ in range(N_DRIVES)]
            stim = [random.uniform(0, noise) for _ in range(N_CATEGORIES)]

            # Chemicals: set drive chemicals to match drive levels
            chemicals = [0.0] * N_CHEMICALS
            for i in range(min(15, N_DRIVES)):
                chemicals[148 + i] = driv[i]  # Drive chemicals 148-162

            obs = {
                "lobes": {
                    "visn": visn, "smel": smel, "driv": driv, "prox": prox,
                    "sitn": sitn, "detl": detl, "noun": noun, "verb": verb,
                    "resp": resp, "stim": stim,
                },
                "chemicals": chemicals,
                "attn_winner": category_idx,
                "decn_winner": action_idx,
            }
            observations.append(obs)

    random.shuffle(observations)
    return observations
```

- [ ] **Step 2: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/instincts.py
git commit -m "nb: synthetic observation generator for instinct pre-training"
```

---

## Task 3: Create Pre-Training Script

**Files:**
- Create: `openc2e/tools/pretrain_instincts.py`

- [ ] **Step 1: Create pretrain_instincts.py**

```python
#!/usr/bin/env python3
"""NB: Pre-train CfC brain from instinct genome definitions.

Generates synthetic training data from instincts.py rules, trains the
MultiLobeBrain via supervised behaviour cloning, and saves genome weights.

Usage:
    python pretrain_instincts.py                    # default 200 epochs
    python pretrain_instincts.py --epochs 500       # more training
    python pretrain_instincts.py --output my.pt     # custom output path
"""

import argparse
import os
import sys

# Add paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "phase1-prototype"))
sys.path.insert(0, _THIS_DIR)

from instincts import get_instinct_rules, generate_training_data


def main():
    parser = argparse.ArgumentParser(description="NB: Pre-train CfC brain from instinct genome")
    parser.add_argument("--epochs", type=int, default=200, help="Training epochs")
    parser.add_argument("--lr", type=float, default=0.005, help="Learning rate")
    parser.add_argument("--samples", type=int, default=50, help="Samples per weight unit")
    parser.add_argument("--output", type=str,
                        default=os.path.join(_PROJECT_ROOT, "phase2-bridge", "genome_weights.pt"),
                        help="Output weights path")
    args = parser.parse_args()

    rules = get_instinct_rules()
    print(f"NB Instinct Pre-Training")
    print(f"  Rules: {len(rules)}")
    print(f"  Epochs: {args.epochs}")
    print(f"  LR: {args.lr}")
    print(f"  Samples/weight: {args.samples}")

    # Generate synthetic training data
    print(f"\nGenerating synthetic observations...")
    observations = generate_training_data(rules, samples_per_weight=args.samples)
    print(f"  Generated {len(observations)} training samples")

    # Count per action
    action_counts = {}
    for obs in observations:
        a = obs["decn_winner"]
        action_counts[a] = action_counts.get(a, 0) + 1
    print(f"  Action distribution:")
    from instincts import ACTIONS
    inv_actions = {v: k for k, v in ACTIONS.items()}
    for idx in sorted(action_counts.keys()):
        name = inv_actions.get(idx, f"#{idx}")
        print(f"    {name:12s}: {action_counts[idx]:4d} samples")

    # Create brain and train
    print(f"\nTraining CfC brain...")
    from multi_lobe_brain import MultiLobeBrain
    brain = MultiLobeBrain()

    losses = brain.train_on_observations(
        observations,
        epochs=args.epochs,
        lr=args.lr,
    )

    print(f"\n  Final loss: {losses[-1]:.4f}")
    print(f"  Loss curve: {losses[0]:.4f} -> {losses[len(losses)//2]:.4f} -> {losses[-1]:.4f}")

    # Quick accuracy check on training data
    brain.train(False)
    correct_attn = 0
    correct_decn = 0
    total = min(len(observations), 500)
    for obs in observations[:total]:
        raw = brain._obs_to_raw_inputs(obs)
        brain.wipe()
        output = brain.tick(raw)
        if output.attention_winner == obs["attn_winner"]:
            correct_attn += 1
        if output.decision_winner == obs["decn_winner"]:
            correct_decn += 1

    print(f"\n  Training accuracy ({total} samples):")
    print(f"    Attention: {correct_attn}/{total} ({100*correct_attn/total:.1f}%)")
    print(f"    Decision:  {correct_decn}/{total} ({100*correct_decn/total:.1f}%)")

    # Save
    brain.save_weights(args.output)
    size_kb = os.path.getsize(args.output) / 1024
    print(f"\n  Saved genome weights to {args.output} ({size_kb:.0f} KB)")
    print(f"\nDone. Use --brain-module nornbrain_cfc.py to load these weights.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the pre-training**

```bash
cd <PROJECT_ROOT>/openc2e/tools
python pretrain_instincts.py --epochs 200 --samples 50
```

Expected output: ~1500-2500 synthetic samples, loss decreasing over 200 epochs, attention accuracy >80%, decision accuracy >60%. A `genome_weights.pt` file is created.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/pretrain_instincts.py
git commit -m "nb: instinct pre-training script: generates genome weights from instinct rules"
```

---

## Task 4: Wire nornbrain_cfc.py to Use Genome Weights

**Files:**
- Modify: `openc2e/tools/nornbrain_cfc.py`

- [ ] **Step 1: Add genome weights path and update loading logic**

In `nornbrain_cfc.py`, after the existing `WEIGHTS_PATH` definition, add:

```python
GENOME_WEIGHTS_PATH = os.path.join(_bridge_path, "genome_weights.pt")
```

- [ ] **Step 2: Update _ensure_brain() to load genome weights as fallback**

In the `_ensure_brain()` function, modify the weight loading logic:

```python
def _ensure_brain():
    global brain, _udp_sock
    if brain is not None:
        return

    print(f"[nornbrain_cfc] Loading CfC brain...")
    try:
        import torch
        from multi_lobe_brain import MultiLobeBrain

        brain = MultiLobeBrain()
        if os.path.exists(WEIGHTS_PATH):
            brain.load_weights(WEIGHTS_PATH)
            print(f"[nornbrain_cfc] Loaded learned weights from {WEIGHTS_PATH}")
        elif os.path.exists(GENOME_WEIGHTS_PATH):
            brain.load_weights(GENOME_WEIGHTS_PATH)
            print(f"[nornbrain_cfc] Loaded genome weights from {GENOME_WEIGHTS_PATH}")
        else:
            print(f"[nornbrain_cfc] No weights found: random init (run pretrain_instincts.py)")
        print(f"[nornbrain_cfc] Brain ready (239 neurons, RL={'ON' if _rl_enabled else 'OFF'})")
    except Exception as e:
        print(f"[nornbrain_cfc] Brain init ERROR: {e}")
        brain = None

    # ... rest unchanged (UDP socket, atexit) ...
```

Weight priority: learned weights (from RL experience) > genome weights (from instinct pre-training) > random init.

- [ ] **Step 3: Remove the additive bias hack**

Remove the entire `INSTINCT_TABLE` list and the `compute_instinct_bias()` function.

In the `tick()` function, remove all references to instinct bias:
- Remove the call to `compute_instinct_bias(driv_vals)`
- Remove `final_attn[:40] += attn_bias`
- Remove `final_decn += decn_bias`
- Keep the visibility mask logic (that's sensory gating, not instinct)

The tick function's attention logic becomes:

```python
        # ── Attention with visibility mask ──
        visn_vals = [float(v) for v in lobes.get("visn", [0.0] * 40)]
        if len(visn_vals) < 40:
            visn_vals += [0.0] * (40 - len(visn_vals))

        attn_raw = output.attention_values
        if hasattr(attn_raw, 'copy'):
            final_attn = attn_raw.copy().astype(np.float32)
        else:
            final_attn = np.array(attn_raw, dtype=np.float32)

        # Visibility proximity bonus (closer objects get higher bonus)
        VISIBILITY_WEIGHT = 1.0
        for i in range(min(len(visn_vals), 40)):
            if abs(visn_vals[i]) > 0.001:
                final_attn[i] += VISIBILITY_WEIGHT * abs(visn_vals[i])

        # Visibility mask: only attend to visible categories
        visible_cats = set()
        for i, v in enumerate(visn_vals):
            if abs(v) > 0.001:
                visible_cats.add(i)

        if visible_cats:
            for i in range(40):
                if i not in visible_cats:
                    final_attn[i] = -999.0
            attn_win = int(np.argmax(final_attn))
        else:
            attn_win = int(output.attention_winner)

        # ── Decision (direct from CfC, no bias) ──
        decn_raw = output.decision_values[:14]
        if hasattr(decn_raw, 'copy'):
            final_decn = decn_raw.copy().astype(np.float32)
        else:
            final_decn = np.array(decn_raw, dtype=np.float32)
        decn_win = int(np.argmax(final_decn))
```

- [ ] **Step 4: Verify syntax**

```bash
python -m py_compile openc2e/tools/nornbrain_cfc.py
```

- [ ] **Step 5: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/nornbrain_cfc.py
git commit -m "nb: load genome weights, remove additive instinct bias hack"
```

---

## Task 5: Test the Full Pipeline

**Files:**
- Create: `openc2e/tools/test_instincts.py`

- [ ] **Step 1: Create test file**

```python
"""Tests for the NB instinct system."""

import os
import sys
import tempfile

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "phase1-prototype")))

from instincts import (
    INSTINCT_RULES, DRIVES, CATEGORIES, ACTIONS,
    get_instinct_rules, generate_training_data,
)


def test_label_maps_consistent():
    """All instinct rules reference valid drive/category/action names."""
    for i, rule in enumerate(INSTINCT_RULES):
        assert rule["drive"] in DRIVES, f"Rule {i}: unknown drive '{rule['drive']}'"
        assert rule["category"] in CATEGORIES, f"Rule {i}: unknown category '{rule['category']}'"
        assert rule["action"] in ACTIONS, f"Rule {i}: unknown action '{rule['action']}'"
        assert 0.0 < rule["threshold"] <= 1.0, f"Rule {i}: threshold {rule['threshold']} out of range"
        assert rule["weight"] >= 1, f"Rule {i}: weight must be >= 1"


def test_generate_training_data_count():
    """Generated sample count matches sum of weights * samples_per_weight."""
    rules = get_instinct_rules()
    total_weight = sum(r["weight"] for r in rules)
    samples_per = 10
    data = generate_training_data(rules, samples_per_weight=samples_per)
    assert len(data) == total_weight * samples_per


def test_generated_observations_format():
    """Each observation has the right keys and shapes for train_on_observations."""
    data = generate_training_data(samples_per_weight=2)
    assert len(data) > 0
    obs = data[0]
    assert "lobes" in obs
    assert "chemicals" in obs
    assert "attn_winner" in obs
    assert "decn_winner" in obs
    lobes = obs["lobes"]
    assert len(lobes["visn"]) == 40
    assert len(lobes["driv"]) == 20
    assert len(lobes["smel"]) == 40
    assert len(obs["chemicals"]) == 256
    assert 0 <= obs["attn_winner"] < 40
    assert 0 <= obs["decn_winner"] < 14


def test_drive_signal_present():
    """The triggering drive is above threshold in generated observations."""
    rules = [{"drive": "hunger_prot", "threshold": 0.3, "category": "food",
              "action": "eat", "weight": 1}]
    data = generate_training_data(rules, samples_per_weight=20)
    drive_idx = DRIVES["hunger_prot"]
    for obs in data:
        assert obs["lobes"]["driv"][drive_idx] >= 0.3


def test_target_category_visible():
    """The target category has nonzero vision activation."""
    rules = [{"drive": "fear", "threshold": 0.2, "category": "beast",
              "action": "retreat", "weight": 1}]
    data = generate_training_data(rules, samples_per_weight=20)
    cat_idx = CATEGORIES["beast"]
    for obs in data:
        assert obs["lobes"]["visn"][cat_idx] > 0.0


def test_pretrain_produces_weights():
    """Full pipeline: generate data, train brain, save weights."""
    from multi_lobe_brain import MultiLobeBrain
    rules = [
        {"drive": "hunger_prot", "threshold": 0.2, "category": "food", "action": "eat", "weight": 2},
        {"drive": "fear", "threshold": 0.2, "category": "beast", "action": "retreat", "weight": 2},
    ]
    data = generate_training_data(rules, samples_per_weight=10)
    brain = MultiLobeBrain()
    losses = brain.train_on_observations(data, epochs=5, lr=0.01)
    assert len(losses) == 5
    assert losses[-1] < losses[0]  # Loss should decrease

    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        path = f.name
    try:
        brain.save_weights(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000
    finally:
        os.unlink(path)


if __name__ == "__main__":
    test_label_maps_consistent()
    print("PASS: label maps consistent")
    test_generate_training_data_count()
    print("PASS: sample count matches weights")
    test_generated_observations_format()
    print("PASS: observation format correct")
    test_drive_signal_present()
    print("PASS: drive signal present")
    test_target_category_visible()
    print("PASS: target category visible")
    test_pretrain_produces_weights()
    print("PASS: pretrain produces weights")
    print("\nAll tests passed.")
```

- [ ] **Step 2: Run tests**

```bash
cd <PROJECT_ROOT>/openc2e/tools
python test_instincts.py
```

Expected: All 6 tests pass.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/test_instincts.py
git commit -m "nb: instinct system tests: label consistency, data generation, training pipeline"
```

---

## Task 6: Run Pre-Training and Live Test

- [ ] **Step 1: Generate genome weights**

```bash
cd <PROJECT_ROOT>/openc2e/tools
python pretrain_instincts.py --epochs 300 --samples 50
```

Expected: genome_weights.pt created, attention accuracy >80%, decision accuracy >50%.

- [ ] **Step 2: Delete old learned weights (start fresh from genome)**

```bash
# Back up old weights, then remove so nornbrain_cfc.py falls through to genome weights
mv <PROJECT_ROOT>/phase2-bridge/brain_weights_multi_lobe.pt <PROJECT_ROOT>/phase2-bridge/brain_weights_multi_lobe.pt.old
```

- [ ] **Step 3: Restart engine and verify instincts work**

```bash
powershell -Command "Stop-Process -Name openc2e -Force -ErrorAction SilentlyContinue"
sleep 3
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
start "" "./openc2e.exe" --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/nornbrain_cfc.py"
```

Wait for world load, hatch norn. Watch the monitor: the norn should now:
- Approach food when hungry (not express at dispenser)
- Retreat from grendels/beasts when scared
- Rest when tired
- Push toys when bored

Diversity should be >0.15 from the start instead of 0.07.

- [ ] **Step 4: Verify genome weights loaded in console**

Check the engine console or brain_crash.log for:
```
[nornbrain_cfc] Loaded genome weights from .../genome_weights.pt
```

- [ ] **Step 5: Commit genome weights**

```bash
cd <PROJECT_ROOT>
git add phase2-bridge/genome_weights.pt
git commit -m "nb: genome weights: instinct-pre-trained CfC defaults"
```
