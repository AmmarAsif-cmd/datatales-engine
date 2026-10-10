"""Ingest a local CSV/XLSX file placed in worker/data/inbox/."""

from pathlib import Path

from datatales.config import WORKER_DIR
from datatales.ingest.common import CONTENT_TYPES, MAX_RAW_BYTES, RawFile, extension

INBOX = WORKER_DIR / "data" / "inbox"


def read_inbox_file(name_or_path: str | Path, inbox: Path = INBOX) -> RawFile:
    inbox = inbox.resolve()
    candidate = Path(name_or_path)
    path = (candidate if candidate.is_absolute() else inbox / candidate).resolve()
    if not path.is_relative_to(inbox):
        raise ValueError(f"file must be inside {inbox}")
    if not path.is_file():
        raise FileNotFoundError(f"no such file in inbox: {path.name}")
    if extension(path.name) not in CONTENT_TYPES:
        raise ValueError(f"unsupported file type: {path.name} (use .csv or .xlsx)")
    if path.stat().st_size > MAX_RAW_BYTES:
        raise ValueError(f"{path.name} is larger than {MAX_RAW_BYTES:,} bytes")
    return RawFile(
        filename=path.name,
        content=path.read_bytes(),
        source_url=f"upload:{path.name}",
        meta={"provider": "upload", "original_filename": path.name},
    )
