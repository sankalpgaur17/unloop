"""unloop: turn slow pandas loops into fast, verified vectorized code."""

__version__ = "0.0.1"

from unloop.optimizer import optimize

__all__ = ["optimize"]
