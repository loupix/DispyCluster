"""Worker GPU (exemple).

Montre comment vérifier la présence de CUDA via `nvidia-smi` et fournit une
fonction factice de calcul vectoriel.
"""

from typing import Optional


def gpu_available() -> bool:
    """Retourne True si `nvidia-smi` est présent dans le PATH."""
    import shutil
    return shutil.which("nvidia-smi") is not None


def vector_add(n: int = 1000000) -> Optional[int]:
    """Additionne deux vecteurs [0..n) et retourne la somme du résultat.

    Si aucune GPU dispo, l'opération est effectuée en CPU.
    """
    # Simule une charge GPU, mais ici on fait une addition CPU si pas de GPU
    a = list(range(n))
    b = list(range(n))
    c = [x + y for x, y in zip(a, b)]
    return sum(c)

