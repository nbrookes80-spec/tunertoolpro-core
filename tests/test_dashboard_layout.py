import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro import prefs  # noqa: E402
from tunertoolpro.scanner import dashboard_layout as layout  # noqa: E402
from tunertoolpro.scanner import pids  # noqa: E402


def pid(code):
    found = pids.get(code)
    assert found is not None, code
    return found


class GroupTests(unittest.TestCase):
    def test_engine_sensors_are_ecu(self):
        for code in ('010C', '0105', '010E', '0143'):
            self.assertEqual(layout.group_of(pid(code)), 'ECU', code)

    def test_transmission_sensors_are_tcm(self):
        for code in ('221940', '22199A', '221941'):
            self.assertEqual(layout.group_of(pid(code)), 'TCM', code)

    def test_boost_sensors_are_boost(self):
        for code in ('010B', '01BB'):
            self.assertEqual(layout.group_of(pid(code)), 'Boost', code)

    def test_intake_and_throttle_sensors_are_air(self):
        for code in ('010F', '0110', '0133', '0111'):
            self.assertEqual(layout.group_of(pid(code)), 'Air', code)

    def test_fuel_sensors_are_fuel(self):
        for code in ('0106', '012F'):
            self.assertEqual(layout.group_of(pid(code)), 'Fuel', code)


class ArrangeTests(unittest.TestCase):
    def test_groups_come_in_the_fixed_order(self):
        mixed = [pid(c) for c in ('010C', '221940', '0106', '010B', '010F')]
        self.assertEqual([p.pid for p in layout.arrange(mixed, order=[])],
                         ['221940', '010C', '0106', '010F', '010B'])

    def test_the_user_order_holds_inside_a_group(self):
        ecu = [pid(c) for c in ('010C', '0105')]
        self.assertEqual([p.pid for p in layout.arrange(ecu, order=['0105', '010C'])], ['0105', '010C'])

    def test_sensors_the_order_does_not_mention_follow_the_listed_ones(self):
        ecu = [pid(c) for c in ('0105', '010C')]
        self.assertEqual([p.pid for p in layout.arrange(ecu, order=['010C'])], ['010C', '0105'])


class PageTests(unittest.TestCase):
    def sizes(self, count, size):
        return [len(p) for p in layout.pages(list(range(count)), size)]

    def test_pages_hold_four_five_or_six(self):
        self.assertEqual(self.sizes(13, 4), [4, 4, 4, 1])
        self.assertEqual(self.sizes(13, 5), [5, 5, 3])
        self.assertEqual(self.sizes(13, 6), [6, 6, 1])

    def test_any_other_size_falls_back_to_four(self):
        self.assertEqual(self.sizes(9, 7), [4, 4, 1])

    def test_an_empty_list_has_no_pages(self):
        self.assertEqual(layout.pages([]), [])

    def test_the_configured_size_is_used_when_none_is_given(self):
        try:
            layout.configure([], 6)
            self.assertEqual(self.sizes(13, None), [6, 6, 1])
        finally:
            layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def test_runs_keep_each_group_together_in_order(self):
        seq = [pid(c) for c in ('221940', '010C', '0105', '010F')]
        self.assertEqual([(g, [p.pid for p in members]) for g, members in layout.runs(seq)],
                         [('TCM', ['221940']), ('ECU', ['010C', '0105']), ('Air', ['010F'])])


class SavedOrderTests(unittest.TestCase):
    def test_a_saved_order_keeps_only_valid_unique_ids(self):
        self.assertEqual(layout.clean_order(['010c', 'zz', '010C', '22199a', 5]), ['010C', '22199A'])

    def test_a_damaged_order_is_empty(self):
        self.assertEqual(layout.clean_order('010C'), [])


class PrefsTests(unittest.TestCase):
    def round_trip(self, **changes):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prefs.json'
            choices = dict(prefs.DEFAULTS, **changes)
            prefs.save(path, choices)
            return prefs.load(path)

    def test_page_size_and_order_are_kept(self):
        saved = self.round_trip(dash_page_size=5, dash_order=['010C', '221940'])
        self.assertEqual(saved['dash_page_size'], 5)
        self.assertEqual(saved['dash_order'], ['010C', '221940'])

    def test_a_page_size_outside_four_to_six_is_replaced(self):
        self.assertEqual(self.round_trip(dash_page_size=9)['dash_page_size'], layout.DEFAULT_PAGE_SIZE)


