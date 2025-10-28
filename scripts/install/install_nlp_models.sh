#!/bin/bash

# Script d'installation des modèles NLP pour le scraper amélioré
# À exécuter après l'installation des dépendances Python

echo "🧠 Installation des modèles NLP pour le scraper amélioré..."

# Vérifier si conda est disponible
if command -v conda &> /dev/null; then
    echo "📦 Environnement conda détecté"
    
    # Activer l'environnement dispycluster
    echo "🔄 Activation de l'environnement dispycluster..."
    conda activate dispycluster
    
    # Installer les modèles spaCy
    echo "📥 Installation du modèle français de spaCy..."
    python -m spacy download fr_core_news_sm
    
    echo "📥 Installation du modèle anglais de spaCy (fallback)..."
    python -m spacy download en_core_web_sm
    
    # Télécharger les données NLTK
    echo "📥 Téléchargement des données NLTK..."
    python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
    
else
    echo "⚠️  Conda non détecté, installation avec pip..."
    
    # Installer les modèles spaCy
    echo "📥 Installation du modèle français de spaCy..."
    python -m spacy download fr_core_news_sm
    
    echo "📥 Installation du modèle anglais de spaCy (fallback)..."
    python -m spacy download en_core_web_sm
    
    # Télécharger les données NLTK
    echo "📥 Téléchargement des données NLTK..."
    python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
fi

echo "✅ Installation des modèles NLP terminée !"
echo ""
echo "🚀 Le scraper amélioré est maintenant prêt à extraire :"
echo "   - Emails et téléphones"
echo "   - Adresses et codes postaux"
echo "   - Liens réseaux sociaux"
echo "   - Entités nommées (personnes, organisations, lieux)"
echo "   - Informations professionnelles"
echo "   - Données structurées (JSON-LD, microdata, Open Graph)"
echo ""
echo "💡 Pour tester : python examples/enhanced_scrape_example.py"