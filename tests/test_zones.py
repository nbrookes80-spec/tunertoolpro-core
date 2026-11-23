"""Red, yellow and green zones and a colour for each sensor (scanner/pid_view.py). No Kivy."""

import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tunertoolpro.scanner import pid_view, pids  # noqa: E402


def zone(value, **shown):
    return pid_view.zone(value, shown)


class ZonePriorityTests(unittest.TestCase):
    FULL = dict(red_low=10.0, warn_low=20.0, cold=30.0, good=40.0, good_to=60.0, warn=70.0, redline=80.0)

    def test_every_band_in_order(self):
        values = [5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 65, 70, 75, 80, 90]
        self.assertEqual([zone(v, **self.FULL) for v in values],
                         ['red', 'red', 'yellow', 'yellow', 'cold', None, None, 'good', 'good', 'good',
                          None, 'yellow', 'yellow', 'red', 'red'])

    def test_zone_order_is_the_priority(self):
        self.assertEqual(pid_view.ZONE_ORDER, ('red', 'yellow', 'good', 'cold'))

    def test_red_at_both_ends(self):
        shown = dict(red_low=5.0, redline=95.0)
        self.assertEqual([zone(v, **shown) for v in (0, 5, 5.1, 50, 94.9, 95, 120)],
                         ['red', 'red', None, None, None, 'red', 'red'])

    def test_red_beats_yellow_beats_green_beats_cold(self):
        self.assertEqual(zone(50, red_low=60.0, warn_low=70.0, good=0.0, cold=100.0), 'red')
        self.assertEqual(zone(65, warn_low=70.0, good=0.0, cold=100.0), 'yellow')
        self.assertEqual(zone(65, good=0.0, cold=100.0), 'good')
        self.assertEqual(zone(65, cold=100.0), 'cold')

    def test_the_yellow_stretch_below_the_red_line(self):
        shown = dict(warn=90.0, redline=100.0)
        self.assertEqual([zone(v, **shown) for v in (89.9, 90, 99.9, 100)], [None, 'yellow', 'yellow', 'red'])

    def test_yellow_low_ends_at_the_value_and_red_low_wins_below_it(self):
        shown = dict(red_low=10.0, warn_low=20.0)
        self.assertEqual([zone(v, **shown) for v in (9, 10, 10.1, 20, 20.1)], ['red', 'red', 'yellow', 'yellow', None])

    def test_green_can_have_either_end_open(self):
        self.assertEqual([zone(v, good=50.0) for v in (49, 50, 1e9)], [None, 'good', 'good'])
        self.assertEqual([zone(v, good_to=50.0) for v in (-1e9, 50, 50.1)], ['good', 'good', None])
        self.assertEqual([zone(v, good=40.0, good_to=60.0) for v in (39.9, 40, 60, 60.1)], [None, 'good', 'good', None])

    def test_no_value_or_no_zones_means_the_ordinary_colour(self):
        self.assertIsNone(zone(None, **self.FULL))
        self.assertIsNone(zone(55, ))
        self.assertIsNone(pid_view.zone(55, {'red_low': None, 'warn': None, 'color': '#00FFFF'}))


class OldKeysUnchangedTests(unittest.TestCase):
    def test_the_old_three_keys_behave_exactly_as_before(self):
        shown = {'cold': 50.0, 'good': 70.0, 'redline': 110.0}
        self.assertEqual([pid_view.zone(v, shown) for v in (40, 50, 69.9, 70, 109.9, 110, 200)],
                         ['cold', None, None, 'good', 'good', 'red', 'red'])
        self.assertEqual(pid_view.zone(100, {'cold': 150.0, 'good': 10.0, 'redline': 90.0}), 'red')

    def test_an_old_entry_cleans_to_itself_and_applies_with_no_new_zones(self):
        old = {'mode': 'graph', 'redline': 6300.0, 'cold': 1.0, 'good': 2.0, 'name': 'Revs', 'low': 0.0, 'high': 8000.0}
        self.assertEqual(pid_view.clean(old), old)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'v.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump({'010C': old}, handle)
            views = pid_view.PidViews(path)
            self.assertEqual(views.get('010C'), old)
            shown = views.apply(pids.CATALOG['010C'])
            for key in ('red_low', 'warn_low', 'good_to', 'warn', 'color'):
                self.assertIsNone(shown[key])


