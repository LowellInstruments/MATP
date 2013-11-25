from __future__ import division
import struct
import math
import os
import itertools
import datetime
import sys
from cStringIO import StringIO

DEBUG=False

def debug(msg):
    if DEBUG:
        print(msg)

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

ISO_SEPARATOR = ','
CLOCK_FORMAT = '%Y-%m-%d %H:%M:%S'

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
        length = int(hss_bytes[offset+3:offset+4], 16)
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

# Passing in values like they come in from the mini header
def get_ori_csv_headers(accel='1', magne='1'):
    '''Returns the header for the orientation CSV file'''
    date_header = "Date,Time"
    accel_header = "Ax (g),Ay (g),Az (g)"
    magne_header = "Mx (mG),My (mG),Mz (mG)"
    headers = [date_header]
    if accel == '1':
        headers.append(accel_header)
    if magne == '1':
        headers.append(magne_header)
    return ','.join(headers) + LINE_BREAK

def get_tmp_csv_headers(temp='1'):
    '''Returns the header for the Temperature CSV file'''
    date_header = "Date,Time"
    temp_header = "Temperature (C)"
    headers = [date_header]
    if temp == '1':
        headers.append(temp_header)
    return ','.join(headers) + LINE_BREAK
    
def get_orientation_format(accel='1', magne='1'):
    '''returns the format for the orientation csv file'''
    fmt = ['%s']
    number = 1
    if accel == '1':
        number += 3
    if magne == '1':
        number += 3
    return ','.join(fmt * number)

def pattern(bmn, ori=1, tri=1, tmp=True, acl=True, mgn=True):
    '''Build the pattern for reading data.
    This pattern is the major and all the minors up to the next major.
    '''
    endian = '<'
    temp = ''
    o = ''
    num = 0
    if tmp:
        temp = 'H'
    if acl or mgn:
        o = 'h'

    if acl:
        num += 3
    if mgn:
        num += 3

    if tri < ori:
        mul = int(ori/tri)
        return endian + temp + str(bmn * num) + o + str(mul-1) + temp
    mul = int(tri/ori)
    return endian + temp + str(bmn * num * mul) + o


'''write orientation data and temperature data to the buffers'''
def all_data_to_buffers(a, tmp_buffer=None, ori_buffer=None,
                        accels=None, magnes=None, temps=None, clk=None,
                        tri=None, ori=None, p_size=None, ori_delta=None,
                        burst_delta=None, orientation_format=None):
    temp_value = a[0]
    a = a[1:]
    tmp_buffer.write(
        "%s,%s%s" % (
            clk.isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS], 
            temps[temp_value],
            LINE_BREAK
        )
    )
    # orientation pattern size
    ori_p_size = int((p_size - 2)/(tri/ori)/2) # divide by size of short
    for j in xrange(int(len(a)/ori_p_size)):
        left = ori_p_size * j
        right = ori_p_size * j + ori_p_size
        d = a[left:right]
        ax = [accels[x] for x in d[0::6]]
        ay = [accels[x] for x in d[1::6]]
        az = [accels[x] for x in d[2::6]]
        mx = [magnes[x] for x in d[3::6]]
        my = [magnes[x] for x in d[4::6]]
        mz = [magnes[x] for x in d[5::6]]
        vs = ["%s" % (clk + burst_delta * k).isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS] for k in xrange(int(len(d)/6))]
        ori_buffer.write(
            LINE_BREAK.join(
                [orientation_format % row for row in itertools.izip(vs, ax, ay, az, mx, my, mz)]
            )
        )
        ori_buffer.write(LINE_BREAK)
        clk += ori_delta
    return
        

