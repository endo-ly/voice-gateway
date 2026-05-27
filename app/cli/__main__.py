"""CLI entry point: uv run python -m app.cli"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli", description="voice-gateway management CLI")
    subparsers = parser.add_subparsers(dest="command")

    from app.cli.voices import register_parser as register_voices

    register_voices(subparsers)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
