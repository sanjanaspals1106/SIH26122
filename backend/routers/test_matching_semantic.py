"""
Regression test for wiring M1's FAISS semantic search into M3's Tier 3
HYBRID_FALLBACK cascade.

Before this fix, match_claim_endpoint never called schedule_index.search_schedule(),
so Tier 3 always ran with semantic_score=0.0. Separately, even when semantic
results were passed in, process_semantic_results() read a `.semantic_score`
attribute that schedule_index.SearchCandidate doesn't have (it exposes
`.score`), so real FAISS results would have been silently zeroed out too.
This test locks in both fixes.
"""
from backend.routers.matching import (
    generate_hybrid_candidates,
    process_semantic_results,
)
from backend.shared.schedule_index import SearchCandidate


def test_process_semantic_results_reads_search_candidate_score_field():
    """SearchCandidate.score (not .semantic_score) must be picked up."""
    results = process_semantic_results(
        claim={"raw_claim_text": "x"},
        semantic_results=[
            SearchCandidate(schedule_id="sched-1", activity_id="A1000", score=0.87),
        ],
    )
    assert results == [{"activity_id": "A1000", "semantic_score": 0.87}]


def test_process_semantic_results_still_reads_semantic_score_dicts():
    """Backward compatible with plain dicts using the "semantic_score" key."""
    results = process_semantic_results(
        claim={"raw_claim_text": "x"},
        semantic_results=[{"activity_id": "A1000", "semantic_score": 0.5}],
    )
    assert results == [{"activity_id": "A1000", "semantic_score": 0.5}]


def test_generate_hybrid_candidates_uses_real_semantic_score_from_faiss():
    claim = {
        "event_id": "evt-1",
        "schedule_id": "sched-1",
        "raw_claim_text": "excavation trench work",
        "location": None,
        "discipline": None,
    }
    activities = [
        {
            "activity_id": "A1000",
            "schedule_id": "sched-1",
            "activity_name": "Utility Trench Excavation",
            "location": None,
            "discipline": None,
        }
    ]
    semantic_results = [
        SearchCandidate(schedule_id="sched-1", activity_id="A1000", score=0.91),
    ]

    candidates = generate_hybrid_candidates(claim, activities, semantic_results)

    assert len(candidates) == 1
    assert candidates[0].semantic_score == 0.91
    # 0.50*0.91 + 0.25*fuzzy + ... must be strictly greater than the
    # semantic_score=0.0 floor case, proving the real FAISS score actually
    # influences the composite confidence.
    zero_semantic = generate_hybrid_candidates(claim, activities, semantic_results=None)
    assert candidates[0].composite_confidence > zero_semantic[0].composite_confidence
