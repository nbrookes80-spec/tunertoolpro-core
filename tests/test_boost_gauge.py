"""The MAP sensor (010B) shows boost gauge pressure: absolute pressure above 14.7 psi atmosphere, never negative,
so it matches a boost gauge. Other sensors are unchanged."""
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

from tunertoolpro.scanner import pid_view, units

PSI_KPA = 6.894757
Stub = namedtuple('Stub', 'pid unit')


class BoostConversionTests(unittest.TestCase):
    def test_atmosphere_reads_zero_boost(self):
        conv = units.boost_conversion('kPa', {'pressure': 'psi'})
        self.assertAlmostEqual(conv.forward(14.7 * PSI_KPA), 0.0, places=6)

    def test_two_psi_above_atmosphere_reads_two_psi(self):
        conv = units.boost_conversion('kPa', {'pressure': 'psi'})
        self.assertAlmostEqual(conv.forward(16.7 * PSI_KPA), 2.0, places=6)

    def test_vacuum_reads_zero_not_negative(self):
        conv = units.boost_conversion('kPa', {'pressure': 'psi'})
        self.assertEqual(conv.forward(40.0), 0.0)

    def test_kpa_choice_is_gauge_kpa(self):
        conv = units.boost_conversion('kPa', {'pressure': 'kPa'})
        self.assertAlmostEqual(conv.forward(120.0), 120.0 - 14.7 * PSI_KPA, places=6)
        self.assertEqual(conv.forward(50.0), 0.0)

    def test_back_reverses_forward_above_atmosphere(self):
        conv = units.boost_conversion('kPa', {'pressure': 'psi'})
        self.assertAlmostEqual(conv.back(conv.forward(130.0)), 130.0, places=6)

    def test_unit_label_is_the_chosen_unit(self):
        self.assertEqual(units.boost_conversion('kPa', {'pressure': 'psi'}).unit, 'psi')


class MapSensorViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.views = pid_view.PidViews(Path(self.tmp.name) / 'views.json')
        self.views.set_units({'pressure': 'psi'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_map_pid_uses_boost_gauge(self):
        conv = self.views.conversion(Stub('010B', 'kPa'))
        self.assertEqual(conv.forward(40.0), 0.0)
        self.assertAlmostEqual(conv.forward(16.7 * PSI_KPA), 2.0, places=6)

    def test_other_pressure_pid_is_not_changed(self):
        conv = self.views.conversion(Stub('0133', 'kPa'))
        self.assertAlmostEqual(conv.forward(101.3), 101.3 / PSI_KPA, places=6)


if __name__ == '__main__':
    unittest.main()