'''The choice to return a closure is that I don't want
to abstract the common bits because this loop runs so many times.
If the common bits got abstracted, that would mean a function call
in the places where the code is slightly different and I don't want
the python overhead of calling functions hundreds of thousands of times.

The choice to use closures vs objects just feels more natural in this
situation.
'''
def get_data_page_parser(burst_delta=None, ori_delta=None, tmp_delta=None,
                         orientation_format=None, temps=None, 
                         accels=None, magnes=None, tmp=None, acl=None, mgn=None,
                         tri=None, ori=None):
    '''Return the parser function to parse this specific type of data'''

    '''This is for only a temperature measurement
    NOTE: This is not returning yet since it's untested
    '''
    def tmp_only(data_page, patterns_in_page=None,
                    p=None, p_size=None, clk=None, ori_buffer=None,
                    tmp_buffer=None):
        '''If there is a really large file with only a temperature measurement
        this could be very slow since we read temps 1 at a time'''
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

            # After each pattern, a certain time has elapsed
            clk += tmp_delta

    '''This is for no_a and tri > ori'''
    def no_a_ori_lte_tri(data_page, patterns_in_page=None,
                    p=None, p_size=None, clk=None, ori_buffer=None,
                    tmp_buffer=None):
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
            
            mx = [magnes[x] for x in a[1::3]]
            my = [magnes[x] for x in a[2::3]]
            mz = [magnes[x] for x in a[3::3]]
            vs = ["%s" % (clk + burst_delta * k).isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS] for k in xrange(int(len(a)/3))]
            
            ori_buffer.write(
                LINE_BREAK.join(
                    [orientation_format % row for row in itertools.izip(vs, mx, my, mz)]
                )
            )
            ori_buffer.write(LINE_BREAK)
            
            # After each pattern, a certain time has elapsed
            clk += tmp_delta

    '''This is for no magnetometer and tri >= ori'''
    def no_m_ori_lte_tri(data_page, patterns_in_page=None,
                    p=None, p_size=None, clk=None, ori_buffer=None,
                    tmp_buffer=None):
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
            
            ax = [accels[x] for x in a[1::3]]
            ay = [accels[x] for x in a[2::3]]
            az = [accels[x] for x in a[3::3]]
            vs = ["%s" % (clk + burst_delta * k).isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS] for k in xrange(int(len(a)/3))]
            
            ori_buffer.write(
                LINE_BREAK.join(
                    [orientation_format % row for row in itertools.izip(vs, ax, ay, az)]
                )
            )
            ori_buffer.write(LINE_BREAK)
            
            # After each pattern, a certain time has elapsed
            clk += tmp_delta

    '''This is for all measurements and tri >= ori'''
    def all_ori_lte_tri(data_page, patterns_in_page=None,
                    p=None, p_size=None, clk=None, ori_buffer=None,
                    tmp_buffer=None):
        for i in xrange(patterns_in_page):
            start = i * p_size
            stop = start + p_size

            # This happens at the last section of the data page.
            if len(data_page[start:stop]) < p_size:
                # we need an entirely new pattern if this is the case
                new_p = '<H' + str(int(len(data_page[start:])/2)-1) + 'h'
                a = struct.unpack_from(new_p, data_page[start:])
                # TODO: \xff * 14 might come halfway in the page
                end_index = data_page[start:].rfind('\xff' * 14)
                if end_index > -1:
                    return
                all_data_to_buffers(a, tmp_buffer=tmp_buffer, ori_buffer=ori_buffer,
                                    accels=accels, magnes=magnes, temps=temps, clk=clk,
                                    tri=tri, ori=ori, p_size=p_size, ori_delta=ori_delta,
                                    burst_delta=burst_delta, orientation_format=orientation_format)
                return
            a = struct.unpack_from(p, data_page[start:stop])
            all_data_to_buffers(a, tmp_buffer=tmp_buffer, ori_buffer=ori_buffer,
                                accels=accels, magnes=magnes, temps=temps, clk=clk,
                                tri=tri, ori=ori, p_size=p_size, ori_delta=ori_delta,
                                burst_delta=burst_delta, orientation_format=orientation_format)
            clk += tmp_delta

    def all_ori_gt_tri(data_page, patterns_in_page=None,
                       p=None, p_size=None, clk=None, ori_buffer=None,
                       tmp_buffer=None):
        pass

    if tmp and acl and mgn:
        if ori <= tri:
            debug("Returning all_ori_lte_tri")
            return all_ori_lte_tri
        debug("Returning all_ori_gt_tri")
        return all_ori_gt_tri
    
    if tmp and acl and not mgn:
        debug("Returning no_m_ori_lte_tri")
        return no_m_ori_lte_tri
    
    if tmp and not acl and mgn:
        debug("returning no_a_ori_lte_tri")
        return no_a_ori_lte_tri

        
