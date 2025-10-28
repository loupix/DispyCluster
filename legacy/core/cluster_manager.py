"""Gestionnaire principal du cluster DispyCluster.

Responsabilités:
- Maintenir la liste des noeuds et leur statut logique (ready, down, etc.)
- Offrir une méthode simple `submit_job` qui sélectionne un noeud où envoyer un job

Remarque: ici on ne fait pas l'envoi réel. C'est un stub pour connecter
ensuite Dispy ou une autre couche RPC.
"""

from typing import List, Dict, Optional


class ClusterManager:
    def __init__(self, nodes: Optional[List[str]] = None) -> None:
        """Initialise le gestionnaire avec une liste optionnelle de noeuds.

        Args:
            nodes: liste d'hôtes (DNS ou IP) connus du cluster.
        """
        self.nodes: List[str] = nodes or []
        self.node_status: Dict[str, str] = {node: "unknown" for node in self.nodes}

    def set_nodes(self, nodes: List[str]) -> None:
        """Met à jour la liste des noeuds et préserve les statuts connus."""
        self.nodes = nodes
        self.node_status = {node: self.node_status.get(node, "unknown") for node in nodes}

    def mark_node_status(self, node: str, status: str) -> None:
        """Marque le statut d'un noeud.

        Exemples de `status`: "ready", "down", "busy".
        """
        if node not in self.node_status:
            self.node_status[node] = status
        else:
            self.node_status[node] = status

    def get_available_nodes(self) -> List[str]:
        """Retourne la liste des noeuds marqués comme prêts."""
        return [n for n, s in self.node_status.items() if s == "ready"]

    def submit_job(self, job_payload: dict) -> Optional[str]:
        """Sélectionne un noeud pour exécuter `job_payload`.

        Stratégie minimale: prend le premier noeud "ready".
        Retourne l'hôte choisi ou None si aucun noeud disponible.
        """
        # Sélection très simple: premier noeud ready
        available = self.get_available_nodes()
        if not available:
            return None
        target = available[0]
        # Ici on enverrait le job via Dispy ou RPC
        return target

