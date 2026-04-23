from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi import HTTPException


def parse_iso_datetime(value: str) -> datetime:
    """Parse timezone-aware ISO datetime and normalize to UTC."""
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Datetime must include timezone information")
    return dt.astimezone(timezone.utc)


def parse_request_times(
    start_time: str, end_time: str, *, enforce_order: bool = False
) -> tuple[datetime, datetime]:
    """Parse and validate start/end timestamps from request fields."""
    try:
        start_dt = parse_iso_datetime(start_time)
        end_dt = parse_iso_datetime(end_time)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if enforce_order and start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")

    return start_dt, end_dt


def parse_positive(value: float, label: str) -> None:
    """Require a strictly positive numeric value."""
    if value <= 0:
        raise HTTPException(status_code=400, detail=f"{label} must be positive")


def parse_video_clips_payload(clips_json: str) -> list[dict[str, datetime | float]]:
    """Parse and validate the trim-by-videos clips JSON payload."""
    try:
        payload = json.loads(clips_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="clips_json must be valid JSON") from exc

    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=400, detail="clips_json must be a non-empty array")

    clips: list[dict[str, datetime | float]] = []
    for index, clip in enumerate(payload, start=1):
        if not isinstance(clip, dict):
            raise HTTPException(status_code=400, detail=f"Clip {index} must be an object")

        start_time = clip.get("start_time")
        end_time = clip.get("end_time")
        duration_seconds = clip.get("duration_seconds")

        if not isinstance(start_time, str) or not isinstance(end_time, str):
            raise HTTPException(
                status_code=400,
                detail=f"Clip {index} must include start_time and end_time strings",
            )
        if not isinstance(duration_seconds, int | float) or duration_seconds <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Clip {index} duration_seconds must be positive",
            )

        start_dt, end_dt = parse_request_times(start_time, end_time, enforce_order=True)
        clips.append(
            {
                "start_dt": start_dt,
                "end_dt": end_dt,
                "duration_seconds": float(duration_seconds),
            }
        )

    return clips


def validate_resolution_dims(width_px: int, height_px: int) -> None:
    """Require positive width/height values."""
    if width_px <= 0 or height_px <= 0:
        raise HTTPException(status_code=400, detail="resolution must be positive")


def validate_opacity(value: float, label: str) -> None:
    """Require opacity value in [0, 1]."""
    if value < 0 or value > 1:
        raise HTTPException(status_code=400, detail=f"{label} must be between 0 and 1")
