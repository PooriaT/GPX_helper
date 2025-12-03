# GPX_helper

Utilities for aligning GoPro (or other camera) video timestamps with GPX tracks. The primary tool, `gpx_splitter.py`, crops a GPX track to match a video clip so you can sync footage and GPS data for mapping or overlays.

## Features
- Extracts video start time and duration from EXIF metadata via `exiftool`.
- Matches GPX track points closest to the video start/end times and writes a cropped GPX.
- Falls back to file modification time when metadata is missing, with clear warnings.
- Works with GPX files that include timezone-aware timestamps (UTC recommended).

## Requirements
- Python 3.8+
- [`exiftool`](https://exiftool.org/) available in your `PATH`

## Installation
No package installation is required. Clone or download this repository and ensure `exiftool` is installed and on your `PATH`.

```bash
# Install exiftool on macOS (Homebrew)
brew install exiftool

# Install exiftool on Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y libimage-exiftool-perl
```

## Usage
Run the splitter by providing the video file and the GPX file. Optionally set an output path.

```bash
python3 gpx_splitter.py /path/to/video.MP4 /path/to/track.gpx \
  -o /path/to/track.cropped.gpx
```

If `-o/--output` is omitted, the script writes to `<input>.cropped.gpx` next to the original GPX file.

### What the script does
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

## Contributing
Feel free to open issues or submit pull requests with improvements or bug fixes.

## License
This repository does not currently specify a license. Please contact the author before reuse.
