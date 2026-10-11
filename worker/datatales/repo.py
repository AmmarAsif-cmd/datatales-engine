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
    status: str = "draft"  # draft | ready (passed its test run) | failed | rejected
    drafted_by: str | None = None
    dataset_id: str | None = None
    test_report: dict[str, Any] | None = None
    reject_note: str | None = None

    @property
    def approved(self) -> bool:
        return self.approved_at is not None


@dataclass(frozen=True)
class CleanTable:
    id: str
    dataset_id: str
    recipe_id: str
    parquet_path: str
    row_count: int
    checks_passed: bool


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
    def insert_recipe(
        self,
        source_id: str,
        version: int,
        spec: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> Recipe: ...
    def approve_recipe(self, recipe_id: str, approved_by: str) -> Recipe: ...
    def replace_unapproved_spec(self, recipe_id: str, spec: dict[str, Any]) -> Recipe: ...
    def update_unapproved_recipe(self, recipe_id: str, fields: dict[str, Any]) -> Recipe: ...
    def get_recipe(self, recipe_id: str) -> Recipe: ...
    def upsert_clean_table(
        self,
        dataset_id: str,
        recipe_id: str,
        parquet_path: str,
        row_count: int,
        checks: list[dict[str, Any]],
        checks_passed: bool,
    ) -> str: ...
    def get_clean_table(self, clean_table_id: str) -> CleanTable: ...
    def find_clean_table(self, dataset_id: str, recipe_id: str) -> CleanTable | None: ...
    def get_findings(self, finding_ids: list[str]) -> list[dict[str, Any]]: ...
    def list_findings(self, clean_table_id: str) -> list[dict[str, Any]]: ...
    def insert_findings(self, clean_table_id: str, records: list[dict[str, Any]]) -> list[str]: ...
    def delete_findings(self, clean_table_id: str) -> int: ...
    def count_stories_using(self, finding_ids: list[str]) -> int: ...
    def insert_story(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_story(self, story_id: str) -> dict[str, Any]: ...
    def update_story(self, story_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...
    def story_id_for_slug(self, slug: str) -> str | None: ...
    def list_stories(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def put_object(
        self, bucket: Bucket, path: str, data: bytes, content_type: str, upsert: bool = False
    ) -> None: ...
    def get_object(self, bucket: Bucket, path: str) -> bytes: ...
    def start_job(self, job_type: str) -> str: ...
    def finish_job(self, job_id: str, status: JobStatus, log: str, error: str | None) -> None: ...
    def insert_llm_call(self, row: dict[str, Any]) -> str: ...
    def update_llm_call(self, call_id: str, fields: dict[str, Any]) -> None: ...
    def llm_spend_since(self, since: datetime) -> tuple[float, int]: ...


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
        status=row.get("status") or "draft",
        drafted_by=row.get("drafted_by"),
        dataset_id=row.get("dataset_id"),
        test_report=row.get("test_report"),
        reject_note=row.get("reject_note"),
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

    def insert_recipe(
        self,
        source_id: str,
        version: int,
        spec: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> Recipe:
        row = {"source_id": source_id, "version": version, "spec": spec, **(meta or {})}
        return _recipe(self.db.table("recipes").insert(row).execute().data[0])

    def get_recipe(self, recipe_id: str) -> Recipe:
        res = self.db.table("recipes").select("*").eq("id", recipe_id).execute()
        if not res.data:
            raise ValueError(f"recipe {recipe_id} not found")
        return _recipe(res.data[0])

    def update_unapproved_recipe(self, recipe_id: str, fields: dict[str, Any]) -> Recipe:
        res = (
            self.db.table("recipes")
            .update(fields)
            .eq("id", recipe_id)
            .is_("approved_at", "null")  # never touch an approved recipe
            .execute()
        )
        if not res.data:
            raise ValueError(f"recipe {recipe_id} is approved or missing; it cannot be changed")
        return _recipe(res.data[0])

    def replace_unapproved_spec(self, recipe_id: str, spec: dict[str, Any]) -> Recipe:
        res = (
            self.db.table("recipes")
            # a changed spec has not been tested: back to draft
            .update({"spec": spec, "status": "draft", "test_report": None})
            .eq("id", recipe_id)
            .is_("approved_at", "null")  # never touch an approved recipe
            .execute()
        )
        if not res.data:
            raise ValueError(f"recipe {recipe_id} is approved or missing; it cannot be replaced")
        return _recipe(res.data[0])

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

    def get_clean_table(self, clean_table_id: str) -> CleanTable:
        res = self.db.table("clean_tables").select("*").eq("id", clean_table_id).limit(1).execute()
        if not res.data:
            raise KeyError(f"clean table {clean_table_id} not found")
        row = res.data[0]
        return CleanTable(
            id=row["id"],
            dataset_id=row["dataset_id"],
            recipe_id=row["recipe_id"],
            parquet_path=row["parquet_path"],
            row_count=row["row_count"],
            checks_passed=row["checks_passed"],
        )

    def find_clean_table(self, dataset_id: str, recipe_id: str) -> CleanTable | None:
        res = (
            self.db.table("clean_tables")
            .select("id")
            .eq("dataset_id", dataset_id)
            .eq("recipe_id", recipe_id)
            .limit(1)
            .execute()
        )
        return self.get_clean_table(res.data[0]["id"]) if res.data else None

    def get_findings(self, finding_ids: list[str]) -> list[dict[str, Any]]:
        if not finding_ids:
            return []
        return self.db.table("findings").select("*").in_("id", finding_ids).execute().data

    def list_findings(self, clean_table_id: str) -> list[dict[str, Any]]:
        res = (
            self.db.table("findings")
            .select("*")
            .eq("clean_table_id", clean_table_id)
            .order("score", desc=True)
            .execute()
        )
        return res.data

    def insert_findings(self, clean_table_id: str, records: list[dict[str, Any]]) -> list[str]:
        if not records:
            return []
        rows = [{**rec, "clean_table_id": clean_table_id} for rec in records]
        return [r["id"] for r in self.db.table("findings").insert(rows).execute().data]

    def delete_findings(self, clean_table_id: str) -> int:
        res = self.db.table("findings").delete().eq("clean_table_id", clean_table_id).execute()
        return len(res.data)

    def count_stories_using(self, finding_ids: list[str]) -> int:
        if not finding_ids:
            return 0
        res = (
            self.db.table("stories")
            .select("id", count="exact")
            .overlaps("finding_ids", finding_ids)
            .execute()
        )
        return res.count or 0

    def insert_story(self, row: dict[str, Any]) -> dict[str, Any]:
        return self.db.table("stories").insert(row).execute().data[0]

    def get_story(self, story_id: str) -> dict[str, Any]:
        res = self.db.table("stories").select("*").eq("id", story_id).limit(1).execute()
        if not res.data:
            raise KeyError(f"story {story_id} not found")
        return res.data[0]

    def update_story(self, story_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        res = self.db.table("stories").update(fields).eq("id", story_id).execute()
        if not res.data:
            raise KeyError(f"story {story_id} not found")
        return res.data[0]

    def story_id_for_slug(self, slug: str) -> str | None:
        res = self.db.table("stories").select("id").eq("slug", slug).limit(1).execute()
        return res.data[0]["id"] if res.data else None

    def list_stories(self, limit: int = 50) -> list[dict[str, Any]]:
        res = (
            self.db.table("stories")
            .select("id, slug, headline, status, verify_status, updated_at")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data

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

    # ---- Claude API usage (llm_calls) ----

    def insert_llm_call(self, row: dict[str, Any]) -> str:
        res = self.db.table("llm_calls").insert(row).execute()
        return str(res.data[0]["id"])

    def update_llm_call(self, call_id: str, fields: dict[str, Any]) -> None:
        self.db.table("llm_calls").update(fields).eq("id", call_id).execute()

    def llm_spend_since(self, since: datetime) -> tuple[float, int]:
        """(GBP spent or reserved since `since`, number of completed calls)."""
        res = (
            self.db.table("llm_calls")
            .select("estimated_cost,status")
            .gte("created_at", since.isoformat())
            .execute()
        )
        rows = res.data or []
        spent = sum(float(r["estimated_cost"] or 0) for r in rows)
        calls = sum(1 for r in rows if r["status"] in ("ok", "invalid_output"))
        return spent, calls
