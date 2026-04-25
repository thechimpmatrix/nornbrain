"""NB (NORNBRAIN) - Liquid Neural Network brain for Creatures 3.

Core package containing CfC infrastructure (signals, tracts, LTM, telemetry)
that survives the v2 → comb-only architectural pivot. The comb-replacement
CfC module itself will be implemented under Phase E.2.

Active modules:
    signal_types  - DataProcessor, ModulationProcessor, MemoryProcessor, SignalRouter
    tract         - TractBundle for sparse NCP projections
    ltm           - Long-term memory (encode, retrieve, consolidate, persist)
    telemetry     - TickRecord dataclass + health signal computations

Archived (legacy v2, see archive/legacy-v2/code/nornbrain/):
    multi_lobe_brain_v2  - 1,100-neuron 4-CfC-module brain (superseded 2026-04-25)
    brain_genome_v2      - 32 typed tracts for the v2 architecture

Archived (legacy v1, see legacy/ subdir if present):
    multi_lobe_brain  - 239-neuron v1 brain
    brain_genome      - v1 tract definitions
    norn_brain        - Original single-module brain
"""
