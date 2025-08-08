import pytest

try:
    from integrations.firehydrant.utils import ObjectKind  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    # Support running tests from within the integrations/firehydrant directory
    from utils import ObjectKind  # type: ignore


def test_object_kind_includes_team():
    """Ensure that the FireHydrant ObjectKind enum includes the TEAM object type.

    The current business requirements state that FireHydrant *teams* should be
    ingested. This translates to having a `TEAM` member on the ObjectKind enum.
    The test fails when this member is absent, reproducing the reported issue.
    """
    assert "TEAM" in ObjectKind.__members__, (
        "ObjectKind is missing the TEAM member expected for team ingestion."
    )
