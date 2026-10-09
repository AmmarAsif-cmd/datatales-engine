from pathlib import Path

import pytest

from datatales.config import ConfigError, load_settings, parse_env_file

GOOD_URL = "https://example-ref.supabase.co"
FAKE_KEY = "fake-test-key-not-real"


def test_parse_env_file_handles_comments_quotes_and_export() -> None:
    text = "# comment\n\nA=1\nexport B=\"two\"\nC='three'\nNOEQUALS\nD= spaced \n"
    assert parse_env_file(text) == {"A": "1", "B": "two", "C": "three", "D": "spaced"}


def test_load_from_environment_without_file() -> None:
    env = {"SUPABASE_URL": GOOD_URL + "/", "SUPABASE_SERVICE_ROLE_KEY": FAKE_KEY}
    settings = load_settings(env=env, env_file=None)
    assert settings.supabase_url == GOOD_URL
    assert settings.supabase_service_role_key.get_secret_value() == FAKE_KEY


def test_environment_overrides_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"SUPABASE_URL=https://from-file.supabase.co\nSUPABASE_SERVICE_ROLE_KEY={FAKE_KEY}\n"
    )
    settings = load_settings(env={"SUPABASE_URL": GOOD_URL}, env_file=env_file)
    assert settings.supabase_url == GOOD_URL
    assert settings.supabase_service_role_key.get_secret_value() == FAKE_KEY


def test_missing_values_raise_clear_error() -> None:
    with pytest.raises(ConfigError, match="SUPABASE_SERVICE_ROLE_KEY"):
        load_settings(env={"SUPABASE_URL": GOOD_URL}, env_file=None)


def test_non_https_url_rejected() -> None:
    env = {"SUPABASE_URL": "http://insecure.example", "SUPABASE_SERVICE_ROLE_KEY": FAKE_KEY}
    with pytest.raises(ConfigError, match="https"):
        load_settings(env=env, env_file=None)


def test_key_is_never_shown_in_repr() -> None:
    env = {"SUPABASE_URL": GOOD_URL, "SUPABASE_SERVICE_ROLE_KEY": FAKE_KEY}
    settings = load_settings(env=env, env_file=None)
    assert FAKE_KEY not in repr(settings)
    assert FAKE_KEY not in str(settings)
