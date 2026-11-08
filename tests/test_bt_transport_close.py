"""A Bluetooth read that races with close() must end as AdapterLost, not as an AttributeError.

The poll thread can be inside read_until() when the connection is closed (set self._in to None). The old code
called self._in.available() on None and crashed with "'NoneType' object has no attribute 'available'".
"""
import unittest

from tunertoolpro.link.obd import AdapterLost, BluetoothTransport


class _Gone:
    """A stream whose socket was closed underneath the reader: the Java call fails."""

    def available(self):
        raise RuntimeError('socket closed')

    def read(self):
        raise RuntimeError('socket closed')


class BluetoothReadRaceTests(unittest.TestCase):
    def test_read_after_close_is_adapter_lost(self):
        transport = BluetoothTransport('66:1E:87:00:D3:04')
        with self.assertRaises(AdapterLost):
            transport.read_until(timeout=0.05)

    def test_read_chunk_after_close_is_adapter_lost(self):
        transport = BluetoothTransport('66:1E:87:00:D3:04')
        with self.assertRaises(AdapterLost):
            transport.read_chunk(timeout=0.05)

    def test_stream_failing_mid_read_is_adapter_lost(self):
        transport = BluetoothTransport('66:1E:87:00:D3:04')
        transport._in = _Gone()
        with self.assertRaises(AdapterLost):
            transport.read_until(timeout=0.05)
        with self.assertRaises(AdapterLost):
            transport.read_chunk(timeout=0.05)


if __name__ == '__main__':
    unittest.main()
