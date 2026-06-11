from __future__ import annotations

from pathlib import Path

import yaml

from src.io_utils import read_text_file
from src.schemas import JobScorecard


def load_job_scorecard(job_description_path: str | Path, scorecard_path: str | Path) -> JobScorecard:
    raw_text = read_text_file(job_description_path)
    config = yaml.safe_load(Path(scorecard_path).read_text(encoding="utf-8"))
    return JobScorecard(raw_text=raw_text, **config)
