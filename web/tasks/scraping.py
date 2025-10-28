from web.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5, name="web.tasks.scraping.run_scrape")
def run_scrape(self, payload: dict):
    # Exemple minimal de job CPU/IO
    try:
        start_url = payload.get("start_url")
        max_pages = int(payload.get("max_pages", 10))
        same_origin_only = bool(payload.get("same_origin_only", True))
        # Ici on ferait le scraping réel. On renvoie un résultat factice.
        return {
            "ok": True,
            "start_url": start_url,
            "pages_crawled": min(max_pages, 10),
            "same_origin_only": same_origin_only,
        }
    except Exception as exc:
        raise self.retry(exc=exc)

