import unittest
import time

from matp import mat

class TimerTestCase(unittest.TestCase):
    def setUp(self):
        self.start = time.time()
    
    def tearDown(self):
        t = time.time() - self.start
        print "%s: %.3f" % (self.id(), t)

class ParseMainHeaderTestCase(TimerTestCase):
    def setUp(self):
        super(ParseMainHeaderTestCase, self).setUp()
        self.header = '4844530d0a53455220303030340d0a46575620312e302e3039380d0a44504c20310d0a444653203078383030300d0a53544d20313937302d30312d30312030303a30303a30300d0a45544d20343039362d30312d30312030303a30303a30300d0a4c454420310d0a4d48530d0a434c4b20323031332d30372d33302031313a34353a30330d0a544d5020310d0a41434c20310d0a4d474e20310d0a5452492036300d0a4f52492036300d0a424d522031360d0a424d4e203936300d0a42415420306537300d0a53545320303030310d0a4d48450d0a4844450d0a485353544d4f0130544d52053130303030544d410f302e30303131323338313030333534544d420f302e30303032333439343537303733544d430f302e303030303030303834383336314158410130415842043130323441594101304159420431303234415a410130415a4204313032344d584101304d594101304d5a4101304d585301314d595301314d5a530131485345ffffffffffffffff'.decode('hex')

    def test_header_parsing(self):
        header, mini_header, hss, mh_size = mat.parse_main_header(self.header)
        self.assertItemsEqual(header, {'LED': '1', 
                                       'SER': '0004', 
                                       'STM': '1970-01-01 00:00:00', 
                                       'DFS': '0x8000', 
                                       'FWV': '1.0.098', 
                                       'DPL': '1', 
                                       'ETM': '4096-01-01 00:00:00'})
        self.assertItemsEqual(mini_header, {'TMP': '1', 
                                            'TRI': '60', 
                                            'BAT': '0e70', 
                                            'CLK': '2013-07-30 11:45:03', 
                                            'STS': '0001', 
                                            'BMN': '960', 
                                            'MGN': '1', 
                                            'ACL': '1', 
                                            'BMR': '16', 
                                            'ORI': '60'})
        self.assertItemsEqual(hss, {'TMR': '10000', 
                                    'MZS': '1', 
                                    'TMC': '0.0000000848361', 
                                    'AZA': '0', 
                                    'AZB': '1024', 
                                    'AYA': '0', 
                                    'MXS': '1', 
                                    'AYB': '1024', 
                                    'AXB': '1024', 
                                    'TMA': '0.0011238100354', 
                                    'TMB': '0.0002349457073', 
                                    'AXA': '0', 
                                    'MZA': '0', 
                                    'MYA': '0', 
                                    'MXA': '0', 
                                    'MYS': '1', 
                                    'TMO': '0'})
        self.assertEqual(mh_size, 109)

    def test_no_hss_tag(self):
        hss = mat.parse_hss('blahblahblah'.encode('hex'))
        self.assertItemsEqual(hss, mat.DEFAULT_HOST_STORAGE)

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
        '''There should be one less than 2**16 since 65536 is inavlid'''
        h = mat.DEFAULT_HOST_STORAGE
        t = mat.build_thermometer_values(h['TMA'], h['TMB'], h['TMC'], h['TMO'], h['TMR'])
        self.assertEqual(len(t), 2**16 - 1)


if __name__ == '__main__':
    suite = unittest.TestLoader().discover('.')
    unittest.TextTestRunner(verbosity=0).run(suite)

