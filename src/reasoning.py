from __future__ import annotations

from datetime import datetime
from src.schemas import CandidateProfile, CandidateScores
from src.scorer_availability import REFERENCE_DATE


def determine_main_concern(candidate: CandidateProfile, penalties: list[str], fit_details: dict) -> str:
    # 1. Inactivity check
    signals = candidate.activity_signals
    last_active_str = signals.get("last_active_date")
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            days_since_active = (REFERENCE_DATE - last_active).days
            if days_since_active > 180:
                return "Inactive >180 days"
        except Exception:
            pass

    # 2. AI skills authenticity
    for p in penalties:
        if "AI-heavy skills lack supporting" in p or "limited work evidence behind AI" in p or "AI skills not supported" in p:
            return "AI skills not supported by career history"

    # 3. Research heavy
    for p in penalties:
        if "research-heavy profile" in p or "research orientation stronger" in p:
            return "Research-heavy background"

    # 4. Notice period >= 60 days
    try:
        notice_period = int(signals.get("notice_period_days", 180))
        if notice_period >= 60:
            return f"{notice_period}-day notice period"
    except Exception:
        pass

    # 5. Limited ranking-system evidence
    if not fit_details.get("has_ranking_evidence", True):
        return "Limited ranking-system evidence"

    # 6. General penalties
    for p in penalties:
        if "consulting-only" in p:
            return "Consulting-only career history"
        if "too many expert skills" in p:
            return "Too many short-duration expert skills"
        if "keyword stuffing" in p or "title-skill mismatch" in p:
            return "Title-skill mismatch (keyword stuffing)"
        if "salary" in p:
            return "Inverted salary expectations"

    return ""


def generate_reasoning(candidate: CandidateProfile, scores: CandidateScores) -> str:
    positives = scores.strengths[:3]
    concerns = scores.penalties[:1]
    lines: list[str] = []

    if positives:
        lines.append(
            f"Currently {candidate.current_title} with {candidate.years_experience:.1f} years experience; "
            + "; ".join(positives[:2])
            + "."
        )
    else:
        lines.append(f"{candidate.years_experience:.1f} years of experience with partial alignment to the role.")

    if candidate.activity_signals.get("open_to_work_flag"):
        lines.append("Open to work and shows usable recruiter engagement.")
    elif concerns:
        lines.append(f"Main concern: {concerns[0]}.")
    else:
        lines.append("Some availability or profile-quality tradeoffs keep this candidate below the very top tier.")

    return " ".join(lines[:2])

