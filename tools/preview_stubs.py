import argparse
import json
import sys

from stubgen import generate, parse_db, parse_nids


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Preview the existing stub generator as JSON without writing code or debt files")
    parser.add_argument("--module", required=True)
    parser.add_argument("--nids", required=True)
    parser.add_argument("--db")
    parser.add_argument("--td-path")
    parser.add_argument("--td-lib")
    args = parser.parse_args(argv)
    try:
        nids = parse_nids(args.nids)
        database = parse_db(args.db) if args.db else {}
        code, debt = generate(args.module, nids, database, args.td_path, args.td_lib)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"nids": nids, "code": code, "technical_debt": debt}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
