from typing import Optional
import time

import redis

from web.config.metrics_config import REDIS_CONFIG

# Helpers simples autour de RedisTimeSeries et Redis Streams
# Objectif: garder un code lisible et réutilisable pour produire/consommer
# des métriques et lire des séries temporelles.


def get_redis_client():
    """Client Redis configuré depuis REDIS_CONFIG.

    Astuce: decode_responses=True pour manipuler des str côté Python.
    """
    return redis.Redis(
        host=REDIS_CONFIG["host"],
        port=REDIS_CONFIG["port"],
        db=REDIS_CONFIG["db"],
        decode_responses=REDIS_CONFIG.get("decode_responses", True),
    )


def ts_create(
    key,
    labels=None,
    retention_ms: Optional[int] = None,
    duplicate_policy: Optional[str] = "last",
):
    """Crée une série TS si elle n'existe pas.

    - retention_ms: durée de rétention en ms (None pour illimité).
    - duplicate_policy: comportement si même timestamp est réécrit (last par défaut).
    - labels: tags de la série (utile pour filtrer/agréger avec MRANGE).
    """
    client = get_redis_client()
    args = ["TS.CREATE", key]

    if retention_ms is not None:
        args.extend(["RETENTION", retention_ms])

    if duplicate_policy:
        # Evite les erreurs quand on écrit plusieurs fois le même timestamp
        args.extend(["DUPLICATE_POLICY", duplicate_policy])

    if labels:
        args.append("LABELS")
        for k, v in labels.items():
            args.extend([k, v])

    try:
        client.execute_command(*args)
        return True
    except redis.ResponseError as e:
        # Si la série existe déjà, on considère que c'est ok
        if "already exists" in str(e).lower():
            return False
        raise


def ts_add(
    key,
    value,
    timestamp_ms: Optional[int] = None,
    labels_if_create=None,
    retention_ms_if_create: Optional[int] = None,
):
    """Ajoute un point (timestamp,value) dans une série TS.

    - Crée la série à la volée si elle n'existe pas (avec labels/rétention).
    - timestamp_ms: si None, utilise l'horodatage actuel en ms.
    """
    client = get_redis_client()
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    try:
        added_ts = client.execute_command("TS.ADD", key, ts, value)
        return int(added_ts)
    except redis.ResponseError as e:
        if "TSDB: the key does not exist" in str(e):
            # Création lazy de la série avec ses labels par défaut
            ts_create(key, labels=labels_if_create, retention_ms=retention_ms_if_create)
            added_ts = client.execute_command("TS.ADD", key, ts, value)
            return int(added_ts)
        raise


def ts_create_rule(src, dest, aggregation, bucket_ms):
    """Crée une règle de downsampling de src -> dest.

    Exemple: avg 60000 pour moyenne par minute.
    La série dest doit exister.
    """
    client = get_redis_client()
    client.execute_command(
        "TS.CREATERULE", src, dest, "AGGREGATION", aggregation, bucket_ms
    )


def xadd(stream, fields, maxlen_approx: Optional[int] = None):
    """Ajoute un message dans un Stream.

    - maxlen_approx: trim approximatif pour limiter la taille du Stream.
    """
    client = get_redis_client()
    kwargs = {}
    if maxlen_approx is not None:
        kwargs["maxlen"] = maxlen_approx
        kwargs["approximate"] = True
    return client.xadd(stream, fields, **kwargs)


def xreadgroup(
    group,
    consumer,
    streams,
    count: Optional[int] = None,
    block_ms: Optional[int] = None,
):
    """Lit des messages en consumer group.

    - streams: dict {stream_key: ">"} pour prendre les nouveaux messages.
    - block_ms: timeout d'attente (ms) avant de rendre la main.
    - count: batch size.
    """
    client = get_redis_client()
    return client.xreadgroup(groupname=group, consumername=consumer, streams=streams, count=count, block=block_ms)


def xgroup_create(stream, group, id: str = "$", mkstream: bool = True):
    """Crée un consumer group si absent.

    - id="0" pour reprendre tout l'historique, "$" pour commencer au tail.
    """
    client = get_redis_client()
    try:
        client.xgroup_create(name=stream, groupname=group, id=id, mkstream=mkstream)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            # Le groupe existe déjà, on ignore
            return
        raise


def ts_range(
    key,
    from_ts,
    to_ts,
    aggregation: Optional[str] = None,
    bucket_ms: Optional[int] = None,
):
    """Retourne les points d'une série entre deux timestamps (ms).

    - aggregation + bucket_ms pour regrouper (ex: avg 60000 pour 1 minute).
    """
    client = get_redis_client()
    args = ["TS.RANGE", key, from_ts, to_ts]
    if aggregation and bucket_ms:
        args.extend(["AGGREGATION", aggregation, bucket_ms])
    data = client.execute_command(*args)
    # data is list of [timestamp, value]
    return [(int(ts), float(val)) for ts, val in data]


def ts_mrange(
    from_ts,
    to_ts,
    filters,
    aggregation: Optional[str] = None,
    bucket_ms: Optional[int] = None,
):
    """Lit plusieurs séries par labels avec TS.MRANGE.

    - filters: liste de filtres label=value (ex: ["metric=cpu.usage"]).
    - aggregation/bucket_ms optionnels.
    Retourne une liste d'objets: {key, labels, points}.
    """
    client = get_redis_client()
    args = ["TS.MRANGE", from_ts, to_ts]
    if aggregation and bucket_ms:
        args.extend(["AGGREGATION", aggregation, bucket_ms])
    # WITHLABELS pour identifier les séries (host, metric, etc.)
    args.append("WITHLABELS")
    args.append("FILTER")
    if isinstance(filters, (list, tuple)):
        args.extend(filters)
    else:
        args.append(str(filters))

    raw = client.execute_command(*args)
    # Format: [[key, [[label, value]...], [[ts,val]...]], ...]
    result = []
    for serie in raw:
        key = serie[0]
        labels_list = serie[1] if len(serie) > 1 else []
        samples = serie[2] if len(serie) > 2 else []
        labels = {k: v for k, v in labels_list}
        points = [(int(ts), float(val)) for ts, val in samples]
        result.append({"key": key, "labels": labels, "points": points})
    return result


