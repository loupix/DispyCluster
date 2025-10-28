#!/bin/bash

# Script d'installation des requirements optimisé pour Raspberry Pi 3B+
# Résout les problèmes de dépendances avec pip

set -e

echo "=== Installation des requirements pour DispyCluster ==="
echo "Optimisé pour Raspberry Pi 3B+ avec Python 3.9"
echo ""

# Vérifier Python
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Version Python: $PYTHON_VERSION"

# Mettre à jour pip et setuptools
echo "Mise à jour de pip et setuptools..."
python3 -m pip install --upgrade pip setuptools wheel

# Installer les dépendances de base d'abord
echo "Installation des dépendances de base..."
python3 -m pip install --no-cache-dir \
    setuptools \
    wheel \
    cython \
    numpy

# Installer les dépendances une par une pour éviter les conflits
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

# Tester les imports principaux
python3 -c "
import fastapi
import dispy
import uvicorn
import aiohttp
import httpx
import apscheduler
import requests
import pydantic
import prometheus_client
import psutil
import beautifulsoup4
import lxml
import selenium
import yaml
import click
import colorama
import dotenv
import paramiko
import cryptography
import pytest
print('✓ Toutes les dépendances sont installées avec succès!')
"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Pour vérifier l'installation:"
echo "  python3 -c 'import fastapi, dispy, uvicorn; print(\"Installation réussie!\")'"
echo ""
echo "Pour lancer les tests:"
echo "  python3 -m pytest tests/"
echo ""
echo "Pour lancer les services:"
echo "  python3 services/cluster_controller.py"
echo "  python3 services/monitoring_service.py"
echo "  python3 services/scheduler_service.py"
echo "  python3 services/api_gateway.py"