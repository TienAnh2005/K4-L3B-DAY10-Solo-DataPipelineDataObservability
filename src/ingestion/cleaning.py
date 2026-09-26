from __future__ import annotations

from datetime import datetime, timezone
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_jats_xml(text: str) -> str:
    """Strip XML / JATS tags and clean text."""
    if not text:
        return ""
    cleaned = re.sub(r"<jats:[^>]+>", "", text)
    cleaned = re.sub(r"</jats:[^>]+>", "", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return normalize_whitespace(cleaned)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into an embedding-ready DataFrame with metadata and freshness metrics."""
    cleaned_rows = []
    run_d = run_date.date() if isinstance(run_date, datetime) else run_date

    for record in records:
        clean_title = _clean_jats_xml(record.title)
        clean_summary = _clean_jats_xml(record.summary)
        authors_joined = ", ".join(record.authors)
        categories_joined = ", ".join(record.categories)

        # Parse date and compute age_days
        try:
            pub_date = datetime.strptime(record.published[:10], "%Y-%m-%d").date()
            age_days = max(0, (run_d - pub_date).days)
        except Exception:
            pub_date = run_d
            age_days = 0

        # Structured 5-part text for embedding
        text_for_embedding = (
            f"Title: {clean_title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {record.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {clean_summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": record.paper_id.strip(),
                "title": clean_title,
                "summary": clean_summary,
                "summary_chars": len(clean_summary),
                "authors": record.authors,
                "authors_joined": authors_joined,
                "categories": record.categories,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category,
                "published": record.published,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)

    if not df.empty:
        # Drop duplicates by paper_id
        df = df.drop_duplicates(subset=["paper_id"], keep="first")
        # Filter valid rows
        df = df[df["paper_id"].astype(str).str.len() > 0]
        df = df[df["title"].astype(str).str.len() >= 5]
        # Sort by published date descending, then paper_id
        df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
