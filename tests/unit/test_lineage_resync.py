"""
S54 — `resync_object`: replace ONE object's lineage rows without moving anything else.

Reuses the canned TML / fixtures of the lineage suite. The contract pinned here:
parity with a full build, failure keeps old rows, the global watermark and the
certified answer set never move UP (resync stamps nothing; it can only lower the
lineage watermark if it replaces the last stamped rows, which just means more
re-export next sync), other objects and other scopes are untouched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from tests.unit.test_lineage_columns import (
    CLUSTER_ID,
    _FakeTMLClient,
    _make_job,
    _seed,
    in_memory_db,  # noqa: F401 — pytest fixture, bound by argument name
    patched_config,  # noqa: F401 — pytest fixture, bound by argument name
)
from tests.unit.test_lineage_incremental import SHADOW_SCOPES, _seed_shadow, _shadow_snapshot
from ts_admin.models.cache.ts_column_lineage import CachedColumnLineage
from ts_admin.models.cache.ts_column_usage import CachedColumnUsage
from ts_admin.models.cache.ts_dependency import CachedDependency
from ts_admin.services import lineage_service
from ts_admin.services.job_service import mark_complete

OLD = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _lineage(engine, guid="model-1"):
    with Session(engine) as s:
        rows = s.exec(select(CachedColumnLineage).where(CachedColumnLineage.model_guid == guid)).all()
    return sorted(
        (r.model_column_name, r.table_guid, r.table_column_name, r.db_table, r.db_column_name, r.connection_name)
        for r in rows
    )


def _lb_rows(engine, guid="lb-1"):
    with Session(engine) as s:
        edges = s.exec(
            select(CachedDependency).where(CachedDependency.source_guid == guid, CachedDependency.relation == "USES")
        ).all()
        usage = s.exec(select(CachedColumnUsage).where(CachedColumnUsage.consumer_guid == guid)).all()
    return (
        sorted((e.target_guid, e.target_type, e.target_name, e.source_name) for e in edges),
        sorted((u.model_guid, u.model_column_name, u.consumer_name) for u in usage),
    )


def _watermarks(engine):
    """(lineage watermark, certified-answer watermark) for c1/org-0 only."""
    from sqlmodel import func

    with Session(engine) as s:
        return (
            s.exec(
                select(func.max(CachedColumnLineage.synced_at)).where(
                    CachedColumnLineage.cluster_id == CLUSTER_ID, CachedColumnLineage.org_id == 0
                )
            ).first(),
            s.exec(
                select(func.max(CachedColumnUsage.synced_at)).where(
                    CachedColumnUsage.cluster_id == CLUSTER_ID,
                    CachedColumnUsage.org_id == 0,
                    CachedColumnUsage.consumer_type == "ANSWER",
                )
            ).first(),
        )


@pytest.fixture
def built(monkeypatch, in_memory_db, patched_config):  # noqa: F811
    """A seeded cache after one full build; the build's job is closed so nothing is in flight."""
    _seed(in_memory_db)
    fake = _FakeTMLClient()
    monkeypatch.setattr("ts_admin.ts_client.ThoughtSpotClient", lambda *a, **k: fake)
    job_id = _make_job()

    async def _go():
        await lineage_service.build_column_map(cluster_id=CLUSTER_ID, org_id=0, job_id=job_id)

    return in_memory_db, fake, job_id, _go


async def test_resync_matches_full_build_for_model_and_liveboard(built):
    engine, fake, job_id, build = built
    await build()
    mark_complete(job_id, {})
    want_model, want_lb = _lineage(engine), _lb_rows(engine)
    assert want_model and want_lb[0] and want_lb[1]  # anti-vacuity

    with Session(engine) as s:  # corrupt both objects so a no-op resync would fail the parity check
        for r in s.exec(select(CachedColumnLineage)).all():
            r.db_column_name = "STALE"
            s.add(r)
        for r in s.exec(select(CachedColumnUsage)).all():
            s.delete(r)
        for r in s.exec(select(CachedDependency).where(CachedDependency.source_guid == "lb-1")).all():
            s.delete(r)
        s.commit()

    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="model-1")
    assert res["status"] == "ok" and res["node_type"] == "MODEL" and res["rows"] == {"lineage": len(want_model)}
    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="lb-1")
    assert res["status"] == "ok" and res["node_type"] == "LIVEBOARD"

    assert _lineage(engine) == want_model
    assert _lb_rows(engine) == want_lb
    with Session(engine) as s:  # nothing resync wrote is stamped
        assert all(r.synced_at is None for r in s.exec(select(CachedColumnLineage)).all())
        assert all(r.synced_at is None for r in s.exec(select(CachedColumnUsage)).all())


