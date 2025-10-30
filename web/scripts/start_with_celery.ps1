$env:CONDA_DEFAULT_ENV
conda activate dispycluster

# Config Redis distant
Set-Item Env:REDIS_HOST node13.lan
Set-Item Env:REDIS_PORT 6379
Set-Item Env:CELERY_BROKER_URL redis://node13.lan:6379/0
Set-Item Env:CELERY_RESULT_BACKEND redis://node13.lan:6379/1

# Démarrer Celery worker
Start-Process pwsh -ArgumentList "conda activate dispycluster; celery -A web.celery_app.celery_app worker --loglevel=info"

# Démarrer Celery beat
Start-Process pwsh -ArgumentList "conda activate dispycluster; celery -A web.celery_app.celery_app beat --loglevel=info"

# Démarrer l'API/UI
uvicorn web.app:app --host 0.0.0.0 --port 8085

