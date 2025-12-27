# GPX Helper Backend

This backend is a FastAPI service that exposes endpoints for working with GPX files.
It accepts GPX uploads and trims the track data based on a requested time range or
based on video metadata timestamps calculated by the client.

## How it works

The API is implemented in `backend/src/gpx_helper/api/main.py` and exposes:

- `GET /api/v1/health` for a basic service check.
- `GET /api/v1/capabilities` to describe available endpoints.
- `POST /api/v1/gpx/trim-by-time` to crop a GPX file to a provided time range.
- `POST /api/v1/gpx/trim-by-video` to crop a GPX file based on the time range
  provided by client-side video metadata.
- `POST /api/v1/gpx/map-animate` to render a GPX track into an MP4 map animation
  using a requested duration and resolution.

GPX trimming logic lives in `backend/src/gpx_helper/gpx_splitter.py`.
The trim-by-video endpoint expects the client to send start/end timestamps plus
the video duration derived from metadata (for example, using the browser video tag).
The map animation endpoint uses `backend/src/gpx_helper/map_animator.py`.

## Running the API locally

Install dependencies with Poetry and run the app with Uvicorn:

```bash
cd backend
poetry install
poetry run uvicorn gpx_helper.api.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Example requests

```bash
curl -X POST http://localhost:8000/api/v1/gpx/trim-by-time \
  -F gpx_file=@/path/to/track.gpx \
  -F start_time=2025-11-02T17:02:23Z \
  -F end_time=2025-11-02T17:07:00Z \
  --output trimmed.gpx
```

```bash
curl -X POST http://localhost:8000/api/v1/gpx/trim-by-video \
  -F gpx_file=@/path/to/track.gpx \
  -F start_time=2025-11-02T17:02:23Z \
  -F end_time=2025-11-02T17:07:00Z \
  -F duration_seconds=277 \
  --output trimmed.gpx
```

```bash
curl -X POST http://localhost:8000/api/v1/gpx/map-animate \
  -F gpx_file=@/path/to/track.gpx \
  -F duration_seconds=45 \
  -F resolution=1920x1080 \
  --output route.mp4
```

## Running unit tests

The backend unit tests are located in `backend/tests`.
Run them from the `backend` directory:

```bash
cd backend
poetry run python -m unittest
```
