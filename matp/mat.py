from __future__ import division
import struct
import math
import os
import itertools
import datetime
import sys
from cStringIO import StringIO

MAX_UNSIGNED_SHORT = 65535
SHORT_SIGNED_MIN = -32768
SHORT_SIGNED_MAX = 32768
DEFAULT_HOST_STORAGE = {
    'AXA': 0,
    'AXB': 1024,
    'AYA': 0,
    'AYB': 1024,
    'AZA': 0,
    'AZB': 1024,
    'MXA': 0,
    'MXS': 0.91743,
    'MYA': 0,
    'MYS': 0.91743,
    'MZA': 0,
    'MZS': 0.91743,
    'TMO': 0,
    'TMR': 10000,
    'TMA': 0.0011238100354,
    'TMB': 0.0002349457073,
    'TMC': 0.0000000848361,
}

LINE_BREAK = '\r\n'
HEADER_SEPARATOR = '\x0d\x0a'
TMP_CSV_HEADERS = "Date,Time,Temperature (C)" + LINE_BREAK
ORI_CSV_HEADERS = "Date,Time,Ax (g),Ay (g),Az (g),Mx (mG),My (mG),Mz (mG)" + LINE_BREAK
ISO_SEPARATOR = ','
CLOCK_FORMAT = '%Y-%m-%d %H:%M:%S'
ORIENTATION_FORMAT = "%s,%s,%s,%s,%s,%s,%s"
TRUNCATE_MICROSECOND_DIGITS = -2
K = 1024
MAIN_HEADER_SIZE = 32 * K
DATA_PAGE_SIZE = 1024 * K

def k_to_c(kelvin):
    '''Kelvin to celcius'''
    return kelvin - 273.15

def parse_header(header_bytes, sep='\x0d\x0a'):
    '''Return the given bytes as a dictionary'''
    kvpairs = header_bytes.split(sep)
    return dict((str(kv).split(' ', 1) for kv in kvpairs if ' ' in kv))

def mh_indicies(header_bytes):
    '''Get where the mini header starts and stops inside the main header'''
    start = header_bytes.rfind('MHS')
    end = header_bytes.rfind('MHE') + 5
    return start, end

def parse_hss(hss_bytes):
    '''If there is no HSS tag use the default, otherwise parse the HSS and return it'''
    if hss_bytes.find('HSS') == -1:
        return DEFAULT_HOST_STORAGE
    # chop off the first three and chop off garbage at the end
    end_index = hss_bytes.rfind('HSE')
    hss_bytes = hss_bytes[3:end_index+3]
    hss = {}
    offset = 0
    while True:
        tag = hss_bytes[offset:offset+3]
        if tag == 'HSE':
            break
        # l is the length of the value to follow
        length = ord(hss_bytes[offset+3:offset+4])
        val = hss_bytes[offset+4:offset+4+length]
        offset += 4 + length
        hss[tag] = val
    int_tags = ['AXA','AXB', 'AYA', 'AYB', 'AZA', 'AZB', 'MXA', 'MYA', 'MZA', 'TMR', 'TMO',]
    float_tags = ['MXS', 'MYS', 'MZS', 'TMA', 'TMB', 'TMC',]
    for tag in int_tags:
        if tag in hss:
            hss[tag] = int(hss[tag])
    for tag in float_tags:
        if tag in hss:
            hss[tag] = float(hss[tag])
    return hss

def parse_main_header(header_bytes):
    '''Return three dictionaries and a value.

    Returns:
        header -- dict of values found in the main header
        mini_header -- dict of values found in the mini header in the main header
        hss -- dict of values for the host storage
        mini_header_size -- int the number of bytes the miniheader takes up
    '''
    hss_start = header_bytes.rfind('HSS')
    mh_start, mh_end = mh_indicies(header_bytes)
    mini_header = parse_header(header_bytes[mh_start:mh_end])
    header = parse_header(header_bytes[:mh_start] + header_bytes[mh_end:hss_start])
    hss = parse_hss(header_bytes[hss_start:])
    return header, mini_header, hss, mh_end - mh_start

def pattern(bmn):
    '''Build the pattern for reading data.

    This pattern is the major and all the minors up to the next major.
    '''
    endian = '<'
    temp = 'H'
    o = 'h'
    return endian + temp + str(bmn * 6) + o

def build_accelerometer_values(a, b):
    '''Build a lookup table for all possible accelerometer values'''
    values = (1/b * f + a for f in xrange(SHORT_SIGNED_MIN, SHORT_SIGNED_MAX))
    return {i: '%.5f' % acc 
            for i, acc in enumerate(values, start=SHORT_SIGNED_MIN)
    }

def build_magnetometer_values(a, s):
    '''build a lookup table for all possible magnetometer values'''
    values = (s * x + a for x in xrange(SHORT_SIGNED_MIN, SHORT_SIGNED_MAX))
    return {i: '%.2f' % mag
            for i, mag in enumerate(values, start=SHORT_SIGNED_MIN)
    }

def t_measure_to_resistance(t, tmo, tmr):
    '''Given a measurement from the device turn it into a resistance measurement'''
    r_adj = t + tmo
    return tmr * r_adj / (MAX_UNSIGNED_SHORT - r_adj)

def s(r, tma, tmb, tmc):
    '''Given a resistance measurement turn that into a celcius reading'''
    l = math.log(r)
    i = tma + tmb * l + tmc * math.pow(l, 3)
    return k_to_c(math.pow(i, -1))

