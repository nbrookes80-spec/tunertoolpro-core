import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro.scanner.session import Session  # noqa: E402


class FakeLink:
    def __init__(self, traffic):
        self._lock = threading.RLock()
        self.traffic = list(traffic)


class AdapterInfoTests(unittest.TestCase):
    def test_no_adapter_means_not_connected_and_nothing_recent(self):
        session = Session()
        self.assertEqual(session.adapter_info(), {'connected': False, 'demo': False, 'recent': []})

    def test_connected_adapter_shares_its_latest_traffic_only(self):
        session = Session()
        session.attach(FakeLink([('TX', f'01{n:02X}') for n in range(50)]))
        info = session.adapter_info(recent=3)
        self.assertTrue(info['connected'])
        self.assertEqual(info['recent'], [['TX', '012F'], ['TX', '0130'], ['TX', '0131']])

    def test_demo_is_reported_alongside_the_adapter(self):
        session = Session()
        session.set_demo(True)
        self.assertTrue(session.adapter_info()['demo'])


class AdapterJobTests(unittest.TestCase):
    """A one-off adapter job (the speed settings after a connect or from the menu) holds the adapter: the Live
    reader checks adapter_busy before each round and the job waits for a round already under way."""

    def test_the_adapter_is_busy_only_during_a_job(self):
        session = Session()
        self.assertFalse(session.adapter_busy)
        with session.adapter_job():
            self.assertTrue(session.adapter_busy)
        self.assertFalse(session.adapter_busy)

    def test_a_failed_job_still_gives_the_adapter_back(self):
        session = Session()
        with self.assertRaises(RuntimeError):
            with session.adapter_job():
                raise RuntimeError('the adapter refused')
        self.assertFalse(session.adapter_busy)

    def test_the_job_waits_for_the_reader_after_marking_the_adapter_busy(self):
        session, seen = Session(), []
        session.wait_reader = lambda timeout: seen.append((session.adapter_busy, timeout))
        with session.adapter_job(timeout=7):
            seen.append('job')
        self.assertEqual(seen, [(True, 7), 'job'])

    def test_a_failed_wait_still_gives_the_adapter_back(self):
        session = Session()

        def broken(_timeout):
            raise RuntimeError('no reader')
        session.wait_reader = broken
        with self.assertRaises(RuntimeError):
            with session.adapter_job():
                pass
        self.assertFalse(session.adapter_busy)

    def test_jobs_on_two_threads_keep_it_busy_until_both_end(self):
        session = Session()
        inner_started, release = threading.Event(), threading.Event()

        def other():
            with session.adapter_job():
                inner_started.set()
                release.wait(5)
        thread = threading.Thread(target=other)
        with session.adapter_job():
            thread.start()
            inner_started.wait(5)
        self.assertTrue(session.adapter_busy)
        release.set()
        thread.join(5)
        self.assertFalse(session.adapter_busy)


class FakeTransport:
    def __init__(self, reply=b'OK\r\r>', fail=None):
        self.reply, self.fail = reply, fail

    def write(self, data):
        pass

    def read_until(self, _end):
        if self.fail:
            raise self.fail
        return self.reply


class TrafficLogTests(unittest.TestCase):
    def test_traffic_refusals_and_errors_reach_the_log(self):
        from tunertoolpro.link import obd
        seen = []
        elm = obd.Elm327(FakeTransport())
        elm.on_traffic = lambda kind, text: seen.append((kind, text))
        elm.command('ATZ')
        with self.assertRaises(obd.UnsafeCommand):
            elm.command('2E0101')
        broken = obd.Elm327(FakeTransport(fail=obd.AdapterLost('gone')))
        broken.on_traffic = lambda kind, text: seen.append((kind, text))
        with self.assertRaises(obd.AdapterLost):
            broken.command('0100')
        self.assertEqual(seen, [('TX', 'ATZ'), ('RX', 'OK  >'), ('REFUSED', '2E0101'), ('TX', '0100'),
                                ('ERR', 'AdapterLost: gone')])

    def test_a_broken_log_does_not_stop_a_reading(self):
        from tunertoolpro.link import obd
        elm = obd.Elm327(FakeTransport())
        elm.on_traffic = lambda kind, text: 1 / 0
        self.assertEqual(elm.command('ATZ'), 'OK\n\n>')


    def test_a_broken_socket_becomes_adapter_lost_and_is_logged(self):
        from tunertoolpro.link import obd
        seen = []
        elm = obd.Elm327(FakeTransport(fail=OSError('socket closed')))
        elm.on_traffic = lambda kind, text: seen.append(kind)
        with self.assertRaises(obd.AdapterLost):
            elm.command('0100')
        self.assertEqual(seen, ['TX', 'ERR'])


class SilentStream:
    def available(self):
        return 0

    def read(self):
        raise AssertionError('must not block on read')


class BluetoothTimeoutTests(unittest.TestCase):
    def test_a_silent_adapter_times_out_instead_of_hanging(self):
        from tunertoolpro.link import obd
        transport = obd.BluetoothTransport('00:00:00:00:00:00')
        transport._in = SilentStream()
        with self.assertRaises(obd.AdapterLost):
            transport.read_until(b'>', timeout=0.05)


if __name__ == '__main__':
    unittest.main()
