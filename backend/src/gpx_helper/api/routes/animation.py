from __future__ import annotations

from io import BytesIO
import json
import os
import re
import tempfile
import zipfile

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
    resolve_marker_style,
    resolve_tile_provider,
)

router = APIRouter()


BatchJob = dict[str, int | float | str | None]
BATCH_ROUTE_ANIMATION_POLICY = "Batch route animation currently uses all-or-nothing behavior."


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


def _parse_batch_jobs(jobs_json: str) -> list[BatchJob]:
    try:
        payload = json.loads(jobs_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="jobs_json must be valid JSON") from exc

    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=400, detail="jobs_json must be a non-empty array")

    jobs: list[BatchJob] = []
    for index, job in enumerate(payload, start=1):
        if not isinstance(job, dict):
            raise HTTPException(status_code=400, detail=f"Batch item {index}: must be an object")

        if "gpx_file_index" not in job:
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: missing gpx_file_index",
            )
        gpx_file_index = job.get("gpx_file_index")
        if not isinstance(gpx_file_index, int) or isinstance(gpx_file_index, bool):
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: gpx_file_index must be an integer",
            )

        duration_seconds = job.get("duration_seconds")
        if (
            not isinstance(duration_seconds, int | float)
            or isinstance(duration_seconds, bool)
            or duration_seconds <= 0
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: duration_seconds must be greater than zero",
            )

        output_name = job.get("output_name")
        if output_name is not None and not isinstance(output_name, str):
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: output_name must be a string",
            )

        jobs.append(
            {
                "gpx_file_index": gpx_file_index,
                "duration_seconds": float(duration_seconds),
                "output_name": output_name,
            }
        )

    return jobs


def _parse_batch_uploads_and_jobs(
    gpx_files: list[UploadFile] | None,
    jobs_json: str,
) -> tuple[list[UploadFile], list[BatchJob]]:
    if not gpx_files:
        raise HTTPException(status_code=400, detail="Missing gpx_files uploads")

    validated_gpx_files = []
    for index, gpx_file in enumerate(gpx_files, start=1):
        try:
            validated_gpx_files.append(validate_upload(gpx_file, f"gpx_files[{index - 1}]"))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else "invalid uploaded GPX file"
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: missing or invalid uploaded GPX file ({detail})",
            ) from exc

    jobs = _parse_batch_jobs(jobs_json)
    if len(jobs) != len(validated_gpx_files):
        raise HTTPException(
            status_code=400,
            detail="Batch job count must match uploaded GPX file count",
        )

    seen_gpx_indexes: set[int] = set()
    for index, job in enumerate(jobs, start=1):
        gpx_file_index = int(job["gpx_file_index"])
        if gpx_file_index < 0 or gpx_file_index >= len(validated_gpx_files):
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: gpx_file_index is out of range",
            )
        if gpx_file_index in seen_gpx_indexes:
            raise HTTPException(
                status_code=400,
                detail=f"Batch item {index}: duplicate gpx_file_index {gpx_file_index}",
            )
        seen_gpx_indexes.add(gpx_file_index)

    return validated_gpx_files, jobs


def _batch_item_error(index: int, gpx_file: UploadFile, exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException) and isinstance(exc.detail, str):
        reason = exc.detail
    else:
        reason = str(exc)
    filename = os.path.basename(gpx_file.filename or "")
    item_label = f"Batch item {index}"
    if filename:
        item_label = f"{item_label} ({filename})"
    return HTTPException(status_code=400, detail=f"{item_label} failed: {reason}")


