# Configuration Dispy pour DispyCluster
# Résout les erreurs "Bad source address" et problèmes de communication

import socket
import dispy

def get_local_ip():
    """Obtenir l'IP locale de manière fiable."""
    try:
        # Méthode 1: Connexion à une adresse externe
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except:
        try:
            # Méthode 2: hostname
            import subprocess
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()[0]
        except:
            pass
    
    # Méthode 3: socket.gethostbyname
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "127.0.0.1"

# Configuration réseau
LOCAL_IP = get_local_ip()

# Configuration Dispy
dispy.config.SchedulerIPAddr = LOCAL_IP
dispy.config.SchedulerPort = "51347"  # Chaîne de caractères
dispy.config.NodeIPAddr = LOCAL_IP
dispy.config.NodePort = "51348"  # Chaîne de caractères

# Timeouts
dispy.config.ClientTimeout = "60"  # Chaîne de caractères
dispy.config.NodeTimeout = "30"  # Chaîne de caractères

# Ressources
dispy.config.NodeAvailMem = "100"  # MB, chaîne de caractères
dispy.config.NodeAvailCores = "1"  # Chaîne de caractères

# Configuration de sécurité
dispy.config.NodeSecret = None  # Pas de secret pour simplifier

print(f"Configuration Dispy:")
print(f"  IP locale: {LOCAL_IP}")
print(f"  Scheduler: {dispy.config.SchedulerIPAddr}:{dispy.config.SchedulerPort}")
print(f"  Node: {dispy.config.NodeIPAddr}:{dispy.config.NodePort}")
print(f"  Timeout client: {dispy.config.ClientTimeout}s")
print(f"  Timeout nœud: {dispy.config.NodeTimeout}s")