from __future__ import division
import struct
import math
import os
import datetime
import sys
from cStringIO import StringIO

DEBUG=os.getenv('DEBUG', False)

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

HEADER_SEPARATOR = '\x0d\x0a'

ISO_SEPARATOR = ','
CLOCK_FORMAT = '%Y-%m-%d %H:%M:%S'

TRUNCATE_MICROSECOND_DIGITS = -2
K = 1024
MAIN_HEADER_SIZE = 32 * K
DATA_PAGE_SIZE = 1024 * K

# Length of header tags
TAG_LEN = 3

def k_to_c(kelvin):
    '''Kelvin to celcius'''
    return kelvin - 273.15

def parse_header(header_bytes, sep=HEADER_SEPARATOR):
    '''Return the given bytes as a dictionary'''
    kvpairs = header_bytes.split(sep)
    return dict((str(kv).split(' ', 1) for kv in kvpairs if ' ' in kv))

def mh_indicies(header_bytes):
    '''Get where the mini header starts and stops inside the main header'''
    start = header_bytes.rfind('MHS')
    end = header_bytes.rfind('MHE') + 5 # +5 for MHE\x0d\x0a
    return start, end

def clean_hss(hss_bytes):
    '''Return the hss bytes between HSS and HSE'''
    start = hss_bytes.find('HSS')
    end = hss_bytes.rfind('HSE') + 3
    return str(hss_bytes[start:end])

def parse_hss(hss_bytes):
    '''If there is no HSS tag use the default, otherwise parse the HSS and return it
    
    This parses strings like this: "ABC13CDE41234"
    Into this: {'ABC': 3, 'CDE': 1234}
    '''
    if hss_bytes.find('HSS') == -1:
        return DEFAULT_HOST_STORAGE
    hss_bytes = clean_hss(hss_bytes)
    hss = {}
    offset = 0
    while True:
        tag = hss_bytes[offset:offset+TAG_LEN]
        if tag == 'HSS':
            offset += 3
            continue
        if tag == 'HSE':
            break
        length = int(hss_bytes[offset+TAG_LEN:offset+TAG_LEN+1], 16)
        val = hss_bytes[offset+TAG_LEN+1:offset+TAG_LEN+1+length]
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
    return ','.join(headers) + os.linesep

def get_tmp_csv_headers(temp='1'):
    '''Returns the header for the Temperature CSV file'''
    date_header = "Date,Time"
    temp_header = "Temperature (C)"
    headers = [date_header]
    if temp == '1':
        headers.append(temp_header)
    return ','.join(headers) + os.linesep
    
def get_orientation_format(accel='1', magne='1'):
    '''returns the format for the orientation csv file'''
    fmt = ['%s']
    number = 1
    if accel == '1':
        number += 3
    if magne == '1':
        number += 3
    return ','.join(fmt * number)

def get_temp_patterns(ori, tri, tmp):
    '''returns a tuple, first pattern and second pattern'''
    if not tmp:
        return ('', '')
    mul = ''
    if tri < ori:
        mul = int(ori/tri)
        return ('H', '%dH' % (mul-1))
    return ('H', '')

def get_ori_pattern(ori, tri, bmn, acl, mgn, size=None):
    '''Returns the orientation pattern based on the input'''
    if not acl and not mgn:
        return ''
    num = 0
    if acl:
        num += 3
    if mgn:
        num += 3

    mul = 1
    total = bmn * num
    if tri > ori:
        mul = int(tri/ori)
    return '%d%s' % (total * mul, 'h')

def pattern(bmn, ori=1, tri=1, tmp=True, acl=True, mgn=True, size=None):
    '''Build the pattern for reading data.
    This pattern is the major and all the minors up to the next major.
    '''
    endian = '<'
    temp_patterns = get_temp_patterns(ori, tri, tmp)
    ori_pattern = get_ori_pattern(ori, tri, bmn, acl, mgn)

    # Here is where the logic for partial patterns needs to go.
    # Using the size, figure out how many TMP and ORI patterns you can read.
    # Note: this will probably require temp_patterns and ori_pattern to return numbers
    #  instead of actual patterns.
    
    return '%s%s%s%s' % (endian, temp_patterns[0], ori_pattern, temp_patterns[1])

def write_accellerations(acl_data, ori_buffer=None, clk=None, accels=None, ori_delta=None,
                        burst_delta=None, bmn=None, orientation_format=None):
    '''This function will be used when we are measuring only ACL and not MGN'''
    pass

def write_magnetometers(mgn_data, ori_buffer=None, clk=None, magnes=None, ori_delta=None,
                        burst_delta=None, bmn=None, orientation_format=None):
    '''This function will be used when we are measuring only MGN and not ACL'''
    pass

