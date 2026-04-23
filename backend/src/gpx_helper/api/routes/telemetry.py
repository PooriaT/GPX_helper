from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from gpx_helper.api.utils.responses import stream_payload
from gpx_helper.api.utils.uploads import validate_upload, write_upload_to_file
from gpx_helper.api.utils.validation import parse_positive, validate_resolution_dims
from gpx_helper.map_animator import DEFAULT_FPS, parse_resolution
from gpx_helper.telemetry_animator import (
    create_telemetry_animation,
    ensure_telemetry_type_supported,
    estimate_telemetry_seconds,
    load_gpx_telemetry,
    parse_background_color,
    resolve_telemetry_type,
)

router = APIRouter()


def _parse_video_dimensions(duration_seconds: float, fps: float, resolution: str) -> tuple[int, int]:
    parse_positive(duration_seconds, "duration_seconds")
    parse_positive(fps, "fps")

    try:
        width_px, height_px = parse_resolution(resolution)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    validate_resolution_dims(width_px, height_px)
    return width_px, height_px


@router.post("/gpx/telemetry-video/estimate")
def estimate_telemetry_video(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    telemetry_type: str = Form(...),
) -> JSONResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")
    width_px, height_px = _parse_video_dimensions(duration_seconds, fps, resolution)

    try:
        resolved_type = resolve_telemetry_type(telemetry_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input:
        write_upload_to_file(gpx_file, gpx_input, "GPX")
        try:
            telemetry_points = load_gpx_telemetry(gpx_input.name)
            ensure_telemetry_type_supported(telemetry_points, resolved_type)
            estimated_seconds = estimate_telemetry_seconds(
                duration_seconds, width_px, height_px, fps=fps
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse({"estimated_seconds": round(float(estimated_seconds), 2)})


@router.post("/gpx/telemetry-video")
def render_telemetry_video(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    telemetry_type: str = Form(...),
    background_color: str = Form("transparent"),
) -> StreamingResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")
    width_px, height_px = _parse_video_dimensions(duration_seconds, fps, resolution)

    try:
        resolved_type = resolve_telemetry_type(telemetry_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        output_background = parse_background_color(background_color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    has_alpha = output_background[3] < 255
    output_suffix = ".webm" if has_alpha else ".mp4"
    output_media_type = "video/webm" if has_alpha else "video/mp4"

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=output_suffix
    ) as video_output:
        write_upload_to_file(gpx_file, gpx_input, "GPX")
        try:
            telemetry_points = load_gpx_telemetry(gpx_input.name)
            ensure_telemetry_type_supported(telemetry_points, resolved_type)
            create_telemetry_animation(
                telemetry_points,
                duration_seconds=duration_seconds,
                fps=fps,
                width_px=width_px,
                height_px=height_px,
                telemetry_type=resolved_type,
                background_color=background_color,
                output_path=video_output.name,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        video_output.seek(0)
        upload_name = os.path.basename(gpx_file.filename or "")
        stem = os.path.splitext(upload_name)[0] if upload_name else "telemetry"
        output_name = f"{stem}-{resolved_type}{output_suffix}"
        return stream_payload(video_output.read(), output_name, output_media_type)
