# -*- coding: utf-8 -*-
"""Slow tests are opt-in.

The exhaustive Quran sweeps take minutes. Keeping them behind a flag is what
lets the default suite stay fast enough to run on every edit - a suite people
skip catches nothing.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", default=False,
                     help="run the exhaustive all-6236-ayat sweeps")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: exhaustive sweep, minutes to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        return
    skip = pytest.mark.skip(reason="needs --run-slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
