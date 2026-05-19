# Copyright (c) 2026 Advanced Micro Devices, Inc. All Rights Reserved.
"""Unit tests for ``command_template`` using lightweight fake script/algorithm dataclasses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Dict, Type, Union
from unittest.mock import MagicMock

import pytest
import yaml
from cyclopts import App, Parameter, validators

from schola.scripts.common.settings import (
    EnvironmentSettings,
    ExternalSimulatorConfig,
    GrpcProtocolConfig,
    UnrealExecutableSimulatorConfig,
)
from schola.scripts.common.command_template import MetaAlgCommand, MetaNoAlgCommand

# --- Fake script / algorithm types (minimal stand-ins for SB3/RLlib settings) ---


@dataclass
class FakeAlgoAlpha:
    """First fake algorithm; a few CLI-overridable fields."""

    alpha: Annotated[float, Parameter(validator=validators.Number(gt=0.0, lte=1.0))] = (
        0.5
    )
    "Fake learning-rate-like scalar."

    extra: int = 7


@dataclass
class FakeAlgoBeta:
    """Second fake algorithm for multi-algorithm routing tests."""

    beta_steps: Annotated[int, Parameter(validator=validators.Number(gte=1))] = 11


@dataclass
class FakeScriptSettings:
    """Minimal script container compatible with ``MetaAlgCommand`` wiring."""

    environment_settings: EnvironmentSettings = field(
        default_factory=lambda: EnvironmentSettings(
            protocol_settings=GrpcProtocolConfig(),
        )
    )
    algorithm_settings: Annotated[
        Union[FakeAlgoAlpha, FakeAlgoBeta], Parameter(show=False, parse=False)
    ] = field(default_factory=FakeAlgoAlpha)


@dataclass
class FakeNoAlgScriptSettings:
    """Script settings without an algorithm subcommand (``MetaNoAlgCommand``)."""

    environment_settings: EnvironmentSettings = field(
        default_factory=lambda: EnvironmentSettings(
            protocol_settings=GrpcProtocolConfig(),
        )
    )


class FakeMetaAlgCommand(MetaAlgCommand[FakeScriptSettings]):
    @property
    def algorithm_table(self) -> Dict[str, Type[Any]]:
        return {
            "alpha": FakeAlgoAlpha,
            "beta": FakeAlgoBeta,
        }

    @property
    def algorithm_help(self) -> Dict[str, str]:
        return {
            "alpha": "Fake algorithm alpha (tests).",
            "beta": "Fake algorithm beta (tests).",
        }


@pytest.fixture
def mock_main() -> MagicMock:
    return MagicMock()


@pytest.fixture
def meta_app(mock_main: MagicMock):
    """Return ``app.meta.meta`` — the parse entry that runs ``train_command_config_handler`` first."""
    app = App(name="train-fake", help="Fake train CLI for template tests")
    logger = logging.getLogger("test_command_template")
    logger.addHandler(logging.NullHandler())
    built = FakeMetaAlgCommand(app, FakeScriptSettings, mock_main, logger).make()
    # ``make()`` returns ``app.meta``; config YAML handling lives on ``app.meta.meta.default``.
    return built.meta


@pytest.fixture
def no_alg_meta_app(mock_main: MagicMock):
    """``MetaNoAlgCommand``: entry is ``app.meta.meta`` (config handler outermost)."""
    app = App(name="train-no-alg-fake", help="Fake no-algorithm train CLI")
    logger = logging.getLogger("test_command_template_no_alg")
    logger.addHandler(logging.NullHandler())
    built = MetaNoAlgCommand(app, FakeNoAlgScriptSettings, mock_main, logger).make()
    return built.meta


def test_yaml_split_meta_no_alg_config_handler():
    """Like ``make_train_config_handler``: only ``environment.simulator`` is removed; ``algorithm`` stays."""
    raw = """
algorithm:
  reserved: 1
environment:
  simulator:
    external: {}
