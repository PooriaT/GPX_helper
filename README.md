# GPX_helper

Utilities for aligning GoPro (or other camera) video timestamps with GPX tracks. The primary tool, `gpx_splitter.py`, crops a GPX track to match a video clip so you can sync footage and GPS data for mapping or overlays. The repository now includes a `frontend/` Svelte landing page and a `backend/` Python workspace that hosts the CLI tools.

## Features
- Extracts video start time and duration from EXIF metadata via `exiftool`.
- Matches GPX track points closest to the video start/end times and writes a cropped GPX.
- Falls back to file modification time when metadata is missing, with clear warnings.
- Works with GPX files that include timezone-aware timestamps (UTC recommended).

## Requirements
- Python 3.8+
- [`exiftool`](https://exiftool.org/) available in your `PATH` (for `gpx_splitter.py`)
- `gpxpy`, `matplotlib`, and `contextily` Python packages (for map animation)
- [`ffmpeg`](https://ffmpeg.org/) available in your `PATH` when exporting video

## Installation
Clone or download this repository. Install the tools you need for the backend:

```bash
# Core dependency for gpx_splitter.py
brew install exiftool  # macOS
sudo apt-get update && sudo apt-get install -y libimage-exiftool-perl  # Ubuntu/Debian

# Map animation dependencies
pip install gpxpy matplotlib contextily
# ffmpeg is required to write MP4 output
brew install ffmpeg  # macOS
sudo apt-get install -y ffmpeg  # Ubuntu/Debian
```

## Backend usage
Run the splitter by providing the video file and the GPX file. Optionally set an output path.

```bash
python3 backend/src/gpx_helper/gpx_splitter.py /path/to/video.MP4 /path/to/track.gpx \
  -o /path/to/track.cropped.gpx
```

If `-o/--output` is omitted, the script writes to `<input>.cropped.gpx` next to the original GPX file.

## Backend API (foundation)
The backend now includes a FastAPI service that exposes endpoints for trimming GPX files by a known time window or by
matching a video file. Start the API from the repository root:

```bash
cd backend
poetry install
poetry run uvicorn gpx_helper.api.main:app --reload
```

Example requests:

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
  -F video_file=@/path/to/video.MP4 \
  --output trimmed.gpx
```

## Animate a GPX route on a map
`map_animator.py` turns a GPX track into an MP4 that draws the route over OpenStreetMap tiles. It converts coordinates to Web Mercator
(EPSG:3857) so they align with the basemap and hides chart axes for a clean map view.

Usage:

```bash
python3 backend/src/gpx_helper/map_animator.py route.gpx 45 1920x1080 -o route.mp4
```

- `route.gpx`: input GPX track
- `45`: duration in seconds
- `1920x1080`: output resolution (width x height)
- `-o route.mp4` (optional): output file name; defaults to `output.mp4`

The script fetches free OpenStreetMap tiles via `contextily` (no API key required) and writes MP4 video with `ffmpeg`.

### What `gpx_splitter.py` does
1. Reads creation and duration metadata from the video (UTC) using `exiftool`.
2. Parses the GPX track, finds the points closest to the video start and end times, and keeps only that segment.
3. Writes the cropped GPX file to the requested location.

### Example output
```
Video start (Local): 2025-11-02T17:02:23+00:00
Video end   (Local): 2025-11-02T17:07:00+00:00
Start time HH:MM:SS: 17:02:23
End time   HH:MM:SS: 17:07:00
Cropped GPX written to: /path/to/track.cropped.gpx
```

## Adjusting timestamps for split GoPro videos
If GoPro splits a recording into multiple files and their timestamps need correction, update the metadata (UTC) with `exiftool`:

```bash
exiftool -overwrite_original -P -api QuickTimeUTC=0 \
  -CreateDate="2025:11:29 18:42:49" \
  -ModifyDate="2025:11:29 18:42:49" \
  -MediaCreateDate="2025:11:29 18:42:49" \
  -MediaModifyDate="2025:11:29 18:42:49" \
  -TrackCreateDate="2025:11:29 18:42:49" \
  -TrackModifyDate="2025:11:29 18:42:49" \
  GX020427.MP4
```

## Troubleshooting
- **`exiftool` not found**: Ensure it is installed and available in your `PATH`.
- **Missing or incomplete metadata**: The script will fall back to the file's modification time and print a warning; verify your video metadata when accuracy matters.
- **No timestamps in GPX**: The crop requires GPX points with valid `<time>` elements that include timezone information (e.g., a trailing `Z` for UTC).

## Frontend landing page
The Svelte-based landing page lives in `frontend/`. To run it locally:

```bash
cd frontend
npm install
npm run dev
```

Then open the local Vite URL (default port 4173).

## Contributing
Feel free to open issues or submit pull requests with improvements or bug fixes.

## License
This repository is available for use without limitations.
