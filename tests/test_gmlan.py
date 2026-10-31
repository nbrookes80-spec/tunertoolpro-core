import unittest

from tunertoolpro.canbus import gmlan
from tunertoolpro.canbus.frames import Frame


class GmlanTableTests(unittest.TestCase):
    def test_every_readme_message_is_present(self):
        for can_id in (0x0C9, 0x0F9, 0x1F3, 0x1F5, 0x4E9, 0x1E1, 0x1F1):
            self.assertIsNotNone(gmlan.lookup(can_id), hex(can_id))

    def test_signal_lists_match_readme_counts(self):
        self.assertEqual(len(gmlan.lookup(0x0C9).signals), 18)
        self.assertEqual(len(gmlan.lookup(0x1F5).signals), 19)
        self.assertEqual(len(gmlan.lookup(0x1F1).signals), 15)

    def test_no_stray_quotes_from_readme(self):
        for message in gmlan.MESSAGES.values():
            for signal in message.signals:
                self.assertNotIn('"', signal)

    def test_sender_comes_from_readme_heading(self):
        self.assertEqual(gmlan.lookup(0x1F5).sender, 'TCM,ECM tx')
        self.assertEqual(gmlan.lookup(0x1F3).sender, 'GW tx')
        self.assertIsNone(gmlan.lookup(0x0C9).sender)

    def test_unknown_id_is_none(self):
        self.assertIsNone(gmlan.lookup(0x7FF))


class GmlanDescribeTests(unittest.TestCase):
    def test_documented_gear_example_is_recognised(self):
        message, example = gmlan.describe(Frame(0x1F5, bytes.fromhex('0F0F000200000300')))
        self.assertEqual(message.can_id, 0x1F5)
        self.assertEqual(example.meaning, 'Reverse')

    def test_all_four_gear_examples_map_to_their_names(self):
        expected = {'0F0F000100000300': 'Park', '0F0F000200000300': 'Reverse',
                    '0F0F000300000300': 'Neutral', '0F0F000400000300': 'Drive'}
        for payload, meaning in expected.items():
            _, example = gmlan.describe(Frame(0x1F5, bytes.fromhex(payload)))
            self.assertEqual(example.meaning, meaning)

    def test_undocumented_payload_has_message_but_no_example(self):
        message, example = gmlan.describe(Frame(0x1F5, bytes(8)))
        self.assertIsNotNone(message)
        self.assertIsNone(example)

    def test_unknown_id_describes_as_nothing(self):
        self.assertEqual(gmlan.describe(Frame(0x7FF, bytes(8))), (None, None))

    def test_extended_frame_is_not_matched_to_11_bit_table(self):
        self.assertEqual(gmlan.describe(Frame(0x1F5, bytes(8), extended=True)), (None, None))


if __name__ == '__main__':
    unittest.main()
