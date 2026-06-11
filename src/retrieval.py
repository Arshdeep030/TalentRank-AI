from __future__ import annotations

import math
import re
from collections import Counter

from src.schemas import CandidateProfile, JobScorecard


TOKEN_PATTERN = re.compile(r"[a-z0-9\+#\.]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def build_query_tokens(scorecard: JobScorecard) -> list[str]:
    query_text = " ".join(
        scorecard.must_have
        + scorecard.nice_to_have
        + scorecard.positive_keywords
        + scorecard.title_positives
    )
    return tokenize(query_text)


def score_candidate_for_retrieval(candidate: CandidateProfile, query_tokens: list[str]) -> float:
    doc_tokens = tokenize(candidate.search_text)
    if not doc_tokens:
        return 0.0
    counts = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        tf = counts.get(token, 0)
        if tf:
            score += 1.0 + math.log1p(tf)
    return score


def retrieve_top_candidates(
    candidates: list[CandidateProfile],
    scorecard: JobScorecard,
    shortlist_size: int,
) -> list[tuple[CandidateProfile, float]]:
    query_tokens = build_query_tokens(scorecard)
    scored = [
        (candidate, score_candidate_for_retrieval(candidate, query_tokens))
        for candidate in candidates
    ]
    scored.sort(key=lambda item: (item[1], item[0].candidate_id), reverse=True)
    return scored[:shortlist_size]
