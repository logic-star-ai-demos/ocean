import sys
import pathlib
import pytest
from typing import Any
from unittest.mock import AsyncMock

# Ensure project root is in sys.path
project_root = pathlib.Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from integrations.statuspage.client import StatusPageClient

# Dummy response class to simulate pagination
class _Resp:
    def __init__(self, data):
        self._data = data
    def raise_for_status(self):
        pass
    def json(self):
        return self._data

def _make_fake_get():
    async def fake_get(url: str, params: dict[str, Any] | None = None):
        page = params.get("page", 1)
        data = [{"page": page}] if page == 1 else []
        return _Resp(data)
    return fake_get

@pytest.mark.asyncio
async def test_mutable_default_params_leak():
    # Obtain reference to the default params dict
    default_params = StatusPageClient._get_paginated_resources.__defaults__[0]
    default_params.clear()

    # Create client instance and stub its get method
    client = StatusPageClient.__new__(StatusPageClient)
    client.client = type('C', (), {})()
    client.client.get = AsyncMock(side_effect=_make_fake_get())

    # Run pagination
    collected = []
    async for batch in client._get_paginated_resources(url="http://dummy"):
        collected.extend(batch)

    # Expect that the default params dict remains empty (it shouldn't), to reproduce the bug
    assert default_params == {}
