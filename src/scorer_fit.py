from __future__ import annotations

import re

from src.schemas import CandidateProfile, JobScorecard


CAREER_RELEVANCE_PATTERNS = {
    "retrieval": r"\b(retrieval|semantic search|vector search|hybrid search|dense retrieval|sparse retrieval)\b",
    "ranking": r"\b(ranking|relevance|learning to rank|ltr|ndcg|mrr|map)\b",
    "recommendation": r"\b(recommendation|personalization|recommendation system)\b",
    "search": r"\b(search engine|search quality|information retrieval|query understanding)\b",
    "embeddings": r"\b(embedding|embeddings|sentence transformers|bge|e5)\b",
    "vector": r"\b(faiss|milvus|qdrant|weaviate|pinecone|pgvector|elasticsearch|opensearch)\b",
    "evaluation": r"\b(a/b test|offline eval|online eval|ranking evaluation|precision@k|recall@k)\b",
}

AI_SIGNAL_PATTERNS = (
    r"\b(rag|llm|langchain|openai|anthropic|gpt|vector db|embedding)\b",
)

PRODUCT_INDUSTRIES = {
    "Software",
    "Fintech",
    "E-commerce",
    "EdTech",
    "Food Delivery",
    "AI/ML",
    "SaaS",
}

PRODUCT_COMPANIES = {
    "Google",
    "Amazon",
    "Swiggy",
    "Zomato",
    "Flipkart",
    "Meesho",
    "Razorpay",
    "Atlassian",
    "Freshworks",
    "Paytm",
    "Microsoft",
    "Sarvam AI",
}

CAREER_DEPTH_WINDOW_MONTHS = 18
EVALUATION_PATTERN = r"\b(ndcg|mrr|map|a/b test|ab testing|offline eval|online eval|ranking evaluation|relevance metrics|precision@k|recall@k)\b"
PRODUCTION_PATTERN = r"\b(production|deployed|shipped|latency|real-time|serving|scale|scaled|users|pipeline|on-call|inference|microservice)\b"
RESEARCH_TITLE_PATTERN = r"\b(applied scientist|research scientist|research engineer|scientist)\b"


def _career_text(candidate: CandidateProfile) -> str:
    return " ".join(
        f"{job.get('title', '')} {job.get('description', '')}".lower()
        for job in candidate.career_history
    )


def _career_relevance_score(career_text: str) -> tuple[float, list[str], int]:
    matched_axes = []
    raw_hits = 0
    for axis, pattern in CAREER_RELEVANCE_PATTERNS.items():
        if re.search(pattern, career_text):
            matched_axes.append(axis)
            raw_hits += len(re.findall(pattern, career_text))

    score = min(22.0, len(matched_axes) * 3.0 + min(raw_hits, 8) * 1.0)
    strengths: list[str] = []
    if matched_axes:
        summary_axes = ", ".join(matched_axes[:3])
        strengths.append(f"career history shows {summary_axes} work")
    return score, strengths, len(matched_axes)


def _career_depth_score(candidate: CandidateProfile) -> tuple[float, list[str]]:
    relevant_months = 0
    relevant_roles = 0
    for job in candidate.career_history:
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        is_relevant = any(re.search(pattern, job_text) for pattern in CAREER_RELEVANCE_PATTERNS.values())
        if is_relevant:
            relevant_roles += 1
            relevant_months += int(job.get("duration_months", 0) or 0)

    score = 0.0
    strengths: list[str] = []
    if relevant_months >= 60:
        score += 10.0
        strengths.append("deep multi-year retrieval/ranking experience")
    elif relevant_months >= 36:
        score += 7.0
        strengths.append("several years of relevant search or ranking work")
    elif relevant_months >= CAREER_DEPTH_WINDOW_MONTHS:
        score += 4.0
        strengths.append("meaningful hands-on depth in relevant systems")

    if relevant_roles >= 2:
        score += 2.0
        strengths.append("relevant work repeated across multiple roles")

    return min(12.0, score), strengths


