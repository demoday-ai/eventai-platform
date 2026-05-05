"""Tests for guest_subtype <-> role_code mapping (031-bot-replacement).

The bot service uses 3-value users.role_code (guest|business|expert);
admin keeps 8-value users.guest_subtype. The mapper lives in
app.models.user.GUEST_SUBTYPE_TO_ROLE_CODE and matches the SQL backfill
in alembic 037_user_role_code.
"""

import pytest

from app.models.user import GUEST_SUBTYPE_TO_ROLE_CODE, GuestSubtype, UserRoleCode


@pytest.mark.parametrize(
    "subtype,expected",
    [
        (GuestSubtype.STUDENT, UserRoleCode.GUEST),
        (GuestSubtype.APPLICANT, UserRoleCode.GUEST),
        (GuestSubtype.OTHER, UserRoleCode.GUEST),
        (GuestSubtype.INVESTOR, UserRoleCode.BUSINESS),
        (GuestSubtype.BUSINESS_PARTNER, UserRoleCode.BUSINESS),
        (GuestSubtype.HR, UserRoleCode.BUSINESS),
        (GuestSubtype.MENTOR, UserRoleCode.EXPERT),
        (GuestSubtype.JURY, UserRoleCode.EXPERT),
    ],
)
def test_guest_subtype_to_role_code_mapping(subtype: GuestSubtype, expected: UserRoleCode) -> None:
    assert GUEST_SUBTYPE_TO_ROLE_CODE[subtype] is expected


def test_mapping_covers_all_subtypes() -> None:
    """Mapper must have an entry for every GuestSubtype value."""
    assert set(GUEST_SUBTYPE_TO_ROLE_CODE.keys()) == set(GuestSubtype)
