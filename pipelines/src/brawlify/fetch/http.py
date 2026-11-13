"""Conditional GETs against BrawlAPI and GitHub."""

from pathlib import Path

import httpx

BASE_URL = "https://api.brawlapi.com"
CDN_TREE_URL = "https://api.github.com/repos/Brawlify/CDN/git/trees/master?recursive=1"


def get_json(
    client: httpx.Client, url: str, local: Path, etag: str | None
) -> tuple[dict | None, str | None]:
    """GET `url` unless `local` is current. Returns (payload or None on 304, new ETag).

    The ETag is only sent when `local` exists, or a deleted file would come back as 304.
    """
    headers = {"If-None-Match": etag} if etag and local.exists() else {}
    response = client.get(url, headers=headers)
    if response.status_code == 304:
        return None, etag
    response.raise_for_status()
    return response.json(), response.headers.get("etag")


def cdn_listing(tree: dict) -> dict:
    """Every .png path of the Brawlify CDN repo, sorted."""
    if tree["truncated"]:
        raise RuntimeError("CDN tree truncated by GitHub: images would look missing")
    files = [
        entry["path"]
        for entry in tree["tree"]
        if entry["type"] == "blob" and entry["path"].endswith(".png")
    ]
    return {"files": sorted(files)}
