"""Configuration centralisée pour les services DispyCluster."""

import os
from typing import Dict, List

# Configuration du cluster
CLUSTER_NODES = [
    "node6.lan", "node7.lan", "node8.lan", "node9.lan", 
    "node10.lan", "node11.lan", "node12.lan", "node13.lan", "node14.lan"
]

# Ports des services
SERVICE_PORTS = {
    "cluster_controller": 8081,
    "monitoring": 8082,
    "scheduler": 8083,
    "api_gateway": 8084,
    "scraper": 8080,
    "dispy_scheduler": 51347,
    "node_exporter": 9100,
    "prometheus": 9090,
    "grafana": 3000
}

# URLs des services (pour l'API Gateway)
SERVICE_URLS = {
    "cluster_controller": f"http://localhost:{SERVICE_PORTS['cluster_controller']}",
    "monitoring": f"http://localhost:{SERVICE_PORTS['monitoring']}",
    "scheduler": f"http://localhost:{SERVICE_PORTS['scheduler']}",
    "scraper": f"http://localhost:{SERVICE_PORTS['scraper']}"
}

# Configuration des limites
LIMITS = {
    "max_pages_per_job": 1000,
    "max_urls_per_batch": 50,
    "max_timeout_seconds": 300,
    "max_priority": 10,
    "job_history_retention_hours": 24,
    "metrics_retention_hours": 24
}

# Configuration du monitoring
MONITORING_CONFIG = {
    "collection_interval_seconds": 30,
    "health_check_timeout": 5,
    "alert_thresholds": {
        "cpu_usage": 90,
        "memory_usage": 90,
        "disk_usage": 90,
        "temperature": 80
    }
}

# Configuration du scheduler
SCHEDULER_CONFIG = {
    "max_concurrent_jobs": 10,
    "job_timeout_seconds": 300,
    "retry_attempts": 3,
    "retry_delay_seconds": 60
}

# Configuration des workers
WORKER_CONFIG = {
    "ping_timeout": 5,
    "job_timeout": 30,
    "max_retries": 3,
    "health_check_interval": 60
}

# Configuration de la base de données (pour une future implémentation)
DATABASE_CONFIG = {
    "type": "sqlite",  # ou "postgresql", "mysql"
    "path": "/opt/dispycluster/data/cluster.db",
    "backup_interval_hours": 24,
    "max_backups": 7
}

# Configuration des logs
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": "/opt/dispycluster/logs/services.log",
    "max_size_mb": 100,
    "backup_count": 5
}

# Configuration de sécurité
SECURITY_CONFIG = {
    "api_key_required": False,  # Pour une future implémentation
    "cors_origins": ["*"],  # À restreindre en production
    "rate_limiting": {
        "enabled": False,
        "requests_per_minute": 100
    }
}

# Configuration des notifications (pour une future implémentation)
NOTIFICATION_CONFIG = {
    "email": {
        "enabled": False,
        "smtp_server": "",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "from_address": "",
        "to_addresses": []
    },
    "webhook": {
        "enabled": False,
        "url": "",
        "timeout": 10
    }
}

# Configuration des métriques
METRICS_CONFIG = {
    "prometheus": {
        "enabled": True,
        "port": 9090,
        "scrape_interval": "30s"
    },
    "custom_metrics": {
        "enabled": True,
        "collection_interval": 30
    }
}

# Configuration des workflows
WORKFLOW_CONFIG = {
    "max_steps": 20,
    "step_timeout": 300,
    "parallel_execution": True,
    "error_handling": "stop_on_error"  # ou "continue_on_error"
}

# Configuration du scraping
SCRAPING_CONFIG = {
    "default_user_agent": "DispyCluster/1.0",
    "default_headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    },
    "respect_robots_txt": True,
    "delay_between_requests": 1,  # secondes
    "max_redirects": 5
}

# Configuration de l'API Gateway
GATEWAY_CONFIG = {
    "timeout": 30,
    "retry_attempts": 3,
    "circuit_breaker": {
        "enabled": True,
        "failure_threshold": 5,
        "recovery_timeout": 60
    }
}

# Fonction pour obtenir la configuration d'un service
def get_service_config(service_name: str) -> Dict:
    """Obtenir la configuration d'un service spécifique."""
    configs = {
        "cluster_controller": {
            "cluster_nodes": CLUSTER_NODES,
            "service_ports": SERVICE_PORTS,
            "limits": LIMITS,
            "worker_config": WORKER_CONFIG
        },
        "monitoring": {
            "cluster_nodes": CLUSTER_NODES,
            "monitoring_config": MONITORING_CONFIG,
            "metrics_config": METRICS_CONFIG,
            "logging_config": LOGGING_CONFIG
        },
        "scheduler": {
            "scheduler_config": SCHEDULER_CONFIG,
            "workflow_config": WORKFLOW_CONFIG,
            "limits": LIMITS
        },
        "api_gateway": {
            "service_urls": SERVICE_URLS,
            "gateway_config": GATEWAY_CONFIG,
            "security_config": SECURITY_CONFIG
        }
    }
    
    return configs.get(service_name, {})

# Fonction pour valider la configuration
def validate_config() -> List[str]:
    """Valider la configuration et retourner les erreurs."""
    errors = []
    
    # Vérifier que tous les ports sont différents
    ports = list(SERVICE_PORTS.values())
    if len(ports) != len(set(ports)):
        errors.append("Les ports des services doivent être uniques")
    
    # Vérifier que les nœuds du cluster sont définis
    if not CLUSTER_NODES:
        errors.append("Aucun nœud du cluster défini")
    
    # Vérifier les limites
    if LIMITS["max_pages_per_job"] <= 0:
        errors.append("max_pages_per_job doit être positif")
    
    if LIMITS["max_priority"] <= 0:
        errors.append("max_priority doit être positif")
    
    return errors

# Fonction pour obtenir l'URL d'un service
def get_service_url(service_name: str) -> str:
    """Obtenir l'URL d'un service."""
    return SERVICE_URLS.get(service_name, f"http://localhost:{SERVICE_PORTS.get(service_name, 8080)}")

# Fonction pour obtenir le port d'un service
def get_service_port(service_name: str) -> int:
    """Obtenir le port d'un service."""
    return SERVICE_PORTS.get(service_name, 8080)

# Configuration par environnement
def get_environment_config() -> Dict:
    """Obtenir la configuration basée sur l'environnement."""
    env = os.getenv("DISPYCLUSTER_ENV", "development")
    
    if env == "production":
        return {
            "debug": False,
            "log_level": "WARNING",
            "cors_origins": ["https://yourdomain.com"],
            "api_key_required": True
        }
    elif env == "staging":
        return {
            "debug": True,
            "log_level": "INFO",
            "cors_origins": ["*"],
            "api_key_required": False
        }
    else:  # development
        return {
            "debug": True,
            "log_level": "DEBUG",
            "cors_origins": ["*"],
            "api_key_required": False
        }

if __name__ == "__main__":
    # Valider la configuration
    errors = validate_config()
    if errors:
        print("Erreurs de configuration:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration valide")
    
    # Afficher la configuration actuelle
    print(f"\nNœuds du cluster: {CLUSTER_NODES}")
    print(f"Ports des services: {SERVICE_PORTS}")
    print(f"Limites: {LIMITS}")