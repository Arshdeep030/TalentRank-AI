from __future__ import annotations

from src.schemas import CandidateProfile


LEADERSHIP_TERMS = {"lead", "manager", "head", "director", "staff", "principal"}


def score_growth(candidate: CandidateProfile, growth_config: dict) -> tuple[float, list[str]]:
    strengths: list[str] = []
    score = 35.0
    titles = [job.get("title", "") for job in candidate.career_history]
    if len(titles) >= 2 and titles[0] != titles[-1]:
        score += float(growth_config["title_progression_bonus"])
        strengths.append("career title progression")

    if any(term in candidate.current_title.lower() for term in LEADERSHIP_TERMS):
        score += float(growth_config["leadership_bonus"])
        strengths.append("leadership signals in current title")

    long_tenures = sum(1 for job in candidate.career_history if int(job.get("duration_months", 0)) >= 24)
    score += min(20.0, long_tenures * 5.0)
    if long_tenures >= 2:
        strengths.append("multiple sustained role tenures")

    if candidate.years_experience >= 6:
        score += 10.0

    return min(100.0, score), strengths
