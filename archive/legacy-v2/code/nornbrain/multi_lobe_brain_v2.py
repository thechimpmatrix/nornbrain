"""
NB Brain Architecture v2 - Multi-Lobe CfC Brain (1/10 scale prototype).
========================================================================

Implements the v2 hierarchical brain replacing v1's MultiLobeBrain.

Key differences from v1 (multi_lobe_brain.py):
  - Three signal types (data / modulation / memory) via SignalRouter.
  - Bidirectional inter-module flows with previous-tick feedback:
      hippocampus <-> amygdala, hippocampus -> thalamus (mem),
      amygdala -> thalamus (mod).
  - Sequential 4-stage processing: Thalamus -> Hippocampus -> Amygdala -> Frontal.
    (v1 processed the first two stages in parallel.)
  - Module naming: "prefrontal" -> "frontal".
  - Frontal produces ATTN/DECN via separate linear heads rather than direct
    argmax on motor outputs.
  - Per-module learning-rate scaling in supervised training.

Scale: 1/10 of the full 11,000-neuron target (1,100 neurons total).

Reference: NB Brain Architecture v2 spec, sections 5-7.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

from ncps.wirings import NCP
from ncps.torch import CfC

from .brain_genome_v2 import (
    DEFAULT_GENOME_V2,
    MODULE_NAMES_V2,
    AMYGDALA_CHEM_INDICES,
    FRONTAL_CHEM_INDICES,
    get_module_input_specs,
    validate_genome_v2,
)
from .legacy.norn_brain import BrainOutput, ATTENTION_LABELS, DECISION_LABELS, N_ATTENTION, N_DECISION
from .signal_types import SignalRouter
from .tract import Tract

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Time-bias constants
# ---------------------------------------------------------------------------

_TIME_BIAS_VALUES: dict[str, float] = {
    "fast": 0.5,
    "slow": -0.5,
    "moderate": 0.0,
    "mixed": 0.0,
}

# ---------------------------------------------------------------------------
# Number of key chemicals fed to amygdala / frontal modulation tracts.
# Both use the same 16-chemical selection (AMYGDALA_CHEM_INDICES ==
# FRONTAL_CHEM_INDICES at this prototype scale).
# ---------------------------------------------------------------------------

N_CHEM_SELECTED = 16  # len(AMYGDALA_CHEM_INDICES)

# Number of LTM recall dimensions fed to frontal memory tract.
N_LTM = 6

# ---------------------------------------------------------------------------
# Source-name -> raw-input key mapping
# ---------------------------------------------------------------------------
# The genome uses short source names (e.g. "visn", "loc", "ltm", "thalamus").
# This table maps those names to the key we look up in the raw_inputs dict
# passed to tick(), or to the special token "chem" / "ltm" / module names.
#
# Module outputs (inter-module tracts) are resolved at tick time once the
# previous/current output is known -- they are NOT in this table.

_EXTERNAL_SRC_KEYS: dict[str, str] = {
    "visn": "visn",
    "smel": "smel",
    "prox": "prox",
    "sitn": "sitn",
    "loc": "location",   # raw_inputs key is "location" (2-dim x,y)
    "stim": "stim",
    "detl": "detl",
    "driv": "driv",
    "noun": "noun",
    "verb": "verb",
}

# Module sources that are resolved from inter-module outputs at tick time.
_MODULE_SRCS: set[str] = {"thalamus", "amygdala", "hippocampus", "frontal"}

# Special sources handled explicitly.
_SPECIAL_SRCS: set[str] = {"chem", "ltm"}


# ===========================================================================
# TractBank -- sparse projections for one module
# ===========================================================================

class TractBank(nn.Module):
    """Holds all Tract projections targeting a single CfC module.

    Each tract in the genome that targets this module is turned into a
    Tract (src_size -> dst_size) stored in an nn.ModuleDict keyed by
    tract name.  At tick time, ``project()`` maps raw input tensors
    through their respective tracts and returns the projected dict,
    ready for consumption by SignalRouter.

    Only enabled tracts are built and projected.
    """

    def __init__(self, tract_specs: list[dict], base_seed: int = 42) -> None:
        """
        Args:
            tract_specs: List of dicts with keys:
                ``name``, ``src_size``, ``dst_size``, ``connections``,
                ``enabled``.  Disabled tracts are skipped entirely.
            base_seed: Seed offset; each tract gets ``base_seed + index``.
        """
        super().__init__()
        self._names: list[str] = []
        self._enabled: dict[str, bool] = {}
        self.tracts: nn.ModuleDict = nn.ModuleDict()

        for idx, spec in enumerate(tract_specs):
            name: str = spec["name"]
            enabled: bool = spec.get("enabled", True)
            self._names.append(name)
            self._enabled[name] = enabled

            if enabled:
                self.tracts[name] = Tract(
                    src_size=spec["src_size"],
                    dst_size=spec["dst_size"],
                    n_connections=spec["connections"],
                    seed=base_seed + idx,
                )

    def project(self, raw_inputs: dict[str, Tensor]) -> dict[str, Tensor]:
        """Project each raw input through its Tract.

        Args:
            raw_inputs: Dict mapping tract names to raw tensors of shape
                        (batch, src_size).  Only enabled tracts are projected;
                        missing keys for enabled tracts raise KeyError.

        Returns:
            Dict mapping tract name -> projected tensor (batch, dst_size).
        """
        projected: dict[str, Tensor] = {}
        for name in self._names:
            if not self._enabled[name]:
                continue
            if name not in raw_inputs:
                raise KeyError(
                    f"TractBank: enabled tract '{name}' has no raw input. "
                    f"Available keys: {sorted(raw_inputs.keys())}"
                )
            projected[name] = self.tracts[name](raw_inputs[name])
        return projected

    def extra_repr(self) -> str:
        enabled = sum(v for v in self._enabled.values())
        return f"enabled={enabled}/{len(self._enabled)}"


# ===========================================================================
# Module builder helpers
# ===========================================================================

def _build_cfc_module(input_size: int, module_spec: dict, seed: int) -> CfC:
    """Build a CfC module with NCP wiring.

    Args:
        input_size: Size of the data tensor fed to the CfC sensory layer.
                    (Only DATA inputs go here; mod/mem are applied to hx.)
        module_spec: Genome dict for this module.
        seed: NCP wiring seed.

    Returns:
        CfC instance with NCP wiring, return_sequences=False, batch_first=True.
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
    return CfC(
        input_size=input_size,
        units=wiring,
        return_sequences=False,
        batch_first=True,
        mixed_memory=False,
        mode="default",
    )


