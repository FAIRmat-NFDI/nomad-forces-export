"""Write ase.Atoms iterables to ASE-DB and/or extxyz files on disk."""

import contextlib
import os
import tarfile
from collections.abc import Iterable
from pathlib import Path

from ase import Atoms
from ase.db import connect
from ase.io import write as ase_write

from nomad_forces_export.config import EXTENSION_MAP, VALID_FORMATS

EXTENSIONS = ('.db', '.aselmdb', '.xyz', '.extxyz')

db_formats = {'ase_db', 'ase_lmdb'}


def _path_for_format(output_path: str, output_format: str) -> str:
    root, ext = os.path.splitext(output_path)
    if output_format not in VALID_FORMATS:
        raise ValueError(f'Unknown output format: {output_format}')
    if ext in EXTENSIONS:
        return output_path
    else:
        root = output_path
    return f'{root}{EXTENSION_MAP.get(output_format)}'


def write_atoms(
    atoms_iter: Iterable[Atoms],
    output_path: str,
    output_format: str | list[str],
) -> int:
    """Write `atoms_iter` to disk in one or more formats.

    `output_format` is `"ase_db"`, `"extxyz"`, or a list containing both. When a
    list is given, `output_path`'s extension is replaced per-format (e.g.
    `"dataset"` becomes `dataset.db` and `dataset.extxyz`).
    """
    formats = [output_format] if isinstance(output_format, str) else list(output_format)
    unknown = set(formats) - VALID_FORMATS
    if unknown:
        raise ValueError(f'Unknown output format(s): {sorted(unknown)}')

    atoms_list = []
    frames_written = 0
    out_paths = {}
    save_to_ase_lmdb = 'ase_lmdb' in formats
    save_to_extxyz = 'extxyz' in formats
    for fmt in formats:
        out_path = _path_for_format(output_path, fmt)
        out_paths[fmt] = out_path
        if os.path.exists(out_path):
            os.remove(out_path)

    with contextlib.ExitStack() as stack:
        print(out_paths)
        dbs = [
            stack.enter_context(connect(out_path))
            for fmt, out_path in out_paths.items()
            if fmt in db_formats
        ]
        xyz_files = (
            [stack.enter_context(open(out_paths['extxyz'], 'w'))]
            if save_to_extxyz
            else []
        )
        for atoms in atoms_iter:
            key_value_pairs = {
                'nomad_entry_id': atoms.info.get('nomad_entry_id', ''),
                # 'nomad_upload_id': atoms.info.get('nomad_upload_id', ''),
            }
            for db in dbs:
                db.write(atoms, key_value_pairs=key_value_pairs, data=atoms.info)
            for xyz_file in xyz_files:
                ase_write(xyz_file, atoms, format='extxyz', append=True)
            frames_written += 1
    if save_to_ase_lmdb:
        db_path = Path(out_paths['ase_lmdb'])
        lock_path = Path(str(db_path) + '-lock')
        # with tarfile.open(f'{db_path}.tar.gz', 'w:gz') as tar:
        #     tar.add(db_path, arcname=Path(db_path).name)

        #     if lock_path.exists():
        #         tar.add(lock_path, arcname=lock_path.name)
        # if db_path.exists():
        #     db_path.unlink(missing_ok=True)

        if lock_path.exists():
            lock_path.unlink(missing_ok=True)
    return len(atoms_list) if atoms_list else frames_written
