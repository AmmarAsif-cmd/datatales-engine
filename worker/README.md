# DataTales worker

Python pipeline: ingest → profile → clean → detect → narrate → verify → publish.

See the root [README](../README.md) for setup. Quick start:

```sh
uv sync
uv run python -m datatales --help
uv run ruff check . && uv run ruff format --check . && uv run pytest
```
