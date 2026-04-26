"""
NB Brain - Signal Type Processing Module
========================================

Three architecturally-distinct signal pathways govern how inputs are integrated
into a CfC module. These pathways are enforced structurally, not learned:

DATA (content pathway)
    Raw sensory or state information concatenated and fed directly into the CfC
    sensory layer. The CfC network learns what to do with it. Examples: vision
    attention outputs, smell CA values, lobe outputs from upstream modules.

MODULATION (gain control pathway)
    Sigmoid-gated scaling of the hidden state. Modulation inputs do not carry
    content - they amplify or dampen existing processing. This mirrors how
    neuromodulators (dopamine, serotonin) work in biological brains: they tune
    the sensitivity of neural populations without injecting new information.
    Biochemical drive chemicals are routed here.

MEMORY (context injection pathway)
    Gated additive injection of memory or context into the hidden state. A
    learned gate determines how much the module should trust its stored memory
    versus its current sensory input. This allows long-term context (memory
    or instinct signals) to influence processing without overriding it.

Processing order within SignalRouter:
    1. Modulation applied first - rescales the hidden state
    2. Memory injected second - adds context on top of the rescaled state
    3. Data tensor returned separately - consumed by the CfC forward pass

SignalRouter pre-processes inputs before the CfC tick, so modulation here
acts on the *previous* hidden state (h_{t-1}) before the CfC sees new data.
"""

import torch
import torch.nn as nn
from torch import Tensor


class DataProcessor(nn.Module):
    """
    Concatenates named data inputs into a single tensor for the CfC sensory layer.

    Inputs are concatenated in sorted key order to ensure deterministic behaviour
    regardless of dict insertion order. Missing keys are filled with zeros of the
    correct size. Extra keys not listed in input_specs are silently ignored.
    """

    def __init__(self, input_specs: dict[str, int]) -> None:
        """
        Args:
            input_specs: Mapping of input name → feature size.
                         E.g. {"visn": 40, "smel": 40, "driv": 20}
        """
        super().__init__()
        # Sorted for determinism across Python versions and dict orderings
        self._keys: list[str] = sorted(input_specs.keys())
        self._sizes: dict[str, int] = dict(input_specs)
        self._total: int = sum(input_specs[k] for k in self._keys)

    def forward(self, inputs: dict[str, Tensor]) -> Tensor:
        """
        Concatenate inputs in sorted-key order.

        Args:
            inputs: Dict mapping input names to tensors of shape (batch, size).

        Returns:
            Tensor of shape (batch, sum_of_sizes). Missing keys are zeros.
        """
        parts: list[Tensor] = []
        for key in self._keys:
            size = self._sizes[key]
            if key in inputs:
                parts.append(inputs[key])
            else:
                # Infer batch size from any present tensor, else default to 1
                batch = next(
                    (t.shape[0] for t in inputs.values() if isinstance(t, Tensor)),
                    1,
                )
                device = next(
                    (t.device for t in inputs.values() if isinstance(t, Tensor)),
                    torch.device("cpu"),
                )
                dtype = next(
                    (t.dtype for t in inputs.values() if isinstance(t, Tensor)),
                    torch.float32,
                )
                parts.append(torch.zeros(batch, size, device=device, dtype=dtype))

        return torch.cat(parts, dim=-1)

    @property
    def output_size(self) -> int:
        """Total size of the concatenated output tensor."""
        return self._total


class ModulationProcessor(nn.Module):
    """
    Sigmoid-gated gain control over the CfC hidden state.

    A linear projection maps modulation inputs to per-neuron gate values in
    [0, 1]. These gates multiplicatively scale the hidden state, allowing
    biochemical signals (drives, chemicals) to amplify or suppress processing
    without injecting spurious content.

    Biological analogue: neuromodulatory systems (dopamine, serotonin, etc.)
    that tune neural gain without encoding specific information.
    """

    def __init__(self, mod_input_size: int, hidden_size: int) -> None:
        """
        Args:
            mod_input_size: Feature size of the concatenated modulation input.
            hidden_size:    Size of the CfC hidden state being gated.
        """
        super().__init__()
        self.W_mod = nn.Linear(mod_input_size, hidden_size)

    def forward(self, mod_inputs: Tensor, hidden_state: Tensor) -> Tensor:
        """
        Apply gain-control scaling to the hidden state.

        Gate is centred at 1.0 (no effect at neutral), range [0.5, 1.5].
        Drives amplify relevant channels (gate > 1.0) or dampen irrelevant
        ones (gate < 1.0) without ever fully suppressing signal.

        Args:
            mod_inputs:   (batch, mod_input_size)
            hidden_state: (batch, hidden_size)

        Returns:
            Gated hidden state: hidden_state * (1.0 + 0.5 * tanh(W_mod(mod_inputs)))
            Shape: (batch, hidden_size)
        """
        gate = 1.0 + 0.5 * torch.tanh(self.W_mod(mod_inputs))
        return hidden_state * gate


