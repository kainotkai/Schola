# Copyright (c) 2026 Advanced Micro Devices, Inc. All Rights Reserved.
"""Tests for the RLlib eval CLI."""

import logging
from pathlib import Path

import pytest
from cyclopts import App

from schola.scripts.rllib.eval.eval import RllibEvalCommand, main as eval_main
from schola.scripts.rllib.eval.settings import RllibEvalScriptSettings
from schola.scripts.rllib.settings import ResourceSettings


@pytest.fixture
def mock_main(mocker):
    return mocker.patch("schola.scripts.rllib.eval.eval.main")


@pytest.fixture
def mock_eval_app(mock_main):
    base = App(name="eval", help="Evaluate a trained RLlib policy from a checkpoint")
    logger = logging.getLogger(__name__)
    return RllibEvalCommand(base, RllibEvalScriptSettings, mock_main, logger).make()


@pytest.fixture
def rllib_eval_meta_app():
    """Real ``schola rllib eval`` Cyclopts meta-app (invokes ``eval_main``)."""
    base = App(name="eval", help="Evaluate a trained RLlib policy from a checkpoint")
    logger = logging.getLogger(__name__)
    return RllibEvalCommand(base, RllibEvalScriptSettings, eval_main, logger).make()


@pytest.fixture
def dummy_rllib_checkpoint_dir(tmp_path: Path, ray_cluster):
    """
    Train a tiny PPO on ``CartPole-v1`` and save a checkpoint directory.

    Uses the session ``ray_cluster`` so ``eval_main`` can run with
    ``ResourceSettings(using_cluster=True)`` without double ``ray.init``.
    """
    pytest.importorskip("ray")
    from ray.rllib.algorithms.ppo import PPOConfig

    config = (
        PPOConfig()
        .environment("CartPole-v1")
        .env_runners(num_env_runners=0)
        .training(
            train_batch_size=200,
            minibatch_size=200,
            num_sgd_iter=1,
        )
        .api_stack(
            enable_rl_module_and_learner=True,
            enable_env_runner_and_connector_v2=True,
        )
        .learners(num_learners=0)
    )
    algo = config.build_algo()
    try:
        algo.train()
        ckpt = tmp_path / "rllib_eval_ckpt"
        algo.save(str(ckpt))
        return ckpt
    finally:
        algo.stop()


def test_eval_cli_forwards_checkpoint_and_defaults(
    mock_eval_app, mock_main, tmp_path: Path
):
    ckpt = tmp_path / "checkpoint_000001"
    ckpt.mkdir()
    mock_eval_app.meta(["--checkpoint", str(ckpt)], result_action="return_value")
    mock_main.assert_called_once()
    args = mock_main.call_args[0][0]
    assert isinstance(args, RllibEvalScriptSettings)
    assert args.checkpoint == ckpt
    assert args.n_eval_episodes == 10


def test_eval_cli_custom_episodes(mock_eval_app, mock_main, tmp_path: Path):
    ckpt = tmp_path / "c"
    ckpt.mkdir()
    mock_eval_app.meta(
        ["--checkpoint", str(ckpt), "--n-eval-episodes", "5"],
        result_action="return_value",
    )
    args = mock_main.call_args[0][0]
    assert args.n_eval_episodes == 5


@pytest.mark.xdist_group(name="ray-cluster")
@pytest.mark.timeout(180)
def test_rllib_eval_main_on_real_checkpoint(dummy_rllib_checkpoint_dir):
    pytest.importorskip("ray")
    args = RllibEvalScriptSettings(
        checkpoint=dummy_rllib_checkpoint_dir,
        n_eval_episodes=2,
        resource_settings=ResourceSettings(using_cluster=True),
    )
    results = eval_main(args)
    assert isinstance(results, dict)
    env_metrics = results.get("env_runners") or results.get("evaluation")
    assert env_metrics is not None


@pytest.mark.xdist_group(name="ray-cluster")
@pytest.mark.timeout(180)
def test_rllib_eval_cli_on_real_checkpoint(
    dummy_rllib_checkpoint_dir, rllib_eval_meta_app
):
    """End-to-end ``schola rllib eval`` parsing and ``eval_main`` on a real checkpoint."""
    pytest.importorskip("ray")
    results = rllib_eval_meta_app.meta(
        [
            "--checkpoint",
            str(dummy_rllib_checkpoint_dir),
            "--n-eval-episodes",
            "2",
            "--using-cluster",
        ],
        result_action="return_value",
    )
    assert isinstance(results, dict)
    env_metrics = results.get("env_runners") or results.get("evaluation")
    assert env_metrics is not None
