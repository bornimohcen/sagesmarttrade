from __future__ import annotations

from itertools import product
from typing import Dict, List


def generate_param_combinations(param_grid: Dict[str, List]) -> List[Dict[str, object]]:
    """Generate all combinations for a parameter grid."""
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos: List[Dict[str, object]] = []
    for vals in product(*values):
        combos.append({k: v for k, v in zip(keys, vals)})
    return combos


__all__ = ["generate_param_combinations"]

