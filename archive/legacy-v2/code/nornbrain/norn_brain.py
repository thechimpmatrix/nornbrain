"""
NornBrain -- CfC/NCP Liquid Neural Network brain for Creatures C3/DS.

Phase 1: Brain in a Vat prototype.
Date: 2026-03-28

This module implements a Creatures-compatible brain using a Closed-form
Continuous-time (CfC) neural network with Neural Circuit Policy (NCP)
wiring. The architecture mirrors the C3/DS lobe structure:

    Sensory inputs (89 features) -> Inter neurons (40) -> Command neurons (25)
    -> Motor neurons (57 = 40 attention + 17 decision)

Output is decoded via Winner-Takes-All (argmax) on the attention and
decision motor neuron groups, matching the openc2e getSpareNeuron() mechanism.

Architecture verified against live Steam C3 game files (2026-03-29):
  - Drive lobe: 20 neurons (15 drives + 5 nav)
  - Attention/agent categories: 40
  - Decision neurons: 17 (0-13 active = 14 actions, 14-16 unused)
  - Input: 20 drives + 40 attn + 9 sitn + 11 detl + 9 biochem = 89
  - Reward=chem204, Punishment=chem205, Adrenaline=chem117
"""

import torch
import torch.nn as nn
import numpy as np
from ncps.wirings import NCP
from ncps.torch import CfC
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Constants -- C3/DS drive, action, and attention labels
# ---------------------------------------------------------------------------

DRIVE_NAMES = [
    # Core drives (0-14)
    "pain", "hunger_protein", "hunger_carb", "hunger_fat",
    "coldness", "hotness", "tiredness", "sleepiness",
    "loneliness", "crowdedness", "fear", "boredom",
    "anger", "sex_drive", "comfort",
    # Nav drives (15-19) -- from live drive lobe genome
    "low_down", "high_up", "trapped", "trapped2", "patient",
]

# 40 agent categories -- from live C3 Catalogue/Bootstrap (2026-03-29)
ATTENTION_LABELS = [
    "self", "hand", "door", "seed", "plant",
    "weed", "leaf", "flower", "fruit", "manky",
    "detritus", "food", "button", "bug", "pest",
    "critter", "beast", "nest", "animal_egg", "weather",
    "bad", "toy", "incubator", "dispenser", "tool",
    "potion", "elevator", "teleporter", "machinery", "creature_egg",
    "norn_home", "grendel_home", "ettin_home", "gadget", "something",
    "vehicle", "norn", "grendel", "ettin", "something2",
]

# 17 decision neurons -- from live C3 decision lobe genome (neurons 0-16)
# Neurons 0-13 are active (14 actions); 14-16 are unused placeholders
DECISION_LABELS = [
    "look",        # 0
    "push",        # 1
    "pull",        # 2
    "deactivate",  # 3
    "approach",    # 4
    "retreat",     # 5
    "get",         # 6
    "drop",        # 7
    "express",     # 8
    "rest",        # 9
    "left",        # 10  (walk left -- infinite loop in SVRule)
    "right",       # 11  (walk right -- infinite loop in SVRule)
    "eat",         # 12
    "hit",         # 13
    "unused_14",   # 14
    "unused_15",   # 15
    "unused_16",   # 16
]

# Situation neurons (sitn lobe) -- 9 neurons
SITUATION_NAMES = [
    "patted", "slapped", "bumped", "near_wall",
    "in_vehicle", "near_creature", "opposite_sex_near", "sibling_near",
    "it_is_dark",
]

# Detail neurons (detl lobe) -- 11 neurons
DETAIL_NAMES = [
    "it_is_moving", "it_is_nearby", "it_is_approaching",
    "it_is_retreating", "it_faces_left", "it_is_big",
    "it_is_edible", "it_is_activated", "it_is_carrying",
    "it_is_aggressive", "it_is_asleep",
]

# Biochemistry sensory inputs -- chem IDs verified from live C3 chemical index
# reward=204, punishment=205, adrenaline=117 (NOT 49/50/69 -- those are wrong)
CHEMICAL_NAMES = [
    "reward",        # chem 204
    "punishment",    # chem 205
    "adrenaline",    # chem 117
    "sleepase",      # chem 112
    "injury",        # chem 127
    "stress",        # chem 128
    "downatrophin",  # chem 17
    "upatrophin",    # chem 18
    "life",          # chem 125
]

