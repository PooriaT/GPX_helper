# GPX_helper

Scripts to align GoPro (or other camera) video times with GPX tracks.

## gpx_splitter.py
`gpx_splitter.py` crops a GPX track to match the start and end time of a video file using `exiftool` metadata.

### Requirements
- Python 3
- [`exiftool`](https://exiftool.org/) available in your `PATH`

### Usage
```bash
python3 gpx_splitter.py /path/to/video.MP4 /path/to/track.gpx -o /path/to/track.cropped.gpx
```

The script:
1. Reads creation and duration metadata from the video (UTC) via `exiftool`.
2. Parses the GPX track and finds the points closest to the video start and end times.
3. Writes a new GPX file containing only the cropped segment.

If `-o/--output` is not provided, the output file defaults to `<input>.cropped.gpx`.

Example output from a run:
```
Video start (Local): 2025-11-02T17:02:23+00:00
Video end   (Local): 2025-11-02T17:07:00+00:00
Start time HH:MM:SS: 17:02:23
End time   HH:MM:SS: 17:07:00
Cropped GPX written to: /path/to/track.cropped.gpx
```

### Notes
- If `exiftool` is missing or the metadata is incomplete, the script falls back to the file's modification time and may print a warning.
- GPX timestamps should include timezone information (e.g., `Z` suffix for UTC) for accurate matching.

## Adjusting timestamps for split GoPro videos
If GoPro splits a recording into multiple files and their timestamps need correction, you can update the metadata (UTC) with `exiftool`:
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
