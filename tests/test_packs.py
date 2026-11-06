"""PID packs for other cars (Generic OBD-II, Toyota-style modules) and the opt-in for reading other modules.

The Toyota-style rows come from the owner's Torque CSV, which must be copied into data/torque_toyota_style.csv
before that pack appears. These tests use a small made-up file (TEST ONLY, not shipped) for the module rows."""

import json
import sys
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro import prefs  # noqa: E402
from tunertoolpro.link import obd  # noqa: E402
from tunertoolpro.link.testing import FakeElm327  # noqa: E402
from tunertoolpro.scanner import car_scan, pids, predefined, profiles, torque_csv  # noqa: E402
from tests.test_torque_csv import HEAD, row  # noqa: E402

DATA = ROOT / 'tunertoolpro' / 'data'
MODULE_HEADERS = ('7B0', '7C0', '7C4', '7E1')

# TEST ONLY: invented ids, to exercise the Mode 21 path. The real rows are the owner's Torque CSV.
TEST_TOYOTA = (HEAD
               + row('[TOY]Test ABS value', '0x2181', 'A-40', header='7B0', unit='C', lo='-40', hi='215')
               + row('[TOY]Test meter value', '0x2172', '((A*256)+B)/4', header='7C0', unit='rpm', hi='8000')
               + row('[TOY]Test A/C value', '0x2191', 'A*100/255', header='7C4', unit='%')
               + row('[TOY]Test other value', '0x2161', 'A', header='7E1')
               + row('[TOY]Standard coolant', '0x0105', 'A-40', unit='C', lo='-40', hi='215'))


def generic_pids():
    found, rejected = torque_csv.parse((DATA / 'torque_generic_obd2.csv').read_text(), source='generic')
    return {p.pid: p for p in found}, rejected


class GenericPackTests(unittest.TestCase):
    def test_every_row_loads_and_nothing_is_refused(self):
        found, rejected = generic_pids()
        self.assertEqual(rejected, [])
        self.assertEqual(len(found), 31)

    def test_the_pack_only_adds_readings_the_catalogue_lacks(self):
        found, _ = generic_pids()
        self.assertEqual(set(found) & set(pids.BUILT_IN), set())

    def test_every_row_is_a_mode_01_read_and_unconfirmed(self):
        found, _ = generic_pids()
        for pid in found.values():
            self.assertTrue(pid.pid.startswith('01'), pid.pid)
            self.assertFalse(pid.verified, pid.pid)
            self.assertEqual(pid.header, 'Auto', pid.pid)

    def test_decoded_values_match_the_j1979_equations(self):
        found, _ = generic_pids()
        # hand worked: (0x12*256 + 0x34) * 0.079 = 4660 * 0.079
        self.assertAlmostEqual(found['0122'].parse('1234'), 368.14, places=2)
        # lambda: (0x8000) * 2 / 65536 = 1.0 ; 0xC000 gives 1.5
        self.assertAlmostEqual(found['0124'].parse('8000'), 1.0)
        self.assertAlmostEqual(found['0124'].parse('C000'), 1.5)
        # catalyst B1S2: 0x0FA0 = 4000 -> 4000 / 10 - 40
        self.assertAlmostEqual(found['013E'].parse('0FA0'), 360.0)
        # wide range O2 current: C,D = 0x81,0x80 -> 33152 / 256 - 128
        self.assertAlmostEqual(found['0134'].parse('00008180'), 1.5)
        # secondary O2 trim: (A - 128) * 100 / 128
        self.assertAlmostEqual(found['0155'].parse('C0'), 50.0)
        self.assertAlmostEqual(found['0155'].parse('80'), 0.0)
        # EGR error: A * 100 / 128 - 100
        self.assertAlmostEqual(found['012D'].parse('00'), -100.0)
        self.assertAlmostEqual(found['012D'].parse('C0'), 50.0)
        # injection timing: 0x6B00 = 27392 -> 27392 / 128 - 210
        self.assertAlmostEqual(found['015D'].parse('6B00'), 4.0)
        # engine fuel rate (the same formula the Torque Pro source uses): 0x0140 = 320 -> * 0.05
        self.assertAlmostEqual(found['015E'].parse('0140'), 16.0)
        # fuel rail absolute pressure: 0x0064 = 100 -> * 10
        self.assertAlmostEqual(found['0159'].parse('0064'), 1000.0)
        # max air flow: A * 10
        self.assertAlmostEqual(found['0150'].parse('19'), 250.0)
        # time run with the MIL on: 0x0102 = 258 minutes
        self.assertAlmostEqual(found['014D'].parse('0102'), 258.0)

    def test_the_pack_is_listed_and_counted(self):
        item = predefined.by_key('generic-obd2')
        self.assertIsNotNone(item)
        self.assertEqual(predefined.count(item), 31)
        self.assertFalse(item.modules)

    def test_the_pack_text_round_trips_through_the_parser(self):
        found, rejected = torque_csv.parse(predefined.csv_text(predefined.by_key('generic-obd2')))
        self.assertEqual((len(found), rejected), (31, []))


