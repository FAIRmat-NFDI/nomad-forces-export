from pathlib import Path
from unittest.mock import patch

from ase.db import connect

from src.nomad_forces_export import NomadQuery, fetch_dataset


def test_fetch_dataset_end_to_end(tmp_path: Path):
    search_response = {
        "data": [
            {"entry_id": "e1", "upload_id": "u1"},
            {
                "entry_id": "e2",
                "upload_id": "u1",
                "datasets": [{"dataset_name": "Alexandria PBE"}],
            },
        ],
        "pagination": {},
    }
    archive_response = {
        "data": [
            {
                "entry_id": "e1",
                "upload_id": "u1",
                "archive": {
                    "run": [
                        {
                            "system": [
                                {
                                    "atoms": {
                                        "species": [1, 1],
                                        "labels": ["H", "H"],
                                        "positions": [[0, 0, 0], [0, 0, 7.4e-11]],
                                        "periodic": [False, False, False],
                                    }
                                }
                            ],
                            "calculation": [
                                {
                                    "energy": {"free": {"value": -1.602176634e-19}},
                                    "forces": {
                                        "total": {"value": [[0, 0, 0], [0, 0, 0]]}
                                    },
                                    "system_ref": "/run/0/system/0",
                                }
                            ],
                        }
                    ]
                },
            }
        ]
    }

    def fake_post(path, payload):
        if path == "/entries/query":
            return search_response
        if path == "/entries/archive/query":
            return archive_response
        raise AssertionError(f"unexpected path {path}")

    query = NomadQuery(elements=["H"], exclude_datasets=["Alexandria"])
    db_path = tmp_path / "dataset.db"
    with patch("nomad_forces_export.api.NomadClient.post", side_effect=fake_post):
        fetch_dataset(
            query=query,
            properties={"energy", "forces"},
            output_format="ase_db",
            output_path=str(db_path),
        )
    with connect(str(db_path)) as db:
        rows = list(db.select())
    assert len(rows) == 1
    assert rows[0].nomad_entry_id == "e1"
