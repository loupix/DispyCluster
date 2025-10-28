"""Worker CPU (exemple).

Expose un calcul CPU-bound simple basé sur la série de Leibniz pour pi.
C'est lent mais idéal pour charger le CPU en test.
"""

from typing import Optional
import math


def compute_pi(iterations: int = 100000) -> Optional[float]:
    """Aproximates pi using the Leibniz series with `iterations` terms."""
    # Leibniz series (lent mais CPU-bound)
    if iterations <= 0:
        return None
    acc = 0.0
    for k in range(iterations):
        acc += ((-1) ** k) / (2 * k + 1)
    return 4 * acc

