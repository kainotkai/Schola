# Copyright (c) 2023-2025 Advanced Micro Devices, Inc. All Rights Reserved.
from itertools import chain
from setuptools import setup, find_packages
import sys


def get_ray_deps():
    return [
        "ray[tune]>=2.43", #>=2.43 for vectorized multiagent on new stack
        "dm_tree",
        "lz4",
        "scikit-image",
        "pyyaml",
        "scipy",
        "typer",
        "rich",
    ]


def get_sb3_deps():
    return ["stable-baselines3>=2.6", "tqdm", "rich"]


def get_docs_deps():
    return ["sphinx", "breathe", "sphinx_rtd_theme", "sphinx_book_theme", "sphinx-tabs", "sphinx-copybutton"]


def get_minari_deps():
    return ["minari[hdf5,create]"]


def get_test_deps():
    return ["pytest", "pytest-timeout", "pytest-cov", "minigrid"]


def merge_deps(*dep_lists):
    return list(set(chain.from_iterable(dep_lists)))


def get_all_deps():
    return merge_deps(get_sb3_deps(), get_ray_deps())


if __name__ == "__main__":
    # load readme
    desc = None
    with open("../../README.md", "rt") as readme:
        desc = readme.read()
    assert desc != None, "failed to load readme"

    setup(
        name="schola",
        version="2.0.0",
        python_requires=">=3.9, <3.13",
        author="Advanced Micro Devices, Inc.",
        author_email="alexcann@amd.com",
        packages=find_packages(),
        description="Schola is a toolkit/plugin for Unreal Engine that facilitates training agents using reinforcement learning frameworks.",
        long_description=desc,
        long_description_content_type="text/markdown",
        install_requires=[
            "protobuf>=3.20",
            "grpcio>=1.51.1",
            "onnx>=1.11, <1.16.2",
            "gymnasium>=1.1.0",
            "backports.strenum; python_version<'3.11'",
            "cyclopts>=4.0"
        ],
        extras_require={
            "sb3": get_sb3_deps(),
            "rllib": get_ray_deps(),  # these are the ray[rllib] requirements ignoring the gym one
            "minari": get_minari_deps(),
            "all": get_all_deps(),
            "docs": get_docs_deps(),
            "test": get_test_deps(),
        },
        entry_points={
            "console_scripts": [
                "schola = schola.scripts.launch:main"
            ]
        },
    )
