# Copyright (c) 2024 Advanced Micro Devices, Inc. All Rights Reserved.

"""
Code in this file is adapted from
https://github.com/ray-project/ray/blob/master/rllib/policy/torch_policy_v2.py

Copyright 2023 Ray Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
# Modifications Copyright (c) 2024-2025 Advanced Micro Devices, Inc. All Rights Reserved.


"""
Utility functions for working with ray and rllib.
"""
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.utils.annotations import override
import torch.nn as nn
from gymnasium.spaces import Box, flatdim, Space
from functools import singledispatch
from ray.rllib.policy import Policy

import torch as th
from ray.rllib.policy.sample_batch import SampleBatch
import os
import numpy as np
from schola.core.utils import ScholaModel
import gymnasium as gym
from ray.rllib.utils.spaces.space_utils import (
    get_dummy_batch_for_space,
)
from ray.rllib.models.modelv2 import restore_original_dimensions


@singledispatch
def export_onnx_from_policy(arg, path: str, policy_name=None):
    raise TypeError(
        f"Cannot export ONNX from Policy/Checkpoint stored as {type(arg)}. Pass a Policy, Dictionary of Policies, or a path to a Policy Checkpoint"
    )


@export_onnx_from_policy.register
def _(arg: Policy, path: str, policy_name=None):
    model_path = path + "/" + policy_name if policy_name else path + "/" + "Policy"
    schola_model = RLLibScholaModel(arg)
    schola_model.save_as_onnx(model_path)


@export_onnx_from_policy.register
def _(arg: dict, path: str, policy_name=None):
    # policy name is ignored, as the dictionary has them already
    for _policy_name, policy in arg.items():
        export_onnx_from_policy(policy, path, _policy_name)


@export_onnx_from_policy.register
def _(arg: str, path: str, policy_name=None):
    policy = Policy.from_checkpoint(arg)
    export_onnx_from_policy(policy, path, policy_name)


class RLLibScholaModel(ScholaModel):

    def __init__(self, policy):
        super().__init__()
        self._policy = policy
        self._model = policy.model.to("cpu")

    def forward(self, *args):
        """
        Forward pass through the model. Removes variance outputs, to make compatible with Unreal.
        """
        seq_len = [1]
        state = args[-1]
        inputs = args[:-1]

        self._policy._get_dummy_batch_from_view_requirements(1)
        self._policy._lazy_tensor_dict(self._policy._dummy_batch)

        dummy_inputs = {
            k: self._policy._dummy_batch[k]
            for k in self._policy._dummy_batch.keys()
            if k != "is_training"
        }

        dummy_inputs["state_in_0"] = state
        dummy_inputs["obs"] = {
            k: v
            for k, v in zip(
                self._policy.observation_space.original_space.spaces.keys(), inputs
            )
        }
        dummy_inputs["obs_flat"] = th.cat(
            [th.flatten(input_tensor, start_dim=1) for input_tensor in inputs], dim=1
        )

        model_out = self._model.forward(dummy_inputs, [state], seq_len)
        # model_out[0] is the logits, model_out[1] is the state
        # check if state is 3D meaning a rnn model, if not, view it as 1x1x1
        # Logits output other miscelanous outputs so we need to mask them out
        return self.make_outputs(model_out[0], model_out[1])

    def make_outputs(self, logits, state):
        if state[0].shape != 3:
            state = [state[0].view(1, 1, -1)]

        outputs = []
        curr_dim = 0
        for space_name, space in self._model.action_space.items():
            space_size = flatdim(space)
            print(curr_dim, curr_dim + space_size)
            # remove the extra dimensions containing variance etc from the outputs
            if isinstance(space, Box):
                outputs.append(logits[:, curr_dim : curr_dim + space_size])
                curr_dim += 2 * space_size
            else:
                outputs.append(logits[:, curr_dim : curr_dim + space_size])
                curr_dim += space_size
        outputs.append(state)
        return tuple(outputs)

    def save_as_onnx(self, export_dir: str, onnx_oppset: int = 17) -> None:
        policy = self._policy
        os.makedirs(export_dir, exist_ok=True)

        enable_rl_module = policy.config.get("enable_rl_module_and_learner", False)
        if enable_rl_module and onnx_oppset:
            raise ValueError("ONNX export not supported for RLModule API.")

        # Replace dummy batch with a batch of size 1 for inference.
        # Disable the preprocessor API to get the unflattened observations in the _dummy_batch
        policy._dummy_batch = policy._get_dummy_batch_from_view_requirements(1)

        # Due to different view requirements for the different columns,
        # columns in the resulting batch may not all have the same batch size.
        policy._lazy_tensor_dict(policy._dummy_batch)

        # Provide dummy state inputs if not an RNN (torch cannot jit with
        # returned empty internal states list).
        if "state_in_0" not in policy._dummy_batch:
            policy._dummy_batch["state_in_0"] = policy._dummy_batch[
                SampleBatch.SEQ_LENS
            ] = np.array([1.0]).reshape(1, 1, -1)

        # only allowed one state for now
        state_in = policy._dummy_batch["state_in_0"].to("cpu")

        input_names = []
        output_names = []
        inputs = []
        for (
            obs_space_name,
            obs_space,
        ) in policy.observation_space.original_space.spaces.items():
            input_names.append(obs_space_name)
            # Just flatten discrete and boolean spaces
            if not isinstance(obs_space, gym.spaces.Box):
                obs_space = gym.spaces.utils.flatten_space()
            inputs.append(th.rand(1, *obs_space.shape))

        for action_space_name, action_space in policy.action_space.items():
            output_names.append(action_space_name)

        inputs.append(state_in)
        input_names.append("state_in")
        output_names.append("state_out")
        # Note that the seq_lens gets dropped from the exported model
        file_name = os.path.join(export_dir, "model.onnx")
        th.onnx.export(
            self,
            tuple(inputs),
            file_name,
            export_params=True,
            opset_version=onnx_oppset,
            do_constant_folding=True,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes={k: {0: "batch_size"} for k in input_names},
        )
