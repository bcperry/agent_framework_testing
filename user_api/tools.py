"""Agent tools that call the records API as the signed-in user.

The access token is captured in a closure and never exposed as a tool parameter.
The model decides *whether* to call these tools; it cannot decide *who it calls
them as*, and it has no way to widen the caller's permissions.
"""

import json
from typing import Annotated

import httpx

API_BASE_URL = "http://127.0.0.1:8099"


def make_records_tools(access_token: str, base_url: str = API_BASE_URL) -> list:
    """Build records tools bound to one user's access token."""
    headers = {"Authorization": f"Bearer {access_token}"}

    async def _get(path: str) -> str:
        async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
            response = await client.get(path, headers=headers)
        if response.status_code == 401:
            return "Denied (401): the access token is missing, expired, or invalid."
        if response.status_code == 403:
            return f"Denied (403): {response.json().get('detail', 'insufficient permissions')}"
        if response.status_code == 404:
            return f"Not found (404): {response.json().get('detail', 'no such record')}"
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)

    async def who_am_i() -> str:
        """Report the signed-in user's identity and what their permissions allow."""
        return await _get("/me")

    async def list_records() -> str:
        """List every record the signed-in user is permitted to see."""
        return await _get("/records")

    async def read_record(
        record_id: Annotated[str, "The record id, for example 'REC-002'."],
    ) -> str:
        """Read one record by id, if the signed-in user is permitted to see it."""
        return await _get(f"/records/{record_id}")

    return [who_am_i, list_records, read_record]
