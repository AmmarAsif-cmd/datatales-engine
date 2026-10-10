"""Source definitions, loaded from worker/sources.yaml."""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from datatales.config import WORKER_DIR

SOURCES_FILE = WORKER_DIR / "sources.yaml"
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)]


class OnsApiFetch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ons_api"]
    dataset_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]+$")]
    edition: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]+$")]


class UploadFetch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["upload"]


Scalar = str | int | float | bool
When = Annotated[dict[str, Annotated[list[Scalar], Field(min_length=1)]], Field(min_length=1)]


class UnitRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when: When
    unit: str


class LabelRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when: When
    label: str


class PolarityRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when: When
    higher_is_better: bool


class DetectConfig(BaseModel):
    """Maps a clean table's columns onto what the detectors need."""

    model_config = ConfigDict(extra="forbid")
    group: str
    group_code: str | None = None
    period: str
    period_label: str | None = None
    value: str
    lower: str | None = None
    upper: str | None = None
    slice_by: list[str] = Field(default_factory=list)
    filters: dict[str, Annotated[list[Scalar], Field(min_length=1)]] = Field(default_factory=dict)
    units: list[UnitRule] = Field(default_factory=list)
    default_unit: str = ""
    polarity: list[PolarityRule] = Field(default_factory=list)
    labels: list[LabelRule] = Field(default_factory=list)
    default_higher_is_better: bool = True
    min_groups_rank: Annotated[int, Field(ge=3)] = 3
    min_groups_outlier: Annotated[int, Field(ge=4)] = 5
    outlier_z: Annotated[float, Field(gt=0)] = 2.5
    top_n: Annotated[int, Field(ge=1, le=50)] = 5


class SourceDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: Slug
    name: str
    publisher: str
    url: HttpUrl
    licence: str | None = None
    refresh_schedule: str | None = None
    relatability: Annotated[int, Field(ge=1, le=5)] = 3
    caveats: list[str] = Field(default_factory=list)
    fetch: Annotated[OnsApiFetch | UploadFetch, Field(discriminator="type")]
    detect: DetectConfig | None = None


class SourcesFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceDef]


def load_sources(path: Path = SOURCES_FILE) -> dict[str, SourceDef]:
    data = SourcesFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    slugs = [s.slug for s in data.sources]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise ValueError(f"duplicate source slugs in {path.name}: {sorted(duplicates)}")
    return {s.slug: s for s in data.sources}


def get_source(slug: str, path: Path = SOURCES_FILE) -> SourceDef:
    sources = load_sources(path)
    if slug not in sources:
        raise KeyError(f"unknown source '{slug}'. Known: {', '.join(sorted(sources))}")
    return sources[slug]
