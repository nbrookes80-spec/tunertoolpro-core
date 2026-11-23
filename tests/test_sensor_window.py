"""The 2.7 bar MAP scaling for PID 010B and the 0.5-4.5 V window the sensor can physically produce.

The owner's report (GM reference doc section 2) gives the line 62.5 x V - 11.25 for the Proflow PFEFI-MAP2, and the
ECU's 8-bit count A stands for V = A x 5 / 255. The two forms must be the same line for every byte.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro.live import LiveStream  # noqa: E402
from tunertoolpro.scanner import pids, sensor_window  # noqa: E402
from tests.test_stream_wire import ECU, FakeAdapter  # noqa: E402


def kpa_from_volts(v):
    """The report's line, clamped at 0 the same way the app clamps."""
    return max(0.0, 62.5 * v - 11.25)


class MapScalingTests(unittest.TestCase):
    def test_the_byte_form_is_the_report_line_for_every_byte(self):
        pid = pids.get('010B')
        for a in range(256):
            with self.subTest(byte=a):
                v = a * 5.0 / 255.0
                self.assertAlmostEqual(pid.parse(f'{a:02X}'), kpa_from_volts(v), places=9)

    def test_the_known_points(self):
        pid = pids.get('010B')
        self.assertAlmostEqual(pid.parse('1A'), 20.6, places=1)     # 0.51 V
        self.assertAlmostEqual(pid.parse('E5'), 269.4, places=1)    # 4.48 V
        self.assertAlmostEqual(pid.parse('FF'), 301.25)             # 5.00 V, the value the window flags
        self.assertEqual(pid.parse('00'), 0.0)                      # -11.25 clamped to 0


class WindowTests(unittest.TestCase):
    def test_inside_the_window_there_is_no_note(self):
        for a in ('1A', '64', 'E5'):   # 0.51 V, 2.0 V, 4.48 V
            with self.subTest(byte=a):
                self.assertIsNone(sensor_window.fault('010B', a))

    def test_above_4_5_volts_is_flagged(self):
        self.assertIsNone(sensor_window.fault('010B', 'E5'))          # 229 = 4.482 V, still inside
        self.assertIsNotNone(sensor_window.fault('010B', 'E6'))       # 230 = 4.510 V, outside
        self.assertIn('above its 4.5 V limit', sensor_window.fault('010B', 'FF'))

    def test_below_0_5_volts_is_flagged(self):
        self.assertIsNotNone(sensor_window.fault('010B', '19'))       # 25 = 0.490 V, outside
        self.assertIsNone(sensor_window.fault('010B', '1A'))          # 26 = 0.510 V, inside
        self.assertIn('below its 0.5 V limit', sensor_window.fault('010B', '00'))

    def test_only_the_map_pid_is_windowed(self):
        self.assertIsNone(sensor_window.fault('010C', 'FF'))
        self.assertIsNone(sensor_window.fault('0105', '00'))

    def test_a_short_reply_is_not_flagged_here(self):
        self.assertIsNone(sensor_window.fault('010B', ''))


class FlagOverTheWireTests(unittest.TestCase):
    """A 5 V reply keeps its number and gets a note; the live stream passes the note on for the screen."""

    def setUp(self):
        self._saved = ECU.get('010B')
        ECU['010B'] = '410BFF'

    def tearDown(self):
        ECU['010B'] = self._saved

    def test_five_volts_keeps_the_value_and_adds_a_note(self):
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        stream = LiveStream(adapter.link())
        stream.step()
        entry = stream.snapshot()['values']['010B']
        self.assertAlmostEqual(entry['value'], 301.25)
        self.assertIn('above its 4.5 V limit', entry['note'])

    def test_a_normal_reply_has_no_note(self):
        ECU['010B'] = '410B64'
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        stream = LiveStream(adapter.link())
        stream.step()
        entry = stream.snapshot()['values']['010B']
        self.assertIsNone(entry['note'])


if __name__ == '__main__':
    unittest.main()