def pack_pids(name, source):
    found, rejected = torque_csv.parse((DATA / name).read_text(encoding='utf-8'), source=source)
    return {p.pid: p for p in found}, rejected


class GenericMorePackTests(unittest.TestCase):
    """The standard Mode 01 readings of the Torque Pro sensor table that neither the catalogue nor the base generic
    pack had. Equations are the SAE J1979 ones, worked by hand below."""

    def test_every_row_loads_and_nothing_is_refused(self):
        found, rejected = pack_pids('torque_generic_obd2_more.csv', 'generic more')
        self.assertEqual(rejected, [])
        self.assertEqual(len(found), 14)

    def test_it_adds_nothing_the_catalogue_or_the_base_pack_already_has(self):
        found, _ = pack_pids('torque_generic_obd2_more.csv', 'generic more')
        base, _ = generic_pids()
        self.assertEqual(set(found) & (set(pids.BUILT_IN) | set(base)), set())

    def test_every_row_is_an_unconfirmed_mode_01_read_to_the_broadcast_address(self):
        found, _ = pack_pids('torque_generic_obd2_more.csv', 'generic more')
        for pid in found.values():
            self.assertTrue(pid.pid.startswith('01'), pid.pid)
            self.assertFalse(pid.verified, pid.pid)
            self.assertEqual(pid.header, 'Auto', pid.pid)

    def test_decoded_values_match_the_j1979_equations(self):
        found, _ = pack_pids('torque_generic_obd2_more.csv', 'generic more')
        self.assertAlmostEqual(found['0126'].parse('8000'), 1.0)             # lambda: 0x8000 * 2 / 65536
        self.assertAlmostEqual(found['012B'].parse('C000'), 1.5)
        self.assertAlmostEqual(found['0138'].parse('00008180'), 1.5)         # current: 0x8180 / 256 - 128
        self.assertAlmostEqual(found['013B'].parse('00008000'), 0.0)
        self.assertAlmostEqual(found['0161'].parse('7D'), 0.0)               # torque percent: A - 125
        self.assertAlmostEqual(found['0162'].parse('96'), 25.0)
        self.assertAlmostEqual(found['0163'].parse('0190'), 400.0)           # reference torque: 0x0190 Nm
        self.assertAlmostEqual(found['01A6'].parse('00030D40'), 20000.0)     # odometer: 200000 / 10 km

    def test_the_pack_is_listed_and_counted(self):
        item = predefined.by_key('generic-obd2-more')
        self.assertEqual((predefined.count(item), item.modules), (14, False))


class FordPackTests(unittest.TestCase):
    """Ford Mode 22 rows from the Torque Pro list. The build tool drops any row that names a module the app cannot
    address, because the reader would quietly send it to the broadcast address instead."""

    def test_every_row_loads_and_nothing_is_refused(self):
        found, rejected = pack_pids('torque_ford.csv', 'ford')
        self.assertEqual(rejected, [])
        self.assertEqual(len(found), 44)

    def test_every_row_is_an_unconfirmed_mode_01_or_22_read(self):
        found, _ = pack_pids('torque_ford.csv', 'ford')
        for pid in found.values():
            self.assertRegex(pid.pid, r'^(01[0-9A-F]{2}|22[0-9A-F]{4})$')
            self.assertFalse(pid.verified, pid.pid)
            self.assertIn(pid.header, ('Auto', '7E0', '7E2', '7E3'), pid.pid)

    def test_no_row_was_sent_to_the_wrong_module(self):
        text = (DATA / 'torque_ford.csv').read_text(encoding='utf-8')
        for word in ('"TCM"', '"ABS"', '"726"', '"C410F1"', '"INS"'):
            self.assertNotIn(word, text)

    def test_decoded_values_match_the_torque_equation(self):
        found, _ = pack_pids('torque_ford.csv', 'ford')
        # FICM main power: ((A*256)+B) * (100/256) / 100 volts; 0x0C00 = 3072 -> 12 V
        self.assertAlmostEqual(found['2209D0'].parse('0C00'), 12.0)

    def test_the_pack_is_listed_and_counted(self):
        item = predefined.by_key('ford')
        self.assertEqual((predefined.count(item), item.modules), (44, False))


