"""Utilitaires de découverte de noeuds.

Ici on implémente une découverte très simple basée sur:
- Une liste de candidats fournie (depuis l'inventaire YAML, par exemple)
- Un "ping" TCP des ports 22 (SSH) et 9100 (node_exporter)

Si les deux sont atteignables, on considère le noeud comme prêt.
"""

import socket
from typing import List

def tcp_ping(host: str, port: int, timeout: float = 1.5) -> bool:
    """Retourne True si une connexion TCP au host:port réussit dans le timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def discover_nodes(candidates: List[str]) -> List[str]:
    """Filtre la liste de `candidates` pour ne garder que les noeuds prêts.

    Un noeud est "ready" si SSH (22) et node_exporter (9100) répondent.
    """
    # On considère ready si SSH et node_exporter répondent
    ready: List[str] = []
    for host in candidates:
        ssh_ok = tcp_ping(host, 22)
        ne_ok = tcp_ping(host, 9100)
        if ssh_ok and ne_ok:
            ready.append(host)
    return ready