IDS = ['221940', '22199A', '221941', '010C', '0105', '010E', '0143', '0106', '010F']   # TCM x3, ECU x4, Fuel, Air


def group(pid_id):
    return layout.group_of(pid(pid_id))


class MoveTests(unittest.TestCase):
    def assertSame(self, before, after):
        self.assertEqual(sorted(before), sorted(after))      # nothing lost, nothing duplicated
        self.assertEqual(len(after), len(set(after)))

    def test_move_earlier_and_later_swap_one_place(self):
        self.assertEqual(layout.move(['A', 'B', 'C'], 'B', -1), ['B', 'A', 'C'])
        self.assertEqual(layout.move(['A', 'B', 'C'], 'B', 1), ['A', 'C', 'B'])

    def test_it_returns_a_new_list_and_leaves_the_old_one_alone(self):
        before = ['A', 'B', 'C']
        after = layout.move(before, 'B', 1)
        self.assertEqual(before, ['A', 'B', 'C'])
        self.assertIsNot(after, before)

    def test_the_edges_stop_the_move(self):
        self.assertEqual(layout.move(['A', 'B', 'C'], 'A', -1), ['A', 'B', 'C'])
        self.assertEqual(layout.move(['A', 'B', 'C'], 'C', 1), ['A', 'B', 'C'])
        self.assertEqual(layout.move(['A', 'B', 'C'], 'A', -5), ['A', 'B', 'C'])

    def test_a_bigger_step_goes_that_far_and_no_further(self):
        self.assertEqual(layout.move(['A', 'B', 'C', 'D'], 'A', 2), ['B', 'C', 'A', 'D'])
        self.assertEqual(layout.move(['A', 'B', 'C', 'D'], 'A', 9), ['B', 'C', 'D', 'A'])

    def test_an_unknown_id_or_no_step_changes_nothing(self):
        self.assertEqual(layout.move(['A', 'B'], 'Z', 1), ['A', 'B'])
        self.assertEqual(layout.move(['A', 'B'], 'A', 0), ['A', 'B'])
        self.assertEqual(layout.move([], 'A', 1), [])

    def test_ids_are_kept_for_every_start_and_step(self):
        for start in IDS:
            for step in (-12, -1, 1, 3, 12):
                self.assertSame(IDS, layout.move(IDS, start, step))

    def test_within_its_group_a_sensor_steps_over_the_other_groups(self):
        # the last TCM sensor, one later: the next TCM sensor does not exist, so nothing moves
        self.assertEqual(layout.move(IDS, '221941', 1, group=group), IDS)
        # an ECU sensor moves past ECU neighbours only
        moved = layout.move(IDS, '010E', -1, group=group)
        self.assertEqual(moved[3:7], ['010C', '010E', '0105', '0143'])
        self.assertEqual(moved[:3], IDS[:3])
        self.assertEqual(moved[7:], IDS[7:])

    def test_a_group_of_one_cannot_move(self):
        self.assertEqual(layout.move(IDS, '0106', -1, group=group), IDS)
        self.assertEqual(layout.move(IDS, '0106', 1, group=group), IDS)


