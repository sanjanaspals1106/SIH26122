from typing import List, Optional, Union
from fastapi import APIRouter, HTTPException

from backend.shared.schemas import CandidateMatch, ExecutionClaim, ScheduleActivity

try:
    from backend.shared.db import get_connection
except ImportError:
    get_connection = None

try:
    from backend.shared.audit import write_audit_log
except ImportError:
    write_audit_log = None

try:
    from backend.shared import schedule_index
except ImportError:
    schedule_index = None


# M3 Match-Tier Constants
EXACT_ID = "EXACT_ID"
EXACT_ASSET = "EXACT_ASSET"
HYBRID_FALLBACK = "HYBRID_FALLBACK"
HARD_MISMATCH = "HARD_MISMATCH"

router = APIRouter(prefix="/api/v1/claims", tags=["matching"])


@router.get("/matching/health")
def health():
    return {"router": "matching", "status": "ok"}


@router.get("/{event_id}/candidates")
def get_candidates_endpoint(event_id: str):
    """
    GET /api/v1/claims/{event_id}/candidates
    Fetches the stored top-3 candidate_matches rows for a claim, as written
    by the most recent /match or /rematch call.
    """
    if get_connection is None:
        raise HTTPException(
            status_code=500, detail="Database connection module unavailable."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM execution_events WHERE event_id = %s",
                (event_id,),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail=f"Execution claim '{event_id}' not found.",
                )

            cur.execute(
                """
                SELECT * FROM candidate_matches
                WHERE event_id = %s
                ORDER BY rank_order ASC
                """,
                (event_id,),
            )
            rows = cur.fetchall()

    return {
        "event_id": event_id,
        "candidates": [dict(r) for r in rows],
    }


def match_exact_id(
    claim: Union[ExecutionClaim, dict],
    schedule_activities: List[Union[ScheduleActivity, dict]],
) -> Optional[CandidateMatch]:
    """
    Tier 1: EXACT_ID Matching.
    If reported_activity_id is provided and exactly matches a schedule activity_id
    within the same schedule_id, return CandidateMatch with EXACT_ID tier and 1.00 confidence.
    The activity_id remains an unchanged source string.
    """
    if isinstance(claim, ExecutionClaim):
        reported_id = claim.reported_activity_id
        claim_schedule_id = claim.schedule_id
        event_id = claim.event_id
    elif isinstance(claim, dict):
        reported_id = claim.get("reported_activity_id")
        claim_schedule_id = claim.get("schedule_id")
        event_id = claim.get("event_id", "evt_unknown")
    else:
        return None

    if not reported_id:
        return None

    for act in schedule_activities:
        if isinstance(act, ScheduleActivity):
            act_id = act.activity_id
            act_schedule_id = act.schedule_id
        elif isinstance(act, dict):
            act_id = act.get("activity_id")
            act_schedule_id = act.get("schedule_id")
        else:
            continue

        if act_schedule_id == claim_schedule_id and act_id == reported_id:
            return CandidateMatch(
                candidate_id=f"cand_{event_id}_{act_id}",
                event_id=event_id,
                schedule_id=act_schedule_id,
                activity_id=act_id,
                rank_order=1,
                match_tier=EXACT_ID,
                composite_confidence=1.00,
                supporting_signals="Exact activity ID match",
            )

    return None