def categorize_candidate_fit(career_text: str) -> str:
    matched_axes = {
        axis for axis, pattern in CAREER_RELEVANCE_PATTERNS.items() if re.search(pattern, career_text)
    }
    if {"retrieval", "search"} & matched_axes and {"embeddings", "vector"} & matched_axes:
        return "search_retrieval"
    if "ranking" in matched_axes:
        return "ranking_relevance"
    if "recommendation" in matched_axes:
        return "recommendation"
    if "embeddings" in matched_axes:
        return "nlp"
    return "general_ml"


def _evaluation_experience_score(candidate: CandidateProfile, career_text: str) -> tuple[float, list[str]]:
    skill_text = " ".join(candidate.skills).lower()
    evidence_hits = len(re.findall(EVALUATION_PATTERN, career_text))
    skill_hits = len(re.findall(EVALUATION_PATTERN, skill_text))
    score = min(8.0, evidence_hits * 3.0 + skill_hits * 1.0)
    strengths: list[str] = []
    if evidence_hits > 0:
        strengths.append("evaluation metrics appear in work history")
    return score, strengths


def _location_bonus(candidate: CandidateProfile, scorecard: JobScorecard) -> tuple[float, list[str]]:
    location = candidate.current_location.lower()
    country = candidate.country.lower()
    preferred = [item.lower() for item in scorecard.preferred_locations]
    strengths: list[str] = []
    if any(item in location for item in preferred):
        strengths.append("located in preferred hiring geography")
        return 4.0, strengths
    if country == "india":
        return 1.5, strengths
    if candidate.activity_signals.get("willing_to_relocate"):
        strengths.append("open to relocation")
        return 1.0, strengths
    return 0.0, strengths


def _research_penalty(candidate: CandidateProfile, career_text: str) -> tuple[float, list[str]]:
    title_text = " ".join(
        [candidate.current_title] + [job.get("title", "") for job in candidate.career_history]
    ).lower()
    penalties: list[str] = []
    if not re.search(RESEARCH_TITLE_PATTERN, title_text):
        return 0.0, penalties

    production_hits = len(re.findall(PRODUCTION_PATTERN, career_text))
    research_hits = len(re.findall(RESEARCH_TITLE_PATTERN, title_text))
    if research_hits and production_hits == 0:
        penalties.append("research-heavy profile with weak production evidence")
        return 10.0, penalties
    if research_hits and production_hits <= 1:
        penalties.append("research orientation stronger than production evidence")
        return 5.0, penalties
    return 0.0, penalties


def _product_company_score(candidate: CandidateProfile) -> tuple[float, list[str]]:
    score = 0.0
    strengths: list[str] = []
    product_company_hits = sum(
        1 for job in candidate.career_history if job.get("company", "") in PRODUCT_COMPANIES
    )
    product_industry_hits = sum(
        1 for job in candidate.career_history if job.get("industry", "") in PRODUCT_INDUSTRIES
    )

    if product_company_hits:
        score += min(8.0, product_company_hits * 3.0)
        strengths.append("worked at product-oriented companies")
    if product_industry_hits >= 2:
        score += 6.0
        strengths.append("multiple product-industry roles")
    elif product_industry_hits == 1:
        score += 3.0

    return score, strengths


def _ai_authenticity_adjustment(candidate: CandidateProfile, career_text: str) -> tuple[float, list[str], list[str]]:
    skills_text = " ".join(candidate.skills).lower()
    declared_ai_signals = len(re.findall(AI_SIGNAL_PATTERNS[0], skills_text))
    career_ai_support = len(re.findall(AI_SIGNAL_PATTERNS[0], career_text))
    authenticity_score = 0.0
    strengths: list[str] = []
    penalties: list[str] = []

    if career_ai_support >= 2:
        authenticity_score += 8.0
        strengths.append("AI claims supported by work history")
    elif declared_ai_signals >= 4 and career_ai_support == 0:
        authenticity_score -= 10.0
        penalties.append("AI-heavy skills lack supporting work history")
    elif declared_ai_signals >= 2 and career_ai_support == 0:
        authenticity_score -= 5.0
        penalties.append("limited work evidence behind AI skills")

    return authenticity_score, strengths, penalties


