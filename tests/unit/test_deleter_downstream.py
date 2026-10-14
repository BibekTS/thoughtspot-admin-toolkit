"""
Downstream-mode resolution: the root is part of the deletion set.

A leaf root (liveboard/answer) has no dependents. When the root was excluded,
picking one produced an empty grid with no Delete button — the drawer had just
promised "only the root would be deleted". The root is now always returned,
first, so the UI can pre-select it and the admin can untick it to keep it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, create_engine

from ts_admin.models.cache.ts_metadata import CachedMetadata
from ts_admin.models.sync_log import SyncLog
from ts_admin.services.deletion_service import SYSTEM_OWNER_NAME

CLUSTER_ID = "c1"
ORG_ID = 0

# root guid → dependents the fake TS reports for it
DEPENDENTS: dict[str, list[dict]] = {
    "ws-1": [{"id": "lb-1", "type": "PINBOARD_ANSWER_BOOK"}, {"id": "ans-1", "type": "QUESTION_ANSWER_BOOK"}],
}


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import ts_admin.database as db_module

    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    db_module.init_db()

    now = datetime.now(tz=timezone.utc)
    with Session(engine) as s:
        for guid, otype, owner in [
            ("ws-1", "WORKSHEET", "Alice"),
            ("lb-1", "LIVEBOARD", "Alice"),
            ("ans-1", "ANSWER", "Alice"),
            ("lb-sys", "LIVEBOARD", SYSTEM_OWNER_NAME),
        ]:
            s.add(
                CachedMetadata(
                    cluster_id=CLUSTER_ID,
                    org_id=ORG_ID,
                    ts_guid=guid,
                    name=guid,
                    object_type=otype,
                    owner_guid="u",
                    owner_name=owner,
                    tag_names=json.dumps([]),
                    synced_at=now,
                )
            )
        s.add(SyncLog(cluster_id=CLUSTER_ID, org_id=ORG_ID, entity_type="metadata", status="SUCCESS", record_count=4))
        s.commit()
    return engine


@pytest.fixture(autouse=True)
def fake_ts(monkeypatch):
    from ts_admin.config import AppConfig, ClusterConfig
    from ts_admin.ts_client.models import AuthType

    cfg = ClusterConfig(
        id=CLUSTER_ID, name="Prod", url="https://prod.thoughtspot.cloud", username="admin", auth_type=AuthType.TRUSTED
    )
    monkeypatch.setattr(
        "ts_admin.config.load_config", lambda: AppConfig(clusters={CLUSTER_ID: cfg}, active_cluster_id=CLUSTER_ID)
    )
    monkeypatch.setattr("ts_admin.config.ClusterConfig.build_auth_strategy", lambda self, org_id=None: None)

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def fetch_dependents(self, *, objects):
            return {o["identifier"]: DEPENDENTS.get(o["identifier"], []) for o in objects}

    monkeypatch.setattr("ts_admin.ts_client.ThoughtSpotClient", FakeClient)


async def _resolve(root_guid: str, root_type: str) -> dict:
    from ts_admin.services import deleter_service

    return await deleter_service.resolve_downstream(
        root_guid=root_guid, root_type=root_type, cluster_id=CLUSTER_ID, org_id=ORG_ID
    )


@pytest.mark.anyio
async def test_leaf_root_resolves_to_itself():
    """The reported bug: a liveboard root must still yield something to delete."""
    res = await _resolve("lb-1", "LIVEBOARD")
    assert [i["ts_guid"] for i in res["items"]] == ["lb-1"]
    assert res["total"] == 1
    assert res["by_type"] == {"LIVEBOARD": 1}


@pytest.mark.anyio
async def test_root_is_listed_first_with_its_dependents():
    res = await _resolve("ws-1", "WORKSHEET")
    guids = [i["ts_guid"] for i in res["items"]]
    assert guids[0] == "ws-1"
    assert sorted(guids[1:]) == ["ans-1", "lb-1"]
    assert res["total"] == 3


@pytest.mark.anyio
async def test_system_owned_root_is_still_excluded():
    """Including the root must not bypass the System-User guard."""
    res = await _resolve("lb-sys", "LIVEBOARD")
    assert res["items"] == []
    assert res["total"] == 0
