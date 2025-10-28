# Script PowerShell pour gérer les fichiers de cache dispy
# Déplace les fichiers _dispy_* vers le dossier temp/

Write-Host "=== Gestion des fichiers de cache dispy ===" -ForegroundColor Green

# Créer le dossier temp s'il n'existe pas
if (-not (Test-Path "temp")) {
    New-Item -ItemType Directory -Path "temp" | Out-Null
    Write-Host "Dossier temp/ créé" -ForegroundColor Yellow
}

# Trouver les fichiers _dispy_*
$dispyFiles = Get-ChildItem -Path "_dispy_*" -ErrorAction SilentlyContinue

if ($dispyFiles.Count -eq 0) {
    Write-Host "Aucun fichier de cache dispy trouvé" -ForegroundColor Yellow
    exit 0
}

Write-Host "Fichiers de cache dispy trouvés: $($dispyFiles.Count)" -ForegroundColor Cyan

# Afficher les fichiers trouvés
Write-Host "Fichiers à déplacer:" -ForegroundColor White
$dispyFiles | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }

# Déplacer tous les fichiers _dispy_* vers temp/
Write-Host "Déplacement des fichiers vers temp/..." -ForegroundColor Yellow
$movedCount = 0

foreach ($file in $dispyFiles) {
    try {
        Move-Item -Path $file.FullName -Destination "temp/" -Force
        $movedCount++
        Write-Host "  ✓ $($file.Name) déplacé" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Erreur lors du déplacement de $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Vérifier le résultat
$movedFiles = Get-ChildItem -Path "temp/_dispy_*" -ErrorAction SilentlyContinue
Write-Host "Fichiers déplacés: $movedCount" -ForegroundColor Cyan

# Afficher la liste des fichiers dans temp/
Write-Host "Fichiers dans temp/:" -ForegroundColor White
if ($movedFiles.Count -gt 0) {
    $movedFiles | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }
} else {
    Write-Host "  Aucun fichier dans temp/" -ForegroundColor Yellow
}

Write-Host "=== Gestion terminée ===" -ForegroundColor Green