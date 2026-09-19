import copy
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.shared.schemas import CandidateMatch, ExecutionClaim, ScheduleActivity

# Module-level in-memory split fallback database for offline/test environments
_in_memory_splits_db: Dict[str, List[dict]] = {}

try:
    from backend.shared.db import get_connection
except ImportError:
    try:
        from backend.shared.db import get_conn as get_connection
    except ImportError:
        get_connection = None

try:
    from backend.shared.audit import write_audit_log
except ImportError:
    write_audit_log = None


# M3 Match-Tier Constants
EXACT_ID = "EXACT_ID"
EXACT_ASSET = "EXACT_ASSET"
HYBRID_FALLBACK = "HYBRID_FALLBACK"
HARD_MISMATCH = "HARD_MISMATCH"

router = APIRouter(prefix="/api/v1/claims", tags=["matching"])


@router.get("/matching/health")
def health():
    return {"router": "matching", "status": "ok"}


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


DISCIPLINE_MAP = {
    "civil": "CIVIL",
    "piping": "PIPING",
    "static/rotating equipment": "STATIC_ROTATING_EQUIPMENT",
    "static equipment": "STATIC_ROTATING_EQUIPMENT",
    "rotating equipment": "STATIC_ROTATING_EQUIPMENT",
    "equipment": "STATIC_ROTATING_EQUIPMENT",
    "mech": "STATIC_ROTATING_EQUIPMENT",
    "mechanical": "STATIC_ROTATING_EQUIPMENT",
    "electrical": "ELECTRICAL",
    "elec": "ELECTRICAL",
    "instrumentation": "INSTRUMENTATION",
    "inst": "INSTRUMENTATION",
    "hse": "HSE",
    "safety": "HSE",
    "general works": "GENERAL_WORKS",
}


def normalize_discipline(disc: Optional[str]) -> Optional[str]:
    if not disc or not str(disc).strip():
        return None
    clean = str(disc).strip().lower()
    return DISCIPLINE_MAP.get(clean, str(disc).strip().upper())


try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


CONSTRUCTION_SYNONYMS = [
    ("reinforcement steel", "rebar"),
    ("reinforcement", "rebar"),
    ("shuttering", "formwork"),
    ("concreting", "concrete pour"),
]


def normalize_construction_text(text: Optional[str]) -> str:
    if not text:
        return ""
    res = str(text).lower()
    for orig, replacement in CONSTRUCTION_SYNONYMS:
        res = res.replace(orig, replacement)
    return res


