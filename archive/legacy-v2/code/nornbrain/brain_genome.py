"""Genome configuration system for the NORNBRAIN multi-lobe CfC brain.

Defines the default genome, validation, mutation, and crossover functions
for the genetically-parameterised multi-module brain architecture.

Each genome dict fully specifies the brain architecture: module neuron counts,
NCP wiring parameters, and inter-module tract projections. Two creatures with
different genomes will have different brain architectures.

See Phase 4A spec Section 11 for the full genome specification.
"""

import copy
import json
import math
import random
from typing import Any

# ---------------------------------------------------------------------------
# Chemical index constants
# ---------------------------------------------------------------------------

AMYGDALA_CHEM_INDICES: list[int] = [
    204,  # reward
    205,  # punishment
    117,  # adrenaline
    161,  # fear (drive chemical)
    160,  # anger (drive chemical)
    148,  # pain (drive chemical)
    149,  # hunger_protein (drive chemical)
    150,  # hunger_carb (drive chemical)
    151,  # hunger_fat (drive chemical)
    156,  # loneliness (drive chemical)
    159,  # boredom (drive chemical)
    162,  # sex_drive (drive chemical)
    163,  # comfort (drive chemical)
    128,  # stress
    127,  # injury
    125,  # life
]

# Same 16 chemicals used for the PFC chemical tract
PFC_CHEM_INDICES: list[int] = AMYGDALA_CHEM_INDICES

# ---------------------------------------------------------------------------
# Valid values for categorical parameters
# ---------------------------------------------------------------------------

VALID_TIME_BIASES: set[str] = {"fast", "mixed", "slow", "moderate"}

REQUIRED_MODULE_KEYS: set[str] = {
    "inter_neurons",
    "command_neurons",
    "motor_neurons",
    "sensory_fanout",
    "inter_fanout",
    "recurrent_command_synapses",
    "motor_fanin",
    "time_bias",
}

REQUIRED_TRACT_KEYS: set[str] = {
    "src",
    "src_size",
    "dst_module",
    "dst_size",
    "connections",
    "enabled",
}

# ---------------------------------------------------------------------------
# Module names (canonical ordering)
# ---------------------------------------------------------------------------

MODULE_NAMES: list[str] = ["thalamus", "amygdala", "hippocampus", "prefrontal"]

# ---------------------------------------------------------------------------
# Default genome
# ---------------------------------------------------------------------------

