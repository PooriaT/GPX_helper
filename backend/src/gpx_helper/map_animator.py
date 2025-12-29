#!/usr/bin/env python3
"""
Create an animated MP4 of a GPX route overlaid on OpenStreetMap tiles.

Usage:
    python3 map_animator.py route.gpx 45 1920x1080 -o route.mp4

Requirements:
    pip install gpxpy matplotlib contextily
    ffmpeg (for MP4 encoding)
"""

import argparse
import math
import os
from typing import Iterable

import gpxpy
import gpxpy.gpx
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
import contextily as cx

EARTH_RADIUS_METERS = 6_378_137.0
MAX_MERCATOR_LAT = 85.05112878
DEFAULT_FPS = 30


def parse_resolution(res_str: str) -> tuple[int, int]:
    """
    Parse resolution string like '1920x1080' or '1920,1080'.
    """
    res_str = res_str.lower().replace(" ", "")
    for sep in ("x", ",", "×"):
        if sep in res_str:
            w_str, h_str = res_str.split(sep, 1)
            return int(w_str), int(h_str)
    raise ValueError(f"Could not parse resolution: {res_str}")


def load_gpx_points(gpx_path: str) -> tuple[list[float], list[float]]:
    """
    Load GPX and return lists of latitudes and longitudes.
    """
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    if not gpx.tracks:
        raise ValueError("No <trk> found in GPX file")

    track = gpx.tracks[0]
    if not track.segments:
        raise ValueError("No <trkseg> found")

    segment = track.segments[0]
    if not segment.points:
        raise ValueError("No <trkpt> points found")

    lats = [p.latitude for p in segment.points]
    lons = [p.longitude for p in segment.points]
    return lats, lons


def latlon_to_web_mercator(lats: Iterable[float], lons: Iterable[float]) -> tuple[list[float], list[float]]:
    """
    Convert WGS84 lat/lon (degrees) to Web Mercator (EPSG:3857) x/y (meters).
    """
    xs: list[float] = []
    ys: list[float] = []
    for lat, lon in zip(lats, lons):
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        x = EARTH_RADIUS_METERS * lon_rad
        # Clamp latitude for Mercator projection
        lat_rad = max(
            min(lat_rad, math.radians(MAX_MERCATOR_LAT)),
            math.radians(-MAX_MERCATOR_LAT),
        )
        y = EARTH_RADIUS_METERS * math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
        xs.append(x)
        ys.append(y)
    return xs, ys


def prepare_animation_data(
    xs: list[float], ys: list[float], duration_sec: float, fps: int = DEFAULT_FPS
) -> tuple[list[int], int, int]:
    """
    Prepare per-frame indices along the route.
    """
    n_points = len(xs)
    if n_points < 2:
        raise ValueError("Need at least 2 points to animate")

    total_frames = int(duration_sec * fps)
    if total_frames < 2:
        total_frames = 2

    frame_indices = []
    for frame in range(total_frames):
        t = frame / (total_frames - 1)
        idx_float = t * (n_points - 1)
        idx = int(round(idx_float))
        idx = max(0, min(n_points - 1, idx))
        frame_indices.append(idx)

    return frame_indices, total_frames, fps


def create_animation(
    xs: list[float],
    ys: list[float],
    frame_indices: list[int],
    total_frames: int,
    fps: int,
    width_px: int,
    height_px: int,
    output_path: str,
) -> None:
    """
    Create and save the animation as an MP4 file with OpenStreetMap basemap.
    """

    dpi = 100
    fig_width_in = width_px / dpi
    fig_height_in = height_px / dpi

    fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in), dpi=dpi)

    # Bounds in Web Mercator
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    x_pad = (max_x - min_x) * 0.05 or 10
    y_pad = (max_y - min_y) * 0.05 or 10

    ax.set_xlim(min_x - x_pad, max_x + x_pad)
    ax.set_ylim(min_y - y_pad, max_y + y_pad)

    # Hide axis for a more "map-like" look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_axis_off()

    # Add OpenStreetMap basemap
    # CRS = EPSG:3857 (Web Mercator)
    cx.add_basemap(
        ax,
        crs="EPSG:3857",
        source=cx.providers.OpenStreetMap.Mapnik,  # standard OSM tiles
    )

    # Static full path
    full_line, = ax.plot(xs, ys, linewidth=1.5, alpha=0.8)

    # Dynamic path up to current position
    animated_line, = ax.plot([], [], linewidth=2.5)

    # Current position marker
    current_point, = ax.plot([], [], marker="o", markersize=6)

    def init():
        animated_line.set_data([], [])
        current_point.set_data([], [])
        return animated_line, current_point

    def update(frame):
        idx = frame_indices[frame]

        animated_line.set_data(xs[:idx + 1], ys[:idx + 1])
        current_point.set_data([xs[idx]], [ys[idx]])

        return animated_line, current_point

    anim = FuncAnimation(
        fig,
        update,
        init_func=init,
        frames=total_frames,
        interval=1000 / fps,
        blit=True,
    )

    writer = FFMpegWriter(fps=fps, bitrate=3000)
    print(f"Saving video to {output_path} ...")
    anim.save(output_path, writer=writer)
    plt.close(fig)
    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a GPX file into an animated route MP4 on a real map (OpenStreetMap)."
    )
    parser.add_argument("gpx", help="Input GPX file")
    parser.add_argument("duration", type=float, help="Duration in seconds")
    parser.add_argument("resolution", help="Resolution, e.g. 1920x1080")
    parser.add_argument(
        "-o",
        "--output",
        default="output.mp4",
        help="Output video file (default: output.mp4)",
    )

    args = parser.parse_args()

    gpx_path = args.gpx
    if not os.path.isfile(gpx_path):
        print(f"Error: GPX file not found: {gpx_path}")
        return

    width_px, height_px = parse_resolution(args.resolution)

    print("Loading GPX...")
    lats, lons = load_gpx_points(gpx_path)
    print(f"Found {len(lats)} track points.")

    print("Converting lat/lon to Web Mercator (EPSG:3857)...")
    xs, ys = latlon_to_web_mercator(lats, lons)

    frame_indices, total_frames, fps = prepare_animation_data(
        xs, ys, args.duration, fps=DEFAULT_FPS
    )

    create_animation(
        xs,
        ys,
        frame_indices,
        total_frames,
        fps,
        width_px,
        height_px,
        args.output,
    )


if __name__ == "__main__":
    main()
