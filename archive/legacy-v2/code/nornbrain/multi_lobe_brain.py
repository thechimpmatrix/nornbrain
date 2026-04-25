"""
MultiLobeBrain -- Compartmentalised multi-module CfC brain for Creatures C3.

Phase 4A: Multi-Lobe CfC Brain Architecture.
Date: 2026-03-30

Replaces the monolithic NornBrainFull (single 513-input CfC/NCP) with four
specialised CfC modules connected by genetically-defined tract projections:

    Thalamus   -- sensory relay, attention gating   (produces attn_winner)
    Amygdala   -- emotional tagging, valence         (continuous output)
    Hippocampus -- contextual memory, spatial state  (continuous output)
    Prefrontal -- executive decision-making           (produces decn_winner)

Each module is an independent CfC instance with its own NCP wiring, hidden
state, and learned time dynamics. The modules are connected via Tract bundles
that route raw sensory inputs and inter-module outputs through sparse,
genetically-parameterised linear projections.

The output contract is IDENTICAL to NornBrainFull -- the bridge client can
swap between them without changes. The tick() method accepts a dict of raw
input tensors and returns a BrainOutput dataclass.

Architecture (default genome):
    Module       Inter  Cmd  Motor  Total  Output
    Thalamus       20   10    40     70    attn (40)
    Amygdala       24   12    16     52    emotion (16)
    Hippocampus    24   12    16     52    context (16)
    Prefrontal     32   16    17     65    decn (17)
    Total         100   50    89    239    89

See Phase 4A spec (docs/superpowers/specs/2026-03-30-phase4a-multi-lobe-cfc-design.md)
for full architectural rationale.
"""

import copy
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from ncps.wirings import NCP
from ncps.torch import CfC

from .norn_brain import (
    BrainOutput,
    ATTENTION_LABELS,
    DECISION_LABELS,
    N_ATTENTION,
    N_DECISION,
)
from .brain_genome import DEFAULT_GENOME, AMYGDALA_CHEM_INDICES, PFC_CHEM_INDICES
from ..tract import Tract, TractBundle


# ---------------------------------------------------------------------------
# Time constant bias values
# ---------------------------------------------------------------------------

_TIME_BIAS_VALUES: dict[str, float] = {
    "fast": 0.5,       # Positive bias -> t_interp -> 1 -> fast updates
    "slow": -0.5,      # Negative bias -> t_interp -> 0 -> slow updates
    "moderate": 0.0,   # No bias -> let training decide
    "mixed": 0.0,      # No bias -> let training decide
}


# ---------------------------------------------------------------------------
# Module names in canonical processing order
# ---------------------------------------------------------------------------

MODULE_NAMES = ["thalamus", "amygdala", "hippocampus", "prefrontal"]

# Stage 1 modules (no inter-module data dependency, can run in parallel)
_STAGE1_MODULES = ["thalamus", "amygdala", "hippocampus"]

# Stage 2 modules (depend on Stage 1 outputs)
_STAGE2_MODULES = ["prefrontal"]


# ---------------------------------------------------------------------------
# Helper: build a CfC module from genome spec
# ---------------------------------------------------------------------------

def _build_cfc_module(
    input_size: int,
    module_spec: dict[str, Any],
    seed: int,
) -> CfC:
    """Build a single CfC module from a genome module specification.

    Parameters
    ----------
    input_size : int
        Number of input features (determined by tract bundle output_size).
    module_spec : dict
        Module genome dict with keys: inter_neurons, command_neurons,
        motor_neurons, sensory_fanout, inter_fanout,
        recurrent_command_synapses, motor_fanin, time_bias.
    seed : int
        RNG seed for NCP wiring generation.

    Returns
    -------
    CfC
        A configured CfC module ready for forward passes.
    """
    wiring = NCP(
        inter_neurons=module_spec["inter_neurons"],
        command_neurons=module_spec["command_neurons"],
        motor_neurons=module_spec["motor_neurons"],
        sensory_fanout=module_spec["sensory_fanout"],
        inter_fanout=module_spec["inter_fanout"],
        recurrent_command_synapses=module_spec["recurrent_command_synapses"],
        motor_fanin=module_spec["motor_fanin"],
        seed=seed,
    )

    model = CfC(
        input_size=input_size,
        units=wiring,
        return_sequences=False,
        batch_first=True,
        mixed_memory=False,
        mode="default",
    )

    return model


def _apply_time_bias(model: CfC, bias_name: str) -> None:
    """Apply time constant initialisation bias to a CfC module.

    Modifies the ``time_b`` bias parameter of the CfC cell in-place.
    This biases the sigmoid interpolation factor:
      - "fast" (+0.5): neurons tend toward full update (reactive)
      - "slow" (-0.5): neurons tend toward retaining old state (persistent)
      - "moderate" / "mixed" (0.0): no bias, let training decide

    Parameters
    ----------
    model : CfC
        The CfC module whose time_b parameter will be biased.
    bias_name : str
        One of "fast", "slow", "moderate", "mixed".
    """
    bias_value = _TIME_BIAS_VALUES.get(bias_name, 0.0)
    if bias_value == 0.0:
        return

    # The CfC model wraps a CfCCell. The time constant bias is stored
    # in the cell's backbone (time_b linear layer).
    cell = model.rnn_cell
    if hasattr(cell, "ff2") and hasattr(cell, "time_b"):
        # CfCCell stores time_b as a nn.Linear layer
        with torch.no_grad():
            cell.time_b.bias.add_(bias_value)
    else:
        # Wired CfC cells may have different internals.
        # Walk all parameters looking for time_b bias tensors.
        for name, param in model.named_parameters():
            if "time_b" in name and "bias" in name:
                with torch.no_grad():
                    param.add_(bias_value)


