import json
from pathlib import Path
from unittest.mock import Mock

from src.nomad_forces_export.query import NomadQuery

FIXTURES = Path(__file__).parent / 'fixtures'


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def test_build_query_dict_from_kwargs():
    q = NomadQuery(elements=['Si', 'O'])
    assert q.to_query_dict()['results.material.elements'] == {'all': ['Si', 'O']}


def test_build_query_dict_merges_formula_and_method():
    q = NomadQuery(elements=['Si'], formula='SiO2', method='dft')
    query_dict = q.to_query_dict()
    assert query_dict['results.material.elements'] == {'all': ['Si']}
    assert query_dict['results.material.chemical_formula_hill'] == 'SiO2'
    assert query_dict['results.method.method_name'] == 'dft'


def test_build_query_dict_with_entry_ids_ignores_other_filters():
    q = NomadQuery(elements=['Si'], entry_ids=['abc', 'def'])
    assert q.to_query_dict() == {'entry_id': {'any': ['abc', 'def']}}


def test_build_query_dict_raw_query_is_merged():
    q = NomadQuery(
        elements=['Si'], raw_query={'upload_create_time': {'gte': '2020-01-01'}}
    )
    query_dict = q.to_query_dict()
    assert query_dict['results.material.elements'] == {'all': ['Si']}
    assert query_dict['upload_create_time'] == {'gte': '2020-01-01'}


def test_search_filters_out_excluded_datasets():
    mock_client = Mock()
    mock_client.post.return_value = _load('search_response_sample.json')

    q = NomadQuery(
        elements=['Si', 'O'], exclude_datasets=['Alexandria'], client=mock_client
    )
    entry_ids = list(q.search(max_entries=3))

    # Both "Alexandria PBEsol" and "Alexandria PBE" entries should be excluded;
    # only the entry with no dataset survives.
    assert entry_ids == ['--BdNTN5GwvFlUVtm9di4rRQ6of2']


def test_search_with_no_exclusions_keeps_all_entries():
    mock_client = Mock()
    mock_client.post.return_value = _load('search_response_sample.json')

    q = NomadQuery(elements=['Si', 'O'], client=mock_client)
    entry_ids = list(q.search(max_entries=3))

    assert entry_ids == [
        '--0TXFv_aZUPi2bqjewWq3CTSGfc',
        '--BdNTN5GwvFlUVtm9di4rRQ6of2',
        '--CP5Me2LwNQFLrq84mPoCnL7Hj1',
    ]


def test_search_respects_max_entries_mid_page():
    mock_client = Mock()
    mock_client.post.return_value = {
        'data': [
            {'entry_id': 'id1', 'upload_id': 'u1'},
            {'entry_id': 'id2', 'upload_id': 'u1'},
            {'entry_id': 'id3', 'upload_id': 'u1'},
        ],
        'pagination': {'next_page_after_value': 'cursor_a'},
    }

    q = NomadQuery(elements=['Si'], client=mock_client)
    entry_ids = list(q.search(max_entries=2))

    assert entry_ids == ['id1', 'id2']
    assert mock_client.post.call_count == 1


def test_fetch_archives_batches_entry_ids_and_yields_archives():
    mock_client = Mock()
    mock_client.post.return_value = {
        'data': [
            {
                'entry_id': 'id1',
                'upload_id': 'u1',
                'archive': {'run': [{'system': []}]},
            },
            {
                'entry_id': 'id2',
                'upload_id': 'u2',
                'archive': {'run': [{'system': []}]},
            },
        ]
    }

    q = NomadQuery(elements=['Si'], client=mock_client)
    archives = list(q.fetch_archives(entry_ids=['id1', 'id2'], batch_size=50))

    assert [a['entry_id'] for a in archives] == ['id1', 'id2']
    called_payload = mock_client.post.call_args.args[1]
    assert called_payload['query'] == {'entry_id': {'any': ['id1', 'id2']}}
    assert called_payload['required']['run']['system']['atoms'] == '*'
    assert called_payload['required']['run']['calculation']['energy'] == '*'
    assert called_payload['required']['run']['calculation']['forces'] == '*'
    assert called_payload['required']['run']['calculation']['stress'] == '*'
    assert called_payload['required']['run']['calculation']['system_ref'] == '*'


def test_fetch_archives_splits_into_multiple_batches():
    mock_client = Mock()
    mock_client.post.return_value = {'data': []}

    q = NomadQuery(elements=['Si'], client=mock_client)
    entry_ids = [f'id{i}' for i in range(5)]
    list(q.fetch_archives(entry_ids=entry_ids, batch_size=2))

    assert mock_client.post.call_count == 3  # batches of 2, 2, 1
