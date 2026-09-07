from unittest.mock import Mock, patch

import requests

from src.nomad_forces_export.api import NomadClient


def _mock_response(json_data, status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = Mock()
    if status_code >= 400:
        error = requests.HTTPError(f"status {status_code}")
        error.response = resp
        resp.raise_for_status.side_effect = error
    return resp


def test_post_returns_json_on_success():
    client = NomadClient()
    with patch("src.nomad_forces_export.api.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"data": [{"entry_id": "abc"}]})
        result = client.post("/entries/query", {"query": {}})
    assert result == {"data": [{"entry_id": "abc"}]}
    mock_post.assert_called_once()


def test_post_retries_on_transient_error_then_succeeds():
    client = NomadClient(max_retries=3, backoff_seconds=0)
    responses = [
        _mock_response({}, status_code=503),
        _mock_response({"data": []}, status_code=200),
    ]
    with patch("src.nomad_forces_export.api.requests.post", side_effect=responses):
        result = client.post("/entries/query", {"query": {}})
    assert result == {"data": []}


def test_post_raises_after_exhausting_retries():
    client = NomadClient(max_retries=2, backoff_seconds=0)
    error_response = _mock_response({}, status_code=503)
    with patch(
        "src.nomad_forces_export.api.requests.post", return_value=error_response
    ):
        try:
            client.post("/entries/query", {"query": {}})
            assert False, "expected requests.HTTPError"
        except requests.HTTPError:
            pass


def test_post_does_not_retry_on_4xx_error():
    client = NomadClient(max_retries=3, backoff_seconds=0)
    error_response = _mock_response({}, status_code=404)
    with patch(
        "src.nomad_forces_export.api.requests.post", return_value=error_response
    ) as mock_post:
        try:
            client.post("/entries/query", {"query": {}})
            assert False, "expected requests.HTTPError"
        except requests.HTTPError:
            pass
    mock_post.assert_called_once()
