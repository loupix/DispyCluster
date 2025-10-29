#!/usr/bin/env python3
"""Script de démarrage pour l'interface web DispyCluster."""

import os
import sys
import uvicorn
from pathlib import Path

# Ajouter le répertoire web au path
web_dir = Path(__file__).parent
sys.path.insert(0, str(web_dir))

# Importer l'application
from app import create_socketio_app

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8085"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"🚀 Démarrage de DispyCluster Web Interface")
    print(f"📍 URL: http://{host}:{port}")
    print(f"🔧 Mode debug: {debug}")
    
    # Démarrer le serveur avec l'app Socket.IO (factory)
    uvicorn.run(
        "app:create_socketio_app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
        factory=True
    )