def _validate_batch_render_jobs(
    gpx_paths: list[str],
    jobs: list[BatchJob],
    gpx_files: list[UploadFile],
    fps: float,
) -> None:
    for index, job in enumerate(jobs, start=1):
        gpx_file_index = int(job["gpx_file_index"])
        try:
            lats, lons = as_bad_request(load_gpx_points, gpx_paths[gpx_file_index])
            xs, ys = as_bad_request(latlon_to_web_mercator, lats, lons)
            as_bad_request(
                prepare_animation_series,
                xs,
                ys,
                float(job["duration_seconds"]),
                fps=fps,
            )
        except Exception as exc:
            raise _batch_item_error(index, gpx_files[gpx_file_index], exc) from exc


def _sanitize_output_stem(value: str, fallback: str) -> str:
    filename = os.path.basename(value.strip())
    stem = os.path.splitext(filename)[0] if filename else ""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return stem or fallback


def _unique_mp4_name(stem: str, used_names: set[str]) -> str:
    candidate = f"{stem}.mp4"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    suffix = 2
    while True:
        candidate = f"{stem}-{suffix}.mp4"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        suffix += 1


def _batch_output_name(
    job: BatchJob,
    gpx_file: UploadFile,
    used_names: set[str],
) -> str:
    output_name = job.get("output_name")
    if isinstance(output_name, str) and output_name.strip():
        stem = _sanitize_output_stem(output_name, "route")
    else:
        upload_name = os.path.basename(gpx_file.filename or "")
        fallback_stem = os.path.splitext(upload_name)[0] if upload_name else "route"
        stem = _sanitize_output_stem(fallback_stem, "route")
    return _unique_mp4_name(stem, used_names)


def _render_animation_file(
    gpx_input_path: str,
    video_output_path: str,
    duration_seconds: float,
    fps: float,
    width_px: int,
    height_px: int,
    marker_color: str,
    trail_color: str,
    full_trail_color: str,
    full_trail_opacity: float,
    line_width: float,
    line_opacity: float,
    marker_size: float,
    marker_style: str,
    tile_template: str,
    tile_subdomains: tuple[str, ...],
) -> None:
    lats, lons = as_bad_request(load_gpx_points, gpx_input_path)
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
        video_output_path,
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
        marker_style=marker_style,
        tile_template=tile_template,
        tile_subdomains=tile_subdomains,
    )


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
    marker_style: str = Form("default"),
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
        resolve_marker_style(marker_style)
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


@router.post("/gpx/map-animate/batch/estimate")
def estimate_map_animation_batch(
    gpx_files: list[UploadFile] | None = File(None),
    jobs_json: str = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    marker_color: str = Form("#0ea5e9"),
    trail_color: str = Form("#0ea5e9"),
    full_trail_color: str = Form("#111827"),
    full_trail_opacity: float = Form(0.8),
    line_width: float = Form(2.5),
    line_opacity: float = Form(1.0),
    marker_size: float = Form(6.0),
    marker_style: str = Form("default"),
    tile_type: str | None = Form(None),
) -> JSONResponse:
    """Estimate batch route animation using the all-or-nothing batch policy."""
    del marker_color, trail_color, full_trail_color
    validated_gpx_files, jobs = _parse_batch_uploads_and_jobs(gpx_files, jobs_json)

    width_px, height_px = _parse_animation_inputs(
        float(jobs[0]["duration_seconds"]),
        fps,
        resolution,
        line_width,
        marker_size,
        full_trail_opacity,
        line_opacity,
    )

    try:
        resolve_marker_style(marker_style)
        resolve_tile_provider(tile_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.TemporaryDirectory() as tmp_dir:
        gpx_paths: list[str] = []
        for index, gpx_file in enumerate(validated_gpx_files):
            gpx_path = os.path.join(tmp_dir, f"input-{index}.gpx")
            try:
                with open(gpx_path, "w+b") as gpx_input:
                    write_upload_to_file(gpx_file, gpx_input, "GPX")
            except Exception as exc:
                raise _batch_item_error(index + 1, gpx_file, exc) from exc
            gpx_paths.append(gpx_path)

        estimated_seconds = 0.0
        for index, job in enumerate(jobs, start=1):
            gpx_file_index = int(job["gpx_file_index"])
            try:
                lats, lons = as_bad_request(load_gpx_points, gpx_paths[gpx_file_index])
                estimated_seconds += float(
                    as_bad_request(
                        estimate_animation_seconds,
                        lats,
                        lons,
                        width_px,
                        height_px,
                        float(job["duration_seconds"]),
                        fps=fps,
                    )
                )
            except Exception as exc:
                raise _batch_item_error(index, validated_gpx_files[gpx_file_index], exc) from exc

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
    marker_style: str = Form("default"),
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
        marker_style = resolve_marker_style(marker_style)
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
            marker_style=marker_style,
            tile_template=tile_template,
            tile_subdomains=tile_subdomains,
        )

        video_output.seek(0)
        upload_name = os.path.basename(gpx_file.filename or "")
        stem = os.path.splitext(upload_name)[0] if upload_name else "route"
        output_name = f"{stem}.mp4"
        return stream_payload(video_output.read(), output_name, "video/mp4")


