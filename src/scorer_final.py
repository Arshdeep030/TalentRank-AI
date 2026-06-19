from __future__ import annotations

from src.schemas import CandidateScores


def blend_scores(
    candidate_id: str,
    retrieval_score: float,
    fit_score: float,
    availability_score: float,
    trust_score: float,
    growth_score: float,
    fit_details: dict,
    weights: dict,
    penalties: list[str],
    strengths: list[str],
    main_concern: str = "",
) -> CandidateScores:
    scoring = weights["scoring"]
    final_score = (
        scoring["fit_weight"] * fit_score
        + scoring["availability_weight"] * availability_score
        + scoring["trust_weight"] * trust_score
        + scoring["growth_weight"] * growth_score
    )
    return CandidateScores(
        candidate_id=candidate_id,
        retrieval_score=retrieval_score,
        fit_score=fit_score,
        availability_score=availability_score,
        trust_score=trust_score,
        growth_score=growth_score,
        career_depth_score=float(fit_details.get("career_depth_score", 0.0)),
        fit_category=str(fit_details.get("fit_category", "")),
        final_score=final_score,
        penalties=penalties,
        strengths=strengths,
        main_concern=main_concern,
    )
