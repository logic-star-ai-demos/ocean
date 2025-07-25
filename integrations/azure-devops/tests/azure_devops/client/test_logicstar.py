import pytest
from unittest.mock import patch, MagicMock
from typing import Any, AsyncGenerator, Dict, List, Optional
from azure_devops.client.azure_devops_client import AzureDevopsClient
from port_ocean.context.event import event_context

MOCK_ORG_URL = "https://your_organization_url.com"
MOCK_PERSONAL_ACCESS_TOKEN = "personal_access_token"

@pytest.mark.asyncio
async def test_generate_pull_requests_skips_disabled_repos():
    client = AzureDevopsClient(MOCK_ORG_URL, MOCK_PERSONAL_ACCESS_TOKEN)

    # Simulate both enabled and disabled repositories
    enabled_repo = {
        "id": "repo1",
        "name": "Enabled Repo",
        "isDisabled": False,
        "project": {"id": "proj1", "name": "Project One"},
    }
    disabled_repo = {
        "id": "repo2",
        "name": "Disabled Repo",
        "isDisabled": True,
        "project": {"id": "proj1", "name": "Project One"},
    }

    async def mock_generate_repositories(*args, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        yield [enabled_repo, disabled_repo]

    async def mock_get_paginated_by_top_and_skip(url: str, *args, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        if "repo2" in url:
            # If called for the disabled repo, raise an error to simulate the bug
            raise AssertionError("Should not fetch pull requests for disabled repositories!")
        # For enabled repo, return a dummy pull request
        yield [{"pullRequestId": "pr1", "repository": {"id": "repo1"}}]

    async with event_context("test_event"):
        with patch.object(client, "generate_repositories", side_effect=mock_generate_repositories):
            with patch.object(client, "_get_paginated_by_top_and_skip", side_effect=mock_get_paginated_by_top_and_skip):
                pull_requests = []
                async for pr_batch in client.generate_pull_requests():
                    pull_requests.extend(pr_batch)

    # Only pull requests from the enabled repo should be present
    assert pull_requests == [{"pullRequestId": "pr1", "repository": {"id": "repo1"}}]
