import pytest

from integrations.sonarqube.client import SonarQubeClient

PAGE_KEY = "p"


@pytest.mark.asyncio
async def test_get_issues_by_component_mutable_default(monkeypatch):
    """The default dict used by get_issues_by_component should not leak state
    between invocations. We patch the internal pagination helper so that it
    mutates the incoming query_params (exactly what the real implementation
    does). If two successive calls to get_issues_by_component share the same
    default dict, the second call will observe the mutation performed during
    the first call – which is the bug we want to surface.
    """

    captured: list[dict] = []

    async def fake_paginated(self, endpoint, data_key, query_params=None, **kwargs):  # type: ignore[override]
        # Record the *current* contents of query_params for later inspection
        captured.append(dict(query_params))
        # Emulate SonarQubeClient._send_paginated_request mutating the dict
        query_params[PAGE_KEY] = query_params.get(PAGE_KEY, 0) + 1
        # Yield a single empty page – content is irrelevant for this test
        yield []

    # Replace the real pagination helper with our controlled fake
    monkeypatch.setattr(SonarQubeClient, "_send_paginated_request", fake_paginated, raising=True)

    # Construct a bare SonarQubeClient instance without running its __init__
    client = SonarQubeClient.__new__(SonarQubeClient)  # type: ignore[call-arg]
    client.is_onpremise = True  # attribute accessed by get_issues_by_component
    client.base_url = "http://example.com"  # required for URL construction inside the method

    # First call (should start with a fresh, empty dict)
    async for _ in client.get_issues_by_component({"key": "project_one"}):
        pass

    # Second call (should again start with a fresh, empty dict)
    async for _ in client.get_issues_by_component({"key": "project_two"}):
        pass

    # We captured the query_params dict *before* our fake mutated it.
    # The second captured dict must not already contain the pagination key
    # introduced during the first invocation. If it does, the same dict
    # instance was reused – indicating the default-mutable-argument bug.
    assert len(captured) == 2, "Expected two separate pagination calls to be captured"
    assert PAGE_KEY not in captured[1], (
        "`get_issues_by_component` re-used its default `query_params` dict, "
        "causing state leakage between calls. The pagination key from the first "
        "call is unexpectedly present in the second call's parameters."
    )
