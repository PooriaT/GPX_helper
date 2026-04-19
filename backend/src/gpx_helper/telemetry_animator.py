from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Iterable
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont

from gpx_helper.map_animator import DEFAULT_FPS

EARTH_RADIUS_METERS = 6_371_000.0
DEFAULT_MAX_FRAMES = 2_400
DEFAULT_BACKGROUND_COLOR = "transparent"
DEFAULT_TELEMETRY_TYPE = "elevation_value"
TELEMETRY_TYPES = {
    "elevation_value": "Elevation value",
    "speed": "Speed",
    "heart_rate": "Heart rate",
    "elevation_graph": "Elevation graph",
}


@dataclass(frozen=True)
class TelemetryPoint:
    elapsed_seconds: float
    elevation_meters: float | None
    speed_mps: float | None
    heart_rate_bpm: float | None


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_heart_rate(track_point: ET.Element) -> float | None:
    for descendant in track_point.iter():
        if _strip_namespace(descendant.tag).lower() in {"hr", "heartrate", "heart_rate"}:
            heart_rate = _parse_float(descendant.text)
            if heart_rate is not None:
                return heart_rate
    return None


def _haversine_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(1.0 - a, 0.0)))
    return EARTH_RADIUS_METERS * c


def _resolve_effective_fps(duration_seconds: float, fps: float) -> float:
    if duration_seconds <= 0 or DEFAULT_MAX_FRAMES <= 0:
        return float(fps)
    return min(float(fps), DEFAULT_MAX_FRAMES / duration_seconds)


def resolve_telemetry_type(telemetry_type: str) -> str:
    normalized = telemetry_type.strip().lower()
    if normalized not in TELEMETRY_TYPES:
        valid = ", ".join(sorted(TELEMETRY_TYPES))
        raise ValueError(f"telemetry_type must be one of: {valid}")
    return normalized


def telemetry_label(telemetry_type: str) -> str:
    return TELEMETRY_TYPES[resolve_telemetry_type(telemetry_type)]


def parse_background_color(background_color: str | None) -> tuple[int, int, int, int]:
    if background_color is None:
        return (0, 0, 0, 0)
    normalized = background_color.strip().lower()
    if not normalized or normalized == "transparent":
        return (0, 0, 0, 0)
    rgb = ImageColor.getrgb(normalized)
    return rgb[0], rgb[1], rgb[2], 255


def load_gpx_telemetry(gpx_path: str) -> list[TelemetryPoint]:
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    track_points = [node for node in root.iter() if _strip_namespace(node.tag) == "trkpt"]
    if len(track_points) < 2:
        raise ValueError("Need at least 2 GPX track points.")

    parsed_points: list[tuple[float, float, datetime, float | None, float | None]] = []
    for track_point in track_points:
        lat = _parse_float(track_point.attrib.get("lat"))
        lon = _parse_float(track_point.attrib.get("lon"))
        timestamp = _parse_timestamp(
            next(
                (
                    child.text
                    for child in track_point
                    if _strip_namespace(child.tag) == "time"
                ),
                None,
            )
        )
        if lat is None or lon is None or timestamp is None:
            continue

        elevation = next(
            (
                _parse_float(child.text)
                for child in track_point
                if _strip_namespace(child.tag) == "ele"
            ),
            None,
        )
        heart_rate = _find_heart_rate(track_point)
        parsed_points.append((lat, lon, timestamp, elevation, heart_rate))

    if len(parsed_points) < 2:
        raise ValueError("GPX file must contain at least 2 timed track points.")

    start_time = parsed_points[0][2]
    telemetry: list[TelemetryPoint] = []
    previous_lat, previous_lon, previous_time, *_ = parsed_points[0]
    previous_speed = 0.0

    for index, (lat, lon, timestamp, elevation, heart_rate) in enumerate(parsed_points):
        elapsed_seconds = max((timestamp - start_time).total_seconds(), 0.0)
        speed_mps = None
        if index == 0:
            speed_mps = 0.0
        else:
            delta_seconds = (timestamp - previous_time).total_seconds()
            if delta_seconds > 0:
                speed_mps = _haversine_meters(previous_lat, previous_lon, lat, lon) / delta_seconds
                previous_speed = speed_mps
            else:
                speed_mps = previous_speed

        telemetry.append(
            TelemetryPoint(
                elapsed_seconds=elapsed_seconds,
                elevation_meters=elevation,
                speed_mps=speed_mps,
                heart_rate_bpm=heart_rate,
            )
        )
        previous_lat = lat
        previous_lon = lon
        previous_time = timestamp

    if telemetry[-1].elapsed_seconds <= 0:
        raise ValueError("GPX timestamps must span more than zero seconds.")

    return telemetry


def telemetry_duration_seconds(points: list[TelemetryPoint]) -> float:
    if not points:
        raise ValueError("Telemetry points are required.")
    duration = points[-1].elapsed_seconds
    if duration <= 0:
        raise ValueError("Telemetry duration must be positive.")
    return duration


