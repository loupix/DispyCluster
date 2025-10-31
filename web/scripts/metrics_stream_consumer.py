import argparse
import json
import time
from typing import Dict

from web.core.redis_ts import xgroup_create, xreadgroup, ts_add


def process_message(values: Dict[str, str]) -> None:
    metric = values.get("metric", "unknown")
    value_raw = values.get("value", "0")
    labels_raw = values.get("labels", "{}")

    try:
        value = float(value_raw)
    except Exception:
        return

    try:
        labels = json.loads(labels_raw)
    except Exception:
        labels = {}

    # Key policy to be refined later
    series_key = f"ts:{metric}"
    ts_add(series_key, value, timestamp_ms=None, labels_if_create={**{"metric": metric}, **{k: str(v) for k, v in labels.items()}}, retention_ms_if_create=None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consumer: read metric events and write to RedisTimeSeries")
    parser.add_argument("--stream", type=str, default="metrics:ingest", help="Stream key")
    parser.add_argument("--group", type=str, default="metrics_cg", help="Consumer group")
    parser.add_argument("--consumer", type=str, default="worker-1", help="Consumer name")
    parser.add_argument("--block", type=int, default=5000, help="Block timeout in ms")
    parser.add_argument("--count", type=int, default=100, help="Read batch size")
    args = parser.parse_args()

    xgroup_create(args.stream, args.group, id="0", mkstream=True)

    while True:
        messages = xreadgroup(
            group=args.group,
            consumer=args.consumer,
            streams={args.stream: ">"},
            count=args.count,
            block_ms=args.block,
        )

        if not messages:
            continue

        for stream_key, entries in messages:
            for entry_id, fields in entries:
                process_message(fields)
        # Small pause to avoid tight loop on empty
        time.sleep(0.05)


if __name__ == "__main__":
    main()


