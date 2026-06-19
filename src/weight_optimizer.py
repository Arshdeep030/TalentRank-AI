from __future__ import annotations

import copy
import csv
import itertools
import math
from pathlib import Path

from src.pipeline import build_ranked_candidates


def load_labels(path: str | Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            label = row.get("manual_label", "").strip()
            if label != "":
                labels[row["candidate_id"]] = int(label)
    return labels


def precision_at(ranked: list[tuple[object, object]], labels: dict[str, int], k: int, threshold: int) -> float | None:
    judged = 0
    positives = 0
    for candidate, _ in ranked[:k]:
        label = labels.get(candidate.candidate_id)
        if label is None:
            continue
        judged += 1
        if label >= threshold:
            positives += 1
    if judged == 0:
        return None
    return positives / judged


def dcg_at(ranked: list[tuple[object, object]], labels: dict[str, int], k: int) -> float | None:
    judged = []
    for candidate, _ in ranked[:k]:
        label = labels.get(candidate.candidate_id)
        if label is not None:
            judged.append(label)
    if not judged:
        return None
    score = 0.0
    for idx, rel in enumerate(judged, start=1):
        gain = (2**rel) - 1
        score += gain / math.log2(idx + 1)
    return score


def ndcg_at(ranked: list[tuple[object, object]], labels: dict[str, int], k: int) -> float | None:
    actual = dcg_at(ranked, labels, k)
    if actual is None:
        return None
    ideal_labels = sorted(labels.values(), reverse=True)[: min(k, len(labels))]
    ideal = 0.0
    for idx, rel in enumerate(ideal_labels, start=1):
        gain = (2**rel) - 1
        ideal += gain / math.log2(idx + 1)
    if ideal == 0.0:
        return None
    return actual / ideal


def weighted_quality_at(ranked: list[tuple[object, object]], labels: dict[str, int], k: int) -> float | None:
    judged = []
    for candidate, _ in ranked[:k]:
        label = labels.get(candidate.candidate_id)
        if label is not None:
            judged.append(label)
    if not judged:
        return None
    return sum(judged) / (2 * len(judged))


def summarize_metrics(ranked: list[tuple[object, object]], labels: dict[str, int]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for k in (10, 20, 50):
        p_strong = precision_at(ranked, labels, k, threshold=2)
        p_good = precision_at(ranked, labels, k, threshold=1)
        ndcg = ndcg_at(ranked, labels, k)
        quality = weighted_quality_at(ranked, labels, k)
        if p_strong is not None:
            metrics[f"p{k}_strong"] = p_strong
        if p_good is not None:
            metrics[f"p{k}_good"] = p_good
        if ndcg is not None:
            metrics[f"ndcg{k}"] = ndcg
        if quality is not None:
            metrics[f"q{k}"] = quality
    return metrics


def objective(metrics: dict[str, float]) -> float:
    return (
        0.35 * metrics.get("ndcg10", 0.0)
        + 0.20 * metrics.get("ndcg20", 0.0)
        + 0.20 * metrics.get("p10_strong", 0.0)
        + 0.10 * metrics.get("p20_strong", 0.0)
        + 0.10 * metrics.get("q20", 0.0)
        + 0.05 * metrics.get("q50", 0.0)
    )


def iter_weight_sets() -> list[dict[str, float]]:
    fit_weights = [0.40, 0.45, 0.50, 0.55, 0.60]
    availability_weights = [0.10, 0.15, 0.20, 0.25]
    trust_weights = [0.10, 0.15, 0.20, 0.25]
    growth_weights = [0.05, 0.10, 0.15]
    for fit, availability, trust, growth in itertools.product(
        fit_weights, availability_weights, trust_weights, growth_weights
    ):
        if round(fit + availability + trust + growth, 2) == 1.00:
            yield {
                "fit_weight": fit,
                "availability_weight": availability,
                "trust_weight": trust,
                "growth_weight": growth,
            }


def optimize_weights(candidates: list, scorecard, base_weights: dict, labels: dict[str, int]) -> list[dict[str, float]]:
    results = []
    for scoring_weights in iter_weight_sets():
        candidate_weights = copy.deepcopy(base_weights)
        candidate_weights["scoring"] = scoring_weights
        ranked = build_ranked_candidates(candidates, scorecard, candidate_weights)
        metrics = summarize_metrics(ranked, labels)
        result = {
            **scoring_weights,
            **metrics,
            "objective": objective(metrics),
        }
        results.append(result)
    results.sort(key=lambda row: row["objective"], reverse=True)
    return results
