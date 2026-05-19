# Copyright (c) 2026 Advanced Micro Devices, Inc. All Rights Reserved.

"""
Cyclopts template for generating Schola subcommands (multi-simulator and algorithm dispatch).
"""

from collections import defaultdict
from itertools import chain
import logging
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    NewType,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from cyclopts import App, ArgumentCollection, Parameter
import cyclopts
from cyclopts.argument import update_argument_collection
from schola.core.utils.dict_helpers import flatten_dict_no_prefix

from schola.scripts.common.settings import (
    UnrealExecutableSimulatorConfig,
    UnrealProjectSimulatorConfig,
    ExternalSimulatorConfig,
)

ScriptArgsType = TypeVar("ScriptArgsType")
SimulatorArgsType = Union[
    UnrealExecutableSimulatorConfig,
    UnrealProjectSimulatorConfig,
    ExternalSimulatorConfig,
]


class MetaCommand(Generic[ScriptArgsType]):
    """
    Factory for Cyclopts commands that bind simulator configs to a training entrypoint.

    Parameters
    ----------
    app : cyclopts.App
        Root CLI application.
    args_type : type
        Dataclass type for full script arguments.
    main_func : callable
        Invoked with a populated ``args_type`` instance.
    logger : logging.Logger
        Logger used when forwarding to ``main_func``.

    Notes
    -----
    ``make_simulator_command`` returns closures wired into Cyclopts ``Parameter`` layouts.
    """

    def __init__(
        self,
        app: App,
        args_type: Type[ScriptArgsType],
        main_func: Callable[[ScriptArgsType], Any],
        logger: logging.Logger,
    ):
        self.app = app
        self.args_type = args_type
        self._main_func = main_func
        self._logger = logger

    def make_simulator_command(self, simulator_type: Type[SimulatorArgsType]):
        SimulatorType = NewType("SimulatorType", simulator_type)  # type: ignore
        ArgsType = NewType("ArgsType", self.args_type)  # type: ignore
        _main_func = self._main_func
        if not issubclass(simulator_type, ExternalSimulatorConfig):
            # When all dataclass fields have defaults (e.g. ExternalSimulatorConfig),
            # cyclopts requires the parameter itself to carry a default value.
            try:
                _sim_default = simulator_type()
            except TypeError:
                _sim_default = None

            if _sim_default is not None:

                def completed_simulator_command(
                    simulator_args: Annotated[SimulatorType, Parameter(name="*")] = _sim_default,  # type: ignore
                    *,
                    hidden_script_args: Annotated[ArgsType, Parameter(parse=False)],
                ):
                    hidden_script_args.environment_settings.simulator_settings = simulator_args  # type: ignore
                    self._logger.debug("Arguments: %s", hidden_script_args)
                    return _main_func(hidden_script_args)

            else:

                def completed_simulator_command(
                    simulator_args: Annotated[SimulatorType, Parameter(name="*")],
                    *,
                    hidden_script_args: Annotated[ArgsType, Parameter(parse=False)],
                ):
                    hidden_script_args.environment_settings.simulator_settings = simulator_args  # type: ignore
                    self._logger.debug("Arguments: %s", hidden_script_args)
                    return _main_func(hidden_script_args)

            return completed_simulator_command
        else:

            def completed_editor_command(
                *,
                hidden_script_args: Annotated[ArgsType, Parameter(parse=False)],
            ):
                hidden_script_args.environment_settings.simulator_settings = (
                    ExternalSimulatorConfig()
                )  # type: ignore
                self._logger.debug("Arguments: %s", hidden_script_args)
                return_value = _main_func(hidden_script_args)
                return return_value

            return completed_editor_command

    @property
    def simulator_table(self) -> Dict[str, Type[SimulatorArgsType]]:
        return {
            "executable": UnrealExecutableSimulatorConfig,
            "project": UnrealProjectSimulatorConfig,
            "external": ExternalSimulatorConfig,
        }

    @property
    def simulator_help(self) -> Dict[str, str]:
        return {
            "executable": "Run Unreal from a pre-built executable.",
            "project": "Build and Run Unreal from a UProject File.",
            "external": "Connect to an externally managed UE process (e.g. Unreal Editor, Kubernetes pod, remote host). Default if no simulator is provided.",
        }

    @property
    def simulator_aliases(self) -> Dict[str, str | Iterable[str] | None]:
        return {
            "external": "editor",
            "project": None,
            "executable": None,
        }


