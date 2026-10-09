"""Settings from environment variables, with an optional local `.env` file.

Real environment variables (e.g. GitHub Actions secrets) take precedence over `.env`.
The service key is held as a SecretStr so it is never printed or logged by accident.
"""

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, field_validator

WORKER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = WORKER_DIR / ".env"

REQUIRED_VARS = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")


class ConfigError(Exception):
    """Raised when required settings are missing or invalid."""


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    supabase_url: str
    supabase_service_role_key: SecretStr

    @field_validator("supabase_url")
    @classmethod
    def _https_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith("https://"):
            raise ValueError("must start with https://")
        return value

    @field_validator("supabase_service_role_key")
    @classmethod
    def _non_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return value


def parse_env_file(text: str) -> dict[str, str]:
    """Parse simple KEY=VALUE lines. Ignores blanks and comments; strips matching quotes."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


def load_settings(
    env: dict[str, str] | None = None, env_file: Path | None = DEFAULT_ENV_FILE
) -> Settings:
    file_values: dict[str, str] = {}
    if env_file is not None and env_file.is_file():
        file_values = parse_env_file(env_file.read_text(encoding="utf-8-sig"))
    environ = os.environ if env is None else env
    merged = {name: environ.get(name) or file_values.get(name, "") for name in REQUIRED_VARS}

    missing = [name for name, value in merged.items() if not value]
    if missing:
        raise ConfigError(
            f"Missing settings: {', '.join(missing)}. "
            "Set them in worker/.env (copy worker/.env.example) or as environment variables."
        )
    try:
        return Settings(
            supabase_url=merged["SUPABASE_URL"],
            supabase_service_role_key=SecretStr(merged["SUPABASE_SERVICE_ROLE_KEY"]),
        )
    except ValidationError as exc:
        problems = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in exc.errors())
        raise ConfigError(f"Invalid settings: {problems}") from None
