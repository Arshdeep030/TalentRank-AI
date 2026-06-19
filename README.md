# Ideathon Ranker

Recruiter-aware candidate ranking system for the Redrob hackathon dataset.

## What this builds

This project ranks candidates against the provided Senior AI Engineer job description using:

- structured job intelligence
- normalized candidate profiles
- fast lexical retrieval
- multi-score ranking
- factual reasoning generation

The pipeline is designed to stay compatible with the hackathon constraint of CPU-only ranking on `100,000` candidates.

## Project layout

- `rank.py` - CLI entrypoint
- `config/jd_scorecard.yaml` - structured requirements for the released JD
- `config/weights.yaml` - score weights and thresholds
- `src/` - ranking pipeline source

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 rank.py \
  --candidates ./dataset/candidates.jsonl \
  --job-description ./dataset/job_description.docx \
  --output ./outputs/submission.csv
```

## Validate

```bash
python3 dataset/validate_submission.py ./outputs/submission.csv
```

## Local evaluation

You cannot compute the real hackathon accuracy locally because the ground-truth labels are hidden, but you can score your ranker with manual proxy labels.

Generate a review sheet and metrics shell:

```bash
python3 eval_local.py \
  --submission ./outputs/submission.csv \
  --candidates ./dataset/candidates.jsonl
```

This creates:

- `outputs/review_sheet.csv` with the top ranked candidates and useful profile fields
- `outputs/manual_labels.csv` where you label each candidate:
  - `2` = strong fit
  - `1` = maybe
  - `0` = bad fit

After filling labels, rerun the command to see:

- `P@10` strong-fit
- `P@20` strong-fit
- `P@50` strong-fit
- good-fit precision including `maybe`
- a weighted quality score

For guided terminal labeling instead of editing CSV manually:

```bash
python3 eval_local.py \
  --submission ./outputs/submission.csv \
  --candidates ./dataset/candidates.jsonl \
  --interactive
```

Useful options:

- `--start-rank 11` to resume from rank 11
- `--top-k 100` to review more candidates

Every evaluation run also exports `outputs/error_analysis.csv` for labeled candidates so you can inspect high-scoring bad fits.

## Weight optimization

After labeling some candidates, grid-search score weights:

```bash
python3 optimize_weights.py \
  --candidates ./dataset/candidates.jsonl \
  --job-description ./dataset/job_description.docx \
  --labels ./outputs/manual_labels.csv
```

This writes `outputs/weight_search.csv` with proxy metrics including:

- `P@10`, `P@20`, `P@50`
- `NDCG@10`, `NDCG@20`, `NDCG@50`
- weighted quality scores

## Top candidate audit

Export a recruiter-style audit sheet for the top ranked candidates:

```bash
python3 audit_top_candidates.py \
  --candidates ./dataset/candidates.jsonl \
  --job-description ./dataset/job_description.docx \
  --top-k 50
```

This creates `outputs/top_candidate_audit.csv` with:

- rank
- candidate_id
- fit / availability / trust / growth scores
- career depth score
- fit category
- final score
- reasoning

## Notes

- `jd_parser.py` can read the provided `.docx` JD, but it primarily uses the hand-tuned scorecard in `config/jd_scorecard.yaml`.
- Retrieval is intentionally lightweight and CPU-friendly.
- Trust and honeypot-style checks are built in as penalties.
