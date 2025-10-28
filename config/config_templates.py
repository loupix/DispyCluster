from typing import List

DEFAULT_WORKERS: List[str] = [
    "node6.lan",
    "node7.lan",
    "node9.lan",
    "node10.lan",
    "node11.lan",
    "node12.lan",
    "node14.lan",
]

MASTER_HOST = "node13.lan"

PROMETHEUS_TARGETS = [f"{w}:9100" for w in DEFAULT_WORKERS]

