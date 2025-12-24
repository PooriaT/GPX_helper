from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from gpx_helper.gpx_splitter import crop_gpx_by_time, get_video_times

API_VERSION = "v1"
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:4173",
)

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


def _validate_upload(upload: UploadFile, label: str) -> None:
    if not upload.filename:
        raise HTTPException(status_code=400, detail=f"Missing {label} filename")


def _read_upload(upload: UploadFile) -> bytes:
    return upload.file.read()


def _stream_gpx(payload: bytes, filename: str) -> StreamingResponse:
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/gpx+xml",
        headers=headers,
    )


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
            ],
        }
    )


@app.post("/api/v1/gpx/trim-by-time")
def trim_by_time(
    gpx_file: UploadFile = File(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
) -> StreamingResponse:
    _validate_upload(gpx_file, "gpx_file")

    try:
        start_dt = _parse_iso_datetime(start_time)
        end_dt = _parse_iso_datetime(end_time)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    gpx_bytes = _read_upload(gpx_file)
    if not gpx_bytes:
        raise HTTPException(status_code=400, detail="GPX file is empty")

    with tempfile.NamedTemporaryFile(suffix=".gpx") as input_file, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as output_file:
        input_file.write(gpx_bytes)
        input_file.flush()
        try:
            crop_gpx_by_time(input_file.name, start_dt, end_dt, output_file.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        output_file.seek(0)
        return _stream_gpx(output_file.read(), "trimmed.gpx")


@app.post("/api/v1/gpx/trim-by-video")
def trim_by_video(
    gpx_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
) -> StreamingResponse:
    _validate_upload(gpx_file, "gpx_file")
    _validate_upload(video_file, "video_file")

    gpx_bytes = _read_upload(gpx_file)
    video_bytes = _read_upload(video_file)
    if not gpx_bytes:
        raise HTTPException(status_code=400, detail="GPX file is empty")
    if not video_bytes:
        raise HTTPException(status_code=400, detail="Video file is empty")

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as gpx_output, tempfile.NamedTemporaryFile(suffix=".mp4") as video_input:
        gpx_input.write(gpx_bytes)
        gpx_input.flush()
        video_input.write(video_bytes)
        video_input.flush()

        try:
            start_dt, end_dt = get_video_times(video_input.name)
            crop_gpx_by_time(gpx_input.name, start_dt, end_dt, gpx_output.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        gpx_output.seek(0)
        return _stream_gpx(gpx_output.read(), "trimmed.gpx")
