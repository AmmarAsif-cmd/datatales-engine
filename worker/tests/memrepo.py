"""In-memory `Repo` for tests. Mirrors the constraints of migration 0001 that matter here."""

import uuid
from datetime import datetime
from typing import Any

from datatales.repo import Bucket, CleanTable, Dataset, JobStatus, Recipe, now_utc
from datatales.sources import SourceDef


class MemRepo:
    def __init__(self) -> None:
        self.sources: dict[str, dict[str, Any]] = {}  # slug -> row
        self.datasets: dict[str, Dataset] = {}
        self.recipes: dict[str, Recipe] = {}
        self.clean_tables: dict[tuple[str, str], dict[str, Any]] = {}
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.findings: dict[str, dict[str, Any]] = {}
        self.stories: dict[str, dict[str, Any]] = {}

    def upsert_source(self, source: SourceDef) -> str:
        existing = self.sources.get(source.slug)
        source_id = existing["id"] if existing else str(uuid.uuid4())
        self.sources[source.slug] = {"id": source_id, **source.model_dump(mode="json")}
        return source_id

    def get_source_id(self, slug: str) -> str | None:
        row = self.sources.get(slug)
        return row["id"] if row else None

    def _slug(self, source_id: str) -> str:
        return next(s for s, r in self.sources.items() if r["id"] == source_id)

    def find_dataset(self, source_id: str, checksum: str) -> Dataset | None:
        return next(
            (
                d
                for d in self.datasets.values()
                if d.source_id == source_id and d.checksum == checksum
            ),
            None,
        )

    def insert_dataset(
        self, source_id: str, raw_path: str, checksum: str, fetched_at: datetime
    ) -> Dataset:
        if self.find_dataset(source_id, checksum):
            raise ValueError("duplicate (source_id, checksum)")
        ds = Dataset(
            id=str(uuid.uuid4()),
            source_id=source_id,
            source_slug=self._slug(source_id),
            raw_path=raw_path,
            fetched_at=fetched_at.isoformat(),
            checksum=checksum,
            profile=None,
        )
        self.datasets[ds.id] = ds
        return ds

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id not in self.datasets:
            raise KeyError(f"dataset {dataset_id} not found")
        return self.datasets[dataset_id]

    def list_datasets(self, source_id: str | None = None, limit: int = 20) -> list[Dataset]:
        found = [d for d in self.datasets.values() if source_id in (None, d.source_id)]
        return sorted(found, key=lambda d: d.fetched_at, reverse=True)[:limit]

    def set_profile(self, dataset_id: str, profile: dict[str, Any]) -> None:
        ds = self.datasets[dataset_id]
        self.datasets[dataset_id] = Dataset(**{**ds.__dict__, "profile": profile})

    def list_recipes(self, source_id: str) -> list[Recipe]:
        found = [r for r in self.recipes.values() if r.source_id == source_id]
        return sorted(found, key=lambda r: r.version)

    def insert_recipe(self, source_id: str, version: int, spec: dict[str, Any]) -> Recipe:
        if any(r.version == version for r in self.list_recipes(source_id)):
            raise ValueError("duplicate (source_id, version)")
        recipe = Recipe(str(uuid.uuid4()), source_id, version, spec, None, None)
        self.recipes[recipe.id] = recipe
        return recipe

    def replace_unapproved_spec(self, recipe_id: str, spec: dict[str, Any]) -> Recipe:
        r = self.recipes[recipe_id]
        if r.approved:
            raise ValueError(f"recipe {recipe_id} is approved or missing; it cannot be replaced")
        self.recipes[recipe_id] = Recipe(r.id, r.source_id, r.version, spec, None, None)
        return self.recipes[recipe_id]

    def approve_recipe(self, recipe_id: str, approved_by: str) -> Recipe:
        r = self.recipes[recipe_id]
        approved = Recipe(r.id, r.source_id, r.version, r.spec, now_utc().isoformat(), approved_by)
        self.recipes[recipe_id] = approved
        return approved

    def upsert_clean_table(
        self,
        dataset_id: str,
        recipe_id: str,
        parquet_path: str,
        row_count: int,
        checks: list[dict[str, Any]],
        checks_passed: bool,
    ) -> str:
        key = (dataset_id, recipe_id)
        row_id = self.clean_tables.get(key, {}).get("id") or str(uuid.uuid4())
        self.clean_tables[key] = {
            "id": row_id,
            "parquet_path": parquet_path,
            "row_count": row_count,
            "checks": checks,
            "checks_passed": checks_passed,
        }
        return row_id

    def get_clean_table(self, clean_table_id: str) -> CleanTable:
        for (dataset_id, recipe_id), row in self.clean_tables.items():
            if row["id"] == clean_table_id:
                return CleanTable(
                    clean_table_id,
                    dataset_id,
                    recipe_id,
                    row["parquet_path"],
                    row["row_count"],
                    row["checks_passed"],
                )
        raise KeyError(f"clean table {clean_table_id} not found")

    def list_findings(self, clean_table_id: str) -> list[dict[str, Any]]:
        rows = [f for f in self.findings.values() if f["clean_table_id"] == clean_table_id]
        return sorted(rows, key=lambda f: -f["score"])

    def insert_findings(self, clean_table_id: str, records: list[dict[str, Any]]) -> list[str]:
        ids = []
        for rec in records:
            fid = str(uuid.uuid4())
            self.findings[fid] = {"id": fid, "clean_table_id": clean_table_id, **rec}
            ids.append(fid)
        return ids

    def delete_findings(self, clean_table_id: str) -> int:
        doomed = [k for k, f in self.findings.items() if f["clean_table_id"] == clean_table_id]
        for k in doomed:
            del self.findings[k]
        return len(doomed)

    def count_stories_using(self, finding_ids: list[str]) -> int:
        wanted = set(finding_ids)
        return sum(1 for s in self.stories.values() if wanted & set(s["finding_ids"]))

    def put_object(
        self, bucket: Bucket, path: str, data: bytes, content_type: str, upsert: bool = False
    ) -> None:
        if (bucket, path) in self.objects and not upsert:
            raise ValueError(f"object exists: {bucket}/{path}")
        self.objects[(bucket, path)] = (data, content_type)

    def get_object(self, bucket: Bucket, path: str) -> bytes:
        return self.objects[(bucket, path)][0]

    def start_job(self, job_type: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {"type": job_type, "status": "running"}
        return job_id

    def finish_job(self, job_id: str, status: JobStatus, log: str, error: str | None) -> None:
        self.jobs[job_id] |= {"status": status, "log": log, "error": error}
