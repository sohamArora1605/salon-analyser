from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.data.manifest import DATASETS


def profile_csv(path: Path) -> dict:
    frame = pd.read_csv(path)
    return {
        "file_name": path.name,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "missing_values": {column: int(frame[column].isna().sum()) for column in frame.columns},
        "sample": frame.head(3).fillna("").to_dict(orient="records"),
    }


def profile_all(raw_dir: Path) -> list[dict]:
    profiles = []
    for dataset in DATASETS:
        path = raw_dir / dataset.file_name
        if path.exists():
            profile = profile_csv(path)
            profile["domain"] = dataset.domain
            profile["target_table"] = dataset.target_table
            profile["description"] = dataset.description
            profiles.append(profile)
        else:
            profiles.append(
                {
                    "file_name": dataset.file_name,
                    "domain": dataset.domain,
                    "target_table": dataset.target_table,
                    "description": dataset.description,
                    "missing": True,
                }
            )
    return profiles