def match_exact_asset(
    claim: Union[ExecutionClaim, dict],
    schedule_activities: List[Union[ScheduleActivity, dict]],
) -> List[CandidateMatch]:
    """
    Tier 2: EXACT_ASSET Matching.
    Matches claims to schedule activities where asset_tag exactly matches
    within the same schedule_id. Both asset_tags must be non-null and non-empty.
    Confidence ranges between 0.80 and 0.95 based on discipline and location agreement,
    and is capped at 0.40 if there is a hard discipline mismatch.
    """
    if isinstance(claim, ExecutionClaim):
        claim_asset = claim.asset_tag
        claim_schedule_id = claim.schedule_id
        claim_disc = claim.discipline
        claim_loc = claim.location
        event_id = claim.event_id
    elif isinstance(claim, dict):
        claim_asset = claim.get("asset_tag")
        claim_schedule_id = claim.get("schedule_id")
        claim_disc = claim.get("discipline")
        claim_loc = claim.get("location")
        event_id = claim.get("event_id", "evt_unknown")
    else:
        return []

    if not claim_asset or not str(claim_asset).strip():
        return []

    claim_asset_clean = str(claim_asset).strip()
    candidates: List[CandidateMatch] = []

    for act in schedule_activities:
        if isinstance(act, ScheduleActivity):
            act_asset = act.asset_tag
            act_schedule_id = act.schedule_id
            act_id = act.activity_id
            act_disc = act.discipline
            act_loc = act.location
        elif isinstance(act, dict):
            act_asset = act.get("asset_tag")
            act_schedule_id = act.get("schedule_id")
            act_id = act.get("activity_id")
            act_disc = act.get("discipline")
            act_loc = act.get("location")
        else:
            continue

        if not act_asset or not str(act_asset).strip():
            continue

        if act_schedule_id != claim_schedule_id:
            continue

        if str(act_asset).strip() != claim_asset_clean:
            continue

        # Asset tag matches within same schedule_id
        supporting: List[str] = ["asset tag matched"]
        disqualifying: List[str] = []

        disc_match = False
        disc_hard_mismatch = False
        if claim_disc and act_disc:
            if str(claim_disc).strip().lower() == str(act_disc).strip().lower():
                disc_match = True
                supporting.append("discipline matched")
            else:
                disc_hard_mismatch = True
                disqualifying.append(
                    f"discipline mismatch: claim={claim_disc}, activity={act_disc}"
                )

        loc_match = False
        if claim_loc and act_loc:
            if str(claim_loc).strip().lower() == str(act_loc).strip().lower():
                loc_match = True
                supporting.append("location matched")
            else:
                disqualifying.append(
                    f"location mismatch: claim={claim_loc}, activity={act_loc}"
                )

        # Confidence calculation
        if disc_hard_mismatch:
            confidence = 0.40
        else:
            agreements = (1 if disc_match else 0) + (1 if loc_match else 0)
            if agreements == 2:
                confidence = 0.95
            elif agreements == 1:
                confidence = 0.875
            else:
                confidence = 0.80

        cand = CandidateMatch(
            candidate_id=f"cand_{event_id}_{act_id}",
            event_id=event_id,
            schedule_id=act_schedule_id,
            activity_id=act_id,  # Unchanged source string
            rank_order=1,
            match_tier=EXACT_ASSET,
            composite_confidence=confidence,
            supporting_signals="; ".join(supporting) if supporting else None,
            disqualifying_signals="; ".join(disqualifying)
            if disqualifying
            else None,
        )
        candidates.append(cand)

    return candidates


try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


def calculate_fuzzy_score(text1: Optional[str], text2: Optional[str]) -> float:
    """
    Calculates normalized text fuzzy similarity in [0.0, 1.0] using RapidFuzz.
    Handles empty/missing text safely.
    """
    if not text1 or not text2:
        return 0.0
    s1 = str(text1).strip()
    s2 = str(text2).strip()
    if not s1 or not s2:
        return 0.0

    if fuzz is not None:
        raw_score = fuzz.ratio(s1, s2)
        score = float(raw_score) / 100.0
    else:
        from difflib import SequenceMatcher

        score = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    return max(0.0, min(1.0, float(score)))


def calculate_location_score(
    claim_location: Optional[str], activity_location: Optional[str]
) -> float:
    """
    Calculates normalized location agreement score [0.0, 1.0].
    Exact normalized location agreement -> 1.0
    Clear location mismatch -> 0.0
    Missing location on either side -> 0.0
    """
    if not claim_location or not activity_location:
        return 0.0
    loc1 = str(claim_location).strip().lower()
    loc2 = str(activity_location).strip().lower()
    if not loc1 or not loc2:
        return 0.0

    return 1.0 if loc1 == loc2 else 0.0