@router.post("/gpx/map-animate/batch")
def animate_gpx_routes_batch(
    gpx_files: list[UploadFile] | None = File(None),
    jobs_json: str = Form(...),
    fps: float = Form(DEFAULT_FPS),
    resolution: str = Form(...),
    marker_color: str = Form("#0ea5e9"),
    trail_color: str = Form("#0ea5e9"),
    full_trail_color: str = Form("#111827"),
    full_trail_opacity: float = Form(0.8),
    line_width: float = Form(2.5),
    line_opacity: float = Form(1.0),
    marker_size: float = Form(6.0),
    marker_style: str = Form("default"),
    tile_type: str | None = Form(None),
) -> StreamingResponse:
    """Render batch route animation using the all-or-nothing batch policy."""
    validated_gpx_files, jobs = _parse_batch_uploads_and_jobs(gpx_files, jobs_json)

    width_px, height_px = _parse_animation_inputs(
        float(jobs[0]["duration_seconds"]),
        fps,
        resolution,
        line_width,
        marker_size,
        full_trail_opacity,
        line_opacity,
    )

    try:
        marker_style = resolve_marker_style(marker_style)
        tile_template, tile_subdomains = resolve_tile_provider(tile_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with tempfile.TemporaryDirectory() as tmp_dir:
        gpx_paths: list[str] = []
        for index, gpx_file in enumerate(validated_gpx_files):
            gpx_path = os.path.join(tmp_dir, f"input-{index}.gpx")
            try:
                with open(gpx_path, "w+b") as gpx_input:
                    write_upload_to_file(gpx_file, gpx_input, "GPX")
            except Exception as exc:
                raise _batch_item_error(index + 1, gpx_file, exc) from exc
            gpx_paths.append(gpx_path)

        _validate_batch_render_jobs(gpx_paths, jobs, validated_gpx_files, fps)

        zip_buffer = BytesIO()
        used_names: set[str] = set()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, job in enumerate(jobs, start=1):
                gpx_file_index = int(job["gpx_file_index"])
                output_path = os.path.join(tmp_dir, f"output-{index}.mp4")
                try:
                    _render_animation_file(
                        gpx_paths[gpx_file_index],
                        output_path,
                        float(job["duration_seconds"]),
                        fps,
                        width_px,
                        height_px,
                        marker_color,
                        trail_color,
                        full_trail_color,
                        full_trail_opacity,
                        line_width,
                        line_opacity,
                        marker_size,
                        marker_style,
                        tile_template,
                        tile_subdomains,
                    )
                    archive.write(
                        output_path,
                        _batch_output_name(job, validated_gpx_files[gpx_file_index], used_names),
                    )
                except Exception as exc:
                    raise _batch_item_error(index, validated_gpx_files[gpx_file_index], exc) from exc

        return stream_payload(zip_buffer.getvalue(), "route-animations.zip", "application/zip")
