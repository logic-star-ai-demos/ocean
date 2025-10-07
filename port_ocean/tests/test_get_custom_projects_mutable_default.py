import pytest

from integrations.sonarqube.client import SonarQubeClient  # noqa: WPS433


@pytest.mark.asyncio
async def test_get_custom_projects_mutable_default_leak(monkeypatch):
    """The default `params={}` dict should not be shared across calls."""

    captured_params: list[dict] = []

    async def fake_paginated_request(*, query_params=None, **kwargs):  # type: ignore[return-value]
        # Store a copy of the dict that the production code passes in so that we
        # can inspect mutations performed by successive calls.
        captured_params.append(query_params.copy() if query_params is not None else None)
        # The real helper is an async generator – we mimic that behaviour.
        yield []

    # ---------------------------------------------------------------------
    # Build two independent SonarQubeClient instances without invoking their
    # heavy constructor. Only the attributes accessed by the method under test
    # are populated.
    # ---------------------------------------------------------------------
    client_with_org = SonarQubeClient.__new__(SonarQubeClient)  # type: ignore[arg-type]
    client_with_org.organization_id = "org1"  # type: ignore[attr-defined]
    monkeypatch.setattr(client_with_org, "_send_paginated_request", fake_paginated_request)

    client_without_org = SonarQubeClient.__new__(SonarQubeClient)  # type: ignore[arg-type]
    client_without_org.organization_id = None  # type: ignore[attr-defined]
    monkeypatch.setattr(client_without_org, "_send_paginated_request", fake_paginated_request)

    # ------------------------------------------------------------------
    # First call: the client with an organisation id populates the default
    # `params` dict with that id.
    # Second call: another client *without* an organisation id should not
    # inherit that value – but due to the shared default it currently does.
    # ------------------------------------------------------------------
    async for _ in client_with_org.get_custom_projects():
        pass
    async for _ in client_without_org.get_custom_projects():
        pass

    # Sanity-check that we captured both calls.
    assert len(captured_params) == 2

    first_call_params, second_call_params = captured_params

    # The issue: the second call unexpectedly contains the organisation from
    # the first call because the same dict instance is reused.
    # We expect the second call *not* to contain the key.
    assert "organization" not in second_call_params, (
        "The default params dictionary is shared between calls, "
        "leading to state leakage across different client instances."
    )
