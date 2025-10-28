"""Worker de scraping simple.

Objectif:
- Télécharger un nombre limité de pages en respectant une profondeur ou une liste d'URLs.
- Extraire un sous-ensemble d'informations personnelles basiques (emails, numéros de téléphone) depuis le HTML texte.

Remarques:
- Ce worker est volontairement minimal et synchrone pour s'exécuter facilement sur un RPi.
- Pour un scraping plus robuste: gérer robots.txt, délais aléatoires, user-agent rotatifs, et backoff.
"""

from typing import Dict, List, Optional, Set, Tuple
import re
import time
from urllib.parse import urljoin, urldefrag

try:
    # On garde requests pour la simplicité; sur RPi c'est OK
    import requests
except Exception:  # pragma: no cover - environnement minimal
    requests = None  # type: ignore


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?\d[\d\s().-]{7,}\d")
HREF_REGEX = re.compile(r"href=[\"']([^\"'#>\s]+)[\"']", re.IGNORECASE)


def _normalize_url(base_url: str, href: str) -> Optional[str]:
    try:
        absolute = urljoin(base_url, href)
        # retire les fragments #...
        absolute, _ = urldefrag(absolute)
        return absolute
    except Exception:
        return None


def _extract_links(base_url: str, html_text: str) -> List[str]:
    links: List[str] = []
    for m in HREF_REGEX.finditer(html_text):
        href = m.group(1)
        normalized = _normalize_url(base_url, href)
        if normalized:
            links.append(normalized)
    return links


def _extract_pii(text: str) -> Dict[str, List[str]]:
    emails = sorted(set(EMAIL_REGEX.findall(text)))
    phones = sorted(set(PHONE_REGEX.findall(text)))
    return {"emails": emails, "phones": phones}


def scrape_site(
    start_url: str,
    max_pages: int = 10,
    same_origin_only: bool = True,
    timeout_s: int = 10,
) -> Dict[str, object]:
    """Crawl basique à partir d'une URL et extrait des PII.

    Args:
        start_url: URL de départ.
        max_pages: limite stricte du nombre de pages à télécharger.
        same_origin_only: si True, ne suit que les liens du même host.
        timeout_s: timeout réseau par requête.

    Returns:
        dict avec:
            - crawled: liste d'URLs visitées
            - pii_by_url: mapping url -> {emails:[], phones:[]}
            - errors: mapping url -> erreur
    """
    if requests is None:
        return {"crawled": [], "pii_by_url": {}, "errors": {"env": "requests manquant"}}

    visited: Set[str] = set()
    to_visit: List[str] = [start_url]
    crawled: List[str] = []
    pii_by_url: Dict[str, Dict[str, List[str]]] = {}
    errors: Dict[str, str] = {}

    try:
        from urllib.parse import urlparse

        origin_netloc = urlparse(start_url).netloc
    except Exception:
        origin_netloc = ""

    session = requests.Session()
    session.headers.update({
        "User-Agent": "DispyClusterScraper/0.1 (+https://example.local)"
    })

    while to_visit and len(crawled) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        # Respect basique: petite pause pour être gentil avec la cible
        time.sleep(0.2)

        try:
            resp = session.get(url, timeout=timeout_s)
            content_type = resp.headers.get("Content-Type", "")
            if resp.status_code != 200 or "text/html" not in content_type:
                errors[url] = f"HTTP {resp.status_code} / type {content_type}"
                continue
            html = resp.text
        except Exception as exc:  # réseau, SSL, etc.
            errors[url] = str(exc)
            continue

        crawled.append(url)
        pii_by_url[url] = _extract_pii(html)

        # Suivi de liens très simple
        for link in _extract_links(url, html):
            if same_origin_only:
                try:
                    from urllib.parse import urlparse

                    if urlparse(link).netloc != origin_netloc:
                        continue
                except Exception:
                    continue
            if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages * 3:
                to_visit.append(link)

    return {"crawled": crawled, "pii_by_url": pii_by_url, "errors": errors}

