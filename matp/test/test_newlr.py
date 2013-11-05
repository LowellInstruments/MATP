import unittest
import time

from matp import mat

class TimerTestCase(unittest.TestCase):
    def setUp(self):
        self.start = time.time()
    
    def tearDown(self):
        t = time.time() - self.start
        print "%s: %.3f" % (self.id(), t)

class TestBuildAccelerometerValues(TimerTestCase):
    def setUp(self):
        super(TestBuildAccelerometerValues, self).setUp()
        self.AXA = 0
        self.AXB = 1024

    def test_number_of_values(self):
        '''there should be 2^16 (two bytes) of values'''
        a = mat.build_accelerometer_values(self.AXA, self.AXB)
        self.assertEqual(len(a), 2**16)

class TestBuildMagnetometerValues(TimerTestCase):
    def setUp(self):
        super(TestBuildMagnetometerValues, self).setUp()
        self.a = 0
        self.s = 0.91743

    def test_number_of_values(self):
        '''there should be 2^16 (two bytes) of values'''
        m = mat.build_magnetometer_values(self.a, self.s)
        self.assertEqual(len(m), 2**16)

class TestBuildThermometerValues(TimerTestCase):
    def test_number_of_values(self):
        '''There should be two less than 2**16 since 0 is invalid and 65536 is inavlid'''
        t = mat.build_thermometer_values()
        self.assertEqual(len(t), 2**16 - 2)


if __name__ == '__main__':
    suite = unittest.TestLoader().discover('.')
    unittest.TextTestRunner(verbosity=0).run(suite)

