"""Genome configuration system for NB Brain Architecture v2 (1/10 scale).

Defines the default genome, validation, mutation, crossover, serialisation,
and input-spec helpers for the v2 multi-module CfC brain.

Key differences from v1 (brain_genome.py):
  - Module list uses "frontal" (not "prefrontal"); four modules total.
  - Every module gains ``sensory_neurons`` and ``output_size`` fields.
  - Every tract gains a ``signal_type`` field: "data", "mod", or "mem".
    - "data"  - raw information; concatenated into the CfC input vector.
    - "mod"   - gain control; multiplied against hidden state via sigmoid gate.
    - "mem"   - context/memory; gated additive injection into hidden state.
  - Inter-module tracts are bidirectional where the biology demands it:
      hippocampus ↔ amygdala, hippocampus → thalamus (mem), amygdala → thalamus (mod).
  - Top-level ``scale`` field records that this is the 1/10 prototype (1,100 total
    neurons vs the full 11,000 neuron target).
  - ``get_module_input_specs()`` returns a typed breakdown of all incoming tracts,
    ready for consumption by SignalRouter.

Reference: NB Brain Architecture v2 spec, sections 5.1–5.3.
"""

import copy
import json
import random
from typing import Any

# ---------------------------------------------------------------------------
# Chemical index constants
# ---------------------------------------------------------------------------

# 16 key chemicals used for amygdala and frontal modulation tracts.
# Sources: ChemicalNames.catalogue (openc2e), docs/reference/game-files-analysis.md §6.
AMYGDALA_CHEM_INDICES: list[int] = [
    204,  # reward
    205,  # punishment
    117,  # adrenalin
    161,  # fear           (drive chemical)
    160,  # anger          (drive chemical)
    148,  # pain           (drive chemical)
    149,  # hunger_protein (drive chemical)
    150,  # hunger_carb    (drive chemical)
    151,  # hunger_fat     (drive chemical)
    156,  # loneliness     (drive chemical)
    159,  # boredom        (drive chemical)
    162,  # sex_drive      (drive chemical)
    163,  # comfort        (drive chemical)
    128,  # stress
    127,  # injury
    125,  # life
]

# Same 16 chemicals used for the frontal chemical modulation tract.
FRONTAL_CHEM_INDICES: list[int] = AMYGDALA_CHEM_INDICES

# ---------------------------------------------------------------------------
# Valid values for categorical parameters
# ---------------------------------------------------------------------------

VALID_TIME_BIASES: set[str] = {"fast", "mixed", "slow", "moderate"}
SIGNAL_TYPES: set[str] = {"data", "mod", "mem"}

# ---------------------------------------------------------------------------
# Module names - canonical ordering for v2
# ---------------------------------------------------------------------------

MODULE_NAMES_V2: list[str] = ["thalamus", "amygdala", "hippocampus", "frontal"]

# ---------------------------------------------------------------------------
# Required key sets (used by the validator)
# ---------------------------------------------------------------------------

REQUIRED_MODULE_KEYS_V2: set[str] = {
    "sensory_neurons",
    "inter_neurons",
    "command_neurons",
    "motor_neurons",
    "sensory_fanout",
    "inter_fanout",
    "recurrent_command_synapses",
    "motor_fanin",
    "time_bias",
    "output_size",
}

REQUIRED_TRACT_KEYS_V2: set[str] = {
    "src",
    "src_size",
    "dst_module",
    "dst_size",
    "connections",
    "signal_type",
    "enabled",
}

# ---------------------------------------------------------------------------
# Default genome v2 - 1/10 scale (1,100 neurons total)
# ---------------------------------------------------------------------------
# Module totals:
#   thalamus    40 + 50 + 30 + 40 = 160
#   amygdala    25 + 35 + 25 + 25 = 110
#   hippocampus 40 + 50 + 30 + 40 = 160
#   frontal    150 +220 +150 +150 = 670
#   TOTAL = 1,100
# ---------------------------------------------------------------------------

