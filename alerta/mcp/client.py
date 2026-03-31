from typing import Any

import httpx

from alerta.mcp.config import ALERTA_API_KEY, ALERTA_API_URL


class AlertaClient:

    def __init__(self, base_url: str = ALERTA_API_URL, api_key: str = ALERTA_API_KEY):
        headers = {}
        if api_key:
            headers['X-API-Key'] = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip('/'),
            headers=headers,
            timeout=30.0,
        )

    async def get(self, path: str, params: dict | list | None = None) -> dict[str, Any]:
        resp = await self.client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: dict | None = None) -> tuple[dict[str, Any], int]:
        resp = await self.client.post(path, json=json)
        resp.raise_for_status()
        return resp.json(), resp.status_code

    async def put(self, path: str, json: dict | None = None, params: dict | list | None = None) -> dict[str, Any]:
        resp = await self.client.put(path, json=json, params=params)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str, params: dict | list | None = None) -> dict[str, Any]:
        resp = await self.client.delete(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()