def calculate_discipline_score(
    claim_discipline: Optional[str], activity_discipline: Optional[str]
) -> float:
    """
    Calculates normalized discipline agreement score [0.0, 1.0].
    Exact normalized discipline agreement -> 1.0
    Clear discipline mismatch -> 0.0
    Missing discipline on either side -> 0.0
    """
    if not claim_discipline or not activity_discipline:
        return 0.0
    disc1 = str(claim_discipline).strip().lower()
    disc2 = str(activity_discipline).strip().lower()
    if not disc1 or not disc2:
        return 0.0

    return 1.0 if disc1 == disc2 else 0.0


def calculate_hybrid_score(
    semantic_score: float,
    fuzzy_score: float,
    location_score: float,
    discipline_score: float,
) -> float:
    """
    Calculates the composite confidence score for HYBRID_FALLBACK.
    Formula: 0.50 * semantic + 0.25 * fuzzy + 0.15 * location + 0.10 * discipline.
    Result is always clamped to [0.0, 1.0].
    """
    sem = max(0.0, min(1.0, float(semantic_score)))
    fuz = max(0.0, min(1.0, float(fuzzy_score)))
    loc = max(0.0, min(1.0, float(location_score)))
    disc = max(0.0, min(1.0, float(discipline_score)))

    composite = 0.50 * sem + 0.25 * fuz + 0.15 * loc + 0.10 * disc
    return max(0.0, min(1.0, round(composite, 6)))


def process_semantic_results(
    claim: Union[ExecutionClaim, dict],
    semantic_results: List[Union[dict, object]],
) -> List[dict]:
    """
    M3 Semantic Retrieval Interface.
    Normalizes semantic retrieval outputs by clamping semantic_score to [0.0, 1.0]
    and preserving activity_id unchanged. Does NOT perform model loading or embeddings.
    """
    normalized: List[dict] = []
    if not semantic_results:
        return []

    for item in semantic_results:
        if isinstance(item, dict):
            act_id = item.get("activity_id")
            # Accept either key: "semantic_score" (this module's own
            # convention) or "score" (schedule_index.SearchCandidate's
            # field name, when passed in as a dict).
            raw_score = item.get("semantic_score", item.get("score", 0.0))
        else:
            act_id = getattr(item, "activity_id", None)
            # schedule_index.SearchCandidate exposes .score, not
            # .semantic_score -- check both so real FAISS results aren't
            # silently zeroed out.
            raw_score = getattr(item, "semantic_score", None)
            if raw_score is None:
                raw_score = getattr(item, "score", 0.0)

        if not act_id:
            continue

        act_id_preserved = act_id if isinstance(act_id, str) else str(act_id)

        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            score = 0.0

        clamped_score = max(0.0, min(1.0, score))

        normalized.append(
            {
                "activity_id": act_id_preserved,
                "semantic_score": clamped_score,
            }
        )

    return normalized


