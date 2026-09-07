"""nomad_forces_export: fetch and package NOMAD data for MLIP fine-tuning."""

import json
from pathlib import Path
from typing import List, Optional, Set, Union

from loguru import logger

from nomad_forces_export.api import NomadClient
from nomad_forces_export.extract import to_atoms
from nomad_forces_export.query import NomadQuery
from nomad_forces_export.write import write_atoms

# logger = logging.getLogger(__name__)

__all__ = [
    "NomadQuery",
    "atoms_generator",
    "create_dataset_from_archives",
    "fetch_dataset",
    "write_atoms",
]


def atoms_generator(archives, properties):
    n_frames = 0
    n_entries_skipped = 0
    entries_processed = 0

    def _atoms_from_entry(archive_entry: dict):
        nonlocal n_frames, n_entries_skipped, entries_processed
        frames_for_entry = 0
        for atoms in to_atoms(archive_entry, properties=properties):
            frames_for_entry += 1
            yield atoms
        frames_for_entry = bool(frames_for_entry)
        n_entries_skipped += not frames_for_entry
        entries_processed += frames_for_entry
        n_frames += frames_for_entry

    try:
        for archive_entry in archives:
            yield from _atoms_from_entry(archive_entry)
    except Exception as e:
        import traceback

        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error(f"Error occurred while processing entries: {e}")
    logger.info(
        f"Extracted {n_frames} frames from {entries_processed} entries; {n_entries_skipped} entries had no usable frames for requested properties. Total entries processed: {n_entries_skipped + entries_processed}."
    )


def fetch_dataset(
    query: NomadQuery,
    properties: set[str],
    output_format: str | list[str],
    output_path: str,
    max_entries: int | None = None,
    batch_size: int = 50,
    client: NomadClient | None = None,
) -> None:
    """Fetch entries matching `query` from NOMAD and write them as a dataset.

    Searches NOMAD for matching entry_ids (respecting `query.exclude_datasets`),
    fetches full archive data in batches, extracts one `ase.Atoms` per calculation
    frame with the requested `properties`, and writes the result to `output_path`
    in the given `output_format` ("ase_db", "extxyz", or a list of both).
    """
    client = client or NomadClient()
    entry_ids = list(
        query.search(
            client=client,
            max_entries=max_entries,
            properties=properties,
        )
    )
    logger.info(
        f"found {len(entry_ids)} matching entries after dataset exclusion filtering"
    )
    archives = query.fetch_archives(
        client=client, entry_ids=entry_ids, batch_size=batch_size
    )
    logger.info(f"Fetching {len(entry_ids)} entries in batches of {batch_size}...")
    write_atoms(
        atoms_generator(archives, properties=properties),
        output_path=output_path,
        output_format=output_format,
    )


def create_dataset_from_archives(
    archives: list[dict] | str | Path,
    properties: set[str],
    output_format: str | list[str],
    output_path: str,
) -> None:
    """Create a dataset from a list of NOMAD archive entries.

    Extracts one `ase.Atoms` per calculation frame with the requested `properties`,
    and writes the result to `output_path` in the given `output_format`
    ("ase_db", "extxyz", or a list of both).
    """
    if isinstance(archives, (str, Path)):
        entries = []
        if isinstance(archives, str):
            archives = Path(archives)
        if archives.is_dir():
            for file in Path(archives).glob("*.json"):
                with open(file) as f:
                    entries.append(json.load(f))
        elif archives.is_file():
            with open(archives) as f:
                entries = json.load(f)
    else:
        entries = archives
    write_atoms(
        atoms_generator(entries, properties=properties),
        output_path=output_path,
        output_format=output_format,
    )
