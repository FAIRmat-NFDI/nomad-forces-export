"""Build NOMAD search queries and list matching entry_ids, filtering excluded datasets."""

import os
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from loguru import logger

from nomad_forces_export.api import NomadClient
from nomad_forces_export.config import (
    BASE_QUERY,
    REQUIRED_ARCHIVE_DATA,
    REQUIRED_METADATA,
)


@dataclass
class NomadQuery:
    """Describes a NOMAD entries search.

    If `entry_ids` is given, it takes precedence over all other filters (elements,
    formula, method, raw_query) -- the query becomes a direct id lookup.
    """

    elements: list[str] | None = None
    formula: str | None = None
    method: str | None = None
    dft_xc_functionals: list[str] | None = None
    program: str | None = None
    entry_ids: list[str] | None = None
    exclude_datasets: list[str] = field(default_factory=list)
    raw_query: dict | None = None
    client: NomadClient | None = None

    def to_query_dict(self, properties: set[str] | None = None) -> dict:
        """Build the NOMAD query dict (the `query` field of an API request body)."""
        if self.entry_ids:
            return {'entry_id': {'any': list(self.entry_ids)}}

        query_dict: dict = BASE_QUERY.copy()

        for prop in properties or []:
            if prop not in {'energy', 'forces', 'stress'}:
                raise ValueError(f'Unknown property requested: {prop}')
            if prop == 'energy':
                query_dict['quantities:all'].append(
                    'run.calculation.energy.total_t0.value'
                )
            else:
                query_dict['quantities:all'].append(
                    f'run.calculation.{prop}.total.value'
                )
        if self.elements:
            query_dict['results.material.elements'] = {'all': list(self.elements)}
        if self.formula:
            query_dict['results.material.chemical_formula_hill'] = self.formula
        if self.method:
            query_dict['results.method.method_name'] = self.method
        if self.dft_xc_functionals:
            query_dict['results.method.simulation.dft.xc_functional_names:any'] = list(
                self.dft_xc_functionals
            )

        if self.program:
            query_dict['results.method.simulation.program_name'] = self.program
        if self.exclude_datasets:
            query_dict['datasets.dataset_name:none'] = list(self.exclude_datasets)
            query_dict['external_db:none'] = list(self.exclude_datasets)
        if self.raw_query:
            query_dict.update(self.raw_query)
        return query_dict

    def _is_excluded(self, entry: dict) -> bool:
        if not self.exclude_datasets:
            return False
        dataset_names = [d.get('dataset_name', '') for d in entry.get('datasets', [])]
        for excluded in self.exclude_datasets:
            for name in dataset_names:
                if excluded.lower() in name.lower():
                    return True
        return False

    def search(
        self,
        max_entries: int | None = None,
        properties: set[str] | None = None,
    ) -> Iterator[str]:
        """Yield entry_ids matching this query, skipping excluded datasets.

        Paginates through `/entries/query` using NOMAD's `page_after_value` cursor
        until no more pages remain, the cursor stops advancing, or `max_entries`
        yielded entry_ids is reached.
        """
        query_dict = self.to_query_dict(properties=properties)
        page_after_value = None
        yielded = 0
        page_size = min(10000, max_entries) if max_entries is not None else 10000
        client = self.client or NomadClient()
        while True:
            payload = {
                'query': query_dict,
                'pagination': {'page_size': page_size},
                'required': {'include': REQUIRED_METADATA},
            }
            if page_after_value:
                payload['pagination']['page_after_value'] = page_after_value

            response = client.post('/entries/query', payload)
            pagination = response.get('pagination', {})
            total_entries = pagination.get('total')
            logger.info(f'query returned total {total_entries})')
            next_page_after_value = pagination.get('next_page_after_value')

            # If the cursor returned for this page is identical to the cursor we
            # just requested with, the server (or a mock) is not making progress
            # (e.g. returning the same page repeatedly) -- stop before processing
            # this page's data to avoid re-yielding already-seen entries.
            if (
                page_after_value is not None
                and next_page_after_value == page_after_value
            ):
                return

            data = response.get('data', [])
            for entry in data:
                if self._is_excluded(entry):
                    continue
                yield entry['entry_id']
                yielded += 1
                if max_entries is not None and yielded >= max_entries:
                    return

            # Stop if there's no cursor or no data (no more pages).
            if not next_page_after_value or not data:
                return

            page_after_value = next_page_after_value

    def search_nomad(
        self,
        max_entries: int | None = None,
        properties: set[str] | None = None,
    ) -> Iterator[str]:
        """Yield entry_ids matching this query, skipping excluded datasets.

        Paginates through `/entries/query` using NOMAD's `page_after_value` cursor
        until no more pages remain, the cursor stops advancing, or `max_entries`
        yielded entry_ids is reached.
        """
        from nomad.app.v1.models.models import (
            MetadataRequired,
        )
        from nomad.client.archive import ArchiveQuery

        query_dict = self.to_query_dict(properties=properties)
        page_size = min(10000, max_entries) if max_entries is not None else 10000
        yielded = 0
        page_after_value = None

        while True:
            archive_query = ArchiveQuery(
                query=query_dict,
                required=MetadataRequired(include=REQUIRED_METADATA),  # type: ignore
                page_size=page_size,
                after=page_after_value,  # type: ignore
            )
            num_queries = archive_query.fetch()
            if num_queries == 0:
                return
            for entry in archive_query.entry_list():
                page_after_value = entry[0]
                yield entry[0]
                yielded += 1
                if max_entries is not None and yielded >= max_entries:
                    return

    def fetch_archives(
        self,
        entry_ids: Iterable[str],
        batch_size: int = 50,
        save_dir: str | None = None,
    ) -> Iterator[dict]:
        """Fetch full archive data (system + calculation sections) for `entry_ids`.

        Requests are batched (`batch_size` entry_ids per request) to keep payload
        sizes reasonable. Yields one archive dict (as returned in the response
        `data` list) per entry.
        """
        client = self.client or NomadClient()
        entry_ids = list(entry_ids)
        required = REQUIRED_ARCHIVE_DATA
        batch_size = min(batch_size, 1000)
        for i in range(0, len(entry_ids), batch_size):
            batch = entry_ids[i : i + batch_size]
            payload = {
                'query': {'entry_id': {'any': batch}},
                'required': required,
                'pagination': {'page_size': batch_size},
            }
            response = client.post('/entries/archive/query', payload)
            time.sleep(1)  # avoid overwhelming the server with back-to-back requests
            logger.info(
                f'Batch no {i // batch_size + 1}: {len(response.get("data", []))} archive entries.'
            )
            for archive_entry in response.get('data', []):
                if save_dir:
                    os.makedirs(f'{save_dir}/archives', exist_ok=True)
                    entry_id = archive_entry.get('entry_id')
                    if entry_id:
                        with open(
                            f'{save_dir}/archives/archive_{entry_id}.json', 'w'
                        ) as f:
                            import json

                            json.dump(archive_entry, f, indent=2)
                yield archive_entry

    def fetch_archives_nomad(
        self,
        entry_ids: Iterable[str],
        batch_size: int = 50,
        save_dir: str | None = None,
    ) -> Iterator[dict]:
        """Fetch full archive data (system + calculation sections) for `entry_ids`.

        Requests are batched (`batch_size` entry_ids per request) to keep payload
        sizes reasonable. Yields one archive dict (as returned in the response
        `data` list) per entry.
        """
        from nomad.client.archive import ArchiveQuery

        entry_ids = list(entry_ids)
        required = REQUIRED_ARCHIVE_DATA.copy()
        # required.pop(
        #     'workflow2', None
        # )  # workflow2 is not available in the nomad package
        for i in range(0, len(entry_ids), batch_size):
            batch = entry_ids[i : i + batch_size]
            query = {'entry_id': {'any': batch}}
            archive_query = ArchiveQuery(
                query=query,
                # required=required,
                page_size=batch_size,
                batch_size=batch_size,
            )
            number_of_entries = archive_query.fetch()
            logger.info(
                f'Batch no {i // batch_size + 1}: {number_of_entries} archive entries.'
            )
            archive_query._required = required
            archives = archive_query.download(as_plain_dict=True)
            for archive_entry in archives:
                archive = {
                    'entry_id': archive_entry['metadata']['entry_id'],
                    'upload_id': archive_entry['metadata']['upload_id'],
                    'archive': archive_entry,
                }
                if save_dir:
                    os.makedirs(f'{save_dir}/archives', exist_ok=True)
                    entry_id = archive_entry['metadata']['entry_id']
                    if entry_id:
                        with open(
                            f'{save_dir}/archives/archive_{entry_id}.json', 'w'
                        ) as f:
                            import json

                            json.dump(archive, f, indent=2)
                yield archive