class MoveToEdgeTests(unittest.TestCase):
    def test_top_and_end(self):
        self.assertEqual(layout.move_to_edge(['A', 'B', 'C'], 'C', 'top'), ['C', 'A', 'B'])
        self.assertEqual(layout.move_to_edge(['A', 'B', 'C'], 'A', 'end'), ['B', 'C', 'A'])

    def test_already_there_changes_nothing(self):
        self.assertEqual(layout.move_to_edge(['A', 'B', 'C'], 'A', 'top'), ['A', 'B', 'C'])
        self.assertEqual(layout.move_to_edge(['A', 'B', 'C'], 'C', 'end'), ['A', 'B', 'C'])

    def test_unknown_id_and_empty_list_change_nothing(self):
        self.assertEqual(layout.move_to_edge(['A', 'B'], 'Z', 'top'), ['A', 'B'])
        self.assertEqual(layout.move_to_edge([], 'A', 'end'), [])

    def test_an_edge_other_than_top_or_end_is_refused(self):
        with self.assertRaises(ValueError):
            layout.move_to_edge(['A', 'B'], 'A', 'middle')

    def test_returns_a_new_list(self):
        before = ['A', 'B', 'C']
        self.assertEqual(layout.move_to_edge(before, 'B', 'end'), ['A', 'C', 'B'])
        self.assertEqual(before, ['A', 'B', 'C'])

    def test_within_a_group_the_edge_is_the_edge_of_that_group(self):
        top = layout.move_to_edge(IDS, '0143', 'top', group=group)
        self.assertEqual(top[3:7], ['0143', '010C', '0105', '010E'])
        end = layout.move_to_edge(IDS, '010C', 'end', group=group)
        self.assertEqual(end[3:7], ['0105', '010E', '0143', '010C'])
        self.assertEqual(top[:3] + top[7:], IDS[:3] + IDS[7:])

    def test_ids_are_kept(self):
        for start in IDS:
            for edge in ('top', 'end'):
                for grouped in (None, group):
                    after = layout.move_to_edge(IDS, start, edge, group=grouped)
                    self.assertEqual(sorted(after), sorted(IDS))


class PositionTests(unittest.TestCase):
    def test_page_and_place_for_each_page_size(self):
        order = [str(n) for n in range(13)]
        self.assertEqual(layout.position(order, '0', 4), (0, 0))
        self.assertEqual(layout.position(order, '5', 4), (1, 1))
        self.assertEqual(layout.position(order, '12', 4), (3, 0))
        self.assertEqual(layout.position(order, '5', 5), (1, 0))
        self.assertEqual(layout.position(order, '12', 5), (2, 2))
        self.assertEqual(layout.position(order, '11', 6), (1, 5))
        self.assertEqual(layout.position(order, '12', 6), (2, 0))

    def test_the_configured_size_is_used_when_none_is_given(self):
        order = [str(n) for n in range(13)]
        try:
            layout.configure([], 6)
            self.assertEqual(layout.position(order, '7'), (1, 1))
        finally:
            layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def test_an_unknown_id_has_no_position(self):
        self.assertIsNone(layout.position(['A'], 'Z', 4))

    def test_it_agrees_with_pages(self):
        order = [str(n) for n in range(13)]
        for size in layout.PAGE_SIZES:
            for index, page in enumerate(layout.pages(order, size)):
                for place, item in enumerate(page):
                    self.assertEqual(layout.position(order, item, size), (index, place))


