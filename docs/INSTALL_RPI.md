# Installation pour Raspberry Pi 3B+

Guide d'installation pour Raspberry Pi avec problèmes de SSL/certificats conda.

## Problème rencontré

Erreur SSL avec conda version ancienne (Python 3.4):
```
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

## Solutions

### Solution 1: Utiliser venv (Recommandé)

Le plus simple et fonctionne à tous les coups:

```bash
# Cloner ou récupérer le projet
cd ~/Documents/DispyCluster

# Exécuter le script d'installation avec venv
./install_venv_rpi.sh

# Activer l'environnement
source venv/bin/activate
```

### Solution 2: Mettre à jour conda d'abord

```bash
# Mettre à jour conda (peut prendre du temps)
conda update -n base conda

# Désactiver temporairement SSL
conda config --set ssl_verify false

# Créer l'environnement
conda create -n dispycluster python=3.9 -y

# Activer l'environnement
conda activate dispycluster

# Réactiver SSL
conda config --set ssl_verify true
```

### Solution 3: Script automatique

```bash
# Le script essaie conda puis venv en fallback
./install_rpi_environment.sh
```

## Démarrer les services

Après l'installation:

```bash
# Démarrer tous les services (Celery + API)
./start_all.sh
```

Le script détecte automatiquement conda ou venv.

## Vérification

```bash
# Vérifier que l'environnement est activé
conda info --envs  # ou: which python

# Tester les imports
python -c "import celery, redis, fastapi"
```

## Dépannage

### Si venv ne se crée pas

```bash
# Installer venv si manquant
sudo apt-get update
sudo apt-get install python3-venv
```

### Si pip est trop ancien

```bash
# Mettre à jour pip
pip install --upgrade pip setuptools wheel
```

### Si des packages échouent à compiler

```bash
# Installer les outils de compilation
sudo apt-get install build-essential python3-dev

# Relancer l'installation
pip install -r web/requirements.txt
```

## Versions compatibles RPi

Les versions dans `install_venv_rpi.sh` sont optimisées pour ARM (Raspberry Pi):
- fastapi==0.100.1 (version plus légère)
- uvicorn==0.23.2 (évite les dépendances lourdes)
- celery==5.3.4 (stable pour RPi)
- redis==5.0.1

## Fichiers créés

- `install_venv_rpi.sh` - Installation avec venv uniquement
- `install_rpi_environment.sh` - Installation avec fallback conda/venv
- `start_all.sh` - Démarrage des services (mis à jour)

## Commandes utiles

```bash
# Voir les logs Celery
tail -f logs/celery_worker.log
tail -f logs/celery_beat.log

# Arrêter tous les services
pkill -f celery
pkill -f uvicorn

# Nettoyer l'environnement
rm -rf venv/
./install_venv_rpi.sh
```



