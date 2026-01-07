from __future__ import annotations

import unittest
from unittest import mock

from gpx_helper import map_animator
from gpx_helper.map_animator import prepare_animation_data, prepare_animation_series


class MapAnimatorTests(unittest.TestCase):
    def test_prepare_animation_data_returns_monotonic_indices(self) -> None:
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [0.0, 1.0, 2.0, 3.0]

        frame_indices, total_frames, fps = prepare_animation_data(xs, ys, 2.0, fps=4)

        self.assertEqual(total_frames, 8)
        self.assertEqual(fps, 4)
        self.assertEqual(frame_indices[0], 0)
        self.assertEqual(frame_indices[-1], len(xs) - 1)
        self.assertTrue(
            all(
                earlier <= later
                for earlier, later in zip(frame_indices, frame_indices[1:])
            )
        )

    def test_prepare_animation_data_enforces_min_frames(self) -> None:
        xs = [0.0, 1.0]
        ys = [0.0, 1.0]

        frame_indices, total_frames, _ = prepare_animation_data(xs, ys, 0.01, fps=1)

        self.assertEqual(total_frames, 2)
        self.assertEqual(len(frame_indices), 2)

    def test_prepare_animation_series_resamples_to_frames(self) -> None:
        xs = [float(i) for i in range(10)]
        ys = [float(i) for i in range(10)]

        with mock.patch.object(map_animator, "DEFAULT_MAX_FRAMES", 1000):
            xs_out, ys_out, frame_indices, total_frames, fps = prepare_animation_series(
                xs, ys, 2.0, fps=2
            )

        self.assertEqual(fps, 2)
        self.assertEqual(total_frames, 4)
        self.assertEqual(len(xs_out), 4)
        self.assertEqual(len(ys_out), 4)
        self.assertEqual(len(frame_indices), total_frames)
        self.assertAlmostEqual(xs_out[0], xs[0])
        self.assertAlmostEqual(xs_out[-1], xs[-1])

    def test_prepare_animation_series_caps_fps(self) -> None:
        xs = [0.0, 1.0, 2.0]
        ys = [0.0, 1.0, 2.0]

        with mock.patch.object(map_animator, "DEFAULT_MAX_FRAMES", 20):
            xs_out, ys_out, frame_indices, total_frames, fps = prepare_animation_series(
                xs, ys, 10.0, fps=30
            )

        self.assertEqual(fps, 2)
        self.assertEqual(total_frames, 20)
        self.assertEqual(len(xs_out), len(xs))
        self.assertEqual(len(ys_out), len(ys))
        self.assertEqual(len(frame_indices), total_frames)

    def test_estimate_animation_seconds_respects_preset_speed(self) -> None:
        lats = [0.0, 0.0, 0.01]
        lons = [0.0, 0.01, 0.02]

        with mock.patch.object(map_animator, "DEFAULT_FFMPEG_PRESET", "ultrafast"):
            fast_estimate = map_animator.estimate_animation_seconds(
                lats, lons, 640, 480, 10.0
            )

        with mock.patch.object(map_animator, "DEFAULT_FFMPEG_PRESET", "veryslow"):
            slow_estimate = map_animator.estimate_animation_seconds(
                lats, lons, 640, 480, 10.0
            )

        self.assertLess(fast_estimate, slow_estimate)


if __name__ == "__main__":
    unittest.main()
