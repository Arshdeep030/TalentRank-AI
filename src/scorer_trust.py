from __future__ import annotations

from src.schemas import CandidateProfile, JobScorecard


def score_trust(candidate: CandidateProfile, scorecard: JobScorecard, trust_config: dict) -> tuple[float, list[str]]:
    penalties: list[str] = []
    score = 100.0
    signals = candidate.activity_signals

    if candidate.trust_features.get("salary_inverted"):
        score -= float(trust_config["bad_salary_penalty"])
        penalties.append("inverted salary range")

    expert_short_skills = 0
    for skill in candidate.skill_details:
        if skill.get("proficiency") == "expert" and int(skill.get("duration_months", 0) or 0) <= int(trust_config["suspicious_expert_duration_max_months"]):
            expert_short_skills += 1
    if expert_short_skills >= int(trust_config["suspicious_skill_count"]):
        score -= 18.0
        penalties.append("too many expert skills with short durations")

    consulting_only = bool(candidate.career_history) and all(
        job.get("company") in set(scorecard.consulting_companies)
        for job in candidate.career_history
    )
    if consulting_only:
        score -= float(trust_config["consulting_only_penalty"])
        penalties.append("consulting-only career history")

    if not candidate.trust_features.get("verified_email"):
        score -= 4.0
        penalties.append("email not verified")
    if not candidate.trust_features.get("verified_phone"):
        score -= 3.0
        penalties.append("phone not verified")

    if signals.get("github_activity_score", -1) == -1 and any(
        skill.lower() in {"python", "ml", "ai", "machine learning", "fine-tuning llms"}
        for skill in candidate.skills
    ):
        score -= 5.0
        penalties.append("no GitHub linked despite AI-heavy profile")

    return max(0.0, min(100.0, score)), penalties