def generate_hybrid_candidates(
    claim: Union[ExecutionClaim, dict],
    schedule_activities: List[Union[ScheduleActivity, dict]],
    semantic_results: Optional[List[Union[dict, object]]] = None,
) -> List[CandidateMatch]:
    """
    Tier 3: HYBRID_FALLBACK Candidate Generation.
    Generates CandidateMatch objects for semantic candidates (if provided) or schedule activities.
    When semantic_results is missing or empty, generates candidates for schedule activities using semantic_score = 0.0.
    Calculates 4 component scores: semantic_score, fuzzy_score, location_score, discipline_score,
    and combines them with formula: 0.50*sem + 0.25*fuz + 0.15*loc + 0.10*disc.
    """
    if isinstance(claim, ExecutionClaim):
        claim_schedule_id = claim.schedule_id
        event_id = claim.event_id
        claim_text = claim.raw_claim_text
        claim_loc = claim.location
        claim_disc = claim.discipline
    elif isinstance(claim, dict):
        claim_schedule_id = claim.get("schedule_id")
        event_id = claim.get("event_id", "evt_unknown")
        claim_text = claim.get("raw_claim_text", "")
        claim_loc = claim.get("location")
        claim_disc = claim.get("discipline")
    else:
        return []

    act_map: dict[str, Union[ScheduleActivity, dict]] = {}
    for act in schedule_activities:
        if isinstance(act, ScheduleActivity):
            if act.schedule_id == claim_schedule_id:
                act_map[act.activity_id] = act
        elif isinstance(act, dict):
            if act.get("schedule_id") == claim_schedule_id:
                act_map[act.get("activity_id")] = act

    if not act_map:
        return []

    targets: List[dict] = []
    if semantic_results:
        targets = process_semantic_results(claim, semantic_results)
    else:
        for act_id in act_map.keys():
            targets.append({"activity_id": act_id, "semantic_score": 0.0})

    candidates: List[CandidateMatch] = []

    for item in targets:
        act_id = item["activity_id"]
        sem_score = item["semantic_score"]

        act = act_map.get(act_id)
        if not act:
            continue

        if isinstance(act, ScheduleActivity):
            act_name = act.activity_name
            act_loc = act.location
            act_disc = act.discipline
            act_schedule_id = act.schedule_id
        else:
            act_name = act.get("activity_name", "")
            act_loc = act.get("location")
            act_disc = act.get("discipline")
            act_schedule_id = act.get("schedule_id")

        fuz_score = calculate_fuzzy_score(claim_text, act_name)
        loc_score = calculate_location_score(claim_loc, act_loc)
        disc_score = calculate_discipline_score(claim_disc, act_disc)

        comp_confidence = calculate_hybrid_score(
            sem_score, fuz_score, loc_score, disc_score
        )

        supporting: List[str] = [
            f"semantic score: {sem_score:.2f}",
            f"fuzzy score: {fuz_score:.2f}",
        ]
        disqualifying: List[str] = []

        if loc_score > 0.0:
            supporting.append("location matched")
        elif claim_loc and act_loc:
            disqualifying.append(
                f"location mismatch: claim={claim_loc}, activity={act_loc}"
            )

        if disc_score > 0.0:
            supporting.append("discipline matched")
        elif claim_disc and act_disc:
            disqualifying.append(
                f"discipline mismatch: claim={claim_disc}, activity={act_disc}"
            )

        cand = CandidateMatch(
            candidate_id=f"cand_{event_id}_{act_id}",
            event_id=event_id,
            schedule_id=act_schedule_id,
            activity_id=act_id,  # Unchanged source string
            rank_order=1,
            match_tier=HYBRID_FALLBACK,
            composite_confidence=comp_confidence,
            semantic_score=sem_score,
            fuzzy_score=fuz_score,
            location_score=loc_score,
            discipline_score=disc_score,
            supporting_signals="; ".join(supporting) if supporting else None,
            disqualifying_signals="; ".join(disqualifying)
            if disqualifying
            else None,
        )
        candidates.append(cand)

    return candidates


def rank_and_explain_candidates(
    candidates: List[CandidateMatch],
) -> List[CandidateMatch]:
    """
    Ranks CandidateMatch objects by composite_confidence descending (with deterministic activity_id tie-breaker),
    assigns rank_order (1, 2, 3 max), populates supporting/disqualifying explanation signals,
    and returns at most top 3 candidates.
    """
    if not candidates:
        return []

    # Sort candidates by composite_confidence descending, then activity_id ascending for deterministic tie-breaking
    sorted_cands = sorted(
        candidates, key=lambda c: (-c.composite_confidence, str(c.activity_id))
    )

    top_cands = sorted_cands[:3]

    ranked: List[CandidateMatch] = []
    for idx, cand in enumerate(top_cands, start=1):
        supporting_list: List[str] = []
        disqualifying_list: List[str] = []

        if cand.supporting_signals:
            supporting_list = [
                s.strip()
                for s in cand.supporting_signals.split(";")
                if s.strip()
            ]
        if cand.disqualifying_signals:
            disqualifying_list = [
                s.strip()
                for s in cand.disqualifying_signals.split(";")
                if s.strip()
            ]

        # Add explicit explanation signals based on scores if not already present
        if cand.semantic_score is not None and cand.semantic_score > 0.0:
            if not any("semantic" in s.lower() for s in supporting_list):
                supporting_list.append(
                    f"semantic similarity ({cand.semantic_score:.2f})"
                )
        if cand.fuzzy_score is not None and cand.fuzzy_score > 0.0:
            if not any(
                "fuzzy" in s.lower() or "text similarity" in s.lower()
                for s in supporting_list
            ):
                supporting_list.append(
                    f"activity text similarity ({cand.fuzzy_score:.2f})"
                )
        if cand.location_score is not None and cand.location_score > 0.0:
            if not any("location" in s.lower() for s in supporting_list):
                supporting_list.append("location agreement")
        if cand.discipline_score is not None and cand.discipline_score > 0.0:
            if not any("discipline" in s.lower() for s in supporting_list):
                supporting_list.append("discipline agreement")

        cand_dict = cand.model_dump()
        cand_dict["rank_order"] = idx
        cand_dict["supporting_signals"] = (
            "; ".join(supporting_list) if supporting_list else None
        )
        cand_dict["disqualifying_signals"] = (
            "; ".join(disqualifying_list) if disqualifying_list else None
        )

        ranked.append(CandidateMatch(**cand_dict))

    return ranked


