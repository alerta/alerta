import os
from typing import Any
from uuid import uuid4

import pytest

CONTRACT_URL = os.environ.get('ALERTA_CONTRACT_URL')
CONTRACT_API_KEY = os.environ.get('ALERTA_CONTRACT_API_KEY')


class Response:

    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self.json = body


class InProcessClient:

    def __init__(self) -> None:
        from alerta.app import create_app
        app = create_app({'TESTING': True, 'AUTH_REQUIRED': False})
        self._client = app.test_client()

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Response:
        r = self._client.open(path, method=method, json=body)
        return Response(r.status_code, r.get_json(silent=True))

    def raw(self, method: str, path: str) -> tuple[int, bytes]:
        r = self._client.open(path, method=method)
        return r.status_code, r.data


class HttpClient:

    def __init__(self, base_url: str, api_key: str | None) -> None:
        import requests
        self._base_url = base_url.rstrip('/')
        self._session = requests.Session()
        if api_key:
            self._session.headers['Authorization'] = f'Key {api_key}'

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Response:
        r = self._session.request(method, self._base_url + path, json=body, timeout=10)
        try:
            payload = r.json()
        except ValueError:
            payload = None
        return Response(r.status_code, payload)

    def raw(self, method: str, path: str) -> tuple[int, bytes]:
        r = self._session.request(method, self._base_url + path, timeout=10)
        return r.status_code, r.content


class Api:

    def __init__(self, client) -> None:
        self._client = client
        self._created: list[str] = []

    def get(self, path: str) -> Response:
        return self._client.request('GET', path)

    def post(self, path: str, body: dict[str, Any]) -> Response:
        r = self._client.request('POST', path, body)
        if r.status in (200, 201) and isinstance(r.json, dict) and 'id' in r.json:
            kind = path.strip('/').split('/')[0]
            self._created.append(f"/{kind}/{r.json['id']}")
        return r

    def put(self, path: str, body: dict[str, Any]) -> Response:
        return self._client.request('PUT', path, body)

    def delete(self, path: str) -> Response:
        return self._client.request('DELETE', path)

    def raw(self, method: str, path: str) -> tuple[int, bytes]:
        return self._client.raw(method, path)

    def cleanup(self) -> None:
        for path in reversed(self._created):
            self._client.request('DELETE', path)
        self._created.clear()


@pytest.fixture(scope='session')
def client():
    if CONTRACT_URL:
        return HttpClient(CONTRACT_URL, CONTRACT_API_KEY)
    return InProcessClient()


@pytest.fixture
def api(client):
    api = Api(client)
    yield api
    api.cleanup()


@pytest.fixture
def resource() -> str:
    return f'contract-{uuid4().hex[:12]}'


@pytest.fixture
def alert(resource) -> dict[str, Any]:
    return {
        'resource': resource,
        'event': 'node_down',
        'environment': 'Production',
        'severity': 'major',
        'correlate': ['node_down', 'node_marginal', 'node_up'],
        'service': ['Network'],
        'group': 'Contract',
        'value': '0',
        'text': 'node is down',
        'tags': ['contract'],
        'attributes': {'region': 'eu-west-1'},
        'origin': 'contract-tests',
        'type': 'exceptionAlert',
        'timeout': 3600,
        'rawData': 'raw',
    }