class MemoryProcessor(nn.Module):
    """
    Learned gating for memory and context injection into the hidden state.

    Two learned projections control the injection:
      - W_gate: decides *how much* of the memory to use, conditioned on both
                the current hidden state and the memory content.
      - W_val:  projects memory into hidden-state space.

    The result is an additive update: hidden + gate * value. This preserves
    the current hidden state by default and lets the gate learn to blend in
    memory when it is contextually relevant.

    Biological analogue: hippocampal-cortical gating - the cortex decides when
    to retrieve and apply stored episodic context.
    """

    def __init__(self, mem_input_size: int, hidden_size: int) -> None:
        """
        Args:
            mem_input_size: Feature size of the concatenated memory input.
            hidden_size:    Size of the CfC hidden state being updated.
        """
        super().__init__()
        # Gate input is the concatenation of hidden state and memory
        self.W_gate = nn.Linear(hidden_size + mem_input_size, hidden_size)
        # Memory projected into hidden-state space
        self.W_val = nn.Linear(mem_input_size, hidden_size)

    def forward(self, mem_inputs: Tensor, hidden_state: Tensor) -> Tensor:
        """
        Inject memory into the hidden state via learned gating.

        Args:
            mem_inputs:   (batch, mem_input_size)
            hidden_state: (batch, hidden_size)

        Returns:
            Updated hidden state: hidden + gate * tanh(W_val(mem))
            Shape: (batch, hidden_size)
        """
        combined = torch.cat([hidden_state, mem_inputs], dim=-1)
        gate = torch.sigmoid(self.W_gate(combined))
        val = torch.tanh(self.W_val(mem_inputs))
        return hidden_state + gate * val


class SignalRouter(nn.Module):
    """
    Combines all three signal processors for a single CfC module.

    Routes named inputs to DataProcessor, ModulationProcessor, and
    MemoryProcessor based on configuration. Not all modules receive all
    signal types - mod_specs and mem_specs may be empty.

    Processing order:
        1. Modulation scales the incoming hidden state (gain control)
        2. Memory injects context into the modulated hidden state
        3. Data tensor is returned for the CfC sensory layer

    This matches the v2 spec ordering: modulation before memory, both applied
    to h_{t-1} before the CfC update sees new sensory data.
    """

    def __init__(
        self,
        data_specs: dict[str, int],
        mod_specs: dict[str, int],
        mem_specs: dict[str, int],
        hidden_size: int,
    ) -> None:
        """
        Args:
            data_specs:  Input names → sizes for the DataProcessor.
            mod_specs:   Input names → sizes for the ModulationProcessor.
                         Pass {} if this module receives no modulation inputs.
            mem_specs:   Input names → sizes for the MemoryProcessor.
                         Pass {} if this module receives no memory inputs.
            hidden_size: Size of the CfC module's hidden state.
        """
        super().__init__()

        self.data_processor = DataProcessor(data_specs)

        # Modulation pathway (optional)
        self._has_mod = bool(mod_specs)
        if self._has_mod:
            mod_total = sum(mod_specs.values())
            self.mod_processor = ModulationProcessor(mod_total, hidden_size)
            self._mod_data = DataProcessor(mod_specs)
        else:
            self.mod_processor = None  # type: ignore[assignment]
            self._mod_data = None  # type: ignore[assignment]

        # Memory pathway (optional)
        self._has_mem = bool(mem_specs)
        if self._has_mem:
            mem_total = sum(mem_specs.values())
            self.mem_processor = MemoryProcessor(mem_total, hidden_size)
            self._mem_data = DataProcessor(mem_specs)
        else:
            self.mem_processor = None  # type: ignore[assignment]
            self._mem_data = None  # type: ignore[assignment]

    def forward(
        self, inputs: dict[str, Tensor], hidden_state: Tensor
    ) -> tuple[Tensor, Tensor]:
        """
        Route inputs to the appropriate processors and return the processed signals.

        Args:
            inputs:       Dict of all named input tensors for this module.
            hidden_state: Previous CfC hidden state, shape (batch, hidden_size).

        Returns:
            (data_tensor, processed_hidden)
            - data_tensor:       (batch, data_size) - ready to feed into CfC sensory layer
            - processed_hidden:  (batch, hidden_size) - hidden state after modulation + memory
        """
        processed_hidden = hidden_state

        # Step 1: Modulation - rescales hidden state via sigmoid gates
        if self._has_mod:
            mod_tensor = self._mod_data(inputs)
            processed_hidden = self.mod_processor(mod_tensor, processed_hidden)

        # Step 2: Memory - adds context via learned gating
        if self._has_mem:
            mem_tensor = self._mem_data(inputs)
            processed_hidden = self.mem_processor(mem_tensor, processed_hidden)

        # Step 3: Data - concatenated content tensor for CfC sensory input
        data_tensor = self.data_processor(inputs)

        return data_tensor, processed_hidden

    @property
    def data_size(self) -> int:
        """Size of the data tensor produced by the DataProcessor."""
        return self.data_processor.output_size
