"""Fetch the latest version of an ONS API dataset as CSV.

API docs: https://developer.ons.gov.uk/ . Only HTTPS URLs on ONS hosts are followed.
"""

from typing import Any
from urllib.parse import urlparse

import httpx

from datatales.errors import UserError
from datatales.ingest.common import MAX_RAW_BYTES, RawFile

API_ROOT = "https://api.beta.ons.gov.uk/v1"
ALLOWED_HOSTS = frozenset(
    {"api.beta.ons.gov.uk", "download.ons.gov.uk", "static.ons.gov.uk", "www.ons.gov.uk"}
)
USER_AGENT = "DataTales/0.1 (+https://datatales.co.uk)"
TIMEOUT = httpx.Timeout(30.0, read=120.0)


class OnsError(UserError):
    pass


def _check_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise OnsError(f"refusing to fetch non-ONS or non-HTTPS URL: {url}")
    return url


def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    resp = client.get(_check_url(url))
    resp.raise_for_status()
    return resp.json()


def _download(client: httpx.Client, url: str) -> tuple[bytes, str]:
    """Download with redirects, checking every hop and capping the size."""
    current = _check_url(url)
    for _ in range(5):
        with client.stream("GET", current) as resp:
            if resp.is_redirect:
                location = resp.headers.get("location", "")
                current = _check_url(str(resp.url.join(location)))
                continue
            resp.raise_for_status()
            chunks, total = [], 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > MAX_RAW_BYTES:
                    raise OnsError(f"download exceeds {MAX_RAW_BYTES:,} bytes: {current}")
                chunks.append(chunk)
            return b"".join(chunks), current
    raise OnsError(f"too many redirects: {url}")


def fetch_latest(dataset_id: str, edition: str, client: httpx.Client | None = None) -> RawFile:
    own_client = client is None
    client = client or httpx.Client(
        timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=False
    )
    try:
        ed = _get_json(client, f"{API_ROOT}/datasets/{dataset_id}/editions/{edition}")
        version_url = ed["links"]["latest_version"]["href"]
        version = _get_json(client, version_url)
        csv_url = version["downloads"]["csv"]["href"]
        content, final_url = _download(client, csv_url)
    finally:
        if own_client:
            client.close()

    version_id = str(version.get("version") or version.get("id") or "unknown")
    return RawFile(
        filename=f"{dataset_id}-{edition}-v{version_id}.csv",
        content=content,
        source_url=csv_url,
        meta={
            "provider": "ons_api",
            "dataset_id": dataset_id,
            "edition": edition,
            "version": version_id,
            "release_date": version.get("release_date"),
            "api_version_url": version_url,
            "final_download_url": final_url,
        },
    )