class ReportExtrasPackTests(unittest.TestCase):
    """Six readings from the owner's E38/T43/FPCM engineering report that the app had nowhere else. Every one is a
    candidate: the report gives the equation, nobody has read it off the car. PIDs the app already holds under
    another meaning (221198, 221199 on the ECM, 221993, 221935, 221934, 22199B) are deliberately not here."""

    LEFT_OUT = ('221198', '221199', '221993', '221935', '221934', '22199B')

    def test_every_row_loads_and_nothing_is_refused(self):
        found, rejected = pack_pids('torque_gm_report_extras.csv', 'report extras')
        self.assertEqual(rejected, [])
        self.assertEqual(set(found), {'221471', '221938', '221939', '22153E', '22193E', '222006'})

    def test_all_unconfirmed_and_on_the_module_the_report_names(self):
        found, _ = pack_pids('torque_gm_report_extras.csv', 'report extras')
        for pid in found.values():
            self.assertFalse(pid.verified, pid.pid)
        self.assertEqual(found['221471'].header, '7E3')
        self.assertEqual({found[k].header for k in ('221938', '221939', '22193E')}, {'7E2'})
        self.assertEqual({found[k].header for k in ('22153E', '222006')}, {'7E0'})

    def test_no_pid_the_app_already_holds_under_another_meaning_is_added(self):
        text = (DATA / 'torque_gm_report_extras.csv').read_text(encoding='utf-8')
        for pid in self.LEFT_OUT:
            self.assertNotIn(pid, text)

    def test_decoded_values_match_the_report_equations(self):
        found, _ = pack_pids('torque_gm_report_extras.csv', 'report extras')
        self.assertAlmostEqual(found['222006'].parse('64'), 60.0)         # A - 40
        self.assertAlmostEqual(found['22153E'].parse('78'), 80.0)         # A - 40
        self.assertAlmostEqual(found['221471'].parse('FF'), 100.0, places=1)   # A * 0.392157
        self.assertAlmostEqual(found['221939'].parse('80'), 50.2, places=1)
        self.assertAlmostEqual(found['221938'].parse('1388'), 50.0)       # 5000 / 100
        self.assertAlmostEqual(found['22193E'].parse('01'), 1.0)

    def test_the_pack_is_listed_and_counted(self):
        item = predefined.by_key('gm-report-extras')
        self.assertEqual((predefined.count(item), item.modules), (6, False))


