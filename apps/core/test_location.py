from django.test import TestCase

from apps.core import location


class HaversineTest(TestCase):
    def test_zero_distance(self):
        self.assertAlmostEqual(
            location.haversine_miles(52.48, -1.90, 52.48, -1.90),
            0.0,
            places=5,
        )

    def test_london_manchester_roughly_160(self):
        d = location.haversine_miles(51.507, -0.127, 53.48, -2.24)
        self.assertGreater(d, 150)
        self.assertLess(d, 200)
