"""
CLI entry point.

Usage:
    candidate-transformer --input data/ --config config.json [--output candidate.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from candidate_transformer.config import PipelineConfig
from candidate_transformer.pipeline import run_pipeline


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="candidate-transformer",
        description="Multi-Source Candidate Data Transformer Pipeline",
    )
    parser.add_argument("--input", required=True, type=Path, help="Directory containing input source files")
    parser.add_argument("--config", required=False, type=Path, default=None, help="Path to config.json")
    parser.add_argument("--output", required=False, type=Path, default=Path("candidate.json"),
                         help="Path to write the generated JSON output (default: candidate.json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.input.exists() or not args.input.is_dir():
        print(f"error: input directory not found: {args.input}", file=sys.stderr)
        return 1

    config = PipelineConfig.load(args.config)

    result = run_pipeline(args.input, config)

    args.output.write_text(json.dumps(result.output_records, indent=2, default=str), encoding="utf-8")

    print(f"Ingested {result.raw_record_count} raw record(s) from '{args.input}'")
    print(f"Resolved into {result.profile_count} canonical candidate profile(s)")
    print(f"Wrote {len(result.output_records)} valid record(s) to '{args.output}'")

    if result.validation_failures:
        print(f"WARNING: {len(result.validation_failures)} record(s) failed schema validation and were excluded:",
              file=sys.stderr)
        for failure in result.validation_failures:
            for err in failure["errors"]:
                print(f"  - {err}", file=sys.stderr)

    return 0 if not result.validation_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
