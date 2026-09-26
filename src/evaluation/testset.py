from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic benchmark test set of 10 questions across 4 business categories."""
    if len(df) < 10:
        raise ValueError(f"DataFrame must contain at least 10 records to build test set, got {len(df)}")

    # Deterministic selection of papers from the cleaned corpus
    # Types: summary (3), authors (3), date (2), categories (2) -> Total 10
    plan = [
        ("summary", 0),
        ("authors", 1),
        ("date", 2),
        ("categories", 3),
        ("summary", 4),
        ("authors", 5),
        ("date", 6),
        ("categories", 7),
        ("summary", 8),
        ("authors", 9),
    ]

    test_questions: list[dict[str, Any]] = []

    for idx, (q_type, row_idx) in enumerate(plan):
        row = df.iloc[row_idx]
        title = str(row["title"]).strip()
        paper_id = str(row["paper_id"]).strip()

        if q_type == "summary":
            question = f"What is the primary contribution or summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        elif q_type == "categories":
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(row["categories_joined"])
        else:
            raise ValueError(f"Unknown question type: {q_type}")

        test_questions.append(
            {
                "id": f"q_{idx+1}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    target_path = Path(output_path)
    write_json(target_path, test_questions)
    return test_questions
