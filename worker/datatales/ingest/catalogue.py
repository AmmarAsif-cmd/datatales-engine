"""Find and fetch a data file attached to a publisher's page (fetch type `catalogue_file`).

Publishers attach a new file to the same page with each release, usually at a new URL, so
the source stores the PAGE and a stable `file_match`, and the file is found again on every
refresh:

* govuk:    GOV.UK Content API (www.gov.uk/api/content/<path>): the page's attachments; for
            a collection page, the attachments of its documents.
* ons_page: ONS website JSON (<page>/data -> current version -> downloads).
* ons_cmd:  ONS API dataset (latest version's CSV download).
* ckan:     data.gov.uk record (its resources).
* html:     links to .csv/.xlsx/.ods files in the page's HTML (other GOV.UK/NHS pages).

Only HTTPS on government hosts (*.gov.uk, *.nhs.uk, ONS and Nomis) is followed, every
redirect hop is checked, and downloads are capped at MAX_RAW_BYTES.
"""

import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx

from datatales.errors import UserError
from datatales.ingest.common import MAX_RAW_BYTES, RawFile

USER_AGENT = "DataTales/0.1 (+https://datatales.co.uk)"
TIMEOUT = httpx.Timeout(30.0, read=180.0)
MAX_DOCUMENTS = 10  # collection pages: how many documents to look into
FORMATS = {".csv": "CSV", ".xlsx": "XLSX", ".ods": "ODS"}
EXTRA_HOSTS = frozenset({"www.nomisweb.co.uk"})


class CatalogueError(UserError):
    pass


@dataclass(frozen=True)
class FileRef:
    title: str
    url: str
    filename: str
    format: str  # CSV | XLSX | ODS
    size: int | None = None


def allowed_host(host: str | None) -> bool:
    host = (host or "").lower()
    return host.endswith(".gov.uk") or host.endswith(".nhs.uk") or host in EXTRA_HOSTS


def check_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not allowed_host(parsed.hostname):
        raise CatalogueError(f"refusing to fetch non-HTTPS or non-government URL: {url}")
    return url


def file_format(name: str) -> str | None:
    lower = name.lower().split("?")[0]
    return next((f for ext, f in FORMATS.items() if lower.endswith(ext)), None)


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=False)


def _get(client: httpx.Client, url: str) -> httpx.Response:
    current = check_url(url)
    for _ in range(5):
        resp = client.get(current)
        if resp.is_redirect:
            current = check_url(str(resp.url.join(resp.headers.get("location", ""))))
            continue
        resp.raise_for_status()
        if len(resp.content) > 10 * 1024 * 1024:
            raise CatalogueError(f"page too large: {current}")
        return resp
    raise CatalogueError(f"too many redirects: {url}")


def _json(client: httpx.Client, url: str) -> Any:
    return _get(client, url).json()


# ---- listing the files on a page ----


def _govuk_attachments(page: dict[str, Any]) -> list[FileRef]:
    out = []
    for a in (page.get("details") or {}).get("attachments") or []:
        url = a.get("url") or ""
        name = a.get("filename") or url.rsplit("/", 1)[-1]
        fmt = file_format(name)
        if fmt and url:
            out.append(
                FileRef((a.get("title") or name).strip(), url, name, fmt, a.get("file_size"))
            )
    return out


def _govuk(client: httpx.Client, page_url: str) -> list[FileRef]:
    path = urlparse(page_url).path
    page = _json(client, f"https://www.gov.uk/api/content{path}")
    files = _govuk_attachments(page)
    if files:
        return files
    for doc in ((page.get("links") or {}).get("documents") or [])[:MAX_DOCUMENTS]:
        base = doc.get("base_path")
        if base:
            files += _govuk_attachments(_json(client, f"https://www.gov.uk/api/content{base}"))
    return files


def _ons_page(client: httpx.Client, page_url: str) -> list[FileRef]:
    page = _json(client, page_url.rstrip("/") + "/data")
    out = []
    for ds in page.get("datasets") or [{"uri": urlparse(page_url).path}]:
        uri = ds.get("uri")
        if not uri:
            continue
        version = _json(client, f"https://www.ons.gov.uk{uri}/data")
        title = ((version.get("description") or {}).get("title") or "").strip()
        for d in version.get("downloads") or []:
            name = d.get("file") or ""
            fmt = file_format(name)
            if fmt:
                url = f"https://www.ons.gov.uk/file?uri={quote(uri + '/' + name)}"
                out.append(FileRef(title or name, url, name, fmt))
    return out


def _ons_cmd(client: httpx.Client, page_url: str) -> list[FileRef]:
    dataset_id = urlparse(page_url).path.rstrip("/").rsplit("/", 1)[-1]
    meta = _json(client, f"https://api.beta.ons.gov.uk/v1/datasets/{dataset_id}")
    version = _json(client, meta["links"]["latest_version"]["href"])
    csv = ((version.get("downloads") or {}).get("csv") or {}).get("href")
    if not csv:
        return []
    size = ((version.get("downloads") or {}).get("csv") or {}).get("size")
    return [FileRef(meta.get("title") or dataset_id, csv, f"{dataset_id}.csv", "CSV",
                    int(size) if size else None)]  # fmt: skip


