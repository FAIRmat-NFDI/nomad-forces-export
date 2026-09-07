"""Command-line interface for nomad_forces_export: thin wrapper over fetch_dataset."""

import argparse
import sys

from nomad_forces_export import NomadQuery, fetch_dataset


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nomad-mlip-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a dataset from NOMAD")
    fetch_parser.add_argument("--elements", nargs="+", default=None)
    fetch_parser.add_argument("--formula", default=None)
    fetch_parser.add_argument("--method", default=None)
    fetch_parser.add_argument("--entry-ids", nargs="+", default=None, dest="entry_ids")
    fetch_parser.add_argument(
        "--exclude-dataset", nargs="+", default=[], dest="exclude_dataset"
    )
    fetch_parser.add_argument(
        "--properties",
        nargs="+",
        default=["energy", "forces"],
        choices=["energy", "forces", "stress"],
    )
    fetch_parser.add_argument(
        "--format", nargs="+", default=["ase_db"], choices=["ase_db", "extxyz"]
    )
    fetch_parser.add_argument("--output", required=True)
    fetch_parser.add_argument(
        "--max-entries", type=int, default=None, dest="max_entries"
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        query = NomadQuery(
            elements=args.elements,
            formula=args.formula,
            method=args.method,
            entry_ids=args.entry_ids,
            exclude_datasets=args.exclude_dataset,
        )
        fetch_dataset(
            query=query,
            properties=set(args.properties),
            output_format=args.format,
            output_path=args.output,
            max_entries=args.max_entries,
        )


if __name__ == "__main__":
    main(sys.argv[1:])
