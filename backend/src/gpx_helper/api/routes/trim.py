from __future__ import annotations

from io import BytesIO
import tempfile
import zipfile

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from gpx_helper.api.utils.gpx import crop_file_by_time, ensure_within_bounds, get_time_bounds
from gpx_helper.api.utils.responses import stream_gpx, stream_payload
from gpx_helper.api.utils.uploads import validate_upload, write_upload_to_file
from gpx_helper.api.utils.validation import parse_request_times, parse_video_clips_payload, parse_positive

router = APIRouter()


@router.post("/gpx/trim-by-time")
def trim_by_time(
    gpx_file: UploadFile | str | None = File(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
) -> StreamingResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")
    start_dt, end_dt = parse_request_times(start_time, end_time)

    with tempfile.NamedTemporaryFile(suffix=".gpx") as input_file, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as output_file:
        write_upload_to_file(gpx_file, input_file, "GPX")
        crop_file_by_time(input_file.name, start_dt, end_dt, output_file.name)
        output_file.seek(0)
        return stream_gpx(output_file.read(), "trimmed.gpx")


@router.post("/gpx/trim-by-video")
def trim_by_video(
    gpx_file: UploadFile | str | None = File(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    duration_seconds: float = Form(...),
) -> StreamingResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")
    parse_positive(duration_seconds, "duration_seconds")
    start_dt, end_dt = parse_request_times(start_time, end_time, enforce_order=True)

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input, tempfile.NamedTemporaryFile(
        suffix=".gpx"
    ) as gpx_output:
        write_upload_to_file(gpx_file, gpx_input, "GPX")
        gpx_start, gpx_end = get_time_bounds(gpx_input.name)
        ensure_within_bounds(
            start_dt,
            end_dt,
            gpx_start,
            gpx_end,
            "Video timestamps fall outside GPX time range",
        )
        crop_file_by_time(gpx_input.name, start_dt, end_dt, gpx_output.name)

        gpx_output.seek(0)
        return stream_gpx(gpx_output.read(), "trimmed.gpx")


@router.post("/gpx/trim-by-videos")
def trim_by_videos(
    gpx_file: UploadFile | str | None = File(None),
    clips_json: str = Form(...),
) -> StreamingResponse:
    gpx_file = validate_upload(gpx_file, "gpx_file")
    clips = parse_video_clips_payload(clips_json)

    with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_input:
        write_upload_to_file(gpx_file, gpx_input, "GPX")
        gpx_start, gpx_end = get_time_bounds(gpx_input.name)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, clip in enumerate(clips, start=1):
                start_dt = clip["start_dt"]
                end_dt = clip["end_dt"]
                ensure_within_bounds(
                    start_dt,
                    end_dt,
                    gpx_start,
                    gpx_end,
                    f"Clip {index} timestamps fall outside GPX time range",
                )

                with tempfile.NamedTemporaryFile(suffix=".gpx") as gpx_output:
                    crop_file_by_time(gpx_input.name, start_dt, end_dt, gpx_output.name)

                    gpx_output.seek(0)
                    archive.writestr(f"{index}.gpx", gpx_output.read())

        return stream_payload(zip_buffer.getvalue(), "trimmed-gpx-files.zip", "application/zip")
