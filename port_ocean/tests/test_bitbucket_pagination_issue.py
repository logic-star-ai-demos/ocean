import asyncio
import sys
import pathlib
import pytest

# Ensure the Bitbucket integration package is importable
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
INTEGRATION_PATH = PROJECT_ROOT / "integrations" / "bitbucket-cloud"
sys.path.insert(0, str(INTEGRATION_PATH))

from bitbucket_cloud.client import BitbucketClient  # type: ignore  # noqa: E402


@pytest.mark.asyncio
async def test_bitbucket_paginated_fetch_gets_all_pages():
    """Regression test for missing pagination handling (GH issue reference).

    The client must follow the `next` link without re-sending the original query
    parameters.  The mocked API below returns a second page *only* when the
    parameters are omitted – mirroring the real failure mode against Bitbucket
    Cloud.  Current buggy implementation keeps passing the params, thus only
    the first page is processed and this test fails.
    """

    # Bypass __init__ so we do not need real credentials / HTTP client
    client = BitbucketClient.__new__(BitbucketClient)  # type: ignore
    client.base_url = "http://dummy"

    calls: list[tuple[str, dict | None]] = []

    async def fake_send_api_request(url: str, *, params=None, method="GET"):
        calls.append((url, params))
        if len(calls) == 1:
            # First page advertises a following page
            return {"values": [1], "next": "http://dummy/page2"}
        # Second request: if params are still present the server responds empty
        if params is not None:
            return {"values": [], "next": None}
        # Correct behaviour (no params) returns final data
        return {"values": [2], "next": None}

    # Patch the network call
    client._send_api_request = fake_send_api_request  # type: ignore

    collected: list[int] = []
    async for batch in client._send_paginated_api_request("http://dummy/repositories/ws"):
        collected.extend(batch)

    # Expect both pages to be fetched. The bug causes only the first page (value 1).
    assert collected == [1, 2], (
        "Pagination did not follow second page. Expected [1, 2] but got "
        f"{collected}. Calls made: {calls}"
    )
