from unittest.mock import patch

from src.nomad_forces_export.cli import build_arg_parser, main


def test_build_arg_parser_parses_all_options():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "fetch",
            "--elements",
            "Si",
            "O",
            "--exclude-dataset",
            "Alexandria PBEsol",
            "--properties",
            "energy",
            "forces",
            "--format",
            "ase_db",
            "extxyz",
            "--output",
            "dataset",
            "--max-entries",
            "5000",
        ]
    )
    assert args.elements == ["Si", "O"]
    assert args.exclude_dataset == ["Alexandria PBEsol"]
    assert args.properties == ["energy", "forces"]
    assert args.format == ["ase_db", "extxyz"]
    assert args.output == "dataset"
    assert args.max_entries == 5000


def test_main_invokes_fetch_dataset_with_parsed_args():
    argv = [
        "fetch",
        "--elements",
        "Si",
        "--properties",
        "energy",
        "forces",
        "--format",
        "ase_db",
        "--output",
        "dataset.db",
    ]
    with patch("src.nomad_forces_export.cli.fetch_dataset") as mock_fetch:
        main(argv)

    assert mock_fetch.call_count == 1
    _, kwargs = mock_fetch.call_args
    assert kwargs["query"].elements == ["Si"]
    assert kwargs["properties"] == {"energy", "forces"}
    assert kwargs["output_format"] == ["ase_db"]
    assert kwargs["output_path"] == "dataset.db"
