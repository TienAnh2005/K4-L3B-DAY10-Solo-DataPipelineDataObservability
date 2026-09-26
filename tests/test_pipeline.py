from __future__ import annotations

from datetime import datetime, timezone
import pytest
import pandas as pd

from core.config import load_settings
from ingestion.crossref import parse_crossref_payload, load_raw_records, PaperRecord
from ingestion.cleaning import build_clean_dataframe, _clean_jats_xml
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import run_data_quality_checks, build_freshness_report
from evaluation.testset import build_test_set


@pytest.fixture
def settings():
    return load_settings()


def test_clean_jats_xml():
    raw = "<jats:p>This is a test <jats:title>Abstract</jats:title></jats:p>"
    cleaned = _clean_jats_xml(raw)
    assert "<" not in cleaned
    assert "This is a test Abstract" == cleaned


def test_parse_crossref_payload(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    assert len(records) == 24
    sample = records[0]
    assert isinstance(sample, PaperRecord)
    assert sample.paper_id.startswith("10.")
    assert len(sample.title) > 0
    assert len(sample.authors) > 0


def test_build_clean_dataframe(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, run_date)

    assert len(df) == 24
    assert "text_for_embedding" in df.columns
    assert "age_days" in df.columns
    assert "authors_joined" in df.columns
    assert df["paper_id"].is_unique
    assert (df["summary_chars"] > 0).all()


def test_gx_quality_gate_clean_data(settings):
    clean_df = pd.read_json(settings.paths.clean_json)
    res = run_data_quality_checks(clean_df, settings, "test_clean")
    assert res["success"] is True
    assert res["total_records"] == 24


def test_freshness_sla_clean_data(settings):
    clean_df = pd.read_json(settings.paths.clean_json)
    res = build_freshness_report(clean_df, settings, settings.paths.quality_dir / "test_freshness.json")
    assert res["total_rows"] == 24
    assert res["is_fresh"] is True
    assert res["stale_ratio"] <= 0.25


def test_testset_generation(settings):
    clean_df = pd.read_json(settings.paths.clean_json)
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    assert len(test_set) == 10
    types = {q["question_type"] for q in test_set}
    assert types == {"summary", "authors", "date", "categories"}


def test_corruption_degradation(settings, tmp_path):
    clean_df = pd.read_json(settings.paths.clean_json)
    log_path = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)

    # 1. Row count modified (dropped 4 rows, duplicated 2 rows)
    assert len(corrupted_df) < len(clean_df)
    # 2. Check quality gate catches corruption
    res = run_data_quality_checks(corrupted_df, settings, "test_corrupted")
    assert res["success"] is False  # GX 1.x flags the dirty data!

    # 3. Check Freshness SLA flags corruption
    fresh_res = build_freshness_report(corrupted_df, settings, tmp_path / "corr_fresh.json")
    assert fresh_res["is_fresh"] is False
    assert fresh_res["stale_ratio"] > 0.25


def test_idempotent_repair(settings):
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(timezone.utc))

    assert len(repaired_df) == 24
    res = run_data_quality_checks(repaired_df, settings, "test_repair")
    assert res["success"] is True
