"""Reverse proxy — forward HTTP requests to app Unix domain sockets."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger("squareberg.proxy")


async def proxy_request(
    socket_path: Path,
    method: str,
    path: str,
    headers: list[tuple[str, str]],
    body: bytes | None = None,
    query_string: str = "",
) -> httpx.Response:
    """Forward an HTTP request to an app listening on a Unix domain socket.

    Args:
        socket_path: Path to the Unix socket file.
        method: HTTP method (GET, POST, etc.).
        path: Request path to forward (e.g. "/api/search").
        headers: List of (name, value) header tuples.
        body: Raw request body bytes, or None.
        query_string: Query string (without leading '?').

    Returns:
        The httpx.Response from the upstream app.
    """
    url = f"http://localhost{path}"
    if query_string:
        url = f"{url}?{query_string}"

    # Filter out hop-by-hop headers that should not be forwarded.
    _hop_by_hop = frozenset({
        "connection", "keep-alive", "proxy-authenticate",
        "proxy-authorization", "te", "trailers",
        "transfer-encoding", "upgrade", "host",
    })
    forwarded_headers = {
        k: v for k, v in headers if k.lower() not in _hop_by_hop
    }

    transport = httpx.AsyncHTTPTransport(uds=str(socket_path))
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=forwarded_headers,
            content=body,
        )

    return response
