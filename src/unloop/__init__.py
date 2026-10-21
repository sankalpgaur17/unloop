"""unloop: turn slow pandas loops into fast, verified vectorized code."""

__version__ = "1.0.0"

from unloop.magic import load_ipython_extension
from unloop.optimizer import optimize

__all__ = ["optimize"]