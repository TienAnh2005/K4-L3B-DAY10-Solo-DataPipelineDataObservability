from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import logging
import requests

from core.config import Settings
from core.utils import read_json, write_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        titles = item.get("title", [])
        title = titles[0].strip() if titles and isinstance(titles, list) else str(titles).strip()
        summary = str(item.get("abstract", "")).strip()

        authors: list[str] = []
        for author in item.get("author", []):
            given = str(author.get("given", "")).strip()
            family = str(author.get("family", "")).strip()
            full = f"{given} {family}".strip()
            if full:
                authors.append(full)

        categories = [str(cat).strip() for cat in item.get("subject", []) if str(cat).strip()]
        primary_category = categories[0] if categories else ""

        # Extract published date parts
        date_parts = item.get("published", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = parts[0] if len(parts) >= 1 else 1970
            month = parts[1] if len(parts) >= 2 else 1
            day = parts[2] if len(parts) >= 3 else 1
            published = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            published = "1970-01-01"

        updated = str(item.get("created", {}).get("date-time", published))
        abs_url = str(item.get("URL", f"https://doi.org/{paper_id}"))
        pdf_url = ""
        comment = ""

        if paper_id and title:
            records.append(
                PaperRecord(
                    paper_id=paper_id,
                    title=title,
                    summary=summary,
                    authors=authors,
                    categories=categories,
                    primary_category=primary_category,
                    published=published,
                    updated=updated,
                    abs_url=abs_url,
                    pdf_url=pdf_url,
                    comment=comment,
                )
            )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API or local snapshot, save raw artifacts, and return parsed records."""
    payload: dict | None = None

    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "DataObservabilityBot/1.0 (mailto:scholar@example.edu)"}
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
            else:
                logger.warning("API returned status %d. Falling back to local snapshot.", resp.status_code)
        except Exception as exc:
            logger.warning("Failed to fetch from API (%s). Falling back to local snapshot.", exc)

    if payload is None:
        if not settings.paths.raw_api_response.exists():
            raise FileNotFoundError(f"Raw snapshot not found at {settings.paths.raw_api_response}")
        payload = read_json(settings.paths.raw_api_response)

    records = parse_crossref_payload(payload)
    records_payload = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_payload)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map to list of PaperRecord."""
    raw_data = read_json(path)
    return [PaperRecord(**item) for item in raw_data]
