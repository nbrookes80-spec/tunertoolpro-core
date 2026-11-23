import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro import prefs  # noqa: E402
from tunertoolpro.scanner import page_layout as pl  # noqa: E402

EPS = 1e-9
ASPECTS = (0.5, 0.75, 1.0, 1.6, 2.2)      # a tall phone, a square, a phone on its side, a very wide screen


def overlap(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)


def supported(template_id):
    spec = pl.TEMPLATES[template_id]
    return range(spec['min'], spec['max'] + 1)


class TemplateTableTests(unittest.TestCase):
    def test_the_required_templates_exist_in_order_with_names_and_counts(self):
        self.assertEqual(list(pl.TEMPLATES)[:6], ['grid', 'columns2', 'hero', 'hero_top', 'rows', 'dials'])
        for spec in pl.TEMPLATES.values():
            self.assertTrue(spec['name'])
            self.assertLessEqual(1, spec['min'])
            self.assertLessEqual(spec['min'], spec['max'])

    def test_every_template_supports_the_page_sizes_the_app_offers(self):
        for template_id, spec in pl.TEMPLATES.items():
            if template_id in ('hero', 'hero_top', 'columns2'):
                self.assertEqual(spec['min'], 2, template_id)    # one sensor on its own is just a full page
            for count in (4, 5, 6):
                self.assertTrue(pl.supports(template_id, count), f'{template_id} {count}')

    def test_supports_is_false_for_unknown_ids_and_out_of_range_counts(self):
        self.assertFalse(pl.supports('nope', 4))
        self.assertFalse(pl.supports('hero', 1))
        self.assertFalse(pl.supports('rows', pl.TEMPLATES['rows']['max'] + 1))
        self.assertFalse(pl.supports(None, 4))