def ensure_telemetry_type_supported(
    points: list[TelemetryPoint],
    telemetry_type: str,
) -> None:
    resolved_type = resolve_telemetry_type(telemetry_type)
    if resolved_type in {"elevation_value", "elevation_graph"} and not any(
        point.elevation_meters is not None for point in points
    ):
        raise ValueError("The GPX file does not contain elevation data.")
    if resolved_type == "heart_rate" and not any(point.heart_rate_bpm is not None for point in points):
        raise ValueError("The GPX file does not contain heart rate data.")


def estimate_telemetry_seconds(
    duration_seconds: float,
    width_px: int,
    height_px: int,
    fps: float = DEFAULT_FPS,
) -> float:
    effective_fps = _resolve_effective_fps(duration_seconds, fps)
    total_frames = max(int(duration_seconds * effective_fps), 2)
    resolution_factor = max(0.4, min((width_px * height_px) / (1280 * 720), 6.0))
    render_seconds = max(total_frames * 0.005 * resolution_factor, 0.3)
    encode_seconds = max(total_frames * 0.0035 * resolution_factor, 0.3)
    return max(1.0, min(1.0 + render_seconds + encode_seconds, 180.0))


def _build_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_text_block(
    image: Image.Image,
    *,
    label: str,
    value: str,
    unit: str = "",
    accent_color: tuple[int, int, int, int],
    text_color: tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    width_px, height_px = image.size
    label_font = _build_font(max(18, int(height_px * 0.045)))
    value_font = _build_font(max(42, int(height_px * 0.14)))
    unit_font = _build_font(max(18, int(height_px * 0.045)))

    label_y = int(height_px * 0.22)
    value_y = int(height_px * 0.5)

    draw.text(
        (width_px / 2, label_y),
        label.upper(),
        font=label_font,
        fill=accent_color,
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 190),
    )
    draw.text(
        (width_px / 2, value_y),
        value,
        font=value_font,
        fill=text_color,
        anchor="mm",
        stroke_width=3,
        stroke_fill=(0, 0, 0, 210),
    )
    if unit:
        draw.text(
            (width_px / 2, int(height_px * 0.67)),
            unit,
            font=unit_font,
            fill=text_color,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 210),
        )


def _chart_bounds(values: Iterable[float]) -> tuple[float, float]:
    values_list = list(values)
    min_value = min(values_list)
    max_value = max(values_list)
    if math.isclose(min_value, max_value):
        padding = max(abs(min_value) * 0.05, 5.0)
        return min_value - padding, max_value + padding
    padding = (max_value - min_value) * 0.08
    return min_value - padding, max_value + padding


def _project_graph_points(
    times: np.ndarray,
    values: np.ndarray,
    *,
    width_px: int,
    height_px: int,
    padding_x: float,
    padding_y: float,
) -> list[tuple[float, float]]:
    min_value, max_value = _chart_bounds(values.tolist())
    usable_width = max(width_px - padding_x * 2, 1.0)
    usable_height = max(height_px - padding_y * 2, 1.0)
    total_time = max(float(times[-1]), 1e-9)
    points: list[tuple[float, float]] = []
    for time_value, metric_value in zip(times, values):
        x = padding_x + (float(time_value) / total_time) * usable_width
        y_progress = (float(metric_value) - min_value) / max(max_value - min_value, 1e-9)
        y = height_px - padding_y - y_progress * usable_height
        points.append((x, y))
    return points


def _render_elevation_graph(
    image: Image.Image,
    *,
    times: np.ndarray,
    elevations: np.ndarray,
    current_elapsed: float,
    current_value: float,
    accent_color: tuple[int, int, int, int],
    text_color: tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    width_px, height_px = image.size
    padding_x = width_px * 0.08
    padding_y = height_px * 0.14
    chart_points = _project_graph_points(
        times,
        elevations,
        width_px=width_px,
        height_px=height_px,
        padding_x=padding_x,
        padding_y=padding_y,
    )
    if len(chart_points) >= 2:
        draw.line(chart_points, fill=accent_color, width=max(2, int(height_px * 0.008)))

    total_time = max(float(times[-1]), 1e-9)
    current_x = padding_x + (current_elapsed / total_time) * max(width_px - padding_x * 2, 1.0)
    closest_index = int(np.searchsorted(times, current_elapsed, side="left"))
    closest_index = min(max(closest_index, 0), len(chart_points) - 1)
    marker_x, marker_y = chart_points[closest_index]
    draw.line(
        [(current_x, padding_y * 0.65), (current_x, height_px - padding_y * 0.65)],
        fill=(255, 255, 255, 90),
        width=1,
    )
    radius = max(5, int(height_px * 0.012))
    draw.ellipse(
        [(marker_x - radius, marker_y - radius), (marker_x + radius, marker_y + radius)],
        fill=accent_color,
        outline=(255, 255, 255, 255),
        width=max(1, int(height_px * 0.0035)),
    )

    title_font = _build_font(max(18, int(height_px * 0.04)))
    value_font = _build_font(max(22, int(height_px * 0.055)))
    draw.text(
        (padding_x, padding_y * 0.45),
        "ELEVATION",
        font=title_font,
        fill=accent_color,
        anchor="la",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 170),
    )
    draw.text(
        (padding_x, height_px - padding_y * 0.25),
        f"{current_value:.0f} m",
        font=value_font,
        fill=text_color,
        anchor="ld",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 190),
    )


