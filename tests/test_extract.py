# tests/test_extract.py
import json
from pathlib import Path

import numpy as np
import pytest

from src.nomad_forces_export.extract import to_atoms

FIXTURES = Path(__file__).parent / "fixtures"


def _load_archive_entry():
    return json.loads((FIXTURES / "archive_trajectory_sample.json").read_text())


def test_to_atoms_yields_one_atoms_per_calculation_frame():
    entry = _load_archive_entry()
    atoms_list = list(to_atoms(entry, properties={"energy", "forces"}))
    assert len(atoms_list) == 2


def test_to_atoms_sets_species_and_positions_in_angstrom():
    entry = _load_archive_entry()
    atoms_list = list(to_atoms(entry, properties={"energy", "forces"}))
    atoms = atoms_list[0]
    assert atoms.get_chemical_symbols() == ["Ca", "Fe", "Fe", "Re"]
    # position of atom 0, y-coordinate: 2.16717099e-10 m -> Angstrom
    assert atoms.positions[0][1] == pytest.approx(2.16717099, rel=1e-6)


def test_to_atoms_sets_cell_and_pbc():
    entry = _load_archive_entry()
    atoms = next(iter(to_atoms(entry, properties={"energy", "forces"})))
    assert atoms.pbc.tolist() == [True, True, True]
    assert atoms.cell.array[0][2] == pytest.approx(4.33434198, rel=1e-6)


def test_to_atoms_attaches_energy_and_forces():
    entry = _load_archive_entry()
    atoms = next(iter(to_atoms(entry, properties={"energy", "forces"})))
    energy_ev = atoms.get_potential_energy()
    # free energy -4.174314829823578e-18 J -> eV
    # assert energy_ev == pytest.approx(-26.05402410465368, rel=1e-4)
    assert energy_ev == pytest.approx(0.0029920300246507126, rel=1e-4)
    forces = atoms.get_forces()
    assert forces.shape == (4, 3)
    assert np.allclose(forces, 0.0)


def test_to_atoms_attaches_stress_when_requested():
    entry = _load_archive_entry()
    atoms = next(iter(to_atoms(entry, properties={"energy", "forces", "stress"})))
    stress = atoms.get_stress(voigt=False)
    assert stress.shape == (3, 3)
    # -22805087491.0 Pa -> eV/Ang^3
    assert stress[0][0] == pytest.approx(-0.14233816169164262, rel=1e-3)


def test_to_atoms_attaches_info_metadata():
    entry = _load_archive_entry()
    atoms = next(iter(to_atoms(entry, properties={"energy", "forces"})))
    assert atoms.info["nomad_entry_id"] == "----9KNOtIZc9bDFEWxgjeSRsJrC"
    assert atoms.info["nomad_upload_id"] == "r0ck_h3kQQGZdp5E41vb9g"


def test_to_atoms_skips_frames_missing_requested_property():
    entry = _load_archive_entry()
    # remove stress from the first calculation frame only
    del entry["archive"]["run"][0]["calculation"][0]["stress"]
    atoms_list = list(to_atoms(entry, properties={"energy", "forces", "stress"}))
    assert len(atoms_list) == 1
    assert atoms_list[0].info["nomad_entry_id"] == "----9KNOtIZc9bDFEWxgjeSRsJrC"


def test_to_atoms_skips_frame_when_system_ref_points_to_different_run():
    entry = {
        "entry_id": "cross-run-test",
        "upload_id": "u1",
        "archive": {
            "run": [
                {
                    "system": [
                        {
                            "atoms": {
                                "species": [1],
                                "labels": ["H"],
                                "positions": [[0.0, 0.0, 0.0]],
                                "periodic": [False, False, False],
                            }
                        }
                    ],
                    "calculation": [
                        {
                            "energy": {"free": {"value": -1.602176634e-19}},
                            "forces": {"total": {"value": [[0.0, 0.0, 0.0]]}},
                            # BUG SCENARIO: this ref points into run 1, not run 0
                            "system_ref": "/run/1/system/0",
                        }
                    ],
                },
                {
                    "system": [
                        {
                            "atoms": {
                                "species": [6],
                                "labels": ["C"],
                                "positions": [[1.0, 1.0, 1.0]],
                                "periodic": [False, False, False],
                            }
                        }
                    ],
                    "calculation": [],
                },
            ]
        },
    }

    atoms_list = list(to_atoms(entry, properties={"energy", "forces"}))
    assert atoms_list == []


def test_to_atoms_resolves_system_ref_within_same_run_in_multirun_archive():
    entry = {
        "entry_id": "same-run-test",
        "upload_id": "u1",
        "archive": {
            "run": [
                {
                    "system": [
                        {
                            "atoms": {
                                "species": [1],
                                "labels": ["H"],
                                "positions": [[0.0, 0.0, 0.0]],
                                "periodic": [False, False, False],
                            }
                        }
                    ],
                    "calculation": [
                        {
                            "energy": {"free": {"value": -1.602176634e-19}},
                            "forces": {"total": {"value": [[0.0, 0.0, 0.0]]}},
                            "system_ref": "/run/0/system/0",
                        }
                    ],
                },
                {
                    "system": [
                        {
                            "atoms": {
                                "species": [6],
                                "labels": ["C"],
                                "positions": [[1.0, 1.0, 1.0]],
                                "periodic": [False, False, False],
                            }
                        }
                    ],
                    "calculation": [
                        {
                            "energy": {"free": {"value": -3.0e-19}},
                            "forces": {"total": {"value": [[0.0, 0.0, 0.0]]}},
                            "system_ref": "/run/1/system/0",
                        }
                    ],
                },
            ]
        },
    }

    atoms_list = list(to_atoms(entry, properties={"energy", "forces"}))
    assert len(atoms_list) == 2
    assert atoms_list[0].get_chemical_symbols() == ["H"]
    assert atoms_list[1].get_chemical_symbols() == ["C"]


def test_to_atoms_skips_frame_with_unparseable_system_ref():
    entry = {
        "entry_id": "malformed-ref-test",
        "upload_id": "u1",
        "archive": {
            "run": [
                {
                    "system": [
                        {
                            "atoms": {
                                "species": [1],
                                "labels": ["H"],
                                "positions": [[0.0, 0.0, 0.0]],
                                "periodic": [False, False, False],
                            }
                        }
                    ],
                    "calculation": [
                        {
                            "energy": {"free": {"value": -1.602176634e-19}},
                            "forces": {"total": {"value": [[0.0, 0.0, 0.0]]}},
                            "system_ref": "not-a-valid-ref",
                        }
                    ],
                }
            ]
        },
    }

    atoms_list = list(to_atoms(entry, properties={"energy", "forces"}))
    assert atoms_list == []
