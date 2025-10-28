"""Worker de scraping avancé avec BeautifulSoup et NLP.

Objectif:
- Extraire un maximum d'informations personnelles et professionnelles
- Utiliser BeautifulSoup pour parser intelligemment le HTML
- Intégrer spaCy pour l'extraction d'entités nommées
- Extraire les données structurées (JSON-LD, microdata, Open Graph)
"""

from typing import Dict, List, Optional, Set, Any
import re
import time
import json
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment
import requests

try:
    import spacy
    from spacy import displacy
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

# Regex avancées pour différents types de données
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+33|0)[1-9](\d{8}|\d{2}\s\d{2}\s\d{2}\s\d{2})")
SOCIAL_REGEX = re.compile(r"(linkedin\.com|twitter\.com|facebook\.com|instagram\.com|github\.com)")
ADDRESS_REGEX = re.compile(r"\d+\s+[A-Za-z\s]+(?:rue|avenue|boulevard|place|chemin|route|impasse)", re.IGNORECASE)
POSTAL_CODE_REGEX = re.compile(r"\b\d{5}\b")
DATE_REGEX = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")

class EnhancedScraper:
    def __init__(self):
        self.nlp = None
        if NLP_AVAILABLE:
            try:
                # Charger le modèle français de spaCy
                self.nlp = spacy.load("fr_core_news_sm")
            except OSError:
                # Fallback sur le modèle anglais si le français n'est pas disponible
                self.nlp = spacy.load("en_core_web_sm")
    
    def extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrait les données structurées (JSON-LD, microdata, Open Graph)."""
        structured_data = {
            "json_ld": [],
            "microdata": [],
            "open_graph": {},
            "twitter_cards": {}
        }
        
        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                structured_data["json_ld"].append(data)
            except:
                pass
        
        # Microdata
        for item in soup.find_all(attrs={"itemscope": True}):
            microdata_item = {}
            item_type = item.get("itemtype", "")
            microdata_item["type"] = item_type
            
            for prop in item.find_all(attrs={"itemprop": True}):
                prop_name = prop.get("itemprop")
                prop_value = prop.get_text(strip=True)
                microdata_item[prop_name] = prop_value
            
            structured_data["microdata"].append(microdata_item)
        
        # Open Graph
        for meta in soup.find_all("meta", property=re.compile(r"^og:")):
            prop = meta.get("property", "").replace("og:", "")
            content = meta.get("content", "")
            structured_data["open_graph"][prop] = content
        
        # Twitter Cards
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = meta.get("name", "").replace("twitter:", "")
            content = meta.get("content", "")
            structured_data["twitter_cards"][name] = content
        
        return structured_data
    
    def extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """Extrait les informations de contact avancées."""
        contact_info = {
            "emails": list(set(EMAIL_REGEX.findall(text))),
            "phones": list(set(PHONE_REGEX.findall(text))),
            "addresses": list(set(ADDRESS_REGEX.findall(text))),
            "postal_codes": list(set(POSTAL_CODE_REGEX.findall(text))),
            "social_links": list(set(SOCIAL_REGEX.findall(text))),
            "dates": list(set(DATE_REGEX.findall(text)))
        }
        return contact_info
    
    def extract_entities_with_nlp(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités nommées avec spaCy."""
        if not self.nlp:
            return {"persons": [], "organizations": [], "locations": [], "misc": []}
        
        doc = self.nlp(text)
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "misc": []
        }
        
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "PER"]:
                entities["persons"].append(ent.text)
            elif ent.label_ in ["ORG", "ORGANIZATION"]:
                entities["organizations"].append(ent.text)
            elif ent.label_ in ["GPE", "LOC", "LOCATION"]:
                entities["locations"].append(ent.text)
            else:
                entities["misc"].append(f"{ent.text} ({ent.label_})")
        
        # Dédupliquer
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def extract_professional_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrait les informations professionnelles."""
        prof_info = {
            "job_titles": [],
            "companies": [],
            "skills": [],
            "industries": []
        }
        
        # Recherche de titres de postes dans les balises communes
        job_keywords = ["développeur", "ingénieur", "manager", "directeur", "consultant", 
                       "analyste", "chef de projet", "responsable", "coordinateur"]
        
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div"]):
            text = element.get_text().lower()
            for keyword in job_keywords:
                if keyword in text:
                    prof_info["job_titles"].append(element.get_text().strip())
        
        # Recherche de compétences techniques
        tech_keywords = ["python", "java", "javascript", "react", "vue", "angular", 
                        "sql", "mongodb", "docker", "kubernetes", "aws", "azure"]
        
        for element in soup.find_all(["p", "li", "span"]):
            text = element.get_text().lower()
            for tech in tech_keywords:
                if tech in text:
                    prof_info["skills"].append(tech)
        
        # Dédupliquer
        for key in prof_info:
            prof_info[key] = list(set(prof_info[key]))
        
        return prof_info
    
    def scrape_enhanced(self, start_url: str, max_pages: int = 10, 
                       same_origin_only: bool = True, timeout_s: int = 10) -> Dict[str, Any]:
        """Scraping avancé avec extraction d'informations complètes."""
        
        visited: Set[str] = set()
        to_visit: List[str] = [start_url]
        crawled: List[str] = []
        results: Dict[str, Any] = {
            "crawled": [],
            "contact_info": {},
            "entities": {},
            "professional_info": {},
            "structured_data": {},
            "errors": {}
        }
        
        try:
            origin_netloc = urlparse(start_url).netloc
        except Exception:
            origin_netloc = ""
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "DispyClusterEnhancedScraper/1.0 (+https://example.local)"
        })
        
        while to_visit and len(crawled) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            
            time.sleep(0.5)  # Pause plus longue pour être respectueux
            
            try:
                resp = session.get(url, timeout=timeout_s)
                if resp.status_code != 200:
                    results["errors"][url] = f"HTTP {resp.status_code}"
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Nettoyer le texte (enlever scripts, styles, etc.)
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text_content = soup.get_text()
                
                crawled.append(url)
                
                # Extraire toutes les informations
                results["contact_info"][url] = self.extract_contact_info(text_content)
                results["entities"][url] = self.extract_entities_with_nlp(text_content)
                results["professional_info"][url] = self.extract_professional_info(soup)
                results["structured_data"][url] = self.extract_structured_data(soup)
                
                # Suivre les liens
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    absolute_url, _ = urldefrag(absolute_url)
                    
                    if same_origin_only:
                        if urlparse(absolute_url).netloc != origin_netloc:
                            continue
                    
                    if (absolute_url not in visited and 
                        absolute_url not in to_visit and 
                        len(visited) + len(to_visit) < max_pages * 3):
                        to_visit.append(absolute_url)
                        
            except Exception as exc:
                results["errors"][url] = str(exc)
        
        results["crawled"] = crawled
        return results

# Fonction de compatibilité avec l'ancien scraper
def scrape_site_enhanced(start_url: str, max_pages: int = 10, 
                        same_origin_only: bool = True, timeout_s: int = 10) -> Dict[str, Any]:
    """Interface compatible avec l'ancien scraper."""
    scraper = EnhancedScraper()
    return scraper.scrape_enhanced(start_url, max_pages, same_origin_only, timeout_s)