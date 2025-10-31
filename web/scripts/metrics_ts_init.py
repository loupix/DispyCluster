import argparse
import json
from typing import Dict

from web.core.redis_ts import ts_create


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize RedisTimeSeries keys with labels and retention")
    parser.add_argument("key", type=str, help="Series key, e.g. ts:cpu.usage")
    parser.add_argument("--labels", type=str, default="{}", help="JSON string of labels")
    parser.add_argument("--retention", type=int, default=None, help="Retention in ms")
    parser.add_argument("--dup-policy", type=str, default="last", help="Duplicate policy: last, first, sum, min, max")
    args = parser.parse_args()

    try:
        labels: Dict[str, str] = json.loads(args.labels)
    except Exception:
        labels = {}

    created = ts_create(args.key, labels=labels, retention_ms=args.retention, duplicate_policy=args.dup_policy)
    print("created" if created else "exists")


if __name__ == "__main__":
    main()


