"""ONS fetcher tests. HTTP is faked with httpx.MockTransport: no network."""

import httpx
import pytest

from datatales.ingest import common, ons

API = "https://api.beta.ons.gov.uk/v1"
DOWNLOAD = "https://download.ons.gov.uk/downloads/datasets/x/editions/time-series/versions/4.csv"
STATIC = "https://static.ons.gov.uk/datasets/x-time-series-v4.csv"
CSV = b"v4_3,Time\n1.0,2011-12\n"  # fake


def handler(redirect_to: str = STATIC, body: bytes = CSV):  # noqa: ANN201
    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == f"{API}/datasets/x/editions/time-series":
            return httpx.Response(
                200,
                json={
                    "links": {
                        "latest_version": {
                            "href": f"{API}/datasets/x/editions/time-series/versions/4"
                        }
                    }
                },
            )
        if url.endswith("/versions/4"):
            return httpx.Response(
                200,
                json={
                    "version": 4,
                    "release_date": "2023-11-28T00:00:00.000Z",
                    "downloads": {"csv": {"href": DOWNLOAD}},
                },
            )
        if url == DOWNLOAD:
            return httpx.Response(301, headers={"location": redirect_to})
        if url == redirect_to:
            return httpx.Response(200, content=body)
        return httpx.Response(404)

    return handle


def client(**kw: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler(**kw)))  # type: ignore[arg-type]


def test_fetch_latest_follows_ons_redirect_and_records_metadata() -> None:
    raw = ons.fetch_latest("x", "time-series", client())
    assert raw.content == CSV
    assert raw.filename == "x-time-series-v4.csv"
    assert raw.source_url == DOWNLOAD
    assert raw.meta["version"] == "4"
    assert raw.meta["release_date"] == "2023-11-28T00:00:00.000Z"
    assert raw.meta["final_download_url"] == STATIC


def test_redirect_off_ons_is_refused() -> None:
    with pytest.raises(ons.OnsError, match="non-ONS"):
        ons.fetch_latest("x", "time-series", client(redirect_to="https://evil.example/x.csv"))


def test_plain_http_is_refused() -> None:
    with pytest.raises(ons.OnsError, match="non-HTTPS"):
        ons.fetch_latest("x", "time-series", client(redirect_to="http://static.ons.gov.uk/x.csv"))


def test_oversized_download_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ons, "MAX_RAW_BYTES", 10)
    with pytest.raises(ons.OnsError, match="exceeds"):
        ons.fetch_latest("x", "time-series", client(body=b"x" * 100))
    assert common.MAX_RAW_BYTES > 10  # the shared limit itself is untouched
