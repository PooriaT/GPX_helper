#!/usr/bin/env python3
"""
Create an animated MP4 of a GPX route overlaid on OpenStreetMap tiles.

Usage:
    python3 map_animator.py route.gpx 45 1920x1080 -o route.mp4

Requirements:
    pip install gpxpy matplotlib pillow
    ffmpeg (for MP4 encoding)
"""

from __future__ import annotations

import argparse
import math
import os
from functools import lru_cache
from typing import Iterable, TYPE_CHECKING

import gpxpy
import gpxpy.gpx
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter

if TYPE_CHECKING:
    from PIL import Image

EARTH_RADIUS_METERS = 6_378_137.0
MAX_MERCATOR_LAT = 85.05112878
DEFAULT_FPS = 30
DEFAULT_TILE_URL_TEMPLATE = os.environ.get(
    "MAP_TILE_URL_TEMPLATE",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
DEFAULT_TILE_SUBDOMAINS = tuple(
    sd for sd in os.environ.get("MAP_TILE_SUBDOMAINS", "").split(",") if sd
) or ("a", "b", "c")
TILE_REQUEST_TIMEOUT = float(os.environ.get("MAP_TILE_TIMEOUT_SECONDS", "10"))
TILE_USER_AGENT = os.environ.get(
    "MAP_TILE_USER_AGENT",
    "gpx-helper/0.1.0 (contact: pooria_taghdiri@hotmail.com)",
)
TILE_REFERER = os.environ.get("MAP_TILE_REFERER", "")


def _compute_tile_range(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    width_px: int,
    height_px: int,
    *,
    max_zoom: int = 18,
) -> tuple[int, tuple[int, int, int, int]]:
    """
    Determine the zoom level and tile bounds that cover the requested area.
    """
    zoom = choose_zoom_for_bounds(
        min_lat, max_lat, min_lon, max_lon, width_px, height_px, max_zoom=max_zoom
    )
    min_x_tile, min_y_tile = lonlat_to_tile(min_lon, max_lat, zoom)
    max_x_tile, max_y_tile = lonlat_to_tile(max_lon, min_lat, zoom)

    max_tile_index = 2 ** zoom - 1
    min_x_tile = max(0, min(min_x_tile, max_tile_index))
    max_x_tile = max(0, min(max_x_tile, max_tile_index))
    min_y_tile = max(0, min(min_y_tile, max_tile_index))
    max_y_tile = max(0, min(max_y_tile, max_tile_index))
    return zoom, (min_x_tile, max_x_tile, min_y_tile, max_y_tile)


def _format_tile_url(
    template: str, subdomains: tuple[str, ...], tile_index: int, zoom: int, x: int, y: int
) -> str:
    format_kwargs = {"z": zoom, "x": x, "y": y}
    if "{s}" in template:
        # Cycle across provided subdomains if the template expects one.
        resolved_subdomains = subdomains or ("a", "b", "c")
        format_kwargs["s"] = resolved_subdomains[tile_index % len(resolved_subdomains)]
    return template.format(**format_kwargs)


@lru_cache(maxsize=256)
def _download_tile(tile_url: str) -> bytes:
    from urllib import request

    headers = {"User-Agent": TILE_USER_AGENT}
    if TILE_REFERER:
        headers["Referer"] = TILE_REFERER

    req = request.Request(tile_url, headers=headers)
    with request.urlopen(req, timeout=TILE_REQUEST_TIMEOUT) as response:
        return response.read()


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


def latlon_to_web_mercator_point(lat: float, lon: float) -> tuple[float, float]:
    """
    Convert a single WGS84 lat/lon to Web Mercator x/y.
    """
    x, y = latlon_to_web_mercator([lat], [lon])
    return x[0], y[0]


def lonlat_to_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    """
    Convert lon/lat to pixel coordinates at a given zoom level.
    """
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n * 256.0
    y = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n * 256.0
    return x, y


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    """
    Convert lon/lat to tile x/y at a given zoom level.
    """
    x, y = lonlat_to_pixel(lon, lat, zoom)
    return int(x // 256), int(y // 256)


def tile_xy_to_lonlat(x: int, y: int, zoom: int) -> tuple[float, float]:
    """
    Convert tile x/y at a given zoom to lon/lat for the tile's NW corner.
    """
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lon, lat


def choose_zoom_for_bounds(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    width_px: int,
    height_px: int,
    *,
    max_zoom: int = 18,
) -> int:
    """
    Pick the highest zoom that fits the bounds within the target resolution.
    """
    for zoom in range(max_zoom, -1, -1):
        x_min, y_max = lonlat_to_pixel(min_lon, max_lat, zoom)
        x_max, y_min = lonlat_to_pixel(max_lon, min_lat, zoom)
        if abs(x_max - x_min) <= width_px and abs(y_max - y_min) <= height_px:
            return zoom
    return 0


def fetch_basemap_image(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    width_px: int,
    height_px: int,
) -> tuple["Image.Image", tuple[float, float, float, float]]:
    """
    Fetch and stitch OpenStreetMap tiles for the given bounds.
    Returns a PIL image and its extent in Web Mercator coordinates.
    """
    from PIL import Image
    from io import BytesIO

    zoom, (min_x_tile, max_x_tile, min_y_tile, max_y_tile) = _compute_tile_range(
        min_lat, max_lat, min_lon, max_lon, width_px, height_px
    )

    tiles_wide = max_x_tile - min_x_tile + 1
    tiles_high = max_y_tile - min_y_tile + 1
    stitched = Image.new("RGB", (tiles_wide * 256, tiles_high * 256))

    tile_index = 0
    for x in range(min_x_tile, max_x_tile + 1):
        for y in range(min_y_tile, max_y_tile + 1):
            tile_url = _format_tile_url(
                DEFAULT_TILE_URL_TEMPLATE, DEFAULT_TILE_SUBDOMAINS, tile_index, zoom, x, y
            )
            tile_index += 1
            try:
                tile_data = _download_tile(tile_url)
                tile_image = Image.open(BytesIO(tile_data)).convert("RGB")
            except Exception:
                tile_image = Image.new("RGB", (256, 256), color=(230, 230, 230))
            x_offset = (x - min_x_tile) * 256
            y_offset = (y - min_y_tile) * 256
            stitched.paste(tile_image, (x_offset, y_offset))

    west_lon, north_lat = tile_xy_to_lonlat(min_x_tile, min_y_tile, zoom)
    east_lon, south_lat = tile_xy_to_lonlat(max_x_tile + 1, max_y_tile + 1, zoom)
    min_x_merc, max_y_merc = latlon_to_web_mercator_point(north_lat, west_lon)
    max_x_merc, min_y_merc = latlon_to_web_mercator_point(south_lat, east_lon)

    extent = (min_x_merc, max_x_merc, min_y_merc, max_y_merc)
    return stitched, extent


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
    *,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> None:
    """
    Create and save the animation as an MP4 file with OpenStreetMap basemap.
    """

    dpi = 100
    fig_width_in = width_px / dpi
    fig_height_in = height_px / dpi

    fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in), dpi=dpi)
    # Remove all padding/margins so the basemap fills the frame.
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])

    # Bounds in Web Mercator
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Hide axis for a more "map-like" look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_axis_off()

    basemap_image, basemap_extent = fetch_basemap_image(
        min_lat, max_lat, min_lon, max_lon, width_px, height_px
    )
    ax.imshow(basemap_image, extent=basemap_extent, origin="upper", aspect="auto")
    ax.set_xlim(basemap_extent[0], basemap_extent[1])
    ax.set_ylim(basemap_extent[2], basemap_extent[3])

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


