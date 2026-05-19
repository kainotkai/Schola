# Copyright (c) 2025 Advanced Micro Devices, Inc. All Rights Reserved.

"""Shared pytest fixtures for Ray RLlib + Schola integration tests."""

import os

import pytest
import gymnasium as gym
import ray
from schola.rllib.env import RayEnv, RayVecEnv
from schola.core.protocols.protobuf.grpc_protocol import GrpcProtocol
from schola.core.simulators.unreal.editor_simulator import UnrealEditor


@pytest.fixture(scope="function")
def make_rllib_env(make_env_server):
    """Create a RayEnv for testing (single environment)."""

    def _factory(env_name, **kwargs):
        env_server_port = make_env_server(env_name)
        simulator = UnrealEditor()
        protocol = GrpcProtocol(url="localhost", port=env_server_port)
        return RayEnv(protocol, simulator)

    return _factory


@pytest.fixture(scope="function")
def make_rllib_vec_env(make_vec_env_server):
    """Create a RayVecEnv for testing."""

    def _factory(env_funcs):
        env_server_port = make_vec_env_server(env_funcs)
        simulator = UnrealEditor()
        protocol = GrpcProtocol(url="localhost", port=env_server_port)
        return RayVecEnv(protocol, simulator)

    return _factory


@pytest.fixture(scope="function")
def make_env():
    """Creates an environment factory."""
    envs = []

    def _make(env_name, action_space_seed=None, **kwargs):
        env = gym.make(env_name, disable_env_checker=True, **kwargs)
        if action_space_seed is not None:
            env.action_space.seed(action_space_seed)
        envs.append(env)
        return env

    yield _make

    for env in envs:
        env.close()


@pytest.fixture(scope="function")
def make_pettingzoo_env():
    """Factory function to create PettingZoo environments."""

    def _make(env_name: str):
        # Import PettingZoo environments dynamically
        if env_name == "pistonball_v6":
            from pettingzoo.butterfly import pistonball_v6

            return pistonball_v6.parallel_env()
        elif env_name == "simple_spread_v3":
            # mpe2's SimpleEnv uses pygame.freetype.Font after pygame.init() but does not
            # call pygame.freetype.init(); many Linux/pygame builds then raise:
            # RuntimeError: The FreeType 2 library hasn't been initialized
            import pygame
            import pygame.freetype

            pygame.init()
            pygame.freetype.init()
            from mpe2 import simple_spread_v3

            return simple_spread_v3.parallel_env()
        elif env_name == "pursuit_v4":
            from pettingzoo.sisl import pursuit_v4

            return pursuit_v4.parallel_env()
        else:
            raise ValueError(f"Unknown PettingZoo environment: {env_name}")

    return _make


@pytest.fixture(scope="function")
def make_rllib_pettingzoo_env(make_pettingzoo_env_server, make_pettingzoo_env):
    """Create a RayEnv for testing with PettingZoo (single environment)."""

    def _factory(env_name: str):
        env_server_port = make_pettingzoo_env_server(make_pettingzoo_env(env_name))
        simulator = UnrealEditor()
        protocol = GrpcProtocol(url="localhost", port=env_server_port)
        return RayEnv(protocol, simulator)

    return _factory


@pytest.fixture(scope="function")
def make_rllib_vec_pettingzoo_env(make_vec_pettingzoo_env_server):
    """Create a RayVecEnv for testing with PettingZoo."""

    def _factory(env_funcs):
        env_server_port = make_vec_pettingzoo_env_server(env_funcs)
        simulator = UnrealEditor()
        protocol = GrpcProtocol(url="localhost", port=env_server_port)
        return RayVecEnv(protocol, simulator)

    return _factory


# This will make any test using this fixture be placed in the xdist_group "ray-cluster" so that only one worker can create a ray cluster.
@pytest.fixture(scope="session")
def ray_cluster():
    # Quiets Ray's FutureWarning about overriding CUDA_VISIBLE_DEVICES when no GPUs are used.
    os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")
    context = ray.init(num_cpus=1, include_dashboard=False, local_mode=True)
    yield context
    ray.shutdown()
