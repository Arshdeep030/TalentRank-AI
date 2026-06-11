from __future__ import annotations

from datetime import date, datetime

from src.schemas import CandidateProfile


REFERENCE_DATE = date(2026, 6, 10)


def score_availability(candidate: CandidateProfile, stale_days: int, ideal_notice_days: int, acceptable_notice_days: int) -> tuple[float, list[str]]:
    signals = candidate.activity_signals
    strengths: list[str] = []
    score = 0.0

    if signals.get("open_to_work_flag"):
        score += 25.0
        strengths.append("open to work")

    response_rate = float(signals.get("recruiter_response_rate", 0.0))
    score += min(20.0, response_rate * 25.0)
    if response_rate >= 0.5:
        strengths.append(f"good recruiter response rate ({response_rate:.2f})")

    interview_completion_rate = float(signals.get("interview_completion_rate", 0.0))
    score += min(15.0, interview_completion_rate * 15.0)

    last_active = datetime.strptime(signals["last_active_date"], "%Y-%m-%d").date()
    days_since_active = (REFERENCE_DATE - last_active).days
    recency_score = max(0.0, 20.0 * (1.0 - min(days_since_active, stale_days) / stale_days))
    score += recency_score
    if days_since_active <= 30:
        strengths.append("recently active")

    notice_period = int(signals.get("notice_period_days", 180))
    if notice_period <= ideal_notice_days:
        score += 15.0
        strengths.append(f"short notice period ({notice_period} days)")
    elif notice_period <= acceptable_notice_days:
        score += 10.0
    elif notice_period <= 90:
        score += 5.0

    profile_completeness = float(signals.get("profile_completeness_score", 0.0))
    score += min(5.0, profile_completeness / 20.0)

    return min(100.0, score), strengths
