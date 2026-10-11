"""Source definitions: worker/sources.yaml (hand-made) plus worker/sources.d/*.yaml (one file
per dataset added from the backlog by the weekly new-dataset step)."""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from datatales.config import WORKER_DIR

SOURCES_FILE = WORKER_DIR / "sources.yaml"
SOURCES_DIR = WORKER_DIR / "sources.d"
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)]


class OnsApiFetch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ons_api"]
    dataset_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]+$")]
    edition: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]+$")]


class CatalogueFileFetch(BaseModel):
    """A file attached to a publisher's page, found again on every refresh (its URL usually
    changes with each release). `file_match` is matched against the attachment's file name
    (stable on GOV.UK, e.g. 'veh0105') or, failing that, its title."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["catalogue_file"]
    kind: Literal["govuk", "ons_page", "ons_cmd", "ckan", "html"]
    page_url: HttpUrl
    file_match: Annotated[str, Field(min_length=2, max_length=300)]
    format: Literal["CSV", "XLSX", "ODS"]


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
    # Administrative counts have no confidence intervals. When `lower`/`upper` are not set,
    # `precision_pct` gives each value a band of +/- precision_pct/2 percent, so changes
    # smaller than that count as "no change" (a materiality rule, not sampling error).
    precision_pct: Annotated[float, Field(gt=0, le=20)] | None = None
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
    fetch: Annotated[OnsApiFetch | CatalogueFileFetch | UploadFetch, Field(discriminator="type")]
    backlog_id: str | None = None  # the dataset_backlog item it came from
    detect: DetectConfig | None = None


class SourcesFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceDef]


def sources_dir(extra_dir: Path | None = None) -> Path:
    """The generated-sources folder (resolved per call, so tests can point it elsewhere)."""
    return SOURCES_DIR if extra_dir is None else extra_dir


def load_sources(path: Path = SOURCES_FILE, extra_dir: Path | None = None) -> dict[str, SourceDef]:
    data = SourcesFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    found = list(data.sources)
    extra_dir = sources_dir(extra_dir)
    if extra_dir.is_dir():
        for f in sorted(extra_dir.glob("*.yaml")):
            found.append(SourceDef.model_validate(yaml.safe_load(f.read_text(encoding="utf-8"))))
    slugs = [s.slug for s in found]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise ValueError(f"duplicate source slugs: {sorted(duplicates)}")
    return {s.slug: s for s in found}


def source_file(slug: str, extra_dir: Path | None = None) -> Path:
    return sources_dir(extra_dir) / f"{slug}.yaml"


def write_source_file(source: SourceDef, extra_dir: Path | None = None) -> Path:
    """Write (or rewrite) a generated source definition; committed by the workflow."""
    path = source_file(source.slug, extra_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Generated by the weekly new-dataset step (worker/datatales/newsource.py) from the\n"
        "# dataset backlog. `detect` is filled in when you approve the recipe.\n"
    )
    body = yaml.safe_dump(
        source.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True
    )
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return path


def get_source(slug: str, path: Path = SOURCES_FILE) -> SourceDef:
    sources = load_sources(path)
    if slug not in sources:
        raise KeyError(f"unknown source '{slug}'. Known: {', '.join(sorted(sources))}")
    return sources[slug]


def set_detect(slug: str, detect: dict, extra_dir: Path | None = None) -> Path | None:
    """On recipe approval: write the drafted `detect` block into a generated source file.
    Hand-made sources (sources.yaml) and sources that already have one are left alone."""
    path = source_file(slug, extra_dir)
    if not path.is_file():
        return None
    source = SourceDef.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    if source.detect is not None:
        return None
    updated = source.model_copy(update={"detect": DetectConfig.model_validate(detect)})
    return write_source_file(updated, extra_dir)