class MoveToPageTests(unittest.TestCase):
    ORDER = [str(n) for n in range(13)]

    def test_without_groups_the_sensor_goes_to_the_end_of_the_page(self):
        after = layout.move_to_page(self.ORDER, '0', 1, 4)
        self.assertEqual(layout.position(after, '0', 4), (1, 3))
        self.assertEqual(after[:3], ['1', '2', '3'])         # the first page closes up
        self.assertEqual(sorted(after), sorted(self.ORDER))

    def test_moving_to_an_earlier_page_works_too(self):
        after = layout.move_to_page(self.ORDER, '9', 0, 4)
        self.assertEqual(layout.position(after, '9', 4), (0, 3))
        self.assertEqual(after[:4], ['0', '1', '2', '9'])

    def test_page_maths_for_every_size(self):
        for size in layout.PAGE_SIZES:
            count = len(layout.pages(self.ORDER, size))
            for page in range(count):
                after = layout.move_to_page(self.ORDER, '0', page, size)
                self.assertEqual(sorted(after), sorted(self.ORDER))
                self.assertEqual(layout.position(after, '0', size)[0], page)
                last = min((page + 1) * size, len(self.ORDER)) - 1     # the last slot of that page
                self.assertEqual(after.index('0'), last)

    def test_the_short_last_page_takes_the_sensor_at_the_end(self):
        after = layout.move_to_page(self.ORDER, '0', 3, 4)       # page 4 holds only '12'
        self.assertEqual(after[-1], '0')

    def test_a_page_that_does_not_exist_changes_nothing(self):
        self.assertEqual(layout.move_to_page(self.ORDER, '0', 9, 4), self.ORDER)
        self.assertEqual(layout.move_to_page(self.ORDER, '0', -1, 4), self.ORDER)

    def test_an_unknown_id_changes_nothing(self):
        self.assertEqual(layout.move_to_page(self.ORDER, 'Z', 1, 4), self.ORDER)

    def test_returns_a_new_list(self):
        before = list(self.ORDER)
        layout.move_to_page(before, '0', 1, 4)
        self.assertEqual(before, self.ORDER)

    def test_with_groups_it_lands_in_the_last_slot_of_its_own_group_on_that_page(self):
        # IDS arranged: TCM TCM TCM | ECU ECU ECU ECU | Fuel | Air, in pages of 4:
        #   page 0: 221940 22199A 221941 010C   page 1: 0105 010E 0143 0106   page 2: 010F
        after = layout.move_to_page(IDS, '010C', 1, 4, group=group)
        self.assertEqual(after[3:7], ['0105', '010E', '0143', '010C'])      # the ECU run ends at slot 6
        self.assertEqual(layout.position(after, '010C', 4)[0], 1)
        self.assertEqual(after[:3] + after[7:], IDS[:3] + IDS[7:])

    def test_with_groups_a_page_with_none_of_its_group_changes_nothing(self):
        # the TCM sensors are all on page 0; page 2 holds only the Air sensor
        self.assertEqual(layout.move_to_page(IDS, '221940', 2, 4, group=group), IDS)
        self.assertEqual(layout.move_to_page(IDS, '221940', 1, 4, group=group), IDS)

    def test_with_groups_a_page_that_ends_before_its_group_does(self):
        # size 4, ECU run is slots 3-6: page 0 covers slot 3 only, so the sensor lands in slot 3
        after = layout.move_to_page(IDS, '0143', 0, 4, group=group)
        self.assertEqual(after[3], '0143')
        self.assertEqual(after[4:7], ['010C', '0105', '010E'])

    def test_which_pages_a_sensor_can_reach(self):
        self.assertEqual(layout.reachable_pages(IDS, '221940', 4, group=group), [0])
        self.assertEqual(layout.reachable_pages(IDS, '010C', 4, group=group), [0, 1])
        self.assertEqual(layout.reachable_pages(IDS, '010F', 4, group=group), [2])
        self.assertEqual(layout.reachable_pages(self_order(), '3', 4), [0, 1, 2, 3])
        self.assertEqual(layout.reachable_pages(IDS, 'ZZ', 4), [])

    def test_a_reachable_page_is_one_the_move_actually_reaches(self):
        for size in layout.PAGE_SIZES:
            for start in IDS:
                for page in layout.reachable_pages(IDS, start, size, group=group):
                    after = layout.move_to_page(IDS, start, page, size, group=group)
                    self.assertEqual(layout.position(after, start, size)[0], page)
                    self.assertEqual(sorted(after), sorted(IDS))


def self_order():
    return [str(n) for n in range(13)]


class ReorderTests(unittest.TestCase):
    def test_each_action_stays_inside_the_sensors_group(self):
        self.assertEqual(layout.reorder(IDS, '010C', 'later')[3:7], ['0105', '010C', '010E', '0143'])
        self.assertEqual(layout.reorder(IDS, '0143', 'earlier')[3:7], ['010C', '0105', '0143', '010E'])
        self.assertEqual(layout.reorder(IDS, '0143', 'top')[3:7], ['0143', '010C', '0105', '010E'])
        self.assertEqual(layout.reorder(IDS, '010C', 'end')[3:7], ['0105', '010E', '0143', '010C'])
        self.assertEqual(layout.reorder(IDS, '010C', 'page', 1, 4)[3:7], ['0105', '010E', '0143', '010C'])

    def test_a_move_that_cannot_happen_returns_the_same_order(self):
        self.assertEqual(layout.reorder(IDS, '221940', 'earlier'), IDS)
        self.assertEqual(layout.reorder(IDS, '0106', 'end'), IDS)
        self.assertEqual(layout.reorder(IDS, '221940', 'page', 2, 4), IDS)

    def test_an_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            layout.reorder(IDS, '010C', 'sideways')

    def test_the_group_of_an_id(self):
        self.assertEqual(layout.group_of_id('221940'), 'TCM')
        self.assertEqual(layout.group_of_id('010B'), 'Boost')
        self.assertEqual(layout.group_of_id('01FF'), 'ECU')