class SlotTests(unittest.TestCase):
    def test_every_template_at_every_supported_count_tiles_the_unit_square(self):
        for template_id in pl.TEMPLATES:
            for count in supported(template_id):
                for aspect in ASPECTS:
                    where = f'{template_id} x{count} aspect {aspect}'
                    rects = pl.slots(template_id, count, aspect=aspect)
                    self.assertEqual(len(rects), count, where)
                    self.assertAlmostEqual(sum(w * h for _x, _y, w, h in rects), 1.0, delta=EPS, msg=where)
                    for x, y, w, h in rects:
                        self.assertGreater(w, 0.05, where)           # no sliver of a cell
                        self.assertGreater(h, 0.05, where)
                        self.assertGreaterEqual(x, -EPS, where)
                        self.assertGreaterEqual(y, -EPS, where)
                        self.assertLessEqual(x + w, 1 + EPS, where)
                        self.assertLessEqual(y + h, 1 + EPS, where)
                    for i, a in enumerate(rects):
                        for b in rects[i + 1:]:
                            self.assertLess(overlap(a, b), EPS, where)

    def test_the_aspect_is_optional(self):
        self.assertEqual(pl.slots('grid', 4), pl.slots('grid', 4, aspect=None))

    def test_sensor_order_runs_left_to_right_then_down_in_a_grid(self):
        rects = pl.slots('grid', 4, aspect=1.6)
        self.assertEqual([(x, y) for x, y, _w, _h in rects], [(0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)])

    def test_the_first_sensor_is_the_biggest_in_the_hero_layouts(self):
        for template_id in ('hero', 'hero_top'):
            for count in (3, 4, 5, 6):
                rects = pl.slots(template_id, count)
                areas = [w * h for _x, _y, w, h in rects]
                self.assertEqual(areas[0], max(areas), f'{template_id} x{count}')
                self.assertGreater(areas[0], areas[1] * 1.5, f'{template_id} x{count}')
        left = pl.slots('hero', 5)
        self.assertEqual(left[0][:2], (0, 0))
        self.assertTrue(all(x > 0 for x, _y, _w, _h in left[1:]))   # the rest stack on the right
        top = pl.slots('hero_top', 5)
        self.assertEqual((top[0][0], top[0][1], top[0][2]), (0, 0, 1))   # one wide sensor on top
        self.assertTrue(all(y > 0 for _x, y, _w, _h in top[1:]))

    def test_rows_are_full_width_and_equal(self):
        rects = pl.slots('rows', 5)
        self.assertEqual([r[2] for r in rects], [1] * 5)
        self.assertEqual(len({round(r[3], 9) for r in rects}), 1)

    def test_two_columns_fill_the_left_column_first(self):
        rects = pl.slots('columns2', 5)
        self.assertEqual([x for x, *_ in rects], [0, 0, 0, 0.5, 0.5])

    def test_dials_pick_the_columns_that_make_cells_closest_to_square(self):
        def off_square(cols, count, aspect):
            return abs(math.log(aspect * (-(-count // cols)) / cols))   # how far a full cell is from square
        for aspect in (0.6, 1.0, 1.8, 2.4):
            for count in (4, 5, 6):
                _x, _y, w, h = pl.slots('dials', count, aspect=aspect)[0]       # the first cell is always a full one
                chosen = abs(math.log(w * aspect / h))
                best = min(off_square(cols, count, aspect) for cols in range(1, count + 1))
                self.assertAlmostEqual(chosen, best, delta=1e-9, msg=f'{count} dials, aspect {aspect}')

    def test_a_wide_page_puts_dials_in_a_row_and_a_tall_page_in_a_column(self):
        self.assertEqual(len({r[1] for r in pl.slots('dials', 4, aspect=4.0)}), 1)
        self.assertEqual(len({r[0] for r in pl.slots('dials', 4, aspect=0.25)}), 1)


class FallbackTests(unittest.TestCase):
    def test_an_unknown_id_gives_the_grid(self):
        self.assertEqual(pl.slots('nope', 4), pl.slots('grid', 4))
        self.assertEqual(pl.slots(None, 5), pl.slots('grid', 5))
        self.assertEqual(pl.slots(['hero'], 5), pl.slots('grid', 5))

    def test_an_unsupported_count_gives_the_grid(self):
        self.assertEqual(pl.slots('hero', 1), pl.slots('grid', 1))
        too_many = pl.TEMPLATES['rows']['max'] + 1
        self.assertEqual(pl.slots('rows', too_many), pl.slots('grid', too_many))

    def test_the_grid_copes_with_one_sensor_and_with_none(self):
        self.assertEqual(pl.slots('grid', 1), [(0, 0, 1, 1)])
        self.assertEqual(pl.slots('grid', 0), [])
        self.assertEqual(pl.slots('hero', 0), [])
        self.assertEqual(pl.slots('grid', -3), [])

    def test_a_grid_of_more_sensors_than_it_declares_still_tiles(self):
        rects = pl.slots('grid', 15, aspect=1.6)
        self.assertEqual(len(rects), 15)
        self.assertAlmostEqual(sum(w * h for _x, _y, w, h in rects), 1.0, delta=EPS)


class DetailTests(unittest.TestCase):
    """How much a sensor card shows in a cell of a given height (the sizes below are dp-like numbers)."""
    SIZES = dict(name=26, reading=40, stats=16, gauge=24, pad=8, spacing=2)

    def detail(self, height):
        return pl.detail_for(height, **self.SIZES)

    def test_a_tall_cell_shows_everything(self):
        self.assertEqual(self.detail(200), 'full')

    def test_the_lowest_highest_line_goes_first_then_the_picture_then_the_stacking(self):
        # name and number need 2*8 + 26 + 40 + 2 = 84; the picture needs 24 + 2 more, the stats line 16 + 2 more
        self.assertEqual(self.detail(130), 'full')
        self.assertEqual(self.detail(120), 'no_stats')
        self.assertEqual(self.detail(90), 'no_gauge')
        self.assertEqual(self.detail(60), 'line')

    def test_the_thresholds_are_exact(self):
        self.assertEqual(self.detail(84), 'no_gauge')
        self.assertEqual(self.detail(83.9), 'line')
        self.assertEqual(self.detail(110), 'no_stats')
        self.assertEqual(self.detail(109.9), 'no_gauge')
        self.assertEqual(self.detail(128), 'full')
        self.assertEqual(self.detail(127.9), 'no_stats')

    def test_a_taller_cell_never_shows_less(self):
        order = ['line', 'no_gauge', 'no_stats', 'full']
        ranks = [order.index(self.detail(h)) for h in range(0, 300)]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual({order[r] for r in ranks}, set(order))

    def test_a_card_with_no_stats_line_needs_no_room_for_it(self):
        self.assertEqual(pl.detail_for(112, **dict(self.SIZES, stats=0)), 'full')


class SavedDataTests(unittest.TestCase):
    def test_clean_choice_keeps_a_known_id_and_defaults_the_rest(self):
        self.assertEqual(pl.DEFAULT, 'grid')
        for template_id in pl.TEMPLATES:
            self.assertEqual(pl.clean_choice(template_id), template_id)
        for junk in ('nope', '', None, 3, True, ['hero'], {'hero': 1}, 'HERO'):
            self.assertEqual(pl.clean_choice(junk), 'grid', repr(junk))

    def test_clean_per_page_keeps_only_valid_pairs_with_plain_number_keys(self):
        raw = {'0': 'hero', '2': 'rows', '7': 'nope', 'x': 'hero', '-1': 'hero', 3: 'dials', '04': 'columns2',
               '': 'hero', '1': 5, True: 'hero'}
        self.assertEqual(pl.clean_per_page(raw), {'0': 'hero', '2': 'rows', '3': 'dials', '4': 'columns2'})

    def test_clean_per_page_survives_junk_and_is_bounded(self):
        for junk in (None, [], 'hero', 5, [('0', 'hero')]):
            self.assertEqual(pl.clean_per_page(junk), {})
        many = {str(i): 'rows' for i in range(500)}
        self.assertLessEqual(len(pl.clean_per_page(many)), 100)

    def test_template_for_page_prefers_the_pages_own_choice(self):
        per_page = {'1': 'hero', '2': 'nope'}
        self.assertEqual(pl.template_for_page('rows', per_page, 1), 'hero')
        self.assertEqual(pl.template_for_page('rows', per_page, 0), 'rows')
        self.assertEqual(pl.template_for_page('rows', per_page, 2), 'rows')       # a bad saved choice is ignored
        self.assertEqual(pl.template_for_page('nope', per_page, 0), 'grid')
        self.assertEqual(pl.template_for_page('rows', None, 0), 'rows')

    def test_apply_to_this_page_leaves_the_others_alone(self):
        default, per_page = pl.apply_to_page('rows', {'0': 'hero'}, 2, 'dials')
        self.assertEqual((default, per_page), ('rows', {'0': 'hero', '2': 'dials'}))

    def test_apply_to_all_pages_sets_the_default_and_drops_the_page_choices(self):
        self.assertEqual(pl.apply_to_all('dials'), ('dials', {}))
        self.assertEqual(pl.apply_to_all('nope'), ('grid', {}))

    def test_apply_does_not_change_the_dict_it_was_given(self):
        original = {'0': 'hero'}
        pl.apply_to_page('grid', original, 1, 'rows')
        self.assertEqual(original, {'0': 'hero'})

    def test_the_configured_choice_is_used_for_a_page(self):
        try:
            pl.configure('rows', {'1': 'hero'})
            self.assertEqual(pl.for_page(0), 'rows')
            self.assertEqual(pl.for_page(1), 'hero')
            self.assertEqual(pl.CHOSEN, 'rows')
            pl.configure('nope', 'junk')
            self.assertEqual(pl.for_page(1), 'grid')
        finally:
            pl.configure('grid', {})


class PixelTests(unittest.TestCase):
    def test_cells_are_placed_in_the_box_with_y_counted_up_from_the_bottom(self):
        cells = pl.to_pixels([(0, 0, 0.5, 1), (0.5, 0, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)], 10, 20, 200, 100)
        self.assertEqual(cells[0], (10, 20, 100, 100))           # the tall cell on the left fills the box's height
        self.assertEqual(cells[1], (110, 70, 100, 50))           # top right: its bottom edge is half way up
        self.assertEqual(cells[2], (110, 20, 100, 50))           # bottom right

    def test_a_gap_insets_each_cell_so_neighbours_are_a_gap_apart(self):
        cells = pl.to_pixels([(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)], 0, 0, 200, 100, gap=10)
        (x1, _y1, w1, _h1), (x2, _y2, _w2, _h2) = cells
        self.assertAlmostEqual(x2 - (x1 + w1), 10)
        self.assertEqual(cells[0][1:4:2], (5, 90))                # inset by half a gap on every side

    def test_a_gap_never_swallows_a_small_cell(self):
        cells = pl.to_pixels([(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)], 0, 0, 20, 20, gap=50)
        self.assertTrue(all(w >= 1 and h >= 1 for _x, _y, w, h in cells))


class PrefsTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / 'prefs.json'

    def test_the_defaults_are_the_grid_and_no_page_choices(self):
        loaded = prefs.load(self.path)
        self.assertEqual(loaded['dash_template'], 'grid')
        self.assertEqual(loaded['dash_page_templates'], {})
        self.assertEqual(prefs.DEFAULTS['dash_template'], 'grid')

    def test_the_choices_round_trip(self):
        prefs.save(self.path, dict(prefs.DEFAULTS, dash_template='rows', dash_page_templates={'1': 'hero'}))
        loaded = prefs.load(self.path)
        self.assertEqual(loaded['dash_template'], 'rows')
        self.assertEqual(loaded['dash_page_templates'], {'1': 'hero'})

    def test_an_old_file_without_the_keys_still_loads(self):
        self.path.write_text(json.dumps({'settings_version': prefs.SETTINGS_VERSION, 'dash_page_size': 5}))
        loaded = prefs.load(self.path)
        self.assertEqual((loaded['dash_page_size'], loaded['dash_template'], loaded['dash_page_templates']),
                         (5, 'grid', {}))

    def test_junk_in_the_file_is_cleaned(self):
        self.path.write_text(json.dumps({'settings_version': prefs.SETTINGS_VERSION, 'dash_template': 'cube',
                                         'dash_page_templates': {'0': 'hero', 'a': 'rows', '1': 'cube'}}))
        loaded = prefs.load(self.path)
        self.assertEqual(loaded['dash_template'], 'grid')
        self.assertEqual(loaded['dash_page_templates'], {'0': 'hero'})

    def test_saving_cleans_the_page_choices_too(self):
        prefs.save(self.path, dict(prefs.DEFAULTS, dash_page_templates={'0': 'hero', 'z': 'rows'}))
        self.assertEqual(json.loads(self.path.read_text())['dash_page_templates'], {'0': 'hero'})


if __name__ == '__main__':
    unittest.main()
