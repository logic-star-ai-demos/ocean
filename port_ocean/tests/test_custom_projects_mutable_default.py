import pytest

from integrations.sonarqube.client import SonarQubeClient


@pytest.mark.asyncio
async def test_get_custom_projects_mutable_default_leak():
    """
    Verify that get_custom_projects does not leak the 'organization' param between calls.
    This should fail due to the mutable default parameter bug.
    """
    captured_params = []

    # Subclass to override _send_paginated_request and capture query_params
    class TestClient(SonarQubeClient):
        def __init__(self, organization_id=None):
            # Skip parent __init__, only set needed attrs
            self.organization_id = organization_id
            self.is_onpremise = False
            self.base_url = "http://example.com"

        async def _send_paginated_request(self, endpoint, data_key, method="GET", query_params=None):
            # Capture a shallow copy of the params dict
            captured_params.append(dict(query_params) if query_params is not None else {})
            # Yield one empty batch to drive the async loop
            yield []

    # First call: with organization_id
    client1 = TestClient(organization_id="org1")
    async for _ in client1.get_custom_projects():
        pass

    # Second call: without organization_id
    client2 = TestClient(organization_id=None)
    async for _ in client2.get_custom_projects():
        pass

    # Ensure we captured both calls
    assert len(captured_params) >= 2, "Expected two calls to _send_paginated_request"

    # Assert that second call did not include 'organization'
    second_params = captured_params[1]
    assert "organization" not in second_params, (
        f"Mutable default dict leaked organization: {second_params}"
    )