DEFAULT_GENOME_V2: dict[str, Any] = {
    "version": 2,
    "seed": 42,
    "scale": 0.1,  # 1/10 of full 11,000-neuron target

    # ------------------------------------------------------------------
    # Module specifications
    # ------------------------------------------------------------------
    "modules": {

        # Thalamus - fast sensory relay, drives attention outputs (40 motor neurons).
        "thalamus": {
            "sensory_neurons": 40,    # receives external sensory inputs
            "inter_neurons": 50,      # internal NCP inter layer
            "command_neurons": 30,    # internal NCP command layer
            "motor_neurons": 40,      # outputs: attention selection + inter-module
            "sensory_fanout": 6,
            "inter_fanout": 4,
            "recurrent_command_synapses": 6,
            "motor_fanin": 4,
            "time_bias": "fast",
            "output_size": 40,        # = motor_neurons; used for inter-module projection
        },

        # Amygdala - emotional evaluation, modulated by drives and chemicals.
        "amygdala": {
            "sensory_neurons": 25,
            "inter_neurons": 35,
            "command_neurons": 25,
            "motor_neurons": 25,
            "sensory_fanout": 6,
            "inter_fanout": 4,
            "recurrent_command_synapses": 6,
            "motor_fanin": 4,
            "time_bias": "mixed",
            "output_size": 25,
        },

        # Hippocampus - context and memory building, slow integration.
        "hippocampus": {
            "sensory_neurons": 40,
            "inter_neurons": 50,
            "command_neurons": 30,
            "motor_neurons": 40,
            "sensory_fanout": 6,
            "inter_fanout": 4,
            "recurrent_command_synapses": 6,
            "motor_fanin": 4,
            "time_bias": "slow",
            "output_size": 40,
        },

        # Frontal - decision-making and action selection (17 decision outputs active).
        "frontal": {
            "sensory_neurons": 150,
            "inter_neurons": 220,
            "command_neurons": 150,
            "motor_neurons": 150,
            "sensory_fanout": 8,
            "inter_fanout": 6,
            "recurrent_command_synapses": 8,
            "motor_fanin": 6,
            "time_bias": "moderate",
            "output_size": 150,
        },
    },

    # ------------------------------------------------------------------
    # Tract specifications
    #
    # Naming convention: "{src}_to_{dst}_{signal_type}"
    # For inter-module tracts src is the module name, not "_out" suffixed.
    #
    # src_size for inter-module tracts = source module's output_size.
    # dst_size is the projection width at the destination:
    #   - 10–20 for data projections (additive input)
    #   - ~inter_neurons or motor_neurons for mod/mem (gate-sized)
    # connections = min(src_size, 6) by default (sparse wiring).
    # ------------------------------------------------------------------
    "tracts": {

        # ==============================================================
        # Section 5.1 - External → Modules
        # ==============================================================

        # --- Thalamus receives raw sensory and drive modulation ---
        "visn_to_thalamus_data": {
            "src": "visn", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "smel_to_thalamus_data": {
            "src": "smel", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "prox_to_thalamus_data": {
            "src": "prox", "src_size": 20,
            "dst_module": "thalamus", "dst_size": 10,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "sitn_to_thalamus_data": {
            "src": "sitn", "src_size": 9,
            "dst_module": "thalamus", "dst_size": 9,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "loc_to_thalamus_data": {
            "src": "loc", "src_size": 2,
            "dst_module": "thalamus", "dst_size": 2,
            "connections": 2, "signal_type": "data", "enabled": True,
        },
        "stim_to_thalamus_data": {
            "src": "stim", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "detl_to_thalamus_data": {
            "src": "detl", "src_size": 11,
            "dst_module": "thalamus", "dst_size": 11,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        # Drive as direct content (thalamus relays "I need X" alongside sensory data)
        "driv_to_thalamus_data": {
            "src": "driv", "src_size": 20,
            "dst_module": "thalamus", "dst_size": 20,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        # Drive modulates thalamic gain (emotional arousal gates sensory relay)
        "driv_to_thalamus_mod": {
            "src": "driv", "src_size": 20,
            "dst_module": "thalamus", "dst_size": 50,   # gates inter layer
            "connections": 6, "signal_type": "mod", "enabled": True,
        },

        # --- Amygdala receives raw sensory + drive/chemical modulation ---
        "visn_to_amygdala_data": {
            "src": "visn", "src_size": 40,
            "dst_module": "amygdala", "dst_size": 12,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "smel_to_amygdala_data": {
            "src": "smel", "src_size": 40,
            "dst_module": "amygdala", "dst_size": 12,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "driv_to_amygdala_mod": {
            "src": "driv", "src_size": 20,
            "dst_module": "amygdala", "dst_size": 35,   # gates inter layer
            "connections": 6, "signal_type": "mod", "enabled": True,
        },
        "prox_to_amygdala_mod": {
            "src": "prox", "src_size": 20,
            "dst_module": "amygdala", "dst_size": 35,
            "connections": 6, "signal_type": "mod", "enabled": True,
        },
        "sitn_to_amygdala_mod": {
            "src": "sitn", "src_size": 9,
            "dst_module": "amygdala", "dst_size": 35,
            "connections": 6, "signal_type": "mod", "enabled": True,
        },
        "chem_to_amygdala_mod": {
            "src": "chem", "src_size": 16,
            "dst_module": "amygdala", "dst_size": 35,
            "connections": 6, "signal_type": "mod", "enabled": True,
        },

        # --- Hippocampus receives proximity/situation mod + location/stimulus mem ---
        "prox_to_hippocampus_mod": {
            "src": "prox", "src_size": 20,
            "dst_module": "hippocampus", "dst_size": 50,  # gates inter layer
            "connections": 6, "signal_type": "mod", "enabled": True,
        },
        "sitn_to_hippocampus_mod": {
            "src": "sitn", "src_size": 9,
            "dst_module": "hippocampus", "dst_size": 50,
            "connections": 6, "signal_type": "mod", "enabled": True,
        },
        "loc_to_hippocampus_mem": {
            "src": "loc", "src_size": 2,
            "dst_module": "hippocampus", "dst_size": 2,
            "connections": 2, "signal_type": "mem", "enabled": True,
        },
        "stim_to_hippocampus_mem": {
            "src": "stim", "src_size": 40,
            "dst_module": "hippocampus", "dst_size": 16,
            "connections": 6, "signal_type": "mem", "enabled": True,
        },
        "detl_to_hippocampus_mem": {
            "src": "detl", "src_size": 11,
            "dst_module": "hippocampus", "dst_size": 11,
            "connections": 6, "signal_type": "mem", "enabled": True,
        },

        # --- Frontal receives drive data + language inputs + chemical modulation ---
        # Drive as direct content (frontal sees raw "I need X" for attention/decision)
        "driv_to_frontal_data": {
            "src": "driv", "src_size": 20,
            "dst_module": "frontal", "dst_size": 20,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "noun_to_frontal_data": {
            "src": "noun", "src_size": 40,
            "dst_module": "frontal", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "verb_to_frontal_data": {
            "src": "verb", "src_size": 17,
            "dst_module": "frontal", "dst_size": 12,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "chem_to_frontal_mod": {
            "src": "chem", "src_size": 16,
            "dst_module": "frontal", "dst_size": 220,  # gates inter layer
            "connections": 6, "signal_type": "mod", "enabled": True,
        },

        # ==============================================================
        # Section 5.2 - Inter-Module tracts
        # src_size = source module's output_size (motor_neurons)
        # ==============================================================

        # Thalamus → downstream modules (fast sensory relay)
        "thalamus_to_hippocampus_data": {
            "src": "thalamus", "src_size": 40,
            "dst_module": "hippocampus", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "thalamus_to_amygdala_data": {
            "src": "thalamus", "src_size": 40,
            "dst_module": "amygdala", "dst_size": 12,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "thalamus_to_frontal_data": {
            "src": "thalamus", "src_size": 40,
            "dst_module": "frontal", "dst_size": 20,
            "connections": 6, "signal_type": "data", "enabled": True,
        },

        # Bidirectional hippocampus ↔ amygdala
        "hippocampus_to_amygdala_mem": {
            "src": "hippocampus", "src_size": 40,
            "dst_module": "amygdala", "dst_size": 35,   # context gates amygdala inter
            "connections": 6, "signal_type": "mem", "enabled": True,
        },
        "amygdala_to_hippocampus_data": {
            "src": "amygdala", "src_size": 25,
            "dst_module": "hippocampus", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },

        # Feedback to thalamus
        "hippocampus_to_thalamus_mem": {
            "src": "hippocampus", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 50,   # memory re-gates sensory inter
            "connections": 6, "signal_type": "mem", "enabled": True,
        },
        "amygdala_to_thalamus_mod": {
            "src": "amygdala", "src_size": 25,
            "dst_module": "thalamus", "dst_size": 50,   # arousal modulates sensory relay
            "connections": 6, "signal_type": "mod", "enabled": True,
        },

        # Context and emotion → frontal decision
        "hippocampus_to_frontal_data": {
            "src": "hippocampus", "src_size": 40,
            "dst_module": "frontal", "dst_size": 20,
            "connections": 6, "signal_type": "data", "enabled": True,
        },
        "amygdala_to_frontal_data": {
            "src": "amygdala", "src_size": 25,
            "dst_module": "frontal", "dst_size": 16,
            "connections": 6, "signal_type": "data", "enabled": True,
        },

        # ==============================================================
        # Section 5.3 - LTM tract
        # ==============================================================

        "ltm_to_frontal_mem": {
            "src": "ltm", "src_size": 6,
            "dst_module": "frontal", "dst_size": 220,   # recalled memories gate FC inter
            "connections": 6, "signal_type": "mem", "enabled": True,
        },
    },
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_genome_v2(genome: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a v2 genome dict for structural correctness.

    Checks top-level keys, module fields and value ranges, tract fields,
    signal types, and cross-references (dst_module membership, connections
    vs src_size).

    Args:
        genome: The genome dict to validate.

    Returns:
        ``(True, [])`` when valid; ``(False, [error, ...])`` otherwise.
    """
    errors: list[str] = []

    # --- Top-level ---
    for key in ("version", "seed", "scale", "modules", "tracts"):
        if key not in genome:
            errors.append(f"Missing top-level key '{key}'")

    if errors:
        return (False, errors)

    if genome["version"] != 2:
        errors.append(
            f"Expected version=2, got {genome['version']!r}"
        )

    # --- Modules ---
    modules = genome["modules"]
    for name in MODULE_NAMES_V2:
        if name not in modules:
            errors.append(f"Missing module '{name}'")
            continue

        mod = modules[name]
        missing = REQUIRED_MODULE_KEYS_V2 - set(mod.keys())
        if missing:
            errors.append(f"Module '{name}' missing keys: {sorted(missing)}")
            continue

        # Neuron counts: positive ints
        for key in ("sensory_neurons", "inter_neurons",
                     "command_neurons", "motor_neurons", "output_size"):
            val = mod[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Module '{name}'.{key} must be a positive integer, got {val!r}"
                )

        # output_size must match motor_neurons
        if (isinstance(mod.get("output_size"), int)
                and isinstance(mod.get("motor_neurons"), int)
                and mod["output_size"] != mod["motor_neurons"]):
            errors.append(
                f"Module '{name}'.output_size ({mod['output_size']}) must equal "
                f"motor_neurons ({mod['motor_neurons']})"
            )

        # Wiring parameters: positive ints
        for key in ("sensory_fanout", "inter_fanout",
                     "recurrent_command_synapses", "motor_fanin"):
            val = mod[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Module '{name}'.{key} must be a positive integer, got {val!r}"
                )

        # Time bias: categorical
        if mod["time_bias"] not in VALID_TIME_BIASES:
            errors.append(
                f"Module '{name}'.time_bias must be one of "
                f"{sorted(VALID_TIME_BIASES)}, got {mod['time_bias']!r}"
            )

    # --- Tracts ---
    tracts = genome["tracts"]
    default_tract_names = set(DEFAULT_GENOME_V2["tracts"].keys())
    for tract_name in default_tract_names:
        if tract_name not in tracts:
            errors.append(f"Missing tract '{tract_name}'")
            continue

        tract = tracts[tract_name]
        missing = REQUIRED_TRACT_KEYS_V2 - set(tract.keys())
        if missing:
            errors.append(f"Tract '{tract_name}' missing keys: {sorted(missing)}")
            continue

        # src_size and dst_size: positive ints
        for key in ("src_size", "dst_size"):
            val = tract[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Tract '{tract_name}'.{key} must be a positive integer, "
                    f"got {val!r}"
                )

        # connections: positive int, must not exceed src_size
        conn = tract["connections"]
        if not isinstance(conn, int) or conn < 1:
            errors.append(
                f"Tract '{tract_name}'.connections must be a positive integer, "
                f"got {conn!r}"
            )
        elif isinstance(tract["src_size"], int) and conn > tract["src_size"]:
            errors.append(
                f"Tract '{tract_name}'.connections ({conn}) exceeds "
                f"src_size ({tract['src_size']})"
            )

        # signal_type: must be a recognised type
        if tract["signal_type"] not in SIGNAL_TYPES:
            errors.append(
                f"Tract '{tract_name}'.signal_type must be one of "
                f"{sorted(SIGNAL_TYPES)}, got {tract['signal_type']!r}"
            )

        # enabled: bool
        if not isinstance(tract["enabled"], bool):
            errors.append(
                f"Tract '{tract_name}'.enabled must be a bool, "
                f"got {tract['enabled']!r}"
            )

        # dst_module: must be a known module
        if tract["dst_module"] not in MODULE_NAMES_V2:
            errors.append(
                f"Tract '{tract_name}'.dst_module '{tract['dst_module']}' "
                f"is not a known v2 module"
            )

    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------

def mutate_genome_v2(
    genome: dict[str, Any],
    rate: float = 0.1,
    seed: int = 42,
) -> dict[str, Any]:
    """Create a mutated copy of a v2 genome.

    Numeric parameters are perturbed with probability ``rate``:
      - Neuron counts (sensory/inter/command/motor/output_size): gaussian +/-20%.
      - Wiring parameters (fanout/fanin/recurrent): gaussian +/-2.
      - Tract dst_size: gaussian +/-2.
      - Tract connections: gaussian +/-2, clamped to [1, src_size].

    Signal types are never mutated (they encode architectural intent, not
    numeric hyperparameters). Time biases can mutate with probability
    ``rate * 0.2``. Tract ``enabled`` flags toggle with probability 0.02.

    ``output_size`` is always kept in sync with ``motor_neurons`` after mutation.

    Args:
        genome: Source genome dict (not modified).
        rate: Per-parameter mutation probability in [0, 1]. Default 0.1.
        seed: RNG seed for reproducibility. Default 42.

    Returns:
        A new genome dict with mutations applied.
    """
    rng = random.Random(seed)
    mutated = copy.deepcopy(genome)

    # --- Modules ---
    for mod_name, mod in mutated["modules"].items():
        # Neuron counts: +/-20% gaussian
        for key in ("sensory_neurons", "inter_neurons",
                     "command_neurons", "motor_neurons"):
            if rng.random() < rate:
                original = mod[key]
                sigma = max(1, round(original * 0.2))
                delta = round(rng.gauss(0, sigma))
                mod[key] = _clamp(original + delta, 1, 512)

        # Keep output_size synchronised with motor_neurons
        mod["output_size"] = mod["motor_neurons"]

        # Wiring parameters: +/-2 gaussian
        for key in ("sensory_fanout", "inter_fanout",
                     "recurrent_command_synapses", "motor_fanin"):
            if rng.random() < rate:
                original = mod[key]
                delta = round(rng.gauss(0, 2))
                mod[key] = _clamp(original + delta, 1, 64)

        # Time bias: rare categorical mutation
        if rng.random() < rate * 0.2:
            choices = sorted(VALID_TIME_BIASES - {mod["time_bias"]})
            if choices:
                mod["time_bias"] = rng.choice(choices)

    # --- Tracts ---
    for tract_name, tract in mutated["tracts"].items():
        # dst_size: +/-2 gaussian
        if rng.random() < rate:
            original = tract["dst_size"]
            delta = round(rng.gauss(0, 2))
            tract["dst_size"] = _clamp(original + delta, 1, 512)

        # connections: +/-2 gaussian, clamped to src_size
        if rng.random() < rate:
            original = tract["connections"]
            delta = round(rng.gauss(0, 2))
            tract["connections"] = _clamp(
                original + delta, 1, tract["src_size"]
            )

        # enabled: toggle with low probability
        if rng.random() < 0.02:
            tract["enabled"] = not tract["enabled"]

        # signal_type is intentionally NOT mutated

    return mutated


# ---------------------------------------------------------------------------
# Crossover
# ---------------------------------------------------------------------------

def crossover_genomes_v2(
    a: dict[str, Any],
    b: dict[str, Any],
    seed: int = 42,
) -> dict[str, Any]:
    """Create an offspring genome by module-level crossover of two v2 parents.

    For each module, the offspring inherits all parameters from either ``a``
    or ``b`` (chosen with equal probability). For each tract, independently,
    all parameters are inherited from either ``a`` or ``b``. Signal types are
    preserved verbatim from whichever parent donates the tract.

    If a module or tract exists in only one parent, that parent donates it
    unconditionally.

    Args:
        a: First parent genome dict.
        b: Second parent genome dict.
        seed: RNG seed for reproducibility. Default 42.

    Returns:
        A new genome dict representing the offspring.
    """
    rng = random.Random(seed)
    offspring: dict[str, Any] = {
        "version": 2,
        "seed": rng.randint(0, 2 ** 31 - 1),
        "scale": a.get("scale", 0.1),
        "modules": {},
        "tracts": {},
    }

    # --- Crossover modules ---
    all_modules = sorted(
        set(a.get("modules", {}).keys()) | set(b.get("modules", {}).keys())
    )
    for mod_name in all_modules:
        in_a = mod_name in a.get("modules", {})
        in_b = mod_name in b.get("modules", {})
        if in_a and in_b:
            donor = a if rng.random() < 0.5 else b
        elif in_a:
            donor = a
        else:
            donor = b
        offspring["modules"][mod_name] = copy.deepcopy(donor["modules"][mod_name])

    # --- Crossover tracts ---
    all_tracts = sorted(
        set(a.get("tracts", {}).keys()) | set(b.get("tracts", {}).keys())
    )
    for tract_name in all_tracts:
        in_a = tract_name in a.get("tracts", {})
        in_b = tract_name in b.get("tracts", {})
        if in_a and in_b:
            donor = a if rng.random() < 0.5 else b
        elif in_a:
            donor = a
        else:
            donor = b
        offspring["tracts"][tract_name] = copy.deepcopy(donor["tracts"][tract_name])

    return offspring


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def genome_to_json_v2(genome: dict[str, Any], indent: int = 2) -> str:
    """Serialise a v2 genome dict to a JSON string.

    Args:
        genome: The genome dict to serialise.
        indent: JSON indentation level. Defaults to 2.

    Returns:
        A JSON string representation of the genome.
    """
    return json.dumps(genome, indent=indent, sort_keys=False)


def genome_from_json_v2(json_str: str) -> dict[str, Any]:
    """Deserialise a v2 genome dict from a JSON string.

    Args:
        json_str: The JSON string to parse.

    Returns:
        The parsed genome dict.
    """
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# SignalRouter input spec helper
# ---------------------------------------------------------------------------

def get_module_input_specs(
    genome: dict[str, Any],
    module_name: str,
) -> dict[str, dict[str, int]]:
    """Return a typed breakdown of all incoming tracts for a module.

    Groups enabled tracts by signal type so that SignalRouter can build
    the correct concatenation / gating tensors without inspecting the full
    genome.

    Example return value for ``module_name="frontal"``::

        {
            "data": {
                "noun_to_frontal_data": 16,
                "verb_to_frontal_data": 12,
                "thalamus_to_frontal_data": 20,
                "hippocampus_to_frontal_data": 20,
                "amygdala_to_frontal_data": 16,
            },
            "mod": {
                "chem_to_frontal_mod": 220,
            },
            "mem": {
                "ltm_to_frontal_mem": 220,
            },
        }

    Only enabled tracts are included. The returned sizes are ``dst_size``
    values (projection width at the destination), not ``src_size``.

    Args:
        genome: A valid v2 genome dict.
        module_name: Name of the target module. Must be in ``MODULE_NAMES_V2``.

    Returns:
        A dict keyed by signal type ("data", "mod", "mem"), each mapping
        tract name → dst_size for tracts targeting ``module_name``.
    Raises:
        ValueError: If ``module_name`` is not a known v2 module.
    """
    if module_name not in MODULE_NAMES_V2:
        raise ValueError(
            f"Unknown module '{module_name}'. "
            f"Valid modules: {MODULE_NAMES_V2}"
        )

    specs: dict[str, dict[str, int]] = {"data": {}, "mod": {}, "mem": {}}

    for tract_name, tract in genome.get("tracts", {}).items():
        if not tract.get("enabled", False):
            continue
        if tract.get("dst_module") != module_name:
            continue
        signal_type = tract.get("signal_type", "data")
        if signal_type not in specs:
            # Unknown signal type - skip rather than raise; validator catches this.
            continue
        specs[signal_type][tract_name] = tract["dst_size"]

    return specs


# ---------------------------------------------------------------------------
# Convenience: quick self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== NB Brain Architecture v2 Genome self-test ===\n")

    # --- Validate default genome ---
    valid, errors = validate_genome_v2(DEFAULT_GENOME_V2)
    print(f"DEFAULT_GENOME_V2 valid: {valid}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")

    # --- Neuron count summary ---
    total = 0
    for mod_name in MODULE_NAMES_V2:
        mod = DEFAULT_GENOME_V2["modules"][mod_name]
        mod_total = (
            mod["sensory_neurons"] + mod["inter_neurons"]
            + mod["command_neurons"] + mod["motor_neurons"]
        )
        total += mod_total
        print(
            f"  {mod_name:12s}: "
            f"S={mod['sensory_neurons']:3d} I={mod['inter_neurons']:3d} "
            f"C={mod['command_neurons']:3d} M={mod['motor_neurons']:3d} "
            f"= {mod_total:4d}"
        )
    print(f"  {'TOTAL':12s}: {total:4d}")

    # --- Tract count by signal type ---
    counts: dict[str, int] = {"data": 0, "mod": 0, "mem": 0}
    for tract in DEFAULT_GENOME_V2["tracts"].values():
        counts[tract["signal_type"]] = counts.get(tract["signal_type"], 0) + 1
    print(
        f"\nTract counts: "
        f"data={counts['data']}, mod={counts['mod']}, mem={counts['mem']}, "
        f"total={sum(counts.values())}"
    )

    # --- Mutation ---
    mutated = mutate_genome_v2(DEFAULT_GENOME_V2, rate=0.3, seed=123)
    valid_m, errors_m = validate_genome_v2(mutated)
    print(f"\nMutated genome valid: {valid_m}")
    if errors_m:
        for e in errors_m:
            print(f"  ERROR: {e}")

    # --- Crossover ---
    parent_b = mutate_genome_v2(DEFAULT_GENOME_V2, rate=0.5, seed=456)
    child = crossover_genomes_v2(DEFAULT_GENOME_V2, parent_b, seed=789)
    valid_c, errors_c = validate_genome_v2(child)
    print(f"Crossover genome valid: {valid_c}")
    if errors_c:
        for e in errors_c:
            print(f"  ERROR: {e}")

    # --- Serialisation round-trip ---
    json_str = genome_to_json_v2(DEFAULT_GENOME_V2)
    recovered = genome_from_json_v2(json_str)
    valid_r, errors_r = validate_genome_v2(recovered)
    print(f"JSON round-trip valid: {valid_r}")
    if errors_r:
        for e in errors_r:
            print(f"  ERROR: {e}")

    # --- Input spec for each module ---
    print("\nInput specs (enabled tracts by signal type):")
    for mod_name in MODULE_NAMES_V2:
        specs = get_module_input_specs(DEFAULT_GENOME_V2, mod_name)
        data_total = sum(specs["data"].values())
        mod_total = sum(specs["mod"].values())
        mem_total = sum(specs["mem"].values())
        print(
            f"  {mod_name:12s}: "
            f"data={len(specs['data'])} tracts ({data_total}), "
            f"mod={len(specs['mod'])} tracts ({mod_total}), "
            f"mem={len(specs['mem'])} tracts ({mem_total})"
        )

    print("\nSelf-test complete.")