class ProfileTests(unittest.TestCase):
    def tearDown(self):
        pids.use_extras([])
        pids.MONITOR_PIDS[:] = pids.DEFAULT_MONITOR

    def test_generic_profile_is_listed_with_no_make_model_or_year(self):
        profile = next(p for p in profiles.built_in() if p.key == 'generic-obd2')
        self.assertEqual((profile.make, profile.years, profile.transmission), ('', '', ''))
        self.assertTrue(profile.mode01_only)
        self.assertFalse(profile.modules)
        self.assertTrue(profile.builtin)

    def test_selecting_it_shows_only_mode_01_readings_including_the_new_ones(self):
        profile = next(p for p in profiles.built_in() if p.key == 'generic-obd2')
        summary = profiles.activate(profile)
        self.assertEqual(summary['rejected'], [])
        self.assertEqual(summary['added'], 31)
        self.assertTrue(all(p.startswith('01') for p in pids.MONITOR_PIDS))
        self.assertIn('0122', pids.MONITOR_PIDS)
        self.assertIn('010C', pids.MONITOR_PIDS)
        self.assertFalse(any(p.startswith('22') for p in pids.MONITOR_PIDS))

    def test_the_gm_profiles_are_unchanged(self):
        profile = next(p for p in profiles.built_in() if p.key == 'holden-ve')
        self.assertFalse(profile.modules)
        profiles.activate(profile)
        self.assertIn('221940', pids.MONITOR_PIDS)
        self.assertNotIn('0122', pids.MONITOR_PIDS)

    def test_no_toyota_pack_is_offered_until_the_csv_is_in_data(self):
        has_file = (DATA / 'torque_toyota_style.csv').exists()
        self.assertEqual(any(p.key == 'toyota-style' for p in profiles.built_in()), has_file)
        self.assertEqual(predefined.by_key('toyota-style') is not None, has_file)

    def test_a_toyota_style_file_makes_a_profile_that_shows_module_readings(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'torque_toyota_style.csv').write_text(TEST_TOYOTA)
            with mock.patch.object(profiles, 'DATA_DIR', Path(folder)):
                profile = next(p for p in profiles.built_in() if p.key == 'toyota-style')
                self.assertTrue(profile.modules)
                self.assertEqual((profile.make, profile.years), ('', ''))
                item = predefined.pack_list('toyota-style')
                self.assertTrue(item.modules)
                self.assertEqual(predefined.count(item), 5)
                summary = profiles.activate(profile)
                self.assertEqual(summary['rejected'], [])
                self.assertEqual((summary['added'], summary['already_known']), (4, 1))   # 0105 is built in
                self.assertIn('2181', pids.MONITOR_PIDS)
                self.assertIn('0105', pids.MONITOR_PIDS)
                self.assertFalse(any(p.startswith('22') for p in pids.MONITOR_PIDS))
                self.assertEqual(pids.CATALOG['2181'].header, '7B0')
                self.assertFalse(pids.CATALOG['2181'].verified)

    def test_a_user_profile_saved_from_a_module_pack_keeps_its_module_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'torque_toyota_style.csv').write_text(TEST_TOYOTA)
            with mock.patch.object(profiles, 'DATA_DIR', Path(folder)):
                item = predefined.pack_list('toyota-style')
                profile, rejected = predefined.save_to_profile(Path(folder) / 'cars', item, 'Corolla', '', '', '', '')
                self.assertEqual(rejected, [])
                self.assertTrue(profile.modules)
                loaded = profiles.list_user(Path(folder) / 'cars')
                self.assertTrue(loaded[0].modules)
                self.assertEqual(len(profiles.load_pids(loaded[0])[0]), 5)

    def test_an_ordinary_import_still_refuses_mode_21(self):
        found, rejected = torque_csv.parse(TEST_TOYOTA, source='import')
        self.assertEqual([p.pid for p in found], ['0105'])
        self.assertEqual(len(rejected), 4)
        self.assertTrue(all('Mode 21' in r['reason'] for r in rejected), rejected)


class ModuleParseTests(unittest.TestCase):
    def parse(self, *rows):
        return torque_csv.parse(HEAD + ''.join(rows), source='pack', modules=True)

    def test_module_rows_decode_from_their_equations(self):
        found, rejected = torque_csv.parse(TEST_TOYOTA, source='pack', modules=True)
        self.assertEqual(rejected, [])
        by_id = {p.pid: p for p in found}
        self.assertEqual(by_id['2181'].mode, '21')
        self.assertEqual(by_id['2181'].echo, '6181')
        self.assertAlmostEqual(by_id['2181'].parse('78'), 80.0)             # 0x78 - 40
        self.assertAlmostEqual(by_id['2172'].parse('1AF8'), 1726.0)         # 0x1AF8 / 4
        self.assertAlmostEqual(by_id['2191'].parse('80'), 50.196, places=2)  # 128 * 100 / 255
        self.assertEqual({p.pid: p.header for p in found if p.mode == '21'},
                         {'2181': '7B0', '2172': '7C0', '2191': '7C4', '2161': '7E1'})

    def test_a_mode_21_row_must_name_one_of_the_four_modules(self):
        found, rejected = self.parse(row('x', '0x2181', 'A', header='7E0'), row('y', '0x2182', 'A', header='Auto'),
                                     row('z', '0x2183', 'A', header='7B1'))
        self.assertEqual(found, [])
        self.assertEqual(len(rejected), 3)

    def test_other_services_are_still_refused(self):
        found, rejected = self.parse(*(row('x', f'0x{service}01', 'A', header='7B0')
                                       for service in ('2E', '2F', '31', '10', '27', '14', '04', '19', '09')))
        self.assertEqual(found, [])
        self.assertEqual(len(rejected), 9)

    def test_a_startdiagnostic_command_is_still_refused(self):
        found, rejected = self.parse(row('x', '0x2181', 'A', header='7B0', start='ATSH7B0'))
        self.assertEqual(found, [])
        self.assertIn('startDiagnostic', rejected[0]['reason'])

    def test_a_mode_01_row_on_a_module_header_reads_from_auto(self):
        found, _ = self.parse(row('x', '0x0105', 'A-40', header='7B0'))
        self.assertEqual(found[0].header, 'Auto')

    def test_a_three_byte_mode_21_id_is_accepted(self):
        found, rejected = self.parse(row('x', '0x217101', 'A', header='7C0'))
        self.assertEqual((found[0].pid, found[0].echo), ('217101', '617101'))
        self.assertEqual(rejected, [])