def temp(num, tma, tmb, tmc, tmo, tmr):
    '''0 is invalid but we need it so our array doesn't have an off by one error'''
    if num == 0:
        return 0
    return s(t_measure_to_resistance(num, tmo, tmr), tma, tmb, tmc)

def build_thermometer_values(tma, tmb, tmc, tmo, tmr):
    '''build a lookup table for all possible thermometer values'''
    return ['%.4f' % temp(x, tma, tmb, tmc, tmo, tmr) for x in xrange(0, 65535)]

def get_lookup_tables(axa, axb, mxa, mxs, tma, tmb, tmc, tmo, tmr):
    accelerometer_values = build_accelerometer_values(axa, axb)
    magnetometer_values = build_magnetometer_values(mxa, mxs)
    # This is a straight array lookup
    thermometer_values = build_thermometer_values(tma, tmb, tmc, tmo, tmr)
    return accelerometer_values, magnetometer_values, thermometer_values

def get_ori_csv_headers():
    return ORI_CSV_HEADERS

def get_tmp_csv_headers():
    return TMP_CSV_HEADERS

def get_orientation_format():
    return ORIENTATION_FORMAT

def parse_file(lid_filename, orientation_filename, temperature_filename, default_host_storage=False):
    microsecond = datetime.timedelta(microseconds=1)
    # Entire file is this big (bytes)
    file_size = os.path.getsize(lid_filename)
    # Size of data (miniheaders are data)
    data_size = file_size - MAIN_HEADER_SIZE
    # The number of data pages that fit in this data
    num_pages = int(math.ceil(data_size/DATA_PAGE_SIZE))
    with open(lid_filename) as lid, open(orientation_filename, 'w') as ori:
        header_bytes = lid.read(MAIN_HEADER_SIZE)
        header, mini_header, hss, mh_size = parse_main_header(header_bytes)
        
        # TODO: hopefully this can go away
        if default_host_storage:
            hss = DEFAULT_HOST_STORAGE

        # TODO: pass things to these functions
        ori_csv_headers = get_ori_csv_headers()
        tmp_csv_headers = get_tmp_csv_headers()
        orientation_format = get_orientation_format()
        
        # Get everything that requires the main/mini header data
        accels, magnes, temps = get_lookup_tables(hss['AXA'], hss['AXB'],
                                                  hss['MXA'], hss['MXS'],
                                                  hss['TMA'], hss['TMB'],
                                                  hss['TMC'], hss['TMO'],
                                                  hss['TMR'],)
        p = pattern(int(mini_header['BMN']))
        p_size = struct.calcsize(p)

        # we might need orientation if TRI < ORI
        temperature_interval = int(mini_header['TRI'])
        burst_mode_rate = int(mini_header['BMR'])
        burst_delta = datetime.timedelta(milliseconds=1000/burst_mode_rate)
        pattern_delta = datetime.timedelta(seconds=temperature_interval)

        # File I/O
        ori.write(ori_csv_headers)
        tmp_buffer = StringIO()

        for page_number in xrange(num_pages):
            ori_buffer = StringIO()

            # Seek to the start of the data page
            lid.seek(MAIN_HEADER_SIZE + DATA_PAGE_SIZE * page_number, os.SEEK_SET)

            # Read the whole data page
            data_page = lid.read(DATA_PAGE_SIZE)

            # Pull out the mini header
            mh = parse_header(data_page[:mh_size])

            # TODO: look for \xff\xff\xff\xff
            data_page = data_page[mh_size:]
            patterns_in_page = int(len(data_page)/p_size)

            # Add a microsecond here to get the .000.
            # Does not effect rounding because it gets chopped off
            clk = datetime.datetime.strptime(mh['CLK'], CLOCK_FORMAT) + microsecond

            # This loop happens a total of 93-94 million times on 1gb of data
            for i in xrange(patterns_in_page):
                start = i * p_size
                stop = start + p_size
                a = struct.unpack_from(p, data_page[start:stop])
                
                tmp_buffer.write(
                    "%s,%s%s" % (
                        clk.isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS], 
                        temps[a[0]], 
                        LINE_BREAK
                    )
                )

                ax = [accels[x] for x in a[1::6]]
                ay = [accels[x] for x in a[2::6]]
                az = [accels[x] for x in a[3::6]]
                mx = [magnes[x] for x in a[4::6]]
                my = [magnes[x] for x in a[5::6]]
                mz = [magnes[x] for x in a[6::6]]
                vs = ["%s" % (clk + burst_delta * k).isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS] for k in xrange(int(len(a)/6))]
                
                ori_buffer.write(
                    LINE_BREAK.join(
                        [orientation_format % row for row in itertools.izip(vs, ax, ay, az, mx, my, mz)]
                    )
                )
                ori_buffer.write(LINE_BREAK)

                # After each pattern, a certain time has elapsed
                clk += pattern_delta
            ori.write(ori_buffer.getvalue())
            ori_buffer.close()

    with open(temperature_filename, 'w') as tmp:
        tmp.write(tmp_csv_headers)
        tmp.write(tmp_buffer.getvalue())
        tmp_buffer.close()

def main():
    # TODO: Check to make sure file exists
    infile = sys.argv[1]
    default_host_storage = bool(sys.argv[2])
    parse_file(infile, "ori.csv", "tmp.csv", default_host_storage=default_host_storage)
    

if __name__ == '__main__':
    main()