def evaluate_hard_mismatch(
    claim: Union[ExecutionClaim, dict],
    activity: Union[ScheduleActivity, dict],
    base_confidence: Optional[float] = None,
) -> Optional[CandidateMatch]:
    """
    Tier 4: HARD_MISMATCH evaluation helper.
    Evaluates whether a claim and activity pair exhibit a clear disqualifying conflict
    (e.g., conflicting discipline or location when both are specified).
    If a hard mismatch exists, returns a CandidateMatch with match_tier = HARD_MISMATCH,
    confidence capped at <= 0.40, and detailed disqualifying_signals.
    If missing metadata alone or no conflict, returns None.
    """
    if isinstance(claim, ExecutionClaim):
        event_id = claim.event_id
        claim_schedule_id = claim.schedule_id
        claim_disc = claim.discipline
        claim_loc = claim.location
        claim_asset = claim.asset_tag
    elif isinstance(claim, dict):
        event_id = claim.get("event_id", "evt_unknown")
        claim_schedule_id = claim.get("schedule_id")
        claim_disc = claim.get("discipline")
        claim_loc = claim.get("location")
        claim_asset = claim.get("asset_tag")
    else:
        return None

    if isinstance(activity, ScheduleActivity):
        act_id = activity.activity_id
        act_schedule_id = activity.schedule_id
        act_disc = activity.discipline
        act_loc = activity.location
        act_asset = activity.asset_tag
    elif isinstance(activity, dict):
        act_id = activity.get("activity_id")
        act_schedule_id = activity.get("schedule_id")
        act_disc = activity.get("discipline")
        act_loc = activity.get("location")
        act_asset = activity.get("asset_tag")
    else:
        return None

    if not act_id:
        return None

    disqualifying: List[str] = []

    # Check discipline conflict if both present
    if claim_disc and act_disc:
        c_disc_clean = str(claim_disc).strip().lower()
        a_disc_clean = str(act_disc).strip().lower()
        if c_disc_clean and a_disc_clean and c_disc_clean != a_disc_clean:
            disqualifying.append(
                f"discipline mismatch: claim={claim_disc}, activity={act_disc}"
            )

    # Check location conflict if both present
    if claim_loc and act_loc:
        c_loc_clean = str(claim_loc).strip().lower()
        a_loc_clean = str(act_loc).strip().lower()
        if c_loc_clean and a_loc_clean and c_loc_clean != a_loc_clean:
            disqualifying.append(
                f"location mismatch: claim={claim_loc}, activity={act_loc}"
            )

    # Check asset conflict if both present
    if claim_asset and act_asset:
        c_asset_clean = str(claim_asset).strip().lower()
        a_asset_clean = str(act_asset).strip().lower()
        if c_asset_clean and a_asset_clean and c_asset_clean != a_asset_clean:
            disqualifying.append(
                f"asset mismatch: claim={claim_asset}, activity={act_asset}"
            )

    if not disqualifying:
        # No hard conflict found (compatible metadata or missing metadata alone)
        return None

    # Calculate confidence: capped at <= 0.40
    if base_confidence is not None:
        confidence = min(0.40, max(0.0, float(base_confidence)))
    else:
        confidence = 0.20

    return CandidateMatch(
        candidate_id=f"cand_{event_id}_{act_id}",
        event_id=event_id,
        schedule_id=act_schedule_id or claim_schedule_id or "SCH_UNKNOWN",
        activity_id=act_id,  # Unchanged source string
        rank_order=3,
        match_tier=HARD_MISMATCH,
        composite_confidence=confidence,
        disqualifying_signals="; ".join(disqualifying),
    )


