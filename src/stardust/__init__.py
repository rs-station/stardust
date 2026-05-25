"""Stardust: Modular coordinate refinement library."""

from stardust.refinementlogger.config import RefinementConfig
from stardust.refinementlogger.engine import RefinementEngine

try:
    from stardust._version import version as __version__
except ImportError:  # pragma: no cover - fallback when not installed
    __version__ = "0.0.0"

__all__ = [
    "RefinementEngine",
    "RefinementConfig",
]
