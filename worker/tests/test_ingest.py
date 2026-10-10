import json
from pathlib import Path

import pytest

from datatales.ingest.common import RawFile, ingest_raw, safe_filename, sha256
from datatales.ingest.upload import read_inbox_file
from datatales.sources import SourceDef, load_sources
from tests.memrepo import MemRepo

SOURCE = SourceDef.model_validate(
    {
        "slug": "fake-source",
        "name": "Fake source",
        "publisher": "Nobody",
        "url": "https://example.org/fake",
        "fetch": {"type": "upload"},
    }
)


def raw(content: bytes = b"a,b\n1,2\n", name: str = "fake.csv") -> RawFile:
    return RawFile(name, content, "upload:fake.csv", {"provider": "upload"})


def test_ingest_stores_raw_untouched_with_fetch_record() -> None:
    repo = MemRepo()
    result = ingest_raw(repo, SOURCE, raw())
    assert not result.skipped
    ds = result.dataset
    assert ds.checksum == sha256(b"a,b\n1,2\n")
    assert repo.get_object("raw", ds.raw_path) == b"a,b\n1,2\n"
    folder = ds.raw_path.rsplit("/", 1)[0]
    assert folder.startswith("fake-source/") and folder.endswith(ds.checksum[:12])
    record = json.loads(repo.get_object("raw", f"{folder}/fetch.json"))
    assert record["checksum_sha256"] == ds.checksum
    assert record["source_url"] == "upload:fake.csv"
    assert record["provider"] == "upload"


def test_same_file_twice_is_skipped() -> None:
    repo = MemRepo()
    first = ingest_raw(repo, SOURCE, raw())
    second = ingest_raw(repo, SOURCE, raw())
    assert second.skipped and second.dataset.id == first.dataset.id
    assert len(repo.datasets) == 1


def test_changed_file_is_a_new_dataset() -> None:
    repo = MemRepo()
    ingest_raw(repo, SOURCE, raw())
    assert not ingest_raw(repo, SOURCE, raw(b"a,b\n1,3\n")).skipped
    assert len(repo.datasets) == 2


@pytest.mark.parametrize(
    ("content", "name", "message"),
    [(b"", "x.csv", "empty"), (b"x", "x.exe", "unsupported"), (b"x", "noext", "unsupported")],
)
def test_bad_raw_files_rejected(content: bytes, name: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ingest_raw(MemRepo(), SOURCE, raw(content, name))


def test_safe_filename() -> None:
    assert safe_filename("../../etc/passwd") == "etc_passwd"
    assert safe_filename("UK cars (2024).xlsx") == "UK_cars_2024_.xlsx"


def test_inbox_reads_only_inside_inbox(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "cars.csv").write_bytes(b"a\n1\n")
    (tmp_path / "secret.csv").write_bytes(b"x\n")
    assert read_inbox_file("cars.csv", inbox).content == b"a\n1\n"
    with pytest.raises(ValueError, match="inside"):
        read_inbox_file("../secret.csv", inbox)
    with pytest.raises(ValueError, match="inside"):
        read_inbox_file(tmp_path / "secret.csv", inbox)
    with pytest.raises(FileNotFoundError):
        read_inbox_file("missing.csv", inbox)
    (inbox / "notes.txt").write_text("x")
    with pytest.raises(ValueError, match="unsupported"):
        read_inbox_file("notes.txt", inbox)


def test_committed_sources_file_is_valid() -> None:
    sources = load_sources()
    assert "ons-wellbeing-local-authority" in sources
    assert sources["ons-wellbeing-local-authority"].fetch.type == "ons_api"


def test_duplicate_source_slugs_rejected(tmp_path: Path) -> None:
    entry = (
        "  - {slug: a, name: A, publisher: P, url: 'https://example.org', fetch: {type: upload}}\n"
    )
    f = tmp_path / "sources.yaml"
    f.write_text("sources:\n" + entry + entry)
    with pytest.raises(ValueError, match="duplicate"):
        load_sources(f)
