import pytest

from datatales import __version__
from datatales.cli import main


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: datatales" in capsys.readouterr().out


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_db_check_without_settings_fails_cleanly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from datatales import cli, config

    def no_settings() -> config.Settings:
        raise config.ConfigError("Missing settings: SUPABASE_URL")

    monkeypatch.setattr(cli, "load_settings", no_settings)
    assert main(["db-check"]) == 1
    assert "Missing settings" in capsys.readouterr().err


def test_recipe_test_command_dry_runs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], ons_csv: bytes
) -> None:
    from datatales import cli, pipeline
    from datatales.config import WORKER_DIR
    from datatales.ingest.common import RawFile
    from datatales.sources import get_source
    from tests.memrepo import MemRepo

    repo = MemRepo()
    pipeline.sync_sources(repo)
    slug = "ons-wellbeing-local-authority"
    ds = pipeline.ingest(repo, get_source(slug), RawFile("f.csv", ons_csv, "x"), print).dataset
    monkeypatch.setattr(cli, "_repo", lambda: repo)
    draft = WORKER_DIR / "recipes" / "drafts" / f"{slug}.v1.yaml"

    assert main(["recipe-test", str(draft), ds.id]) == 1  # 20 fake rows < 90k expected
    out = capsys.readouterr().out
    assert "FAIL  row_count" in out and "PASS  unique" in out
    assert "dry run" not in out


def test_unknown_dataset_is_one_line_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from datatales import cli
    from tests.memrepo import MemRepo

    monkeypatch.setattr(cli, "_repo", MemRepo)
    assert main(["profile", "00000000-0000-0000-0000-000000000000"]) == 1
    assert "not found" in capsys.readouterr().err