async def test_failed_export_keeps_old_rows(built, monkeypatch):
    engine, fake, job_id, build = built
    await build()
    mark_complete(job_id, {})
    before = (_lineage(engine), _lb_rows(engine))

    class _Stub(_FakeTMLClient):
        fail: set[str] = set()

        async def tml_export(self, *, object_ids, edoc_format=None):
            items = await super().tml_export(object_ids=object_ids, edoc_format=edoc_format)
            for i in items:
                if i["info"]["id"] in self.fail:
                    i["edoc"] = ""  # ERROR-status stub
            return items

    stub = _Stub()
    monkeypatch.setattr("ts_admin.ts_client.ThoughtSpotClient", lambda *a, **k: stub)
    for failing, guid in (({"lb-1"}, "lb-1"), ({"model-1"}, "model-1"), ({"table-1"}, "model-1")):
        stub.fail = failing
        res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid=guid)
        assert res["status"] == "export_failed" and res["rows"] == {}
        assert (_lineage(engine), _lb_rows(engine)) == before


async def test_watermarks_other_objects_and_other_scopes_untouched(built):
    engine, fake, job_id, build = built
    await build()
    mark_complete(job_id, {})
    now = datetime.now(tz=timezone.utc)
    with Session(engine) as s:  # a certified answer plus a second model the resync must not touch
        s.add(
            CachedColumnUsage(
                cluster_id=CLUSTER_ID, org_id=0, model_guid="model-1", model_column_name="Region",
                consumer_guid="answer-1", consumer_type="ANSWER", consumer_name="a", synced_at=now,
            )
        )  # fmt: skip
        s.add(
            CachedColumnLineage(
                cluster_id=CLUSTER_ID, org_id=0, model_guid="model-2", model_column_name="X", synced_at=now
            )
        )
        s.commit()
    for scope in SHADOW_SCOPES:
        _seed_shadow(engine, cluster_id=scope[0], org_id=scope[1], synced_at=now + timedelta(days=400))
    shadows = {sc: _shadow_snapshot(engine, cluster_id=sc[0], org_id=sc[1]) for sc in SHADOW_SCOPES}
    assert all(any(v.values()) for v in shadows.values())
    marks, other = _watermarks(engine), _lineage(engine, "model-2")
    assert marks[0] is not None and marks[1] is not None and other  # anti-vacuity

    await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="model-1")
    await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="lb-1")

    assert _watermarks(engine) == marks
    assert _lineage(engine, "model-2") == other
    assert {sc: _shadow_snapshot(engine, cluster_id=sc[0], org_id=sc[1]) for sc in SHADOW_SCOPES} == shadows
    with Session(engine) as s:  # the answer's certified usage row is not re-stamped or removed
        ans = s.exec(
            select(CachedColumnUsage).where(
                CachedColumnUsage.consumer_type == "ANSWER",
                CachedColumnUsage.cluster_id == CLUSTER_ID,
                CachedColumnUsage.org_id == 0,
            )
        ).all()
    assert len(ans) == 1 and ans[0].synced_at is not None


async def test_answer_resync_replaces_its_rows_only(built):
    engine, fake, job_id, build = built
    mark_complete(job_id, {})
    with Session(engine) as s:
        s.add(
            CachedColumnUsage(
                cluster_id=CLUSTER_ID, org_id=0, model_guid="model-1", model_column_name="Stale",
                consumer_guid="answer-1", consumer_type="ANSWER", consumer_name="a",
            )
        )  # fmt: skip
        s.commit()
    assert await lineage_service.index_answer(cluster_id=CLUSTER_ID, org_id=0, guid="answer-1") == 0  # memoized
    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="answer-1")
    assert res["status"] == "ok" and res["rows"]["usage"] > 0
    with Session(engine) as s:
        names = {u.model_column_name for u in s.exec(select(CachedColumnUsage)).all()}
    assert names == {"Total Revenue"}


async def test_table_is_refused_and_unknown_is_404(built):
    engine, fake, job_id, build = built
    mark_complete(job_id, {})
    with pytest.raises(lineage_service.ResyncUnsupportedError, match="full dependencies sync"):
        await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="table-1")
    with pytest.raises(lineage_service.ObjectNotCachedError):
        await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="nope")
    assert fake.exported == []


async def test_refused_while_dependencies_sync_in_flight(built):
    engine, fake, job_id, build = built  # the build's job is still QUEUED
    with pytest.raises(lineage_service.ResyncInFlightError):
        await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="lb-1")
    assert fake.exported == []


# ── Review-board additions ───────────────────────────────────────────────────────

FQNLESS_MODEL_EDOC = {
    "guid": "model-2",
    "worksheet": {
        "name": "Fqnless Model",
        # no fqn and a name whose case differs from the physical table's ("SALES")
        "tables": [{"name": "sales"}],
        "table_paths": [{"id": "sales_1", "table": "sales", "join_path": [{"join": []}]}],
        "worksheet_columns": [
            {"name": "Rev", "column_id": "sales_1::Revenue"},
            {"name": "Reg", "column_id": "SALES::Region"},
        ],
    },
}


def _lb2_edoc():
    import copy

    from tests.unit.test_lineage_columns import LIVEBOARD_EDOC

    edoc = copy.deepcopy(LIVEBOARD_EDOC)
    edoc["guid"] = "lb-2"
    edoc["liveboard"]["name"] = "Other LB"
    return edoc


