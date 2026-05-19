# Copyright (c) 2026 Advanced Micro Devices, Inc. All Rights Reserved.
"""Tests for the SB3 eval CLI."""

import logging
import math
from pathlib import Path

import pytest
from cyclopts import App

from schola.scripts.common.settings import EnvironmentSettings, GrpcProtocolConfig
from schola.scripts.sb3.eval.eval import MetaEvalSB3Command, main as eval_main
from schola.scripts.sb3.eval.settings import Sb3EvalScriptSettings


@pytest.fixture
def dummy_sb3_policy_zip(tmp_path: Path) -> Path:
    """
    Train a tiny PPO on ``CartPole-v1`` (in-process ``DummyVecEnv``) and save ``.zip``.

    Observation and action spaces match the gRPC CartPole vec server used in tests.
    """
    pytest.importorskip("stable_baselines3")
    import gymnasium as gym
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    save_stem = tmp_path / "dummy_cartpole_policy"
    venv = DummyVecEnv([lambda: gym.make("CartPole-v1")])
    try:
        model = PPO(
            "MlpPolicy",
            venv,
            n_steps=64,
            batch_size=64,
            ent_coef=0.0,
            verbose=0,
        )
        model.learn(total_timesteps=512, progress_bar=False)
        model.save(str(save_stem))
    finally:
        venv.close()
    out = save_stem.with_suffix(".zip")
    assert out.is_file()
    return out


@pytest.fixture
def mock_main(mocker):
    return mocker.patch("schola.scripts.sb3.eval.eval.main")


@pytest.fixture
def mock_eval_app(mock_main):
    base = App(name="eval", help="Evaluate a trained Stable-Baselines3 policy")
    logger = logging.getLogger(__name__)
    return MetaEvalSB3Command(base, Sb3EvalScriptSettings, mock_main, logger).make()


@pytest.fixture
def sb3_eval_meta_app():
    """Real ``schola sb3 eval`` Cyclopts meta-app (invokes ``eval_main``)."""
    base = App(name="eval", help="Evaluate a trained Stable-Baselines3 policy")
    logger = logging.getLogger(__name__)
    return MetaEvalSB3Command(base, Sb3EvalScriptSettings, eval_main, logger).make()


def test_eval_cli_forwards_checkpoint_and_defaults(
    mock_eval_app, mock_main, tmp_path: Path
):
    checkpoint = tmp_path / "policy.zip"
    checkpoint.write_bytes(b"x")
    mock_eval_app.meta(
        ["ppo", "--checkpoint", str(checkpoint)], result_action="return_value"
    )
    mock_main.assert_called_once()
    args = mock_main.call_args[0][0]
    assert isinstance(args, Sb3EvalScriptSettings)
    assert args.checkpoint == checkpoint
    assert args.n_eval_episodes == 10
    assert args.deterministic is True


def test_eval_cli_custom_episodes(mock_eval_app, mock_main, tmp_path: Path):
    checkpoint = tmp_path / "policy.zip"
    checkpoint.write_bytes(b"x")
    mock_eval_app.meta(
        [
            "ppo",
            "--checkpoint",
            str(checkpoint),
            "--n-eval-episodes",
            "3",
            "--no-deterministic",
        ],
        result_action="return_value",
    )
    args = mock_main.call_args[0][0]
    assert args.n_eval_episodes == 3
    assert args.deterministic is False


def test_sb3_eval_main_on_real_vec_env(dummy_sb3_policy_zip, make_vec_env_server):
    pytest.importorskip("stable_baselines3")
    import gymnasium as gym

    port = make_vec_env_server([lambda: gym.make("CartPole-v1")])
    args = Sb3EvalScriptSettings(
        checkpoint=dummy_sb3_policy_zip,
        n_eval_episodes=2,
        environment_settings=EnvironmentSettings(
            protocol_settings=GrpcProtocolConfig(url="localhost", port=port),
        ),
    )
    mean_r, std_r = eval_main(args)
    assert isinstance(mean_r, (int, float)) and isinstance(std_r, (int, float))
    assert math.isfinite(mean_r) and math.isfinite(std_r)


def test_sb3_eval_cli_on_real_vec_env(
    dummy_sb3_policy_zip, make_vec_env_server, sb3_eval_meta_app
):
    """End-to-end ``schola sb3 eval`` parsing and ``eval_main`` on a live gRPC vec env."""
    pytest.importorskip("stable_baselines3")
    import gymnasium as gym

    port = make_vec_env_server([lambda: gym.make("CartPole-v1")])
    mean_r, std_r = sb3_eval_meta_app.meta(
        [
            "ppo",
            "--checkpoint",
            str(dummy_sb3_policy_zip),
            "--port",
            str(port),
            "--url",
            "localhost",
            "--n-eval-episodes",
            "2",
        ],
        result_action="return_value",
    )
    assert math.isfinite(mean_r) and math.isfinite(std_r)
