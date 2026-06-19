#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from src.candidate_normalizer import normalize_candidate
from src.io_utils import iter_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local proxy evaluation for Redrob submissions.")
    parser.add_argument("--submission", required=True, help="Path to submission CSV")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument(
        "--labels",
        default="outputs/manual_labels.csv",
        help="CSV file with manual labels. Created if missing.",
    )
    parser.add_argument(
        "--export-review",
        default="outputs/review_sheet.csv",
        help="Review sheet export with candidate details for manual judging.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=50,
        help="How many ranked candidates to include in the review sheet.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch terminal-based labeling for the review candidates.",
    )
    parser.add_argument(
        "--start-rank",
        type=int,
        default=1,
        help="Starting rank for interactive review.",
    )
    parser.add_argument(
        "--export-error-analysis",
        default="outputs/error_analysis.csv",
        help="CSV export with labeled candidates and score breakdown for analysis.",
    )
    return parser.parse_args()


def load_submission(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_candidates(path: str | Path) -> dict[str, object]:
    candidates = {}
    for record in iter_jsonl(path):
        candidate = normalize_candidate(record)
        candidates[candidate.candidate_id] = candidate
    return candidates


def build_review_rows(submission_rows: list[dict[str, str]], candidates: dict[str, object], top_k: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in submission_rows[:top_k]:
        candidate = candidates[row["candidate_id"]]
        skills = ", ".join(candidate.skills[:8])
        last_active = candidate.activity_signals["last_active_date"]
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "rank": row["rank"],
                "model_score": row["score"],
                "current_title": candidate.current_title,
                "years_experience": f"{candidate.years_experience:.1f}",
                "current_company": candidate.current_company,
                "current_industry": candidate.current_industry,
                "location": candidate.current_location,
                "open_to_work": str(candidate.activity_signals.get("open_to_work_flag", False)),
                "response_rate": str(candidate.activity_signals.get("recruiter_response_rate", 0.0)),
                "notice_period_days": str(candidate.activity_signals.get("notice_period_days", "")),
                "last_active_date": last_active,
                "top_skills": skills,
                "reasoning": row["reasoning"],
                "manual_label": "",
                "notes": "",
            }
        )
    return rows


def write_review_sheet(path: str | Path, rows: list[dict[str, str]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def ensure_labels_file(path: str | Path, review_rows: list[dict[str, str]]) -> None:
    labels_path = Path(path)
    if labels_path.exists():
        return
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "manual_label", "notes"])
        writer.writeheader()
        for row in review_rows:
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "manual_label": "",
                    "notes": "",
                }
            )


def load_labels(path: str | Path) -> dict[str, dict[str, str]]:
    labels = {}
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            labels[row["candidate_id"]] = row
    return labels


def write_labels(path: str | Path, labels: dict[str, dict[str, str]]) -> None:
    labels_path = Path(path)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_rows = sorted(labels.values(), key=lambda row: row["candidate_id"])
    with labels_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "manual_label", "notes"])
        writer.writeheader()
        writer.writerows(ordered_rows)


def precision_at(rows: list[dict[str, str]], labels: dict[str, dict[str, str]], k: int, positive_threshold: int) -> float | None:
    slice_rows = rows[:k]
    judged = 0
    positives = 0
    for row in slice_rows:
        label = labels.get(row["candidate_id"], {}).get("manual_label", "").strip()
        if label == "":
            continue
        judged += 1
        if int(label) >= positive_threshold:
            positives += 1
    if judged == 0:
        return None
    return positives / judged


def weighted_quality_at(rows: list[dict[str, str]], labels: dict[str, dict[str, str]], k: int) -> float | None:
    slice_rows = rows[:k]
    judged_scores = []
    for row in slice_rows:
        label = labels.get(row["candidate_id"], {}).get("manual_label", "").strip()
        if label == "":
            continue
        judged_scores.append(int(label))
    if not judged_scores:
        return None
    return sum(judged_scores) / (2 * len(judged_scores))


def dcg_at(rows: list[dict[str, str]], labels: dict[str, dict[str, str]], k: int) -> float | None:
    judged_scores = []
    for row in rows[:k]:
        label = labels.get(row["candidate_id"], {}).get("manual_label", "").strip()
        if label == "":
            continue
        judged_scores.append(int(label))
    if not judged_scores:
        return None
    score = 0.0
    for idx, rel in enumerate(judged_scores, start=1):
        gain = (2**rel) - 1
        score += gain / math.log2(idx + 1)
    return score


def ndcg_at(rows: list[dict[str, str]], labels: dict[str, dict[str, str]], k: int) -> float | None:
    actual = dcg_at(rows, labels, k)
    if actual is None:
        return None
    ideal_scores = sorted(
        (int(item["manual_label"]) for item in labels.values() if item.get("manual_label", "").strip() != ""),
        reverse=True,
    )[:k]
    if not ideal_scores:
        return None
    ideal = 0.0
    for idx, rel in enumerate(ideal_scores, start=1):
        gain = (2**rel) - 1
        ideal += gain / math.log2(idx + 1)
    if ideal == 0.0:
        return None
    return actual / ideal


