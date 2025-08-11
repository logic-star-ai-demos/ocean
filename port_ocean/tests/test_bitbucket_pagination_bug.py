import os
import sys
import pytest

# Ensure the Bitbucket integration package is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
INTEGRATION_SRC = os.path.join(PROJECT_ROOT, "integrations", "bitbucket-cloud")
if INTEGRATION_SRC not in sys.path:
    sys.path.insert(0, INTEGRATION_SRC)

from bitbucket_cloud.client import BitbucketClient  # noqa: E402


class StubBitbucketClient(BitbucketClient):
    """Client stub that simulates the Bitbucket paginated API."""

    def __init__(self):  # pylint: disable=super-init-not-called
        self.base_url = "https://api.bitbucket.org/2.0"
        self.workspace = "demo"

    async def _send_api_request(self, url, params=None, method="GET", **_):  # type: ignore[override]
        """Simulated responses highlighting the pagination problem."""
        # Second page
        if "page=2" in url:
            # Buggy behaviour: if *params* is still present the API would repeat
            # the first page; we signal this by returning an empty "values".
            if params:
                return {"values": []}
            return {"values": [3]}

        # First page
        return {
            "values": [1, 2],
            "next": f"{self.base_url}/repositories/{self.workspace}?page=2",
        }


@pytest.mark.asyncio
async def test_fetch_paginated_api_fetches_all_pages():
    """`_fetch_paginated_api_with_rate_limiter` should iterate over *every* page.

    The current implementation keeps passing the original `params` dict on
    subsequent requests, causing pagination to stop after the first page. The
    complete result should be `[1, 2, 3]`, but only `[1, 2]` are returned –
    this assertion intentionally fails to reveal the issue.
    """

    client = StubBitbucketClient()
    collected: list[int] = []

    async for batch in client._fetch_paginated_api_with_rate_limiter(
        f"{client.base_url}/repositories/{client.workspace}"
    ):
        collected.extend(batch)

    assert collected == [1, 2, 3], (
        "Pagination should continue to subsequent pages; got partial result "
        f"{collected} instead."
    )
