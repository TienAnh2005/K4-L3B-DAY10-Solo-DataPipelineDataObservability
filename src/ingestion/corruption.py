from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject 6 synthetic data corruption scenarios into a clean DataFrame."""
    corrupted_df = df.copy()
    corruption_log: dict[str, Any] = {
        "original_rows": len(df),
        "injected_scenarios": [],
    }

    # 1. Drop latest records (20% newest records, e.g. top 4 records)
    # This directly causes retrieval misses for test questions referencing these papers!
    drop_count = max(2, int(len(corrupted_df) * 0.20))
    dropped_papers = corrupted_df.iloc[:drop_count]["paper_id"].tolist()
    dropped_titles = corrupted_df.iloc[:drop_count]["title"].tolist()
    corrupted_df = corrupted_df.iloc[drop_count:].copy().reset_index(drop=True)
    corruption_log["injected_scenarios"].append(
        {
            "scenario": "drop_latest_records",
            "dropped_count": drop_count,
            "dropped_paper_ids": dropped_papers,
            "dropped_titles": dropped_titles,
            "impact": "Decreases retrieval hit rate and recall; questions querying these papers will fail.",
        }
    )

    # 2. Blank summary (clear summary for the first remaining record)
    if len(corrupted_df) > 0:
        corrupted_df.loc[0, "summary"] = ""
        corrupted_df.loc[0, "summary_chars"] = 0
        corruption_log["injected_scenarios"].append(
            {
                "scenario": "blank_summary",
                "target_paper_id": corrupted_df.loc[0, "paper_id"],
                "target_title": corrupted_df.loc[0, "title"],
                "impact": "Violates GX summary length expectation; degrades semantic embedding vector.",
            }
        )

    # 3. Inject noise into summary (gibberish characters in second remaining record)
    if len(corrupted_df) > 1:
        corrupted_df.loc[1, "summary"] = "!@#$%^&*()_+ RANDOM GARBAGE CORRUPTED BYTES INJECTION !@#$%^&*()"
        corrupted_df.loc[1, "summary_chars"] = len(corrupted_df.loc[1, "summary"])
        corruption_log["injected_scenarios"].append(
            {
                "scenario": "inject_noise",
                "target_paper_id": corrupted_df.loc[1, "paper_id"],
                "target_title": corrupted_df.loc[1, "title"],
                "impact": "Perturbs dense vector space, shifts cosine distances, causes ranking errors.",
            }
        )

    # 4. Truncate title (< 8 characters in third remaining record)
    if len(corrupted_df) > 2:
        old_title = corrupted_df.loc[2, "title"]
        corrupted_df.loc[2, "title"] = "Bad"
        corruption_log["injected_scenarios"].append(
            {
                "scenario": "truncate_title",
                "target_paper_id": corrupted_df.loc[2, "paper_id"],
                "old_title": old_title,
                "new_title": "Bad",
                "impact": "Violates GX title length expectation (min 8 chars) and breaks title matching.",
            }
        )

    # 5. Stale date (shift publication dates back 4 years for multiple papers)
    stale_count = min(8, len(corrupted_df))
    for i in range(stale_count):
        corrupted_df.loc[i, "published"] = "2020-01-01"
        corrupted_df.loc[i, "age_days"] = 2400
    corruption_log["injected_scenarios"].append(
        {
            "scenario": "stale_date",
            "modified_rows": stale_count,
            "new_date": "2020-01-01",
            "impact": "Violates Freshness SLA; stale ratio exceeds 25% threshold, triggering alerts.",
        }
    )

    # 6. Duplicate rows (duplicate 2 existing rows)
    if len(corrupted_df) >= 2:
        dup_rows = corrupted_df.iloc[[0, 1]].copy()
        corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
        corruption_log["injected_scenarios"].append(
            {
                "scenario": "duplicate_rows",
                "duplicated_paper_ids": dup_rows["paper_id"].tolist(),
                "impact": "Violates GX paper_id uniqueness expectation; pollutes index with duplicate vectors.",
            }
        )

    # 7. Rebuild text_for_embedding for all rows
    corrupted_df["text_for_embedding"] = corrupted_df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    corruption_log["corrupted_rows"] = len(corrupted_df)
    target_log = Path(output_log_path)
    write_json(target_log, corruption_log)
    return corrupted_df