def load_yaml_file(file_path: Path, logger: logging.Logger) -> Dict[str, Any]:
    """
    Load a YAML configuration file into a dictionary.

    Parameters
    ----------
    file_path : pathlib.Path
        Path to an existing YAML file.
    logger : logging.Logger
        Receives parse errors (including marked locations when available).

    Returns
    -------
    dict
        Parsed mapping, or ``{}`` if parsing fails.
    """
    import yaml

    # assume path exists
    try:
        with open(file_path, "r") as f:
            config_dict = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        # print the location of the yaml error
        error_message = f"Error loading config file {file_path}: {e}"
        if isinstance(e, yaml.MarkedYAMLError) and e.problem_mark is not None:
            error_message += f" at {e.problem_mark}"
        logger.error(error_message)
        return {}
    return config_dict


class _ScholaConfig(cyclopts.config.Dict):
    """
    Cyclopts dict config source tailored for Schola meta-CLI merging.

    Notes
    -----
    Behaves like ``cyclopts.config.Dict`` but passes ``None`` for the app stack when
    calling ``update_argument_collection``, which Schola's nested commands require.
    """

    def __call__(
        self, app: "App", commands: Tuple[str, ...], arguments: ArgumentCollection
    ):
        config: dict[str, Any] = self.config.copy()

        try:
            if self.use_commands_as_keys and len(commands) > 0:
                config = config[commands[-1]]
        except KeyError:
            return

        update_argument_collection(
            config,
            self.source,
            arguments,
            None,  # passing app stack breaks Schola meta-app config parsing
            root_keys=self.root_keys,
            allow_unknown=self.allow_unknown,
        )


class MetaAlgCommand(MetaCommand[ScriptArgsType]):
    """
    ``MetaCommand`` that nests one Cyclopts sub-app per supported RL algorithm.

    Notes
    -----
    Subclasses implement ``algorithm_table`` and ``algorithm_help`` to list backends.
    """

    def make_algorithm_command(
        self, algorithm_app: App, algorithm_type: Type[Any], args_type: Type[Any]
    ):
        ResolvedArgsType = NewType("ResolvedArgsType", args_type)  # type: ignore
        AlgorithmType = NewType("AlgorithmType", algorithm_type)  # type: ignore

        def algorithm_meta_command(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            algorithm_args: Annotated[AlgorithmType, Parameter(name="*")] = algorithm_type(),  # type: ignore
            hidden_script_args: Annotated[ResolvedArgsType, Parameter(parse=False)],
            hidden_sim_config_dict: Annotated[
                Optional[Dict[str, Any]], Parameter(parse=False)
            ] = None,
        ):  # type: ignore

            additional_kwargs = {
                "hidden_script_args": hidden_script_args,
            }
            hidden_script_args.algorithm_settings = algorithm_args  # type: ignore

            if hidden_sim_config_dict is not None:
                algorithm_app.config = [
                    _ScholaConfig(
                        hidden_sim_config_dict,
                        use_commands_as_keys=True,
                        allow_unknown=False,
                        source=f"config:environment:simulator",
                    ),
                ]

            command, bound, ignored = algorithm_app.parse_args(tokens)
            return command(*bound.args, **bound.kwargs, **additional_kwargs)

        return algorithm_meta_command

    def make_train_meta_command(self, args_type: Type[Any]):
        ResolvedArgsType = NewType("ResolvedArgsType", args_type)  # type: ignore

        def train_meta_command(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            script_args: Annotated[
                ResolvedArgsType,
                Parameter(name="*"),  # pyright: ignore[reportInvalidTypeForm]
            ] = self.args_type(),
            hidden_sim_config_dict: Annotated[
                Optional[Dict[str, Any]], Parameter(parse=False)
            ] = None,
        ):
            hidden_sim_config_dict = (
                {} if hidden_sim_config_dict is None else hidden_sim_config_dict
            )
            additional_kwargs = {
                "hidden_script_args": script_args,
                "hidden_sim_config_dict": hidden_sim_config_dict,
            }

            command, bound, ignored = self.app.parse_args(tokens)
            return command(*bound.args, **bound.kwargs, **additional_kwargs)

        return train_meta_command

    def make_train_config_handler(self):
        def train_command_config_handler(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            config_file: Annotated[
                Optional[cyclopts.types.ExistingYamlPath],
                Parameter(parse=True, show=True),
            ] = None,
        ):
            config_dict = {}
            if config_file is not None:
                config_dict = load_yaml_file(config_file, self._logger)

            alg_config_dict = config_dict.pop("algorithm", {})
            sim_config_dict = (config_dict.get("environment") or {}).pop(
                "simulator", {}
            )

            flat_config = flatten_dict_no_prefix(config_dict)
            self.app.meta.config = [
                _ScholaConfig(
                    flat_config,
                    use_commands_as_keys=False,
                    allow_unknown=False,
                    source=f"config",
                ),
            ]

            self.app.config = [
                _ScholaConfig(
                    alg_config_dict,
                    use_commands_as_keys=True,
                    allow_unknown=False,
                    source=f"config:algorithm",
                ),
            ]

            command, bound, ignored = self.app.meta.parse_args(tokens)

            additional_kwargs = {
                "hidden_sim_config_dict": sim_config_dict,
            }

            return command(*bound.args, **bound.kwargs, **additional_kwargs)

        return train_command_config_handler

    def make(self):
        # setup the default meta func on the base app to parse the Script Args
        self.app.meta.default(self.make_train_meta_command(self.args_type))
        # This takes the config file and adds it to the meta app to allow for the config to be aligned with the script args
        self.app.meta.meta.default(self.make_train_config_handler())

        self.app.group_commands = "Algorithm (Choose One)"
        # setup the algorithm commands (e.g. PPO, SAC, etc.)
        for algorithm in self.algorithm_table:
            algorithm_app = App(name=algorithm, group_commands="Simulator (Choose One)")
            algorithm_type = self.algorithm_table[algorithm]
            algorithm_app.meta.default(
                self.make_algorithm_command(
                    algorithm_app, algorithm_type, self.args_type
                )
            )

            for simulator_type in self.simulator_table:
                sim_command = self.make_simulator_command(
                    self.simulator_table[simulator_type]
                )
                if simulator_type == "external":
                    algorithm_app.default(sim_command)
                algorithm_app.command(
                    sim_command,
                    name=simulator_type,
                    alias=self.simulator_aliases[simulator_type],
                )
                algorithm_app[simulator_type].help = self.simulator_help[simulator_type]

            self.app.command(algorithm_app.meta, name=algorithm)
            self.app[algorithm].help = self.algorithm_help[algorithm]

        return self.app.meta

    @property
    def algorithm_table(self) -> Dict[str, Type[Any]]:
        raise NotImplementedError("algorithm_table must be implemented in the subclass")

    @property
    def algorithm_help(self) -> Dict[str, str]:
        return defaultdict(str)