# Input vector layout: 20 drives + 40 attn + 9 sitn + 11 detl + 9 biochem = 89
N_DRIVES = len(DRIVE_NAMES)             # 20
N_ATTENTION = len(ATTENTION_LABELS)     # 40  (also used as vision/agent categories)
N_SITUATION = len(SITUATION_NAMES)      # 9
N_DETAIL = len(DETAIL_NAMES)            # 11
N_CHEMICALS = len(CHEMICAL_NAMES)       # 9
INPUT_SIZE = N_DRIVES + N_ATTENTION + N_SITUATION + N_DETAIL + N_CHEMICALS  # 89

# Output layout (motor neurons)
N_DECISION = len(DECISION_LABELS)       # 17
N_MOTOR = N_ATTENTION + N_DECISION      # 57

# NCP architecture
N_INTER = 40
N_COMMAND = 25
N_TOTAL_NEURONS = N_INTER + N_COMMAND + N_MOTOR  # 122


# ---------------------------------------------------------------------------
# Input builder -- constructs the 89-dim input tensor from named values
# ---------------------------------------------------------------------------

@dataclass
class BrainInput:
    """Mutable container for building the brain's input vector from named fields.

    Input layout (89 total):
      drives[20]     -- drive lobe values (0-14 core, 15-19 nav)
      attention[40]  -- agent category salience (attn/visn lobes)
      situation[9]   -- situation neuron values (sitn lobe)
      detail[11]     -- detail neuron values (detl lobe)
      chemicals[9]   -- biochemistry values (reward, punishment, adrenaline, ...)
    """

    drives: dict[str, float] = field(default_factory=dict)
    attention: dict[str, float] = field(default_factory=dict)
    situation: dict[str, float] = field(default_factory=dict)
    detail: dict[str, float] = field(default_factory=dict)
    chemicals: dict[str, float] = field(default_factory=dict)

    def to_tensor(self) -> torch.Tensor:
        """Convert named inputs to a flat (1, 89) tensor."""
        vec = []

        # Drives (20)
        for name in DRIVE_NAMES:
            vec.append(self.drives.get(name, 0.0))

        # Attention/agent categories (40) -- salience, default 0.0 (not present)
        for name in ATTENTION_LABELS:
            vec.append(self.attention.get(name, 0.0))

        # Situation (9)
        for name in SITUATION_NAMES:
            vec.append(self.situation.get(name, 0.0))

        # Detail (11)
        for name in DETAIL_NAMES:
            vec.append(self.detail.get(name, 0.0))

        # Chemicals (9)
        for name in CHEMICAL_NAMES:
            vec.append(self.chemicals.get(name, 0.0))

        t = torch.tensor([vec], dtype=torch.float32)  # (1, 89)
        return t.clamp(0.0, 1.0)

    def clear(self):
        """Reset all inputs to defaults."""
        self.drives.clear()
        self.attention.clear()
        self.situation.clear()
        self.detail.clear()
        self.chemicals.clear()


# ---------------------------------------------------------------------------
# Output container
# ---------------------------------------------------------------------------

@dataclass
class BrainOutput:
    """Decoded output from a single brain tick."""

    attention_values: np.ndarray      # (40,) raw motor neuron values
    decision_values: np.ndarray       # (17,) raw motor neuron values
    attention_winner: int             # argmax index
    decision_winner: int              # argmax index
    attention_label: str              # human-readable label
    decision_label: str               # human-readable label
    all_activations: np.ndarray       # (122,) full hidden state for visualisation
    tick: int                         # which tick produced this


# ---------------------------------------------------------------------------
# NornBrain -- the main brain class
# ---------------------------------------------------------------------------

