from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml

from src.candidate_normalizer import normalize_candidate
from src.honeypot_rules import honeypot_penalties
from src.io_utils import iter_jsonl
from src.jd_parser import load_job_scorecard
from src.reasoning import generate_reasoning
from src.retrieval import retrieve_top_candidates
from src.scorer_availability import score_availability
from src.scorer_final import blend_scores
from src.scorer_fit import score_fit
from src.scorer_growth import score_growth
from src.scorer_trust import score_trust


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank candidates for the Redrob hackathon.")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument("--job-description", required=True, help="Path to job description file")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    parser.add_argument("--scorecard", default="config/jd_scorecard.yaml", help="Path to structured JD scorecard")
    parser.add_argument("--weights", default="config/weights.yaml", help="Path to scoring weights")
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> list[dict[str, object]]:
    weights = yaml.safe_load(Path(args.weights).read_text(encoding="utf-8"))
    scorecard = load_job_scorecard(args.job_description, args.scorecard)
    candidates = [normalize_candidate(record) for record in iter_jsonl(args.candidates)]
    retrieved = retrieve_top_candidates(candidates, scorecard, int(weights["retrieval"]["shortlist_size"]))

    ranked = []
    for candidate, retrieval_score in retrieved:
        fit_score, fit_strengths = score_fit(candidate, scorecard)
        availability_score, availability_strengths = score_availability(
            candidate,
            stale_days=int(weights["availability"]["stale_days"]),
            ideal_notice_days=int(weights["availability"]["ideal_notice_days"]),
            acceptable_notice_days=int(weights["availability"]["acceptable_notice_days"]),
        )
        trust_score, trust_penalties = score_trust(candidate, scorecard, weights["trust"])
        growth_score, growth_strengths = score_growth(candidate, weights["growth"])
        extra_penalty, extra_reasons = honeypot_penalties(candidate)
        trust_score = max(0.0, trust_score - extra_penalty)

        score_bundle = blend_scores(
            candidate_id=candidate.candidate_id,
            retrieval_score=retrieval_score,
            fit_score=fit_score,
            availability_score=availability_score,
            trust_score=trust_score,
            growth_score=growth_score,
            weights=weights,
            penalties=trust_penalties + extra_reasons,
            strengths=fit_strengths + availability_strengths + growth_strengths,
        )
        ranked.append((candidate, score_bundle))

    ranked.sort(
        key=lambda item: (
            -item[1].final_score,
            -item[1].fit_score,
            -item[1].trust_score,
            item[0].candidate_id,
        )
    )

    top_ranked = ranked[:100]
    top_ranked.sort(
        key=lambda item: (
            -round(item[1].final_score / 100, 4),
            item[0].candidate_id,
        )
    )

    rows = []
    for rank, (candidate, scores) in enumerate(top_ranked, start=1):
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "rank": rank,
                "score": f"{scores.final_score / 100:.4f}",
                "reasoning": generate_reasoning(candidate, scores),
            }
        )
    return rows


def write_submission(rows: list[dict[str, object]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rows = run_pipeline(args)
    write_submission(rows, args.output)