class MetaNoAlgCommand(MetaCommand[ScriptArgsType]):
    """
    ``MetaCommand`` variant with a flat script argument tree plus optional YAML merge.

    Notes
    -----
    Used when algorithms are not split into separate Cyclopts subcommands.
    """

    def make_train_config_handler(self):
        def train_command_config_handler(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            config_file: Annotated[
                Optional[cyclopts.types.ExistingYamlPath], Parameter(parse=True)
            ] = None,
        ):
            config_dict = {}
            if config_file is not None:
                config_dict = load_yaml_file(config_file, self._logger)
            sim_config_dict = (config_dict.get("environment") or {}).pop(
                "simulator", {}
            )
            flat_config = flatten_dict_no_prefix(config_dict)
            self.app.meta.config = [
                _ScholaConfig(
                    flat_config,
                    use_commands_as_keys=False,
                    allow_unknown=False,
                    source=f"config",
                ),
            ]
            additional_kwargs = {
                "hidden_sim_config_dict": sim_config_dict,
            }
            command, bound, ignored = self.app.meta.parse_args(tokens)
            return command(*bound.args, **bound.kwargs, **additional_kwargs)

        return train_command_config_handler

    def make_train_meta_command(self, args_type: Type[Any]):
        ResolvedArgsType = NewType("ArgsType", args_type)  # type: ignore

        def train_meta_command(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            script_args: Annotated[ResolvedArgsType, Parameter(name="*")] = args_type(),
            hidden_sim_config_dict: Annotated[
                Optional[Dict[str, Any]], Parameter(parse=False)
            ] = None,
        ):  # type: ignore
            hidden_sim_config_dict = hidden_sim_config_dict or {}
            self.app.config = [
                _ScholaConfig(
                    hidden_sim_config_dict,
                    use_commands_as_keys=True,
                    allow_unknown=False,
                    source="config:environment:simulator",
                ),
            ]
            additional_kwargs = {
                "hidden_script_args": script_args,
            }

            command, bound, ignored = self.app.parse_args(tokens)
            return command(*bound.args, **bound.kwargs, **additional_kwargs)

        return train_meta_command

    def make(self):
        self.app.meta.default(self.make_train_meta_command(self.args_type))
        self.app.meta.meta.default(self.make_train_config_handler())

        self.app.group_commands = "Simulator (Choose One)"

        for simulator_type in self.simulator_table:
            sim_command = self.make_simulator_command(
                self.simulator_table[simulator_type]
            )
            if simulator_type == "external":
                self.app.default(sim_command)
            self.app.command(
                sim_command,
                name=simulator_type,
                alias=self.simulator_aliases[simulator_type],
            )
            self.app[simulator_type].help = self.simulator_help[simulator_type]

        return self.app.meta
