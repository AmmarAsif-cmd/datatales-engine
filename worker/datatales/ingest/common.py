"""Store a fetched raw file: checksum, skip duplicates, upload untouched, record dataset."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from datatales.repo import Dataset, Repo, now_utc
from datatales.sources import SourceDef

MAX_RAW_BYTES = 50 * 1024 * 1024  # Supabase free-tier per-file limit (bucket limit in 0001)
CONTENT_TYPES = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
}


@dataclass(frozen=True)
class RawFile:
    filename: str
    content: bytes
    source_url: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestResult:
    dataset: Dataset
    skipped: bool


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return stem or "file"


def extension(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def ingest_raw(repo: Repo, source: SourceDef, raw: RawFile) -> IngestResult:
    if len(raw.content) == 0:
        raise ValueError("raw file is empty")
    if len(raw.content) > MAX_RAW_BYTES:
        raise ValueError(f"raw file is {len(raw.content):,} bytes; limit is {MAX_RAW_BYTES:,}")
    ext = extension(raw.filename)
    if ext not in CONTENT_TYPES:
        raise ValueError(f"unsupported file type '{ext}'; allowed: {', '.join(CONTENT_TYPES)}")

    source_id = repo.upsert_source(source)
    checksum = sha256(raw.content)
    existing = repo.find_dataset(source_id, checksum)
    if existing:
        return IngestResult(existing, skipped=True)

    fetched_at = now_utc()
    folder = f"{source.slug}/{fetched_at:%Y%m%dT%H%M%SZ}-{checksum[:12]}"
    raw_path = f"{folder}/{safe_filename(raw.filename)}"
    fetch_record = {
        "source_slug": source.slug,
        "source_url": raw.source_url,
        "fetched_at": fetched_at.isoformat(),
        "checksum_sha256": checksum,
        "bytes": len(raw.content),
        "filename": raw.filename,
        **raw.meta,
    }
    repo.put_object("raw", raw_path, raw.content, CONTENT_TYPES[ext])
    repo.put_object(
        "raw",
        f"{folder}/fetch.json",
        json.dumps(fetch_record, indent=2).encode(),
        "application/json",
    )
    dataset = repo.insert_dataset(source_id, raw_path, checksum, fetched_at)
    return IngestResult(dataset, skipped=False)
