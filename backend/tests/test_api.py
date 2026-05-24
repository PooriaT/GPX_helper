from __future__ import annotations

import json
from io import BytesIO
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

from fastapi.testclient import TestClient

from gpx_helper.api.main import app
from gpx_helper.api.routes import animation as animation_route


GPX_NS = "http://www.topografix.com/GPX/1/1"


def _build_gpx() -> bytes:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<gpx version=\"1.1\" creator=\"test\" xmlns=\"http://www.topografix.com/GPX/1/1\">"
        "<trk><trkseg>"
        "<trkpt lat=\"0\" lon=\"0\"><time>2024-01-01T00:00:00Z</time></trkpt>"
        "<trkpt lat=\"0\" lon=\"0\"><time>2024-01-01T00:00:10Z</time></trkpt>"
        "<trkpt lat=\"0\" lon=\"0\"><time>2024-01-01T00:00:20Z</time></trkpt>"
        "</trkseg></trk></gpx>"
    ).encode("utf-8")


def _build_one_point_gpx() -> bytes:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<gpx version=\"1.1\" creator=\"test\" xmlns=\"http://www.topografix.com/GPX/1/1\">"
        "<trk><trkseg>"
        "<trkpt lat=\"0\" lon=\"0\"><time>2024-01-01T00:00:00Z</time></trkpt>"
        "</trkseg></trk></gpx>"
    ).encode("utf-8")


def _build_gpx_with_telemetry() -> bytes:
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
    ).encode("utf-8")


