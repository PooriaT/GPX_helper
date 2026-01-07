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
import numpy as np
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
DEFAULT_FFMPEG_PRESET = os.environ.get("MAP_ANIM_FFMPEG_PRESET", "veryfast")
DEFAULT_TILE_SUBDOMAINS = tuple(
    sd for sd in os.environ.get("MAP_TILE_SUBDOMAINS", "").split(",") if sd
) or ("a", "b", "c")
TILE_PROVIDERS = {
    "osm": {
        "label": "OpenStreetMap (Standard)",
        "template": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "subdomains": (),
    },
    "cyclosm": {
        "label": "CyclOSM",
        "template": "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        "subdomains": ("a", "b", "c"),
    },
    "opentopomap": {
        "label": "OpenTopoMap",
        "template": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "subdomains": ("a", "b", "c"),
    },
}
TILE_REQUEST_TIMEOUT = float(os.environ.get("MAP_TILE_TIMEOUT_SECONDS", "10"))
TILE_USER_AGENT = os.environ.get(
    "MAP_TILE_USER_AGENT",
    "gpx-helper/0.1.0 (contact: pooria_taghdiri@hotmail.com)",
)
TILE_REFERER = os.environ.get("MAP_TILE_REFERER", "")
FFMPEG_PRESET_SPEED = {
    "ultrafast": 0.55,
    "superfast": 0.65,
    "veryfast": 0.75,
    "faster": 0.85,
    "fast": 0.95,
    "medium": 1.0,
    "slow": 1.15,
    "slower": 1.3,
    "veryslow": 1.5,
}


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_FFMPEG_CRF = _read_int_env("MAP_ANIM_FFMPEG_CRF", 23)
DEFAULT_FFMPEG_THREADS = _read_int_env("MAP_ANIM_FFMPEG_THREADS", 0)
DEFAULT_MAX_FRAMES = _read_int_env("MAP_ANIM_MAX_FRAMES", 2400)


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


def resolve_tile_provider(tile_type: str | None) -> tuple[str, tuple[str, ...]]:
    if not tile_type:
        return DEFAULT_TILE_URL_TEMPLATE, DEFAULT_TILE_SUBDOMAINS
    key = tile_type.lower()
    provider = TILE_PROVIDERS.get(key)
    if not provider:
        valid = ", ".join(sorted(TILE_PROVIDERS))
        raise ValueError(f"tile_type must be one of: {valid}")
    return provider["template"], provider["subdomains"]


def _normalize_ffmpeg_preset(preset: str) -> str:
    normalized = preset.strip().lower()
    return normalized if normalized in FFMPEG_PRESET_SPEED else "veryfast"


def _ffmpeg_extra_args(preset: str, crf: int, threads: int) -> list[str]:
    args = ["-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-threads", str(threads)]
    return args


def _ffmpeg_preset_speed_factor(preset: str) -> float:
    return FFMPEG_PRESET_SPEED.get(preset, FFMPEG_PRESET_SPEED["veryfast"])


