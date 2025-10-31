from typing import Dict, Any, Optional, List, Tuple
import time

import redis

from web.config.metrics_config import REDIS_CONFIG


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=REDIS_CONFIG["host"],
        port=REDIS_CONFIG["port"],
        db=REDIS_CONFIG["db"],
        decode_responses=REDIS_CONFIG.get("decode_responses", True),
    )


def ts_create(
    key: str,
    labels: Optional[Dict[str, str]] = None,
    retention_ms: Optional[int] = None,
    duplicate_policy: Optional[str] = "last",
) -> bool:
    client = get_redis_client()
    args: List[Any] = ["TS.CREATE", key]

    if retention_ms is not None:
        args.extend(["RETENTION", retention_ms])

    if duplicate_policy:
        args.extend(["DUPLICATE_POLICY", duplicate_policy])

    if labels:
        args.append("LABELS")
        for k, v in labels.items():
            args.extend([k, v])

    try:
        client.execute_command(*args)
        return True
    except redis.ResponseError as e:
        # Already exists is fine
        if "already exists" in str(e).lower():
            return False
        raise


def ts_add(
    key: str,
    value: float,
    timestamp_ms: Optional[int] = None,
    labels_if_create: Optional[Dict[str, str]] = None,
    retention_ms_if_create: Optional[int] = None,
) -> int:
    client = get_redis_client()
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    try:
        added_ts: int = client.execute_command("TS.ADD", key, ts, value)
        return int(added_ts)
    except redis.ResponseError as e:
        if "TSDB: the key does not exist" in str(e):
            ts_create(key, labels=labels_if_create, retention_ms=retention_ms_if_create)
            added_ts = client.execute_command("TS.ADD", key, ts, value)
            return int(added_ts)
        raise


def ts_create_rule(src: str, dest: str, aggregation: str, bucket_ms: int) -> None:
    client = get_redis_client()
    client.execute_command(
        "TS.CREATERULE", src, dest, "AGGREGATION", aggregation, bucket_ms
    )


def xadd(stream: str, fields: Dict[str, Any], maxlen_approx: Optional[int] = None) -> str:
    client = get_redis_client()
    kwargs: Dict[str, Any] = {}
    if maxlen_approx is not None:
        kwargs["maxlen"] = maxlen_approx
        kwargs["approximate"] = True
    return client.xadd(stream, fields, **kwargs)


def xreadgroup(
    group: str,
    consumer: str,
    streams: Dict[str, str],
    count: Optional[int] = None,
    block_ms: Optional[int] = None,
) -> Optional[List[Tuple[str, List[Tuple[str, Dict[str, str]]]]]]:
    client = get_redis_client()
    return client.xreadgroup(groupname=group, consumername=consumer, streams=streams, count=count, block=block_ms)


def xgroup_create(stream: str, group: str, id: str = "$", mkstream: bool = True) -> None:
    client = get_redis_client()
    try:
        client.xgroup_create(name=stream, groupname=group, id=id, mkstream=mkstream)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            return
        raise


