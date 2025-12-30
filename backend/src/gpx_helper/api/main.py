from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import shutil
import tempfile
from typing import BinaryIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from gpx_helper.gpx_splitter import crop_gpx_by_time, get_gpx_time_range
from gpx_helper.map_animator import (
    create_animation,
    estimate_animation_seconds,
    latlon_to_web_mercator,
    load_gpx_points,
    parse_resolution,
    prepare_animation_data,
)

API_VERSION = "v1"
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:4173",
)
MAX_UPLOAD_READ_BYTES = 1024 * 1024

app = FastAPI(title="GPX Helper API", version=API_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(DEFAULT_ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Datetime must include timezone information")
    return dt.astimezone(timezone.utc)


def _parse_request_times(
    start_time: str, end_time: str, *, enforce_order: bool = False
) -> tuple[datetime, datetime]:
    try:
        start_dt = _parse_iso_datetime(start_time)
        end_dt = _parse_iso_datetime(end_time)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if enforce_order and start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")

    return start_dt, end_dt


def _validate_upload(upload: UploadFile | str | None, label: str) -> StarletteUploadFile:
    if not isinstance(upload, StarletteUploadFile) or not upload.filename:
        raise HTTPException(status_code=400, detail=f"Missing {label} filename")
    return upload


def _write_upload_to_file(upload: StarletteUploadFile, dest_file: BinaryIO, label: str) -> None:
    upload.file.seek(0)
    first_chunk = upload.file.read(MAX_UPLOAD_READ_BYTES)
    if not first_chunk:
        raise HTTPException(status_code=400, detail=f"{label} file is empty")
    dest_file.write(first_chunk)
    shutil.copyfileobj(upload.file, dest_file)
    dest_file.flush()
    upload.file.seek(0)


def _stream_gpx(payload: bytes, filename: str) -> StreamingResponse:
    return _stream_payload(payload, filename, "application/gpx+xml")


def _stream_payload(payload: bytes, filename: str, media_type: str) -> StreamingResponse:
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(BytesIO(payload), media_type=media_type, headers=headers)


@app.get("/api/v1/health")
def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "gpx-helper"})


@app.get("/api/v1/capabilities")
def capabilities() -> JSONResponse:
    return JSONResponse(
        {
            "version": API_VERSION,
            "endpoints": [
                "POST /api/v1/gpx/trim-by-time",
                "POST /api/v1/gpx/trim-by-video",
                "POST /api/v1/gpx/map-animate/estimate",
                "POST /api/v1/gpx/map-animate",
            ],
        }
    )


@app.post("/api/v1/gpx/trim-by-time")
def trim_by_time(
    gpx_file: UploadFile | str | None = File(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
) -> StreamingResponse:
    gpx_file = _validate_upload(gpx_file, "gpx_file")
    start_dt, end_dt = _parse_request_times(start_time, end_time)

    with tempfile.NamedTemporaryFile(suffix=".gpx") as input_file, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as output_file:
        _write_upload_to_file(gpx_file, input_file, "GPX")
        try:
            crop_gpx_by_time(input_file.name, start_dt, end_dt, output_file.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        output_file.seek(0)
        return _stream_gpx(output_file.read(), "trimmed.gpx")


@app.post("/api/v1/gpx/trim-by-video")
def trim_by_video(
    gpx_file: UploadFile | str | None = File(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    duration_seconds: float = Form(...),
) -> StreamingResponse:
    gpx_file = _validate_upload(gpx_file, "gpx_file")

    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="duration_seconds must be positive")
    start_dt, end_dt = _parse_request_times(start_time, end_time, enforce_order=True)

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as gpx_output:
        _write_upload_to_file(gpx_file, gpx_input, "GPX")
        try:
            gpx_start, gpx_end = get_gpx_time_range(gpx_input.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if start_dt < gpx_start or end_dt > gpx_end:
            raise HTTPException(
                status_code=400,
                detail="Video timestamps fall outside GPX time range",
            )
        try:
            crop_gpx_by_time(gpx_input.name, start_dt, end_dt, gpx_output.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        gpx_output.seek(0)
        return _stream_gpx(gpx_output.read(), "trimmed.gpx")


@app.post("/api/v1/gpx/map-animate/estimate")
def estimate_map_animation(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    resolution: str = Form(...),
) -> JSONResponse:
    gpx_file = _validate_upload(gpx_file, "gpx_file")

    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="duration_seconds must be positive")

    try:
        width_px, height_px = parse_resolution(resolution)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input:
        _write_upload_to_file(gpx_file, gpx_input, "GPX")
        try:
            lats, lons = load_gpx_points(gpx_input.name)
            estimated_seconds = estimate_animation_seconds(
                lats, lons, width_px, height_px, duration_seconds
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse({"estimated_seconds": round(float(estimated_seconds), 2)})


@app.post("/api/v1/gpx/map-animate")
def animate_gpx_route(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    resolution: str = Form(...),
) -> StreamingResponse:
    gpx_file = _validate_upload(gpx_file, "gpx_file")

    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="duration_seconds must be positive")

    try:
        width_px, height_px = parse_resolution(resolution)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=".mp4"
    ) as video_output:
        _write_upload_to_file(gpx_file, gpx_input, "GPX")

        try:
            lats, lons = load_gpx_points(gpx_input.name)
            xs, ys = latlon_to_web_mercator(lats, lons)
            frame_indices, total_frames, fps = prepare_animation_data(
                xs, ys, duration_seconds, fps=30
            )
            create_animation(
                xs,
                ys,
                frame_indices,
                total_frames,
                fps,
                width_px,
                height_px,
                video_output.name,
                min_lat=min(lats),
                max_lat=max(lats),
                min_lon=min(lons),
                max_lon=max(lons),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        video_output.seek(0)
        return _stream_payload(video_output.read(), "route.mp4", "video/mp4")
