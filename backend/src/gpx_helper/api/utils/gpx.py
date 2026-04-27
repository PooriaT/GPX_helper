from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from gpx_helper.api.utils.exceptions import as_bad_request
from gpx_helper.gpx_splitter import crop_gpx_by_time, get_gpx_time_range


def get_time_bounds(gpx_path: str) -> tuple[datetime, datetime]:
    """Read first/last GPX timestamps from file."""
    return as_bad_request(get_gpx_time_range, gpx_path)


def crop_file_by_time(gpx_input_path: str, start_dt: datetime, end_dt: datetime, output_path: str) -> None:
    """Crop GPX points by UTC datetime range into an output file."""
    as_bad_request(crop_gpx_by_time, gpx_input_path, start_dt, end_dt, output_path)


def ensure_within_bounds(start_dt: datetime, end_dt: datetime, bound_start: datetime, bound_end: datetime, detail: str) -> None:
    if start_dt < bound_start or end_dt > bound_end:
        raise HTTPException(status_code=400, detail=detail)
