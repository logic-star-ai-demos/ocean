"""Test that FireHydrant ObjectKind enum contains the missing `TEAM` member.

This reproduces the reported issue that teams are **not** ingested because the
`ObjectKind` enum lacks the corresponding `TEAM` value.  The test intentionally
fails until the enum is extended with `TEAM = "team"` (or the appropriate
string).
"""

import importlib
from types import ModuleType

# The module can be imported via two possible paths depending on test runner CWD
module: ModuleType
try:
    module = importlib.import_module("integrations.firehydrant.utils")
except ModuleNotFoundError:
    module = importlib.import_module("utils")  # type: ignore

ObjectKind = getattr(module, "ObjectKind")

def test_objectkind_contains_team():
    """`ObjectKind` should expose a `TEAM` member for FireHydrant teams."""
    assert hasattr(ObjectKind, "TEAM"), (
        "`TEAM` member is missing from integrations.firehydrant.utils.ObjectKind; "
        "FireHydrant teams cannot be ingested until this is added."
    )
