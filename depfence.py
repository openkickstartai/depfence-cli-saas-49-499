#!/usr/bin/env python3
"""DepFence CLI \u2014 Dependency maintainer risk intelligence scanner."""
import argparse
import os
import sys

from scanner import scan
from formatters import format_table, format_json, format_sarif

FREE_LIMIT = 20


def main():
    """CLI entry point."""
    p = argparse.ArgumentParser(
        prog="depfence",
        description="Scan dependencies for maintainer abandonment risk",
    )
    p.add_argument("file", help="Path to requirements.txt or package.json")
    p.add_argument(
        "-o", "--output", choices=["table", "json", "sarif"], default="table",
        help="Output format: table (default), json, sarif",
    )
    p.add_argument(
        "--json", action="store_true", dest="json_legacy",
        help="Output JSON (legacy flag, prefer -o json)",
    )
    p.add_argument(
        "--exit-code", action="store_true",
        help="Exit with code 1 if any package risk_score >= threshold",
    )
    p.add_argument(
        "--threshold", type=float, default=0.7, metavar="T",
        help="Risk score threshold for --exit-code (default: 0.7)",
    )
    p.add_argument(
        "--fail-over", type=int, default=0, metavar="N",
        help="Exit 1 if any dependency risk score >= N (legacy CI gate)",
    )
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    reports = scan(args.file)
    truncated = len(reports) > FREE_LIMIT
    shown = reports[:FREE_LIMIT] if truncated else reports

    # Determine output format (legacy --json flag support)
    output_format = args.output
    if args.json_legacy:
        output_format = "json"

    if output_format == "json":
        print(format_json(shown))
    elif output_format == "sarif":
        print(format_sarif(shown))
    else:
        print(format_table(shown, color=not args.no_color))

    if truncated:
        print(
            f"\n\u26a0 Free tier: showing {FREE_LIMIT}/{len(reports)} deps. "
            "Upgrade to Pro for unlimited.",
            file=sys.stderr,
        )

    # Exit code logic
    exit_code = 0

    # Legacy --fail-over support
    if args.fail_over and any(r.score >= args.fail_over for r in shown):
        exit_code = 1

    # New --exit-code support
    if args.exit_code:
        threshold_score = args.threshold * 100
        if any(r.score >= threshold_score for r in shown):
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
