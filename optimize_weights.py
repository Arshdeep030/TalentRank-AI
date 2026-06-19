#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.pipeline import load_candidates_and_scorecard
from src.weight_optimizer import load_labels, optimize_weights


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grid-search scoring weights against manual labels.")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument("--job-description", required=True, help="Path to job description file")
    parser.add_argument("--labels", default="outputs/manual_labels.csv", help="Path to manual labels CSV")
    parser.add_argument("--scorecard", default="config/jd_scorecard.yaml", help="Path to JD scorecard YAML")
    parser.add_argument("--weights", default="config/weights.yaml", help="Path to base weights YAML")
    parser.add_argument("--output", default="outputs/weight_search.csv", help="Path to weight search results CSV")
    parser.add_argument("--top-n", type=int, default=10, help="How many top weight sets to print")
    return parser.parse_args()


def write_results(path: str | Path, results: list[dict[str, float]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        output.write_text("", encoding="utf-8")
        return
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    args = parse_args()
    labels = load_labels(args.labels)
    if not labels:
        raise SystemExit("No manual labels found. Label some candidates first in outputs/manual_labels.csv.")

    candidates, scorecard, weights = load_candidates_and_scorecard(args)
    results = optimize_weights(candidates, scorecard, weights, labels)
    write_results(args.output, results)

    print("Top weight sets")
    print("===============")
    for row in results[: args.top_n]:
        print(
            f"objective={row['objective']:.4f} | "
            f"fit={row['fit_weight']:.2f} avail={row['availability_weight']:.2f} "
            f"trust={row['trust_weight']:.2f} growth={row['growth_weight']:.2f} | "
            f"NDCG@10={row.get('ndcg10', 0.0):.3f} P@10={row.get('p10_strong', 0.0):.3f}"
        )
    print()
    print(f"Saved full results to {args.output}")


if __name__ == "__main__":
    main()