def _apply_time_bias(model: CfC, bias_name: str) -> None:
    """Add a constant offset to all time_b bias parameters in a CfC module.

    Args:
        model: The CfC instance to modify.
        bias_name: One of "fast", "slow", "moderate", "mixed".
                   "moderate" and "mixed" result in no change.
    """
    bias_value = _TIME_BIAS_VALUES.get(bias_name, 0.0)
    if bias_value == 0.0:
        return
    for name, param in model.named_parameters():
        if "time_b" in name and "bias" in name:
            with torch.no_grad():
                param.add_(bias_value)


def _hidden_size(module_spec: dict) -> int:
    """Return the total hidden-state size managed by NCP for this module.

    NCP manages inter + command + motor neurons internally.  The sensory
    neurons are handled by the input projection layer and are NOT part of hx.
    """
    return (
        module_spec["inter_neurons"]
        + module_spec["command_neurons"]
        + module_spec["motor_neurons"]
    )


# ===========================================================================
# MultiLobeBrainV2
# ===========================================================================

class MultiLobeBrainV2(nn.Module):
    """NB Brain Architecture v2 -- hierarchical CfC brain (1/10 scale).

    Four CfC modules process information in strict sequential order each tick:
        1. Thalamus     -- fast sensory relay, gates attention
        2. Hippocampus  -- context/memory integration (uses current thalamus output)
        3. Amygdala     -- emotional evaluation (uses current thal + hipp outputs)
        4. Frontal      -- decision-making (uses all three current outputs)

    Inter-module feedback from the PREVIOUS tick flows back into thalamus
    modulation (amygdala -> thalamus) and thalamus memory (hippocampus ->
    thalamus), and into hippocampus data (amygdala -> hippocampus).

    Outputs:
        - attention_winner  -- argmax over 40 frontal ATTN head outputs
        - decision_winner   -- argmax over first 14 of 17 frontal DECN head outputs
    """

    def __init__(self, genome: dict | None = None, seed: int = 42) -> None:
        """
        Args:
            genome: v2 genome dict.  Defaults to DEFAULT_GENOME_V2.
            seed: Global RNG seed (also used as base for NCP/Tract wiring seeds).
        """
        super().__init__()

        if genome is None:
            genome = DEFAULT_GENOME_V2
        self._genome: dict = copy.deepcopy(genome)

        valid, errors = validate_genome_v2(self._genome)
        if not valid:
            raise ValueError("Invalid v2 genome:\n" + "\n".join(errors))

        torch.manual_seed(seed)
        np.random.seed(seed)
        self._seed = seed

        modules_cfg = self._genome["modules"]
        tracts_cfg = self._genome["tracts"]

        # ------------------------------------------------------------------
        # Per-module NCP hidden sizes (needed for SignalRouter construction)
        # ------------------------------------------------------------------
        self._hidden_sizes: dict[str, int] = {
            name: _hidden_size(modules_cfg[name]) for name in MODULE_NAMES_V2
        }

        # ------------------------------------------------------------------
        # Build TractBanks, SignalRouters, CfC modules, and linear heads
        # ------------------------------------------------------------------

        # Seed offsets: each module gets a block of 100 seed slots.
        _seed_block = {name: seed + i * 100 for i, name in enumerate(MODULE_NAMES_V2)}

        # Containers as nn.ModuleDicts so parameters are registered.
        self.tract_banks: nn.ModuleDict = nn.ModuleDict()
        self.routers: nn.ModuleDict = nn.ModuleDict()
        self.cfcs: nn.ModuleDict = nn.ModuleDict()

        for mod_name in MODULE_NAMES_V2:
            mod_cfg = modules_cfg[mod_name]
            hidden_sz = self._hidden_sizes[mod_name]
            mod_seed = _seed_block[mod_name]

            # --- TractBank ---
            # Collect all enabled tracts targeting this module.
            tract_specs: list[dict] = []
            for tract_name, tract in tracts_cfg.items():
                if tract.get("dst_module") == mod_name and tract.get("enabled", False):
                    tract_specs.append({
                        "name": tract_name,
                        "src_size": tract["src_size"],
                        "dst_size": tract["dst_size"],
                        "connections": tract["connections"],
                        "enabled": True,
                    })
            self.tract_banks[mod_name] = TractBank(tract_specs, base_seed=mod_seed)

            # --- SignalRouter ---
            input_specs = get_module_input_specs(self._genome, mod_name)
            self.routers[mod_name] = SignalRouter(
                data_specs=input_specs["data"],
                mod_specs=input_specs["mod"],
                mem_specs=input_specs["mem"],
                hidden_size=hidden_sz,
            )

            # --- CfC ---
            data_input_size = self.routers[mod_name].data_size
            cfc = _build_cfc_module(data_input_size, mod_cfg, seed=mod_seed)
            _apply_time_bias(cfc, mod_cfg["time_bias"])
            self.cfcs[mod_name] = cfc

        # ------------------------------------------------------------------
        # Frontal output heads: motor neurons -> ATTN and DECN logits
        # ------------------------------------------------------------------
        frontal_motor = modules_cfg["frontal"]["motor_neurons"]  # 150
        self.attn_head = nn.Linear(frontal_motor, N_ATTENTION)   # 150 -> 40
        self.decn_head = nn.Linear(frontal_motor, N_DECISION)    # 150 -> 17
        self.value_head = nn.Linear(frontal_motor, 1)            # 150 -> 1 (A2C critic)

        # ------------------------------------------------------------------
        # Hidden states (one per module; None means "no prior tick")
        # ------------------------------------------------------------------
        self._hx: dict[str, Tensor | None] = {name: None for name in MODULE_NAMES_V2}

        # ------------------------------------------------------------------
        # Previous-tick inter-module outputs (used as feedback inputs)
        # Initialised to zeros; shape = (1, output_size).
        # ------------------------------------------------------------------
        self._prev_outputs: dict[str, Tensor] = {}
        for name in MODULE_NAMES_V2:
            out_sz = modules_cfg[name]["output_size"]
            self._prev_outputs[name] = torch.zeros(1, out_sz)

        # ------------------------------------------------------------------
        # RL baseline (exponential moving average of observed rewards)
        # ------------------------------------------------------------------
        self._reward_baseline: float = 0.0

        # Tick counter (incremented by every call to tick())
        self._tick_count: int = 0

        logger.info(
            "MultiLobeBrainV2 initialised: "
            + ", ".join(
                f"{n}={modules_cfg[n]['output_size']}mo"
                for n in MODULE_NAMES_V2
            )
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _ensure_batch(t: Tensor) -> Tensor:
        """Add a batch dimension if tensor is 1-D."""
        if t.dim() == 1:
            return t.unsqueeze(0)
        return t

    @staticmethod
    def _extract_chemicals(full_chemicals: Tensor, indices: list[int]) -> Tensor:
        """Extract a subset of chemicals from the full 256-dim chemical tensor.

        Args:
            full_chemicals: Tensor of shape (batch, 256).
            indices: List of chemical indices to extract.

        Returns:
            Tensor of shape (batch, len(indices)).
        """
        idx_t = torch.tensor(indices, dtype=torch.long, device=full_chemicals.device)
        return full_chemicals[:, idx_t]

    def _forward_module(
        self,
        mod_name: str,
        data_input: Tensor,
        hx: Tensor | None,
    ) -> tuple[Tensor, Tensor]:
        """Run a single CfC module forward pass.

        Args:
            mod_name: Module name (used to look up self.cfcs).
            data_input: (batch, data_size) -- CfC sensory input.
            hx: Previous hidden state (batch, hidden_size) or None.

        Returns:
            (output, new_hx) where output is (batch, motor_neurons).
        """
        cfc = self.cfcs[mod_name]
        input_seq = data_input.unsqueeze(1)  # (batch, 1, data_size)
        output, new_hx = cfc(input_seq, hx)
        # output: (batch, motor_neurons) when return_sequences=False
        return output, new_hx

    def _gather_module_raw_inputs(
        self,
        module_name: str,
        raw_inputs: dict[str, Tensor],
        chemicals: Tensor,
        ltm: Tensor,
        current_outputs: dict[str, Tensor],
    ) -> dict[str, Tensor]:
        """Construct the complete raw-input dict for a module's TractBank.

        Each tract in the genome specifies a ``src`` name.  This method
        resolves the ``src`` to an actual tensor:

        - External sources ("visn", "smel", etc.) -> raw_inputs[mapped_key]
        - "chem" -> the pre-extracted chemical tensor
        - "ltm"  -> the LTM recall tensor
        - Module sources ("thalamus", "amygdala", etc.) ->
            current_outputs[src_name]  (caller decides which tick's outputs)

        Only tracts that target ``module_name`` and are enabled are
        included in the result.

        Args:
            module_name: The target module (e.g. "thalamus").
            raw_inputs: External sensory inputs keyed as in _EXTERNAL_SRC_KEYS.
            chemicals: (batch, N_CHEM_SELECTED) extracted chemical tensor.
            ltm: (batch, N_LTM) LTM recall tensor.
            current_outputs: Dict of module name -> tensor for inter-module flow.
                             Caller provides previous-tick or current-tick outputs
                             depending on the processing stage.

        Returns:
            Dict mapping tract name -> raw tensor (batch, src_size).
        """
        tracts_cfg = self._genome["tracts"]
        result: dict[str, Tensor] = {}

        for tract_name, tract in tracts_cfg.items():
            if not tract.get("enabled", False):
                continue
            if tract.get("dst_module") != module_name:
                continue

            src = tract["src"]

            if src in _EXTERNAL_SRC_KEYS:
                key = _EXTERNAL_SRC_KEYS[src]
                if key not in raw_inputs:
                    # Missing external input -- fill with zeros
                    batch = next(
                        (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)),
                        1,
                    )
                    device = next(
                        (t.device for t in raw_inputs.values() if isinstance(t, Tensor)),
                        torch.device("cpu"),
                    )
                    result[tract_name] = torch.zeros(batch, tract["src_size"], device=device)
                else:
                    result[tract_name] = self._ensure_batch(raw_inputs[key])

            elif src == "chem":
                result[tract_name] = chemicals

            elif src == "ltm":
                result[tract_name] = ltm

            elif src in _MODULE_SRCS:
                if src in current_outputs:
                    result[tract_name] = current_outputs[src]
                else:
                    # Source module output not yet available -- use zeros
                    batch = next(
                        (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)),
                        1,
                    )
                    device = next(
                        (t.device for t in raw_inputs.values() if isinstance(t, Tensor)),
                        torch.device("cpu"),
                    )
                    result[tract_name] = torch.zeros(batch, tract["src_size"], device=device)

            else:
                logger.warning("Unknown tract src '%s' in tract '%s'", src, tract_name)

        return result

    # -----------------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------------

    def tick(
        self,
        raw_inputs: dict[str, Tensor],
        ltm_injection: dict[str, float] | None = None,
    ) -> BrainOutput:
        """Run one tick of the hierarchical brain.

        Processing order (strict):
            1. Thalamus    -- external sensory + previous-tick amyg/hipp feedback
            2. Hippocampus -- current thalamus output + previous-tick amyg feedback
            3. Amygdala    -- current thalamus + current hippocampus output
            4. Frontal     -- current thal + hipp + amyg outputs + noun/verb/chem/ltm

        Previous-tick feedback is read from self._prev_outputs at the START
        of the tick and is not modified until all four modules have run.

        Args:
            raw_inputs: Dict of named tensors.  Expected keys (all optional,
                        zeros used for missing):
                          "visn"      (batch, 40)   -- attention/vision lobe values
                          "smel"      (batch, 40)   -- olfaction / smell CA
                          "prox"      (batch, 20)   -- proximity CA
                          "sitn"      (batch, 9)    -- situation neurons
                          "location"  (batch, 2)    -- x, y position (normalised)
                          "stim"      (batch, 40)   -- stimulus lobe
                          "detl"      (batch, 11)   -- detail neurons
                          "driv"      (batch, 20)   -- drive lobe values
                          "noun"      (batch, 40)   -- noun lobe (language)
                          "verb"      (batch, 17)   -- verb lobe (language)
                          "chemicals" (batch, 256)  -- full chemical vector
            ltm_injection: Optional dict of named memory values (max 6 keys,
                           values in [0, 1]).  Missing values filled with 0.

        Returns:
            BrainOutput with attention_winner, decision_winner, and raw values.
        """
        # ------------------------------------------------------------------
        # Step 0: Prepare chemicals and LTM
        # ------------------------------------------------------------------
        if "chemicals" in raw_inputs:
            full_chem = self._ensure_batch(raw_inputs["chemicals"])
        else:
            batch = next(
                (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)), 1
            )
            device = next(
                (t.device for t in raw_inputs.values() if isinstance(t, Tensor)),
                torch.device("cpu"),
            )
            full_chem = torch.zeros(batch, 256, device=device)

        # Extract the 16 selected chemicals for amygdala / frontal modulation
        amyg_chem = self._extract_chemicals(full_chem, AMYGDALA_CHEM_INDICES)  # (B, 16)
        fron_chem = self._extract_chemicals(full_chem, FRONTAL_CHEM_INDICES)   # (B, 16)

        # LTM tensor (B, 6)
        batch_sz = full_chem.shape[0]
        device = full_chem.device
        ltm_vec = torch.zeros(batch_sz, N_LTM, device=device)
        if ltm_injection:
            for i, k in enumerate(sorted(ltm_injection.keys())[:N_LTM]):
                ltm_vec[0, i] = float(ltm_injection[k])

        # Snapshot previous-tick outputs (feedback flows read these)
        prev = {name: t.to(device) for name, t in self._prev_outputs.items()}

        # Accumulate current-tick module outputs as each stage completes
        current: dict[str, Tensor] = {}

        # ------------------------------------------------------------------
        # Step 1: THALAMUS
        #   Data:       visn, smel, prox, sitn, loc, stim, detl
        #   Modulation: driv, amygdala (PREVIOUS tick)
        #   Memory:     hippocampus (PREVIOUS tick)
        # ------------------------------------------------------------------
        thal_raw = self._gather_module_raw_inputs(
            "thalamus", raw_inputs, amyg_chem, ltm_vec,
            current_outputs={
                "amygdala": prev["amygdala"],
                "hippocampus": prev["hippocampus"],
            },
        )
        thal_projected = self.tract_banks["thalamus"].project(thal_raw)
        hx_thal = self._hx["thalamus"]
        if hx_thal is not None:
            hx_thal = hx_thal.to(device)
        else:
            hx_thal = torch.zeros(batch_sz, self._hidden_sizes["thalamus"], device=device)
        thal_data, hx_thal_mod = self.routers["thalamus"](thal_projected, hx_thal)
        thal_output, new_hx_thal = self._forward_module("thalamus", thal_data, hx_thal_mod)
        current["thalamus"] = thal_output

        # ------------------------------------------------------------------
        # Step 2: HIPPOCAMPUS
        #   Data:       thalamus (CURRENT), amygdala (PREVIOUS)
        #   Modulation: prox, sitn
        #   Memory:     loc, stim, detl
        # ------------------------------------------------------------------
        hipp_raw = self._gather_module_raw_inputs(
            "hippocampus", raw_inputs, amyg_chem, ltm_vec,
            current_outputs={
                "thalamus": current["thalamus"],
                "amygdala": prev["amygdala"],
            },
        )
        hipp_projected = self.tract_banks["hippocampus"].project(hipp_raw)
        hx_hipp = self._hx["hippocampus"]
        if hx_hipp is not None:
            hx_hipp = hx_hipp.to(device)
        else:
            hx_hipp = torch.zeros(batch_sz, self._hidden_sizes["hippocampus"], device=device)
        hipp_data, hx_hipp_mod = self.routers["hippocampus"](hipp_projected, hx_hipp)
        hipp_output, new_hx_hipp = self._forward_module("hippocampus", hipp_data, hx_hipp_mod)
        current["hippocampus"] = hipp_output

        # ------------------------------------------------------------------
        # Step 3: AMYGDALA
        #   Data:       visn, smel, thalamus (CURRENT)
        #   Modulation: driv, prox, sitn, chem
        #   Memory:     hippocampus (CURRENT)   <- hippocampus ran first
        # ------------------------------------------------------------------
        amyg_raw = self._gather_module_raw_inputs(
            "amygdala", raw_inputs, amyg_chem, ltm_vec,
            current_outputs={
                "thalamus": current["thalamus"],
                "hippocampus": current["hippocampus"],
            },
        )
        amyg_projected = self.tract_banks["amygdala"].project(amyg_raw)
        hx_amyg = self._hx["amygdala"]
        if hx_amyg is not None:
            hx_amyg = hx_amyg.to(device)
        else:
            hx_amyg = torch.zeros(batch_sz, self._hidden_sizes["amygdala"], device=device)
        amyg_data, hx_amyg_mod = self.routers["amygdala"](amyg_projected, hx_amyg)
        amyg_output, new_hx_amyg = self._forward_module("amygdala", amyg_data, hx_amyg_mod)
        current["amygdala"] = amyg_output

        # ------------------------------------------------------------------
        # Step 4: FRONTAL CORTEX
        #   Data:       thal, hipp, amyg (all CURRENT), noun, verb
        #   Modulation: chem (frontal subset)
        #   Memory:     ltm_recall
        # ------------------------------------------------------------------
        fron_raw = self._gather_module_raw_inputs(
            "frontal", raw_inputs, fron_chem, ltm_vec,
            current_outputs={
                "thalamus": current["thalamus"],
                "hippocampus": current["hippocampus"],
                "amygdala": current["amygdala"],
            },
        )
        fron_projected = self.tract_banks["frontal"].project(fron_raw)
        hx_fron = self._hx["frontal"]
        if hx_fron is not None:
            hx_fron = hx_fron.to(device)
        else:
            hx_fron = torch.zeros(batch_sz, self._hidden_sizes["frontal"], device=device)
        fron_data, hx_fron_mod = self.routers["frontal"](fron_projected, hx_fron)
        fron_output, new_hx_fron = self._forward_module("frontal", fron_data, hx_fron_mod)
        current["frontal"] = fron_output

        # ------------------------------------------------------------------
        # Step 5: Update hidden states and feedback outputs
        # ------------------------------------------------------------------
        self._hx["thalamus"] = new_hx_thal.detach()
        self._hx["hippocampus"] = new_hx_hipp.detach()
        self._hx["amygdala"] = new_hx_amyg.detach()
        self._hx["frontal"] = new_hx_fron.detach()

        self._prev_outputs["thalamus"] = current["thalamus"].detach()
        self._prev_outputs["hippocampus"] = current["hippocampus"].detach()
        self._prev_outputs["amygdala"] = current["amygdala"].detach()
        self._prev_outputs["frontal"] = current["frontal"].detach()

        # ------------------------------------------------------------------
        # Step 6: Decode ATTN and DECN from frontal motor outputs via heads
        # ------------------------------------------------------------------
        attn_logits = self.attn_head(fron_output)   # (B, 40)
        decn_logits = self.decn_head(fron_output)   # (B, 17)

        # Winner-Takes-All (argmax); clamp decision to active indices 0-13
        attn_winner = int(attn_logits[0].argmax().item())
        decn_all_14 = decn_logits[0, :14]           # only active neurons
        decn_winner = int(decn_all_14.argmax().item())

        # Build numpy views for BrainOutput
        attn_vals = attn_logits[0].detach().cpu().numpy()   # (40,)
        decn_vals = decn_logits[0].detach().cpu().numpy()   # (17,)

        # Concatenate all module motor outputs for visualisation
        all_activations = torch.cat(
            [current[n][0] for n in MODULE_NAMES_V2], dim=-1
        ).detach().cpu().numpy()

        self._tick_count += 1

        return BrainOutput(
            attention_values=attn_vals,
            decision_values=decn_vals,
            attention_winner=attn_winner,
            decision_winner=decn_winner,
            attention_label=ATTENTION_LABELS[attn_winner],
            decision_label=DECISION_LABELS[decn_winner],
            all_activations=all_activations,
            tick=self._tick_count,
        )

    def wipe(self) -> None:
        """Reset all hidden states and inter-module feedback to zero.

        Call this between episodes or when spawning a new creature to
        prevent hidden state bleed-over.
        """
        self._hx = {name: None for name in MODULE_NAMES_V2}
        modules_cfg = self._genome["modules"]
        for name in MODULE_NAMES_V2:
            out_sz = modules_cfg[name]["output_size"]
            self._prev_outputs[name] = torch.zeros(1, out_sz)
        logger.debug("MultiLobeBrainV2: hidden states wiped")

    def save_weights(self, path: str = "brain_weights_v2.pt") -> None:
        """Save model state, genome, tick counter, and reward baseline.

        Args:
            path: File path for the checkpoint.
        """
        checkpoint = {
            "state_dict": self.state_dict(),
            "genome": self._genome,
            "tick_count": self._tick_count,
            "reward_baseline": self._reward_baseline,
        }
        torch.save(checkpoint, path)
        logger.info("MultiLobeBrainV2: weights saved to '%s'", path)

    def load_weights(self, path: str = "brain_weights_v2.pt") -> None:
        """Load model state from a checkpoint.

        Restores state_dict and genome meta-data.  Hidden states are reset
        to zero (the creature needs a fresh tick to re-initialise its state).

        Args:
            path: File path of the checkpoint to load.
        """
        checkpoint = torch.load(path, weights_only=False)
        # strict=False allows loading old checkpoints that lack value_head
        self.load_state_dict(checkpoint["state_dict"], strict=False)
        self._genome = checkpoint.get("genome", self._genome)
        self._tick_count = checkpoint.get("tick_count", 0)
        self._reward_baseline = checkpoint.get("reward_baseline", 0.0)
        self.wipe()
        logger.info("MultiLobeBrainV2: weights loaded from '%s'", path)

    # -----------------------------------------------------------------------
    # Training
    # -----------------------------------------------------------------------

    def train_on_observations(
        self,
        observations: list[dict],
        epochs: int = 100,
        lr: float = 0.005,
    ) -> list[float]:
        """Supervised behaviour cloning via cross-entropy on attn/decn targets.

        Each observation dict should contain:
            "raw_inputs"    : dict[str, Tensor]  -- sensory inputs
            "attn_target"   : int                -- ground-truth attention winner
            "decn_target"   : int                -- ground-truth decision winner (0-13)
            "ltm_injection" : dict | None        -- optional LTM values

        Per-module learning rate scaling:
            - thalamus, frontal, tract_banks, routers, attn_head, decn_head: lr
            - amygdala:   lr * 0.6
            - hippocampus: lr * 0.4

        Args:
            observations: List of observation dicts.
            epochs: Number of passes over the dataset.
            lr: Base learning rate.

        Returns:
            List of per-epoch mean losses.
        """
        lr_scale: dict[str, float] = {
            "thalamus": 1.0,
            "amygdala": 0.6,
            "hippocampus": 0.4,
            "frontal": 1.0,
        }
        param_groups: list[dict] = []
        for mod_name in MODULE_NAMES_V2:
            scale = lr_scale[mod_name]
            param_groups.append({
                "params": list(self.cfcs[mod_name].parameters()),
                "lr": lr * scale,
            })
            param_groups.append({
                "params": list(self.tract_banks[mod_name].parameters()),
                "lr": lr,
            })
            param_groups.append({
                "params": list(self.routers[mod_name].parameters()),
                "lr": lr,
            })
        param_groups.append({"params": list(self.attn_head.parameters()), "lr": lr})
        param_groups.append({"params": list(self.decn_head.parameters()), "lr": lr})

        optimizer = torch.optim.Adam(param_groups)

        epoch_losses: list[float] = []
        self.train()
        device = next(self.parameters()).device

        # Pre-batch all observations for GPU-efficient training.
        # CfC hidden states are wiped between batches (each sample is independent
        # in supervised pre-training - no temporal sequence).
        batch_size = min(64, len(observations))
        batches = []
        for i in range(0, len(observations), batch_size):
            chunk = observations[i : i + batch_size]
            all_raw = [self._adapt_observation(o) for o in chunk]
            keys = all_raw[0].keys()
            batched = {
                k: torch.cat([r[k] for r in all_raw], dim=0).to(device)
                for k in keys
            }
            attn_t = torch.tensor(
                [o.get("attn_target", o.get("attn_winner", 0)) for o in chunk],
                dtype=torch.long, device=device,
            )
            decn_t = torch.tensor(
                [o.get("decn_target", o.get("decn_winner", 0)) for o in chunk],
                dtype=torch.long, device=device,
            )
            batches.append((batched, attn_t, decn_t))

        logger.info("Training: %d batches of %d (device=%s)", len(batches), batch_size, device)

        # Number of warm-up ticks before the loss tick.  Teaches the CfC to
        # maintain correct decisions across ticks (not just at tick 1).
        # Empirical: eat-action rate drops from 55% at tick 1 to 5% by tick 3+
        # without this.  3 warm-up + 1 loss tick = 4 total ticks per sample.
        N_PRETRAIN_TICKS = 3

        for epoch in range(epochs):
            epoch_loss = 0.0
            for b_inputs, b_attn, b_decn in batches:
                self.wipe()

                # Warm-up ticks: build CfC hidden state without tracking gradients.
                # Each call mirrors _supervised_forward but DOES write back to
                # self._hx so the hidden state carries over into the loss tick.
                if N_PRETRAIN_TICKS > 1:
                    with torch.no_grad():
                        for _ in range(N_PRETRAIN_TICKS - 1):
                            self._supervised_forward_update_hx(b_inputs, None)

                # Loss tick: full forward pass with gradient tracking.
                optimizer.zero_grad()
                loss = self._supervised_forward(b_inputs, b_attn, b_decn, None)
                loss.backward()
                nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
                optimizer.step()
                epoch_loss += loss.item() * b_attn.shape[0]

            mean_loss = epoch_loss / max(len(observations), 1)
            epoch_losses.append(mean_loss)
            if epoch % 10 == 0:
                logger.debug("train epoch %d/%d -- loss=%.4f", epoch + 1, epochs, mean_loss)

        self.train(False)  # switch to inference mode
        return epoch_losses

    @staticmethod
    def _adapt_observation(obs: dict) -> dict[str, Tensor]:
        """Convert an observation dict to raw_inputs tensor dict.

        Accepts two formats:
          1. v2 native: {"raw_inputs": dict[str, Tensor], ...}
          2. v1/instinct: {"lobes": {name: list[float]}, "chemicals": list[float], ...}

        Returns a dict of (1, N) tensors keyed by lobe name + "chemicals" + "location".
        """
        if "raw_inputs" in obs:
            return obs["raw_inputs"]

        # v1/instinct format adaptation
        lobes = obs.get("lobes", {})
        raw: dict[str, Tensor] = {}
        for key, values in lobes.items():
            raw[key] = torch.tensor([values], dtype=torch.float32)

        if "chemicals" in obs:
            raw["chemicals"] = torch.tensor([obs["chemicals"]], dtype=torch.float32)
        else:
            raw["chemicals"] = torch.zeros(1, 256)

        if "location" not in raw:
            raw["location"] = torch.zeros(1, 2)

        return raw

    def _supervised_forward_update_hx(
        self,
        raw_inputs: dict[str, Tensor],
        ltm_injection: dict[str, float] | None,
    ) -> None:
        """Warm-up forward pass for multi-tick pre-training.

        Runs one full forward pass through all four modules and writes the
        new hidden states back to self._hx (exactly as tick() does).  Called
        under torch.no_grad() to build CfC temporal state cheaply without
        storing a computation graph.

        This is intentionally separate from _supervised_forward so that the
        loss tick can be called independently without polluting its gradient
        graph with warm-up state.

        Args:
            raw_inputs: Batched sensory input dict (same format as tick()).
            ltm_injection: Optional LTM values (typically None during pre-training).
        """
        if "chemicals" in raw_inputs:
            full_chem = self._ensure_batch(raw_inputs["chemicals"])
        else:
            batch = next(
                (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)), 1
            )
            full_chem = torch.zeros(batch, 256)

        amyg_chem = self._extract_chemicals(full_chem, AMYGDALA_CHEM_INDICES)
        fron_chem = self._extract_chemicals(full_chem, FRONTAL_CHEM_INDICES)
        batch_sz = full_chem.shape[0]
        device = full_chem.device

        ltm_vec = torch.zeros(batch_sz, N_LTM, device=device)
        if ltm_injection:
            for i, k in enumerate(sorted(ltm_injection.keys())[:N_LTM]):
                ltm_vec[0, i] = float(ltm_injection[k])

        # Expand prev outputs to match batch size
        prev: dict[str, Tensor] = {}
        for name, t in self._prev_outputs.items():
            t = t.to(device)
            if t.shape[0] != batch_sz:
                t = t.expand(batch_sz, -1)
            prev[name] = t
        current: dict[str, Tensor] = {}

        def _get_hx(name: str) -> Tensor:
            hx = self._hx[name]
            if hx is None:
                return torch.zeros(batch_sz, self._hidden_sizes[name], device=device)
            if hx.shape[0] != batch_sz:
                return hx.to(device).expand(batch_sz, -1)
            return hx.to(device)

        # Thalamus
        thal_raw = self._gather_module_raw_inputs(
            "thalamus", raw_inputs, amyg_chem, ltm_vec,
            {"amygdala": prev["amygdala"], "hippocampus": prev["hippocampus"]},
        )
        thal_data, hx_thal_mod = self.routers["thalamus"](
            self.tract_banks["thalamus"].project(thal_raw), _get_hx("thalamus")
        )
        current["thalamus"], new_hx_thal = self._forward_module("thalamus", thal_data, hx_thal_mod)

        # Hippocampus
        hipp_raw = self._gather_module_raw_inputs(
            "hippocampus", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "amygdala": prev["amygdala"]},
        )
        hipp_data, hx_hipp_mod = self.routers["hippocampus"](
            self.tract_banks["hippocampus"].project(hipp_raw), _get_hx("hippocampus")
        )
        current["hippocampus"], new_hx_hipp = self._forward_module("hippocampus", hipp_data, hx_hipp_mod)

        # Amygdala
        amyg_raw = self._gather_module_raw_inputs(
            "amygdala", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "hippocampus": current["hippocampus"]},
        )
        amyg_data, hx_amyg_mod = self.routers["amygdala"](
            self.tract_banks["amygdala"].project(amyg_raw), _get_hx("amygdala")
        )
        current["amygdala"], new_hx_amyg = self._forward_module("amygdala", amyg_data, hx_amyg_mod)

        # Frontal
        fron_raw = self._gather_module_raw_inputs(
            "frontal", raw_inputs, fron_chem, ltm_vec,
            {n: current[n] for n in ("thalamus", "hippocampus", "amygdala")},
        )
        fron_data, hx_fron_mod = self.routers["frontal"](
            self.tract_banks["frontal"].project(fron_raw), _get_hx("frontal")
        )
        _, new_hx_fron = self._forward_module("frontal", fron_data, hx_fron_mod)

        # Write hidden states back so the next tick sees evolved state
        self._hx["thalamus"] = new_hx_thal.detach()
        self._hx["hippocampus"] = new_hx_hipp.detach()
        self._hx["amygdala"] = new_hx_amyg.detach()
        self._hx["frontal"] = new_hx_fron.detach()

        # Update prev_outputs for feedback tracts on the next tick
        self._prev_outputs["thalamus"] = current["thalamus"].detach()
        self._prev_outputs["hippocampus"] = current["hippocampus"].detach()
        self._prev_outputs["amygdala"] = current["amygdala"].detach()

    def _supervised_forward(
        self,
        raw_inputs: dict[str, Tensor],
        attn_target: Tensor,
        decn_target: Tensor,
        ltm_injection: dict[str, float] | None,
    ) -> Tensor:
        """Forward pass that preserves gradients for supervised training.

        Mirrors tick() but does NOT call .detach() on intermediate tensors
        so that loss.backward() can propagate gradients through the full graph.

        Returns:
            Scalar loss tensor (CE on attn + CE on decn).
        """
        if "chemicals" in raw_inputs:
            full_chem = self._ensure_batch(raw_inputs["chemicals"])
        else:
            batch = next(
                (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)), 1
            )
            full_chem = torch.zeros(batch, 256)

        amyg_chem = self._extract_chemicals(full_chem, AMYGDALA_CHEM_INDICES)
        fron_chem = self._extract_chemicals(full_chem, FRONTAL_CHEM_INDICES)
        batch_sz = full_chem.shape[0]
        device = full_chem.device

        ltm_vec = torch.zeros(batch_sz, N_LTM, device=device)
        if ltm_injection:
            for i, k in enumerate(sorted(ltm_injection.keys())[:N_LTM]):
                ltm_vec[0, i] = float(ltm_injection[k])

        # Expand prev outputs to match batch size (they may be batch=1 from init)
        prev: dict[str, Tensor] = {}
        for name, t in self._prev_outputs.items():
            t = t.to(device)
            if t.shape[0] != batch_sz:
                t = t.expand(batch_sz, -1)
            prev[name] = t
        current: dict[str, Tensor] = {}

        def _get_hx(name: str) -> Tensor:
            hx = self._hx[name]
            if hx is None:
                return torch.zeros(batch_sz, self._hidden_sizes[name], device=device)
            if hx.shape[0] != batch_sz:
                return hx.to(device).expand(batch_sz, -1)
            return hx.to(device)

        # Thalamus
        thal_raw = self._gather_module_raw_inputs(
            "thalamus", raw_inputs, amyg_chem, ltm_vec,
            {"amygdala": prev["amygdala"], "hippocampus": prev["hippocampus"]},
        )
        thal_data, hx_thal_mod = self.routers["thalamus"](
            self.tract_banks["thalamus"].project(thal_raw), _get_hx("thalamus")
        )
        current["thalamus"], _ = self._forward_module("thalamus", thal_data, hx_thal_mod)

        # Hippocampus
        hipp_raw = self._gather_module_raw_inputs(
            "hippocampus", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "amygdala": prev["amygdala"]},
        )
        hipp_data, hx_hipp_mod = self.routers["hippocampus"](
            self.tract_banks["hippocampus"].project(hipp_raw), _get_hx("hippocampus")
        )
        current["hippocampus"], _ = self._forward_module("hippocampus", hipp_data, hx_hipp_mod)

        # Amygdala
        amyg_raw = self._gather_module_raw_inputs(
            "amygdala", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "hippocampus": current["hippocampus"]},
        )
        amyg_data, hx_amyg_mod = self.routers["amygdala"](
            self.tract_banks["amygdala"].project(amyg_raw), _get_hx("amygdala")
        )
        current["amygdala"], _ = self._forward_module("amygdala", amyg_data, hx_amyg_mod)

        # Frontal
        fron_raw = self._gather_module_raw_inputs(
            "frontal", raw_inputs, fron_chem, ltm_vec,
            {n: current[n] for n in ("thalamus", "hippocampus", "amygdala")},
        )
        fron_data, hx_fron_mod = self.routers["frontal"](
            self.tract_banks["frontal"].project(fron_raw), _get_hx("frontal")
        )
        fron_out, _ = self._forward_module("frontal", fron_data, hx_fron_mod)

        attn_logits = self.attn_head(fron_out)   # (B, 40)
        decn_logits = self.decn_head(fron_out)   # (B, 17)

        return (
            F.cross_entropy(attn_logits, attn_target)
            + F.cross_entropy(decn_logits, decn_target)
        )

    def forward_with_policy(
        self,
        raw_inputs: dict[str, Tensor],
    ) -> tuple[int, int, "Tensor", "Tensor", "Tensor"]:
        """Forward pass that returns policy info for A2C training.

        Returns:
            (attn_winner, decn_winner, log_prob, entropy, value_estimate)
            All tensors retain gradients for backward pass.
        """
        self.train()

        if "chemicals" in raw_inputs:
            full_chem = self._ensure_batch(raw_inputs["chemicals"])
        else:
            batch = next(
                (t.shape[0] for t in raw_inputs.values() if isinstance(t, Tensor)), 1
            )
            full_chem = torch.zeros(batch, 256)

        amyg_chem = self._extract_chemicals(full_chem, AMYGDALA_CHEM_INDICES)
        fron_chem = self._extract_chemicals(full_chem, FRONTAL_CHEM_INDICES)
        batch_sz = full_chem.shape[0]
        device = full_chem.device
        ltm_vec = torch.zeros(batch_sz, N_LTM, device=device)

        prev = {name: t.to(device) for name, t in self._prev_outputs.items()}
        current: dict[str, Tensor] = {}

        def _get_hx(name: str) -> Tensor:
            hx = self._hx[name]
            if hx is None:
                return torch.zeros(batch_sz, self._hidden_sizes[name], device=device)
            return hx.to(device)

        # Sequential processing: Thalamus → Hippocampus → Amygdala → Frontal
        thal_raw = self._gather_module_raw_inputs(
            "thalamus", raw_inputs, amyg_chem, ltm_vec,
            {"amygdala": prev["amygdala"], "hippocampus": prev["hippocampus"]},
        )
        thal_data, hx_thal_mod = self.routers["thalamus"](
            self.tract_banks["thalamus"].project(thal_raw), _get_hx("thalamus")
        )
        current["thalamus"], _ = self._forward_module("thalamus", thal_data, hx_thal_mod)

        hipp_raw = self._gather_module_raw_inputs(
            "hippocampus", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "amygdala": prev["amygdala"]},
        )
        hipp_data, hx_hipp_mod = self.routers["hippocampus"](
            self.tract_banks["hippocampus"].project(hipp_raw), _get_hx("hippocampus")
        )
        current["hippocampus"], _ = self._forward_module("hippocampus", hipp_data, hx_hipp_mod)

        amyg_raw = self._gather_module_raw_inputs(
            "amygdala", raw_inputs, amyg_chem, ltm_vec,
            {"thalamus": current["thalamus"], "hippocampus": current["hippocampus"]},
        )
        amyg_data, hx_amyg_mod = self.routers["amygdala"](
            self.tract_banks["amygdala"].project(amyg_raw), _get_hx("amygdala")
        )
        current["amygdala"], _ = self._forward_module("amygdala", amyg_data, hx_amyg_mod)

        fron_raw = self._gather_module_raw_inputs(
            "frontal", raw_inputs, fron_chem, ltm_vec,
            {n: current[n] for n in ("thalamus", "hippocampus", "amygdala")},
        )
        fron_data, hx_fron_mod = self.routers["frontal"](
            self.tract_banks["frontal"].project(fron_raw), _get_hx("frontal")
        )
        fron_out, _ = self._forward_module("frontal", fron_data, hx_fron_mod)

        attn_logits = self.attn_head(fron_out)   # (B, 40)
        decn_logits = self.decn_head(fron_out)   # (B, 17)
        value = self.value_head(fron_out)         # (B, 1)

        # Policy: log_prob of chosen actions
        attn_log_probs = F.log_softmax(attn_logits, dim=-1)
        decn_log_probs = F.log_softmax(decn_logits, dim=-1)

        attn_winner = int(attn_logits[0].argmax().item())
        decn_winner = int(decn_logits[0, :14].argmax().item())

        log_prob = attn_log_probs[0, attn_winner] + decn_log_probs[0, decn_winner]

        # Entropy for exploration bonus
        attn_entropy = -(F.softmax(attn_logits, dim=-1) * attn_log_probs).sum(dim=-1).mean()
        decn_entropy = -(F.softmax(decn_logits, dim=-1) * decn_log_probs).sum(dim=-1).mean()
        entropy = attn_entropy + decn_entropy

        self.train(False)
        return attn_winner, decn_winner, log_prob, entropy, value.squeeze(-1)

    def train_a2c_batch(
        self,
        trace_log_probs: list["Tensor"],
        trace_entropies: list["Tensor"],
        trace_values: list["Tensor"],
        reward: float,
        gamma: float = 0.95,
        entropy_coeff: float = 0.1,
        value_coeff: float = 0.5,
        lr: float = 0.0005,
    ) -> float:
        """A2C update using an eligibility trace of past (log_prob, entropy, value).

        Distributes reward backwards through the trace with exponential decay
        (γ^k weighting). Each entry in the trace gets credit proportional to
        how recently it occurred.

        Args:
            trace_log_probs: List of log_prob tensors from recent ticks.
            trace_entropies: List of entropy tensors from recent ticks.
            trace_values: List of value estimate tensors from recent ticks.
            reward: Scalar reward signal (positive=good, negative=bad).
            gamma: Discount factor for temporal credit assignment.
            entropy_coeff: Weight for entropy bonus (exploration).
            value_coeff: Weight for value function loss (critic).
            lr: Learning rate.

        Returns:
            Scalar loss value (float).
        """
        if not trace_log_probs:
            return 0.0

        optimizer = torch.optim.Adam(self.parameters(), lr=lr)
        optimizer.zero_grad()
        self.train()

        total_policy_loss = torch.tensor(0.0)
        total_value_loss = torch.tensor(0.0)
        total_entropy = torch.tensor(0.0)
        n = len(trace_log_probs)

        # Distribute reward backwards: most recent gets γ^0, oldest gets γ^(n-1)
        for i in range(n):
            # i=0 is oldest, i=n-1 is most recent
            age = n - 1 - i  # 0 for most recent, n-1 for oldest
            discounted_reward = reward * (gamma ** age)

            value_est = trace_values[i]
            advantage = discounted_reward - value_est.detach()

            # Policy gradient: -log_prob * advantage
            total_policy_loss = total_policy_loss - trace_log_probs[i] * advantage

            # Value loss: MSE between value estimate and discounted reward
            total_value_loss = total_value_loss + (value_est - discounted_reward) ** 2

            # Entropy bonus
            total_entropy = total_entropy + trace_entropies[i]

        # Average over trace length
        total_policy_loss = total_policy_loss / n
        total_value_loss = total_value_loss / n
        total_entropy = total_entropy / n

        loss = total_policy_loss + value_coeff * total_value_loss - entropy_coeff * total_entropy

        loss.backward()
        nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
        optimizer.step()

        self.train(False)
        return float(loss.item())
