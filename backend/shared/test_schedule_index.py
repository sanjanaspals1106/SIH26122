"""Focused tests for the M1 FAISS semantic retrieval layer
(backend.shared.schedule_index) — single active, in-memory index.

Opt-in, like backend/shared/test_schedule_repository_integration.py: these
write real schedule_activities rows to PostgreSQL (via
backend.shared.schedule_repository.save_schedule) and build a real FAISS
index using the actual sentence-transformers model — no mocks, since the
property under test (single-active-schedule replacement) only means
something against the real module-level state. Skipped automatically when
the database is not reachable.

Because there is exactly one active index per process (by design — see the
module docstring in schedule_index.py), these tests run sequentially
against shared module state rather than each getting an isolated fixture;
each still cleans up its own PostgreSQL rows in a `finally` block.

Run directly (requires a reachable DATABASE_URL):
    python backend/shared/test_schedule_index.py
"""

import uuid
from datetime import date

from backend.shared.db import get_connection
from backend.shared.schedule import ScheduleParseResult
from backend.shared.schedule_index import (
    DEFAULT_TOP_K,
    EMBEDDING_MODEL_NAME,
    NoActiveIndexError,
    ScheduleIndexError,
    ScheduleNotActiveError,
    build_index,
    build_searchable_text,
    clear_active_index,
    get_active_schedule_id,
    search_schedule,
)
from backend.shared.schedule_repository import save_schedule
from backend.shared.schemas import Schedule, ScheduleActivity


def _new_schedule_id(label: str = "") -> str:
    suffix = f"-{label}" if label else ""
    return f"m1-index-test{suffix}-{uuid.uuid4().hex[:10]}"


def _activity(schedule_id: str, activity_id: str, activity_name: str, discipline: str, location: str) -> ScheduleActivity:
    return ScheduleActivity(
        schedule_id=schedule_id,
        activity_id=activity_id,
        activity_name=activity_name,
        discipline=discipline,
        location=location,
        planned_start=date(2026, 8, 1),
        planned_finish=date(2026, 8, 10),
    )


def _persist(schedule_id: str, activities: list[ScheduleActivity]) -> None:
    schedule = Schedule(schedule_id=schedule_id, project_name="M1 index test project")
    parse_result = ScheduleParseResult(schedule_id=schedule_id, activities=activities, errors=[])
    save_schedule(schedule, parse_result)