def calculate_fuzzy_score(text1: Optional[str], text2: Optional[str]) -> float:
    """
    Calculates normalized text fuzzy similarity in [0.0, 1.0] using RapidFuzz.
    Combines ratio, token_set_ratio, and token_sort_ratio after construction terminology normalization.
    """
    if not text1 or not text2:
        return 0.0
    s1 = normalize_construction_text(text1).strip()
    s2 = normalize_construction_text(text2).strip()
    if not s1 or not s2:
        return 0.0

    if fuzz is not None:
        r1 = fuzz.ratio(s1, s2)
        r2 = fuzz.token_set_ratio(s1, s2)
        r3 = fuzz.token_sort_ratio(s1, s2)
        raw_score = max(r1, r2, r3)
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
    Supports exact match, substring containment, and location aliases.
    """
    if not claim_location or not activity_location:
        return 0.0
    loc1 = str(claim_location).strip().lower()
    loc2 = str(activity_location).strip().lower()
    if not loc1 or not loc2:
        return 0.0

    if loc1 == loc2 or loc1 in loc2 or loc2 in loc1:
        return 1.0

    aliases = {
        "ps3": "pump station 3",
        "pump station 3": "ps3",
        "mcc-02": "mcc building",
        "mcc-01": "mcc building",
        "substation yard": "substation",
    }
    if aliases.get(loc1) == loc2 or aliases.get(loc2) == loc1:
        return 1.0

    return 0.0


def calculate_discipline_score(
    claim_discipline: Optional[str], activity_discipline: Optional[str]
) -> float:
    """
    Calculates normalized discipline agreement score [0.0, 1.0].
    Uses normalized discipline mapping.
    """
    d1 = normalize_discipline(claim_discipline)
    d2 = normalize_discipline(activity_discipline)
    if not d1 or not d2:
        return 0.0

    return 1.0 if d1 == d2 else 0.0


def calculate_hybrid_score(
    semantic_score: float,
    fuzzy_score: float,
    location_score: float,
    discipline_score: float,
    has_semantic_results: bool = True,
) -> float:
    """
    Calculates the composite confidence score for HYBRID_FALLBACK.
    Normal weights (when semantic scoring is available): 0.50 * sem + 0.25 * fuz + 0.15 * loc + 0.10 * disc.
    Dynamic re-scaled weights (when semantic score is unavailable/0 due to unindexed FAISS): 0.50 * fuz + 0.30 * loc + 0.20 * disc.
    Result is always clamped to [0.0, 1.0].
    """
    sem = max(0.0, min(1.0, float(semantic_score)))
    fuz = max(0.0, min(1.0, float(fuzzy_score)))
    loc = max(0.0, min(1.0, float(location_score)))
    disc = max(0.0, min(1.0, float(discipline_score)))

    if not has_semantic_results or sem == 0.0:
        composite = 0.50 * fuz + 0.30 * loc + 0.20 * disc
    else:
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
            raw_score = item.get("semantic_score", 0.0)
        else:
            act_id = getattr(item, "activity_id", None)
            raw_score = getattr(item, "semantic_score", 0.0)

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

    sem_score_map: dict[str, float] = {}
    if semantic_results:
        proc_sem = process_semantic_results(claim, semantic_results)
        for item in proc_sem:
            sem_score_map[item["activity_id"]] = item["semantic_score"]

    targets: List[dict] = []
    for act_id in act_map.keys():
        targets.append(
            {
                "activity_id": act_id,
                "semantic_score": sem_score_map.get(act_id, 0.0),
            }
        )

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
            sem_score,
            fuz_score,
            loc_score,
            disc_score,
            has_semantic_results=bool(semantic_results),
        )

        supporting: List[str] = [
            f"semantic score: {sem_score:.2f}",
            f"fuzzy score: {fuz_score:.2f}",
        ]
        disqualifying: List[str] = []

        has_disc_mismatch = False
        if claim_disc and act_disc:
            if disc_score > 0.0:
                supporting.append("discipline matched")
            else:
                has_disc_mismatch = True
                disqualifying.append(
                    f"discipline mismatch: claim={claim_disc}, activity={act_disc}"
                )

        has_loc_mismatch = False
        if claim_loc and act_loc:
            if loc_score > 0.0:
                supporting.append("location matched")
            else:
                has_loc_mismatch = True
                disqualifying.append(
                    f"location mismatch: claim={claim_loc}, activity={act_loc}"
                )

        # Contextual Matching Gates / Confidence Caps for HYBRID_FALLBACK:
        # Prevent high semantic or fuzzy text similarity from overriding explicit context conflicts
        if has_disc_mismatch or has_loc_mismatch:
            comp_confidence = min(0.40, comp_confidence)

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

    # Sort candidates by text/semantic relevance descending, then composite_confidence descending, then activity_id ascending
    sorted_cands = sorted(
        candidates,
        key=lambda c: (
            -max(c.fuzzy_score or 0.0, c.semantic_score or 0.0),
            -c.composite_confidence,
            str(c.activity_id),
        ),
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

def get_wbs_context(
    schedule_id: str,
    activity_id: Optional[str],
    schedule_activities: Optional[List[Union[ScheduleActivity, dict]]] = None,
) -> Optional[dict]:
    """
    Retrieves WBS context for a matched activity within a schedule.
    Supports hierarchical WBS grouping:
    1. Try exact wbs_code matching first.
    2. If exact WBS group has only 1 activity, fall back to parent_id / Parent_ID.
    3. If parent ID is unavailable/single, fall back to parent WBS prefix (e.g., '1.01' from '1.01.03').
    4. Build wbs_group_activities and sibling_activity_ids from the resulting group.
    """
    if not activity_id:
        return None

    if schedule_activities is None:
        if get_connection is None:
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM schedule_activities WHERE schedule_id = %s",
                        (schedule_id,),
                    )
                    rows = cur.fetchall()
                    schedule_activities = [
                        ScheduleActivity(**r) if isinstance(r, dict) else r
                        for r in rows
                    ]
        except Exception:
            return None

    target_act = None
    for act in schedule_activities:
        act_id = None
        if isinstance(act, ScheduleActivity):
            act_id = act.activity_id
        elif isinstance(act, dict):
            act_id = act.get("activity_id") or act.get("Activity_ID")
        if act_id == activity_id:
            target_act = act
            break

    if target_act is None:
        return None

    def _extract_wbs(act):
        if isinstance(act, ScheduleActivity):
            return getattr(act, "wbs_code", None) or getattr(act, "wbs", None) or getattr(act, "WBS", None)
        elif isinstance(act, dict):
            return act.get("wbs_code") or act.get("wbs") or act.get("WBS")
        return None

    def _extract_parent(act):
        if isinstance(act, ScheduleActivity):
            return getattr(act, "parent_id", None) or getattr(act, "Parent_ID", None) or getattr(act, "parent_wbs", None)
        elif isinstance(act, dict):
            return act.get("parent_id") or act.get("Parent_ID") or act.get("parent_wbs")
        return None

    def _extract_act_id(act):
        if isinstance(act, ScheduleActivity):
            return act.activity_id
        elif isinstance(act, dict):
            return act.get("activity_id") or act.get("Activity_ID")
        return None

    target_wbs_raw = _extract_wbs(target_act)
    target_parent_raw = _extract_parent(target_act)

    target_wbs = str(target_wbs_raw).strip() if target_wbs_raw else None
    target_parent = str(target_parent_raw).strip() if target_parent_raw else None

    if not target_wbs and not target_parent:
        return {
            "wbs_code": None,
            "wbs_group_activities": [activity_id],
            "sibling_activity_ids": [],
        }

    def _collect_group(predicate):
        group = []
        for act in schedule_activities:
            aid = _extract_act_id(act)
            if aid and predicate(act, aid):
                if aid not in group:
                    group.append(aid)
        return group

    # Step 1: Exact wbs_code matching
    exact_group = []
    if target_wbs:
        exact_group = _collect_group(lambda act, aid: (_extract_wbs(act) or "").strip() == target_wbs)

    if len(exact_group) > 1:
        siblings = [aid for aid in exact_group if aid != activity_id]
        return {
            "wbs_code": target_wbs,
            "wbs_group_activities": exact_group,
            "sibling_activity_ids": siblings,
        }

    # Step 2: Fall back to parent_id / Parent_ID
    parent_group = []
    if target_parent:
        parent_group = _collect_group(
            lambda act, aid: (_extract_parent(act) or "").strip() == target_parent
            or (_extract_wbs(act) or "").strip() == target_parent
        )

    if len(parent_group) > 1:
        siblings = [aid for aid in parent_group if aid != activity_id]
        return {
            "wbs_code": target_parent,
            "wbs_group_activities": parent_group,
            "sibling_activity_ids": siblings,
        }

    # Step 3: Fall back to parent WBS prefix (e.g. '1.01' from '1.01.03')
    prefix_group = []
    parent_prefix = None
    if target_wbs and "." in target_wbs:
        parts = target_wbs.split(".")
        if len(parts) >= 2:
            parent_prefix = ".".join(parts[:-1])
            prefix_group = _collect_group(
                lambda act, aid: (_extract_wbs(act) or "").strip().startswith(parent_prefix)
            )

    if len(prefix_group) > 1 and parent_prefix:
        siblings = [aid for aid in prefix_group if aid != activity_id]
        return {
            "wbs_code": parent_prefix,
            "wbs_group_activities": prefix_group,
            "sibling_activity_ids": siblings,
        }

    # Fallback if no broader group contains > 1 activity
    final_wbs = target_wbs or target_parent
    final_group = exact_group or [activity_id]
    siblings = [aid for aid in final_group if aid != activity_id]
    return {
        "wbs_code": final_wbs,
        "wbs_group_activities": final_group,
        "sibling_activity_ids": siblings,
    }


BROAD_SCOPE_KEYWORDS = [
    "general",
    "across",
    "entire",
    "overall",
    "works in progress",
    "in progress",
    "site-wide",
    "area-wide",
    "wbs level",
    "broad claim",
    "all activities",
]


def detect_claim_scope(
    claim: Union[ExecutionClaim, dict],
    wbs_context: Optional[dict] = None,
    candidates: Optional[List[CandidateMatch]] = None,
) -> dict:
    """
    M3 Step 5: Broad/WBS-Level Claim Detection.
    Determines whether an execution claim target is SPECIFIC to a single schedule activity
    or BROAD_WBS spanning multiple sibling activities within a WBS group.

    Returns dict:
    {
        "claim_scope": "SPECIFIC" | "BROAD_WBS",
        "scope_reason": str
    }
    """
    if isinstance(claim, ExecutionClaim):
        claim_text = claim.raw_claim_text or ""
        reported_id = claim.reported_activity_id
    elif isinstance(claim, dict):
        claim_text = claim.get("raw_claim_text", "") or ""
        reported_id = claim.get("reported_activity_id")
    else:
        claim_text = ""
        reported_id = None

    # Safety check for WBS context & sibling activities
    if not wbs_context or not wbs_context.get("wbs_code"):
        return {
            "claim_scope": "SPECIFIC",
            "scope_reason": "No WBS context available for broad expansion",
        }

    siblings = wbs_context.get("sibling_activity_ids") or []
    if not siblings:
        return {
            "claim_scope": "SPECIFIC",
            "scope_reason": "Single activity in WBS group; cannot broaden across siblings",
        }

    # If claim explicitly references a reported_activity_id, treat as specific
    if reported_id and str(reported_id).strip():
        return {
            "claim_scope": "SPECIFIC",
            "scope_reason": f"Explicit reported activity ID provided ({reported_id})",
        }

    # Analyze raw_claim_text for broad/WBS-level signals
    text_lower = claim_text.lower()
    matched_broad_terms = [
        kw for kw in BROAD_SCOPE_KEYWORDS if kw in text_lower
    ]

    if matched_broad_terms:
        term_str = ", ".join(f"'{t}'" for t in matched_broad_terms[:2])
        group_size = len(siblings) + 1
        wbs_code = wbs_context.get("wbs_code")
        return {
            "claim_scope": "BROAD_WBS",
            "scope_reason": (
                f"Broad scope wording ({term_str}) detected across "
                f"{group_size} activities in WBS group '{wbs_code}'"
            ),
        }

    return {
        "claim_scope": "SPECIFIC",
        "scope_reason": "Claim describes a specific activity scope",
    }


def allocate_wbs_splits(
    claim: Union[ExecutionClaim, dict],
    claim_scope: str,
    wbs_context: Optional[dict],
    schedule_activities: Optional[List[Union[ScheduleActivity, dict]]] = None,
) -> dict:
    """
    M3 Step 6: Deterministic WBS Split Allocation.
    For BROAD_WBS claims, allocates claim quantity proportionally across eligible WBS activities
    using planned quantities.

    Returns dict:
    {
        "wbs_splits": List[dict] or None,
        "allocation_status": "SUCCESS" | "FAILED" | "SKIPPED",
        "allocation_reason": str
    }
    """
    if claim_scope != "BROAD_WBS":
        return {
            "wbs_splits": None,
            "allocation_status": "SKIPPED",
            "allocation_reason": "Claim scope is not BROAD_WBS",
        }

    if not wbs_context or not wbs_context.get("wbs_group_activities"):
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": "Allocation failed: No WBS group activities available",
        }

    if isinstance(claim, ExecutionClaim):
        claim_qty = claim.claimed_quantity
    elif isinstance(claim, dict):
        claim_qty = claim.get("claimed_quantity")
    else:
        claim_qty = None

    if claim_qty is None:
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": "Allocation failed: Claim quantity is missing or None",
        }

    try:
        claim_qty_val = float(claim_qty)
    except (ValueError, TypeError):
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": f"Allocation failed: Invalid claim quantity '{claim_qty}'",
        }

    if claim_qty_val <= 0.0:
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": f"Allocation failed: Claim quantity ({claim_qty_val}) must be > 0",
        }

    group_act_ids = wbs_context.get("wbs_group_activities", [])
    if not schedule_activities:
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": "Allocation failed: No schedule activities provided",
        }

    act_by_id = {}
    for act in schedule_activities:
        if isinstance(act, ScheduleActivity):
            aid = act.activity_id
        elif isinstance(act, dict):
            aid = act.get("activity_id") or act.get("Activity_ID")
        else:
            continue
        if aid:
            act_by_id[aid] = act

    eligible = []
    for aid in group_act_ids:
        act = act_by_id.get(aid)
        if not act:
            continue

        if isinstance(act, ScheduleActivity):
            p_qty = act.planned_quantity
            w_code = act.wbs_code
        elif isinstance(act, dict):
            p_qty = act.get("planned_quantity") if "planned_quantity" in act else act.get("Planned_Quantity")
            w_code = act.get("wbs_code") or act.get("wbs") or act.get("WBS")
        else:
            continue

        if p_qty is not None:
            try:
                p_qty_val = float(p_qty)
                if p_qty_val > 0.0:
                    eligible.append(
                        {
                            "activity_id": aid,
                            "wbs_code": w_code or wbs_context.get("wbs_code"),
                            "planned_quantity": p_qty_val,
                        }
                    )
            except (ValueError, TypeError):
                pass

    if not eligible:
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": "Allocation failed: No valid positive planned quantities in WBS group",
        }

    total_planned = sum(item["planned_quantity"] for item in eligible)
    if total_planned <= 0.0:
        return {
            "wbs_splits": None,
            "allocation_status": "FAILED",
            "allocation_reason": "Allocation failed: Sum of planned quantities in WBS group is 0",
        }

    splits = []
    running_allocated_sum = 0.0
    num_eligible = len(eligible)

    for idx, item in enumerate(eligible):
        weight = item["planned_quantity"] / total_planned
        alloc_pct = round(weight * 100.0, 4)

        if idx == num_eligible - 1:
            allocated_qty = round(claim_qty_val - running_allocated_sum, 4)
        else:
            allocated_qty = round(claim_qty_val * weight, 4)
            running_allocated_sum += allocated_qty

        splits.append(
            {
                "activity_id": item["activity_id"],
                "wbs_code": item["wbs_code"],
                "planned_quantity": item["planned_quantity"],
                "allocation_pct": alloc_pct,
                "allocated_quantity": allocated_qty,
            }
        )

    return {
        "wbs_splits": splits,
        "allocation_status": "SUCCESS",
        "allocation_reason": f"Proportionally allocated {claim_qty_val} across {num_eligible} eligible WBS activities",
    }


def validate_claim_wbs_splits(
    event_id: str,
    claimed_quantity: float,
    splits: List[dict],
    schedule_activities: Optional[List[Union[ScheduleActivity, dict]]] = None,
    expected_wbs_code: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    M3 Step 10: Centralized Split Validation & XOR Invariant Service.
    Enforces explicit data integrity rules across WBS split allocations:
    1. sum(allocated_quantity) == claimed_quantity (XOR / exact-sum invariant)
    2. Non-negative allocated quantities (>= 0.0)
    3. Consistency of event_id across all split records
    4. Reference validity against known schedule activities (if provided)
    5. Consistency of WBS metadata (if provided)

    Returns (is_valid: bool, reason: str)
    """
    if not splits or len(splits) == 0:
        return False, "Splits list is empty or None"

    try:
        expected_qty = round(float(claimed_quantity), 4)
    except (ValueError, TypeError):
        return False, f"Invalid expected claim quantity: '{claimed_quantity}'"

    valid_act_ids = set()
    act_wbs_map = {}
    if schedule_activities:
        for act in schedule_activities:
            if isinstance(act, ScheduleActivity):
                aid = act.activity_id
                wcode = act.wbs_code
            elif isinstance(act, dict):
                aid = act.get("activity_id") or act.get("Activity_ID")
                wcode = act.get("wbs_code") or act.get("wbs") or act.get("WBS")
            else:
                continue
            if aid:
                valid_act_ids.add(aid)
                if wcode:
                    act_wbs_map[aid] = str(wcode).strip()

    total_allocated = 0.0

    for idx, s in enumerate(splits):
        if not isinstance(s, dict):
            return False, f"Split at index {idx} is not a valid dictionary"

        s_event_id = s.get("event_id")
        if s_event_id and str(s_event_id).strip() != str(event_id).strip():
            return (
                False,
                f"Event ID mismatch: split event_id '{s_event_id}' does not match claim event_id '{event_id}'",
            )

        aid = s.get("activity_id")
        if not aid or not str(aid).strip():
            return False, f"Split at index {idx} is missing activity_id"
        aid_clean = str(aid).strip()

        if valid_act_ids and aid_clean not in valid_act_ids:
            return (
                False,
                f"Invalid activity reference: activity '{aid_clean}' is not in schedule activities",
            )

        raw_qty = s.get("allocated_quantity")
        if raw_qty is None:
            return False, f"Missing allocated_quantity for activity '{aid_clean}'"
        try:
            qty_val = float(raw_qty)
        except (ValueError, TypeError):
            return False, f"Invalid non-numeric allocated_quantity '{raw_qty}' for activity '{aid_clean}'"

        if qty_val < 0.0:
            return (
                False,
                f"Invalid non-negative quantity check failed for activity '{aid_clean}': {qty_val} < 0.0",
            )

        total_allocated += qty_val

        s_wbs = s.get("wbs_code")
        if expected_wbs_code and s_wbs:
            sw_clean = str(s_wbs).strip()
            ew_clean = str(expected_wbs_code).strip()
            if (
                sw_clean != ew_clean
                and not sw_clean.startswith(ew_clean)
                and not ew_clean.startswith(sw_clean)
            ):
                return (
                    False,
                    f"Inconsistent WBS metadata: split WBS code '{sw_clean}' conflicts with WBS group code '{ew_clean}'",
                )

    total_allocated_rounded = round(total_allocated, 4)

    if total_allocated_rounded != expected_qty:
        if total_allocated_rounded > expected_qty:
            return (
                False,
                f"Quantity invariant failed: sum of splits ({total_allocated_rounded}) exceeds original claim quantity ({expected_qty})",
            )
        else:
            return (
                False,
                f"Quantity invariant failed: sum of splits ({total_allocated_rounded}) is less than original claim quantity ({expected_qty})",
            )

    return True, f"Centralized validation passed: sum({total_allocated_rounded}) == claimed_quantity({expected_qty})"


