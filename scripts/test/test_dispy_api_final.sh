#!/bin/bash

# Script de test de l'API Dispy - Version finale
# Vérifie la bonne utilisation de l'API Dispy 4.15.0

set -e

echo "=== Test de l'API Dispy 4.15.0 ==="
echo "Vérification de la configuration et de l'API"
echo ""

# Obtenir l'IP locale
get_local_ip() {
    local ip=""
    
    if command -v ip >/dev/null 2>&1; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    fi
    
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' 2>/dev/null || echo "")
    fi
    
    echo "$ip"
}

LOCAL_IP=$(get_local_ip)
echo "IP locale: $LOCAL_IP"

# Test de l'API Dispy
echo ""
echo "=== Test de l'API Dispy ==="

python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

print('Version Dispy:', dispy.__version__)
print()

print('Classes disponibles dans dispy:')
for attr in sorted(dir(dispy)):
    if not attr.startswith('_') and not callable(getattr(dispy, attr)):
        try:
            value = getattr(dispy, attr)
            print(f'  {attr}: {value}')
        except:
            pass
print()

print('Classes de scheduler disponibles:')
scheduler_classes = []
for attr in dir(dispy):
    if not attr.startswith('_') and 'scheduler' in attr.lower():
        try:
            cls = getattr(dispy, attr)
            if callable(cls):
                scheduler_classes.append(attr)
                print(f'  {attr}: {cls}')
        except:
            pass

if not scheduler_classes:
    print('  Aucune classe de scheduler trouvée')
    print('  Classes disponibles:')
    for attr in sorted(dir(dispy)):
        if not attr.startswith('_') and callable(getattr(dispy, attr)):
            print(f'    {attr}')
print()

print('Test de création d\\'un scheduler...')
try:
    # Essayer différentes API possibles
    scheduler = None
    
    # Essayer JobScheduler
    try:
        scheduler = dispy.JobScheduler()
        print('✓ JobScheduler() créé avec succès')
    except AttributeError as e:
        print(f'✗ JobScheduler non disponible: {e}')
        
        # Essayer Scheduler
        try:
            scheduler = dispy.Scheduler()
            print('✓ Scheduler() créé avec succès')
        except AttributeError as e:
            print(f'✗ Scheduler non disponible: {e}')
            
            # Essayer d'autres classes
            for cls_name in ['DispyScheduler', 'Master', 'Server']:
                try:
                    cls = getattr(dispy, cls_name)
                    scheduler = cls()
                    print(f'✓ {cls_name}() créé avec succès')
                    break
                except (AttributeError, TypeError) as e:
                    print(f'✗ {cls_name} non disponible: {e}')
    
    if scheduler:
        print(f'  Type: {type(scheduler).__name__}')
        
        # Essayer de démarrer
        try:
            scheduler.start()
            print('✓ Scheduler démarré avec succès')
            
            # Arrêter le scheduler
            scheduler.close()
            print('✓ Scheduler arrêté proprement')
        except Exception as e:
            print(f'✗ Erreur lors du démarrage: {e}')
    else:
        print('✗ Aucune classe de scheduler utilisable trouvée')
    
except Exception as e:
    print(f'✗ Erreur lors de la création du scheduler: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== Test terminé ==="