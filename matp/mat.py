from __future__ import division
import struct
import math
import os
import itertools
import datetime
import sys
from cStringIO import StringIO

def accel(v, m, b):
    return (1.0/m * v) + b

def magne(v, m, b):
    return m * v + b

def k_to_c(kelvin):
    return kelvin - 273.15

# TODO: Grab these out of the HSS area
TMO = 0
TMR = 10000
TMA = 0.0011238100354
TMB = 0.0002349457073
TMC = 0.0000000848361
MAX_UNSIGNED_SHORT = 65535
def t_measure_to_resistance(t):
    r_adj = t + TMO
    return TMR * r_adj / (MAX_UNSIGNED_SHORT - r_adj)

def s(r):
    l = math.log(r)
    i = TMA + TMB * l + TMC * math.pow(l, 3)
    return k_to_c(math.pow(i, -1))

def temp(num):
    return s(t_measure_to_resistance(num))

def parse_header(header_bytes):
    kvpairs = header_bytes.split('\x0d\x0a')
    return dict((str(kv).split(' ', 1) for kv in kvpairs if ' ' in kv))

def mh_indicies(header_bytes):
    start = header_bytes.rfind('MHS')
    end = header_bytes.rfind('MHE') + 5
    return start, end

def parse_main_header(header_bytes):
    '''return a dict'''
    mh_start, mh_end = mh_indicies(header_bytes)
    mini_header = parse_header(header_bytes[mh_start:mh_end])
    header = parse_header(header_bytes[:mh_start] + header_bytes[mh_end:])
    return header, mini_header, mh_end - mh_start

def pattern(bmn):
    endian = '<'
    temp = 'H'
    o = 'h'
    return endian + temp + str(bmn * 6) + o

def build_accelerometer_values(a, b):
    '''Build a lookup table for all possible accelerometer values'''
    return dict(
        (i, '%.5f' % acc) for i, acc in enumerate(
            (1/b * f +a for f in xrange(-32768, 32768)), start=-32768
        )
    )

def build_magnetometer_values(a, s):
    '''build a lookup table for all possible magnetometer values'''
    return dict(
        (i, '%.2f' % mag) for i, mag in enumerate(
            (s * x + a for x in range(-32768, 32768)), start=-32768
        )
    )

def build_thermometer_values():
    '''build a lookup table for all possible thermometer values'''
    return [temp(x) for x in xrange(1, 65535)]

def get_lookup_tables(axa, axb, mxa, mxs):
    accelerometer_values = build_accelerometer_values(axa, axb)
    magnetometer_values = build_magnetometer_values(mxa, mxs)
    # This is a straight array lookup
    thermometer_values = build_thermometer_values()
    return accelerometer_values, magnetometer_values, thermometer_values

def main(): 
    K = 1024
    MAIN_HEADER_SIZE = 32 * K
    DATA_PAGE_SIZE = 1024 * K
    MIN_SIGNED_SHORT = -32768
    AXA = 0
    AXB = 1024
    AYA = 0
    AYB = 1024
    AZA = 0
    AZB = 1024
    MXA = 0
    MXS = 0.91743
    MYA = 0
    MYS = 0.91743
    MZA = 0
    MZS = 0.91743

    # TODO: Check to make sure file exists
    INFILE = sys.argv[1]

    with open(INFILE) as infile, open('o.csv', 'w') as outfile:
        file_size = os.path.getsize(INFILE)
        print("filesize {}".format(file_size))
        data_size = file_size - MAIN_HEADER_SIZE
        print("data_size {}".format(data_size))
        num_pages = int(math.ceil(data_size/DATA_PAGE_SIZE))
        print("num pages {}".format(num_pages))
        
        # Read in and parse the header
        header_bytes = infile.read(MAIN_HEADER_SIZE)
        # Get the header, the mini header and the size of the mini header
        header, mini_header, mh_bytes = parse_main_header(header_bytes)

        ACCELS, MAGNES, TEMPS = get_lookup_tables(AXA, AXB, MXA, MXS)

        p = pattern(int(mini_header['BMN']))
        p_size = struct.calcsize(p)

        patterns_per_page = int(DATA_PAGE_SIZE / p_size)
        
        delta_for_burst = datetime.timedelta(milliseconds=1000/int(mini_header['BMR']))
        clk_fmt = '%Y-%m-%d %H:%M:%S'
        outfile.write("Date,Time,Ax (g),Ay (g),Az (g),Mx (mG),My (mG),Mz (mG)\n")
        for j in range(num_pages):
            print j
            buffer = StringIO()
            infile.seek(MAIN_HEADER_SIZE + DATA_PAGE_SIZE * j, os.SEEK_SET)
            mini_header_bytes = infile.read(mh_bytes)
            mh = parse_header(mini_header_bytes)
            clk = datetime.datetime.strptime(mh['CLK'], clk_fmt)
            for i in range(patterns_per_page):
                data_bytes = infile.read(p_size)
                a = struct.unpack_from(p, data_bytes)
                # ignore temp for now
                ax = map(lambda x: ACCELS[x], a[1::6])
                ay = map(lambda x: ACCELS[x], a[2::6])
                az = map(lambda x: ACCELS[x], a[3::6])
                mx = map(lambda x: MAGNES[x], a[4::6])
                my = map(lambda x: MAGNES[x], a[5::6])
                mz = map(lambda x: MAGNES[x], a[6::6])
                vs = ("%s" % (clk + delta_for_burst * k).isoformat(',') for k in range(len(ax)))
                buffer.write("\n".join(["%s,%s,%s,%s,%s,%s,%s" % t for t in zip(vs, ax, ay, az, mx, my, mz)]))
            outfile.write(buffer.getvalue())
            buffer.close()

        

if __name__ == '__main__':
    main()
