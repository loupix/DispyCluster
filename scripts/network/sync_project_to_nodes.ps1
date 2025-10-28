# Script de synchronisation du projet DispyCluster vers tous les nœuds
# Copie le projet vers /home/dispy/DispyCluster sur chaque nœud

param(
    [switch]$Force = $false
)

Write-Host "=== Synchronisation du projet DispyCluster ===" -ForegroundColor Green
Write-Host "Copie vers /home/dispy/DispyCluster sur tous les nœuds" -ForegroundColor Green
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
$Nodes = @()

foreach ($line in $NodesContent) {
    if ($line -match "^\s*-\s+(.+)$") {
        $node = $matches[1].Trim()
        $Nodes += $node
    }
}

if ($Nodes.Count -eq 0) {
    Write-Host "✗ Aucun nœud trouvé dans la configuration" -ForegroundColor Red
    exit 1
}

Write-Host "Nœuds détectés:" -ForegroundColor Yellow
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

# Fonction pour synchroniser un nœud
function Sync-Node {
    param([string]$Node)
    
    # Déterminer l'utilisateur selon le nœud
    $username = if ($Node -match "node(9|10)\.lan") { "pi" } else { "dispy" }
    
    Write-Host "Synchronisation de $Node (utilisateur: $username)..." -ForegroundColor Cyan
    
    # Tester la connectivité
    if (-not (Test-NodeConnectivity $Node)) {
        Write-Host "  ✗ Impossible de joindre $Node" -ForegroundColor Red
        return $false
    }
    
    try {
        # Créer le répertoire de destination
        Write-Host "  Création du répertoire de destination..." -ForegroundColor Gray
        $createDirCmd = "sudo mkdir -p /home/dispy/DispyCluster && sudo chown dispy:dispy /home/dispy/DispyCluster"
        ssh "$username@$Node" $createDirCmd
        
        # Synchroniser les fichiers avec rsync (si disponible) ou scp
        Write-Host "  Synchronisation des fichiers..." -ForegroundColor Gray
        
        # Créer un répertoire temporaire sur le nœud
        $tempDir = "/tmp/DispyCluster"
        ssh "$username@$Node" "sudo rm -rf $tempDir && sudo mkdir -p $tempDir"
        
        # Copier les fichiers principaux
        $excludePatterns = @(
            "*.pyc",
            "__pycache__",
            ".git",
            "_dispy_*",
            "*.log",
            "temp_*"
        )
        
        # Utiliser scp pour copier les fichiers essentiels
        $essentialFiles = @(
            "core",
            "config", 
            "services",
            "workers",
            "examples",
            "scripts",
            "requirements*.txt",
            "environment.yml",
            "README.md"
        )
        
        foreach ($pattern in $essentialFiles) {
            $sourcePath = Join-Path $ProjectRoot $pattern
            if (Test-Path $sourcePath) {
                if ((Get-Item $sourcePath) -is [System.IO.DirectoryInfo]) {
                    # C'est un répertoire
                    scp -r "$sourcePath" "$username@$Node`:$tempDir/"
                } else {
                    # C'est un fichier
                    scp "$sourcePath" "$username@$Node`:$tempDir/"
                }
            }
        }
        
        # Copier vers le répertoire final
        Write-Host "  Installation finale..." -ForegroundColor Gray
        $finalInstallCmd = "sudo cp -r $tempDir/* /home/dispy/DispyCluster/ && sudo chown -R dispy:dispy /home/dispy/DispyCluster && sudo rm -rf $tempDir"
        ssh "$username@$Node" $finalInstallCmd
        
        Write-Host "  ✓ Synchronisation terminée pour $Node" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "  ✗ Erreur lors de la synchronisation de $Node : $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Synchroniser tous les nœuds
Write-Host "Début de la synchronisation..." -ForegroundColor Green
Write-Host ""

$SuccessCount = 0
$TotalCount = $Nodes.Count

foreach ($node in $Nodes) {
    Write-Host "--- Nœud $node ---" -ForegroundColor Yellow
    
    if (Sync-Node $node) {
        $SuccessCount++
    } else {
        Write-Host "  ✗ Échec de la synchronisation pour $node" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Résumé
Write-Host "=== Résumé de la synchronisation ===" -ForegroundColor Green
Write-Host "Nœuds synchronisés avec succès: $SuccessCount/$TotalCount" -ForegroundColor Yellow

if ($SuccessCount -eq $TotalCount) {
    Write-Host "✓ Tous les nœuds ont été synchronisés avec succès !" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠ Certains nœuds n'ont pas pu être synchronisés" -ForegroundColor Yellow
    exit 1
}