# ---------------------------------------------------------------------------
# Tract bundle builders
# ---------------------------------------------------------------------------

def _build_tract_specs_for_module(
    module_name: str,
    genome: dict[str, Any],
) -> list[dict]:
    """Extract tract specifications for a given target module from the genome.

    Returns a list of dicts suitable for TractBundle construction, sorted by
    tract name for deterministic ordering.

    Parameters
    ----------
    module_name : str
        Target module name (e.g. "thalamus", "prefrontal").
    genome : dict
        Full genome dict.

    Returns
    -------
    list[dict]
        Tract specification dicts with keys: name, src_size, dst_size,
        connections, seed, enabled.
    """
    base_seed = genome.get("seed", 42)
    specs = []

    for tract_name, tract_spec in sorted(genome["tracts"].items()):
        if tract_spec["dst_module"] != module_name:
            continue

        # Each tract gets a unique seed derived from the genome seed and tract name
        tract_seed = base_seed + hash(tract_name) % (2**31)

        specs.append({
            "name": tract_name,
            "src_size": tract_spec["src_size"],
            "dst_size": tract_spec["dst_size"],
            "connections": tract_spec["connections"],
            "seed": tract_seed,
            "enabled": tract_spec["enabled"],
        })

    return specs


# ---------------------------------------------------------------------------
# MultiLobeBrain
# ---------------------------------------------------------------------------

