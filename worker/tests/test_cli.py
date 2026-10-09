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
