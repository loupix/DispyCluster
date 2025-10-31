"""Endpoints TimeSeries pour le dashboard.

Expose des lectures simples (TS.RANGE) avec support d'agrégation côté RedisTimeSeries.
"""

from fastapi import APIRouter, HTTPException, Query

from web.core.redis_ts import ts_range, ts_mrange


# Routeur dédié aux séries temporelles
router = APIRouter(prefix="/api/ts", tags=["metrics-timeseries"])


@router.get("/range")
async def get_ts_range(
    key: str = Query(..., description="Clé de la série TS, ex: ts:cpu.usage"),
    frm: int = Query(..., description="Timestamp ms début"),
    to: int = Query(..., description="Timestamp ms fin"),
    agg = Query(None, description="Agrégation: avg,sum,min,max,count,first,last"),
    bucket_ms = Query(None, description="Taille de fenêtre en ms si agg"),
):
    """Lit une plage de points sur une série temporelle.

    - Si `agg` et `bucket_ms` sont fournis, Redis agrège par fenêtres (downsampling côté serveur).
    - `frm`/`to` sont en millisecondes depuis epoch.
    """
    try:
        points = ts_range(key, frm, to, aggregation=agg, bucket_ms=bucket_ms)
        return {
            "key": key,
            "from": frm,
            "to": to,
            "aggregation": agg,
            "bucket_ms": bucket_ms,
            "points": points,
        }
    except Exception as e:
        # On renvoie l'erreur au client, utile pour diagnostiquer clé manquante ou mauvais paramètres
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mrange")
async def get_ts_mrange(
    frm: int = Query(..., description="Timestamp ms début"),
    to: int = Query(..., description="Timestamp ms fin"),
    filters = Query(["metric=cpu.usage"], description="Filtres label=value, répétables"),
    agg = Query(None, description="Agrégation: avg,sum,min,max,count,first,last"),
    bucket_ms = Query(None, description="Taille de fenêtre en ms si agg"),
):
    """Lit plusieurs séries en une requête via des labels.

    Exemple: filters=metric=cpu.usage&filters=host=node13.lan
    """
    try:
        series = ts_mrange(frm, to, filters, aggregation=agg, bucket_ms=bucket_ms)
        return {"from": frm, "to": to, "filters": filters, "aggregation": agg, "bucket_ms": bucket_ms, "series": series}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


