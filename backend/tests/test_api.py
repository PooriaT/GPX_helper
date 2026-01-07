from __future__ import annotations

import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from gpx_helper.api.main import app


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
        self.assertIn("POST /api/v1/gpx/map-animate/estimate", payload["endpoints"])
        self.assertIn("POST /api/v1/gpx/map-animate", payload["endpoints"])

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

    def test_map_animation_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
            "tile_type": "cyclosm",
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
            with open(output_path, "wb") as f:
                f.write(fake_video)

        with mock.patch("gpx_helper.api.main.create_animation", side_effect=_fake_animation):
            response = self.client.post("/api/v1/gpx/map-animate", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertEqual(response.content, fake_video)
        self.assertIn("attachment; filename=route.mp4", response.headers["content-disposition"])
        self.assertEqual(
            captured.get("tile_template"),
            "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        )
        self.assertEqual(captured.get("tile_subdomains"), ("a", "b", "c"))

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
    def test_map_animation_eta_success(self) -> None:
        files = {
            "gpx_file": ("track.gpx", _build_gpx(), "application/gpx+xml"),
        }
        data = {
            "duration_seconds": "5",
            "resolution": "640x480",
        }
        with mock.patch(
            "gpx_helper.api.main.estimate_animation_seconds", return_value=3.5
        ):
            response = self.client.post(
                "/api/v1/gpx/map-animate/estimate", files=files, data=data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"estimated_seconds": 3.5})

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


if __name__ == "__main__":
    unittest.main()
