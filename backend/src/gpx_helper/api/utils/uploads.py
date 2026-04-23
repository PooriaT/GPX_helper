from __future__ import annotations

import shutil
from typing import BinaryIO

from fastapi import HTTPException, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from gpx_helper.api.config import MAX_UPLOAD_READ_BYTES


def validate_upload(upload: UploadFile | str | None, label: str) -> StarletteUploadFile:
    """Validate an uploaded file object and ensure a filename exists."""
    if not isinstance(upload, StarletteUploadFile) or not upload.filename:
        raise HTTPException(status_code=400, detail=f"Missing {label} filename")
    return upload


def write_upload_to_file(upload: StarletteUploadFile, dest_file: BinaryIO, label: str) -> None:
    """Copy uploaded data into a temporary file and reject empty uploads."""
    upload.file.seek(0)
    first_chunk = upload.file.read(MAX_UPLOAD_READ_BYTES)
    if not first_chunk:
        raise HTTPException(status_code=400, detail=f"{label} file is empty")
    dest_file.write(first_chunk)
    shutil.copyfileobj(upload.file, dest_file)
    dest_file.flush()
    upload.file.seek(0)