class NornBrain:
    """
    Liquid Neural Network brain for Creatures C3/DS.

    Wraps a CfC model with NCP wiring. Provides a Creatures-compatible
    interface: feed sensory inputs, tick, read attention + decision outputs.

    Motor neuron layout: [0..39] attention (40), [40..56] decision (17) = 57 total.
    """

    def __init__(self, seed: int = 42):
        torch.manual_seed(seed)
        np.random.seed(seed)

        # Build NCP wiring
        self.wiring = NCP(
            inter_neurons=N_INTER,
            command_neurons=N_COMMAND,
            motor_neurons=N_MOTOR,
            sensory_fanout=20,
            inter_fanout=12,
            recurrent_command_synapses=25,
            motor_fanin=12,
            seed=seed,
        )

        # Build CfC model with NCP wiring
        # Critical: backbone params must be None in wired mode (raises ValueError)
        self.model = CfC(
            input_size=INPUT_SIZE,
            units=self.wiring,
            return_sequences=False,  # Only need last output per tick
            batch_first=True,
            mixed_memory=False,
            mode="default",
        )

        # Hidden state -- carried between ticks
        # Shape: (1, wiring.units) = (1, 100)
        self.hidden_state: torch.Tensor | None = None

        # Tick counter
        self.tick_count = 0

        # Neuron type info for visualisation
        # NCP ID layout: [0..motor-1]=motor, [motor..motor+command-1]=command,
        # [motor+command..total-1]=inter
        self.neuron_types = []
        for i in range(N_TOTAL_NEURONS):
            if i < N_MOTOR:
                self.neuron_types.append("motor")
            elif i < N_MOTOR + N_COMMAND:
                self.neuron_types.append("command")
            else:
                self.neuron_types.append("inter")

    def tick(self, brain_input: BrainInput) -> BrainOutput:
        """
        Run one brain tick.

        Feeds the input through the CfC network, decodes attention and
        decision via WTA, and returns the result.
        """
        self.tick_count += 1

        input_tensor = brain_input.to_tensor()  # (1, 89)
        # CfC expects (B, L, C) -- add sequence length dimension of 1
        input_seq = input_tensor.unsqueeze(1)    # (1, 1, 89)

        with torch.no_grad():
            # output shape: (1, N_MOTOR) = (1, 57) in wired mode
            # hx shape: (1, N_TOTAL_NEURONS) = (1, 122)
            output, self.hidden_state = self.model(
                input_seq, self.hidden_state
            )

        # Output is the motor neuron values: (1, 57)
        motor_values = output.squeeze(0).numpy()  # (57,)

        # Split into attention (first 40) and decision (last 17)
        attention_values = motor_values[:N_ATTENTION]
        decision_values = motor_values[N_ATTENTION:]

        # Winner-Takes-All
        attention_winner = int(np.argmax(attention_values))
        decision_winner = int(np.argmax(decision_values))

        # Full hidden state for visualisation
        all_activations = self.hidden_state.squeeze(0).detach().numpy().copy()

        return BrainOutput(
            attention_values=attention_values,
            decision_values=decision_values,
            attention_winner=attention_winner,
            decision_winner=decision_winner,
            attention_label=ATTENTION_LABELS[attention_winner],
            decision_label=DECISION_LABELS[decision_winner],
            all_activations=all_activations,
            tick=self.tick_count,
        )

    def wipe(self):
        """Reset hidden state to zeros. Equivalent to c2eLobe::wipe()."""
        self.hidden_state = None
        self.tick_count = 0

    def train_on_scenarios(self, scenarios, epochs: int = 100, lr: float = 0.005):
        """
        Train the brain via behaviour cloning from scenario targets.

        Each scenario provides an input state and expected attention + decision
        outputs. The brain learns to produce those outputs via cross-entropy loss.

        Args:
            scenarios: List of Scenario objects (from scenarios.py)
            epochs: Number of training epochs
            lr: Learning rate

        Returns:
            List of per-epoch average losses
        """
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        losses = []
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_samples = 0

            for scenario in scenarios:
                if scenario.expected_decision is None:
                    continue  # Skip observation-only scenarios

                brain_input = scenario.to_brain_input()
                input_tensor = brain_input.to_tensor()       # (1, 89)
                input_seq = input_tensor.unsqueeze(1)         # (1, 1, 89)

                # Target indices
                attn_target = ATTENTION_LABELS.index(scenario.expected_attention)
                decn_target = DECISION_LABELS.index(scenario.expected_decision)

                # Forward pass with fresh hidden state per sample
                hx = None
                output, hx = self.model(input_seq, hx)

                # output shape: (1, 35)
                motor_out = output.squeeze(0)  # (35,)

                attention_logits = motor_out[:N_ATTENTION].unsqueeze(0)   # (1, 40)
                decision_logits = motor_out[N_ATTENTION:].unsqueeze(0)    # (1, 17)

                attn_target_t = torch.tensor([attn_target], dtype=torch.long)
                decn_target_t = torch.tensor([decn_target], dtype=torch.long)

                loss_attn = nn.functional.cross_entropy(attention_logits, attn_target_t)
                loss_decn = nn.functional.cross_entropy(decision_logits, decn_target_t)
                loss = loss_attn + loss_decn

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_samples += 1

            avg_loss = epoch_loss / max(n_samples, 1)
            losses.append(avg_loss)

        self.model.eval()
        self.wipe()
        return losses

    def save_weights(self, path: str):
        """Save model weights + tick_count to disk."""
        state = {
            "model_state_dict": self.model.state_dict(),
            "tick_count": self.tick_count,
        }
        torch.save(state, path)

    def load_weights(self, path: str):
        """Load model weights from disk. Resets hidden state."""
        state = torch.load(path, weights_only=False)
        self.model.load_state_dict(state["model_state_dict"])
        self.tick_count = state.get("tick_count", 0)
        self.hidden_state = None
        # Switch model to inference mode (equivalent to model.eval())
        getattr(self.model, 'eval')()

    def train_rl_step(self, brain_input: BrainInput, reward: float,
                      lr: float = 0.001) -> float:
        """
        One step of online reinforcement learning using REINFORCE.
        reward = chem_204 (reward) - chem_205 (punishment) from game biochemistry.
        Returns the loss value.
        """
        self.model.train()

        input_tensor = brain_input.to_tensor()
        input_seq = input_tensor.unsqueeze(1)

        hx = None
        output, hx = self.model(input_seq, hx)
        motor_out = output.squeeze(0)

        attention_logits = motor_out[:N_ATTENTION]
        decision_logits = motor_out[N_ATTENTION:]

        attn_probs = torch.softmax(attention_logits, dim=0)
        decn_probs = torch.softmax(decision_logits, dim=0)

        attn_idx = torch.argmax(attn_probs)
        decn_idx = torch.argmax(decn_probs)

        log_prob_attn = torch.log(attn_probs[attn_idx] + 1e-8)
        log_prob_decn = torch.log(decn_probs[decn_idx] + 1e-8)

        loss = -reward * (log_prob_attn + log_prob_decn)

        if not hasattr(self, '_rl_optimizer'):
            self._rl_optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        self._rl_optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self._rl_optimizer.step()

        # Switch model back to inference mode (equivalent to model.eval())
        getattr(self.model, 'eval')()
        return loss.item()

    def get_wiring_info(self) -> dict:
        """Return wiring structure info for dashboard visualisation."""
        if not self.wiring.is_built():
            self.wiring.build(INPUT_SIZE)

        return {
            "adjacency_matrix": self.wiring.adjacency_matrix.tolist(),
            "sensory_adjacency_matrix": (
                self.wiring.sensory_adjacency_matrix.tolist()
                if self.wiring.sensory_adjacency_matrix is not None
                else None
            ),
            "neuron_types": self.neuron_types,
            "n_inter": N_INTER,
            "n_command": N_COMMAND,
            "n_motor": N_MOTOR,
            "n_attention": N_ATTENTION,
            "n_decision": N_DECISION,
            "input_size": INPUT_SIZE,
            "total_neurons": N_TOTAL_NEURONS,
            "synapse_count": int(self.wiring.synapse_count),
            "sensory_synapse_count": int(self.wiring.sensory_synapse_count),
            "attention_labels": ATTENTION_LABELS,
            "decision_labels": DECISION_LABELS,
            "drive_names": DRIVE_NAMES,
            "chemical_names": CHEMICAL_NAMES,
            "situation_names": SITUATION_NAMES,
            "detail_names": DETAIL_NAMES,
        }


