from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
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
            "video_file": ("clip.mp4", BytesIO(b"fake-video"), "video/mp4"),
        }
        start_dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(2024, 1, 1, 0, 0, 20, tzinfo=timezone.utc)

        with mock.patch("gpx_helper.api.main.get_video_times", return_value=(start_dt, end_dt)):
            response = self.client.post("/api/v1/gpx/trim-by-video", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/gpx+xml")
        self.assertEqual(_count_trkpts(response.content), 3)


if __name__ == "__main__":
    unittest.main()
