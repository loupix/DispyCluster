import argparse

from web.core.redis_ts import ts_create, ts_create_rule


def main() -> None:
    parser = argparse.ArgumentParser(description="Create downsampling rules between series")
    parser.add_argument("src", type=str, help="Source series key")
    parser.add_argument("dest", type=str, help="Destination series key")
    parser.add_argument("aggregation", type=str, choices=["avg", "sum", "min", "max", "count", "first", "last"], help="Aggregation type")
    parser.add_argument("bucket", type=int, help="Bucket size in ms")
    args = parser.parse_args()

    # Ensure destination series exists
    ts_create(args.dest)
    ts_create_rule(args.src, args.dest, args.aggregation, args.bucket)
    print("rule-created")


if __name__ == "__main__":
    main()