def _metric_series(
    points: list[TelemetryPoint],
    telemetry_type: str,
) -> tuple[np.ndarray, np.ndarray]:
    resolved_type = resolve_telemetry_type(telemetry_type)
    if resolved_type == "elevation_value" or resolved_type == "elevation_graph":
        values = [point.elevation_meters for point in points]
    elif resolved_type == "speed":
        values = [point.speed_mps for point in points]
    else:
        values = [point.heart_rate_bpm for point in points]

    filtered = [
        (point.elapsed_seconds, value)
        for point, value in zip(points, values)
        if value is not None and math.isfinite(float(value))
    ]
    if not filtered:
        raise ValueError("The selected telemetry type does not have usable data.")

    times = np.asarray([entry[0] for entry in filtered], dtype=float)
    metric_values = np.asarray([float(entry[1]) for entry in filtered], dtype=float)
    return times, metric_values


def _interpolate_value(times: np.ndarray, values: np.ndarray, elapsed_seconds: float) -> float:
    return float(np.interp(elapsed_seconds, times, values))


def _render_frame(
    *,
    telemetry_type: str,
    background_rgba: tuple[int, int, int, int],
    width_px: int,
    height_px: int,
    times: np.ndarray,
    values: np.ndarray,
    current_elapsed: float,
) -> Image.Image:
    image = Image.new("RGBA", (width_px, height_px), background_rgba)
    accent_color = (56, 189, 248, 255)
    text_color = (255, 255, 255, 255)
    current_value = _interpolate_value(times, values, current_elapsed)
    if telemetry_type == "elevation_value":
        _draw_text_block(
            image,
            label="Elevation",
            value=f"{current_value:.0f}",
            unit="meters",
            accent_color=accent_color,
            text_color=text_color,
        )
    elif telemetry_type == "speed":
        _draw_text_block(
            image,
            label="Speed",
            value=f"{current_value * 3.6:.1f}",
            unit="km/h",
            accent_color=accent_color,
            text_color=text_color,
        )
    elif telemetry_type == "heart_rate":
        _draw_text_block(
            image,
            label="Heart rate",
            value=f"{current_value:.0f}",
            unit="bpm",
            accent_color=accent_color,
            text_color=text_color,
        )
    else:
        _render_elevation_graph(
            image,
            times=times,
            elevations=values,
            current_elapsed=current_elapsed,
            current_value=current_value,
            accent_color=accent_color,
            text_color=text_color,
        )
    return image


def _open_ffmpeg_writer(
    output_path: str,
    *,
    width_px: int,
    height_px: int,
    fps: float,
) -> "subprocess.Popen[bytes]":
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{width_px}x{height_px}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-vcodec",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def create_telemetry_animation(
    points: list[TelemetryPoint],
    *,
    duration_seconds: float,
    fps: float,
    width_px: int,
    height_px: int,
    telemetry_type: str,
    background_color: str | None,
    output_path: str,
) -> None:
    resolved_type = resolve_telemetry_type(telemetry_type)
    ensure_telemetry_type_supported(points, resolved_type)
    source_duration_seconds = telemetry_duration_seconds(points)
    background_rgba = parse_background_color(background_color)
    times, values = _metric_series(points, resolved_type)
    effective_fps = _resolve_effective_fps(duration_seconds, fps)
    total_frames = max(int(duration_seconds * effective_fps), 2)
    ffmpeg_proc = _open_ffmpeg_writer(
        output_path,
        width_px=width_px,
        height_px=height_px,
        fps=effective_fps,
    )
    if ffmpeg_proc.stdin is None:
        raise RuntimeError("Failed to open ffmpeg pipe for writing.")

    try:
        for frame_index in range(total_frames):
            progress = frame_index / (total_frames - 1) if total_frames > 1 else 0.0
            current_elapsed = progress * source_duration_seconds
            frame_image = _render_frame(
                telemetry_type=resolved_type,
                background_rgba=background_rgba,
                width_px=width_px,
                height_px=height_px,
                times=times,
                values=values,
                current_elapsed=current_elapsed,
            )
            ffmpeg_proc.stdin.write(frame_image.tobytes())
    finally:
        ffmpeg_proc.stdin.close()
        return_code = ffmpeg_proc.wait()
        if return_code != 0:
            raise RuntimeError(f"ffmpeg exited with status {return_code}.")