class TwoScreensTests(unittest.TestCase):
    """The Live screen and the Scan pages show different sensor sets but share one saved order. A move on one
    screen must not reshuffle sensors nobody touched, on either screen."""

    @staticmethod
    def live_src():
        from tunertoolpro.live import STREAM_PIDS
        return list(STREAM_PIDS)

    @staticmethod
    def scan_src():
        return [p.pid for p in layout.dashboard_pids()]

    @staticmethod
    def arranged(source):
        return [p.pid for p in layout.arrange([pids.get(i) for i in source])]

    def setUp(self):
        layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def tearDown(self):
        layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def move(self, source, pid_id, action):
        """Move on the screen listing `source`, save like the app does; returns (old, new) arranged ids of it."""
        old = self.arranged(source)
        moved = layout.reorder(old, pid_id, action)
        layout.configure(layout.merged_order(layout.ORDER, moved, source), layout.PAGE_SIZE)
        return old, moved

    def test_the_sets_really_differ(self):
        live, scan = set(self.live_src()), set(self.scan_src())
        self.assertTrue(live - scan and scan - live and live & scan)

    def check_move(self, source, other_source, pid_id, action):
        other_old = self.arranged(other_source)
        old, moved = self.move(source, pid_id, action)
        label = f'{action} {pid_id}'
        self.assertEqual(self.arranged(source), moved, label)                 # where that screen's menu said
        other_new = self.arranged(other_source)
        group = layout.group_of_id(pid_id)
        # sensors of the other groups do not move at all, on the other screen
        self.assertEqual([i for i in other_new if layout.group_of_id(i) != group],
                         [i for i in other_old if layout.group_of_id(i) != group], label)
        # sensors only the other screen shows keep their order among themselves
        own = set(source)
        self.assertEqual([i for i in other_new if i not in own], [i for i in other_old if i not in own], label)
        # and so does every sensor the move did not list in the saved order
        listed = set(layout.ORDER)
        self.assertEqual([i for i in other_new if i not in listed and i != pid_id],
                         [i for i in other_old if i not in listed and i != pid_id], label)

    def test_any_move_on_live_leaves_the_untouched_sensors_alone_on_both_screens(self):
        for pid_id in self.arranged(self.live_src()):
            for action in ('earlier', 'later', 'top', 'end'):
                layout.configure([], layout.DEFAULT_PAGE_SIZE)
                self.check_move(self.live_src(), self.scan_src(), pid_id, action)

    def test_any_move_on_scan_leaves_the_untouched_sensors_alone_on_both_screens(self):
        for pid_id in self.arranged(self.scan_src()):
            for action in ('earlier', 'later', 'top', 'end'):
                layout.configure([], layout.DEFAULT_PAGE_SIZE)
                self.check_move(self.scan_src(), self.live_src(), pid_id, action)

    def test_one_place_earlier_on_live_changes_nothing_on_scan(self):
        # the reported case: Live and Scan list 0105, 010D and 010E in different orders by default
        before = self.arranged(self.scan_src())
        self.move(self.live_src(), '0105', 'earlier')
        self.assertEqual(self.arranged(self.scan_src()), before)
        self.assertEqual(self.arranged(self.live_src())[:3], ['22199A', '221991', '221941'])   # TCM untouched
        ecu = [i for i in self.arranged(self.live_src()) if layout.group_of_id(i) == 'ECU']
        self.assertEqual(ecu, ['010C', '0105', '010D', '0104', '010E'])

    def test_one_place_later_on_scan_does_not_touch_the_tcm_sensors_on_live(self):
        before = self.arranged(self.live_src())
        self.move(self.scan_src(), '010C', 'later')
        after = self.arranged(self.live_src())
        self.assertEqual([i for i in after if layout.group_of_id(i) == 'TCM'],
                         [i for i in before if layout.group_of_id(i) == 'TCM'])

    def test_moves_on_both_screens_in_turn_keep_what_each_said(self):
        self.move(self.live_src(), '010E', 'top')
        _, moved = self.move(self.scan_src(), '0103', 'top')
        self.assertEqual(self.arranged(self.scan_src()), moved)
        ecu_live = [i for i in self.arranged(self.live_src()) if layout.group_of_id(i) == 'ECU']
        self.assertEqual(ecu_live[0], '010E')               # the first move still holds on Live
        ecu_scan = [i for i in self.arranged(self.scan_src()) if layout.group_of_id(i) == 'ECU']
        self.assertEqual(ecu_scan[:2], ['0103', '010E'])

    def test_ids_saved_earlier_that_neither_screen_shows_are_kept(self):
        layout.configure(['0143', '01FF'], 4)
        live = self.arranged(self.live_src())
        moved = layout.reorder(live, live[0], 'later')
        merged = layout.merged_order(layout.ORDER, moved, self.live_src())
        self.assertIn('01FF', merged)
        self.assertEqual(len(merged), len(set(merged)))
        self.assertEqual(layout._arranged_ids(self.live_src(), merged), moved)

    def test_no_move_saves_the_same_order(self):
        live = self.arranged(self.live_src())
        self.assertEqual(layout.merged_order([], live, self.live_src()), [])


