import pytest
from integrations.sonarqube.client import SonarQubeClient

@pytest.mark.asyncio
async def test_get_issues_by_component_does_not_leak_query_params(monkeypatch):
    """Calling get_issues_by_component twice should not leak state via the default query_params.

    The first call adds pagination keys to the shared dict; if the same dict is
    reused, the second call will receive these leftovers and the assertion
    below will fail. Once the bug is fixed (default changed to None), the test
    will pass because each call starts with a fresh dictionary.
    """

    # Bypass __init__ to avoid caring about its signature – we only need a few attributes.
    client = SonarQubeClient.__new__(SonarQubeClient)  # type: ignore[arg-type]
    client.is_onpremise = False  # attribute read by get_issues_by_component
    client.base_url = "https://sonarqube.example.com"  # used for __link construction

    captured_params: list[dict] = []

    async def fake_send_paginated_request(*, endpoint, data_key, query_params):  # noqa: D401,E501
        # Record a copy to avoid later mutations affecting the captured version
        captured_params.append(dict(query_params))
        # Emulate real side-effect: add page size so a leftover key will leak
        query_params["ps"] = 500
        yield []  # return an empty page so the caller terminates

    # Patch the helper method on our client instance
    monkeypatch.setattr(client, "_send_paginated_request", fake_send_paginated_request)

    # First invocation – populates shared default dict with pagination data
    async for _ in client.get_issues_by_component({"key": "COMP_A"}):
        pass

    # Second invocation – should start from a clean dict, but buggy code reuses it
    async for _ in client.get_issues_by_component({"key": "COMP_B"}):
        pass

    # Ensure we captured both calls
    assert len(captured_params) == 2, "Expected two calls to _send_paginated_request"

    # The first set of params should only include the component key initially
    assert captured_params[0] == {"componentKeys": "COMP_A"}

    # The second call must *not* already contain the 'ps' leftover – bug reveals itself here
    assert "ps" not in captured_params[1], (
        "Pagination key 'ps' leaked from the first invocation – shared mutable default detected."
    )