def _resolve_effective_fps(duration_sec: float, fps: float) -> float:
    if duration_sec <= 0 or DEFAULT_MAX_FRAMES <= 0:
        return float(fps)
    max_fps = DEFAULT_MAX_FRAMES / duration_sec
    return min(float(fps), max_fps)


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
    *,
    tile_template: str | None = None,
    tile_subdomains: tuple[str, ...] | None = None,
) -> tuple["Image.Image", tuple[float, float, float, float]]:
    """
    Fetch and stitch map tiles for the given bounds.
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

    resolved_template = tile_template or DEFAULT_TILE_URL_TEMPLATE
    resolved_subdomains = (
        tile_subdomains if tile_subdomains is not None else DEFAULT_TILE_SUBDOMAINS
    )

    tile_index = 0
    for x in range(min_x_tile, max_x_tile + 1):
        for y in range(min_y_tile, max_y_tile + 1):
            tile_url = _format_tile_url(
                resolved_template, resolved_subdomains, tile_index, zoom, x, y
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
    xs: list[float],
    ys: list[float],
    duration_sec: float,
    fps: float = DEFAULT_FPS,
) -> tuple[list[int], int, float]:
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


def resample_route(
    xs: list[float], ys: list[float], target_points: int
) -> tuple[list[float], list[float]]:
    n_points = len(xs)
    if n_points <= target_points or n_points < 2 or target_points < 2:
        return xs, ys

    xs_arr = np.asarray(xs, dtype=float)
    ys_arr = np.asarray(ys, dtype=float)
    deltas = np.hypot(np.diff(xs_arr), np.diff(ys_arr))
    cumulative = np.concatenate(([0.0], np.cumsum(deltas)))
    unique_dist, unique_idx = np.unique(cumulative, return_index=True)

    total_dist = float(unique_dist[-1])
    if total_dist == 0.0:
        resampled_xs = np.full(target_points, xs_arr[0], dtype=float)
        resampled_ys = np.full(target_points, ys_arr[0], dtype=float)
        return resampled_xs.tolist(), resampled_ys.tolist()

    target_dist = np.linspace(0.0, total_dist, target_points)
    resampled_xs = np.interp(target_dist, unique_dist, xs_arr[unique_idx])
    resampled_ys = np.interp(target_dist, unique_dist, ys_arr[unique_idx])
    return resampled_xs.tolist(), resampled_ys.tolist()


def prepare_animation_series(
    xs: list[float],
    ys: list[float],
    duration_sec: float,
    fps: int = DEFAULT_FPS,
) -> tuple[list[float], list[float], list[int], int, int]:
    effective_fps = _resolve_effective_fps(duration_sec, fps)
    total_frames = max(int(duration_sec * effective_fps), 2)
    target_points = min(len(xs), total_frames)
    xs_resampled, ys_resampled = resample_route(xs, ys, target_points)
    frame_indices, total_frames, effective_fps = prepare_animation_data(
        xs_resampled, ys_resampled, duration_sec, fps=effective_fps
    )
    return xs_resampled, ys_resampled, frame_indices, total_frames, effective_fps


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
    marker_color: str = "#0ea5e9",
    animated_line_color: str = "#0ea5e9",
    full_line_color: str = "#111827",
    full_line_opacity: float = 0.8,
    line_width: float = 2.5,
    animated_line_opacity: float = 1.0,
    marker_size: float = 6.0,
    tile_template: str | None = None,
    tile_subdomains: tuple[str, ...] | None = None,
) -> None:
    """
    Create and save the animation as an MP4 file with a map tile basemap.
    """
    xs_arr = np.asarray(xs, dtype=float)
    ys_arr = np.asarray(ys, dtype=float)

    dpi = 100
    fig_width_in = width_px / dpi
    fig_height_in = height_px / dpi

    fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in), dpi=dpi)
    # Remove all padding/margins so the basemap fills the frame.
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])

    # Hide axis for a more "map-like" look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_axis_off()

    basemap_image, basemap_extent = fetch_basemap_image(
        min_lat,
        max_lat,
        min_lon,
        max_lon,
        width_px,
        height_px,
        tile_template=tile_template,
        tile_subdomains=tile_subdomains,
    )
    ax.imshow(basemap_image, extent=basemap_extent, origin="upper", aspect="auto")
    ax.set_xlim(basemap_extent[0], basemap_extent[1])
    ax.set_ylim(basemap_extent[2], basemap_extent[3])

    # Static full path
    full_line, = ax.plot(
        xs_arr,
        ys_arr,
        linewidth=max(line_width - 0.5, 0.5),
        alpha=max(0.0, min(full_line_opacity, 1.0)),
        color=full_line_color,
    )

    # Dynamic path up to current position
    animated_line, = ax.plot(
        [],
        [],
        linewidth=max(line_width, 0.5),
        color=animated_line_color,
        alpha=max(0.0, min(animated_line_opacity, 1.0)),
    )

    # Current position marker
    current_point, = ax.plot(
        [],
        [],
        marker="o",
        markersize=max(marker_size, 1.0),
        color=marker_color,
        markeredgecolor="white",
        markeredgewidth=0.8,
    )

    def init():
        animated_line.set_data(xs_arr[:0], ys_arr[:0])
        current_point.set_data([], [])
        return animated_line, current_point

    def update(frame):
        idx = frame_indices[frame]

        animated_line.set_data(xs_arr[: idx + 1], ys_arr[: idx + 1])
        current_point.set_data(xs_arr[idx : idx + 1], ys_arr[idx : idx + 1])

        return animated_line, current_point

    anim = FuncAnimation(
        fig,
        update,
        init_func=init,
        frames=total_frames,
        interval=1000 / fps,
        blit=True,
        cache_frame_data=False,
    )

    preset = _normalize_ffmpeg_preset(DEFAULT_FFMPEG_PRESET)
    extra_args = _ffmpeg_extra_args(preset, DEFAULT_FFMPEG_CRF, DEFAULT_FFMPEG_THREADS)
    writer = FFMpegWriter(fps=fps, codec="libx264", extra_args=extra_args)
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
    xs, ys, _, total_frames, fps = prepare_animation_series(xs, ys, duration_sec, fps=fps)
    n_points = len(xs)
    preset = _normalize_ffmpeg_preset(DEFAULT_FFMPEG_PRESET)
    preset_factor = _ffmpeg_preset_speed_factor(preset)

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
    path_factor = 1.0 + min(n_points / 6000, 0.75)

    tile_seconds = tiles_needed * 0.4  # conservative per-tile cost
    render_seconds = max(total_frames * 0.02 * resolution_factor * path_factor, 0.5)
    encode_seconds = max(
        total_frames * 0.0045 * resolution_factor * preset_factor,
        0.5,
    )
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

    xs, ys, frame_indices, total_frames, fps = prepare_animation_series(
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
