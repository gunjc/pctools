
import unittest

import numpy as np

from pypctools.Bucket import Bucket


class TestBucket(unittest.TestCase):
    def test_value_distribution(self):
        from_ = ['1Y', '3Y']
        values = [100, -100]
        bkt = Bucket(from_, values)

        tos_ = [
            ['2Y'],
            ['1Y', '3Y'],
            ['2Y', '4Y']
        ]
        expected_values = [
            [0],
            [100, -100],
            [50, -50]
        ]
        for to_, expected in zip(tos_, expected_values):
            self.assertTrue(
                np.allclose(
                    bkt.distribute_values(to_), expected, rtol=0, atol=1.e-14
                )
            )
