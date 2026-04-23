from __future__ import annotations

from io import BytesIO

from fastapi.responses import StreamingResponse


def stream_payload(payload: bytes, filename: str, media_type: str) -> StreamingResponse:
    """Return binary payload as downloadable response."""
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(BytesIO(payload), media_type=media_type, headers=headers)


def stream_gpx(payload: bytes, filename: str) -> StreamingResponse:
    """Return GPX payload with GPX media type."""
    return stream_payload(payload, filename, "application/gpx+xml")
