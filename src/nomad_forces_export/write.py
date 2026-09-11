"""Write ase.Atoms iterables to ASE-DB and/or extxyz files on disk."""

import os
from collections.abc import Iterable

from ase import Atoms
from ase.db import connect
from ase.io import write as ase_write

from nomad_forces_export.config import VALID_FORMATS


def _path_for_format(output_path: str, output_format: str) -> str:
    root, ext = os.path.splitext(output_path)
    if ext not in ('.db', '.xyz', '.extxyz'):
        root = output_path
    if output_format == 'ase_db':
        return output_path if ext == '.db' else f'{root}.db'
    if output_format == 'extxyz':
        return output_path if ext in ('.xyz', '.extxyz') else f'{root}.xyz'
    raise ValueError(f'Unknown output format: {output_format}')


def write_atoms(
    atoms_iter: Iterable[Atoms],
    output_path: str,
    output_format: str | list[str],
) -> None:
    """Write `atoms_iter` to disk in one or more formats.

    `output_format` is `"ase_db"`, `"extxyz"`, or a list containing both. When a
    list is given, `output_path`'s extension is replaced per-format (e.g.
    `"dataset"` becomes `dataset.db` and `dataset.extxyz`).
    """
    formats = [output_format] if isinstance(output_format, str) else list(output_format)
    unknown = set(formats) - VALID_FORMATS
    if unknown:
        raise ValueError(f'Unknown output format(s): {sorted(unknown)}')

    atoms_list = list(atoms_iter)

    if 'ase_db' in formats:
        db_path = _path_for_format(output_path, 'ase_db')
        if os.path.exists(db_path):
            os.remove(db_path)
        with connect(db_path) as db:
            for atoms in atoms_list:
                key_value_pairs = {
                    'nomad_entry_id': atoms.info.get('nomad_entry_id', ''),
                    'nomad_upload_id': atoms.info.get('nomad_upload_id', ''),
                }
                db.write(atoms, key_value_pairs=key_value_pairs, data=atoms.info)

    if 'extxyz' in formats:
        xyz_path = _path_for_format(output_path, 'extxyz')
        if os.path.exists(xyz_path):
            os.remove(xyz_path)
        for atoms in atoms_list:
            ase_write(xyz_path, atoms, format='extxyz', append=True)
