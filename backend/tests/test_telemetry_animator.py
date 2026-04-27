from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import gpx_helper.telemetry_animator as telemetry_animator
from gpx_helper.telemetry_animator import (
    elevation_extrema,
    ensure_telemetry_type_supported,
    load_gpx_telemetry,
    parse_background_color,
    telemetry_duration_seconds,
)


def _build_gpx_with_telemetry() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<gpx version=\"1.1\" creator=\"test\" "
        "xmlns=\"http://www.topografix.com/GPX/1/1\" "
        "xmlns:gpxtpx=\"http://www.garmin.com/xmlschemas/TrackPointExtension/v1\">"
        "<trk><trkseg>"
        "<trkpt lat=\"49.0\" lon=\"-123.0\">"
        "<ele>10</ele><time>2024-01-01T00:00:00Z</time>"
        "<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>120</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions>"
        "</trkpt>"
        "<trkpt lat=\"49.0002\" lon=\"-123.0002\">"
        "<ele>20</ele><time>2024-01-01T00:00:10Z</time>"
        "<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>140</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions>"
        "</trkpt>"
        "<trkpt lat=\"49.0004\" lon=\"-123.0004\">"
        "<ele>30</ele><time>2024-01-01T00:00:20Z</time>"
        "<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>160</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions>"
        "</trkpt>"
        "</trkseg></trk></gpx>"
    )


def _build_gpx_without_heart_rate() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<gpx version=\"1.1\" creator=\"test\" xmlns=\"http://www.topografix.com/GPX/1/1\">"
        "<trk><trkseg>"
        "<trkpt lat=\"49.0\" lon=\"-123.0\"><ele>10</ele><time>2024-01-01T00:00:00Z</time></trkpt>"
        "<trkpt lat=\"49.0002\" lon=\"-123.0002\"><ele>20</ele><time>2024-01-01T00:00:10Z</time></trkpt>"
        "</trkseg></trk></gpx>"
    )


class TelemetryAnimatorTests(unittest.TestCase):
    def _write_temp_gpx(self, payload: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".gpx", delete=False)
        self.addCleanup(lambda: os.unlink(handle.name))
        with handle:
            handle.write(payload)
        return handle.name

    def test_load_gpx_telemetry_extracts_duration_and_metrics(self) -> None:
        path = self._write_temp_gpx(_build_gpx_with_telemetry())

        points = load_gpx_telemetry(path)

        self.assertEqual(len(points), 3)
        self.assertEqual(telemetry_duration_seconds(points), 20.0)
        self.assertEqual(points[0].elevation_meters, 10.0)
        self.assertEqual(points[-1].heart_rate_bpm, 160.0)
        self.assertGreater(points[1].speed_mps or 0.0, 0.0)

    def test_ensure_telemetry_type_supported_rejects_missing_heart_rate(self) -> None:
        path = self._write_temp_gpx(_build_gpx_without_heart_rate())
        points = load_gpx_telemetry(path)

        with self.assertRaisesRegex(ValueError, "heart rate data"):
            ensure_telemetry_type_supported(points, "heart_rate")

    def test_parse_background_color_supports_transparent_keyword(self) -> None:
        self.assertEqual(parse_background_color(None), (0, 0, 0, 0))
        self.assertEqual(parse_background_color(""), (0, 0, 0, 0))
        self.assertEqual(parse_background_color("transparent"), (0, 0, 0, 0))
        self.assertEqual(parse_background_color("#112233"), (17, 34, 51, 255))

    def test_parse_background_color_rejects_invalid_color(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid background_color"):
            parse_background_color("not-a-color")

    def test_elevation_extrema_uses_actual_values(self) -> None:
        values = telemetry_animator.np.asarray([42.0, 318.0, 101.0], dtype=float)

        min_point, max_point = elevation_extrema(values)

        self.assertEqual(min_point, (0, 42.0))
        self.assertEqual(max_point, (1, 318.0))

    def test_open_ffmpeg_writer_uses_alpha_capable_encoding(self) -> None:
        with mock.patch("subprocess.Popen") as mock_popen:
            telemetry_animator._open_ffmpeg_writer(
                "/tmp/out.webm",
                width_px=640,
                height_px=360,
                fps=30.0,
                use_alpha=True,
            )

        cmd = mock_popen.call_args.args[0]
        self.assertIn("libvpx-vp9", cmd)
        self.assertIn("yuva420p", cmd)
        self.assertNotIn("libx264", cmd)


if __name__ == "__main__":
    unittest.main()
