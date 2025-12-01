#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import re
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

GPX_NS = "http://www.topografix.com/GPX/1/1"
NSMAP = {"gpx": GPX_NS}

ET.register_namespace("", GPX_NS)
ET.register_namespace("gpxtpx", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")
ET.register_namespace("gpxx", "http://www.garmin.com/xmlschemas/GpxExtensions/v3")

def run_exiftool(video_path, tags):
    """
    Run exiftool on video_path and return a dict {tag: value_string}.
    tags: list like ["CreateDate", "MediaCreateDate", "Duration", ...]
    """
    cmd = ["exiftool", "-api", "QuickTimeUTC=1"]
    for tag in tags:
        cmd.append(f"-{tag}")
    cmd.append(video_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print("ERROR: exiftool not found in PATH", file=sys.stderr)
        return {}
    except subprocess.CalledProcessError as e:
        print("ERROR running exiftool:", e.stderr, file=sys.stderr)
        return {}

    info = {}
    for line in result.stdout.splitlines():
        # Example line: "CreateDate                      : 2025:11:02 17:02:23"
        if ":" not in line:
            continue
        parts = line.split(":", 1)
        tag_name = parts[0].strip().replace(" ", "")
        value = parts[1].strip()
        if value:
            info[tag_name] = value
    return info


def parse_exif_datetime(dt_str):
    """
    Parse exiftool datetime like "2025:11:02 17:02:23"
    Assume it is already UTC because of QuickTimeUTC=1.
    """
    try:
        # Handle datetime strings with or without timezone offset
        if dt_str[-6] in ('+', '-'):
            return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S%z")
        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        raise


def parse_exif_duration(d_str):
    """
    Parse exiftool duration like "0:04:34" or "0:04:34 (approx)".
    Return a timedelta.
    """
    # Remove " (approx)" or similar
    d_str = d_str.split(" ", 1)[0]
    m = re.match(r"(\d+):(\d+):(\d+(?:\.\d*)?)", d_str)
    if not m:
        raise ValueError(f"Cannot parse duration '{d_str}'")
    hours = int(m.group(1))
    minutes = int(m.group(2))
    seconds = float(m.group(3))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def get_video_times(video_path):
    """
    Return (start_dt_utc, end_dt_utc) as aware datetimes in UTC.

    Primary method: exiftool.
    Fallback: file modification time via os.stat (assumed local time).
    """
    tags = ["MediaCreateDate", "CreateDate", "MediaModifyDate", "ModifyDate",
            "MediaDuration", "Duration", "PlayDuration"]
    info = run_exiftool(video_path, tags)

    start_dt = None
    duration_td = None

    # Choose start time tag by preference
    for key in ("MediaCreateDate", "CreateDate", "MediaModifyDate", "ModifyDate"):
        if key in info:
            start_dt = parse_exif_datetime(info[key])
            break

    # Choose duration tag by preference
    for key in ("MediaDuration", "Duration", "PlayDuration"):
        if key in info:
            try:
                duration_td = parse_exif_duration(info[key])
                break
            except ValueError:
                continue

    if start_dt is None or duration_td is None:
        # Fallback: use file modification time and try duration 0
        st = os.stat(video_path)
        # Use local time then convert to UTC
        local_dt = datetime.fromtimestamp(st.st_mtime)
        start_dt = local_dt.astimezone(timezone.utc)
        duration_td = duration_td or timedelta(seconds=0)
        print(
            "WARNING: Using file modification time as fallback. "
            "Check exiftool installation and metadata.",
            file=sys.stderr,
        )

    end_dt = start_dt + duration_td

    return start_dt, end_dt


def parse_gpx_time(time_text):
    """
    Parse GPX time element content like "2025-11-02T17:02:23.000Z" to aware UTC datetime.
    """
    if time_text.endswith("Z"):
        time_text = time_text.replace("Z", "+00:00")
    # fromisoformat handles fractional seconds and offset
    return datetime.fromisoformat(time_text).astimezone(timezone.utc)


def crop_gpx_by_time(gpx_path, start_dt, end_dt, output_path):
    """
    Read GPX, crop <trkseg> to closest points between start_dt and end_dt.
    Save to output_path.
    """
    tree = ET.parse(gpx_path)
    root = tree.getroot()

    # Find first trkseg
    trkseg = root.find(".//{%s}trkseg" % GPX_NS)
    if trkseg is None:
        raise RuntimeError("No <trkseg> element found in GPX")

    trkpts = list(trkseg.findall("{%s}trkpt" % GPX_NS))
    if not trkpts:
        raise RuntimeError("No <trkpt> elements found in <trkseg>")

    # Collect times
    times = []
    for pt in trkpts:
        time_el = pt.find("{%s}time" % GPX_NS)
        if time_el is None or not time_el.text:
            times.append(None)
            continue
        try:
            dt = parse_gpx_time(time_el.text.strip())
        except Exception:
            dt = None
        times.append(dt)

    # Filter indices that have valid times
    valid_indices = [i for i, t in enumerate(times) if t is not None]
    if not valid_indices:
        raise RuntimeError("No valid <time> elements in GPX track points")

    def closest_index(target_dt):
        best_i = None
        best_diff = None
        for i in valid_indices:
            diff = abs(times[i] - target_dt)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_i = i
        return best_i

    idx_start = closest_index(start_dt)
    idx_end = closest_index(end_dt)

    if idx_start is None or idx_end is None:
        raise RuntimeError("Could not find closest points in GPX")

    if idx_start > idx_end:
        idx_start, idx_end = idx_end, idx_start

    cropped_pts = trkpts[idx_start : idx_end + 1]

    if not cropped_pts:
        raise RuntimeError("No points selected after cropping")

    # Replace trkseg contents with cropped points
    for child in list(trkseg):
        trkseg.remove(child)
    for pt in cropped_pts:
        trkseg.append(pt)

    # Write result
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)


def format_hms(dt):
    """
    Return "HH:MM:SS" for a UTC datetime.
    """
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(
        description="Crop a GPX file based on a GoPro (or other) video timing."
    )
    parser.add_argument("video", help="Path to the video file (e.g. GX010415.MP4)")
    parser.add_argument("gpx", help="Path to the GPX file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output GPX file path (default: input_gpx_name.cropped.gpx)",
    )
    args = parser.parse_args()

    video_path = args.video
    gpx_path = args.gpx

    if not os.path.isfile(video_path):
        print(f"Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(gpx_path):
        print(f"GPX file not found: {gpx_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(gpx_path)
        output_path = base + ".cropped" + ext

    start_dt, end_dt = get_video_times(video_path)

    print("Video start (Local):", start_dt.isoformat())
    print("Video end   (Local):", end_dt.isoformat())
    print("Start time HH:MM:SS:", format_hms(start_dt))
    print("End time   HH:MM:SS:", format_hms(end_dt))

    crop_gpx_by_time(gpx_path, start_dt, end_dt, output_path)

    print(f"Cropped GPX written to: {output_path}")


if __name__ == "__main__":
    main()
