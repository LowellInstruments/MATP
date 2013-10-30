import unittest

import numpy as np

from lidreader_numpy import build_dtype, Settings

class SettingsTestCase(unittest.TestCase):
    def setUp(self):
        '''This hex produces
        {'TMP': '1', 'TRI': '60', 'BAT': '0e70', 'LED': '1', 'SER': '0004', 'CLK': '2013-07-30 11:45:03', 'STM': '1970-01-01 00:00:00', 'STS': '0001', 'BMN': '960', 'MGN': '1', 'DFS': '0x8000', 'ACL': '1', 'BMR': '16', 'ORI': '60', 'FWV': '1.0.098', 'DPL': '1', 'ETM': '4096-01-01 00:00:00'}
        '''
        ba = '4844530d0a53455220303030340d0a46575620312e302e3039380d0a44504c20310d0a444653203078383030300d0a53544d20313937302d30312d30312030303a30303a30300d0a45544d20343039362d30312d30312030303a30303a30300d0a4c454420310d0a4d48530d0a434c4b20323031332d30372d33302031313a34353a30330d0a544d5020310d0a41434c20310d0a4d474e20310d0a5452492036300d0a4f52492036300d0a424d522031360d0a424d4e203936300d0a42415420306537300d0a53545320303030310d0a4d48450d0a4844450d0affffffff'.decode('hex')
        self.s = Settings(ba)
        self.mh = self.s.mini_header

    def test_convert_types(self):
        self.assertEqual(self.mh.settings['TMP'], 1)
        self.assertEqual(self.mh.settings['TRI'], 60)
    
    def test_dtype(self):
        self.assertEqual(self.mh.dtype, np.dtype([('s', np.str_, 109)]))

class BuildDtypeTestCase(unittest.TestCase):
    def test_simple_settings(self):
        settings = {
            'TRI': 60,
            'ORI': 30,
            'BMN': 5,
            'TMP': 1,
            'ACL': 1,
            'MGN': 1,
        }
        dtype = build_dtype(**settings)
        expected_dtype = np.dtype([
            ('t', '<H', 1),
            ('o', '<h', 60),
        ])
        self.assertEqual(expected_dtype, dtype)

    def test_same_settings(self):
        settings = {
            'TRI': 60,
            'ORI': 60,
            'BMN': 1,
            'TMP': 1,
            'ACL': 1,
            'MGN': 1,
        }
        dtype = build_dtype(**settings)
        expected_dtype = np.dtype([
            ('t', '<H', 1),
            ('o', '<h', 6),
        ])

if __name__ == '__main__':
    unittest.main()
