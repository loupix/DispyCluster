"""Service web FastAPI pour lancer le scraping sur un worker.

Endpoints:
- GET /health: statut simple
- POST /scrape: lance un crawl limité et renvoie les résultats
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field

from workers.scraper_worker import scrape_site


app = FastAPI(title="Dispy Scraper Service", version="0.1.0")


class ScrapeRequest(BaseModel):
    start_url: HttpUrl
    max_pages: int = Field(10, ge=1, le=1000)
    same_origin_only: bool = True
    timeout_s: int = Field(10, ge=1, le=60)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/scrape")
def scrape(req: ScrapeRequest) -> Dict[str, Any]:
    try:
        result = scrape_site(
            start_url=str(req.start_url),
            max_pages=req.max_pages,
            same_origin_only=req.same_origin_only,
            timeout_s=req.timeout_s,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