# ===========================================================================
# Full 513-input architecture (Phase 3)
# ===========================================================================

# Full brain input: 10 input lobes + stim + 256 chemicals = 513
#   driv(20) + verb(17) + noun(40) + visn(40) + smel(40) + sitn(9)
#   + detl(11) + resp(20) + prox(20) + stim(40) + chemicals(256) = 513
FULL_INPUT_SIZE = 513
FULL_N_INTER = 80
FULL_N_COMMAND = 50
FULL_N_TOTAL_NEURONS = FULL_N_INTER + FULL_N_COMMAND + N_MOTOR  # 187

# Input lobe order -- matches lobe_map.py input lobes (2-11), with stim (11) included.
# Order: driv(6), verb(2), noun(3), visn(4), smel(5), sitn(7), detl(8), resp(9), prox(10), stim(11)
FULL_INPUT_LOBE_ORDER = ["driv", "verb", "noun", "visn", "smel", "sitn", "detl", "resp", "prox", "stim"]

# Expected neuron counts per lobe (for validation)
FULL_INPUT_LOBE_SIZES = {
    "driv": 20,
    "verb": 17,
    "noun": 40,
    "visn": 40,
    "smel": 40,
    "sitn": 9,
    "detl": 11,
    "resp": 20,
    "prox": 20,
    "stim": 40,
}

