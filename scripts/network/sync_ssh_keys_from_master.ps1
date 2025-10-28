# Script de synchronisation des clés SSH depuis le nœud maître
# Copie les clés SSH de node13 vers tous les autres nœuds

param(
    [switch]$Force = $false
)

Write-Host "=== Synchronisation des clés SSH depuis le nœud maître ===" -ForegroundColor Green
Write-Host "Copie des clés SSH de node13 vers tous les autres nœuds" -ForegroundColor Green
Write-Host ""

# Obtenir le répertoire du script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$NodesConfig = Join-Path $ProjectRoot "inventory\nodes.yaml"

if (-not (Test-Path $NodesConfig)) {
    Write-Host "✗ Fichier de configuration des nœuds non trouvé: $NodesConfig" -ForegroundColor Red
    exit 1
}

# Charger la configuration des nœuds
$NodesContent = Get-Content $NodesConfig
$AllNodes = @()

foreach ($line in $NodesContent) {
    if ($line -match "^\s*-\s+(.+)$") {
        $node = $matches[1].Trim()
        $AllNodes += $node
    }
}

if ($AllNodes.Count -eq 0) {
    Write-Host "✗ Aucun nœud trouvé dans la configuration" -ForegroundColor Red
    exit 1
}

# Identifier le nœud maître
$MasterNode = "node13.lan"

# Filtrer les nœuds workers (exclure le maître)
$Nodes = @()
foreach ($node in $AllNodes) {
    if ($node -ne $MasterNode) {
        $Nodes += $node
    }
}
Write-Host "Nœud maître: $MasterNode" -ForegroundColor Yellow
Write-Host "Nœuds workers:" -ForegroundColor Yellow
foreach ($node in $Nodes) {
    Write-Host "  - $node" -ForegroundColor Yellow
}
Write-Host ""

# Fonction pour tester la connectivité
function Test-NodeConnectivity {
    param([string]$Node)
    
    try {
        $result = Test-Connection -ComputerName $Node -Count 1 -Quiet
        return $result
    }
    catch {
        return $false
    }
}

# Fonction pour synchroniser les clés SSH d'un nœud
function Sync-SSHKeys {
    param([string]$TargetNode)
    
    # Déterminer l'utilisateur selon le nœud
    $username = if ($TargetNode -match "node(9|10)\.lan") { "pi" } else { "dispy" }
    
    Write-Host "Synchronisation des clés SSH vers $TargetNode (utilisateur: $username)..." -ForegroundColor Cyan
    
    # Tester la connectivité
    if (-not (Test-NodeConnectivity $TargetNode)) {
        Write-Host "  ✗ Impossible de joindre $TargetNode" -ForegroundColor Red
        return $false
    }
    
    try {
        # Créer le répertoire .ssh sur le nœud cible
        Write-Host "  Création du répertoire .ssh..." -ForegroundColor Gray
        $createDirCmd = "sudo mkdir -p /home/dispy/.ssh && sudo chown dispy:dispy /home/dispy/.ssh && sudo chmod 700 /home/dispy/.ssh"
        ssh "$username@$TargetNode" $createDirCmd
        
        # Copier la clé publique du maître vers le nœud cible
        Write-Host "  Copie de la clé publique..." -ForegroundColor Gray
        $pubKey = ssh "dispy@$MasterNode" "cat ~/.ssh/id_rsa.pub"
        ssh "$username@$TargetNode" "echo '$pubKey' | sudo tee /home/dispy/.ssh/authorized_keys && sudo chmod 600 /home/dispy/.ssh/authorized_keys && sudo chown dispy:dispy /home/dispy/.ssh/authorized_keys"
        
        # Copier la clé privée du maître vers le nœud cible (pour la cohérence)
        Write-Host "  Copie de la clé privée..." -ForegroundColor Gray
        $privKey = ssh "dispy@$MasterNode" "cat ~/.ssh/id_rsa"
        ssh "$username@$TargetNode" "echo '$privKey' | sudo tee /home/dispy/.ssh/id_rsa && sudo chmod 600 /home/dispy/.ssh/id_rsa && sudo chown dispy:dispy /home/dispy/.ssh/id_rsa"
        
        # Copier la clé publique du maître vers le nœud cible
        Write-Host "  Copie de la clé publique..." -ForegroundColor Gray
        ssh "$username@$TargetNode" "echo '$pubKey' | sudo tee /home/dispy/.ssh/id_rsa.pub && sudo chmod 644 /home/dispy/.ssh/id_rsa.pub && sudo chown dispy:dispy /home/dispy/.ssh/id_rsa.pub"
        
        Write-Host "  ✓ Clés SSH synchronisées pour $TargetNode" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "  ✗ Erreur lors de la synchronisation de $TargetNode : $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Vérifier que le nœud maître est accessible
Write-Host "Vérification de l'accès au nœud maître..." -ForegroundColor Yellow
if (-not (Test-NodeConnectivity $MasterNode)) {
    Write-Host "✗ Impossible de joindre le nœud maître $MasterNode" -ForegroundColor Red
    exit 1
}

# Vérifier que les clés SSH existent sur le maître
Write-Host "Vérification des clés SSH sur le maître..." -ForegroundColor Yellow
$checkKeysCmd = "test -f ~/.ssh/id_rsa && test -f ~/.ssh/id_rsa.pub"
try {
    ssh "dispy@$MasterNode" $checkKeysCmd
    Write-Host "✓ Clés SSH trouvées sur le nœud maître" -ForegroundColor Green
}
catch {
    Write-Host "✗ Clés SSH manquantes sur le nœud maître $MasterNode" -ForegroundColor Red
    Write-Host "  Veuillez générer les clés SSH sur le maître avec:" -ForegroundColor Yellow
    Write-Host "  ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Synchroniser tous les nœuds workers
Write-Host "Début de la synchronisation des clés SSH..." -ForegroundColor Green
Write-Host ""

$SuccessCount = 0
$TotalCount = 0

foreach ($node in $Nodes) {
    if ($node -ne $MasterNode) {
        $TotalCount++
        Write-Host "--- Nœud $node ---" -ForegroundColor Yellow
        
        if (Sync-SSHKeys $node) {
            $SuccessCount++
        } else {
            Write-Host "  ✗ Échec de la synchronisation pour $node" -ForegroundColor Red
        }
        
        Write-Host ""
    }
}

# Test final de connectivité
Write-Host "=== Test de connectivité final ===" -ForegroundColor Green
Write-Host "Test de l'accès SSH sans mot de passe depuis le maître vers tous les nœuds..." -ForegroundColor Yellow
Write-Host ""

foreach ($node in $Nodes) {
    if ($node -ne $MasterNode) {
        Write-Host -NoNewline "Test $node... "
        try {
            ssh "dispy@$MasterNode" "ssh dispy@$node 'hostname' >/dev/null 2>&1"
            Write-Host "✓ OK" -ForegroundColor Green
        }
        catch {
            Write-Host "✗ Échec" -ForegroundColor Red
        }
    }
}

# Résumé
Write-Host ""
Write-Host "=== Résumé de la synchronisation ===" -ForegroundColor Green
Write-Host "Nœuds synchronisés avec succès: $SuccessCount/$TotalCount" -ForegroundColor Yellow

if ($SuccessCount -eq $TotalCount) {
    Write-Host "✓ Toutes les clés SSH ont été synchronisées avec succès !" -ForegroundColor Green
    Write-Host "✓ Le nœud maître peut maintenant se connecter sans mot de passe à tous les nœuds" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠ Certains nœuds n'ont pas pu être synchronisés" -ForegroundColor Yellow
    exit 1
}