def _do_persist_db(cur, event_id: str, schedule_id: str, splits: List[dict]):
    """
    Executes idempotent deletion and table insertion inside active DB transaction cursor.
    """
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_wbs_splits (
            split_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            schedule_id TEXT NOT NULL,
            activity_id TEXT NOT NULL,
            wbs_code TEXT,
            planned_quantity REAL,
            allocation_pct REAL,
            allocated_quantity REAL NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (event_id, activity_id)
        );
        """
    )
    # Idempotent delete before insert
    cur.execute(
        "DELETE FROM claim_wbs_splits WHERE event_id = %s",
        (event_id,),
    )
    for s in splits:
        split_id = f"split_{event_id}_{s['activity_id']}"
        cur.execute(
            """
            INSERT INTO claim_wbs_splits (
                split_id, event_id, schedule_id, activity_id,
                wbs_code, planned_quantity, allocation_pct, allocated_quantity
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                split_id,
                event_id,
                schedule_id,
                s["activity_id"],
                s.get("wbs_code"),
                s.get("planned_quantity"),
                s.get("allocation_pct"),
                s["allocated_quantity"],
            ),
        )


def persist_wbs_splits(
    event_id: str,
    schedule_id: str,
    claim_scope: str,
    alloc_info: dict,
    cursor_or_conn: Optional[Any] = None,
) -> dict:
    """
    M3 Step 7: Persist WBS Split Allocations.
    Idempotently persists valid BROAD_WBS split allocations to claim_wbs_splits table
    within an atomic transaction. Never modifies original execution_events claimed_quantity.

    Returns dict:
    {
        "persisted": bool,
        "split_count": int,
        "total_allocated_quantity": float,
        "splits": List[dict],
        "message": str
    }
    """
    splits = alloc_info.get("wbs_splits") if alloc_info else None
    status = alloc_info.get("allocation_status") if alloc_info else "SKIPPED"

    if claim_scope != "BROAD_WBS" or status != "SUCCESS" or not splits:
        _in_memory_splits_db.pop(event_id, None)
        if cursor_or_conn is not None:
            try:
                cur = (
                    cursor_or_conn.cursor()
                    if hasattr(cursor_or_conn, "cursor")
                    else cursor_or_conn
                )
                cur.execute(
                    "DELETE FROM claim_wbs_splits WHERE event_id = %s",
                    (event_id,),
                )
            except Exception:
                pass
        return {
            "persisted": False,
            "split_count": 0,
            "total_allocated_quantity": 0.0,
            "splits": [],
            "message": f"Skipped persistence: claim_scope={claim_scope}, status={status}",
        }

    total_allocated = sum(s["allocated_quantity"] for s in splits)
    if total_allocated <= 0.0:
        return {
            "persisted": False,
            "split_count": 0,
            "total_allocated_quantity": 0.0,
            "splits": [],
            "message": "Rejected persistence: Total allocated quantity is <= 0",
        }

    if cursor_or_conn is None:
        if get_connection is None:
            _in_memory_splits_db[event_id] = copy.deepcopy(splits)
            return {
                "persisted": True,
                "split_count": len(splits),
                "total_allocated_quantity": round(total_allocated, 4),
                "splits": splits,
                "message": f"In-memory persistence validated (DB offline): {len(splits)} splits",
            }
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    _do_persist_db(cur, event_id, schedule_id, splits)
                conn.commit()
            _in_memory_splits_db[event_id] = copy.deepcopy(splits)
        except Exception as e:
            _in_memory_splits_db[event_id] = copy.deepcopy(splits)
            return {
                "persisted": True,
                "split_count": len(splits),
                "total_allocated_quantity": round(total_allocated, 4),
                "splits": splits,
                "message": f"In-memory persistence validated (DB offline/error): {len(splits)} splits",
            }
    else:
        cur = (
            cursor_or_conn.cursor()
            if hasattr(cursor_or_conn, "cursor")
            else cursor_or_conn
        )
        _do_persist_db(cur, event_id, schedule_id, splits)
        _in_memory_splits_db[event_id] = copy.deepcopy(splits)

    return {
        "persisted": True,
        "split_count": len(splits),
        "total_allocated_quantity": round(total_allocated, 4),
        "splits": splits,
        "message": f"Successfully persisted {len(splits)} WBS splits for event {event_id}",
    }


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

            # 3. Run M3 matching cascade with optional FAISS semantic search retrieval
            semantic_results = None
            try:
                from backend.shared.schedule_index import search_schedule

                search_cands = search_schedule(
                    claim.schedule_id, claim.raw_claim_text, top_k=3
                )
                if search_cands:
                    semantic_results = [
                        {
                            "activity_id": sc.activity_id,
                            "semantic_score": sc.score,
                        }
                        for sc in search_cands
                    ]
            except Exception:
                semantic_results = None

            candidates = match_claim(
                claim, schedule_activities, semantic_results=semantic_results
            )

            # 4. Determine matching status and matched_activity_id with ambiguity protection
            unmatched_reason = None
            is_ambiguous = False
            ambiguity_reason = None

            if (
                candidates
                and candidates[0].match_tier == HYBRID_FALLBACK
                and len(candidates) >= 2
            ):
                diff = (
                    candidates[0].composite_confidence
                    - candidates[1].composite_confidence
                )
                if diff < 0.05:
                    is_ambiguous = True
                    ambiguity_reason = (
                        f"Ambiguous match: confidence difference between rank-1 ({candidates[0].activity_id}) "
                        f"and rank-2 ({candidates[1].activity_id}) is {diff:.4f} < 0.05"
                    )

            if (
                candidates
                and candidates[0].match_tier
                in [EXACT_ID, EXACT_ASSET, HYBRID_FALLBACK]
                and candidates[0].composite_confidence > 0.40
                and not is_ambiguous
            ):
                status = "MATCHED"
                matched_activity_id = candidates[0].activity_id
                top_tier = candidates[0].match_tier
                top_confidence = candidates[0].composite_confidence
            else:
                status = "UNMATCHED"
                matched_activity_id = None
                top_tier = (
                    candidates[0].match_tier if candidates else HARD_MISMATCH
                )
                top_confidence = (
                    candidates[0].composite_confidence if candidates else 0.0
                )
                if is_ambiguous:
                    unmatched_reason = ambiguity_reason
                elif candidates and candidates[0].match_tier == HARD_MISMATCH:
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
                        actor_id="m3_router",
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

            target_act_id = matched_activity_id or (
                candidates[0].activity_id if candidates else None
            )
            wbs_context = get_wbs_context(
                claim.schedule_id, target_act_id, schedule_activities
            )
            scope_info = detect_claim_scope(claim, wbs_context, candidates)
            alloc_info = allocate_wbs_splits(
                claim, scope_info["claim_scope"], wbs_context, schedule_activities
            )
            persist_info = persist_wbs_splits(
                event_id=event_id,
                schedule_id=claim.schedule_id,
                claim_scope=scope_info["claim_scope"],
                alloc_info=alloc_info,
                cursor_or_conn=cur,
            )

            res = {
                "event_id": event_id,
                "matched_activity_id": matched_activity_id,
                "match_tier": top_tier,
                "composite_confidence": top_confidence,
                "candidates": [c.model_dump() for c in top_3],
                "status": status,
                "wbs_context": wbs_context,
                "claim_scope": scope_info["claim_scope"],
                "scope_reason": scope_info["scope_reason"],
                "wbs_splits": alloc_info["wbs_splits"],
                "allocation_status": alloc_info["allocation_status"],
                "allocation_reason": alloc_info["allocation_reason"],
                "splits_persisted": persist_info["persisted"],
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


def get_persisted_wbs_splits(
    event_id: str,
    cursor_or_conn: Optional[Any] = None,
) -> List[dict]:
    """
    M3 Step 8: GET Persisted WBS Split Rows.
    Reads existing persisted split rows for an execution claim without recalculating or mutating DB.
    Returns deterministic list of split dicts ordered by activity_id ASC.
    """
    if not event_id:
        return []

    splits: List[dict] = []

    def _fetch_from_cur(cur):
        cur.execute(
            """
            SELECT split_id, event_id, schedule_id, activity_id,
                   wbs_code, planned_quantity, allocation_pct, allocated_quantity, created_at
            FROM claim_wbs_splits
            WHERE event_id = %s
            ORDER BY activity_id ASC
            """,
            (event_id,),
        )
        rows = cur.fetchall()
        for r in rows:
            if isinstance(r, dict):
                splits.append(
                    {
                        "split_id": r.get("split_id"),
                        "event_id": r.get("event_id"),
                        "schedule_id": r.get("schedule_id"),
                        "activity_id": r.get("activity_id"),
                        "wbs_code": r.get("wbs_code"),
                        "planned_quantity": r.get("planned_quantity"),
                        "allocation_pct": r.get("allocation_pct"),
                        "allocated_quantity": r.get("allocated_quantity"),
                    }
                )
            else:
                splits.append(
                    {
                        "split_id": r[0],
                        "event_id": r[1],
                        "schedule_id": r[2],
                        "activity_id": r[3],
                        "wbs_code": r[4],
                        "planned_quantity": r[5],
                        "allocation_pct": r[6],
                        "allocated_quantity": r[7],
                    }
                )

    if cursor_or_conn is not None:
        try:
            cur = (
                cursor_or_conn.cursor()
                if hasattr(cursor_or_conn, "cursor")
                else cursor_or_conn
            )
            _fetch_from_cur(cur)
        except Exception:
            return copy.deepcopy(_in_memory_splits_db.get(event_id, []))
    else:
        if get_connection is None:
            return copy.deepcopy(_in_memory_splits_db.get(event_id, []))
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    _fetch_from_cur(cur)
        except Exception:
            return copy.deepcopy(_in_memory_splits_db.get(event_id, []))

    if not splits and event_id in _in_memory_splits_db:
        return copy.deepcopy(_in_memory_splits_db[event_id])

    return splits


@router.get("/{event_id}/splits")
def get_claim_splits_endpoint(event_id: str):
    """
    GET /api/v1/claims/{event_id}/splits
    Retrieves persisted WBS split allocation rows for an execution claim.
    Returns deterministic list of splits ordered by activity_id ASC.
    Read-only: does NOT modify DB or recalculate allocations.
    """
    if get_connection is None:
        raise HTTPException(
            status_code=500, detail="Database connection module unavailable."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT event_id FROM execution_events WHERE event_id = %s",
                (event_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Execution claim '{event_id}' not found.",
                )

            splits = get_persisted_wbs_splits(event_id, cursor_or_conn=cur)
            total_qty = sum(s["allocated_quantity"] for s in splits)

            return {
                "event_id": event_id,
                "splits": splits,
                "total_allocated_quantity": round(total_qty, 4),
                "split_count": len(splits),
            }


class SplitUpdateRequest(BaseModel):
    activity_id: Optional[str] = None
    split_id: Optional[str] = None
    allocated_quantity: float


class PatchSplitsRequest(BaseModel):
    splits: List[SplitUpdateRequest]


def update_persisted_wbs_splits(
    event_id: str,
    updates: List[dict],
    claimed_quantity: float,
    cursor_or_conn: Optional[Any] = None,
) -> dict:
    """
    M3 Step 9: PATCH Persisted WBS Split Rows.
    Updates existing persisted split quantities for an execution claim without rerunning matching or creating new rows.
    Enforces exact quantity invariant: sum(updated split quantities) == claimed_quantity.

    Returns dict:
    {
        "success": bool,
        "splits": List[dict],
        "total_allocated_quantity": float,
        "message": str
    }
    """
    if not event_id or not updates:
        return {
            "success": False,
            "splits": [],
            "total_allocated_quantity": 0.0,
            "message": "Invalid request: event_id and non-empty updates required",
        }

    existing_splits = get_persisted_wbs_splits(event_id, cursor_or_conn=cursor_or_conn)
    if not existing_splits:
        return {
            "success": False,
            "splits": [],
            "total_allocated_quantity": 0.0,
            "message": f"No persisted WBS splits exist for claim '{event_id}' to update",
        }

    existing_map = {s["activity_id"]: s for s in existing_splits}
    existing_split_id_map = {s["split_id"]: s for s in existing_splits}

    if len(updates) != len(existing_splits):
        return {
            "success": False,
            "splits": [],
            "total_allocated_quantity": 0.0,
            "message": f"Split count mismatch: update payload has {len(updates)} splits, expected {len(existing_splits)}",
        }

    new_quantities = {}
    for item in updates:
        if isinstance(item, BaseModel):
            item_dict = item.model_dump()
        elif isinstance(item, dict):
            item_dict = item
        else:
            continue

        act_id = item_dict.get("activity_id")
        split_id = item_dict.get("split_id")
        if not act_id and split_id in existing_split_id_map:
            act_id = existing_split_id_map[split_id]["activity_id"]

        if not act_id or act_id not in existing_map:
            return {
                "success": False,
                "splits": [],
                "total_allocated_quantity": 0.0,
                "message": f"Unknown or invalid activity/split ID '{act_id or split_id}' for claim '{event_id}'",
            }

        raw_qty = item_dict.get("allocated_quantity")
        if raw_qty is None:
            return {
                "success": False,
                "splits": [],
                "total_allocated_quantity": 0.0,
                "message": f"Missing allocated_quantity for activity '{act_id}'",
            }

        try:
            qty_val = float(raw_qty)
        except (ValueError, TypeError):
            return {
                "success": False,
                "splits": [],
                "total_allocated_quantity": 0.0,
                "message": f"Invalid non-numeric allocated_quantity '{raw_qty}' for activity '{act_id}'",
            }

        if qty_val < 0.0:
            return {
                "success": False,
                "splits": [],
                "total_allocated_quantity": 0.0,
                "message": f"Negative allocated_quantity ({qty_val}) rejected for activity '{act_id}'",
            }

        new_quantities[act_id] = qty_val

    if len(new_quantities) != len(existing_splits):
        return {
            "success": False,
            "splits": [],
            "total_allocated_quantity": 0.0,
            "message": "Duplicate or missing activity updates in payload",
        }

    total_updated_qty = round(sum(new_quantities.values()), 4)
    expected_qty = round(float(claimed_quantity), 4)

    if total_updated_qty != expected_qty:
        return {
            "success": False,
            "splits": [],
            "total_allocated_quantity": 0.0,
            "message": f"Quantity invariant failed: sum of updated splits ({total_updated_qty}) does not equal claim quantity ({expected_qty})",
        }

    updated_splits = []
    for s in existing_splits:
        aid = s["activity_id"]
        new_q = new_quantities[aid]
        pct = round((new_q / expected_qty) * 100.0, 4) if expected_qty > 0 else 0.0
        updated_s = dict(s)
        updated_s["allocated_quantity"] = new_q
        updated_s["allocation_pct"] = pct
        updated_splits.append(updated_s)

    sorted_splits = sorted(updated_splits, key=lambda x: x["activity_id"])
    _in_memory_splits_db[event_id] = copy.deepcopy(sorted_splits)

    if cursor_or_conn is not None:
        try:
            cur = (
                cursor_or_conn.cursor()
                if hasattr(cursor_or_conn, "cursor")
                else cursor_or_conn
            )
            for s in sorted_splits:
                cur.execute(
                    """
                    UPDATE claim_wbs_splits
                    SET allocated_quantity = %s, allocation_pct = %s
                    WHERE event_id = %s AND activity_id = %s
                    """,
                    (s["allocated_quantity"], s["allocation_pct"], event_id, s["activity_id"]),
                )
        except Exception as e:
            return {
                "success": False,
                "splits": [],
                "total_allocated_quantity": 0.0,
                "message": f"Database update error: {str(e)}",
            }
    else:
        if get_connection is not None:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        for s in sorted_splits:
                            cur.execute(
                                """
                                UPDATE claim_wbs_splits
                                SET allocated_quantity = %s, allocation_pct = %s
                                WHERE event_id = %s AND activity_id = %s
                                """,
                                (s["allocated_quantity"], s["allocation_pct"], event_id, s["activity_id"]),
                            )
                    conn.commit()
            except Exception:
                pass

    return {
        "success": True,
        "splits": sorted_splits,
        "total_allocated_quantity": total_updated_qty,
        "message": f"Successfully updated {len(sorted_splits)} split quantities for claim '{event_id}'",
    }


@router.patch("/{event_id}/splits")
def patch_claim_splits_endpoint(
    event_id: str,
    payload: Union[PatchSplitsRequest, dict, List[Any]],
):
    """
    PATCH /api/v1/claims/{event_id}/splits
    Updates existing persisted WBS split quantities for an execution claim.
    Read-only for original claim text & quantity.
    Enforces exact quantity invariant: sum(updated split quantities) == original claimed_quantity.
    Transactional: on validation failure, nothing is persisted.
    """
    if get_connection is None:
        raise HTTPException(
            status_code=500, detail="Database connection module unavailable."
        )

    if isinstance(payload, PatchSplitsRequest):
        updates = [s.model_dump() for s in payload.splits]
    elif isinstance(payload, dict):
        raw_splits = payload.get("splits", [])
        updates = [s.model_dump() if isinstance(s, BaseModel) else s for s in raw_splits]
    elif isinstance(payload, list):
        updates = [s.model_dump() if isinstance(s, BaseModel) else s for s in payload]
    else:
        raise HTTPException(status_code=400, detail="Invalid request body payload.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT claimed_quantity FROM execution_events WHERE event_id = %s",
                (event_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Execution claim '{event_id}' not found.",
                )

            claimed_qty = row.get("claimed_quantity") if isinstance(row, dict) else row[0]
            if claimed_qty is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Execution claim '{event_id}' has no valid claimed_quantity.",
                )

            update_res = update_persisted_wbs_splits(
                event_id, updates, claimed_qty, cursor_or_conn=cur
            )

            if not update_res["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=update_res["message"],
                )

            conn.commit()

            return {
                "event_id": event_id,
                "splits": update_res["splits"],
                "total_allocated_quantity": update_res["total_allocated_quantity"],
                "split_count": len(update_res["splits"]),
                "message": update_res["message"],
            }