class _ExtraClient(_FakeTMLClient):
    """The canned client plus model-2 / lb-2, with hooks to raise or drop objects."""

    def __init__(self):
        super().__init__()
        self.raises: dict[str, Exception] = {}
        self.drop: set[str] = set()

    async def tml_export(self, *, object_ids, edoc_format=None):
        for g in object_ids:
            if g in self.raises:
                raise self.raises[g]
        items = await super().tml_export(object_ids=object_ids, edoc_format=edoc_format)
        extra = {"model-2": FQNLESS_MODEL_EDOC, "lb-2": _lb2_edoc()}
        for g in object_ids:
            if g in extra:
                items.append({"info": {"id": g}, "edoc": extra[g]})
        return [i for i in items if i["info"]["id"] not in self.drop]


@pytest.fixture
def built2(monkeypatch, in_memory_db, patched_config):  # noqa: F811
    from ts_admin.models.cache.ts_metadata import CachedMetadata

    _seed(in_memory_db)
    with Session(in_memory_db) as s:
        for guid, name, otype in (("model-2", "Fqnless Model", "WORKSHEET"), ("lb-2", "Other LB", "LIVEBOARD")):
            s.add(
                CachedMetadata(
                    cluster_id=CLUSTER_ID, org_id=0, ts_guid=guid, name=name, object_type=otype, owner_name="A"
                )
            )
        s.commit()
    fake = _ExtraClient()
    monkeypatch.setattr("ts_admin.ts_client.ThoughtSpotClient", lambda *a, **k: fake)
    return in_memory_db, fake


async def _full_build(engine):
    job_id = _make_job()
    await lineage_service.build_column_map(cluster_id=CLUSTER_ID, org_id=0, job_id=job_id)
    mark_complete(job_id, {})


async def test_fqnless_case_mismatched_model_matches_full_build(built2):
    engine, fake = built2
    await _full_build(engine)
    want = _lineage(engine, "model-2")
    assert want and all(row[3] == "FACT_SALES" for row in want)  # resolved through the name fallback
    with Session(engine) as s:
        for r in s.exec(select(CachedColumnLineage).where(CachedColumnLineage.model_guid == "model-2")).all():
            r.db_table = ""
            s.add(r)
        s.commit()

    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="model-2")

    assert res["status"] == "ok"
    assert _lineage(engine, "model-2") == want


async def test_resync_leaves_a_sibling_liveboard_alone(built2):
    engine, fake = built2
    await _full_build(engine)
    sibling = _lb_rows(engine, "lb-2")
    assert sibling[0] and sibling[1]
    await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="lb-1")
    assert _lb_rows(engine, "lb-2") == sibling


@pytest.mark.parametrize(
    ("guid", "raising"),
    [("lb-1", "lb-1"), ("model-1", "model-1"), ("model-1", "table-1"), ("answer-1", "answer-1")],
)
@pytest.mark.parametrize("make_exc", [lambda: _exc("TSServerError", 500, "x"), lambda: _exc("TSTimeoutError")])
async def test_raising_export_is_export_failed_and_keeps_rows(built2, guid, raising, make_exc):
    engine, fake = built2
    await _full_build(engine)
    with Session(engine) as s:
        s.add(
            CachedColumnUsage(
                cluster_id=CLUSTER_ID, org_id=0, model_guid="model-1", model_column_name="Old",
                consumer_guid="answer-1", consumer_type="ANSWER", consumer_name="a",
            )
        )  # fmt: skip
        s.commit()
    before = (_lineage(engine), _lb_rows(engine), _answer_rows(engine))
    assert all(before)

    fake.raises[raising] = make_exc()
    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid=guid)

    assert res["status"] == "export_failed"
    assert (_lineage(engine), _lb_rows(engine), _answer_rows(engine)) == before


async def test_rate_limit_on_any_path_is_export_failed(built2):
    engine, fake = built2
    await _full_build(engine)
    before = _lb_rows(engine)
    fake.raises["lb-1"] = _exc("TSRateLimitError")
    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="lb-1")
    assert res["status"] == "export_failed" and _lb_rows(engine) == before


async def test_source_missing_from_export_response_is_export_failed(built2):
    engine, fake = built2
    await _full_build(engine)
    before = _lineage(engine)
    assert before
    fake.drop = {"table-1"}  # the export "succeeds" but silently omits the source table
    res = await lineage_service.resync_object(cluster_id=CLUSTER_ID, org_id=0, guid="model-1")
    assert res["status"] == "export_failed" and _lineage(engine) == before


def _exc(name: str, *args):
    from ts_admin.ts_client import exceptions

    return getattr(exceptions, name)(*args)


def _answer_rows(engine):
    with Session(engine) as s:
        rows = s.exec(select(CachedColumnUsage).where(CachedColumnUsage.consumer_type == "ANSWER")).all()
    return sorted((r.model_column_name, r.consumer_guid) for r in rows)
