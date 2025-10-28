"""Configuration centralisée du logging pour DispyCluster."""

import os
import logging
import logging.handlers
from pathlib import Path

def setup_logging():
    """Configure le logging global pour l'application."""
    
    # Charger la configuration depuis les variables d'environnement
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_file = os.getenv("LOG_FILE", "logs/dispycluster.log")
    
    # Créer le dossier de logs s'il n'existe pas
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configuration du logging
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            # Handler pour fichier avec rotation
            logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            # Handler pour console
            logging.StreamHandler()
        ]
    )
    
    # Configuration spécifique pour les modules
    loggers_config = {
        'web.core.cluster_manager': 'DEBUG',
        'web.tasks.monitoring': 'DEBUG', 
        'web.views.cluster_view': 'INFO',
        'web.api.cluster': 'INFO',
        'web.api.monitoring': 'INFO',
        'celery': 'WARNING',  # Réduire le bruit de Celery
        'redis': 'WARNING'     # Réduire le bruit de Redis
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level, logging.INFO))

def get_logger(name: str) -> logging.Logger:
    """Retourne un logger configuré pour le module donné."""
    return logging.getLogger(name)