class BandTests(unittest.TestCase):
    def test_old_keys_give_the_old_bands(self):
        self.assertEqual(pid_view.bands({'cold': 20.0, 'good': 50.0, 'redline': 80.0}, 0.0, 100.0),
                         [(0.0, 20.0, 'cold'), (50.0, 80.0, 'good'), (80.0, 100.0, 'red')])

    def test_both_ends_and_yellow(self):
        shown = dict(red_low=10.0, warn_low=20.0, good=40.0, good_to=60.0, warn=70.0, redline=80.0)
        self.assertEqual(pid_view.bands(shown, 0.0, 100.0),
                         [(0.0, 10.0, 'red'), (10.0, 20.0, 'yellow'), (40.0, 60.0, 'good'),
                          (70.0, 80.0, 'yellow'), (80.0, 100.0, 'red')])

    def test_open_ended_green_runs_to_the_next_zone_or_the_end(self):
        self.assertEqual(pid_view.bands({'good': 50.0}, 0.0, 100.0), [(50.0, 100.0, 'good')])
        self.assertEqual(pid_view.bands({'good_to': 30.0}, 0.0, 100.0), [(0.0, 30.0, 'good')])

    def test_limits_outside_the_scale_and_a_bad_scale(self):
        self.assertEqual(pid_view.bands({'redline': 500.0}, 0.0, 100.0), [])
        self.assertEqual(pid_view.bands({'redline': -5.0}, 0.0, 100.0), [(0.0, 100.0, 'red')])
        self.assertEqual(pid_view.bands({'redline': 5.0}, 10.0, 10.0), [])
        self.assertEqual(pid_view.bands({}, 0.0, 100.0), [])

    def test_every_band_agrees_with_zone(self):
        shown = dict(red_low=10.0, warn_low=20.0, cold=35.0, good=40.0, good_to=60.0, warn=70.0, redline=80.0)
        for start, end, name in pid_view.bands(shown, 0.0, 100.0):
            self.assertEqual(pid_view.zone((start + end) / 2, shown), name)


class CleanTests(unittest.TestCase):
    def test_new_numbers_are_kept(self):
        entry = dict(red_low=1, warn_low=2.5, good_to=3, warn=4)
        self.assertEqual(pid_view.clean(entry), dict(red_low=1.0, warn_low=2.5, good_to=3.0, warn=4.0))

    def test_nan_inf_bool_and_text_numbers_are_dropped(self):
        for bad in (float('nan'), float('inf'), -math.inf, True, False, '5', None, [1], {}):
            entry = {key: bad for key in ('red_low', 'warn_low', 'good_to', 'warn')}
            self.assertEqual(pid_view.clean(entry), {}, bad)

    def test_a_good_colour_is_kept_and_normalised(self):
        self.assertEqual(pid_view.clean({'color': '#00ffff'}), {'color': '#00FFFF'})
        self.assertEqual(pid_view.clean({'color': ' #FF8800 '}), {'color': '#FF8800'})

    def test_a_bad_colour_is_dropped(self):
        for bad in ('00FFFF', '#0FF', '#GGGGGG', '#00FFFFAA', 'red', '', None, 5, True, ['#000000']):
            self.assertEqual(pid_view.clean({'color': bad, 'redline': 1}), {'redline': 1.0}, bad)

    def test_rgba_turns_a_colour_into_floats(self):
        self.assertEqual(pid_view.rgba('#FF0000'), (1.0, 0.0, 0.0, 1.0))
        self.assertEqual(pid_view.rgba('#000000', 0.5), (0.0, 0.0, 0.0, 0.5))
        self.assertIsNone(pid_view.rgba('nope'))
        self.assertIsNone(pid_view.rgba(None))