def match_claim(
    claim: Union[ExecutionClaim, dict],
    schedule_activities: List[Union[ScheduleActivity, dict]],
    semantic_results: Optional[List[Union[dict, object]]] = None,
) -> List[CandidateMatch]:
    """
    M3 4-Tier Matching Cascade:
    1. EXACT_ID
    2. EXACT_ASSET
    3. HYBRID_FALLBACK
    4. HARD_MISMATCH
    Returns a ranked list of up to 3 CandidateMatch objects.
    """
    # Tier 1: EXACT_ID
    exact_cand = match_exact_id(claim, schedule_activities)
    if exact_cand:
        return [exact_cand]

    # Tier 2: EXACT_ASSET
    asset_cands = match_exact_asset(claim, schedule_activities)
    if asset_cands:
        ranked_asset = rank_and_explain_candidates(asset_cands)
        if ranked_asset and ranked_asset[0].composite_confidence > 0.40:
            return ranked_asset

    # Tier 3: HYBRID_FALLBACK (uses semantic_results if present, else fallback mode with semantic_score = 0.0)
    hybrid_cands = generate_hybrid_candidates(
        claim, schedule_activities, semantic_results
    )
    if hybrid_cands:
        ranked_hybrid = rank_and_explain_candidates(hybrid_cands)
        if ranked_hybrid and ranked_hybrid[0].composite_confidence > 0.0:
            top_cand = ranked_hybrid[0]
            # Check that top candidate does not have a hard discipline mismatch
            if not (
                top_cand.disqualifying_signals
                and "discipline mismatch" in top_cand.disqualifying_signals
            ):
                return ranked_hybrid

    # Tier 4: HARD_MISMATCH evaluation
    mismatch_cands: List[CandidateMatch] = []
    for act in schedule_activities:
        mismatch_cand = evaluate_hard_mismatch(claim, act)
        if mismatch_cand:
            mismatch_cands.append(mismatch_cand)

    if mismatch_cands:
        return rank_and_explain_candidates(mismatch_cands)

    if hybrid_cands:
        return rank_and_explain_candidates(hybrid_cands)

    return []



