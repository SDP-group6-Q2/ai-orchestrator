import pytest

from src.access import can_access_commercial_data, can_access_machine_identity, can_access_technical_data


@pytest.mark.parametrize(
    "visibility, commercial, technical, identity",
    [
        ("full", True, True, True),
        ("technician", False, True, True),
        ("commercial", True, False, True),
        (None, False, False, False),
        ("admin", False, False, False),
    ],
)
def test_tier_matrix(visibility, commercial, technical, identity):
    assert can_access_commercial_data(visibility) is commercial
    assert can_access_technical_data(visibility) is technical
    assert can_access_machine_identity(visibility) is identity