def _cleanup(schedule_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM schedule_activities WHERE schedule_id = %s", (schedule_id,))
        conn.execute("DELETE FROM schedules WHERE schedule_id = %s", (schedule_id,))
        conn.commit()


def _database_available() -> bool:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as exc:  # connection/auth/network failure
        print(f"  (database unavailable: {exc})")
        return False


def test_build_searchable_text_omits_missing_fields():
    activity = _activity(
        "SCH", "A-1", "Excavate utility trench", "Civil", "North Field / Pump Station 3"
    )
    text = build_searchable_text(activity)
    assert text == "Excavate utility trench Civil North Field / Pump Station 3"
    assert "None" not in text  # asset_tag is None and must be omitted, not stringified

    print("✓ searchable text uses only present fields, never the literal word 'None'")


def test_build_index_and_search_returns_relevant_candidate():
    schedule_id = _new_schedule_id("search")
    activities = [
        _activity(schedule_id, "A-1", "Excavate utility trench for water pipeline", "Civil", "North Field"),
        _activity(schedule_id, "A-2", "Install electrical control panel for substation", "Electrical", "South Yard"),
        _activity(schedule_id, "A-3", "Calibrate pressure transmitter on header line", "Instrumentation", "Pump Station 3"),
    ]

    try:
        _persist(schedule_id, activities)

        result = build_index(schedule_id)
        assert result.schedule_id == schedule_id
        assert result.activity_count == 3
        assert get_active_schedule_id() == schedule_id

        candidates = search_schedule(schedule_id, "digging a trench for a pipeline", top_k=1)
        assert len(candidates) == 1
        assert candidates[0].activity_id == "A-1"
        assert candidates[0].schedule_id == schedule_id
        assert 0.0 <= candidates[0].score <= 1.0 + 1e-6  # cosine similarity range (float slack)
    finally:
        _cleanup(schedule_id)

    print("✓ build_index + search_schedule retrieves the semantically relevant activity")


def test_uses_specified_model_and_index_type():
    assert EMBEDDING_MODEL_NAME == "all-MiniLM-L6-v2"

    import faiss

    import backend.shared.schedule_index as module

    schedule_id = _new_schedule_id("model-check")
    try:
        _persist(schedule_id, [_activity(schedule_id, "A-1", "Excavate trench", "Civil", "North Field")])
        build_index(schedule_id)

        active_index = module._active_index  # white-box check of the actual built index
        assert isinstance(active_index, faiss.IndexFlatIP)
        assert active_index.metric_type == faiss.METRIC_INNER_PRODUCT
        assert active_index.d == 384  # all-MiniLM-L6-v2's embedding dimension
    finally:
        _cleanup(schedule_id)

    print("✓ the active index is a real FAISS IndexFlatIP over all-MiniLM-L6-v2's 384-dim embeddings")


def test_top_k_behavior():
    schedule_id = _new_schedule_id("topk")
    activities = [
        _activity(schedule_id, "A-1", "Excavate utility trench", "Civil", "North Field"),
        _activity(schedule_id, "A-2", "Backfill utility trench", "Civil", "North Field"),
    ]

    try:
        _persist(schedule_id, activities)
        build_index(schedule_id)

        default_candidates = search_schedule(schedule_id, "trench work")
        assert len(default_candidates) == min(DEFAULT_TOP_K, 2)

        clamped = search_schedule(schedule_id, "trench work", top_k=50)
        assert len(clamped) == 2  # clamped to the number of indexed activities, not fabricated

        try:
            search_schedule(schedule_id, "trench work", top_k=0)
            raised = False
        except ValueError:
            raised = True
        assert raised
    finally:
        _cleanup(schedule_id)

    print("✓ top_k is respected, clamped to available activities, and rejects non-positive values")


def test_single_active_schedule_replacement():
    schedule_a = _new_schedule_id("single-a")
    schedule_b = _new_schedule_id("single-b")

    try:
        _persist(schedule_a, [_activity(schedule_a, "A-1", "Excavate utility trench for water pipeline", "Civil", "North Field")])
        _persist(schedule_b, [_activity(schedule_b, "B-1", "Install electrical control panel for substation", "Electrical", "South Yard")])

        build_index(schedule_a)
        assert get_active_schedule_id() == schedule_a
        results_a = search_schedule(schedule_a, "excavate a trench", top_k=5)
        assert {c.activity_id for c in results_a} == {"A-1"}

        # Uploading B replaces the active index entirely — A is no longer searchable.
        build_index(schedule_b)
        assert get_active_schedule_id() == schedule_b

        try:
            search_schedule(schedule_a, "excavate a trench", top_k=5)
            raised = False
        except ScheduleNotActiveError as exc:
            raised = True
            assert exc.schedule_id == schedule_a
            assert exc.active_schedule_id == schedule_b
        assert raised

        results_b = search_schedule(schedule_b, "electrical panel install", top_k=5)
        assert {c.activity_id for c in results_b} == {"B-1"}
    finally:
        _cleanup(schedule_a)
        _cleanup(schedule_b)

    print("✓ uploading a new schedule replaces the active index; the old schedule is no longer searchable, though its rows remain in PostgreSQL")


def test_build_index_rejects_schedule_with_no_activities():
    schedule_id = _new_schedule_id("empty")

    try:
        build_index(schedule_id)
        raised = False
    except ScheduleIndexError:
        raised = True
    assert raised

    print("✓ building an index for a schedule with zero activities (including an unknown schedule_id) fails cleanly, not silently")


def test_search_with_no_active_index_raises_not_found():
    clear_active_index()
    try:
        search_schedule("anything", "query", top_k=3)
        raised = False
    except NoActiveIndexError:
        raised = True
    assert raised

    print("✓ searching before any schedule has been indexed raises a clear not-indexed error, not a fabricated empty result")


if __name__ == "__main__":
    print("Checking database availability (DATABASE_URL)...")
    if not _database_available():
        print(
            "Skipping M1 schedule index tests: no reachable database. Configure "
            "DATABASE_URL in the project .env to run them (see backend/.env.example)."
        )
    else:
        test_build_searchable_text_omits_missing_fields()
        test_build_index_and_search_returns_relevant_candidate()
        test_uses_specified_model_and_index_type()
        test_top_k_behavior()
        test_single_active_schedule_replacement()
        test_build_index_rejects_schedule_with_no_activities()
        test_search_with_no_active_index_raises_not_found()

        print("\nM1 schedule index tests passed.")