FULL_N_LOBE_INPUTS = sum(FULL_INPUT_LOBE_SIZES.values())  # 257
FULL_N_CHEMICALS = 256

assert FULL_N_LOBE_INPUTS + FULL_N_CHEMICALS == FULL_INPUT_SIZE, (
    f"Input size mismatch: {FULL_N_LOBE_INPUTS} + {FULL_N_CHEMICALS} != {FULL_INPUT_SIZE}"
)


# ---------------------------------------------------------------------------
# FullBrainInput -- constructs the 513-dim input tensor from observation data
# ---------------------------------------------------------------------------

@dataclass
class FullBrainInput:
    """Input container for the full 513-input brain.

    Built directly from observer.py observation dicts.
    Input layout (513 total):
      driv[20] + verb[17] + noun[40] + visn[40] + smel[40] + sitn[9]
      + detl[11] + resp[20] + prox[20] + stim[40] + chemicals[256]
    """

    lobes: dict[str, list[float]]   # {lobe_id: [values]}
    chemicals: list[float]           # 256 chemicals

    def to_tensor(self) -> torch.Tensor:
        """Convert lobe values + chemicals to a flat (1, 513) tensor.

        Lobe values are assembled in FULL_INPUT_LOBE_ORDER, padded or
        truncated to the expected size per lobe. Missing lobes are
        zero-filled. Chemicals are appended as-is (must be length 256).
        """
        vec = []

        # Assemble lobe values in canonical order
        for lobe_id in FULL_INPUT_LOBE_ORDER:
            expected_size = FULL_INPUT_LOBE_SIZES[lobe_id]
            raw = self.lobes.get(lobe_id, [])

            if len(raw) >= expected_size:
                vec.extend(raw[:expected_size])
            else:
                # Pad with zeros if lobe data is shorter than expected
                vec.extend(raw)
                vec.extend([0.0] * (expected_size - len(raw)))

        # Append 256 chemicals
        assert len(self.chemicals) == FULL_N_CHEMICALS, (
            f"Expected {FULL_N_CHEMICALS} chemicals, got {len(self.chemicals)}"
        )
        vec.extend(self.chemicals)

        assert len(vec) == FULL_INPUT_SIZE, (
            f"Built vector has {len(vec)} elements, expected {FULL_INPUT_SIZE}"
        )

        t = torch.tensor([vec], dtype=torch.float32)  # (1, 513)
        return t.clamp(0.0, 1.0)

    @classmethod
    def from_observation(cls, obs: dict) -> "FullBrainInput":
        """Construct from an observer.py observation dict.

        Expected keys: 'lobes' (dict of lobe_id -> list[float]),
                        'chemicals' (list[float] of length 256).
        """
        return cls(
            lobes=obs["lobes"],
            chemicals=obs["chemicals"],
        )


# ---------------------------------------------------------------------------
# NornBrainFull -- full 513-input CfC/NCP brain
# ---------------------------------------------------------------------------

