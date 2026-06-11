from __future__ import annotations

from src.schemas import CandidateProfile


def honeypot_penalties(candidate: CandidateProfile) -> tuple[float, list[str]]:
    penalty = 0.0
    reasons: list[str] = []
    signals = candidate.activity_signals

    if candidate.current_title.lower() in {"marketing manager", "graphic designer", "sales executive"}:
        ai_skill_count = sum(
            1
            for skill in candidate.skills
            if skill.lower() in {
                "fine-tuning llms",
                "peft",
                "lora",
                "milvus",
                "nlp",
                "information retrieval",
                "ranking",
                "embeddings",
            }
        )
        if ai_skill_count >= 5:
            penalty += 15.0
            reasons.append("title-skill mismatch suggests keyword stuffing")

    if signals.get("profile_completeness_score", 0.0) < 35 and signals.get("saved_by_recruiters_30d", 0) > 8:
        penalty += 6.0
        reasons.append("engagement inconsistent with sparse profile")

    if candidate.trust_features.get("salary_inverted"):
        penalty += 5.0
        reasons.append("invalid salary expectation structure")

    return penalty, reasons
