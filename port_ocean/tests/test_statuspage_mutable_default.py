import asyncio
from typing import Any, List

import pytest

from integrations.statuspage.client import StatusPageClient


class _DummyResponse:
    """Mimimal stub emulating an HTTPX response object."""

    def __init__(self, data: list[dict[str, Any]]):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class _DummyHTTPClient:
    """Captures the *identity* of the params dict passed on every call."""

    def __init__(self):
        self.param_ids: List[int] = []

    async def get(self, url: str, params: dict[str, Any] | None = None):  # noqa: D401
        # Record the *object id* (memory address) of the dict received.
        self.param_ids.append(id(params))
        # Only the first page returns data so that the paginator stops afterwards.
        data = [1] if params and params.get("page") == 1 else []
        return _DummyResponse(data)


async def _consume(client_instance: StatusPageClient):
    """Helper that exhausts the paginator once."""
    async for _ in client_instance._get_paginated_resources("/ignored"):
        pass


@pytest.mark.asyncio
async def test_get_paginated_resources_uses_fresh_params_dict_each_time():
    """Calling the paginator twice *should* use a *new* params dict every time.

    Unfortunately, because the implementation uses a mutable dict as the
    default value, both invocations reuse the same object.  This test documents
    the bug by asserting the _expected_ behaviour (different object ids), which
    currently fails.
    """

    dummy_http = _DummyHTTPClient()

    # Construct StatusPageClient instance without executing its real __init__.
    sp_client: StatusPageClient = StatusPageClient.__new__(StatusPageClient)
    sp_client.client = dummy_http

    # First run – collects the id of the params dict used internally.
    await _consume(sp_client)
    first_id = dummy_http.param_ids[0]

    # Reset recorder and run again.
    dummy_http.param_ids.clear()
    await _consume(sp_client)
    second_id = dummy_http.param_ids[0]

    # Expectation: the paginator should create a fresh params dict each call.
    # Reality: they are identical, so this assertion currently FAILS.
    assert first_id != second_id, (
        "_get_paginated_resources re-used the same default `params` dict between "
        "invocations, demonstrating the mutable-default bug."
    )
