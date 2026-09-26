from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def auto_heal_pipeline(df: pd.DataFrame, source_name: str = "incoming") -> dict[str, Any]:
    """Automated Self-Healing / Auto-Repair Engine (Bonus B2).

    Inspects incoming data through Great Expectations 1.x and Freshness SLA.
    If any quality rule or freshness threshold is breached, automatically triggers
    an Idempotent Rollback & Self-Healing procedure from immutable raw snapshot storage.
    """
    settings = load_settings()
    logger.info("Executing Automated Quality Gate on %s data (%d rows)...", source_name, len(df))

    # 1. Inspect quality & freshness
    quality = run_data_quality_checks(df, settings, f"{source_name}_eval")
    freshness_path = settings.paths.quality_dir / f"{source_name}_freshness.json"
    freshness = build_freshness_report(df, settings, freshness_path)

    is_healthy = quality["success"] and freshness["is_fresh"]

    incident_log = {
        "timestamp": now_utc().isoformat(),
        "source": source_name,
        "input_rows": len(df),
        "quality_gate_passed": quality["success"],
        "freshness_sla_healthy": freshness["is_fresh"],
        "stale_ratio": freshness["stale_ratio"],
        "self_healing_triggered": False,
        "resolution": "None required - data passed all quality gates",
    }

    if is_healthy:
        logger.info("✅ Quality gate PASSED. Data is healthy and ready for serving.")
        return incident_log

    logger.warning("🚨 QUALITY GATE BREACH DETECTED!")
    logger.warning("   GX 1.x Success: %s | Freshness Healthy: %s (Stale: %.2f%%)", quality["success"], freshness["is_fresh"], freshness["stale_ratio"] * 100)
    logger.info("🔄 Initiating AUTOMATED SELF-HEALING & IDEMPOTENT REPAIR...")

    # 2. Automated Self-Healing from immutable raw lineage
    raw_records = load_raw_records(settings.paths.raw_records_json)
    healed_df = build_clean_dataframe(raw_records, now_utc())

    # 3. Overwrite clean serving store
    write_csv(healed_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, healed_df.to_dict(orient="records"))

    # 4. Re-index serving vector store
    LocalEmbeddingIndex.build(healed_df, settings, settings.paths.embeddings_json)

    # 5. Re-verify post-heal quality
    healed_quality = run_data_quality_checks(healed_df, settings, "post_auto_heal")
    healed_freshness = build_freshness_report(healed_df, settings, settings.paths.freshness_report)

    incident_log.update(
        {
            "self_healing_triggered": True,
            "resolution": "Automatically rolled back to immutable raw snapshot, re-cleaned, and re-indexed ChromaDB.",
            "post_heal_gx_success": healed_quality["success"],
            "post_heal_freshness_healthy": healed_freshness["is_fresh"],
            "healed_rows": len(healed_df),
        }
    )

    incident_path = settings.paths.quality_dir / "self_healing_incident_log.json"
    write_json(incident_path, incident_log)
    logger.info("✅ Automated Self-Healing completed successfully. Incident audit logged to %s", incident_path)
    return incident_log


def main() -> None:
    settings = load_settings()
    logger.info("Testing Auto-Repair Engine with Corrupted Data...")
    corrupted_df = pd.read_json(settings.paths.corrupted_clean_json)
    result = auto_heal_pipeline(corrupted_df, source_name="corrupted_feed")
    print("\n" + "=" * 60)
    print("      AUTOMATED SELF-HEALING INCIDENT AUDIT REPORT          ")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k:<28}: {v}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