def _count_trkpts(payload: bytes) -> int:
    root = ET.fromstring(payload)
    return len(root.findall(".//{%s}trkpt" % GPX_NS))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_check(self) -> None:
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "gpx-helper"})

    def test_capabilities(self) -> None:
        response = self.client.get("/api/v1/capabilities")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], "v1")
        self.assertIn("POST /api/v1/gpx/trim-by-time", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/trim-by-video", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/trim-by-videos", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/map-animate/estimate", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/map-animate", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/map-animate/batch", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/map-animate/batch/estimate", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/telemetry-video/estimate", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/telemetry-video", payload["endpoints"])
        self.assertEqual(
            payload["map_layers"],
            [
                {"key": "", "value": "", "label": "Backend default (MAP_TILE_URL_TEMPLATE)"},
                {
                    "key": "osm",
                    "value": "osm",
                    "label": "OpenStreetMap (Standard)",
                    "preview_url": "https://tile.openstreetmap.org/12/654/1582.png",
                    "attribution": "OpenStreetMap contributors",
                },
                {
                    "key": "cyclosm",
                    "value": "cyclosm",
                    "label": "CyclOSM",
                    "preview_url": "https://a.tile-cyclosm.openstreetmap.fr/cyclosm/12/654/1582.png",
                    "attribution": "CyclOSM and OpenStreetMap contributors",
                },
                {
                    "key": "opentopomap",
                    "value": "opentopomap",
                    "label": "OpenTopoMap (Topo)",
                    "preview_url": "https://a.tile.opentopomap.org/12/654/1582.png",
                    "attribution": "OpenTopoMap and OpenStreetMap contributors",
                },
                {
                    "key": "esri_world_imagery",
                    "value": "esri_world_imagery",
                    "label": "Satellite (Esri World Imagery)",
                    "preview_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/12/1582/654",
                    "attribution": "Esri, Vantor, Earthstar Geographics, and the GIS User Community",
                },
            ],
        )
        for layer in payload["map_layers"]:
            self.assertNotIn("tile_url_template", layer)
            self.assertNotIn("subdomains", layer)

    def test_trim_by_time_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2024-01-01T00:00:02Z",
            "end_time": "2024-01-01T00:00:12Z",
        }

        response = self.client.post("/api/v1/gpx/trim-by-time", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/gpx+xml")
        self.assertEqual(_count_trkpts(response.content), 2)

    def test_trim_by_time_invalid_datetime(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2024-01-01T00:00:02",
            "end_time": "2024-01-01T00:00:12Z",
        }

        response = self.client.post("/api/v1/gpx/trim-by-time", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("timezone", response.json()["detail"])

    def test_trim_by_time_missing_filename(self) -> None:
        files = {
            "gpx_file": ("", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2024-01-01T00:00:02Z",
            "end_time": "2024-01-01T00:00:12Z",
        }

        response = self.client.post("/api/v1/gpx/trim-by-time", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Missing gpx_file filename")

    def test_trim_by_video_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T00:00:20Z",
            "duration_seconds": "20",
        }

        response = self.client.post("/api/v1/gpx/trim-by-video", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/gpx+xml")
        self.assertEqual(_count_trkpts(response.content), 3)

    def test_trim_by_video_out_of_range(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2023-12-31T23:59:50Z",
            "end_time": "2024-01-01T00:00:10Z",
            "duration_seconds": "20",
        }

        response = self.client.post("/api/v1/gpx/trim-by-video", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("outside GPX time range", response.json()["detail"])

    def test_trim_by_video_rejects_reversed_times(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "start_time": "2024-01-01T00:00:20Z",
            "end_time": "2024-01-01T00:00:10Z",
            "duration_seconds": "10",
        }

        response = self.client.post("/api/v1/gpx/trim-by-video", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "start_time must be before end_time")

    def test_trim_by_videos_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "clips_json": json.dumps(
                [
                    {
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:10Z",
                        "duration_seconds": 10,
                    },
                    {
                        "start_time": "2024-01-01T00:00:10Z",
                        "end_time": "2024-01-01T00:00:20Z",
                        "duration_seconds": 10,
                    },
                ]
            )
        }

        response = self.client.post("/api/v1/gpx/trim-by-videos", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn(
            "attachment; filename=trimmed-gpx-files.zip",
            response.headers["content-disposition"],
        )

        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ["1.gpx", "2.gpx"])
            self.assertEqual(_count_trkpts(archive.read("1.gpx")), 2)
            self.assertEqual(_count_trkpts(archive.read("2.gpx")), 2)

    def test_trim_by_videos_out_of_range(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "clips_json": json.dumps(
                [
                    {
                        "start_time": "2024-01-01T00:00:10Z",
                        "end_time": "2024-01-01T00:00:30Z",
                        "duration_seconds": 20,
                    }
                ]
            )
        }

        response = self.client.post("/api/v1/gpx/trim-by-videos", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Clip 1 timestamps fall outside GPX time range")

    def test_trim_by_videos_rejects_invalid_json(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "clips_json": "{not valid json}",
        }

        response = self.client.post("/api/v1/gpx/trim-by-videos", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "clips_json must be valid JSON")

    def test_map_animation_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "fps": "24",
            "resolution": "640x480",
            "tile_type": "cyclosm",
            "full_trail_opacity": "0.35",
            "line_opacity": "0.25",
        }
        fake_video = b"mp4-bytes"
        captured = {}

        def _fake_animation(
            xs,
            ys,
            frame_indices,
            total_frames,
            fps,
            width_px,
            height_px,
            output_path,
            **kwargs,
        ):
            captured.update(kwargs)
            captured["fps"] = fps
            with open(output_path, "wb") as f:
                f.write(fake_video)

        with mock.patch("gpx_helper.api.routes.animation.create_animation", side_effect=_fake_animation):
            response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertEqual(response.content, fake_video)
        self.assertIn("attachment; filename=track.mp4", response.headers["content-disposition"])
        self.assertEqual(
            captured.get("tile_template"),
            "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        )
        self.assertEqual(captured.get("tile_subdomains"), ("a", "b", "c"))
        self.assertEqual(captured.get("fps"), 24.0)
        self.assertEqual(captured.get("full_line_opacity"), 0.35)
        self.assertEqual(captured.get("animated_line_opacity"), 0.25)
        self.assertEqual(captured.get("marker_style"), "default")

    def test_map_animation_passes_marker_styles(self) -> None:
        for marker_style in ("bike", "runner"):
            with self.subTest(marker_style=marker_style):
                files = {
                    "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
                }
                data = {
                    "duration_seconds": "5",
                    "fps": "24",
                    "resolution": "640x480",
                    "marker_style": marker_style,
                }
                captured = {}

                def _fake_animation(
                    xs,
                    ys,
                    frame_indices,
                    total_frames,
                    fps,
                    width_px,
                    height_px,
                    output_path,
                    **kwargs,
                ):
                    captured.update(kwargs)
                    with open(output_path, "wb") as f:
                        f.write(b"mp4-bytes")

                with mock.patch(
                    "gpx_helper.api.routes.animation.create_animation",
                    side_effect=_fake_animation,
                ):
                    response = self.client.post(
                        "/api/v1/gpx/map-animate", files=files, data=data
                    )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(captured.get("marker_style"), marker_style)

    def test_map_animation_accepts_esri_world_imagery_tile_type(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "fps": "24",
            "resolution": "640x480",
            "tile_type": "esri_world_imagery",
        }
        captured = {}

        def _fake_animation(
            xs,
            ys,
            frame_indices,
            total_frames,
            fps,
            width_px,
            height_px,
            output_path,
            **kwargs,
        ):
            captured.update(kwargs)
            with open(output_path, "wb") as f:
                f.write(b"mp4-bytes")

        with mock.patch("gpx_helper.api.routes.animation.create_animation", side_effect=_fake_animation):
            response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            captured.get("tile_template"),
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        )
        self.assertEqual(captured.get("tile_subdomains"), ())

    def test_map_animation_invalid_resolution(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "not-a-size",
        }

        response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("resolution", response.json()["detail"])

    def test_map_animation_invalid_duration(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "0",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("duration_seconds", response.json()["detail"])

    def test_map_animation_invalid_fps(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "fps": "0",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("fps", response.json()["detail"])

    def test_map_animation_invalid_tile_type(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
            "tile_type": "not-a-tile",
        }

        response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("tile_type", response.json()["detail"])
        self.assertIn("esri_world_imagery", response.json()["detail"])

    def test_map_animation_invalid_marker_style(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
            "marker_style": "skis",
        }

        response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "marker_style must be one of: bike, default, runner",
        )

    def test_map_animation_batch_success(self) -> None:
        files = [
            ("gpx_files", ("track one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("track-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5, "output_name": "clip.mp4"},
                    {"gpx_file_index": 1, "duration_seconds": 7, "output_name": "clip"},
                ]
            ),
            "fps": "24",
            "resolution": "640x480",
            "marker_color": "#ef4444",
            "marker_style": "bike",
            "trail_color": "#22c55e",
            "full_trail_color": "#111827",
            "full_trail_opacity": "0.4",
            "line_width": "4.5",
            "line_opacity": "0.65",
            "marker_size": "8",
            "tile_type": "cyclosm",
        }
        captured_calls = []

        def _fake_animation(
            xs,
            ys,
            frame_indices,
            total_frames,
            fps,
            width_px,
            height_px,
            output_path,
            **kwargs,
        ):
            captured_calls.append(
                {
                    "fps": fps,
                    "width_px": width_px,
                    "height_px": height_px,
                    **kwargs,
                }
            )
            with open(output_path, "wb") as f:
                f.write(f"mp4-{len(captured_calls)}".encode("utf-8"))

        with mock.patch(
            "gpx_helper.api.routes.animation.create_animation",
            side_effect=_fake_animation,
        ) as mock_create_animation, mock.patch(
            "gpx_helper.api.routes.animation.load_gpx_points",
            wraps=animation_route.load_gpx_points,
        ) as mock_load_gpx_points:
            response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_load_gpx_points.call_count, 2)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn(
            "attachment; filename=route-animations.zip",
            response.headers["content-disposition"],
        )
        self.assertEqual(mock_create_animation.call_count, 2)
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ["clip.mp4", "clip-2.mp4"])
            self.assertEqual(archive.read("clip.mp4"), b"mp4-1")
            self.assertEqual(archive.read("clip-2.mp4"), b"mp4-2")

        for captured in captured_calls:
            self.assertEqual(captured["fps"], 24.0)
            self.assertEqual(captured["width_px"], 640)
            self.assertEqual(captured["height_px"], 480)
            self.assertEqual(captured["marker_color"], "#ef4444")
            self.assertEqual(captured["animated_line_color"], "#22c55e")
            self.assertEqual(captured["full_line_color"], "#111827")
            self.assertEqual(captured["full_line_opacity"], 0.4)
            self.assertEqual(captured["line_width"], 4.5)
            self.assertEqual(captured["animated_line_opacity"], 0.65)
            self.assertEqual(captured["marker_size"], 8.0)
            self.assertEqual(captured["marker_style"], "bike")
            self.assertEqual(
                captured["tile_template"],
                "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
            )
            self.assertEqual(captured["tile_subdomains"], ("a", "b", "c"))

    def test_map_animation_batch_rejects_invalid_jobs_json(self) -> None:
        files = [
            ("gpx_files", ("track.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": "{not valid json}",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "jobs_json must be valid JSON")

    def test_map_animation_batch_rejects_empty_jobs(self) -> None:
        files = [
            ("gpx_files", ("track.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": "[]",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "jobs_json must be a non-empty array")

    def test_map_animation_batch_rejects_invalid_gpx_index(self) -> None:
        files = [
            ("gpx_files", ("track.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps([{"gpx_file_index": 1, "duration_seconds": 5}]),
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Batch item 1: gpx_file_index is out of range",
        )

    def test_map_animation_batch_rejects_invalid_pair_duration_with_item(self) -> None:
        files = [
            ("gpx_files", ("track-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("track-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5},
                    {"gpx_file_index": 1, "duration_seconds": 0},
                ]
            ),
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Batch item 2: duration_seconds must be greater than zero",
        )

    def test_map_animation_batch_rejects_duplicate_gpx_index_with_item(self) -> None:
        files = [
            ("gpx_files", ("track-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("track-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5},
                    {"gpx_file_index": 0, "duration_seconds": 7},
                ]
            ),
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Batch item 2: duplicate gpx_file_index 0")

    def test_map_animation_batch_render_failure_identifies_item_and_file(self) -> None:
        files = [
            ("gpx_files", ("ride-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("ride-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5},
                    {"gpx_file_index": 1, "duration_seconds": 7},
                ]
            ),
            "resolution": "640x480",
        }
        calls = 0

        def _fake_animation(
            xs,
            ys,
            frame_indices,
            total_frames,
            fps,
            width_px,
            height_px,
            output_path,
            **kwargs,
        ):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("encoder failed")
            with open(output_path, "wb") as f:
                f.write(b"mp4-bytes")

        with mock.patch(
            "gpx_helper.api.routes.animation.create_animation",
            side_effect=_fake_animation,
        ):
            response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(
            response.json()["detail"],
            "Batch item 2 (ride-two.gpx) failed: encoder failed",
        )

    def test_map_animation_batch_preflight_rejects_invalid_gpx_before_rendering(self) -> None:
        files = [
            ("gpx_files", ("ride-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("ride-two.gpx", _build_one_point_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5},
                    {"gpx_file_index": 1, "duration_seconds": 7},
                ]
            ),
            "resolution": "640x480",
        }

        with mock.patch("gpx_helper.api.routes.animation.create_animation") as mock_create_animation:
            response = self.client.post("/api/v1/gpx/map-animate/batch", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mock_create_animation.call_count, 0)
        self.assertNotEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(
            response.json()["detail"],
            "Batch item 2 (ride-two.gpx) failed: Need at least 2 points to animate",
        )

    def test_map_animation_batch_eta_success(self) -> None:
        files = [
            ("gpx_files", ("track-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("track-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5, "output_name": "one"},
                    {"gpx_file_index": 1, "duration_seconds": 7, "output_name": "two"},
                ]
            ),
            "fps": "12",
            "resolution": "640x480",
            "marker_color": "#ef4444",
            "marker_style": "bike",
            "trail_color": "#22c55e",
            "full_trail_color": "#111827",
            "full_trail_opacity": "0.4",
            "line_width": "4.5",
            "line_opacity": "0.65",
            "marker_size": "8",
            "tile_type": "cyclosm",
        }
        with mock.patch(
            "gpx_helper.api.routes.animation.estimate_animation_seconds",
            side_effect=[1.234, 2.345],
        ) as mock_estimate:
            response = self.client.post(
                "/api/v1/gpx/map-animate/batch/estimate", files=files, data=data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"estimated_seconds": 3.58})
        self.assertEqual(mock_estimate.call_count, 2)
        self.assertEqual(mock_estimate.call_args_list[0].args[2:5], (640, 480, 5.0))
        self.assertEqual(mock_estimate.call_args_list[0].kwargs["fps"], 12.0)
        self.assertEqual(mock_estimate.call_args_list[1].args[2:5], (640, 480, 7.0))

    def test_map_animation_batch_eta_rejects_invalid_gpx_index(self) -> None:
        files = [
            ("gpx_files", ("track.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps([{"gpx_file_index": 2, "duration_seconds": 5}]),
            "resolution": "640x480",
        }

        response = self.client.post(
            "/api/v1/gpx/map-animate/batch/estimate", files=files, data=data
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Batch item 1: gpx_file_index is out of range",
        )

    def test_map_animation_batch_eta_rejects_invalid_duration_with_item(self) -> None:
        files = [
            ("gpx_files", ("track-one.gpx", _build_gpx(), "application/gpx+xml")),
            ("gpx_files", ("track-two.gpx", _build_gpx(), "application/gpx+xml")),
        ]
        data = {
            "jobs_json": json.dumps(
                [
                    {"gpx_file_index": 0, "duration_seconds": 5},
                    {"gpx_file_index": 1, "duration_seconds": 0},
                ]
            ),
            "resolution": "640x480",
        }

        response = self.client.post(
            "/api/v1/gpx/map-animate/batch/estimate", files=files, data=data
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Batch item 2: duration_seconds must be greater than zero",
        )

    def test_map_animation_eta_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "fps": "12",
            "resolution": "640x480",
        }
        with mock.patch(
            "gpx_helper.api.routes.animation.estimate_animation_seconds", return_value=3.5
        ) as mock_estimate:
            response = self.client.post(
                "/api/v1/gpx/map-animate/estimate", files=files, data=data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"estimated_seconds": 3.5})
        self.assertEqual(mock_estimate.call_args.kwargs["fps"], 12.0)

    def test_map_animation_eta_invalid_duration(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "0",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/estimate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("duration_seconds", response.json()["detail"])

    def test_map_animation_eta_invalid_fps(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "fps": "-1",
            "resolution": "640x480",
        }

        response = self.client.post("/api/v1/gpx/map-animate/estimate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("fps", response.json()["detail"])

    def test_map_animation_eta_invalid_tile_type(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
            "tile_type": "bad-tile",
        }

        response = self.client.post("/api/v1/gpx/map-animate/estimate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("tile_type", response.json()["detail"])
        self.assertIn("esri_world_imagery", response.json()["detail"])

    def test_map_animation_eta_invalid_marker_style(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
            "marker_style": "skis",
        }

        response = self.client.post("/api/v1/gpx/map-animate/estimate", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "marker_style must be one of: bike, default, runner",
        )

    def test_telemetry_video_success(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "heart_rate",
            "background_color": "transparent",
        }
        fake_video = b"telemetry-webm"
        captured = {}

        def _fake_telemetry_animation(points, **kwargs):
            captured["point_count"] = len(points)
            captured.update(kwargs)
            with open(kwargs["output_path"], "wb") as f:
                f.write(fake_video)

        with mock.patch(
            "gpx_helper.api.routes.telemetry.create_telemetry_animation",
            side_effect=_fake_telemetry_animation,
        ):
            response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/webm")
        self.assertEqual(response.content, fake_video)
        self.assertIn(
            "attachment; filename=ride-heart_rate.webm",
            response.headers["content-disposition"],
        )
        self.assertEqual(captured["point_count"], 3)
        self.assertEqual(captured["telemetry_type"], "heart_rate")
        self.assertEqual(captured["background_color"], "transparent")
        self.assertEqual(captured["width_px"], 640)
        self.assertEqual(captured["height_px"], 640)

    def test_telemetry_video_omitted_background_defaults_to_webm(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "heart_rate",
        }
        fake_video = b"telemetry-default-webm"
        captured = {}

        def _fake_telemetry_animation(points, **kwargs):
            captured.update(kwargs)
            with open(kwargs["output_path"], "wb") as f:
                f.write(fake_video)

        with mock.patch(
            "gpx_helper.api.routes.telemetry.create_telemetry_animation",
            side_effect=_fake_telemetry_animation,
        ):
            response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/webm")
        self.assertEqual(response.content, fake_video)
        self.assertIn(
            "attachment; filename=ride-heart_rate.webm",
            response.headers["content-disposition"],
        )
        self.assertIsNone(captured["background_color"])

    def test_telemetry_video_opaque_background_returns_mp4(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "heart_rate",
            "background_color": "#000000",
        }
        fake_video = b"telemetry-mp4"

        def _fake_telemetry_animation(points, **kwargs):
            with open(kwargs["output_path"], "wb") as f:
                f.write(fake_video)

        with mock.patch(
            "gpx_helper.api.routes.telemetry.create_telemetry_animation",
            side_effect=_fake_telemetry_animation,
        ):
            response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertEqual(response.content, fake_video)
        self.assertIn(
            "attachment; filename=ride-heart_rate.mp4",
            response.headers["content-disposition"],
        )

    def test_telemetry_video_rejects_missing_heart_rate_data(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "heart_rate",
            "background_color": "transparent",
        }

        response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("heart rate data", response.json()["detail"])

    def test_telemetry_video_elevation_graph_success(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "elevation_graph",
            "background_color": "transparent",
        }
        fake_video = b"elevation-graph-webm"
        captured = {}

        def _fake_telemetry_animation(points, **kwargs):
            captured.update(kwargs)
            with open(kwargs["output_path"], "wb") as f:
                f.write(fake_video)

        with mock.patch(
            "gpx_helper.api.routes.telemetry.create_telemetry_animation",
            side_effect=_fake_telemetry_animation,
        ):
            response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/webm")
        self.assertEqual(response.content, fake_video)
        self.assertEqual(captured["telemetry_type"], "elevation_graph")

    def test_telemetry_video_rejects_invalid_background_color(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "heart_rate",
            "background_color": "not-a-color",
        }

        response = self.client.post("/api/v1/gpx/telemetry-video", files=files, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid background_color", response.json()["detail"])

    def test_telemetry_video_estimate_success(self) -> None:
        files = {
            "gpx_file": ("ride.gpx", _build_gpx_with_telemetry(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "20",
            "fps": "30",
            "resolution": "640x640",
            "telemetry_type": "elevation_graph",
        }

        response = self.client.post("/api/v1/gpx/telemetry-video/estimate", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["estimated_seconds"], float)


if __name__ == "__main__":
    unittest.main()
