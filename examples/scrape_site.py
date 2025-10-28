"""Exemple: soumettre un job de scraping avec limite de pages.

Cet exemple ne fait qu'appeler directement la fonction du worker pour la démo.
Dans une vraie exécution cluster, vous enverriez cette tâche via le dispatcher
ou une couche RPC vers un noeud RPi.
"""

from typing import Any, Dict

from workers.scraper_worker import scrape_site


def main() -> None:
    url = "https://example.com/"  # à adapter
    max_pages = 5
    result: Dict[str, Any] = scrape_site(url, max_pages=max_pages, same_origin_only=True)

    print("Crawled:")
    for u in result.get("crawled", []):
        print(" -", u)

    print("\nPII:")
    pii = result.get("pii_by_url", {})
    for u, data in pii.items():
        print(" -", u)
        print("    emails:", ", ".join(data.get("emails", [])))
        print("    phones:", ", ".join(data.get("phones", [])))

    errs = result.get("errors", {})
    if errs:
        print("\nErreurs:")
        for u, e in errs.items():
            print(" -", u, "->", e)


if __name__ == "__main__":
    main()

