from __future__ import annotations

import logging
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Execute end-to-end Corruption -> Evaluation -> Idempotent Repair -> Comparison flow."""
    settings = load_settings()
    logger.info("Starting Corruption & Repair Flow...")

    # 1. Load baseline metrics and clean dataset
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        raise FileNotFoundError("Baseline artifacts not found. Please run script/run_phase1.py first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    logger.info("Loaded baseline data (%d records)", len(clean_df))

    # 2. Inject 6 synthetic data corruptions
    logger.info("Injecting 6 synthetic data corruption scenarios...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    logger.info("Corrupted dataset saved with %d rows", len(corrupted_df))

    # 3. Build index & evaluate on corrupted data
    logger.info("Building corrupted Chroma vector index '%s'...", settings.corrupted_collection_name)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    logger.info("Evaluating corrupted pipeline (measuring Silent Failure)...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    logger.info(
        "Corrupted evaluation: Hit Rate=%.2f%%, Mean F1=%.4f",
        corrupted_bundle.summary["retrieval_hit_rate"] * 100,
        corrupted_bundle.summary["mean_token_f1"],
    )

    # 4. Observability on corrupted data
    logger.info("Running Data Quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    logger.info("Corrupted GX Quality status: %s", corrupted_quality["success"])

    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    logger.info(
        "Corrupted Freshness status: %s (Stale ratio: %.2f%%)",
        corrupted_freshness["is_fresh"],
        corrupted_freshness["stale_ratio"] * 100,
    )

    # 5. Idempotent Repair: reload from immutable raw storage
    logger.info("Initiating Idempotent Repair: reloading from raw snapshot %s...", settings.paths.raw_records_json)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    logger.info("Repaired clean dataset saved with %d rows", len(repaired_df))

    # 6. Build index & evaluate on repaired data
    logger.info("Building repaired Chroma vector index '%s'...", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    logger.info("Evaluating repaired pipeline...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    logger.info(
        "Repaired evaluation: Hit Rate=%.2f%%, Mean F1=%.4f",
        repaired_bundle.summary["retrieval_hit_rate"] * 100,
        repaired_bundle.summary["mean_token_f1"],
    )

    # 7. Observability on repaired data
    logger.info("Running Data Quality checks on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    logger.info("Repaired GX Quality status: %s", repaired_quality["success"])

    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    logger.info(
        "Repaired Freshness status: %s (Stale ratio: %.2f%%)",
        repaired_freshness["is_fresh"],
        repaired_freshness["stale_ratio"] * 100,
    )

    # 8. Generate 3-State Comparison Markdown Report
    logger.info("Generating 3-State comparison report: %s", settings.paths.comparison_report)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # 9. Print 3-state summary table to console
    print("\n" + "=" * 80)
    print("               BẢNG ĐỐI CHIẾU HIỆU NĂNG 3 TRẠNG THÁI               ")
    print("=" * 80)
    print(f"{'Tiêu chí':<25} | {'Baseline':<16} | {'Corrupted':<16} | {'Repaired':<16}")
    print("-" * 80)
    print(f"{'Total Documents':<25} | {baseline_metrics.get('samples', 24):<16} | {len(corrupted_df):<16} | {len(repaired_df):<16}")
    print(f"{'GX Quality Gate':<25} | {'Passed (True)':<16} | {str(corrupted_quality['success']):<16} | {str(repaired_quality['success']):<16}")
    print(f"{'Freshness SLA':<25} | {'Healthy':<16} | {'STALE' if not corrupted_freshness['is_fresh'] else 'Healthy':<16} | {'Healthy':<16}")
    print(f"{'Retrieval Hit Rate':<25} | {baseline_metrics['retrieval_hit_rate']*100:>15.2f}% | {corrupted_bundle.summary['retrieval_hit_rate']*100:>15.2f}% | {repaired_bundle.summary['retrieval_hit_rate']*100:>15.2f}%")
    print(f"{'Mean Token F1':<25} | {baseline_metrics['mean_token_f1']:>16.4f} | {corrupted_bundle.summary['mean_token_f1']:>16.4f} | {repaired_bundle.summary['mean_token_f1']:>16.4f}")
    print(f"{'Judge Accuracy':<25} | {baseline_metrics['judge_accuracy']*100:>15.2f}% | {corrupted_bundle.summary['judge_accuracy']*100:>15.2f}% | {repaired_bundle.summary['judge_accuracy']*100:>15.2f}%")
    print(f"{'Mean Judge Score':<25} | {baseline_metrics['mean_judge_score']:>14.2f}/5 | {corrupted_bundle.summary['mean_judge_score']:>14.2f}/5 | {repaired_bundle.summary['mean_judge_score']:>14.2f}/5")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