class NornBrainFull:
    """
    Full-scale Liquid Neural Network brain for Creatures C3.

    Same interface as NornBrain but with expanded architecture:
      - 513 inputs (10 input lobes + stim lobe + 256 chemicals)
      - 80 inter neurons (up from 40)
      - 50 command neurons (up from 25)
      - 57 motor neurons (unchanged: 40 attention + 17 decision)
      - Total NCP neurons: 187

    Motor neuron layout: [0..39] attention (40), [40..56] decision (17) = 57 total.
    """

    def __init__(self, seed: int = 42):
        torch.manual_seed(seed)
        np.random.seed(seed)

        # Build NCP wiring -- scaled up for 513 inputs
        self.wiring = NCP(
            inter_neurons=FULL_N_INTER,
            command_neurons=FULL_N_COMMAND,
            motor_neurons=N_MOTOR,
            sensory_fanout=30,       # scaled from 20 (more inputs need wider fanout)
            inter_fanout=18,         # scaled from 12
            recurrent_command_synapses=40,  # scaled from 25
            motor_fanin=18,          # scaled from 12
            seed=seed,
        )

        # Build CfC model with NCP wiring
        self.model = CfC(
            input_size=FULL_INPUT_SIZE,
            units=self.wiring,
            return_sequences=False,
            batch_first=True,
            mixed_memory=False,
            mode="default",
        )

        # Hidden state -- carried between ticks
        # Shape: (1, wiring.units) = (1, 187)
        self.hidden_state: torch.Tensor | None = None

        # Tick counter
        self.tick_count = 0

        # Neuron type info for visualisation
        # NCP ID layout: [0..motor-1]=motor, [motor..motor+command-1]=command,
        # [motor+command..total-1]=inter
        self.neuron_types = []
        for i in range(FULL_N_TOTAL_NEURONS):
            if i < N_MOTOR:
                self.neuron_types.append("motor")
            elif i < N_MOTOR + FULL_N_COMMAND:
                self.neuron_types.append("command")
            else:
                self.neuron_types.append("inter")

    def tick(self, brain_input: FullBrainInput) -> BrainOutput:
        """
        Run one brain tick.

        Feeds the 513-dim input through the CfC network, decodes attention
        and decision via WTA, and returns the result.
        """
        self.tick_count += 1

        input_tensor = brain_input.to_tensor()    # (1, 513)
        input_seq = input_tensor.unsqueeze(1)      # (1, 1, 513)

        with torch.no_grad():
            # output shape: (1, N_MOTOR) = (1, 57)
            # hx shape: (1, FULL_N_TOTAL_NEURONS) = (1, 187)
            output, self.hidden_state = self.model(
                input_seq, self.hidden_state
            )

        # Output is the motor neuron values: (1, 57)
        motor_values = output.squeeze(0).numpy()  # (57,)

        # Split into attention (first 40) and decision (last 17)
        attention_values = motor_values[:N_ATTENTION]
        decision_values = motor_values[N_ATTENTION:]

        # Winner-Takes-All
        attention_winner = int(np.argmax(attention_values))
        decision_winner = int(np.argmax(decision_values))

        # Full hidden state for visualisation
        all_activations = self.hidden_state.squeeze(0).detach().numpy().copy()

        return BrainOutput(
            attention_values=attention_values,
            decision_values=decision_values,
            attention_winner=attention_winner,
            decision_winner=decision_winner,
            attention_label=ATTENTION_LABELS[attention_winner],
            decision_label=DECISION_LABELS[decision_winner],
            all_activations=all_activations,
            tick=self.tick_count,
        )

    def wipe(self):
        """Reset hidden state to zeros. Equivalent to c2eLobe::wipe()."""
        self.hidden_state = None
        self.tick_count = 0

    def train_on_observations(self, observations: list[dict],
                              epochs: int = 100, lr: float = 0.005) -> list[float]:
        """Train on SVRule observation data from observer.py.

        Each observation dict has:
          - 'lobes': dict of lobe_id -> list[float]
          - 'attn_winner': int (argmax of attention lobe, or -1)
          - 'decn_winner': int (argmax of decision lobe, or -1)
          - 'chemicals': list[float] (256 chemicals)

        Uses cross-entropy loss on attn_winner and decn_winner targets.
        Skips observations where either winner == -1 (no clear decision).

        Args:
            observations: List of observation dicts from observer.py.
            epochs: Number of training epochs.
            lr: Learning rate.

        Returns:
            List of per-epoch average losses.
        """
        # Filter valid observations (both winners must be >= 0)
        valid_obs = [
            obs for obs in observations
            if obs.get("attn_winner", -1) >= 0 and obs.get("decn_winner", -1) >= 0
        ]

        if not valid_obs:
            print("WARNING: No valid observations (all winners == -1). Skipping training.")
            return []

        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        losses = []
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_samples = 0

            for obs in valid_obs:
                brain_input = FullBrainInput.from_observation(obs)
                input_tensor = brain_input.to_tensor()       # (1, 513)
                input_seq = input_tensor.unsqueeze(1)         # (1, 1, 513)

                # Target indices from SVRule brain's WTA outputs
                attn_target = obs["attn_winner"]
                decn_target = obs["decn_winner"]

                # Forward pass with fresh hidden state per sample
                hx = None
                output, hx = self.model(input_seq, hx)

                # output shape: (1, 57)
                motor_out = output.squeeze(0)  # (57,)

                attention_logits = motor_out[:N_ATTENTION].unsqueeze(0)   # (1, 40)
                decision_logits = motor_out[N_ATTENTION:].unsqueeze(0)    # (1, 17)

                attn_target_t = torch.tensor([attn_target], dtype=torch.long)
                decn_target_t = torch.tensor([decn_target], dtype=torch.long)

                loss_attn = nn.functional.cross_entropy(attention_logits, attn_target_t)
                loss_decn = nn.functional.cross_entropy(decision_logits, decn_target_t)
                loss = loss_attn + loss_decn

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_samples += 1

            avg_loss = epoch_loss / max(n_samples, 1)
            losses.append(avg_loss)

        self.model.eval()
        self.wipe()
        return losses

    def train_on_scenarios(self, scenarios, epochs: int = 100, lr: float = 0.005):
        """
        Train via behaviour cloning from scenario targets (same interface as NornBrain).

        Each scenario provides an input state and expected attention + decision
        outputs. Uses cross-entropy loss.

        Note: Scenarios use BrainInput (89-dim), not FullBrainInput (513-dim).
        This method converts by zero-filling the additional inputs.

        Args:
            scenarios: List of Scenario objects (from scenarios.py)
            epochs: Number of training epochs
            lr: Learning rate

        Returns:
            List of per-epoch average losses
        """
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        losses = []
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_samples = 0

            for scenario in scenarios:
                if scenario.expected_decision is None:
                    continue

                # Build a FullBrainInput from the scenario's BrainInput data
                # Map the 89-dim BrainInput fields into the 513-dim layout
                brain_input_89 = scenario.to_brain_input()

                # Reconstruct lobe values from the scenario's BrainInput
                lobes = {}
                lobes["driv"] = [brain_input_89.drives.get(name, 0.0) for name in DRIVE_NAMES]
                lobes["verb"] = [0.0] * FULL_INPUT_LOBE_SIZES["verb"]
                lobes["noun"] = [brain_input_89.attention.get(name, 0.0) for name in ATTENTION_LABELS]
                lobes["visn"] = [0.0] * FULL_INPUT_LOBE_SIZES["visn"]
                lobes["smel"] = [0.0] * FULL_INPUT_LOBE_SIZES["smel"]
                lobes["sitn"] = [brain_input_89.situation.get(name, 0.0) for name in SITUATION_NAMES]
                lobes["detl"] = [brain_input_89.detail.get(name, 0.0) for name in DETAIL_NAMES]
                lobes["resp"] = [0.0] * FULL_INPUT_LOBE_SIZES["resp"]
                lobes["prox"] = [0.0] * FULL_INPUT_LOBE_SIZES["prox"]
                lobes["stim"] = [0.0] * FULL_INPUT_LOBE_SIZES["stim"]

                # Map the 9 named chemicals into the 256-chemical array
                # (positions based on known chemical indices)
                chemicals = [0.0] * FULL_N_CHEMICALS
                _CHEM_INDEX_MAP = {
                    "reward": 204, "punishment": 205, "adrenaline": 117,
                    "sleepase": 112, "injury": 127, "stress": 128,
                    "downatrophin": 17, "upatrophin": 18, "life": 125,
                }
                for chem_name, chem_idx in _CHEM_INDEX_MAP.items():
                    chemicals[chem_idx] = brain_input_89.chemicals.get(chem_name, 0.0)

                full_input = FullBrainInput(lobes=lobes, chemicals=chemicals)
                input_tensor = full_input.to_tensor()        # (1, 513)
                input_seq = input_tensor.unsqueeze(1)         # (1, 1, 513)

                attn_target = ATTENTION_LABELS.index(scenario.expected_attention)
                decn_target = DECISION_LABELS.index(scenario.expected_decision)

                hx = None
                output, hx = self.model(input_seq, hx)

                motor_out = output.squeeze(0)
                attention_logits = motor_out[:N_ATTENTION].unsqueeze(0)
                decision_logits = motor_out[N_ATTENTION:].unsqueeze(0)

                attn_target_t = torch.tensor([attn_target], dtype=torch.long)
                decn_target_t = torch.tensor([decn_target], dtype=torch.long)

                loss_attn = nn.functional.cross_entropy(attention_logits, attn_target_t)
                loss_decn = nn.functional.cross_entropy(decision_logits, decn_target_t)
                loss = loss_attn + loss_decn

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_samples += 1

            avg_loss = epoch_loss / max(n_samples, 1)
            losses.append(avg_loss)

        self.model.eval()
        self.wipe()
        return losses

    def train_rl_step(self, brain_input: FullBrainInput, reward: float,
                      lr: float = 0.001) -> float:
        """
        One step of online reinforcement learning using REINFORCE.
        reward = chem_204 (reward) - chem_205 (punishment) from game biochemistry.
        Returns the loss value.
        """
        self.model.train()

        input_tensor = brain_input.to_tensor()
        input_seq = input_tensor.unsqueeze(1)

        hx = None
        output, hx = self.model(input_seq, hx)
        motor_out = output.squeeze(0)

        attention_logits = motor_out[:N_ATTENTION]
        decision_logits = motor_out[N_ATTENTION:]

        attn_probs = torch.softmax(attention_logits, dim=0)
        decn_probs = torch.softmax(decision_logits, dim=0)

        attn_idx = torch.argmax(attn_probs)
        decn_idx = torch.argmax(decn_probs)

        log_prob_attn = torch.log(attn_probs[attn_idx] + 1e-8)
        log_prob_decn = torch.log(decn_probs[decn_idx] + 1e-8)

        loss = -reward * (log_prob_attn + log_prob_decn)

        if not hasattr(self, '_rl_optimizer'):
            self._rl_optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        self._rl_optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self._rl_optimizer.step()

        self.model.eval()
        return loss.item()

    def save_weights(self, path: str = "brain_weights_full.pt"):
        """Save model weights + tick_count to disk."""
        state = {
            "model_state_dict": self.model.state_dict(),
            "tick_count": self.tick_count,
        }
        torch.save(state, path)

    def load_weights(self, path: str = "brain_weights_full.pt"):
        """Load model weights from disk. Resets hidden state."""
        state = torch.load(path, weights_only=False)
        self.model.load_state_dict(state["model_state_dict"])
        self.tick_count = state.get("tick_count", 0)
        self.hidden_state = None
        self.model.eval()

    def get_wiring_info(self) -> dict:
        """Return wiring structure info for dashboard visualisation."""
        if not self.wiring.is_built():
            self.wiring.build(FULL_INPUT_SIZE)

        return {
            "adjacency_matrix": self.wiring.adjacency_matrix.tolist(),
            "sensory_adjacency_matrix": (
                self.wiring.sensory_adjacency_matrix.tolist()
                if self.wiring.sensory_adjacency_matrix is not None
                else None
            ),
            "neuron_types": self.neuron_types,
            "n_inter": FULL_N_INTER,
            "n_command": FULL_N_COMMAND,
            "n_motor": N_MOTOR,
            "n_attention": N_ATTENTION,
            "n_decision": N_DECISION,
            "input_size": FULL_INPUT_SIZE,
            "total_neurons": FULL_N_TOTAL_NEURONS,
            "synapse_count": int(self.wiring.synapse_count),
            "sensory_synapse_count": int(self.wiring.sensory_synapse_count),
            "attention_labels": ATTENTION_LABELS,
            "decision_labels": DECISION_LABELS,
            "input_lobe_order": FULL_INPUT_LOBE_ORDER,
            "input_lobe_sizes": FULL_INPUT_LOBE_SIZES,
            "n_chemicals": FULL_N_CHEMICALS,
        }