"""
    config_dict = yaml.safe_load(raw) or {}
    sim_config_dict = (config_dict.get("environment") or {}).pop("simulator", {})
    assert sim_config_dict == {"external": {}}
    assert config_dict.get("algorithm") == {"reserved": 1}
    assert "simulator" not in (config_dict.get("environment") or {})


def test_no_alg_cli_default_external_simulator(no_alg_meta_app, mock_main: MagicMock):
    """Default route invokes external simulator and ``main`` with script args."""
    no_alg_meta_app([], result_action="return_value", exit_on_error=False)

    mock_main.assert_called_once()
    args = mock_main.call_args[0][0]
    assert isinstance(args, FakeNoAlgScriptSettings)
    assert isinstance(
        args.environment_settings.simulator_settings, ExternalSimulatorConfig
    )


def test_no_alg_cli_explicit_external(no_alg_meta_app, mock_main: MagicMock):
    no_alg_meta_app(["external"], result_action="return_value", exit_on_error=False)

    mock_main.assert_called_once()
    assert isinstance(
        mock_main.call_args[0][0].environment_settings.simulator_settings,
        ExternalSimulatorConfig,
    )


def test_no_alg_cli_executable(no_alg_meta_app, mock_main: MagicMock, tmp_path: Path):
    exe = tmp_path / "FakeNoAlg.exe"
    exe.write_bytes(b"")
    no_alg_meta_app(
        ["executable", "--executable-path", str(exe)],
        result_action="return_value",
        exit_on_error=False,
    )
    sim = mock_main.call_args[0][0].environment_settings.simulator_settings
    assert isinstance(sim, UnrealExecutableSimulatorConfig)
    assert sim.executable_path == exe


def test_no_alg_config_file_yaml(no_alg_meta_app, mock_main: MagicMock, tmp_path: Path):
    """``--config-file`` loads YAML; algorithm key stays in flat config (no pop)."""
    cfg = tmp_path / "no_alg.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "environment": {
                    "simulator": {
                        "external": {},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    no_alg_meta_app(
        ["--config-file", str(cfg), "external"],
        result_action="return_value",
        exit_on_error=False,
    )

    mock_main.assert_called_once()
    assert isinstance(
        mock_main.call_args[0][0].environment_settings.simulator_settings,
        ExternalSimulatorConfig,
    )


def test_cli_default_algorithm_selects_alpha_and_external_simulator(
    meta_app, mock_main: MagicMock
):
    """``<algorithm>`` alone should default to the external simulator and invoke ``main`` once."""
    meta_app(["alpha"], result_action="return_value", exit_on_error=False)

    mock_main.assert_called_once()
    args: FakeScriptSettings = mock_main.call_args[0][0]
    assert isinstance(args, FakeScriptSettings)
    assert isinstance(args.algorithm_settings, FakeAlgoAlpha)
    assert args.algorithm_settings.alpha == 0.5
    assert isinstance(
        args.environment_settings.simulator_settings, ExternalSimulatorConfig
    )


def test_cli_overrides_algorithm_fields(meta_app, mock_main: MagicMock):
    """CLI tokens should override fake algorithm defaults."""
    meta_app(
        ["alpha", "--alpha", "0.25", "--extra", "99"],
        result_action="return_value",
        exit_on_error=False,
    )

    args: FakeScriptSettings = mock_main.call_args[0][0]
    assert isinstance(args.algorithm_settings, FakeAlgoAlpha)
    assert args.algorithm_settings.alpha == 0.25
    assert args.algorithm_settings.extra == 99


def test_cli_second_algorithm_route(meta_app, mock_main: MagicMock):
    meta_app(
        ["beta", "--beta-steps", "42"],
        result_action="return_value",
        exit_on_error=False,
    )

    args: FakeScriptSettings = mock_main.call_args[0][0]
    assert isinstance(args.algorithm_settings, FakeAlgoBeta)
    assert args.algorithm_settings.beta_steps == 42


def test_cli_executable_simulator(meta_app, mock_main: MagicMock, tmp_path: Path):
    """Non-default simulator subcommand should attach ``UnrealExecutableSimulatorConfig``."""
    exe = tmp_path / "FakeGame.exe"
    exe.write_bytes(b"")

    meta_app(
        [
            "alpha",
            "executable",
            "--executable-path",
            str(exe),
        ],
        result_action="return_value",
        exit_on_error=False,
    )

    args: FakeScriptSettings = mock_main.call_args[0][0]
    sim = args.environment_settings.simulator_settings
    assert isinstance(sim, UnrealExecutableSimulatorConfig)
    assert sim.executable_path == exe


def test_config_file_yaml_merges_algorithm_environment_and_simulator(
    meta_app, mock_main: MagicMock, tmp_path: Path
):
    """YAML ``algorithm`` / ``environment.simulator`` split; algorithm block merges into CLI."""
    # Omit nested ``environment.protocol_settings`` here: ``flatten_dict_no_prefix`` yields
    # leaf keys like ``port`` that do not match cyclopts option names for ``FakeScriptSettings``
    # (that path is covered by integration tests with full script settings types).
    cfg = tmp_path / "train.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "algorithm": {
                    "alpha": {
                        "alpha": 0.11,
                        "extra": 3,
                    }
                },
                "environment": {
                    "simulator": {
                        "external": {},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    meta_app(
        [
            "--config-file",
            str(cfg),
            "alpha",
            "external",
        ],
        result_action="return_value",
        exit_on_error=False,
    )

    mock_main.assert_called_once()
    args: FakeScriptSettings = mock_main.call_args[0][0]
    assert isinstance(args.algorithm_settings, FakeAlgoAlpha)
    assert args.algorithm_settings.alpha == 0.11
    assert args.algorithm_settings.extra == 3
    assert isinstance(
        args.environment_settings.simulator_settings, ExternalSimulatorConfig
    )


def test_config_file_without_optional_simulator_key(
    meta_app, mock_main: MagicMock, tmp_path: Path
):
    """Missing ``environment.simulator`` still runs; inner command returns ``None`` (``main`` stub)."""
    cfg = tmp_path / "minimal.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "algorithm": {"alpha": {}},
                "environment": {},
            }
        ),
        encoding="utf-8",
    )

    meta_app(
        ["--config-file", str(cfg), "alpha"],
        result_action="return_value",
        exit_on_error=False,
    )

    mock_main.assert_called_once()
    args: FakeScriptSettings = mock_main.call_args[0][0]
    assert isinstance(args.algorithm_settings, FakeAlgoAlpha)


def _write_invalid_yaml(path: Path) -> None:
    """YAML that ``yaml.safe_load`` rejects (nested mapping on one line)."""
    path.write_text("foo: bar: baz\n", encoding="utf-8")


def test_invalid_yaml_config_file_logs_error_with_details(
    meta_app, mock_main: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """Invalid ``--config-file`` triggers ``logger.error`` with path and parser context."""
    cfg = tmp_path / "bad.yaml"
    _write_invalid_yaml(cfg)

    with caplog.at_level(logging.ERROR):
        meta_app(
            ["--config-file", str(cfg), "alpha"],
            result_action="return_value",
            exit_on_error=False,
        )

    error_messages = [
        r.getMessage() for r in caplog.records if r.levelno == logging.ERROR
    ]
    assert error_messages, "expected at least one ERROR log for invalid YAML"
    combined = " ".join(error_messages)
    assert "Error loading config file" in combined
    assert str(cfg) in combined
    # ``load_yaml_file`` appends ``MarkedYAMLError.problem_mark`` when present
    assert " at " in combined


def test_invalid_yaml_no_alg_config_file_logs_error_with_details(
    no_alg_meta_app,
    mock_main: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    """``MetaNoAlgCommand``: invalid YAML still logs a detailed error before empty config."""
    cfg = tmp_path / "bad_no_alg.yaml"
    _write_invalid_yaml(cfg)

    with caplog.at_level(logging.ERROR):
        no_alg_meta_app(
            ["--config-file", str(cfg), "external"],
            result_action="return_value",
            exit_on_error=False,
        )

    error_messages = [
        r.getMessage() for r in caplog.records if r.levelno == logging.ERROR
    ]
    assert error_messages
    combined = " ".join(error_messages)
    assert "Error loading config file" in combined
    assert str(cfg) in combined
    assert " at " in combined
