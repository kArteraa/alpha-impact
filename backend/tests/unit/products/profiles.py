import datetime as dt

from shared.contracts.schemas import ClientProfile, Feature

UPDATED_AT = dt.datetime(2026, 10, 20, tzinfo=dt.UTC)


def make_profile(flags: dict[str, bool], cl_type: str = "CLIENT") -> ClientProfile:
    return ClientProfile(
        client_id="client",
        group_id=None,
        group_members=[],
        features={
            "cl_type": Feature(value=cl_type, source="bank", confidence=1.0, updated_at=UPDATED_AT)
        },
        exposures={},
        flags=flags,
        version=1,
    )
