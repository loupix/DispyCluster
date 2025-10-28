import os
from celery import Celery


def _build_redis_url(default_db: int) -> str:
    host = os.getenv("REDIS_HOST", "node13.lan")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return f"redis://{host}:{port}/{default_db}"


broker_url = os.getenv("CELERY_BROKER_URL", _build_redis_url(0))
backend_url = os.getenv("CELERY_RESULT_BACKEND", _build_redis_url(1))

celery_app = Celery(
    "dispycluster",
    broker=broker_url,
    backend=backend_url,
    include=[
        "web.tasks.scraping",
        "web.tasks.monitoring",
    ],
)

celery_app.conf.update(
    task_soft_time_limit=60,
    task_time_limit=120,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_transport_options={"visibility_timeout": 3600},
    # Configuration spécifique Windows
    worker_pool='solo',  # Évite les problèmes de multiprocessing sur Windows
    worker_concurrency=1,
    beat_schedule={
        "collect-metrics-every-5s": {
            "task": "web.tasks.monitoring.collect_metrics",
            "schedule": 5.0,  # Collecte toutes les 5 secondes pour les graphiques
        },
    },
)