def _ckan(client: httpx.Client, page_url: str) -> list[FileRef]:
    parts = urlparse(page_url).path.strip("/").split("/")
    dataset_id = parts[1] if len(parts) > 1 else parts[-1]
    data = _json(
        client,
        f"https://ckan.publishing.service.gov.uk/api/action/package_show?id={quote(dataset_id)}",
    )
    out = []
    for r in (data.get("result") or {}).get("resources") or []:
        url = r.get("url") or ""
        fmt = (r.get("format") or "").strip(" .").upper() or file_format(url) or ""
        if fmt not in FORMATS.values() or not url.startswith("https://"):
            continue
        name = url.split("?")[0].rsplit("/", 1)[-1] or f"{r.get('id')}.{fmt.lower()}"
        size = r.get("size")
        out.append(FileRef((r.get("name") or name).strip(), url, name, fmt,
                           int(size) if str(size or "").isdigit() else None))  # fmt: skip
    return out


LINK = re.compile(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)


def _html(client: httpx.Client, page_url: str) -> list[FileRef]:
    html = _get(client, page_url).text
    out, seen = [], set()
    for href, text in LINK.findall(html):
        url = urljoin(page_url, unescape(href))
        fmt = file_format(url)
        if not fmt or url in seen or not allowed_host(urlparse(url).hostname):
            continue
        seen.add(url)
        title = re.sub(r"<[^>]+>", " ", unescape(text))
        out.append(FileRef(" ".join(title.split()) or url, url, url.rsplit("/", 1)[-1], fmt))
    return out


LISTERS = {
    "govuk": _govuk,
    "ons_page": _ons_page,
    "ons_cmd": _ons_cmd,
    "ckan": _ckan,
    "html": _html,
}


def kind_for(url: str, catalogue: str | None = None) -> str:
    """Which lister fits a page URL (backlog source_url)."""
    host = (urlparse(url).hostname or "").lower()
    if host == "www.gov.uk":
        return "govuk"
    if host == "www.ons.gov.uk":
        return "ons_cmd" if urlparse(url).path.startswith("/datasets/") else "ons_page"
    if host.endswith("data.gov.uk") and "/dataset/" in url:
        return "ckan"
    return "html"


def list_files(kind: str, page_url: str, client: httpx.Client | None = None) -> list[FileRef]:
    own = client is None
    client = client or _client()
    try:
        files = LISTERS[kind](client, check_url(page_url))
    finally:
        if own:
            client.close()
    # government-hosted, HTTPS files only
    return [
        f for f in files if allowed_host(urlparse(f.url).hostname) and f.url.startswith("https://")
    ]


def _stem(name: str) -> str:
    return re.sub(r"\.(csv|xlsx|ods)$", "", name.lower().split("?")[0])


DATED = re.compile(r"(19|20)\d{2}([-_]?(0[1-9]|1[0-2]|q[1-4]))?([-_]?\d{2})?")


def stable_name(name: str) -> str:
    """A file name without release dates, so the next release still matches:
    'evci5001_2026-07_orcs_uk.ods' -> 'evci5001_orcs_uk'; 'veh0105.ods' -> 'veh0105'."""
    stem = DATED.sub("", _stem(name))
    return re.sub(r"[-_ ]{2,}", "_", stem).strip("-_ ")


def match_file(files: list[FileRef], file_match: str, fmt: str) -> FileRef:
    """The file a source refers to: by file name (stable on GOV.UK), else by title."""
    wanted = file_match.lower().strip()
    same_format = [f for f in files if f.format == fmt] or files
    for pick in (
        [f for f in same_format if stable_name(f.filename) == wanted],
        [f for f in same_format if _stem(f.filename) == wanted],
        [f for f in same_format if wanted in f.filename.lower()],
        [f for f in same_format if f.title.lower() == wanted],
        [f for f in same_format if wanted in f.title.lower()],
    ):
        if pick:
            return pick[0]
    raise CatalogueError(f"no file matching '{file_match}' ({fmt}) on the page any more")


def download(url: str, client: httpx.Client | None = None) -> tuple[bytes, str]:
    """Download with every redirect hop checked and the size capped."""
    own = client is None
    client = client or _client()
    try:
        current = check_url(url)
        for _ in range(5):
            with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    current = check_url(str(resp.url.join(resp.headers.get("location", ""))))
                    continue
                resp.raise_for_status()
                chunks, total = [], 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > MAX_RAW_BYTES:
                        raise CatalogueError(
                            f"file is larger than {MAX_RAW_BYTES:,} bytes: {current}"
                        )
                    chunks.append(chunk)
                return b"".join(chunks), current
        raise CatalogueError(f"too many redirects: {url}")
    finally:
        if own:
            client.close()


def fetch_catalogue_file(
    kind: str, page_url: str, file_match: str, fmt: str, client: httpx.Client | None = None
) -> RawFile:
    own = client is None
    client = client or _client()
    try:
        ref = match_file(list_files(kind, page_url, client), file_match, fmt)
        content, final_url = download(ref.url, client)
    finally:
        if own:
            client.close()
    ext = {"CSV": ".csv", "XLSX": ".xlsx", "ODS": ".ods"}[ref.format]
    filename = ref.filename if ref.filename.lower().endswith(ext) else f"{_stem(ref.filename)}{ext}"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", filename)[:120]
    return RawFile(
        filename=safe,
        content=content,
        source_url=final_url,
        meta={
            "provider": "catalogue_file",
            "kind": kind,
            "page_url": page_url,
            "file_title": ref.title,
            "file_url": ref.url,
        },  # fmt: skip
    )
