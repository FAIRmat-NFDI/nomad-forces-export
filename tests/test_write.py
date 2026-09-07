from pathlib import Path

from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.db import connect
from ase.io import read

from src.nomad_forces_export.write import write_atoms


def _make_atoms(entry_id="e1", upload_id="u1"):
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]])
    atoms.calc = SinglePointCalculator(
        atoms, energy=-1.0, forces=[[0, 0, 0], [0, 0, 0]]
    )
    atoms.info["nomad_entry_id"] = entry_id
    atoms.info["nomad_upload_id"] = upload_id
    return atoms


def test_write_atoms_to_ase_db(tmp_path: Path):
    db_path = tmp_path / "dataset.db"
    atoms_list = [_make_atoms("e1"), _make_atoms("e2")]

    write_atoms(atoms_list, output_path=str(db_path), output_format="ase_db")

    with connect(str(db_path)) as db:
        rows = list(db.select())
    assert len(rows) == 2
    assert rows[0].nomad_entry_id == "e1"
    assert rows[1].nomad_entry_id == "e2"
    assert rows[0].toatoms().get_potential_energy() == -1.0


def test_write_atoms_to_extxyz(tmp_path: Path):
    xyz_path = tmp_path / "dataset.extxyz"
    atoms_list = [_make_atoms("e1"), _make_atoms("e2")]

    write_atoms(atoms_list, output_path=str(xyz_path), output_format="extxyz")

    read_atoms = read(str(xyz_path), index=":")
    assert len(read_atoms) == 2
    assert read_atoms[0].info["nomad_entry_id"] == "e1"
    assert read_atoms[0].get_potential_energy() == -1.0


def test_write_atoms_to_both_formats(tmp_path: Path):
    base_path = tmp_path / "dataset"
    atoms_list = [_make_atoms("e1")]

    write_atoms(
        atoms_list, output_path=str(base_path), output_format=["ase_db", "extxyz"]
    )

    assert (tmp_path / "dataset.db").exists()
    assert (tmp_path / "dataset.xyz").exists()


def test_write_atoms_rejects_unknown_format(tmp_path: Path):
    try:
        write_atoms(
            [_make_atoms()], output_path=str(tmp_path / "x"), output_format="bogus"
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
