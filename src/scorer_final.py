from __future__ import annotations

from src.schemas import CandidateScores


def blend_scores(
    candidate_id: str,
    retrieval_score: float,
    fit_score: float,
    availability_score: float,
    trust_score: float,
    growth_score: float,
    weights: dict,
    penalties: list[str],
    strengths: list[str],
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
        final_score=final_score,
        penalties=penalties,
        strengths=strengths,
    )