def parse_file(lid_filename, ori_fh, temp_fh, default_host_storage=False, debugger=False):
    global DEBUG
    DEBUG = debugger
    # Microsecond is used to add a bit of time to a number to get decimal points. 
    microsecond = datetime.timedelta(microseconds=1)

    # Entire file is this big (bytes)
    file_size = os.path.getsize(lid_filename)

    # Size of data (miniheaders are data) (filesize less header)
    data_size = file_size - MAIN_HEADER_SIZE

    # The number of data pages that fit in this data
    num_pages = int(math.ceil(data_size/DATA_PAGE_SIZE))
    with open(lid_filename, 'rb') as lid, open(orientation_filename, 'w') as ori:
        header_bytes = lid.read(MAIN_HEADER_SIZE)
        header, mini_header, hss, mh_size = parse_main_header(header_bytes)
        
        # TODO: hopefully this can go away
        if default_host_storage:
            hss = DEFAULT_HOST_STORAGE

        # Get everything that requires the main/mini header data/hss
        ori_csv_headers = get_ori_csv_headers(accel=mini_header['ACL'], magne=mini_header['MGN'])
        tmp_csv_headers = get_tmp_csv_headers(temp=mini_header['TMP'])
        orientation_format = get_orientation_format(accel=mini_header['ACL'], magne=mini_header['MGN'])
        accels = build_accelerometer_values(hss['AXA'], hss['AXB'])
        magnes = build_magnetometer_values(hss['MXA'], hss['MXS'])
        temps = build_thermometer_values(hss['TMA'], hss['TMB'], hss['TMC'], hss['TMO'], hss['TMR'])
        p = pattern(int(mini_header['BMN']), 
                    tri=int(mini_header['TRI']), 
                    ori=int(mini_header['ORI']),
                    tmp=bool(int(mini_header['TMP'])), 
                    acl=bool(int(mini_header['ACL'])), 
                    mgn=bool(int(mini_header['MGN'])))
        p_size = struct.calcsize(p)
        # we might need orientation_interval if TRI < ORI
        temperature_interval = int(mini_header['TRI'])
        orientation_interval = int(mini_header['ORI'])
        burst_mode_rate = int(mini_header['BMR'])
        burst_delta = datetime.timedelta(milliseconds=1000/burst_mode_rate)
        # TODO: get pattern delta, might not be TRI
        orientation_delta = datetime.timedelta(seconds=orientation_interval)
        temperature_delta = datetime.timedelta(seconds=temperature_interval)

        # File I/O
        ori.write(ori_csv_headers)
        tmp_buffer = StringIO()

        parse_data_page = get_data_page_parser(burst_delta=burst_delta, 
                                               ori_delta=orientation_delta,
                                               tmp_delta=temperature_delta,
                                               orientation_format=orientation_format,
                                               temps=temps, accels=accels, magnes=magnes,
                                               tmp=bool(int(mini_header['TMP'])),
                                               acl=bool(int(mini_header['ACL'])), 
                                               mgn=bool(int(mini_header['MGN'])),
                                               tri=int(mini_header['TRI']),
                                               ori=int(mini_header['ORI']),)


        for page_number in xrange(num_pages):
            debug(page_number)
            ori_buffer = StringIO()

            # Seek to the start of the data page
            lid.seek(MAIN_HEADER_SIZE + DATA_PAGE_SIZE * page_number, os.SEEK_SET)

            # Read the whole data page
            data_page = lid.read(DATA_PAGE_SIZE)

            # Pull out the mini header
            mh = parse_header(data_page[:mh_size])

            # TODO: look for \xff\xff\xff\xff
            data_page = data_page[mh_size:]

            patterns_in_page = int(math.ceil((len(data_page)/p_size)))

            # Add a microsecond here to get the .000.
            # Does not effect rounding because it gets chopped off
            clk = datetime.datetime.strptime(mh['CLK'], CLOCK_FORMAT) + microsecond

            # writing things to ori_buffer and tmp_buffer are the only real side effects
            parse_data_page(data_page, patterns_in_page=patterns_in_page,
                            p=p, p_size=p_size, clk=clk, ori_buffer=ori_buffer,
                            tmp_buffer=tmp_buffer)

            ori.write(ori_buffer.getvalue())
            ori_buffer.close()

    with open(temperature_filename, 'w') as tmp:
        tmp.write(tmp_csv_headers)
        tmp.write(tmp_buffer.getvalue())
        tmp_buffer.close()

def main():
    if len(sys.argv) < 2:
        print("Need to specify a file")
    # TODO: Check to make sure file exists
    infile = sys.argv[1]
    default_host_storage = False
    if len(sys.argv) > 2:
        default_host_storage = sys.argv[2]
    with open("ori.csv", "w") as ori, open("tmp.csv", "w") as tmp:
        parse_file(infile, ori, tmp, default_host_storage=default_host_storage, debugger=True)
    

if __name__ == '__main__':
    main()
