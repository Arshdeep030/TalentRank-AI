from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobScorecard:
    role_name: str
    seniority: str
    must_have: list[str]
    nice_to_have: list[str]
    negative_signals: list[str]
    preferred_locations: list[str]
    positive_keywords: list[str]
    title_positives: list[str]
    target_experience_years: dict[str, float]
    location_rules: dict[str, object]
    work_mode: dict[str, list[str]]
    hard_filters: dict[str, float]
    consulting_companies: list[str]
    raw_text: str = ""


@dataclass
class CandidateProfile:
    candidate_id: str
    years_experience: float
    current_title: str
    current_company: str
    current_industry: str
    current_location: str
    country: str
    summary: str
    headline: str
    skills: list[str]
    skill_details: list[dict]
    career_history: list[dict]
    education: list[dict]
    certifications: list[dict]
    languages: list[dict]
    activity_signals: dict
    salary_data: dict
    trust_features: dict = field(default_factory=dict)
    search_text: str = ""


@dataclass
class CandidateScores:
    candidate_id: str
    retrieval_score: float
    fit_score: float
    availability_score: float
    trust_score: float
    growth_score: float
    final_score: float
    career_depth_score: float = 0.0
    fit_category: str = ""
    main_concern: str = ""
    penalties: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
