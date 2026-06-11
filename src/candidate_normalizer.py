from __future__ import annotations

from src.schemas import CandidateProfile


def normalize_candidate(record: dict) -> CandidateProfile:
    profile = record["profile"]
    redrob = record["redrob_signals"]
    skills = [skill["name"] for skill in record.get("skills", [])]
    search_parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        " ".join(skills),
        " ".join(job.get("title", "") for job in record.get("career_history", [])),
        " ".join(job.get("description", "") for job in record.get("career_history", [])),
    ]
    trust_features = {
        "salary_inverted": redrob["expected_salary_range_inr_lpa"]["min"] > redrob["expected_salary_range_inr_lpa"]["max"],
        "linkedin_connected": redrob.get("linkedin_connected", False),
        "verified_email": redrob.get("verified_email", False),
        "verified_phone": redrob.get("verified_phone", False),
    }
    return CandidateProfile(
        candidate_id=record["candidate_id"],
        years_experience=float(profile.get("years_of_experience", 0.0)),
        current_title=profile.get("current_title", ""),
        current_company=profile.get("current_company", ""),
        current_industry=profile.get("current_industry", ""),
        current_location=profile.get("location", ""),
        country=profile.get("country", ""),
        summary=profile.get("summary", ""),
        headline=profile.get("headline", ""),
        skills=skills,
        skill_details=record.get("skills", []),
        career_history=record.get("career_history", []),
        education=record.get("education", []),
        certifications=record.get("certifications", []),
        languages=record.get("languages", []),
        activity_signals=redrob,
        salary_data=redrob.get("expected_salary_range_inr_lpa", {}),
        trust_features=trust_features,
        search_text=" ".join(part for part in search_parts if part).lower(),
    )
