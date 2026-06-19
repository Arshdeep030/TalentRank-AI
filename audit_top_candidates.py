#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.pipeline import build_ranked_candidates, load_candidates_and_scorecard
from src.reasoning import generate_reasoning


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export top candidate audit CSV with score breakdown.")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument("--job-description", required=True, help="Path to job description file")
    parser.add_argument("--scorecard", default="config/jd_scorecard.yaml", help="Path to JD scorecard YAML")
    parser.add_argument("--weights", default="config/weights.yaml", help="Path to weights YAML")
    parser.add_argument("--output", default="outputs/top_candidate_audit.csv", help="Path to audit CSV")
    parser.add_argument("--top-k", type=int, default=50, help="How many top candidates to export")
    return parser.parse_args()


def write_audit(rows: list[dict[str, object]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    candidates, scorecard, weights = load_candidates_and_scorecard(args)
    ranked = build_ranked_candidates(candidates, scorecard, weights)

    rows = []
    for rank, (candidate, scores) in enumerate(ranked[: args.top_k], start=1):
        rows.append(
            {
                "rank": rank,
                "candidate_id": candidate.candidate_id,
                "fit_score": f"{scores.fit_score:.2f}",
                "availability_score": f"{scores.availability_score:.2f}",
                "trust_score": f"{scores.trust_score:.2f}",
                "growth_score": f"{scores.growth_score:.2f}",
                "career_depth_score": f"{scores.career_depth_score:.2f}",
                "final_score": f"{scores.final_score:.4f}",
                "fit_category": scores.fit_category,
                "main_concern": scores.main_concern,
                "reasoning": generate_reasoning(candidate, scores),
            }
        )

    write_audit(rows, args.output)
    print(f"Saved top candidate audit to {args.output}")


if __name__ == "__main__":
    main()
