from __future__ import annotations

import logging
from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run baseline pipeline end-to-end: Ingest -> Clean -> Index -> Eval -> Quality -> Report."""
    settings = load_settings()
    logger.info("Starting Phase 1 Baseline Pipeline...")

    # 1. Fetch / load raw records
    records = fetch_source_records(settings)
    logger.info("Ingested %d raw records", len(records))

    # 2. Clean data
    df = build_clean_dataframe(records, now_utc())
    logger.info("Cleaned %d records", len(df))

    # 3. Save clean artifacts
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    logger.info("Saved clean CSV and JSON artifacts")

    # 4. Build Chroma vector index
    logger.info("Building Chroma vector index '%s'...", settings.baseline_collection_name)
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    logger.info("Indexed %d documents into ChromaDB", len(df))

    # 5. Build benchmark test set
    test_set = build_test_set(df, settings.paths.eval_testset)
    logger.info("Generated %d benchmark test questions", len(test_set))

    # 6. Evaluate baseline pipeline
    logger.info("Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info(
        "Baseline evaluation metrics: Hit Rate=%.2f%%, Mean F1=%.4f, Judge Acc=%.2f%%",
        bundle.summary["retrieval_hit_rate"] * 100,
        bundle.summary["mean_token_f1"],
        bundle.summary["judge_accuracy"] * 100,
    )

    # 7. Quality Gate & Freshness SLA
    logger.info("Running Data Quality checks with Great Expectations 1.x...")
    quality_report = run_data_quality_checks(df, settings, "baseline")
    logger.info("GX Quality status: %s", quality_report["success"])

    logger.info("Generating Freshness SLA report...")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)
    logger.info("Freshness status: %s (Stale ratio: %.2f%%)", freshness_report["is_fresh"], freshness_report["stale_ratio"] * 100)

    # 8. Generate Phase 1 Markdown report
    source_summary = {
        "raw_count": len(records),
        "clean_count": len(df),
        "source_api": settings.source_api,
        "source_query": settings.source_query,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    logger.info("Phase 1 Baseline Pipeline completed successfully. Report saved to: %s", settings.paths.baseline_report)


if __name__ == "__main__":
    main()