def write_orientation(ori_data, ori_buffer=None, clk=None, accels=None, magnes=None, ori_delta=None, 
                      burst_delta=None, bmn=None, orientation_format=None):
    '''Write the orientation data to the orientation buffer'''
    for i in xrange(int(len(ori_data)/6)):
        left = 6 * i
        right = 6 * (i + 1)
        d = ori_data[left:right]
        ori_buffer.write(
            (orientation_format+'%s') % (clk.isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS], 
                                         accels[d[0]], accels[d[1]], accels[d[2]], 
                                         magnes[d[3]], magnes[d[4]], magnes[d[5]],
                                         os.linesep,)
        )
        clk += burst_delta

def write_temperature(tmp_data, tmp_buffer=None, temps=None, clk=None, tmp_delta=None):
    '''Write the tmp data to the temperature buffer'''
    for t in tmp_data:
        tmp_buffer.write(
            "%s,%s%s" % (
                clk.isoformat(ISO_SEPARATOR)[:TRUNCATE_MICROSECOND_DIGITS],
                temps[t],
                os.linesep,
            )
        )
        clk += tmp_delta

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
                         tri=None, ori=None, bmn=None):
    '''Return the parser function to parse this specific type of data
   
    MGN: 1 or 0
    ACL: 1 or 0
    TMP: 1 or 0
    TRI >= or < ORI
    
      MGN ACL TMP TRI comp ORI
    *  1   1   1   >=
    *  1   1   1   <
    *  1   1   0   N/A
    *  1   0   1   >=
    *  1   0   1   <
    *  1   0   0   N/A
    *  0   1   1   >=
    *  0   1   1   <
    *  0   1   0   N/A
    *  0   0   1   N/A
    '''


    '''This is for all measurements and tri >= ori'''
    def all_ori_lte_tri(data_page, patterns_in_page=None,
                    p=None, p_size=None, clk=None, ori_buffer=None,
                        tmp_buffer=None, bmn=bmn):
        for i in xrange(patterns_in_page):
            start = i * p_size
            stop = start + p_size

            # This happens at the last section of the data page.
            if len(data_page[start:stop]) < p_size:
                # we need an entirely new pattern if this is the case
                new_p = '<H' + str(int(len(data_page[start:])/2)-1) + 'h'
                # TODO: \xff * 14 might come halfway in the page
                end_index = data_page[start:].rfind('\xff' * 14)
                if end_index > -1:
                    return
                a = struct.unpack_from(new_p, data_page[start:])
            else:
                a = struct.unpack_from(p, data_page[start:stop])
            
            t_data = a[0:1]
            o_data = a[1:]
            write_temperature(t_data, tmp_buffer=tmp_buffer, temps=temps, clk=clk,
                              tmp_delta=tmp_delta)
            write_orientation(o_data, ori_buffer=ori_buffer, clk=clk, accels=accels,
                              magnes=magnes, ori_delta=ori_delta, burst_delta=burst_delta,
                              bmn=bmn, orientation_format=orientation_format)
            clk += tmp_delta


    def all_ori_gt_tri(data_page, patterns_in_page=None,
                       p=None, p_size=None, clk=None, ori_buffer=None,
                       tmp_buffer=None, bmn=bmn):
        for i in xrange(patterns_in_page):
            start = i * p_size
            stop = start + p_size
            if len(data_page[start:stop]) < p_size:
                new_p = pattern(bmn, ori=ori, tri=tri, tmp=tmp, acl=acl, 
                                mgn=mgn, size=len(data_page[start:stop]))
                # get the number of remaining bytes
                remaining = len(data_page[start:stop])
                # get number of h bytes needed in original pattern
                h_index = p.rindex('h')
                # <H12h59H => H + 12 h = 13
                hs = int(p[2:h_index]) + 1
                # No partial intervals are allowed:
                if hs * 2 > remaining:
                    # pull out one temp
                    return
                # 60 / 2 = 30 (since each short is 2 bytes)
                # 30 - 13 = 17 H measurements remaining
                new_p = p[:h_index+1] + str(int(remaining/2) - hs) + 'H'
                end_index = data_page[start:].rfind('\xff' * 14)
                if end_index > -1:
                    return
                a = struct.unpack_from(new_p, data_page[start:])
            else:
                a = struct.unpack_from(p, data_page[start:stop])


            t_data = a[0:1] + a[bmn*6+1:]
            o_data = a[1:bmn * 6 + 1]
            if tri > ori:
                t_data = a[0:1]
                o_data = a[1:]
    
            write_temperature(t_data, tmp_buffer=tmp_buffer, temps=temps, clk=clk,
                              tmp_delta=tmp_delta)
            write_orientation(o_data, ori_buffer=ori_buffer, clk=clk, accels=accels,
                              magnes=magnes, ori_delta=ori_delta, burst_delta=burst_delta,
                              bmn=bmn, orientation_format=orientation_format)

            clk += ori_delta

    return all_ori_gt_tri

        
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
    with open(lid_filename, 'rb') as lid:
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
        ori_fh.write(ori_csv_headers)
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
                                               ori=int(mini_header['ORI']),
                                               bmn=int(mini_header['BMN']),)


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

            ori_fh.write(ori_buffer.getvalue())
            ori_buffer.close()

            
    temp_fh.write(tmp_csv_headers)
    temp_fh.write(tmp_buffer.getvalue())
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