class MultiLobeBrain(nn.Module):
    """Compartmentalised multi-module CfC brain for Creatures C3.

    Four CfC modules (Thalamus, Amygdala, Hippocampus, Prefrontal Cortex)
    connected by genetically-defined tract projections. Each module has
    independent hidden states, NCP wiring, and time dynamics.

    The output contract is identical to NornBrainFull: the tick() method
    returns a BrainOutput dataclass with attn_winner, decn_winner, and
    all_activations.

    Parameters
    ----------
    genome : dict or None
        Genome configuration dict. If None, uses DEFAULT_GENOME.
    seed : int
        Master RNG seed for reproducibility.
    """

    def __init__(self, genome: dict = None, seed: int = 42):
        super().__init__()

        self.genome = copy.deepcopy(genome) if genome is not None else copy.deepcopy(DEFAULT_GENOME)
        self.seed = seed

        torch.manual_seed(seed)
        np.random.seed(seed)

        # ---------------------------------------------------------------
        # Build tract bundles (one per module)
        # ---------------------------------------------------------------

        thal_specs = _build_tract_specs_for_module("thalamus", self.genome)
        amyg_specs = _build_tract_specs_for_module("amygdala", self.genome)
        hipp_specs = _build_tract_specs_for_module("hippocampus", self.genome)
        pfc_specs = _build_tract_specs_for_module("prefrontal", self.genome)

        self.thalamus_tracts = TractBundle(thal_specs)
        self.amygdala_tracts = TractBundle(amyg_specs)
        self.hippocampus_tracts = TractBundle(hipp_specs)
        self.prefrontal_tracts = TractBundle(pfc_specs)

        # ---------------------------------------------------------------
        # Build CfC modules
        # ---------------------------------------------------------------

        modules_spec = self.genome["modules"]

        self.thalamus = _build_cfc_module(
            input_size=self.thalamus_tracts.output_size,
            module_spec=modules_spec["thalamus"],
            seed=seed,
        )
        self.amygdala = _build_cfc_module(
            input_size=self.amygdala_tracts.output_size,
            module_spec=modules_spec["amygdala"],
            seed=seed + 1,
        )
        self.hippocampus = _build_cfc_module(
            input_size=self.hippocampus_tracts.output_size,
            module_spec=modules_spec["hippocampus"],
            seed=seed + 2,
        )
        self.prefrontal = _build_cfc_module(
            input_size=self.prefrontal_tracts.output_size,
            module_spec=modules_spec["prefrontal"],
            seed=seed + 3,
        )

        # ---------------------------------------------------------------
        # Apply time constant biases
        # ---------------------------------------------------------------

        _apply_time_bias(self.thalamus, modules_spec["thalamus"]["time_bias"])
        _apply_time_bias(self.amygdala, modules_spec["amygdala"]["time_bias"])
        _apply_time_bias(self.hippocampus, modules_spec["hippocampus"]["time_bias"])
        _apply_time_bias(self.prefrontal, modules_spec["prefrontal"]["time_bias"])

        # ---------------------------------------------------------------
        # Per-module hidden states (None = uninitialised)
        # ---------------------------------------------------------------

        self._hx_thalamus: torch.Tensor | None = None
        self._hx_amygdala: torch.Tensor | None = None
        self._hx_hippocampus: torch.Tensor | None = None
        self._hx_prefrontal: torch.Tensor | None = None

        # Tick counter
        self.tick_count: int = 0

        # RL baseline for REINFORCE variance reduction
        self._reward_baseline: float = 0.0

        # Lazy-initialised RL optimizer
        self._rl_optimizer: torch.optim.Adam | None = None

    # -------------------------------------------------------------------
    # Chemical extraction
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_chemicals(
        full_chemicals: torch.Tensor,
        indices: list[int],
    ) -> torch.Tensor:
        """Extract selected chemicals from the full 256-chemical tensor.

        Parameters
        ----------
        full_chemicals : torch.Tensor
            Tensor of shape ``(..., 256)`` containing all chemical values.
        indices : list[int]
            Chemical indices to extract (e.g. AMYGDALA_CHEM_INDICES).

        Returns
        -------
        torch.Tensor
            Tensor of shape ``(..., len(indices))``.
        """
        idx = torch.tensor(indices, dtype=torch.long, device=full_chemicals.device)
        return torch.index_select(full_chemicals, dim=-1, index=idx)

    # -------------------------------------------------------------------
    # Forward pass (single module)
    # -------------------------------------------------------------------

    def _forward_module(
        self,
        module: CfC,
        module_input: torch.Tensor,
        hx: torch.Tensor | None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Run a single CfC module forward pass.

        Parameters
        ----------
        module : CfC
            The CfC module to run.
        module_input : torch.Tensor
            Input tensor of shape ``(batch, input_size)``.
        hx : torch.Tensor or None
            Hidden state from the previous tick, or None for fresh state.

        Returns
        -------
        tuple[torch.Tensor, torch.Tensor]
            (output, new_hidden_state) where output has shape
            ``(batch, motor_neurons)`` and hx has shape
            ``(batch, total_neurons)``.
        """
        # CfC expects (B, L, C) -- add sequence length dimension of 1
        input_seq = module_input.unsqueeze(1)  # (B, 1, C)
        output, new_hx = module(input_seq, hx)
        return output, new_hx

    # -------------------------------------------------------------------
    # tick -- main inference entry point
    # -------------------------------------------------------------------

    def tick(
        self,
        raw_inputs: dict[str, torch.Tensor],
        ltm_injection: dict[str, float] | None = None,
    ) -> BrainOutput:
        """Run one brain tick through all four modules.

        Routes raw inputs through tract bundles, runs the four CfC modules
        in the correct causal order (Thalamus/Amygdala/Hippocampus in
        parallel, then Prefrontal), and assembles the output.

        Parameters
        ----------
        raw_inputs : dict[str, torch.Tensor]
            Raw sensory inputs from the bridge. Expected keys:
              visn(40), smel(40), driv(20), prox(20), sitn(9), detl(11),
              noun(40), verb(17), resp(20), stim(40), chemicals(256),
              location(2).
            All tensors should have shape ``(1, N)`` (batch size 1).
        ltm_injection : dict[str, float] or None
            Long-term memory injection channels (Phase 4B). If None,
            uses zeros. Expected 6 channels.

        Returns
        -------
        BrainOutput
            Same dataclass as NornBrainFull with attention_values,
            decision_values, winners, labels, and all_activations.
        """
        self.tick_count += 1

        # Determine device from any input tensor
        device = next(iter(raw_inputs.values())).device

        # --- Extract selected chemicals for amygdala and PFC ---
        full_chems = raw_inputs["chemicals"]  # (1, 256)
        selected_chems = self._extract_chemicals(full_chems, AMYGDALA_CHEM_INDICES)  # (1, 16)

        # --- Build LTM injection tensor (zeroed in Phase 4A) ---
        if ltm_injection is not None:
            ltm_values = [
                ltm_injection.get("mem1_valence", 0.0),
                ltm_injection.get("mem1_arousal", 0.0),
                ltm_injection.get("mem2_valence", 0.0),
                ltm_injection.get("mem2_arousal", 0.0),
                ltm_injection.get("mem3_valence", 0.0),
                ltm_injection.get("mem3_arousal", 0.0),
            ]
            ltm_tensor = torch.tensor([ltm_values], dtype=torch.float32, device=device)
        else:
            ltm_tensor = torch.zeros(1, 6, dtype=torch.float32, device=device)

        # =================================================================
        # Stage 1: Thalamus, Amygdala, Hippocampus (no inter-dependency)
        # =================================================================

        # --- Thalamus tract inputs ---
        thal_tract_inputs = {
            "tract_visn_thal": raw_inputs["visn"],
            "tract_smel_thal": raw_inputs["smel"],
            "tract_driv_thal": raw_inputs["driv"],
            "tract_prox_thal": raw_inputs["prox"],
        }
        thal_input = self.thalamus_tracts(thal_tract_inputs)

        # --- Amygdala tract inputs ---
        amyg_tract_inputs = {
            "tract_driv_amyg": raw_inputs["driv"],
            "tract_stim_amyg": raw_inputs["stim"],
            "tract_chem_amyg": selected_chems,
        }
        amyg_input = self.amygdala_tracts(amyg_tract_inputs)

        # --- Hippocampus tract inputs ---
        hipp_tract_inputs = {
            "tract_sitn_hipp": raw_inputs["sitn"],
            "tract_detl_hipp": raw_inputs["detl"],
            "tract_noun_hipp": raw_inputs["noun"],
            "tract_verb_hipp": raw_inputs["verb"],
            "tract_loc_hipp": raw_inputs["location"],
        }
        hipp_input = self.hippocampus_tracts(hipp_tract_inputs)

        # --- Forward passes (Stage 1) ---
        with torch.no_grad():
            thal_out, self._hx_thalamus = self._forward_module(
                self.thalamus, thal_input, self._hx_thalamus
            )
            amyg_out, self._hx_amygdala = self._forward_module(
                self.amygdala, amyg_input, self._hx_amygdala
            )
            hipp_out, self._hx_hippocampus = self._forward_module(
                self.hippocampus, hipp_input, self._hx_hippocampus
            )

        # =================================================================
        # Stage 2: Prefrontal Cortex (depends on Stage 1 outputs)
        # =================================================================

        pfc_tract_inputs = {
            "tract_thal_pfc": thal_out,
            "tract_amyg_pfc": amyg_out,
            "tract_hipp_pfc": hipp_out,
            "tract_driv_pfc": raw_inputs["driv"],
            "tract_verb_pfc": raw_inputs["verb"],
            "tract_noun_pfc": raw_inputs["noun"],
            "tract_resp_pfc": raw_inputs["resp"],
            "tract_stim_pfc": raw_inputs["stim"],
            "tract_chem_pfc": selected_chems,
            "tract_ltm_pfc": ltm_tensor,
        }
        pfc_input = self.prefrontal_tracts(pfc_tract_inputs)

        with torch.no_grad():
            pfc_out, self._hx_prefrontal = self._forward_module(
                self.prefrontal, pfc_input, self._hx_prefrontal
            )

        # =================================================================
        # Output assembly
        # =================================================================

        # Thalamus output -> attention (40 neurons)
        attn_values = thal_out.squeeze(0).detach().cpu().numpy()   # (40,)
        attn_winner = int(np.argmax(attn_values))

        # Prefrontal output -> decision (17 neurons, but only 0-13 are active)
        decn_values = pfc_out.squeeze(0).detach().cpu().numpy()    # (17,)
        # Only consider active decision neurons (0-13); 14-16 are unused
        decn_winner = int(np.argmax(decn_values[:14]))

        # Concatenate all hidden states for visualisation (239 floats)
        all_hidden = []
        for hx in [self._hx_thalamus, self._hx_amygdala,
                    self._hx_hippocampus, self._hx_prefrontal]:
            if hx is not None:
                all_hidden.append(hx.squeeze(0).detach().cpu().numpy())
            else:
                # Should not happen after first tick, but handle gracefully
                all_hidden.append(np.zeros(0))
        all_activations = np.concatenate(all_hidden)

        return BrainOutput(
            attention_values=attn_values,
            decision_values=decn_values,
            attention_winner=attn_winner,
            decision_winner=decn_winner,
            attention_label=ATTENTION_LABELS[attn_winner],
            decision_label=DECISION_LABELS[decn_winner],
            all_activations=all_activations,
            tick=self.tick_count,
        )

    # -------------------------------------------------------------------
    # wipe -- reset all hidden states
    # -------------------------------------------------------------------

    def wipe(self) -> None:
        """Reset all module hidden states to None and tick count to zero.

        Equivalent to c2eLobe::wipe() across all modules.
        """
        self._hx_thalamus = None
        self._hx_amygdala = None
        self._hx_hippocampus = None
        self._hx_prefrontal = None
        self.tick_count = 0
        self._reward_baseline = 0.0

    # -------------------------------------------------------------------
    # save / load weights
    # -------------------------------------------------------------------

    def save_weights(self, path: str = "brain_weights_multilobe.pt") -> None:
        """Save all module and tract parameters to disk.

        Parameters
        ----------
        path : str
            File path for the saved state dict.
        """
        state = {
            "model_state_dict": self.state_dict(),
            "tick_count": self.tick_count,
            "reward_baseline": self._reward_baseline,
            "genome": self.genome,
        }
        torch.save(state, path)

    def load_weights(self, path: str = "brain_weights_multilobe.pt") -> None:
        """Load module and tract parameters from disk.

        Resets all hidden states after loading.

        Parameters
        ----------
        path : str
            File path to load the state dict from.
        """
        state = torch.load(path, weights_only=False)
        self.load_state_dict(state["model_state_dict"])
        self.tick_count = state.get("tick_count", 0)
        self._reward_baseline = state.get("reward_baseline", 0.0)
        self._hx_thalamus = None
        self._hx_amygdala = None
        self._hx_hippocampus = None
        self._hx_prefrontal = None
        # Switch to inference mode
        self.train(False)

    # -------------------------------------------------------------------
    # train_on_observations -- behaviour cloning (supervised)
    # -------------------------------------------------------------------

    def train_on_observations(
        self,
        observations: list[dict],
        epochs: int = 100,
        lr: float = 0.005,
    ) -> list[float]:
        """Train on SVRule observation data via behaviour cloning.

        Same interface as NornBrainFull.train_on_observations(). Uses
        cross-entropy loss on attn_winner (from Thalamus) and decn_winner
        (from Prefrontal). Per-module learning rates via parameter groups.

        Parameters
        ----------
        observations : list[dict]
            Observation dicts from observer.py. Each dict has:
              'lobes': dict of lobe_id -> list[float]
              'attn_winner': int (argmax of attention lobe, or -1)
              'decn_winner': int (argmax of decision lobe, or -1)
              'chemicals': list[float] (256 chemicals)
        epochs : int
            Number of training epochs.
        lr : float
            Base learning rate.

        Returns
        -------
        list[float]
            Per-epoch average losses.
        """
        # Filter valid observations (both winners must be >= 0)
        valid_obs = [
            obs for obs in observations
            if obs.get("attn_winner", -1) >= 0 and obs.get("decn_winner", -1) >= 0
        ]

        if not valid_obs:
            print("WARNING: No valid observations (all winners == -1). Skipping training.")
            return []

        self.train(True)

        # Per-module learning rates
        optimizer = torch.optim.Adam([
            {"params": self.thalamus.parameters(), "lr": lr},
            {"params": self.amygdala.parameters(), "lr": lr * 0.6},
            {"params": self.hippocampus.parameters(), "lr": lr * 0.4},
            {"params": self.prefrontal.parameters(), "lr": lr},
            {"params": self.thalamus_tracts.parameters(), "lr": lr},
            {"params": self.amygdala_tracts.parameters(), "lr": lr},
            {"params": self.hippocampus_tracts.parameters(), "lr": lr},
            {"params": self.prefrontal_tracts.parameters(), "lr": lr},
        ])

        losses = []
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_samples = 0

            for obs in valid_obs:
                raw_inputs = self._obs_to_raw_inputs(obs)

                attn_target = obs["attn_winner"]
                decn_target = obs["decn_winner"]

                # Forward pass with fresh hidden states per sample
                self.wipe()

                # Run the forward pass (with gradients)
                thal_out, amyg_out, hipp_out, pfc_out = self._forward_all(raw_inputs)

                # Cross-entropy loss on attention (thalamus) and decision (prefrontal)
                attn_logits = thal_out if thal_out.dim() == 2 else thal_out.unsqueeze(0)
                decn_logits = pfc_out if pfc_out.dim() == 2 else pfc_out.unsqueeze(0)

                attn_target_t = torch.tensor([attn_target], dtype=torch.long)
                decn_target_t = torch.tensor([decn_target], dtype=torch.long)

                loss_attn = F.cross_entropy(attn_logits, attn_target_t)
                loss_decn = F.cross_entropy(decn_logits, decn_target_t)
                loss = loss_attn + loss_decn

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_samples += 1

            avg_loss = epoch_loss / max(n_samples, 1)
            losses.append(avg_loss)

        self.train(False)
        self.wipe()
        return losses

    # -------------------------------------------------------------------
    # train_on_observations_with_checkpoints -- supervised with snapshots
    # -------------------------------------------------------------------

    def train_on_observations_with_checkpoints(
        self,
        observations: list[dict],
        epochs: int = 500,
        lr: float = 0.003,
        checkpoint_dir: str = "checkpoints",
        checkpoint_every: int = 50,
    ) -> list[float]:
        """Train with periodic weight checkpoints.

        Wraps train_on_observations() by calling it in chunks of
        ``checkpoint_every`` epochs and saving a snapshot after each chunk.

        Checkpoints are saved to ``checkpoint_dir/epoch_050.pt``,
        ``epoch_100.pt``, etc. A final checkpoint is always saved at the
        last epoch even if it does not land on a checkpoint boundary.

        Parameters
        ----------
        observations : list[dict]
            Same format as train_on_observations().
        epochs : int
            Total number of training epochs.
        lr : float
            Base learning rate.
        checkpoint_dir : str
            Directory for checkpoint files (created if needed).
        checkpoint_every : int
            Save a checkpoint every N epochs.

        Returns
        -------
        list[float]
            Per-epoch average losses (concatenated across all chunks).
        """
        import os

        os.makedirs(checkpoint_dir, exist_ok=True)

        all_losses: list[float] = []
        epochs_done = 0
        remaining = epochs

        while remaining > 0:
            chunk = min(remaining, checkpoint_every)
            losses = self.train_on_observations(
                observations, epochs=chunk, lr=lr,
            )
            all_losses.extend(losses)
            epochs_done += chunk
            remaining -= chunk

            # Save checkpoint
            ckpt_path = os.path.join(
                checkpoint_dir, f"epoch_{epochs_done:04d}.pt"
            )
            self.save_weights(ckpt_path)
            last_loss = losses[-1] if losses else float("nan")
            print(
                f"  Checkpoint saved: {ckpt_path}  "
                f"(epoch {epochs_done}/{epochs}, loss={last_loss:.4f})"
            )

        return all_losses

    # -------------------------------------------------------------------
    # train_rl_step -- online REINFORCE with baseline and entropy bonus
    # -------------------------------------------------------------------

    def train_rl_step(
        self,
        raw_inputs: dict[str, torch.Tensor],
        reward: float,
        lr: float = 0.001,
    ) -> float:
        """One step of online reinforcement learning using REINFORCE.

        Uses baseline subtraction (running average) and entropy bonus
        per the Phase 4A spec Section 8.

        Parameters
        ----------
        raw_inputs : dict[str, torch.Tensor]
            Raw sensory inputs (same format as tick()).
        reward : float
            Scalar reward signal (typically chem_204 - chem_205).
        lr : float
            Learning rate.

        Returns
        -------
        float
            The loss value for this step.
        """
        self.train(True)

        # Lazy-initialise the RL optimizer with per-module learning rates
        if self._rl_optimizer is None:
            self._rl_optimizer = torch.optim.Adam([
                {"params": self.thalamus.parameters(), "lr": lr},
                {"params": self.amygdala.parameters(), "lr": lr * 0.6},
                {"params": self.hippocampus.parameters(), "lr": lr * 0.4},
                {"params": self.prefrontal.parameters(), "lr": lr},
                {"params": self.thalamus_tracts.parameters(), "lr": lr},
                {"params": self.amygdala_tracts.parameters(), "lr": lr},
                {"params": self.hippocampus_tracts.parameters(), "lr": lr},
                {"params": self.prefrontal_tracts.parameters(), "lr": lr},
            ])

        # Forward pass (with gradients, using fresh hidden state for RL)
        thal_out, amyg_out, hipp_out, pfc_out = self._forward_all(
            raw_inputs, use_stored_hx=False,
        )

        # Softmax to get action probabilities
        attn_probs = torch.softmax(thal_out.squeeze(0), dim=0)   # (40,)
        decn_probs = torch.softmax(pfc_out.squeeze(0), dim=0)    # (17,)

        # Selected actions (argmax)
        attn_idx = torch.argmax(attn_probs)
        decn_idx = torch.argmax(decn_probs)

        # Log probabilities of selected actions
        log_prob_attn = torch.log(attn_probs[attn_idx] + 1e-8)
        log_prob_decn = torch.log(decn_probs[decn_idx] + 1e-8)

        # Baseline subtraction (exponential moving average)
        self._reward_baseline = 0.99 * self._reward_baseline + 0.01 * reward
        advantage = reward - self._reward_baseline

        # Policy gradient loss
        policy_loss = -advantage * (log_prob_attn + log_prob_decn)

        # Entropy bonus (encourage exploration)
        entropy_attn = -(attn_probs * torch.log(attn_probs + 1e-8)).sum()
        entropy_decn = -(decn_probs * torch.log(decn_probs + 1e-8)).sum()
        entropy_bonus = entropy_attn + entropy_decn

        loss = policy_loss - 0.01 * entropy_bonus

        # Backward + gradient clipping per module + step
        self._rl_optimizer.zero_grad()
        loss.backward()

        for module in [self.thalamus, self.amygdala,
                       self.hippocampus, self.prefrontal]:
            torch.nn.utils.clip_grad_norm_(module.parameters(), max_norm=1.0)

        self._rl_optimizer.step()
        self.train(False)

        return loss.item()

    # -------------------------------------------------------------------
    # Internal: forward pass through all modules (with gradients)
    # -------------------------------------------------------------------

    def _forward_all(
        self,
        raw_inputs: dict[str, torch.Tensor],
        ltm_injection: dict[str, float] | None = None,
        use_stored_hx: bool = True,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Run the full forward pass through all four modules.

        Unlike tick(), this preserves gradients for training. Returns raw
        output tensors rather than a BrainOutput dataclass.

        Parameters
        ----------
        raw_inputs : dict[str, torch.Tensor]
            Raw sensory inputs.
        ltm_injection : dict[str, float] or None
            LTM injection channels (Phase 4B). Zeroed if None.
        use_stored_hx : bool
            If True, uses and updates stored hidden states. If False,
            uses fresh (None) hidden states without storing them.

        Returns
        -------
        tuple of 4 torch.Tensor
            (thal_out, amyg_out, hipp_out, pfc_out)
        """
        device = next(iter(raw_inputs.values())).device

        # Chemical extraction
        full_chems = raw_inputs["chemicals"]
        selected_chems = self._extract_chemicals(full_chems, AMYGDALA_CHEM_INDICES)

        # LTM tensor
        if ltm_injection is not None:
            ltm_values = [
                ltm_injection.get("mem1_valence", 0.0),
                ltm_injection.get("mem1_arousal", 0.0),
                ltm_injection.get("mem2_valence", 0.0),
                ltm_injection.get("mem2_arousal", 0.0),
                ltm_injection.get("mem3_valence", 0.0),
                ltm_injection.get("mem3_arousal", 0.0),
            ]
            ltm_tensor = torch.tensor([ltm_values], dtype=torch.float32, device=device)
        else:
            ltm_tensor = torch.zeros(1, 6, dtype=torch.float32, device=device)

        # Hidden states
        hx_thal = self._hx_thalamus if use_stored_hx else None
        hx_amyg = self._hx_amygdala if use_stored_hx else None
        hx_hipp = self._hx_hippocampus if use_stored_hx else None
        hx_pfc = self._hx_prefrontal if use_stored_hx else None

        # Stage 1: Thalamus
        thal_tract_inputs = {
            "tract_visn_thal": raw_inputs["visn"],
            "tract_smel_thal": raw_inputs["smel"],
            "tract_driv_thal": raw_inputs["driv"],
            "tract_prox_thal": raw_inputs["prox"],
        }
        thal_input = self.thalamus_tracts(thal_tract_inputs)
        thal_out, new_hx_thal = self._forward_module(
            self.thalamus, thal_input, hx_thal
        )

        # Stage 1: Amygdala
        amyg_tract_inputs = {
            "tract_driv_amyg": raw_inputs["driv"],
            "tract_stim_amyg": raw_inputs["stim"],
            "tract_chem_amyg": selected_chems,
        }
        amyg_input = self.amygdala_tracts(amyg_tract_inputs)
        amyg_out, new_hx_amyg = self._forward_module(
            self.amygdala, amyg_input, hx_amyg
        )

        # Stage 1: Hippocampus
        hipp_tract_inputs = {
            "tract_sitn_hipp": raw_inputs["sitn"],
            "tract_detl_hipp": raw_inputs["detl"],
            "tract_noun_hipp": raw_inputs["noun"],
            "tract_verb_hipp": raw_inputs["verb"],
            "tract_loc_hipp": raw_inputs["location"],
        }
        hipp_input = self.hippocampus_tracts(hipp_tract_inputs)
        hipp_out, new_hx_hipp = self._forward_module(
            self.hippocampus, hipp_input, hx_hipp
        )

        # Stage 2: Prefrontal
        pfc_tract_inputs = {
            "tract_thal_pfc": thal_out,
            "tract_amyg_pfc": amyg_out,
            "tract_hipp_pfc": hipp_out,
            "tract_driv_pfc": raw_inputs["driv"],
            "tract_verb_pfc": raw_inputs["verb"],
            "tract_noun_pfc": raw_inputs["noun"],
            "tract_resp_pfc": raw_inputs["resp"],
            "tract_stim_pfc": raw_inputs["stim"],
            "tract_chem_pfc": selected_chems,
            "tract_ltm_pfc": ltm_tensor,
        }
        pfc_input = self.prefrontal_tracts(pfc_tract_inputs)
        pfc_out, new_hx_pfc = self._forward_module(
            self.prefrontal, pfc_input, hx_pfc
        )

        # Update stored hidden states if requested
        if use_stored_hx:
            self._hx_thalamus = new_hx_thal
            self._hx_amygdala = new_hx_amyg
            self._hx_hippocampus = new_hx_hipp
            self._hx_prefrontal = new_hx_pfc

        return thal_out, amyg_out, hipp_out, pfc_out

    # -------------------------------------------------------------------
    # Observation dict -> raw_inputs conversion
    # -------------------------------------------------------------------

    @staticmethod
    def _obs_to_raw_inputs(obs: dict) -> dict[str, torch.Tensor]:
        """Convert an observer.py observation dict to raw_inputs tensors.

        Parameters
        ----------
        obs : dict
            Observation dict with 'lobes' (dict of lobe_id -> list[float])
            and 'chemicals' (list[float] of length 256).

        Returns
        -------
        dict[str, torch.Tensor]
            Raw input tensors suitable for tick() or _forward_all().
        """
        lobes = obs["lobes"]
        chemicals = obs["chemicals"]

        def _lobe_tensor(lobe_id: str, expected_size: int) -> torch.Tensor:
            raw = lobes.get(lobe_id, [])
            if len(raw) >= expected_size:
                values = raw[:expected_size]
            else:
                values = list(raw) + [0.0] * (expected_size - len(raw))
            return torch.tensor([values], dtype=torch.float32).clamp(0.0, 1.0)

        raw_inputs = {
            "driv": _lobe_tensor("driv", 20),
            "verb": _lobe_tensor("verb", 17),
            "noun": _lobe_tensor("noun", 40),
            "visn": _lobe_tensor("visn", 40),
            "smel": _lobe_tensor("smel", 40),
            "sitn": _lobe_tensor("sitn", 9),
            "detl": _lobe_tensor("detl", 11),
            "resp": _lobe_tensor("resp", 20),
            "prox": _lobe_tensor("prox", 20),
            "stim": _lobe_tensor("stim", 40),
            "chemicals": torch.tensor(
                [chemicals], dtype=torch.float32
            ).clamp(0.0, 1.0),
            "location": torch.tensor(
                [[obs.get("posx", 0.0), obs.get("posy", 0.0)]],
                dtype=torch.float32,
            ).clamp(0.0, 1.0),
        }
        return raw_inputs

    # -------------------------------------------------------------------
    # get_wiring_info -- dashboard introspection
    # -------------------------------------------------------------------

    def get_wiring_info(self) -> dict:
        """Return per-module wiring info for dashboard visualisation.

        Returns
        -------
        dict
            Nested dict with per-module wiring details (adjacency matrices,
            neuron types, synapse counts) plus global architecture info.
        """
        modules_info = {}
        module_map = {
            "thalamus": (self.thalamus, self.thalamus_tracts),
            "amygdala": (self.amygdala, self.amygdala_tracts),
            "hippocampus": (self.hippocampus, self.hippocampus_tracts),
            "prefrontal": (self.prefrontal, self.prefrontal_tracts),
        }

        total_neurons = 0
        total_synapses = 0

        for mod_name, (model, tracts) in module_map.items():
            mod_spec = self.genome["modules"][mod_name]

            n_inter = mod_spec["inter_neurons"]
            n_cmd = mod_spec["command_neurons"]
            n_motor = mod_spec["motor_neurons"]
            n_total = n_inter + n_cmd + n_motor
            total_neurons += n_total

            # Build neuron type list (NCP layout: motor, command, inter)
            neuron_types = (
                ["motor"] * n_motor
                + ["command"] * n_cmd
                + ["inter"] * n_inter
            )

            mod_info = {
                "inter_neurons": n_inter,
                "command_neurons": n_cmd,
                "motor_neurons": n_motor,
                "total_neurons": n_total,
                "time_bias": mod_spec["time_bias"],
                "neuron_types": neuron_types,
                "tract_input_size": tracts.output_size,
                "tract_connections": tracts.total_active_connections,
            }

            # Extract wiring info from the CfC cell if available
            cell = model.rnn_cell
            wiring = getattr(cell, 'wiring', None)
            if wiring is not None and hasattr(wiring, 'adjacency_matrix'):
                mod_info["adjacency_matrix"] = wiring.adjacency_matrix.tolist()
                if wiring.sensory_adjacency_matrix is not None:
                    mod_info["sensory_adjacency_matrix"] = (
                        wiring.sensory_adjacency_matrix.tolist()
                    )
                mod_info["synapse_count"] = int(wiring.synapse_count)
                mod_info["sensory_synapse_count"] = int(wiring.sensory_synapse_count)
                total_synapses += int(wiring.synapse_count) + int(wiring.sensory_synapse_count)

            modules_info[mod_name] = mod_info

        return {
            "architecture": "multi_lobe",
            "modules": modules_info,
            "total_neurons": total_neurons,
            "total_synapses": total_synapses,
            "n_attention": N_ATTENTION,
            "n_decision": N_DECISION,
            "attention_labels": ATTENTION_LABELS,
            "decision_labels": DECISION_LABELS,
            "genome_version": self.genome.get("version", 1),
        }

    # -------------------------------------------------------------------
    # get_all_hidden_states -- for LTM context key generation
    # -------------------------------------------------------------------

    def get_all_hidden_states(self) -> list[float]:
        """Return concatenated hidden states from all modules.

        Used for LTM context key generation (Phase 4B). Returns a flat
        list of floats representing the full brain state (239 floats
        with default genome).

        Returns
        -------
        list[float]
            Concatenated hidden state values from thalamus, amygdala,
            hippocampus, and prefrontal (in that order). Returns empty
            list if no hidden states are initialised.
        """
        result = []
        for hx in [self._hx_thalamus, self._hx_amygdala,
                    self._hx_hippocampus, self._hx_prefrontal]:
            if hx is not None:
                result.extend(hx.squeeze(0).detach().cpu().numpy().tolist())
        return result


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building MultiLobeBrain with default genome...")
    brain = MultiLobeBrain()

    # Count parameters
    total_params = sum(p.numel() for p in brain.parameters())
    trainable_params = sum(p.numel() for p in brain.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Build dummy inputs
    raw_inputs = {
        "driv": torch.rand(1, 20),
        "verb": torch.rand(1, 17),
        "noun": torch.rand(1, 40),
        "visn": torch.rand(1, 40),
        "smel": torch.rand(1, 40),
        "sitn": torch.rand(1, 9),
        "detl": torch.rand(1, 11),
        "resp": torch.rand(1, 20),
        "prox": torch.rand(1, 20),
        "stim": torch.rand(1, 40),
        "chemicals": torch.rand(1, 256),
        "location": torch.rand(1, 2),
    }

    # Run a tick
    print("\nRunning tick 1...")
    output = brain.tick(raw_inputs)
    print(f"  attn_winner: {output.attention_winner} ({output.attention_label})")
    print(f"  decn_winner: {output.decision_winner} ({output.decision_label})")
    print(f"  attention_values shape: {output.attention_values.shape}")
    print(f"  decision_values shape: {output.decision_values.shape}")
    print(f"  all_activations shape: {output.all_activations.shape}")
    print(f"  tick: {output.tick}")

    # Run a second tick (hidden states persist)
    print("\nRunning tick 2...")
    output2 = brain.tick(raw_inputs)
    print(f"  attn_winner: {output2.attention_winner} ({output2.attention_label})")
    print(f"  decn_winner: {output2.decision_winner} ({output2.decision_label})")
    print(f"  tick: {output2.tick}")

    # Test hidden state extraction
    hidden = brain.get_all_hidden_states()
    print(f"\nHidden state length: {len(hidden)} (expected 239)")

    # Test wiring info
    info = brain.get_wiring_info()
    print(f"\nWiring info:")
    print(f"  Architecture: {info['architecture']}")
    print(f"  Total neurons: {info['total_neurons']}")
    for mod_name, mod_info in info["modules"].items():
        print(f"  {mod_name}: {mod_info['total_neurons']} neurons, "
              f"tract_input={mod_info['tract_input_size']}, "
              f"time_bias={mod_info['time_bias']}")

    # Test wipe
    brain.wipe()
    print(f"\nAfter wipe: tick_count={brain.tick_count}, "
          f"hidden states all None: "
          f"{all(h is None for h in [brain._hx_thalamus, brain._hx_amygdala, brain._hx_hippocampus, brain._hx_prefrontal])}")

    # Test save/load
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        path = f.name
    brain.tick(raw_inputs)  # Generate some hidden state
    brain.save_weights(path)
    brain.wipe()
    brain.load_weights(path)
    print(f"\nSave/load round-trip: tick_count={brain.tick_count}")
    os.unlink(path)

    print("\nAll self-tests passed.")