class ProblemTests(unittest.TestCase):
    def test_a_good_set_has_no_problems(self):
        full = dict(red_low=10.0, warn_low=20.0, cold=30.0, good=40.0, good_to=60.0, warn=70.0, redline=80.0)
        self.assertEqual(pid_view.zone_problems(full), [])
        self.assertEqual(pid_view.zone_problems({}), [])

    def test_only_red_at_the_top_or_the_bottom_is_fine(self):
        self.assertEqual(pid_view.zone_problems({'redline': 6500.0}), [])
        self.assertEqual(pid_view.zone_problems({'red_low': 10.0}), [])
        self.assertEqual(pid_view.zone_problems({'red_low': 10.0, 'redline': 6500.0}), [])
        self.assertEqual(pid_view.zone_problems({'warn': 90.0}), [])
        self.assertEqual(pid_view.zone_problems({'good_to': 60.0}), [])
        self.assertEqual(pid_view.zone_problems({'cold': 40.0, 'redline': 100.0}), [])

    def test_the_old_editor_rules_still_hold(self):
        self.assertEqual(len(pid_view.zone_problems({'cold': 80.0, 'good': 70.0})), 1)
        self.assertEqual(len(pid_view.zone_problems({'good': 100.0, 'redline': 100.0})), 1)
        self.assertEqual(pid_view.zone_problems({'cold': 70.0, 'good': 70.0, 'redline': 100.0}), [])

    def test_red_low_must_be_below_warn_low(self):
        problems = pid_view.zone_problems({'red_low': 20.0, 'warn_low': 20.0})
        self.assertEqual(len(problems), 1)
        self.assertIn('Red at or below', problems[0])
        self.assertIn('Yellow at or below', problems[0])
        self.assertEqual(len(pid_view.zone_problems({'red_low': 30.0, 'warn_low': 20.0})), 1)

    def test_warn_must_be_below_redline(self):
        problems = pid_view.zone_problems({'warn': 100.0, 'redline': 90.0})
        self.assertEqual(len(problems), 1)
        self.assertIn('Yellow from', problems[0])
        self.assertEqual(len(pid_view.zone_problems({'warn': 90.0, 'redline': 90.0})), 1)

    def test_good_to_must_not_be_below_good(self):
        self.assertEqual(len(pid_view.zone_problems({'good': 60.0, 'good_to': 50.0})), 1)
        self.assertEqual(pid_view.zone_problems({'good': 60.0, 'good_to': 60.0}), [])

    def test_the_low_side_must_stay_below_the_high_side(self):
        self.assertEqual(len(pid_view.zone_problems({'warn_low': 90.0, 'warn': 80.0})), 1)
        self.assertEqual(len(pid_view.zone_problems({'red_low': 120.0, 'redline': 100.0})), 1)

    def test_several_problems_are_all_listed_as_plain_sentences(self):
        problems = pid_view.zone_problems({'red_low': 30.0, 'warn_low': 20.0, 'warn': 100.0, 'redline': 90.0,
                                           'good': 50.0, 'good_to': 40.0})
        self.assertEqual(len(problems), 3)
        for text in problems:
            self.assertTrue(text.endswith('.') and text[0].isupper(), text)

    def test_missing_or_junk_values_are_not_problems(self):
        self.assertEqual(pid_view.zone_problems({'red_low': None, 'warn_low': 'x', 'redline': float('nan')}), [])
        self.assertEqual(pid_view.zone_problems(None), [])


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.views = pid_view.PidViews(os.path.join(self.folder.name, 'v.json'))
        self.temp = next(p for p in pids.CATALOG.values() if p.unit == '°C')

    def test_new_limits_are_saved_in_the_sensors_unit_and_shown_in_the_chosen_one(self):
        saved = dict(red_low=-10.0, warn_low=0.0, good=60.0, good_to=100.0, warn=110.0, redline=120.0, color='#FF8800')
        self.views.update(self.temp.pid, **saved)
        self.views.set_units({'temperature': '°F'})
        shown = self.views.apply(self.temp)
        for key in ('red_low', 'warn_low', 'good', 'good_to', 'warn', 'redline'):
            self.assertAlmostEqual(shown[key], saved[key] * 1.8 + 32, msg=key)
            self.assertAlmostEqual(shown['back'](shown[key]), saved[key], msg=key)
        self.assertEqual(shown['color'], '#FF8800')
        self.assertEqual(self.views.get(self.temp.pid), saved)
        self.views.set_units({'temperature': '°C'})
        self.assertAlmostEqual(self.views.apply(self.temp)['warn'], 110.0)

    def test_the_zone_of_a_converted_reading_matches_the_zone_of_the_raw_one(self):
        self.views.update(self.temp.pid, warn=100.0, redline=110.0, red_low=0.0)
        self.views.set_units({'temperature': '°F'})
        shown = self.views.apply(self.temp)
        for raw in (-5, 0, 50, 99, 100, 109, 110, 130):
            self.assertEqual(pid_view.zone(shown['convert'](raw), shown),
                             pid_view.zone(raw, {'warn': 100.0, 'redline': 110.0, 'red_low': 0.0}), raw)

    def test_they_survive_a_restart_and_none_removes_them(self):
        self.views.update(self.temp.pid, red_low=5.0, color='#00FFFF')
        again = pid_view.PidViews(self.views.path)
        self.assertEqual(again.get(self.temp.pid), {'red_low': 5.0, 'color': '#00FFFF'})
        again.update(self.temp.pid, red_low=None, color=None)
        self.assertEqual(again.get(self.temp.pid), {})

    def test_an_old_file_with_junk_in_the_new_keys_still_loads(self):
        self.views.path.write_text(json.dumps({self.temp.pid: {'color': 'blue', 'warn': 'x', 'redline': 5}}))
        self.assertEqual(pid_view.PidViews(self.views.path).get(self.temp.pid), {'redline': 5.0})


if __name__ == '__main__':
    unittest.main()