class IsAllowedTests(unittest.TestCase):
    def setUp(self):
        found, _ = torque_csv.parse(TEST_TOYOTA, source='pack', modules=True)
        pids.use_extras(found)

    def tearDown(self):
        pids.use_extras([])

    def test_default_refuses_the_module_headers_and_mode_21(self):
        for command in ('ATSH7B0', 'ATSH7C0', 'ATSH7C4', 'ATSH7E1', '2181', '2172', '217101', '2161'):
            with self.subTest(command=command):
                self.assertFalse(obd.is_allowed(command))
                self.assertFalse(obd.is_allowed(command, allow_clear=True))
                self.assertFalse(obd.is_allowed(command, extra_modules=False))

    def test_opt_in_allows_exactly_the_four_headers(self):
        for header in MODULE_HEADERS:
            self.assertTrue(obd.is_allowed(f'ATSH{header}', extra_modules=True), header)
        for header in ('7B1', '7C1', '7C5', '7E4', '7E5', '7FF', '7B', '7B00', '000', '7B0X', '7e0x'):
            self.assertFalse(obd.is_allowed(f'ATSH{header}', extra_modules=True), header)
        self.assertEqual(set(obd.EXTRA_HEADERS), set(MODULE_HEADERS))
        self.assertEqual(set(pids.EXTRA_HEADERS), set(MODULE_HEADERS))

    def test_opt_in_allows_catalogued_mode_21_reads_only(self):
        for command in ('2181', '2172', '2191', '2161', '21 81'):
            self.assertTrue(obd.is_allowed(command, extra_modules=True), command)
        for command in ('2182', '21FF', '2100', '217101', '21', '2181FF'):
            self.assertFalse(obd.is_allowed(command, extra_modules=True), command)

    def test_opt_in_still_refuses_every_write_and_service(self):
        for command in ('2E1234', '2E81', '2F1234', '3101', '3181', '1003', '1001', '2701', '2702', '14FF00',
                        '1902', '0902', '0400', '04', '08', 'ATSPA', 'ATZZ'):
            with self.subTest(command=command):
                self.assertFalse(obd.is_allowed(command, extra_modules=True))
        self.assertFalse(obd.is_allowed('04', extra_modules=True))          # the clear needs allow_clear
        self.assertTrue(obd.is_allowed('04', allow_clear=True, extra_modules=True))

    def test_the_opt_in_does_not_change_what_was_allowed_before(self):
        for command in ('ATZ', '0100', '010C', '03', 'ATSH7E0', 'ATSH7E2', 'ATSH7DF', '221940', 'ATAT1', 'ATSP6'):
            self.assertTrue(obd.is_allowed(command, extra_modules=True), command)
            self.assertTrue(obd.is_allowed(command), command)

    def test_a_mode_21_id_cannot_be_catalogued_on_another_header(self):
        bad, _ = torque_csv.parse(HEAD + row('x', '0x2199', 'A', header='7B0'), modules=True)
        forged = replace(bad[0], header='7E0')
        skipped = pids.use_extras([forged])
        self.assertEqual(skipped, ['2199'])
        self.assertFalse(obd.is_allowed('2199', extra_modules=True))


