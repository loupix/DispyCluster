"""Exemple d'utilisation du scraper amélioré avec BeautifulSoup et NLP.

Ce script démontre les capacités avancées d'extraction d'informations
personnelles et professionnelles du scraper cluster.
"""

import json
from typing import Any, Dict
from workers.enhanced_scraper_worker import scrape_site_enhanced


def print_section(title: str, data: Any, max_items: int = 5) -> None:
    """Affiche une section de résultats de manière lisible."""
    print(f"\n=== {title.upper()} ===")
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                print(f"{key}: {', '.join(str(v) for v in value[:max_items])}")
                if len(value) > max_items:
                    print(f"  ... et {len(value) - max_items} autres")
            elif isinstance(value, dict) and value:
                print(f"{key}: {json.dumps(value, indent=2, ensure_ascii=False)[:200]}...")
            elif value:
                print(f"{key}: {value}")
    elif isinstance(data, list) and len(data) > 0:
        for item in data[:max_items]:
            print(f"- {item}")
        if len(data) > max_items:
            print(f"  ... et {len(data) - max_items} autres")
    else:
        print("Aucune donnée trouvée")


def main() -> None:
    """Exemple d'utilisation du scraper amélioré."""
    
    # URL à scraper (remplace par une vraie URL)
    url = "https://example.com"  # Change ça par un vrai site
    max_pages = 3  # Limite pour l'exemple
    
    print(f"🔍 Scraping avancé de {url}")
    print(f"📄 Maximum {max_pages} pages")
    print("⏳ Extraction en cours...")
    
    try:
        # Lancer le scraping amélioré
        result = scrape_site_enhanced(
            start_url=url,
            max_pages=max_pages,
            same_origin_only=True,
            timeout_s=15
        )
        
        print(f"\n✅ Scraping terminé ! {len(result['crawled'])} pages analysées")
        
        # Afficher les pages visitées
        print_section("Pages visitées", result["crawled"])
        
        # Analyser les résultats par page
        for url_visited in result["crawled"]:
            print(f"\n{'='*60}")
            print(f"📄 ANALYSE DE: {url_visited}")
            print('='*60)
            
            # Informations de contact
            contact_info = result["contact_info"].get(url_visited, {})
            if any(contact_info.values()):
                print_section("Informations de contact", contact_info)
            
            # Entités nommées (NLP)
            entities = result["entities"].get(url_visited, {})
            if any(entities.values()):
                print_section("Entités détectées (NLP)", entities)
            
            # Informations professionnelles
            prof_info = result["professional_info"].get(url_visited, {})
            if any(prof_info.values()):
                print_section("Informations professionnelles", prof_info)
            
            # Données structurées
            structured = result["structured_data"].get(url_visited, {})
            if any(structured.values()):
                print_section("Données structurées", structured)
        
        # Résumé global
        print(f"\n{'='*60}")
        print("📊 RÉSUMÉ GLOBAL")
        print('='*60)
        
        all_emails = set()
        all_phones = set()
        all_persons = set()
        all_orgs = set()
        
        for url_data in result["contact_info"].values():
            all_emails.update(url_data.get("emails", []))
            all_phones.update(url_data.get("phones", []))
        
        for url_data in result["entities"].values():
            all_persons.update(url_data.get("persons", []))
            all_orgs.update(url_data.get("organizations", []))
        
        print(f"📧 Emails trouvés: {len(all_emails)}")
        if all_emails:
            print(f"   {', '.join(list(all_emails)[:5])}")
        
        print(f"📞 Téléphones trouvés: {len(all_phones)}")
        if all_phones:
            print(f"   {', '.join(list(all_phones)[:3])}")
        
        print(f"👥 Personnes identifiées: {len(all_persons)}")
        if all_persons:
            print(f"   {', '.join(list(all_persons)[:5])}")
        
        print(f"🏢 Organisations identifiées: {len(all_orgs)}")
        if all_orgs:
            print(f"   {', '.join(list(all_orgs)[:5])}")
        
        # Erreurs
        if result["errors"]:
            print(f"\n❌ Erreurs rencontrées: {len(result['errors'])}")
            for url_error, error_msg in list(result["errors"].items())[:3]:
                print(f"   {url_error}: {error_msg}")
        
        # Sauvegarder les résultats
        output_file = "scraping_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultats sauvegardés dans {output_file}")
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping: {e}")
        print("💡 Vérifie que l'URL est accessible et que les dépendances sont installées")


if __name__ == "__main__":
    main()