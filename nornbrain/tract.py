"""
Tract -- Sparse linear projection mirroring C3 brain tract genes.

A tract is a learnable sparse linear projection that transforms one input
source's values for a target CfC module. Tracts replace the dense input
layer of a monolithic CfC with structured, genetically-parameterised
connections.

Each tract mirrors the C3 brain's tract genes: a source lobe connects to a
destination lobe with a specific number of connections per destination neuron.
The connection mask is genetic (fixed per creature, heritable); the weights
are learned through training.

A TractBundle groups multiple tracts feeding into a single CfC module and
concatenates their outputs into a single input tensor.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class Tract(nn.Module):
    """Learnable sparse projection between an input source and a CfC module.

    Parameters
    ----------
    src_size : int
        Dimensionality of the source input.
    dst_size : int
        Dimensionality of the tract output (projection target width).
    n_connections : int
        Number of source neurons each destination neuron connects to.
        Clamped to src_size if larger.
    seed : int
        RNG seed for generating the sparse connection mask. This is the
        genetic parameter -- same seed produces the same wiring, making
        the mask heritable and reproducible across runs.
    """

    def __init__(self, src_size: int, dst_size: int,
                 n_connections: int, seed: int = 42):
        super().__init__()
        self.src_size = src_size
        self.dst_size = dst_size
        self.n_connections = min(n_connections, src_size)

        # Learnable weight matrix
        self.weight = nn.Parameter(torch.zeros(dst_size, src_size))
        nn.init.xavier_uniform_(self.weight)

        # Genetic connection mask (not learned -- fixed per creature)
        rng = np.random.RandomState(seed)
        mask = np.zeros((dst_size, src_size), dtype=np.float32)
        for dst in range(dst_size):
            src_indices = rng.choice(src_size,
                                     size=self.n_connections,
                                     replace=False)
            mask[dst, src_indices] = 1.0
        self.register_buffer('mask', torch.from_numpy(mask))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Project input through masked weights.

        Parameters
        ----------
        x : torch.Tensor
            Input tensor of shape ``(..., src_size)``.

        Returns
        -------
        torch.Tensor
            Projected tensor of shape ``(..., dst_size)``.
        """
        return F.linear(x, self.weight * self.mask)

    @property
    def active_connections(self) -> int:
        """Number of non-zero entries in the connection mask."""
        return int(self.mask.sum().item())

    def extra_repr(self) -> str:
        return (f"src_size={self.src_size}, dst_size={self.dst_size}, "
                f"connections={self.n_connections}, "
                f"active={self.active_connections}/{self.dst_size * self.src_size}")


class TractBundle(nn.Module):
    """Collection of tracts feeding into a single CfC module.

    Groups multiple named tracts and concatenates their outputs into a
    single input tensor for the target module. Disabled tracts are excluded
    from the output.

    Parameters
    ----------
    tract_specs : list[dict]
        List of tract specification dicts, each containing:
            - ``name`` (str): Tract identifier (e.g. ``"tract_visn_thal"``).
            - ``src_size`` (int): Source dimensionality.
            - ``dst_size`` (int): Projection output dimensionality.
            - ``connections`` (int): Connections per destination neuron.
            - ``seed`` (int): Genetic RNG seed.
            - ``enabled`` (bool): Whether this tract is active.
    """

    def __init__(self, tract_specs: list[dict]):
        super().__init__()
        self._spec_order: list[str] = []
        self._enabled: dict[str, bool] = {}
        self.tracts = nn.ModuleDict()

        for spec in tract_specs:
            name: str = spec["name"]
            enabled: bool = spec.get("enabled", True)
            self._spec_order.append(name)
            self._enabled[name] = enabled

            if enabled:
                self.tracts[name] = Tract(
                    src_size=spec["src_size"],
                    dst_size=spec["dst_size"],
                    n_connections=spec["connections"],
                    seed=spec["seed"],
                )

    @property
    def output_size(self) -> int:
        """Total output dimensionality (sum of enabled tract dst_sizes)."""
        return sum(t.dst_size for t in self.tracts.values())

    @property
    def total_active_connections(self) -> int:
        """Total active connections across all enabled tracts."""
        return sum(t.active_connections for t in self.tracts.values())

    def forward(self, inputs: dict[str, torch.Tensor]) -> torch.Tensor:
        """Project inputs through all enabled tracts and concatenate.

        Parameters
        ----------
        inputs : dict[str, torch.Tensor]
            Mapping from source name to input tensor. Keys should match
            the tract names registered in the bundle. Tracts whose names
            are not present in ``inputs`` are skipped (they must be
            disabled, or an error is raised).

        Returns
        -------
        torch.Tensor
            Concatenated tract outputs of shape ``(..., output_size)``.

        Raises
        ------
        KeyError
            If an enabled tract's name is not found in ``inputs``.
        """
        outputs: list[torch.Tensor] = []
        for name in self._spec_order:
            if not self._enabled[name]:
                continue
            if name not in inputs:
                raise KeyError(
                    f"TractBundle: enabled tract '{name}' not found in inputs. "
                    f"Available keys: {list(inputs.keys())}"
                )
            outputs.append(self.tracts[name](inputs[name]))

        return torch.cat(outputs, dim=-1)

    def extra_repr(self) -> str:
        enabled = sum(1 for v in self._enabled.values() if v)
        total = len(self._enabled)
        return (f"tracts={enabled}/{total} enabled, "
                f"output_size={self.output_size}, "
                f"active_connections={self.total_active_connections}")