def score_fit(candidate: CandidateProfile, scorecard: JobScorecard) -> tuple[float, list[str], list[str], dict]:
    strengths: list[str] = []
    penalties: list[str] = []
    score = 0.0
    skill_text = " ".join(candidate.skills).lower()
    full_text = f"{candidate.search_text} {candidate.current_title.lower()} {candidate.current_industry.lower()}"
    career_text = _career_text(candidate)

    must_matches = sum(1 for item in scorecard.must_have if item.lower() in full_text or item.lower() in skill_text)
    nice_matches = sum(1 for item in scorecard.nice_to_have if item.lower() in full_text or item.lower() in skill_text)
    title_match = any(title.lower() in candidate.current_title.lower() for title in scorecard.title_positives)
    retrieval_terms = len(re.findall(r"\b(retrieval|ranking|search|recommendation|relevance|embedding|vector)\b", full_text))
    product_background = any(job.get("industry", "") in PRODUCT_INDUSTRIES for job in candidate.career_history)
    career_relevance_score, career_strengths, matched_axes = _career_relevance_score(career_text)
    career_depth_score, career_depth_strengths = _career_depth_score(candidate)
    evaluation_score, evaluation_strengths = _evaluation_experience_score(candidate, career_text)
    product_company_score, product_strengths = _product_company_score(candidate)
    location_bonus, location_strengths = _location_bonus(candidate, scorecard)
    research_penalty, research_penalties = _research_penalty(candidate, career_text)
    ai_authenticity_score, ai_strengths, ai_penalties = _ai_authenticity_adjustment(candidate, career_text)
    fit_category = categorize_candidate_fit(career_text)

    score += min(18.0, must_matches * 2.8)
    score += min(6.0, nice_matches * 1.5)
    score += min(4.0, retrieval_terms * 0.8)
    score += career_relevance_score
    score += career_depth_score
    score += evaluation_score
    score += product_company_score
    score += location_bonus
    score += ai_authenticity_score
    score -= research_penalty
    strengths.extend(
        career_strengths
        + career_depth_strengths
        + evaluation_strengths
        + product_strengths
        + location_strengths
        + ai_strengths
    )
    penalties.extend(ai_penalties + research_penalties)

    if title_match:
        score += 5.0
        strengths.append(f"title aligned as {candidate.current_title}")
    if product_background:
        score += 2.0
        strengths.append("product-oriented career history")

    experience = candidate.years_experience
    ideal_min = scorecard.target_experience_years["ideal_min"]
    ideal_max = scorecard.target_experience_years["ideal_max"]
    if ideal_min <= experience <= ideal_max:
        score += 10.0
        strengths.append(f"{experience:.1f} years of experience in target band")
    elif scorecard.target_experience_years["min"] <= experience <= scorecard.target_experience_years["max"]:
        score += 6.0
    else:
        score += max(0.0, 4.0 - abs(experience - ideal_min) * 0.6)

    if must_matches >= max(3, len(scorecard.must_have) // 2):
        strengths.append(f"matches {must_matches} must-have requirements")
    if matched_axes >= 3:
        strengths.append("strong retrieval/ranking relevance in actual work")

    score = min(98.0, max(0.0, score))

    has_ranking_evidence = bool(re.search(CAREER_RELEVANCE_PATTERNS["ranking"], career_text))

    return score, strengths, penalties, {
        "career_depth_score": career_depth_score,
        "fit_category": fit_category,
        "evaluation_score": evaluation_score,
        "research_penalty": research_penalty,
        "has_ranking_evidence": has_ranking_evidence,
    }