class MenuMeetsArrangeTests(unittest.TestCase):
    """What the menu says is where the sensor ends up once `arrange` has sorted by group and saved order."""

    def setUp(self):
        self.pids = [pid(c) for c in IDS]
        layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def tearDown(self):
        layout.configure([], layout.DEFAULT_PAGE_SIZE)

    def arranged_ids(self):
        return [p.pid for p in layout.arrange(self.pids)]

    def save(self, moved):
        layout.configure(layout.merged_order(layout.ORDER, moved, IDS), layout.PAGE_SIZE)

    def test_move_later_shows_up_after_arrange(self):
        before = self.arranged_ids()
        self.save(layout.move(before, '010C', 1, group=group))
        self.assertEqual(self.arranged_ids()[3:7], ['0105', '010C', '010E', '0143'])

    def test_move_to_top_and_end_show_up_after_arrange(self):
        self.save(layout.move_to_edge(self.arranged_ids(), '0143', 'top', group=group))
        self.assertEqual(self.arranged_ids()[3], '0143')
        self.save(layout.move_to_edge(self.arranged_ids(), '0143', 'end', group=group))
        self.assertEqual(self.arranged_ids()[6], '0143')

    def test_move_to_page_shows_up_on_that_page(self):
        self.save(layout.move_to_page(self.arranged_ids(), '010C', 1, 4, group=group))
        pages = layout.pages(layout.arrange(self.pids), 4)
        self.assertEqual([p.pid for p in pages[1]], ['010E', '0143', '010C', '0106'])
        self.assertEqual([p.pid for p in pages[0]], ['221940', '22199A', '221941', '0105'])

    def test_a_move_without_the_group_rule_would_be_undone_by_arrange(self):
        # this is why the app passes the group: moving a TCM sensor past an ECU one means nothing
        before = self.arranged_ids()
        self.save(layout.move(before, '221941', 1))
        self.assertEqual(self.arranged_ids(), before)

    def test_the_saved_order_keeps_sensors_that_were_not_on_the_screen(self):
        layout.configure(['0143', '010C'], 4)
        shown = ['0105', '010C']                      # the user put 0105 ahead of 010C; the screen listed 0105 first
        merged = layout.merged_order(layout.ORDER, shown, ['0105', '010C'])
        self.assertEqual(merged, ['0105', '0143', '010C'])   # 0143, which the screen does not show, keeps its place
        self.assertEqual(layout._arranged_ids(['0105', '010C'], merged), shown)

    def test_a_merged_order_survives_the_settings_file(self):
        moved = layout.move(self.arranged_ids(), '010C', 1, group=group)
        merged = layout.merged_order([], moved, IDS)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prefs.json'
            prefs.save(path, dict(prefs.DEFAULTS, dash_order=merged))
            self.assertEqual(prefs.load(path)['dash_order'], merged)


if __name__ == '__main__':
    unittest.main()