class ElmModuleTests(unittest.TestCase):
    def make(self, extra_modules):
        fake = FakeElm327()
        fake.REPLIES = dict(FakeElm327.REPLIES, ATSH7B0='OK', ATSH7C0='OK', **{'2181': '618178', '2172': '61721AF8'})
        elm = obd.Elm327(obd.WifiTransport('127.0.0.1', fake.port, timeout=3), extra_modules=extra_modules)
        elm.open()
        self.addCleanup(fake.close)
        self.addCleanup(elm.close)
        found, _ = torque_csv.parse(TEST_TOYOTA, source='pack', modules=True)
        pids.use_extras(found)
        self.addCleanup(pids.use_extras, [])
        return fake, elm

    def test_the_default_is_off(self):
        elm = obd.Elm327(mock.Mock())
        self.assertIs(elm.extra_modules, False)
        self.assertIs(elm.allow_clear, False)

    def test_off_skips_module_reads_with_a_clear_message_and_sends_nothing(self):
        fake, elm = self.make(False)
        before = len(fake.received)
        values, errors = elm.poll(['2181', '2172'])
        self.assertEqual(values, {})
        for pid in ('2181', '2172'):
            self.assertIn('module access is off', errors[pid].lower())
        self.assertEqual(len(fake.received), before)
        with self.assertRaises(obd.ModuleAccessOff):
            elm.read('2181')
        with self.assertRaises(obd.UnsafeCommand):
            elm.command('ATSH7B0')
        self.assertEqual(len(fake.received), before)

    def test_off_still_reads_the_standard_readings_in_the_same_poll(self):
        _fake, elm = self.make(False)
        values, errors = elm.poll(['010C', '2181', '010D'])
        self.assertEqual(set(values), {'010C', '010D'})
        self.assertEqual(set(errors), {'2181'})

    def test_on_reads_a_module_and_goes_back_to_the_broadcast_address(self):
        fake, elm = self.make(True)
        before = len(fake.received)
        values, errors = elm.poll(['2181', '2172', '010D'])
        self.assertEqual(errors, {})
        self.assertEqual(values['2181'], (80.0, 'C'))
        self.assertAlmostEqual(values['2172'][0], 1726.0)
        self.assertEqual(fake.received[before:], ['ATSH7B0', '2181', 'ATSH7C0', '2172', 'ATSH7DF', '010D'])

    def test_on_never_sends_an_uncatalogued_mode_21_request(self):
        fake, elm = self.make(True)
        before = len(fake.received)
        for command in ('2182', '2E81', '3101', '1003', '2701', '14FF00', '04'):
            with self.assertRaises(obd.UnsafeCommand):
                elm.command(command)
        values, errors = elm.poll(['2182'])
        self.assertEqual((values, list(errors)), ({}, ['2182']))
        self.assertEqual(len(fake.received), before)

    def test_a_scan_with_module_access_off_skips_module_readings_and_says_why(self):
        fake, elm = self.make(False)
        result = car_scan.scan(elm, ['010D', '2181'])
        self.assertTrue(result['complete'])
        self.assertEqual(list(result['answered']), ['010D'])
        self.assertEqual(result['silent'], [])
        self.assertEqual(result['skipped'], ['2181'])
        shown, hidden = car_scan.enforce(['010D', '2181'], result)
        self.assertEqual(shown, ['010D'])
        self.assertEqual(hidden, {'2181': 'module access is off'})
        self.assertNotIn('2181', fake.received)

    def test_module_note_names_the_setting(self):
        self.make(False)
        self.assertEqual(obd.module_note(pids.CATALOG['2181'], False), 'module access is off')
        self.assertIsNone(obd.module_note(pids.CATALOG['2181'], True))
        self.assertIsNone(obd.module_note(pids.CATALOG['0105'], False))
        self.assertIsNone(obd.module_note(pids.BUILT_IN['010C'], False))


class PrefsTests(unittest.TestCase):
    def test_default_is_off_and_old_files_load(self):
        self.assertIs(prefs.DEFAULTS['extra_modules'], False)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prefs.json'
            path.write_text('{"link_kind": "Wi-Fi"}')
            self.assertIs(prefs.load(path)['extra_modules'], False)

    def test_saved_choice_is_kept_and_junk_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prefs.json'
            prefs.save(path, dict(prefs.DEFAULTS, extra_modules=True))
            self.assertIs(prefs.load(path)['extra_modules'], True)
            for junk in ('yes', 1, None, [], {}):
                path.write_text(f'{{"extra_modules": {json.dumps(junk)}}}')
                self.assertIs(prefs.load(path)['extra_modules'], False, junk)


if __name__ == '__main__':
    unittest.main()
