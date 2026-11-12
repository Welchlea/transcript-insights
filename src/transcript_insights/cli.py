"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .load import load_transcripts
from .metrics import summarise
from .report import to_json, to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="transcript-insights", description=__doc__)
    parser.add_argument("transcripts", help="JSON Lines file with one conversation on each line")
    parser.add_argument("--designed-handover", action="append", default=[], metavar="TOPIC",
                        help="a topic that should always go to a person. Repeat for each topic")
    parser.add_argument("--top", type=int, default=5, help="rows to show in each list")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", help="write the report to this file")
    args = parser.parse_args(argv)

    summary = summarise(load_transcripts(args.transcripts), set(args.designed_handover), args.top)
    output = to_json(summary) if args.format == "json" else to_markdown(summary)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
