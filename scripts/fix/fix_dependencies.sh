#!/bin/bash

# Script de réparation des dépendances pour Raspberry Pi
# Résout les problèmes de markupsafe et autres conflits

set -e

echo "=== Réparation des dépendances DispyCluster ==="
echo "Résolution des problèmes de markupsafe et conflits"
echo ""

# Vérifier l'environnement Python
echo "Vérification de l'environnement Python..."
python3 --version
pip3 --version

# Nettoyer l'environnement pip
echo "Nettoyage de l'environnement pip..."
pip3 cache purge
rm -rf ~/.cache/pip

# Mettre à jour pip et outils de base
echo "Mise à jour des outils de base..."
python3 -m pip install --upgrade --no-cache-dir pip setuptools wheel

# Installer les dépendances de base d'abord
echo "Installation des dépendances de base..."
python3 -m pip install --no-cache-dir \
    setuptools>=65.0.0 \
    wheel>=0.38.0 \
    cython>=0.29.0 \
    numpy>=1.21.0

# Résoudre le problème markupsafe spécifiquement
echo "Résolution du problème markupsafe..."
python3 -m pip install --no-cache-dir --force-reinstall markupsafe==2.0.1
python3 -m pip install --no-cache-dir --force-reinstall jinja2==3.1.2

# Installer les dépendances une par une
echo "Installation des dépendances principales..."

# Core web framework
python3 -m pip install --no-cache-dir fastapi==0.100.1
python3 -m pip install --no-cache-dir uvicorn==0.23.2
python3 -m pip install --no-cache-dir aiohttp==3.8.5
python3 -m pip install --no-cache-dir httpx==0.24.1
python3 -m pip install --no-cache-dir apscheduler==3.9.1
python3 -m pip install --no-cache-dir requests==2.31.0
python3 -m pip install --no-cache-dir pydantic==1.10.12

# Dispy
echo "Installation de Dispy..."
python3 -m pip install --no-cache-dir dispy==4.15.0

# Monitoring
python3 -m pip install --no-cache-dir prometheus-client==0.17.1
python3 -m pip install --no-cache-dir psutil==5.9.5

# Web scraping
python3 -m pip install --no-cache-dir beautifulsoup4==4.12.2
python3 -m pip install --no-cache-dir lxml==4.9.3
python3 -m pip install --no-cache-dir selenium==4.10.0

# Utilitaires
python3 -m pip install --no-cache-dir pyyaml==6.0.1
python3 -m pip install --no-cache-dir click==8.1.7
python3 -m pip install --no-cache-dir colorama==0.4.6
python3 -m pip install --no-cache-dir python-dotenv==1.0.0

# SSH et sécurité
python3 -m pip install --no-cache-dir paramiko==3.2.0
python3 -m pip install --no-cache-dir cryptography==3.4.8

# Tests
python3 -m pip install --no-cache-dir pytest==7.4.2
python3 -m pip install --no-cache-dir pytest-asyncio==0.21.1

echo ""
echo "=== Vérification de l'installation ==="

# Test des imports critiques
echo "Test des imports critiques..."
python3 -c "
try:
    import fastapi
    print('✓ FastAPI importé')
except ImportError as e:
    print('✗ Erreur FastAPI:', e)

try:
    import dispy
    print('✓ Dispy importé')
except ImportError as e:
    print('✗ Erreur Dispy:', e)

try:
    import uvicorn
    print('✓ Uvicorn importé')
except ImportError as e:
    print('✗ Erreur Uvicorn:', e)

try:
    import aiohttp
    print('✓ Aiohttp importé')
except ImportError as e:
    print('✗ Erreur Aiohttp:', e)

try:
    import markupsafe
    print('✓ MarkupSafe importé (version:', markupsafe.__version__, ')')
except ImportError as e:
    print('✗ Erreur MarkupSafe:', e)

try:
    import jinja2
    print('✓ Jinja2 importé (version:', jinja2.__version__, ')')
except ImportError as e:
    print('✗ Erreur Jinja2:', e)
"

echo ""
echo "=== Test de fonctionnement des services ==="

# Test des services
echo "Test des services DispyCluster..."
python3 -c "
try:
    from services.cluster_controller import app as controller_app
    print('✓ Cluster Controller importé')
except Exception as e:
    print('✗ Erreur Cluster Controller:', e)

try:
    from services.monitoring_service import app as monitoring_app
    print('✓ Monitoring Service importé')
except Exception as e:
    print('✗ Erreur Monitoring Service:', e)

try:
    from services.scheduler_service import app as scheduler_app
    print('✓ Scheduler Service importé')
except Exception as e:
    print('✗ Erreur Scheduler Service:', e)

try:
    from services.api_gateway import app as gateway_app
    print('✓ API Gateway importé')
except Exception as e:
    print('✗ Erreur API Gateway:', e)
"

echo ""
echo "=== Réparation terminée ==="
echo ""
echo "Si des erreurs persistent, essayez:"
echo "  1. python3 -m pip install --upgrade pip"
echo "  2. python3 -m pip install --force-reinstall markupsafe==2.0.1"
echo "  3. python3 -m pip install --force-reinstall jinja2==3.1.2"
echo ""
echo "Pour lancer les services:"
echo "  python3 services/cluster_controller.py"
echo "  python3 services/monitoring_service.py"
echo "  python3 services/scheduler_service.py"
echo "  python3 services/api_gateway.py"