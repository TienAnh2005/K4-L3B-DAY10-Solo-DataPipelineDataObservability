from __future__ import annotations

from pathlib import Path
from typing import Any
import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Data Quality checks using Great Expectations 1.x ephemeral mode and save report."""
    context = gx.get_context(mode="ephemeral")
    data_source_name = f"papers_source_{report_name}"
    data_source = context.data_sources.add_pandas(name=data_source_name)
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"{report_name}_suite")
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=15, max_value=30))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=15))

    validation_result = batch.validate(suite)
    result_dict = validation_result.to_json_dict()

    summary: dict[str, Any] = {
        "report_name": report_name,
        "success": bool(validation_result.success),
        "total_records": len(df),
        "statistics": result_dict.get("statistics", {}),
        "results": [
            {
                "expectation_type": r.get("expectation_config", {}).get("type"),
                "kwargs": r.get("expectation_config", {}).get("kwargs"),
                "success": r.get("success"),
                "result": r.get("result"),
            }
            for r in result_dict.get("results", [])
        ],
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, summary)
    return summary


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Calculate freshness metrics and SLA compliance, then save JSON report."""
    total_rows = len(df)
    if total_rows == 0:
        payload = {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "is_fresh": True,
            "freshness_threshold_days": settings.freshness_threshold_days,
        }
    else:
        threshold = settings.freshness_threshold_days
        stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns else 0
        stale_ratio = stale_rows / total_rows
        latest_published = str(df["published"].max()) if "published" in df.columns else "N/A"
        oldest_published = str(df["published"].min()) if "published" in df.columns else "N/A"
        # SLA: Warning / not fresh if stale ratio > 25%
        is_fresh = stale_ratio <= 0.25

        payload = {
            "total_rows": total_rows,
            "stale_rows": stale_rows,
            "stale_ratio": round(stale_ratio, 4),
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "is_fresh": bool(is_fresh),
            "freshness_threshold_days": threshold,
        }

    target = Path(report_path)
    write_json(target, payload)
    return payload