DEFAULT_GENOME: dict[str, Any] = {
    "version": 1,
    "seed": 42,

    # Module specifications
    "modules": {
        "thalamus": {
            "inter_neurons": 20,
            "command_neurons": 10,
            "motor_neurons": 40,
            "sensory_fanout": 8,
            "inter_fanout": 6,
            "recurrent_command_synapses": 10,
            "motor_fanin": 6,
            "time_bias": "fast",
        },
        "amygdala": {
            "inter_neurons": 24,
            "command_neurons": 12,
            "motor_neurons": 16,
            "sensory_fanout": 8,
            "inter_fanout": 6,
            "recurrent_command_synapses": 12,
            "motor_fanin": 6,
            "time_bias": "mixed",
        },
        "hippocampus": {
            "inter_neurons": 24,
            "command_neurons": 12,
            "motor_neurons": 16,
            "sensory_fanout": 6,
            "inter_fanout": 6,
            "recurrent_command_synapses": 16,
            "motor_fanin": 6,
            "time_bias": "slow",
        },
        "prefrontal": {
            "inter_neurons": 32,
            "command_neurons": 16,
            "motor_neurons": 17,
            "sensory_fanout": 12,
            "inter_fanout": 8,
            "recurrent_command_synapses": 16,
            "motor_fanin": 8,
            "time_bias": "moderate",
        },
    },

    # Tract specifications
    "tracts": {
        "tract_visn_thal": {
            "src": "visn", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 10,
            "connections": 8, "enabled": True,
        },
        "tract_smel_thal": {
            "src": "smel", "src_size": 40,
            "dst_module": "thalamus", "dst_size": 10,
            "connections": 8, "enabled": True,
        },
        "tract_driv_thal": {
            "src": "driv", "src_size": 20,
            "dst_module": "thalamus", "dst_size": 10,
            "connections": 6, "enabled": True,
        },
        "tract_prox_thal": {
            "src": "prox", "src_size": 20,
            "dst_module": "thalamus", "dst_size": 10,
            "connections": 6, "enabled": True,
        },
        "tract_driv_amyg": {
            "src": "driv", "src_size": 20,
            "dst_module": "amygdala", "dst_size": 8,
            "connections": 6, "enabled": True,
        },
        "tract_stim_amyg": {
            "src": "stim", "src_size": 40,
            "dst_module": "amygdala", "dst_size": 8,
            "connections": 8, "enabled": True,
        },
        "tract_chem_amyg": {
            "src": "chemicals", "src_size": 16,
            "dst_module": "amygdala", "dst_size": 8,
            "connections": 6, "enabled": True,
        },
        "tract_sitn_hipp": {
            "src": "sitn", "src_size": 9,
            "dst_module": "hippocampus", "dst_size": 4,
            "connections": 4, "enabled": True,
        },
        "tract_detl_hipp": {
            "src": "detl", "src_size": 11,
            "dst_module": "hippocampus", "dst_size": 4,
            "connections": 4, "enabled": True,
        },
        "tract_noun_hipp": {
            "src": "noun", "src_size": 40,
            "dst_module": "hippocampus", "dst_size": 4,
            "connections": 8, "enabled": True,
        },
        "tract_verb_hipp": {
            "src": "verb", "src_size": 17,
            "dst_module": "hippocampus", "dst_size": 4,
            "connections": 6, "enabled": True,
        },
        "tract_loc_hipp": {
            "src": "location", "src_size": 2,
            "dst_module": "hippocampus", "dst_size": 4,
            "connections": 2, "enabled": True,
        },
        "tract_thal_pfc": {
            "src": "thalamus_out", "src_size": 40,
            "dst_module": "prefrontal", "dst_size": 10,
            "connections": 10, "enabled": True,
        },
        "tract_amyg_pfc": {
            "src": "amygdala_out", "src_size": 16,
            "dst_module": "prefrontal", "dst_size": 8,
            "connections": 8, "enabled": True,
        },
        "tract_hipp_pfc": {
            "src": "hippocampus_out", "src_size": 16,
            "dst_module": "prefrontal", "dst_size": 6,
            "connections": 6, "enabled": True,
        },
        "tract_driv_pfc": {
            "src": "driv", "src_size": 20,
            "dst_module": "prefrontal", "dst_size": 8,
            "connections": 6, "enabled": True,
        },
        "tract_verb_pfc": {
            "src": "verb", "src_size": 17,
            "dst_module": "prefrontal", "dst_size": 4,
            "connections": 6, "enabled": True,
        },
        "tract_noun_pfc": {
            "src": "noun", "src_size": 40,
            "dst_module": "prefrontal", "dst_size": 4,
            "connections": 8, "enabled": True,
        },
        "tract_resp_pfc": {
            "src": "resp", "src_size": 20,
            "dst_module": "prefrontal", "dst_size": 4,
            "connections": 6, "enabled": True,
        },
        "tract_stim_pfc": {
            "src": "stim", "src_size": 40,
            "dst_module": "prefrontal", "dst_size": 4,
            "connections": 8, "enabled": True,
        },
        "tract_chem_pfc": {
            "src": "chemicals", "src_size": 16,
            "dst_module": "prefrontal", "dst_size": 6,
            "connections": 6, "enabled": True,
        },
        "tract_ltm_pfc": {
            "src": "ltm", "src_size": 6,
            "dst_module": "prefrontal", "dst_size": 6,
            "connections": 6, "enabled": True,
        },
    },
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_genome(genome: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a genome dict for structural correctness.

    Checks that all required module and tract keys exist, neuron counts are
    positive integers, tract dimensions and connection counts are valid, and
    categorical parameters have legal values.

    Args:
        genome: The genome dict to validate.

    Returns:
        A tuple of (is_valid, error_messages). Returns (True, []) when valid,
        or (False, [list of error strings]) when invalid.
    """
    errors: list[str] = []

    # Top-level keys
    if "version" not in genome:
        errors.append("Missing top-level key 'version'")
    if "seed" not in genome:
        errors.append("Missing top-level key 'seed'")

    # --- Modules ---
    if "modules" not in genome:
        errors.append("Missing top-level key 'modules'")
        return (False, errors)

    modules = genome["modules"]
    for name in MODULE_NAMES:
        if name not in modules:
            errors.append(f"Missing module '{name}'")
            continue

        mod = modules[name]
        missing = REQUIRED_MODULE_KEYS - set(mod.keys())
        if missing:
            errors.append(f"Module '{name}' missing keys: {sorted(missing)}")
            continue

        # Neuron counts must be positive integers
        for key in ("inter_neurons", "command_neurons", "motor_neurons"):
            val = mod[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Module '{name}'.{key} must be a positive integer, got {val!r}"
                )

        # Fanout/fanin/recurrent must be positive integers
        for key in ("sensory_fanout", "inter_fanout",
                     "recurrent_command_synapses", "motor_fanin"):
            val = mod[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Module '{name}'.{key} must be a positive integer, got {val!r}"
                )

        # Time bias must be a valid string
        if mod["time_bias"] not in VALID_TIME_BIASES:
            errors.append(
                f"Module '{name}'.time_bias must be one of {sorted(VALID_TIME_BIASES)}, "
                f"got {mod['time_bias']!r}"
            )

    # --- Tracts ---
    if "tracts" not in genome:
        errors.append("Missing top-level key 'tracts'")
        return (len(errors) == 0, errors)

    tracts = genome["tracts"]
    default_tract_names = set(DEFAULT_GENOME["tracts"].keys())
    for tract_name in default_tract_names:
        if tract_name not in tracts:
            errors.append(f"Missing tract '{tract_name}'")
            continue

        tract = tracts[tract_name]
        missing = REQUIRED_TRACT_KEYS - set(tract.keys())
        if missing:
            errors.append(f"Tract '{tract_name}' missing keys: {sorted(missing)}")
            continue

        # src_size and dst_size must be positive integers
        for key in ("src_size", "dst_size"):
            val = tract[key]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"Tract '{tract_name}'.{key} must be a positive integer, got {val!r}"
                )

        # connections must be a positive integer
        conn = tract["connections"]
        if not isinstance(conn, int) or conn < 1:
            errors.append(
                f"Tract '{tract_name}'.connections must be a positive integer, "
                f"got {conn!r}"
            )

        # connections should not exceed src_size (cannot wire more than exist)
        if (isinstance(conn, int) and conn >= 1
                and isinstance(tract["src_size"], int) and tract["src_size"] >= 1):
            if conn > tract["src_size"]:
                errors.append(
                    f"Tract '{tract_name}'.connections ({conn}) exceeds "
                    f"src_size ({tract['src_size']})"
                )

        # enabled must be a bool
        if not isinstance(tract["enabled"], bool):
            errors.append(
                f"Tract '{tract_name}'.enabled must be a bool, "
                f"got {tract['enabled']!r}"
            )

        # dst_module must name a known module
        if tract["dst_module"] not in MODULE_NAMES:
            errors.append(
                f"Tract '{tract_name}'.dst_module '{tract['dst_module']}' "
                f"is not a known module"
            )

    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------

def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer value to [lo, hi]."""
    return max(lo, min(hi, value))


def mutate_genome(
    genome: dict[str, Any],
    mutation_rate: float = 0.1,
    seed: int | None = None,
) -> dict[str, Any]:
    """Create a mutated copy of a genome.

    For each numeric parameter, with probability ``mutation_rate``, applies a
    gaussian perturbation: +/-20% for neuron counts, +/-2 for connection and
    fanout parameters. Tract ``enabled`` flags can toggle with low probability
    (0.02). All values are clamped to valid ranges.

    Args:
        genome: The source genome dict (not modified).
        mutation_rate: Probability [0, 1] that each numeric parameter is
            perturbed. Defaults to 0.1.
        seed: Optional RNG seed for reproducibility.

    Returns:
        A new genome dict with mutations applied.
    """
    rng = random.Random(seed)
    mutated = copy.deepcopy(genome)

    # --- Mutate modules ---
    for mod_name, mod in mutated["modules"].items():
        # Neuron counts: +/-20% gaussian perturbation
        for key in ("inter_neurons", "command_neurons", "motor_neurons"):
            if rng.random() < mutation_rate:
                original = mod[key]
                sigma = max(1, round(original * 0.2))
                delta = round(rng.gauss(0, sigma))
                mod[key] = _clamp(original + delta, 1, 256)

        # Fanout / fanin / recurrent: +/-2 perturbation
        for key in ("sensory_fanout", "inter_fanout",
                     "recurrent_command_synapses", "motor_fanin"):
            if rng.random() < mutation_rate:
                original = mod[key]
                delta = round(rng.gauss(0, 2))
                mod[key] = _clamp(original + delta, 1, 64)

        # Time bias: rare categorical mutation
        if rng.random() < mutation_rate * 0.2:
            choices = sorted(VALID_TIME_BIASES - {mod["time_bias"]})
            if choices:
                mod["time_bias"] = rng.choice(choices)

    # --- Mutate tracts ---
    for tract_name, tract in mutated["tracts"].items():
        # dst_size: +/-2 perturbation
        if rng.random() < mutation_rate:
            original = tract["dst_size"]
            delta = round(rng.gauss(0, 2))
            tract["dst_size"] = _clamp(original + delta, 1, 64)

        # connections: +/-2 perturbation, clamped to [1, src_size]
        if rng.random() < mutation_rate:
            original = tract["connections"]
            delta = round(rng.gauss(0, 2))
            tract["connections"] = _clamp(
                original + delta, 1, tract["src_size"]
            )

        # enabled: toggle with low probability
        if rng.random() < 0.02:
            tract["enabled"] = not tract["enabled"]

    return mutated


# ---------------------------------------------------------------------------
# Crossover
# ---------------------------------------------------------------------------

def crossover_genomes(
    parent_a: dict[str, Any],
    parent_b: dict[str, Any],
    seed: int | None = None,
) -> dict[str, Any]:
    """Create an offspring genome by crossing two parent genomes.

    For each module, the offspring randomly inherits all parameters from
    either parent_a or parent_b. For each tract, independently, the offspring
    randomly inherits all parameters from either parent_a or parent_b.

    Args:
        parent_a: First parent genome dict.
        parent_b: Second parent genome dict.
        seed: Optional RNG seed for reproducibility.

    Returns:
        A new genome dict representing the offspring.
    """
    rng = random.Random(seed)
    offspring: dict[str, Any] = {
        "version": parent_a.get("version", 1),
        "seed": rng.randint(0, 2**31 - 1),
        "modules": {},
        "tracts": {},
    }

    # --- Crossover modules ---
    all_modules = set(parent_a.get("modules", {}).keys()) | set(
        parent_b.get("modules", {}).keys()
    )
    for mod_name in sorted(all_modules):
        donor = parent_a if rng.random() < 0.5 else parent_b
        if mod_name in donor.get("modules", {}):
            offspring["modules"][mod_name] = copy.deepcopy(
                donor["modules"][mod_name]
            )
        else:
            # Fallback: use whichever parent has this module
            fallback = (
                parent_a if mod_name in parent_a.get("modules", {})
                else parent_b
            )
            offspring["modules"][mod_name] = copy.deepcopy(
                fallback["modules"][mod_name]
            )

    # --- Crossover tracts ---
    all_tracts = set(parent_a.get("tracts", {}).keys()) | set(
        parent_b.get("tracts", {}).keys()
    )
    for tract_name in sorted(all_tracts):
        donor = parent_a if rng.random() < 0.5 else parent_b
        if tract_name in donor.get("tracts", {}):
            offspring["tracts"][tract_name] = copy.deepcopy(
                donor["tracts"][tract_name]
            )
        else:
            fallback = (
                parent_a if tract_name in parent_a.get("tracts", {})
                else parent_b
            )
            offspring["tracts"][tract_name] = copy.deepcopy(
                fallback["tracts"][tract_name]
            )

    return offspring


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def genome_to_json(genome: dict[str, Any], indent: int = 2) -> str:
    """Serialise a genome dict to a JSON string.

    Args:
        genome: The genome dict to serialise.
        indent: JSON indentation level. Defaults to 2.

    Returns:
        A JSON string representation of the genome.
    """
    return json.dumps(genome, indent=indent, sort_keys=False)


def genome_from_json(json_str: str) -> dict[str, Any]:
    """Deserialise a genome dict from a JSON string.

    Args:
        json_str: The JSON string to parse.

    Returns:
        The parsed genome dict.
    """
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# Convenience: quick self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Validate the default genome
    valid, errors = validate_genome(DEFAULT_GENOME)
    print(f"DEFAULT_GENOME valid: {valid}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")

    # Test mutation
    mutated = mutate_genome(DEFAULT_GENOME, mutation_rate=0.3, seed=123)
    valid_m, errors_m = validate_genome(mutated)
    print(f"Mutated genome valid: {valid_m}")
    if errors_m:
        for e in errors_m:
            print(f"  ERROR: {e}")

    # Test crossover
    parent_b = mutate_genome(DEFAULT_GENOME, mutation_rate=0.5, seed=456)
    child = crossover_genomes(DEFAULT_GENOME, parent_b, seed=789)
    valid_c, errors_c = validate_genome(child)
    print(f"Crossover genome valid: {valid_c}")
    if errors_c:
        for e in errors_c:
            print(f"  ERROR: {e}")

    # Show tract count
    print(f"Tract count: {len(DEFAULT_GENOME['tracts'])}")
    print(f"Module count: {len(DEFAULT_GENOME['modules'])}")
    print(f"Chemical indices: {len(AMYGDALA_CHEM_INDICES)}")