@router.post("/{event_id}/match")
def match_claim_endpoint(event_id: str, action: str = "MATCH_CLAIM"):
    """
    POST /api/v1/claims/{event_id}/match
    Loads execution claim and schedule activities from DB, executes M3 matching cascade,
    persists candidate_matches and updates execution_events status/matched_activity_id,
    and returns matching summary JSON.
    """
    if get_connection is None:
        raise HTTPException(
            status_code=500, detail="Database connection module unavailable."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Load execution claim
            cur.execute(
                "SELECT * FROM execution_events WHERE event_id = %s",
                (event_id,),
            )
            event_row = cur.fetchone()
            if not event_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Execution claim '{event_id}' not found.",
                )

            claim = ExecutionClaim(**event_row)

            # 2. Load schedule activities for schedule_id
            cur.execute(
                "SELECT * FROM schedule_activities WHERE schedule_id = %s",
                (claim.schedule_id,),
            )
            act_rows = cur.fetchall()
            schedule_activities = [ScheduleActivity(**r) for r in act_rows]

            # 2b. M1's FAISS semantic retrieval, scoped to this claim's own
            # schedule_id. Only usable while that schedule is still the
            # single active in-memory index (see M1's single-active-schedule
            # contract) -- if it isn't (no schedule indexed yet in this
            # process, or a newer schedule has since replaced the index),
            # Tier 3 falls back to fuzzy/location/discipline signals only,
            # exactly as it already did before this was wired in.
            semantic_results = None
            if claim.raw_claim_text and schedule_index is not None:
                try:
                    if schedule_index.get_active_schedule_id() != claim.schedule_id:
                        try:
                            schedule_index.build_index(claim.schedule_id)
                        except Exception as build_err:
                            print(f"[M3] FAISS auto-build index warning for {claim.schedule_id}: {build_err}")
                    semantic_results = schedule_index.search_schedule(
                        claim.schedule_id, claim.raw_claim_text
                    )
                except Exception as search_err:
                    print(f"[M3] FAISS search warning: {search_err}")
                    semantic_results = None

            # 3. Run M3 matching cascade
            candidates = match_claim(claim, schedule_activities, semantic_results)

            # 4. Determine matching status and matched_activity_id
            unmatched_reason = None
            if (
                candidates
                and candidates[0].match_tier
                in [EXACT_ID, EXACT_ASSET, HYBRID_FALLBACK]
                and candidates[0].composite_confidence > 0.40
            ):
                status = "MATCHED"
                matched_activity_id = candidates[0].activity_id
                top_tier = candidates[0].match_tier
                top_confidence = candidates[0].composite_confidence
            else:
                status = "UNMATCHED"
                # Per spec: matched_activity_id is set unconditionally to the
                # rank-1 candidate on every /match and /rematch call, even
                # when the claim ends up UNMATCHED, so there's always a
                # best-guess fallback for the UI and for M4's checks to
                # validate against.
                matched_activity_id = candidates[0].activity_id if candidates else None
                top_tier = (
                    candidates[0].match_tier if candidates else HARD_MISMATCH
                )
                top_confidence = (
                    candidates[0].composite_confidence if candidates else 0.0
                )
                if candidates and candidates[0].match_tier == HARD_MISMATCH:
                    unmatched_reason = (
                        candidates[0].disqualifying_signals
                        or "Hard metadata mismatch"
                    )
                elif candidates:
                    unmatched_reason = f"Low confidence match ({candidates[0].composite_confidence:.2f})"
                else:
                    unmatched_reason = "No matching schedule activities found"

            # 5. Persist up to 3 ranked candidates and update execution_event safely
            cur.execute(
                "DELETE FROM candidate_matches WHERE event_id = %s",
                (event_id,),
            )

            top_3 = candidates[:3]
            for cand in top_3:
                cur.execute(
                    """
                    INSERT INTO candidate_matches (
                        candidate_id, event_id, schedule_id, activity_id,
                        rank_order, match_tier, composite_confidence,
                        semantic_score, fuzzy_score, location_score,
                        discipline_score, supporting_signals, disqualifying_signals
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cand.candidate_id,
                        cand.event_id,
                        cand.schedule_id,
                        cand.activity_id,
                        cand.rank_order,
                        cand.match_tier,
                        cand.composite_confidence,
                        cand.semantic_score,
                        cand.fuzzy_score,
                        cand.location_score,
                        cand.discipline_score,
                        cand.supporting_signals,
                        cand.disqualifying_signals,
                    ),
                )

            cur.execute(
                """
                UPDATE execution_events
                SET status = %s, matched_activity_id = %s
                WHERE event_id = %s
                """,
                (status, matched_activity_id, event_id),
            )

            conn.commit()

            # 6. Audit log integration
            if write_audit_log is not None:
                try:
                    write_audit_log(
                        entity_type="execution_event",
                        entity_id=event_id,
                        action=action,
                        actor_id="SYSTEM:M3",
                        before_state={"status": event_row.get("status")},
                        after_state={
                            "status": status,
                            "matched_activity_id": matched_activity_id,
                        },
                        payload={
                            "match_tier": top_tier,
                            "composite_confidence": top_confidence,
                            "unmatched_reason": unmatched_reason,
                        },
                    )
                except Exception:
                    pass

            res = {
                "event_id": event_id,
                "matched_activity_id": matched_activity_id,
                "match_tier": top_tier,
                "composite_confidence": top_confidence,
                "candidates": [c.model_dump() for c in top_3],
                "status": status,
            }
            if unmatched_reason:
                res["unmatched_reason"] = unmatched_reason

            return res


@router.post("/{event_id}/rematch")
def rematch_claim_endpoint(event_id: str):
    """
    POST /api/v1/claims/{event_id}/rematch
    Re-runs the M3 4-tier matching cascade for an existing execution claim.
    Updates candidate_matches and status/matched_activity_id accordingly.
    """
    return match_claim_endpoint(event_id, action="REMATCH_CLAIM")










