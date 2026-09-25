"""nomad_forces_export: fetch and package NOMAD data for MLIP fine-tuning."""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import List, Optional, Set, Union

from loguru import logger

from nomad_forces_export.api import NomadClient
from nomad_forces_export.extract import to_atoms
from nomad_forces_export.query import NomadQuery
from nomad_forces_export.write import write_atoms

# logger = logging.getLogger(__name__)

__all__ = [
    'NomadQuery',
    'atoms_generator',
    'create_dataset_from_archives',
    'fetch_dataset',
    'fetch_dataset_one_call',
    'write_atoms',
]


def atoms_generator(archives, properties, max_frames: int | None = None):
    n_frames = 0
    n_entries_skipped = 0
    entries_processed = 0

    def _atoms_from_entry(archive_entry: dict):
        nonlocal n_frames, n_entries_skipped, entries_processed
        frames_for_entry = 0
        for atoms in to_atoms(archive_entry, properties=properties):
            frames_for_entry += 1
            yield atoms
            n_frames += 1
            if max_frames is not None and n_frames >= max_frames:
                logger.info(
                    f'Maximum number of frames ({max_frames}) reached; stopping extraction.'
                )
                entries_processed += 1
                return
        frames_for_entry = bool(frames_for_entry)
        n_entries_skipped += not frames_for_entry
        entries_processed += frames_for_entry

    try:
        for archive_entry in archives:
            yield from _atoms_from_entry(archive_entry)
            if max_frames is not None and n_frames >= max_frames:
                break
    except Exception as e:
        import traceback

        logger.error(f'Traceback:\n{traceback.format_exc()}')
        logger.error(f'Error occurred while processing entries: {e}')
    logger.info(
        f'Extracted {n_frames} frames from {entries_processed} entries; {n_entries_skipped} entries had no usable frames for requested properties. Total entries processed: {n_entries_skipped + entries_processed}.'
    )


def fetch_dataset(
    query: NomadQuery,
    properties: set[str],
    output_format: str | list[str],
    output_path: str,
    max_entries: int | None = None,
    max_frames: int | None = None,
    batch_size: int = 50,
    use_nomad_pkg: bool = False,
) -> None:
    """Fetch entries matching `query` from NOMAD and write them as a dataset.

    Searches NOMAD for matching entry_ids (respecting `query.exclude_datasets`),
    fetches full archive data in batches, extracts one `ase.Atoms` per calculation
    frame with the requested `properties`, and writes the result to `output_path`
    in the given `output_format` ("ase_db", "extxyz", or a list of both).
    """
    if use_nomad_pkg:
        search = query.search_nomad
        fetch_archives = query.fetch_archives_nomad
    else:
        search = query.search
        fetch_archives = query.fetch_archives
    entry_ids = list(
        search(
            max_entries=max_entries,
            properties=properties,
        )
    )
    logger.info(
        f'found {len(entry_ids)} matching entries after dataset exclusion filtering'
    )
    logger.info(f'Fetching {len(entry_ids)} entries in batches of {batch_size}...')
    archives = fetch_archives(entry_ids=entry_ids, batch_size=batch_size)
    write_atoms(
        atoms_generator(archives, properties=properties, max_frames=max_frames),
        output_path=output_path,
        output_format=output_format,
    )


def fetch_dataset_one_call(
    query: NomadQuery,
    properties: set[str],
    output_format: str | list[str],
    output_path: str,
    max_entries: int | None = None,
    max_frames: int | None = None,
    batch_size: int = 50,
    # use_nomad_pkg: bool = False,
) -> None:
    """Fetch entries matching `query` from NOMAD and write them as a dataset.

    Searches NOMAD for matching entry_ids (respecting `query.exclude_datasets`),
    fetches full archive data in batches, extracts one `ase.Atoms` per calculation
    frame with the requested `properties`, and writes the result to `output_path`
    in the given `output_format` ("ase_db", "extxyz", or a list of both).
    """

    search_and_fetch_archives = query.search_and_fetch_archives
    archives = search_and_fetch_archives(
        max_entries=max_entries,
        properties=properties,
        batch_size=batch_size,
    )
    write_atoms(
        atoms_generator(archives, properties=properties, max_frames=max_frames),
        output_path=output_path,
        output_format=output_format,
    )


def create_dataset_from_archives(
    archives: list[dict] | Iterable[dict] | str | Path,
    properties: set[str],
    output_format: str | list[str],
    output_path: str,
    max_frames: int | None = None,
) -> None:
    """Create a dataset from a list of NOMAD archive entries.

    Extracts one `ase.Atoms` per calculation frame with the requested `properties`,
    and writes the result to `output_path` in the given `output_format`
    ("ase_db", "extxyz", or a list of both).
    """

    def _yield_archives(
        archives: list[dict] | Iterable[dict] | str | Path,
    ) -> Iterator[dict]:
        if isinstance(archives, (str, Path)):
            entries = []
            if isinstance(archives, str):
                archives = Path(archives)
            if archives.is_dir():
                for file in Path(archives).glob('*.json'):
                    with open(file) as f:
                        entry = json.load(f)
                        yield entry
            elif archives.is_file():
                with open(archives) as f:
                    entries = json.load(f)
                if isinstance(entries, dict):
                    entries = [entries]
                for entry in entries:
                    yield entry
        else:
            for entry in archives:
                yield entry

    archives_iterable = _yield_archives(archives)
    write_atoms(
        atoms_generator(
            archives_iterable, properties=properties, max_frames=max_frames
        ),
        output_path=output_path,
        output_format=output_format,
    )
