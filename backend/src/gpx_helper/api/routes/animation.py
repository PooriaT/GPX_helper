from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from gpx_helper.api.utils.exceptions import as_bad_request
from gpx_helper.api.utils.responses import stream_payload
from gpx_helper.api.utils.uploads import validate_upload, write_upload_to_file
from gpx_helper.api.utils.validation import (
    parse_positive,
    validate_opacity,
    validate_resolution_dims,
)
from gpx_helper.map_animator import (
    DEFAULT_FPS,
    create_animation,
    estimate_animation_seconds,
    latlon_to_web_mercator,
    load_gpx_points,
    parse_resolution,
    prepare_animation_series,
    resolve_tile_provider,
)

router = APIRouter()


def _parse_animation_inputs(
    duration_seconds: float,
    fps: float,
    resolution: str,
    line_width: float,
    marker_size: float,
    full_trail_opacity: float,
    line_opacity: float,
) -> tuple[int, int]:
    parse_positive(duration_seconds, "duration_seconds")
    parse_positive(fps, "fps")
    try:
        width_px, height_px = parse_resolution(resolution)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    validate_resolution_dims(width_px, height_px)
    parse_positive(line_width, "line_width")
    parse_positive(marker_size, "marker_size")
    validate_opacity(full_trail_opacity, "full_trail_opacity")
    validate_opacity(line_opacity, "line_opacity")
    return width_px, height_px


@router.post("/gpx/map-animate/estimate")
def estimate_map_animation(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    marker_color: str = Form("#0ea5e9"),
    trail_color: str = Form("#0ea5e9"),
    full_trail_color: str = Form("#111827"),
    full_trail_opacity: float = Form(0.8),
    line_width: float = Form(2.5),
    line_opacity: float = Form(1.0),
    marker_size: float = Form(6.0),
    tile_type: str | None = Form(None),
) -> JSONResponse:
    del marker_color, trail_color, full_trail_color
    gpx_file = validate_upload(gpx_file, "gpx_file")

    width_px, height_px = _parse_animation_inputs(
        duration_seconds,
        fps,
        resolution,
        line_width,
        marker_size,
        full_trail_opacity,
        line_opacity,
    )

    try:
        resolve_tile_provider(tile_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input:
        write_upload_to_file(gpx_file, gpx_input, "GPX")
        lats, lons = as_bad_request(load_gpx_points, gpx_input.name)
        estimated_seconds = as_bad_request(
            estimate_animation_seconds,
            lats,
            lons,
            width_px,
            height_px,
            duration_seconds,
            fps=fps,
        )

    return JSONResponse({"estimated_seconds": round(float(estimated_seconds), 2)})


@router.post("/gpx/map-animate")
def animate_gpx_route(
    gpx_file: UploadFile | str | None = File(None),
    duration_seconds: float = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    marker_color: str = Form("#0ea5e9"),
    trail_color: str = Form("#0ea5e9"),
    full_trail_color: str = Form("#111827"),
    full_trail_opacity: float = Form(0.8),
    line_width: float = Form(2.5),
    line_opacity: float = Form(1.0),
    marker_size: float = Form(6.0),
    tile_type: str | None = Form(None),
) -> StreamingResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")

    width_px, height_px = _parse_animation_inputs(
        duration_seconds,
        fps,
        resolution,
        line_width,
        marker_size,
        full_trail_opacity,
        line_opacity,
    )

    try:
        tile_template, tile_subdomains = resolve_tile_provider(tile_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=".mp4"
    ) as video_output:
        write_upload_to_file(gpx_file, gpx_input, "GPX")

        lats, lons = as_bad_request(load_gpx_points, gpx_input.name)
        xs, ys = as_bad_request(latlon_to_web_mercator, lats, lons)
        xs, ys, frame_indices, total_frames, fps = as_bad_request(
            prepare_animation_series,
            xs,
            ys,
            duration_seconds,
            fps=fps,
        )
        as_bad_request(
            create_animation,
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
            marker_color=marker_color,
            animated_line_color=trail_color,
            full_line_color=full_trail_color,
            full_line_opacity=full_trail_opacity,
            line_width=line_width,
            animated_line_opacity=line_opacity,
            marker_size=marker_size,
            tile_template=tile_template,
            tile_subdomains=tile_subdomains,
        )

        video_output.seek(0)
        upload_name = os.path.basename(gpx_file.filename or "")
        stem = os.path.splitext(upload_name)[0] if upload_name else "route"
        output_name = f"{stem}.mp4"
        return stream_payload(video_output.read(), output_name, "video/mp4")
