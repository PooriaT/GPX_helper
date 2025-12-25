# GPX Helper Backend

This backend is a FastAPI service that exposes endpoints for working with GPX files.
It accepts GPX uploads and trims the track data based on a requested time range or
based on timestamps extracted from a companion video file.

## How it works

The API is implemented in `backend/src/gpx_helper/api/main.py` and exposes:

- `GET /api/v1/health` for a basic service check.
- `GET /api/v1/capabilities` to describe available endpoints.
- `POST /api/v1/gpx/trim-by-time` to crop a GPX file to a provided time range.
- `POST /api/v1/gpx/trim-by-video` to crop a GPX file based on the time range
  extracted from an uploaded video.

GPX trimming logic lives in `backend/src/gpx_helper/gpx_splitter.py`.
The trim-by-video endpoint uses `get_video_times`, which reads video metadata via
`exiftool` if it is available, then falls back to the file modification time.

## Running the API locally

Install dependencies with Poetry and run the app with Uvicorn:

```bash
cd backend
poetry install
poetry run uvicorn gpx_helper.api.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Running unit tests

The backend unit tests are located in `backend/tests`.
Run them from the `backend` directory:

```bash
cd backend
poetry run python -m unittest
```
