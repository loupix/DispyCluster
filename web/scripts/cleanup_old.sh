#!/bin/bash
# Script de nettoyage et réorganisation des anciens dossiers

echo "🧹 Nettoyage et réorganisation des anciens dossiers..."

# Créer le dossier legacy pour les anciens services
mkdir -p ../legacy/services
mkdir -p ../legacy/monitoring

# Déplacer les anciens services vers legacy
if [ -d "../services" ]; then
    echo "📦 Déplacement des anciens services vers legacy/"
    mv ../services/* ../legacy/services/ 2>/dev/null || true
    rmdir ../services 2>/dev/null || true
fi

# Déplacer l'ancien monitoring vers legacy
if [ -d "../monitoring" ]; then
    echo "📊 Déplacement de l'ancien monitoring vers legacy/"
    mv ../monitoring/* ../legacy/monitoring/ 2>/dev/null || true
    rmdir ../monitoring 2>/dev/null || true
fi

# Créer un fichier README pour expliquer la réorganisation
cat > ../legacy/README.md << 'EOF'
# Legacy Services

Ce dossier contient les anciens services qui ont été intégrés dans l'interface web unifiée.

## Structure

- `services/` - Anciens services individuels
- `monitoring/` - Ancien système de monitoring

## Migration

Ces services ont été remplacés par l'interface web unifiée dans le dossier `web/` qui offre :

- Interface web moderne
- API RESTful unifiée
- Base de données centralisée
- Monitoring en temps réel
- Gestion des jobs intégrée

## Utilisation

Pour utiliser les nouveaux services, démarrez l'interface web :

```bash
cd web
./scripts/start_web.sh
```

L'interface sera accessible sur http://localhost:8085
EOF

echo "✅ Nettoyage terminé"
echo "📁 Anciens services déplacés vers legacy/"
echo "🌐 Nouvelle interface web disponible dans web/"