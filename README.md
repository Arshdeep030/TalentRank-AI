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

## Notes

- `jd_parser.py` can read the provided `.docx` JD, but it primarily uses the hand-tuned scorecard in `config/jd_scorecard.yaml`.
- Retrieval is intentionally lightweight and CPU-friendly.
- Trust and honeypot-style checks are built in as penalties.
