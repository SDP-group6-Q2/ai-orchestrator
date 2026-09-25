from types import SimpleNamespace

import pytest

from src.graph import check_access


def _runtime(visibility):
    return SimpleNamespace(context=SimpleNamespace(visibility=visibility))


@pytest.mark.parametrize(
    "intent, visibility, denied",
    [
        ("commercial", "full", False),
        ("commercial", "commercial", False),
        ("commercial", "technician", True),
        ("technical", "technician", False),
        ("technical", "commercial", False),  # machine identity and manuals are visible to every tier
        ("technical", "full", False),
        ("technical", None, True),
        ("commercial", None, True),
        ("out_of_scope", "technician", False),
    ],
)
def test_gate(intent, visibility, denied):
    result = check_access({"intent": intent, "messages": []}, _runtime(visibility))
    assert result == ({"intent": "access_denied"} if denied else {})
