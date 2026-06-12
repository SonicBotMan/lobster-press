# -*- coding: utf-8 -*-
"""
LobsterPress - Cognitive Memory System for AI Agents

Single source of truth — other modules import version from here.
"""

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("lobster-press")
except PackageNotFoundError:
    __version__ = "5.1.0"

__author__ = "SonicBotMan"


def get_version():
    """Return the current version string."""
    return __version__
