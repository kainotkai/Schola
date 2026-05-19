# Copyright (c) 2026 Advanced Micro Devices, Inc. All Rights Reserved.

"""Tests for ``IdManager`` agent and environment ID bookkeeping."""

from schola.core.utils.id_manager import IdManager


def test_agent_types_are_normalized_to_known_ids():
    """Agent type metadata is kept alongside the IDs it describes."""
    id_manager = IdManager(
        [["AgentA", "AgentB"], ["AgentC"]],
        {
            0: {"AgentA": "TeamA"},
            1: {"AgentC": "TeamC", "UnknownAgent": "Ignored"},
            2: {"OtherEnvAgent": "Ignored"},
        },
    )

    assert id_manager.agent_types == {
        0: {"AgentA": "TeamA", "AgentB": ""},
        1: {"AgentC": "TeamC"},
    }
    assert id_manager.agent_types_for_env(0) == {
        "AgentA": "TeamA",
        "AgentB": "",
    }
    assert id_manager.get_agent_type(1, "AgentC") == "TeamC"
    assert id_manager.get_agent_type(1, "MissingAgent") == ""


def test_agent_types_accept_list_metadata_shape():
    """Protocol metadata can also arrive as a list indexed by environment ID."""
    id_manager = IdManager(
        [["AgentA"], ["AgentB"]],
        [{"AgentA": "TeamA"}, {"AgentB": "TeamB"}],
    )

    assert id_manager.agent_types == {
        0: {"AgentA": "TeamA"},
        1: {"AgentB": "TeamB"},
    }


def test_agent_type_accessors_return_copies():
    """Callers should not mutate IdManager's normalized metadata by accident."""
    id_manager = IdManager([["AgentA"]], {0: {"AgentA": "TeamA"}})

    agent_types = id_manager.agent_types
    agent_types[0]["AgentA"] = "Changed"
    env_agent_types = id_manager.agent_types_for_env(0)
    env_agent_types["AgentA"] = "Changed"

    assert id_manager.get_agent_type(0, "AgentA") == "TeamA"
