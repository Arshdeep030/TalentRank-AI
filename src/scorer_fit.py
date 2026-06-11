from __future__ import annotations

import re

from src.schemas import CandidateProfile, JobScorecard


def score_fit(candidate: CandidateProfile, scorecard: JobScorecard) -> tuple[float, list[str]]:
    strengths: list[str] = []
    score = 0.0
    skill_text = " ".join(candidate.skills).lower()
    full_text = f"{candidate.search_text} {candidate.current_title.lower()} {candidate.current_industry.lower()}"

    must_matches = sum(1 for item in scorecard.must_have if item.lower() in full_text or item.lower() in skill_text)
    nice_matches = sum(1 for item in scorecard.nice_to_have if item.lower() in full_text or item.lower() in skill_text)
    title_match = any(title.lower() in candidate.current_title.lower() for title in scorecard.title_positives)
    retrieval_terms = len(re.findall(r"\b(retrieval|ranking|search|recommendation|relevance|embedding|vector)\b", full_text))
    product_background = any(job.get("industry", "") in {"Software", "Fintech", "E-commerce", "EdTech", "Food Delivery"} for job in candidate.career_history)

    score += min(45.0, must_matches * 6.0)
    score += min(15.0, nice_matches * 3.0)
    score += min(15.0, retrieval_terms * 2.5)
    if title_match:
        score += 10.0
        strengths.append(f"title aligned as {candidate.current_title}")
    if product_background:
        score += 8.0
        strengths.append("product-oriented career history")

    experience = candidate.years_experience
    ideal_min = scorecard.target_experience_years["ideal_min"]
    ideal_max = scorecard.target_experience_years["ideal_max"]
    if ideal_min <= experience <= ideal_max:
        score += 12.0
        strengths.append(f"{experience:.1f} years of experience in target band")
    elif scorecard.target_experience_years["min"] <= experience <= scorecard.target_experience_years["max"]:
        score += 8.0
    else:
        score += max(0.0, 8.0 - abs(experience - ideal_min))

    if must_matches >= max(3, len(scorecard.must_have) // 2):
        strengths.append(f"matches {must_matches} must-have requirements")

    return min(100.0, score), strengths
