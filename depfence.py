#!/usr/bin/env python3
"""DepFence CLI \u2014 Dependency maintainer risk intelligence scanner."""
import argparse
import json
import os
import sys
from dataclasses import asdict

from scanner import scan

COLORS = {
    "LOW": "\033[32m",
    "MEDIUM": "\033[33m",
    "HIGH": "\033[31m",
    "CRITICAL": "\033[91m",
    "UNKNOWN": "\033[90m",
}
RESET = "\033[0m"
FREE_LIMIT = 20


def render(reports, color=True):
    """Print a formatted risk table to stdout."""
    print(f"\n{'Package':<30} {'Risk':>5} {'Days':>6} {'Maint':>5} {'Rels':>5} Verdict")
    print("\u2500" * 70)
    for rpt in reports:
        c = COLORS.get(rpt.verdict, "") if color else ""
        e = RESET if color else ""
        d = str(rpt.last_release_days) if rpt.last_release_days >= 0 else "?"
        print(
            f"{rpt.name:<30} {c}{rpt.score:>5}{e} {d:>6} "
            f"{rpt.maintainer_count:>5} {rpt.release_count:>5} {c}{rpt.verdict}{e}"
        )


def main():
    """CLI entry point."""
    p = argparse.ArgumentParser(
        prog="depfence",
        description="Scan dependencies for maintainer abandonment risk",
    )
    p.add_argument("file", help="Path to requirements.txt or package.json")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument(
        "--fail-over", type=int, default=0, metavar="N",
        help="Exit 1 if any dependency risk score >= N (CI gate)",
    )
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    reports = scan(args.file)
    truncated = len(reports) > FREE_LIMIT
    shown = reports[:FREE_LIMIT] if truncated else reports

    if args.json:
        out = {"results": [asdict(r) for r in shown], "truncated": truncated}
        print(json.dumps(out, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        render(shown, color=use_color)
        if truncated:
            print(f"\n\u26a0 Showing {FREE_LIMIT}/{len(reports)} deps \u2014 upgrade at depfence.dev/pricing")
        risky = [r for r in shown if r.score >= 50]
        if risky:
            print(f"\n\U0001f6a8 {len(risky)} package(s) at HIGH+ abandonment risk!")

    if args.fail_over and any(r.score >= args.fail_over for r in shown):
        sys.exit(1)


if __name__ == "__main__":
    main()
