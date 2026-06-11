from __future__ import annotations

from src.schemas import CandidateProfile, CandidateScores


def generate_reasoning(candidate: CandidateProfile, scores: CandidateScores) -> str:
    positives = scores.strengths[:3]
    concerns = scores.penalties[:1]
    lines: list[str] = []

    if positives:
        lines.append("; ".join(positives).capitalize() + ".")
    else:
        lines.append(f"{candidate.years_experience:.1f} years of experience with partial alignment to the role.")

    if candidate.activity_signals.get("open_to_work_flag"):
        lines.append("Open to work and shows usable recruiter engagement.")
    elif concerns:
        lines.append(f"Main concern: {concerns[0]}.")
    else:
        lines.append("Some availability or profile-quality tradeoffs keep this candidate below the very top tier.")

    return " ".join(lines[:2])