def print_metrics(submission_rows: list[dict[str, str]], labels: dict[str, dict[str, str]]) -> None:
    label_counts = Counter()
    for item in labels.values():
        label = item.get("manual_label", "").strip()
        if label:
            label_counts[label] += 1

    print("Local proxy evaluation")
    print("======================")
    print("Label guide: 2 = strong fit, 1 = maybe, 0 = bad fit")
    print(f"Labeled candidates: {sum(label_counts.values())}")
    print(f"Label counts: {dict(label_counts)}")

    for k in (10, 20, 50):
        p_strong = precision_at(submission_rows, labels, k, positive_threshold=2)
        p_good = precision_at(submission_rows, labels, k, positive_threshold=1)
        quality = weighted_quality_at(submission_rows, labels, k)
        ndcg = ndcg_at(submission_rows, labels, k)
        strong_text = "n/a" if p_strong is None else f"{p_strong:.3f}"
        good_text = "n/a" if p_good is None else f"{p_good:.3f}"
        quality_text = "n/a" if quality is None else f"{quality:.3f}"
        ndcg_text = "n/a" if ndcg is None else f"{ndcg:.3f}"
        print(f"P@{k} strong-fit: {strong_text}")
        print(f"P@{k} good-fit : {good_text}")
        print(f"Q@{k} weighted : {quality_text}")
        print(f"NDCG@{k}       : {ndcg_text}")


def export_error_analysis(
    submission_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    labels: dict[str, dict[str, str]],
    output_path: str | Path,
) -> None:
    review_lookup = {row["candidate_id"]: row for row in review_rows}
    exported = []
    for row in submission_rows:
        label = labels.get(row["candidate_id"], {}).get("manual_label", "").strip()
        if label == "":
            continue
        review = review_lookup.get(row["candidate_id"], {})
        numeric_label = int(label)
        model_score = float(row["score"])
        error_gap = round(model_score - (numeric_label / 2.0), 4)
        exported.append(
            {
                "candidate_id": row["candidate_id"],
                "rank": row["rank"],
                "model_score": row["score"],
                "manual_label": label,
                "error_gap": f"{error_gap:.4f}",
                "current_title": review.get("current_title", ""),
                "years_experience": review.get("years_experience", ""),
                "current_company": review.get("current_company", ""),
                "current_industry": review.get("current_industry", ""),
                "open_to_work": review.get("open_to_work", ""),
                "response_rate": review.get("response_rate", ""),
                "notice_period_days": review.get("notice_period_days", ""),
                "reasoning": row["reasoning"],
                "notes": labels.get(row["candidate_id"], {}).get("notes", ""),
            }
        )
    exported.sort(key=lambda item: float(item["error_gap"]), reverse=True)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(exported[0].keys()) if exported else [
            "candidate_id", "rank", "model_score", "manual_label", "error_gap", "current_title",
            "years_experience", "current_company", "current_industry", "open_to_work",
            "response_rate", "notice_period_days", "reasoning", "notes"
        ])
        writer.writeheader()
        writer.writerows(exported)


def prompt(text: str) -> str:
    return input(text).strip()


def interactive_label_review(
    review_rows: list[dict[str, str]],
    labels_path: str | Path,
    labels: dict[str, dict[str, str]],
    start_rank: int,
) -> dict[str, dict[str, str]]:
    print("Interactive labeling mode")
    print("=========================")
    print("Commands: 2 = strong fit, 1 = maybe, 0 = bad fit, s = skip, q = quit")
    print()

    rows_by_rank = [row for row in review_rows if int(row["rank"]) >= start_rank]
    for row in rows_by_rank:
        candidate_id = row["candidate_id"]
        existing = labels.get(candidate_id, {"candidate_id": candidate_id, "manual_label": "", "notes": ""})

        print("-" * 72)
        print(f"Rank #{row['rank']} | {candidate_id} | score={row['model_score']}")
        print(f"Title: {row['current_title']}")
        print(f"Experience: {row['years_experience']} years")
        print(f"Company/Industry: {row['current_company']} / {row['current_industry']}")
        print(f"Location: {row['location']}")
        print(
            "Signals: "
            f"open_to_work={row['open_to_work']}, "
            f"response_rate={row['response_rate']}, "
            f"notice={row['notice_period_days']}d, "
            f"last_active={row['last_active_date']}"
        )
        print(f"Top skills: {row['top_skills']}")
        print(f"Reasoning: {row['reasoning']}")
        if existing.get("manual_label"):
            print(f"Existing label: {existing['manual_label']} | notes: {existing.get('notes', '')}")

        label = prompt("Label [2/1/0/s/q]: ")
        while label not in {"2", "1", "0", "s", "q"}:
            label = prompt("Please enter 2, 1, 0, s, or q: ")

        if label == "q":
            print("Stopping interactive review.")
            break
        if label == "s":
            continue

        notes = prompt("Notes (optional): ")
        labels[candidate_id] = {
            "candidate_id": candidate_id,
            "manual_label": label,
            "notes": notes,
        }
        write_labels(labels_path, labels)
        print("Saved.")
        print()

    return labels


def main() -> None:
    args = parse_args()
    submission_rows = load_submission(args.submission)
    candidates = load_candidates(args.candidates)
    review_rows = build_review_rows(submission_rows, candidates, args.top_k)
    write_review_sheet(args.export_review, review_rows)
    ensure_labels_file(args.labels, review_rows)
    labels = load_labels(args.labels)
    if args.interactive:
        labels = interactive_label_review(review_rows, args.labels, labels, args.start_rank)
    print_metrics(submission_rows, labels)
    export_error_analysis(submission_rows, review_rows, labels, args.export_error_analysis)
    print()
    print(f"Review sheet: {args.export_review}")
    print(f"Labels file : {args.labels}")
    print(f"Error sheet : {args.export_error_analysis}")
    if args.interactive:
        print("Interactive review complete. Rerun anytime to continue from a later rank.")
    else:
        print("Fill manual_label with 2, 1, or 0 and rerun to see proxy metrics.")


if __name__ == "__main__":
    main()
