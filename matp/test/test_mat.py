import unittest
import time

from matp import mat

class TimerTestCase(unittest.TestCase):
    def setUp(self):
        self.start = time.time()
    
    def tearDown(self):
        t = time.time() - self.start
        print "%s: %.3f" % (self.id(), t)

class PatternTestCase(TimerTestCase):
    def setUp(self):
        super(PatternTestCase, self).setUp()

    def test_simple_pattern(self):
        '''using same ORI and TRI and all measurements'''
        expected = '<H6h'
        tri = 1
        ori = 1
        acl = True
        mgn = True
        tmp = True
        bmn = 1
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

    def test_big_pattern(self):
        '''use the same input as the big file'''
        expected = '<H5760h'
        tri = 60
        ori = 60
        acl = True
        mgn = True
        tmp = True
        bmn = 960
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

    def test_spec_pattern(self):
        '''use the input as shown in the spec'''
        expected = '<H60h'
        tri = 60
        ori = 30
        acl = True
        mgn = True
        tmp = True
        bmn = 5
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

    def test_extreme_pttern(self):
        '''use the endpoints of BMN'''
        expected = '<H786432h'
        tri = 60
        ori = 30
        acl = True
        mgn = True
        tmp = True
        bmn = 65536
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

    def test_complex_pattern(self):
        '''use the complex pattern provided'''
        expected = '<H3072h'
        tri = 20
        ori = 5
        acl = True
        mgn = True
        tmp = True
        bmn = 128
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

    
    @unittest.skip("not implemented yet")
    def test_ori_bigger_than_tri(self):
        '''use a tri value smaller than ori'''
        expected = '<H6h5H'
        tri = 10
        ori = 60
        acl = True
        mgn = True
        tmp = True
        bmn = 1
        pattern = mat.pattern(bmn, tri=tri, ori=ori, acl=acl, mgn=mgn, tmp=tmp)
        self.assertEqual(pattern, expected)

class GetOriFormatTestCase(TimerTestCase):
    def setUp(self):
        super(GetOriFormatTestCase, self).setUp()
        
    def test_all_measurements(self):
        '''Should return 7 %s'''
        accel = '1'
        magne = '1'
        fmt = mat.get_orientation_format(accel=accel, magne=magne)
        expected = ','.join(['%s'] * 7)
        self.assertEqual(fmt, expected)

    def test_only_magne(self):
        '''should return 4 %s'''
        accel = '0'
        magne = '1'
        fmt = mat.get_orientation_format(accel=accel, magne=magne)
        expected = ','.join(['%s'] * 4)
        self.assertEqual(fmt, expected)

    def test_only_accel(self):
        '''should return 4 %s'''
        accel = '1'
        magne = '0'
        fmt = mat.get_orientation_format(accel=accel, magne=magne)
        expected = ','.join(['%s'] * 4)
        self.assertEqual(fmt, expected)
        

class GetTmpCSVHeadersTestCase(TimerTestCase):
    def setUp(self):
        super(GetTmpCSVHeadersTestCase, self).setUp()
        self.datetime_header = "Date,Time"
        self.temp = "Temperature (C)"

    def test_temp(self):
        '''should return datetime and temperature and linebreak'''
        temp = '1'
        ori_header = mat.get_tmp_csv_headers(temp=temp)
        self.assertIn(self.datetime_header, ori_header)
        self.assertIn(self.temp, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

    def test_no_temp(self):
        '''should only return datetime'''
        temp = '0'
        ori_header = mat.get_tmp_csv_headers(temp=temp)
        self.assertIn(self.datetime_header, ori_header)
        self.assertNotIn(self.temp, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

class GetOriCSVHeadersTestCase(TimerTestCase):
    def setUp(self):
        super(GetOriCSVHeadersTestCase, self).setUp()
        self.datetime_header = "Date,Time"
        self.accel_header = "Ax (g),Ay (g),Az (g)"
        self.magne_header = "Mx (mG),My (mG),Mz (mG)"

    def test_both_measurements(self):
        '''Should return a time and 3 acl and 3 mgn headers and end in linebreak'''
        accel = '1'
        magne = '1'
        ori_header = mat.get_ori_csv_headers(accel=accel, magne=magne)
        self.assertIn(self.datetime_header, ori_header)
        self.assertIn(self.accel_header, ori_header)
        self.assertIn(self.magne_header, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

    def test_only_accel(self):
        '''Should only return time and accel headers'''
        accel = '1'
        magne = '0'
        ori_header = mat.get_ori_csv_headers(accel=accel, magne=magne)
        self.assertIn(self.datetime_header, ori_header)
        self.assertIn(self.accel_header, ori_header)
        self.assertNotIn(self.magne_header, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

    def test_only_magne(self):
        '''should only return time and magne headers'''
        accel = '0'
        magne = '1'
        ori_header = mat.get_ori_csv_headers(accel=accel, magne=magne)
        self.assertIn(self.datetime_header, ori_header)
        self.assertNotIn(self.accel_header, ori_header)
        self.assertIn(self.magne_header, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

    def test_neither(self):
        '''should return just the date header'''
        accel = '0'
        magne = '0'
        ori_header = mat.get_ori_csv_headers(accel=accel, magne=magne)
        self.assertIn(self.datetime_header, ori_header)
        self.assertNotIn(self.accel_header, ori_header)
        self.assertNotIn(self.magne_header, ori_header)
        self.assertEqual(mat.LINE_BREAK, ori_header[ori_header.rfind(mat.LINE_BREAK):])

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

