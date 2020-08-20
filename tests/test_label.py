"""
Tests for Label class
"""

import unittest

import pandas as pd

from pypctools.Bucket import Label


class TestLabelConstructor(unittest.TestCase):
    # testing for failure
    def test_not_str(self):
        invalid_type_inputs = (
            44, 0, 0.9999, -5.6, -10, b'hello', b'',
            [1, 4, 'none'], True, False, None,
            {9, 8, 1.2, 'hey'}, {5: 'A', 9: 'B'}, str,
        )
        for inp in invalid_type_inputs:
            with self.assertRaises(TypeError):
                Label(inp)

    # testing for success
    def test_valid_input(self):
        valid_inputs = (
            '3M', '1D', '1Y1M1W1D', '5Y', '1004Y90M', '80M', '365W1D',
            '700D', '999999Y1M3D', '90Y7W2D', '1M600W10D', '7W4D', '5Y3W',
            '333333Y1D', '8W', '9000W', '1M8000D', '9Y10M11W12D', '9Y9W',
            '54D', '8Y1M', '999D', '7W9D', '0Y', '0M', '0W', '0D', '9Y0D',
        )
        for inp in valid_inputs:
            Label(inp)

    # testing for failure
    def test_invalid_input(self):
        invalid_inputs = (
            '-7W0D', '1D2W', '2W400M', '-1Y',
            '-999D', '90D1Y', 'BAY', '1D0W', 'AY', '1W6Y',
            '1M1M1M1M1M1M', '5Y6Y', '4D3D', '40M40M', '7W7W7W', '0D0D',
            'ALFABET', 'NOMATCH', 'INVALID', 'VALID', 'Y', 'M', 'W', 'D',
            'YYYY', 'Y6M', 'M5D', '6y7y', '', '6.7Y', '8.9M3.8D',
            '  9Y', '9Y  ', ' 4M 3D', '9M    1W 1D', '   1', '32', '0.6',
            '0.0D', '1d', '-1D', '-0Y', '+2W', '10 D', '9 Y'
        )
        for inp in invalid_inputs:
            with self.assertRaises(ValueError):
                Label(inp)


class TestLabelDayCount(unittest.TestCase):
    def test_day_count(self):
        dc_map = [
            ('1D', 1),
            ('1W', 7),
            ('1M', 30),
            ('1Y', 360),
            ('1Y1M', 390),
            ('1Y1D', 361),
            ('10Y', 3600),
            ('1032D', 1032),
            ('7W', 49),
            ('10M', 300),
            ('1M2W', 44),
            ('10Y2W', 3614),
            ('1Y1W1D', 368),
            ('2Y1M1W1D', 758),
        ]
        for label, dc in dc_map:
            self.assertEqual(Label(label).dc_count, dc)

    def test_labels_map(self):
        labels_map = [
            ('1D', {'Y': 0, 'M': 0, 'W': 0, 'D': 1}),
            ('1W', {'Y': 0, 'M': 0, 'W': 1, 'D': 0}),
            ('1M', {'Y': 0, 'M': 1, 'W': 0, 'D': 0}),
            ('1Y', {'Y': 1, 'M': 0, 'W': 0, 'D': 0}),
            ('1Y1M', {'Y': 1, 'M': 1, 'W': 0, 'D': 0}),
            ('1Y1D', {'Y': 1, 'M': 0, 'W': 0, 'D': 1}),
            ('10Y', {'Y': 10, 'M': 0, 'W': 0, 'D': 0}),
            ('1032D', {'Y': 0, 'M': 0, 'W': 0, 'D': 1032}),
            ('7W', {'Y': 0, 'M': 0, 'W': 7, 'D': 0}),
            ('10M', {'Y': 0, 'M': 10, 'W': 0, 'D': 0}),
            ('1M2W', {'Y': 0, 'M': 1, 'W': 2, 'D': 0}),
            ('10Y2W', {'Y': 10, 'M': 0, 'W': 2, 'D': 0}),
            ('1Y1W1D', {'Y': 1, 'M': 0, 'W': 1, 'D': 1}),
            ('2Y1M1W1D', {'Y': 2, 'M': 1, 'W': 1, 'D': 1}),
        ]
        for label, dict_ in labels_map:
            self.assertEqual(Label(label).letter_map, dict_)


class TestLabelToDate(unittest.TestCase):
    def test_labeltodate(self):
        """Labelshift testing"""
        ref_date = "2020-01-08"
        answers = [
            # label | expected shifted date from ref_date
            ('1D', "2020-01-09"),
            ('1W', "2020-01-15"),
            ('1M', "2020-02-10"),
            ('1Y', "2021-01-08"),
        ]

        for label, expected in answers:
            calc = Label(label).to_date(ref_date, date_adjust='DU', cal='BRL')
            self.assertEqual(pd.Timestamp(expected), calc)


if __name__ == '__main__':
    unittest.main()