def estimate_animation_seconds(
    lats: list[float],
    lons: list[float],
    width_px: int,
    height_px: int,
    duration_sec: float,
    fps: int = DEFAULT_FPS,
) -> float:
    """
    Provide a rough wall-clock estimate for rendering an animation.
    Factors in tile downloads and frame rendering work.
    """
    xs, ys = latlon_to_web_mercator(lats, lons)
    _, total_frames, _ = prepare_animation_data(xs, ys, duration_sec, fps=fps)

    zoom, (min_x_tile, max_x_tile, min_y_tile, max_y_tile) = _compute_tile_range(
        min(lats),
        max(lats),
        min(lons),
        max(lons),
        width_px,
        height_px,
    )
    tiles_needed = (max_x_tile - min_x_tile + 1) * (max_y_tile - min_y_tile + 1)

    # Scale render/encode cost by resolution with a 720p baseline.
    resolution_factor = max(0.5, min((width_px * height_px) / (1280 * 720), 8.0))

    tile_seconds = tiles_needed * 0.35  # slightly conservative per-tile cost
    render_seconds = max(total_frames * 0.015 * resolution_factor, 0.5)
    encode_seconds = duration_sec * 0.05 * resolution_factor
    overhead_seconds = 1.5  # setup/IO overhead

    estimate = overhead_seconds + tile_seconds + render_seconds + encode_seconds
    # Keep ETA bounded to avoid extreme values on odd inputs
    return max(2.0, min(estimate, 600.0))


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
        min_lat=min(lats),
        max_lat=max(lats),
        min_lon=min(lons),
        max_lon=max(lons),
    )


if __name__ == "__main__":
    main()
