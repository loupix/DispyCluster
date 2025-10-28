$env:CONDA_DEFAULT_ENV
conda activate dispycluster

Write-Host "Environnement actif: $env:CONDA_DEFAULT_ENV"

# Config Redis distant
Set-Item Env:REDIS_HOST node13.lan
Set-Item Env:REDIS_PORT 6379
Set-Item Env:CELERY_BROKER_URL redis://node13.lan:6379/0
Set-Item Env:CELERY_RESULT_BACKEND redis://node13.lan:6379/1

# Config logging
Set-Item Env:LOG_LEVEL INFO
Set-Item Env:LOG_FILE logs/dispycluster.log

# Vérifier dépendances minimales (celery, redis)
python -c "import celery, redis" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation des dépendances web..."
    pip install -r web/requirements.txt
}

# Lancer Celery (worker + beat) en arrière-plan dans ce même terminal
Write-Host "Démarrage Celery worker en tâche de fond..."
$null = Start-Job -Name dispy_celery -ScriptBlock {
    # Reconfigurer l'environnement dans le job
    $env:REDIS_HOST = "node13.lan"
    $env:REDIS_PORT = "6379"
    $env:CELERY_BROKER_URL = "redis://node13.lan:6379/0"
    $env:CELERY_RESULT_BACKEND = "redis://node13.lan:6379/1"

    # Activer conda dans le job avec logs détaillés
    & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; celery -A web.celery_app.celery_app worker --loglevel=debug --concurrency=1"
}

Write-Host "Démarrage Celery beat (scheduler) en tâche de fond..."
$null = Start-Job -Name dispy_celery_beat -ScriptBlock {
    # Reconfigurer l'environnement dans le job
    $env:REDIS_HOST = "node13.lan"
    $env:REDIS_PORT = "6379"
    $env:CELERY_BROKER_URL = "redis://node13.lan:6379/0"
    $env:CELERY_RESULT_BACKEND = "redis://node13.lan:6379/1"

    # Activer conda dans le job avec logs détaillés
    & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; celery -A web.celery_app.celery_app beat --loglevel=debug"
}

Start-Sleep -Seconds 3

# Afficher les logs de Celery pour debug
Write-Host "Vérification des logs Celery..."
try {
    $celeryLogs = Receive-Job -Name dispy_celery -ErrorAction Stop
    if ($celeryLogs) {
        Write-Host "=== LOGS CELERY ==="
        $celeryLogs | ForEach-Object { Write-Host $_ }
        Write-Host "=================="
    }
} catch {
    Write-Host "Pas de logs Celery disponibles encore"
}

# Démarrer les services legacy en arrière-plan (optionnel)
$StartLegacyServices = $false
if ($StartLegacyServices) {
    Write-Host "Démarrage des services legacy en tâche de fond..."
    $env:PYTHONUNBUFFERED = "1"
    $global:svc_controller = Start-Job -Name svc_controller -ScriptBlock { & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; python legacy/services/cluster_controller.py" }
    Start-Sleep -Seconds 1
    $global:svc_monitoring = Start-Job -Name svc_monitoring -ScriptBlock { & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; python legacy/services/monitoring_service.py" }
    Start-Sleep -Seconds 1
    $global:svc_scheduler = Start-Job -Name svc_scheduler -ScriptBlock { & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; python legacy/services/scheduler_service.py" }
    Start-Sleep -Seconds 1
    $global:svc_gateway = Start-Job -Name svc_gateway -ScriptBlock { & pwsh -NoLogo -NoProfile -Command "conda activate dispycluster; python legacy/services/api_gateway.py" }

    # Vérifier les /health avant de lancer l'UI
    Write-Host "Vérification des services (health)..."
    $healthTargets = @(
        @{ Name = 'cluster_controller'; Url = 'http://localhost:8081/health' },
        @{ Name = 'monitoring';         Url = 'http://localhost:8082/health' },
        @{ Name = 'scheduler';          Url = 'http://localhost:8083/health' },
        @{ Name = 'api_gateway';        Url = 'http://localhost:8084/health' }
    )

    foreach ($t in $healthTargets) {
        $ok = $false
        for ($i=0; $i -lt 20; $i++) {
            try {
                $resp = Invoke-WebRequest -Uri $t.Url -UseBasicParsing -TimeoutSec 2
                if ($resp.StatusCode -eq 200) { $ok = $true; break }
            } catch {}
            Start-Sleep -Seconds 1
        }
        if ($ok) { Write-Host ("✓ {0} en ligne: {1}" -f $t.Name, $t.Url) }
        else { Write-Host ("⚠ {0} hors ligne: {1}" -f $t.Name, $t.Url) }
    }
}


# Lancer l'API/UI en avant-plan
Write-Host "Démarrage de l'API/UI (Uvicorn) sur http://localhost:8085..."
Write-Host "📊 Graphiques disponibles sur: http://localhost:8085/monitoring"
Write-Host "🔧 API Graphiques: http://localhost:8085/api/graphs/"
Set-Item Env:WEB_SIMULATE_NODES 0
uvicorn web.app:app --host 0.0.0.0 --port 8085

# À l'arrêt de l'API, tenter d'arrêter Celery proprement
try {
    $jobInfo = Get-Job -Name dispy_celery -ErrorAction Stop
} catch {
    $jobInfo = $null
}
if ($jobInfo -and $jobInfo.State -eq 'Running') {
    Write-Host "Arrêt de Celery..."
    Stop-Job -Name dispy_celery
    Remove-Job -Name dispy_celery
}

# Arrêter les services legacy si démarrés
if ($StartLegacyServices) {
    foreach ($name in @('svc_gateway','svc_scheduler','svc_monitoring','svc_controller')) {
        try {
            $j = Get-Job -Name $name -ErrorAction Stop
            if ($j -and $j.State -eq 'Running') {
                Write-Host "Arrêt $name..."
                Stop-Job -Name $name
                Remove-Job -Name $name
            }
        } catch {}
    }
}

