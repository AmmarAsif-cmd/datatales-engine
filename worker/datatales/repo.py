"""Persistence: the `Repo` interface and its Supabase implementation.

Pipeline code talks only to `Repo`, so tests can use the in-memory version in
tests/memrepo.py and never touch the network.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from supabase import Client

from datatales.sources import SourceDef

Bucket = Literal["raw", "clean"]
JobStatus = Literal["succeeded", "failed"]


@dataclass(frozen=True)
class Dataset:
    id: str
    source_id: str
    source_slug: str
    raw_path: str
    fetched_at: str
    checksum: str
    profile: dict[str, Any] | None


@dataclass(frozen=True)
class Recipe:
    id: str
    source_id: str
    version: int
    spec: dict[str, Any]
    approved_at: str | None
    approved_by: str | None

    @property
    def approved(self) -> bool:
        return self.approved_at is not None


class Repo(Protocol):
    def upsert_source(self, source: SourceDef) -> str: ...
    def get_source_id(self, slug: str) -> str | None: ...
    def find_dataset(self, source_id: str, checksum: str) -> Dataset | None: ...
    def insert_dataset(
        self, source_id: str, raw_path: str, checksum: str, fetched_at: datetime
    ) -> Dataset: ...
    def get_dataset(self, dataset_id: str) -> Dataset: ...
    def list_datasets(self, source_id: str | None = None, limit: int = 20) -> list[Dataset]: ...
    def set_profile(self, dataset_id: str, profile: dict[str, Any]) -> None: ...
    def list_recipes(self, source_id: str) -> list[Recipe]: ...
    def insert_recipe(self, source_id: str, version: int, spec: dict[str, Any]) -> Recipe: ...
    def approve_recipe(self, recipe_id: str, approved_by: str) -> Recipe: ...
    def upsert_clean_table(
        self,
        dataset_id: str,
        recipe_id: str,
        parquet_path: str,
        row_count: int,
        checks: list[dict[str, Any]],
        checks_passed: bool,
    ) -> str: ...
    def put_object(
        self, bucket: Bucket, path: str, data: bytes, content_type: str, upsert: bool = False
    ) -> None: ...
    def get_object(self, bucket: Bucket, path: str) -> bytes: ...
    def start_job(self, job_type: str) -> str: ...
    def finish_job(self, job_id: str, status: JobStatus, log: str, error: str | None) -> None: ...


def now_utc() -> datetime:
    return datetime.now(UTC)


def _dataset(row: dict[str, Any]) -> Dataset:
    return Dataset(
        id=row["id"],
        source_id=row["source_id"],
        source_slug=row["sources"]["slug"],
        raw_path=row["raw_path"],
        fetched_at=row["fetched_at"],
        checksum=row["checksum"],
        profile=row.get("profile"),
    )


def _recipe(row: dict[str, Any]) -> Recipe:
    return Recipe(
        id=row["id"],
        source_id=row["source_id"],
        version=row["version"],
        spec=row["spec"],
        approved_at=row.get("approved_at"),
        approved_by=row.get("approved_by"),
    )


class SupabaseRepo:
    """`Repo` backed by Supabase (service role). Used by the worker CLI and Actions."""

    _DATASET_COLS = "id, source_id, raw_path, fetched_at, checksum, profile, sources(slug)"

    def __init__(self, client: Client) -> None:
        self.db = client

    def upsert_source(self, source: SourceDef) -> str:
        row = {
            "slug": source.slug,
            "name": source.name,
            "publisher": source.publisher,
            "url": str(source.url),
            "licence": source.licence,
            "refresh_schedule": source.refresh_schedule,
            "relatability": source.relatability,
        }
        res = self.db.table("sources").upsert(row, on_conflict="slug").execute()
        return res.data[0]["id"]

    def get_source_id(self, slug: str) -> str | None:
        res = self.db.table("sources").select("id").eq("slug", slug).limit(1).execute()
        return res.data[0]["id"] if res.data else None

    def find_dataset(self, source_id: str, checksum: str) -> Dataset | None:
        res = (
            self.db.table("datasets")
            .select(self._DATASET_COLS)
            .eq("source_id", source_id)
            .eq("checksum", checksum)
            .limit(1)
            .execute()
        )
        return _dataset(res.data[0]) if res.data else None

    def insert_dataset(
        self, source_id: str, raw_path: str, checksum: str, fetched_at: datetime
    ) -> Dataset:
        row = {
            "source_id": source_id,
            "raw_path": raw_path,
            "checksum": checksum,
            "fetched_at": fetched_at.isoformat(),
        }
        res = self.db.table("datasets").insert(row).execute()
        return self.get_dataset(res.data[0]["id"])

    def get_dataset(self, dataset_id: str) -> Dataset:
        res = (
            self.db.table("datasets")
            .select(self._DATASET_COLS)
            .eq("id", dataset_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise KeyError(f"dataset {dataset_id} not found")
        return _dataset(res.data[0])

    def list_datasets(self, source_id: str | None = None, limit: int = 20) -> list[Dataset]:
        q = self.db.table("datasets").select(self._DATASET_COLS)
        if source_id:
            q = q.eq("source_id", source_id)
        res = q.order("fetched_at", desc=True).limit(limit).execute()
        return [_dataset(r) for r in res.data]

    def set_profile(self, dataset_id: str, profile: dict[str, Any]) -> None:
        self.db.table("datasets").update({"profile": profile}).eq("id", dataset_id).execute()

    def list_recipes(self, source_id: str) -> list[Recipe]:
        res = (
            self.db.table("recipes")
            .select("*")
            .eq("source_id", source_id)
            .order("version")
            .execute()
        )
        return [_recipe(r) for r in res.data]

    def insert_recipe(self, source_id: str, version: int, spec: dict[str, Any]) -> Recipe:
        row = {"source_id": source_id, "version": version, "spec": spec}
        return _recipe(self.db.table("recipes").insert(row).execute().data[0])

    def approve_recipe(self, recipe_id: str, approved_by: str) -> Recipe:
        res = (
            self.db.table("recipes")
            .update({"approved_at": now_utc().isoformat(), "approved_by": approved_by})
            .eq("id", recipe_id)
            .execute()
        )
        return _recipe(res.data[0])

    def upsert_clean_table(
        self,
        dataset_id: str,
        recipe_id: str,
        parquet_path: str,
        row_count: int,
        checks: list[dict[str, Any]],
        checks_passed: bool,
    ) -> str:
        row = {
            "dataset_id": dataset_id,
            "recipe_id": recipe_id,
            "parquet_path": parquet_path,
            "row_count": row_count,
            "checks": checks,
            "checks_passed": checks_passed,
        }
        res = (
            self.db.table("clean_tables").upsert(row, on_conflict="dataset_id,recipe_id").execute()
        )
        return res.data[0]["id"]

    def put_object(
        self, bucket: Bucket, path: str, data: bytes, content_type: str, upsert: bool = False
    ) -> None:
        self.db.storage.from_(bucket).upload(
            path, data, {"content-type": content_type, "upsert": "true" if upsert else "false"}
        )

    def get_object(self, bucket: Bucket, path: str) -> bytes:
        return self.db.storage.from_(bucket).download(path)

    def start_job(self, job_type: str) -> str:
        res = self.db.table("jobs").insert({"type": job_type, "status": "running"}).execute()
        return res.data[0]["id"]

    def finish_job(self, job_id: str, status: JobStatus, log: str, error: str | None) -> None:
        self.db.table("jobs").update(
            {
                "status": status,
                "finished_at": now_utc().isoformat(),
                "log": log,
                "error": error,
            }
        ).eq("id", job_id).execute()
