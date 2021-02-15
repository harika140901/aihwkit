# -*- coding: utf-8 -*-

# (C) Copyright 2020, 2021 IBM. All Rights Reserved.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Analog layers."""

from typing import Optional

from torch import Tensor
from torch.nn import Linear

from aihwkit.nn.functions import AnalogFunction
from aihwkit.nn.modules.base import AnalogModuleBase, RPUConfigAlias


class AnalogLinear(Linear, AnalogModuleBase):
    """Linear layer that uses an analog tile.

    Linear layer that uses an analog tile during its forward, backward and
    update passes.

    Note:
        The tensor parameters of this layer (``.weight`` and ``.bias``) are not
        guaranteed to contain the same values as the internal weights and biases
        stored in the analog tile. Please use ``set_weights`` and
        ``get_weights`` when attempting to read or modify the weight/bias. This
        read/write process can simulate the (noisy and inexact) analog writing
        and reading of the resistive elements.

    Args:
        in_features: input vector size (number of columns).
        out_features: output vector size (number of rows).
        rpu_config: resistive processing unit configuration.
        bias: whether to use a bias row on the analog tile or not
        realistic_read_write: whether to enable realistic read/write
           for setting initial weights and read out of weights
        weight_scaling_omega: the weight value where the max
            weight will be scaled to. If zero, no weight scaling will
            be performed
    """
    # pylint: disable=abstract-method

    __constants__ = ['in_features', 'out_features']
    in_features: int
    out_features: int
    realistic_read_write: bool
    weight_scaling_omega: float

    def __init__(
            self,
            in_features: int,
            out_features: int,
            bias: bool = True,
            rpu_config: Optional[RPUConfigAlias] = None,
            realistic_read_write: bool = False,
            weight_scaling_omega: float = 0.0,
    ):
        # Create the tile.
        self.analog_tile = self._setup_tile(in_features,
                                            out_features,
                                            bias,
                                            rpu_config,
                                            realistic_read_write,
                                            weight_scaling_omega)
        # Call super() after tile creation, including ``reset_parameters``.
        super().__init__(in_features, out_features, bias=bias)

        # Setup the Parameter custom attributes needed by the optimizer.
        self.weight.is_weight = True
        if bias:
            self.bias.is_bias = True

    def reset_parameters(self) -> None:
        """Reset the parameters (weight and bias)."""
        super().reset_parameters()
        self.set_weights(self.weight, self.bias)

    def forward(self, x_input: Tensor) -> Tensor:
        """Computes the forward pass."""
        # pylint: disable=arguments-differ
        return AnalogFunction.apply(self.analog_tile, x_input, self.weight, self.bias,
                                    not self.training)

    def extra_repr(self) -> str:

        output = super().extra_repr()
        if self.realistic_read_write:
            output += ', realistic_read_write={}'.format(self.realistic_read_write)
        if self.weight_scaling_omega > 0:
            alpha = self.analog_tile.tile.get_alpha_scale()
            output += ', alpha_scale={:.3f}'.format(alpha)

        return '{}, is_cuda={}'.format(output,
                                       self.analog_tile.is_cuda)
