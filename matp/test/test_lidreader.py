import unittest

from lidreader import steinhart, k_to_c, rate_to_delta
from lidreader import measurement_to_resistance
from lidreader import acceleration, magnetometer
from lidreader import major_minor_patterns
from lidreader import pattern_iterator
from lidreader import build_full_pattern

class SteinhartTestCase(unittest.TestCase):
    def setUp(self):
        self.a = 0.0011238100354
        self.b = 0.0002349457073
        self.c = 0.0000000848361

    def test_samples(self):
        '''Steinhart should be the same as the given values'''
        resistance = measurement_to_resistance(35893, 0, 10000)
        self.assertEqual(20.6912, steinhart(resistance, self.a, self.b, self.c))

class KelvinToCelciusTestCase(unittest.TestCase):
    def test_absolute_zero(self):
        '''Kelvin to celius should return sane values'''
        self.assertEqual(k_to_c(0), -273.15)  # absolute zero
        self.assertEqual(k_to_c(373.15), 100) # boiling point of water
        self.assertEqual(k_to_c(273.15), 0)   # freezing point of water

class RateToMicrosecondsTestCase(unittest.TestCase):
    def test_rate_to_microseconds(self):
        '''Should return a timedelta with the correct number of microseconds'''
        self.assertEqual(rate_to_delta(64).microseconds, 15625)
        self.assertEqual(rate_to_delta(16).microseconds, 62500)
        self.assertEqual(rate_to_delta(2).microseconds,  500000)
        self.assertEqual(rate_to_delta(1).seconds, 1)


class AccelerationTestCase(unittest.TestCase):
    def setUp(self):
        self.axa = 0
        self.axb = 1024
        self.aya = 0
        self.ayb = 1024
        self.aza = 0
        self.azb = 1024

    def test_sample_data(self):
        '''Should match the sample data
        70fc     d501    1500 
        ax,      ay,     az
        -0.89063,0.45801,0.02051,
        '''
        self.assertEqual(acceleration(-912, self.axb, self.axa), -0.89063)
        self.assertEqual(acceleration(469, self.ayb, self.aya), 0.45801)
        self.assertEqual(acceleration(21, self.azb, self.aza), 0.02051)


class MagnetometerTestCase(unittest.TestCase):
    def setUp(self):
        self.mxa = 0
        self.mxs = 1
        self.mya = 0
        self.mys = 1
        self.mza = 0
        self.mzs = 1
        
    def test_sample_data(self):
        '''should match the sample data
        87fe    c270   4c00
        mx      my     mz
        -345.87,-56.88,69.72
        '''

class MajorMinorPatternsTestCase(unittest.TestCase):
    def test_simple_generate_binary_pattern(self):
        '''The minor should just be the smaller interval'''
        major, minor = major_minor_patterns(1, 1, 1, 30, 60, 1)
        self.assertEqual(major, '<Hhhhhhh')
        self.assertEqual(minor, '<H')

    def test_same_interval_generate_binary_pattern(self):
        '''if the intervals are the same, the major and minor are identical.'''
        major, minor = major_minor_patterns(1, 1, 1, 30, 30, 1)
        self.assertEqual(major, '<Hhhhhhh')
        self.assertEqual(minor, '<Hhhhhhh')

    def test_no_temp(self):
        '''No temp should have equal major and minor'''
        major, minor = major_minor_patterns(0, 1, 1, 0, 10, 1)
        self.assertEqual(major, '<hhhhhh')
        self.assertEqual(major, minor)

    def test_no_orientation(self):
        '''No orientation should have equal major and minor'''
        major, minor = major_minor_patterns(1, 0, 0, 10, 0, 1)
        self.assertEqual(major, '<H')
        self.assertEqual(major, minor)

    def test_no_accel(self):
        '''No accel should record temp and magnetometer'''
        major, minor = major_minor_patterns(1, 0, 1, 10, 20, 1)
        self.assertEqual(major, '<Hhhh')
        self.assertEqual(minor, '<H')

    def test_big_burst(self):
        '''A burst will multiply out the orientation pattern'''
        major, minor = major_minor_patterns(1, 1, 1, 60, 30, 5)
        self.assertEqual(major, '<Hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh')
        self.assertEqual(minor, '<hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh')

class BuildFullPatternTestCase(unittest.TestCase):
    def test_all_enabled_same_intervals(self):
        '''If all channels are enabled and intervals are the same, the patterns
        should be the same too.
        '''
        major, minor = major_minor_patterns(1, 1, 1, 60, 30, 5)
        full_pattern = build_full_pattern(major, minor, 2)
        ma = '<Hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'
        mi = '<hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'
        self.assertEqual(full_pattern, [ma, mi])

if __name__ == '__main__':
    unittest.main()
