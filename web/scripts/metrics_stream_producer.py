import argparse
import json
from typing import Dict

from web.core.redis_ts import xadd


def main() -> None:
    parser = argparse.ArgumentParser(description="Producer: push metric events to Redis Streams")
    parser.add_argument("metric", type=str, help="Metric name, e.g. cpu.usage")
    parser.add_argument("value", type=float, help="Metric value")
    parser.add_argument("--labels", type=str, default="{}", help="JSON string of labels")
    parser.add_argument("--stream", type=str, default="metrics:ingest", help="Stream key")
    parser.add_argument("--maxlen", type=int, default=100000, help="Approximate maxlen for stream")
    args = parser.parse_args()

    try:
        labels: Dict[str, str] = json.loads(args.labels)
    except Exception:
        labels = {}

    fields: Dict[str, str] = {
        "metric": args.metric,
        "value": str(args.value),
        "labels": json.dumps(labels),
    }

    message_id = xadd(args.stream, fields, maxlen_approx=args.maxlen)
    print(f"pushed: {message_id}")


if __name__ == "__main__":
    main()


