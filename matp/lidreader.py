from __future__ import print_function, division
import math
import os
import datetime
import string
import math
import struct
import itertools
'''
headers = {
    'HDS': 'Header start tag',
    'SER': 'String serial number',
    'FWV': 'Firmware version',
    'DPL': 'Deployment Logger number',
    'DFS': 'Hex address of first data page',
    'STM': 'Configured start time',
    'ETM': 'Configured end time',
    'LED': 'LEDs behavior',
    'HDE': 'header end tag',
}

mini_header_tags = {
    'MHS': 'Miniheader start tag',
    'CLK': 'Clock time at start of 1024k block',
    'TMP': 'Bool if temp is enabled 1=true 0=false',
    'ACL': 'Bool if accelerometer is enabled',
    'MGN': 'Bool if Magnetometer is enabled',
    'TRI': 'Temperature interval',
    'ORI': 'Orientation interval',
    'BMR': 'Burst Mode Rate, hz',
    'BMN': 'Burst Mode Samples',
    'BAT': 'Battery in mV, hex, little endian',
    'STS': 'status bits',
    'MHE': 'Miniheader end tag',
}

calibration_tags = {
    # Temperature
    'TMO': 'A/D offset in counts',
    'TMR': 'Balance resistor value',
    'TMA': 'Steinhart "A" offset coefficient',
    'TMB': 'Steinhart "B" ln(R) coefficient',
    'TMC': 'Steinhart "C" ln(R)^3 coefficient',
    # Accelerometer X-Axis
    'AXA': 'zero point offset',
    'AXB': 'slope',
    # Accelerometer Y-Axis

    'AYA': 'zero point offset',
    'AYB': 'slope',
    # Magnetometer X-Axis
    'MXA': 'Hard Iron Offset',
    'MXS': 'Scale Factor',
    # Magnetometer Y-Axis
    'MYA': 'Hard Iron Offset',
    'MYS': 'Scale Factor',
    # Magnetometer Z-Axis
    'MZA': 'Hard iron offset',
    'MZS': 'Scale factor',
}
'''
K = 1024 # 1 kb in bytes
HEADER_PAGE_SIZE = 32 * K # 32 kb in bytes
DATA_PAGE_SIZE = 1024 * K # 1024 kb in bytes
DATA_SIZE = 2 # bytes
DEFAULT_HOST_STORAGE = {
    'TMO': 0,
    'TMR': 10000,
    'TMA': 0.0011238100354,
    'TMB': 0.0002349457073,
    'TMC': 0.0000000848361,
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
}

# TODO: use better version from other lidreader_numpy.py
def parse_header(header_line):
    headers = {}
    metatags = set(['HDS', 'HDE', 'MHS', 'MHE'])
    # \x0d \x0a separate each tag
    for line in header_line.split('\n'):
        line = line.rstrip()
        # If there is nothing after a strip it was all whitespace
        if not line:
            continue
        tag = line[:3]
        # bail out of the end main header tag
        if tag == 'HDE':
            return headers
        # Ignore start/end tags
        if tag in metatags:
            tag = ''
            continue
        # Special parsing for host storage
        if tag == 'HSS':
            headers['Host Storage'] = parse_hss_line(line)
            tag = ''
            continue
        headers[tag] = line.split(' ', 1)[1]
    return headers

def parse_hss_line(hss_line):
    index = hss_line.rfind('HSE')
    data = hss_line[:index+3]
    tag = ''
    value = ''
    host_storage = {}
    for c in data:
        if ord(c) <= 16:
            continue
        if len(tag) == 3:
            if tag == 'HSS' or tag == 'HSE':
                tag = c
                continue
            if c in string.uppercase:
                host_storage[tag] = value
                tag = c
                value = ''
                continue
            value += c
            continue
        tag += c
    return host_storage

MAX_UNSIGNED_SHORT = 65535

def measurement_to_resistance(r, tmo, tmr):
    '''r is the measured value from the device
       tmo is tha A/D offset
    '''
    r_adj = r + tmo
    return tmr * r_adj / (MAX_UNSIGNED_SHORT - r_adj)

#TODO: How do I know if I've managed to get a temperature or not? 0.0 is a valid temp.
def convert_temp(temp, a, b, c, tmo, tmr):
    r = measurement_to_resistance(temp, tmo, tmr)
    return steinhart(r, a, b, c)

def convert_accel(accel, axa, axb, aya, ayb, aza, azb):
    x = accel[0]
    y = accel[1]
    z = accel[2]
    return (acceleration(x, axb, axa), acceleration(y, ayb, aya), acceleration(z, azb, aza))

def convert_magne(magne, mxa, mxs, mya, mys, mza, mzs):
    x = magne[0]
    y = magne[1]
    z = magne[2]
    return (magnetometer(x, mxs, mxa), magnetometer(y, mys, mya), magnetometer(z, mzs, mza))

def steinhart(resistance, a, b, c):
    '''a, b, c are floats resistance is an int'''
    r = float(resistance)
    l = math.log(r)
    inv_temp = a + b * l + c * math.pow(l, 3)
    return round(k_to_c(pow(inv_temp, -1)), 4)

def k_to_c(kelvin):
    '''kelvin to celcius'''
    return kelvin - 273.15

def orientation_pattern(accel, magne):
    '''Is little endian'''
    pattern = ''
    if accel and magne:
        pattern = 'hhhhhh'
    elif accel or magne:
        pattern = 'hhh'
    return pattern

def temp_pattern(temp):
    '''Is little endian'''
    pattern = ''
    if temp:
        pattern = 'H'
    return pattern

def get_pattern(temp, accel, magne, temp_i, ori_i, burst_num, burst_rate):
    tp = temp_pattern(temp)
    op = orientation_pattern(accel, magne)
    pattern = [(0, '<' + tp)]
    for i in range(0, temp_i//ori_i):
        pattern += [(ori_i * i * 10e5 + j/burst_rate * 10e5, '<' + m) for j, m in enumerate(itertools.repeat(op, burst_num))]
    return pattern

def major_minor_patterns(temp, accel, magne, temperature_interval, orientation_interval):
    t_pattern = temp_pattern(temp)
    o_pattern = orientation_pattern(accel, magne)

    major_pattern = '<' + t_pattern + o_pattern
    
    # if the intervals are the same, we only use the major interval
    minor_pattern = major_pattern
    if temperature_interval < orientation_interval:
        minor_pattern = '<' + t_pattern
    elif temperature_interval > orientation_interval:
        minor_pattern = '<' + o_pattern
    
    # if there is no temp or no orientation then major and minor are the same.
    if not temperature_interval or not orientation_interval:
        minor_pattern = major_pattern
    
    return major_pattern, minor_pattern

def build_full_pattern(major, minor, burst_mode_rate, frequency, tmp_interval, ori_interval):
    print("Major:\n{}\nMinor:\n{}\n".format(major, minor))
    if ori_interval < tmp_interval:
        # Getting one too many items so we cut one off latner
        # Subtract one from the secondary part because it shows up in the major already
        pattern =  [(0, major)] + [((i/frequency) * 10e5, m) for i, m in enumerate(itertools.repeat(minor, burst_mode_rate-1), start=1)]
        for i in range(1, tmp_interval/ori_interval):
            # Don't subtract one, there is no major part.
            pattern += [(ori_interval * i * 10e5 + (j/frequency) * 10e5, m) for j, m in enumerate(itertools.repeat(minor, burst_mode_rate))]
        return pattern

#        return [(tmp_interval * 10e5, major)] + [((1.0/frequency) * 10e5, m) for m in itertools.repeat(minor, burst_mode_rate)] * (tmp_interval/ori_interval)

def pattern_iterator(major, minor, burst_mode_rate, frequency, tmp_i, ori_i):
    #build_ful_pattern returns one too many
    for pattern in build_full_pattern(major, minor, burst_mode_rate, frequency, tmp_i, ori_i):
        yield pattern

def split_binary_data(data):
    '''Return the miniheaders and the data'''
    index = data.find('MHE')
    # +3 because we want to ignore MHE +2 beause of \x0d\x0a
    return parse_header(data[:index]), data[index+3+2:]
    
def rate_to_delta(rate):
    '''Return the timedelta given a rate in hertz'''
    return datetime.timedelta(microseconds=(1.0/rate) * 10e5)

# Accel: struct.unpack('<h', '\x70\xfc')
accel_lookup = {}
def acceleration(binary_data, m, b):
    '''Given the binary data and two constants for y = mx + b
    return the acceleration
    m = AXB, b = AXA
    '''
    if binary_data in accel_lookup:
        return accel_lookup[binary_data]
    accel = round((1.0/m * binary_data) + b, 5)
    accel_lookup[binary_data] = accel
    return accel

magne_lookup = {}
def magnetometer(binary_data, m, b):
    '''m = MXS, b = MXA'''
    if binary_data in magne_lookup:
        return magne_lookup[binary_data]
    mgn = round(m * binary_data + b, 2)
    magne_lookup[binary_data] = mgn
    return mgn

import pprint
pp = pprint.PrettyPrinter(indent=4)

def parse_vals(temp, accel, magne, a, b, c, tmo, tmr, axa, axb, aya, ayb, aza, azb,
               mxa, mxs, mya, mys, mza, mzs):
    '''vals is a tuple'''
    def fn(vals):
        temperature = 0.0
        acceleration = ()
        magnetometer = ()
        size = len(vals)
        if size == 7:
            temperature = convert_temp(vals[0], a, b, c, tmo, tmr)
            acceleration = convert_accel(vals[1:4], axa, axb, aya, ayb, aza, azb)
            magnetometer = convert_magne(vals[4:], mxa, mxs, mya, mys, mza, mzs)
        elif size == 6:
            acceleration = convert_accel(vals[:3], axa, axb, aya, ayb, aza, azb)
            magnetometer = convert_magne(vals[3:], mxa, mxs, mya, mys, mza, mzs)
        elif size == 3:
            if accel:
                acceleration = convert_accel(vals, axa, axb, aya, ayb, aza, azb)
            if magne:
                magnetometer = convert_magne(vals, mxa, mxs, mya, mys, mza, mzs)
        elif size == 1:
            temperature = convert_temp(vals[0], a, b, c, tmo, tmr)

        return temperature, acceleration, magnetometer
    return fn


def main():
    import sys
    print(sys.argv)

    # TODO: Check to make sure file exists
    INFILE = sys.argv[1]#'big/Big_File.lid'
    # TODO: print where file will be written
    OUTFILE = 'out.txt'
    file_size = os.path.getsize(INFILE)
    data_size = file_size - HEADER_PAGE_SIZE
    num_pages = math.ceil(data_size / DATA_PAGE_SIZE)
    END_MARKER = '\xff'*14
    print("Reading {} pages".format(num_pages))
    out = ''
    with open(INFILE) as f, open(OUTFILE, 'w') as o:
        #with open('simple.lid') as f:
        #with open('complex.lid') as f: #success
        header = f.read(HEADER_PAGE_SIZE)
        headers = parse_header(header)
        if 'Host Storage' not in headers:
            headers['Host Storage'] = DEFAULT_HOST_STORAGE

    a = float(headers['Host Storage']['TMA'])
    b = float(headers['Host Storage']['TMB'])
    c = float(headers['Host Storage']['TMC'])
    tmo = int(headers['Host Storage']['TMO'])
    tmr = int(headers['Host Storage']['TMR'])
    axa = int(headers['Host Storage']['AXA'])
    axb = int(headers['Host Storage']['AXB'])
    aya = int(headers['Host Storage']['AYA'])
    ayb = int(headers['Host Storage']['AYB'])
    aza = int(headers['Host Storage']['AZA'])
    azb = int(headers['Host Storage']['AZB'])
    mxa = float(headers['Host Storage']['MXA'])
    mxs = float(headers['Host Storage']['MXS'])
    mya = float(headers['Host Storage']['MYA'])
    mys = float(headers['Host Storage']['MYS'])
    mza = float(headers['Host Storage']['MZA'])
    mzs = float(headers['Host Storage']['MZS'])
    
    # example files list this value as 1 which is wrong
    mxs = 0.91743
    mys = 0.91743
    mzs = 0.91743

    big_i = int(headers['TRI'])
    small_i = int(headers['ORI'])
    if big_i < small_i:
        big_i, small_i = small_i, big_i
        parse_function = parse_vals(headers['TMP'], headers['ACL'], headers['MGN'],
                                    a, b, c, tmo, tmr, axa, axb, aya, ayb, aza, azb,
                                    mxa, mxs, mya, mys, mza, mzs)
        # how many pages of data?
        for k in range(int(num_pages)):
            print("reading page: {}".format(k))
            p1 = f.read(DATA_PAGE_SIZE)
            miniheader, data = split_binary_data(p1)
            clk = miniheader['CLK']
            current_time = datetime.datetime.strptime(clk, "%Y-%m-%d %H:%M:%S")
            total_size = 0
            # We don't want to range forever, we want to get a page at a time and
            # iterate over each page
            i = 0
            run = True
            page = []
            while run:
                # Given the headers get an infinite generator
                pattern_iterator = get_pattern(int(headers['TMP']), int(headers['ACL']),
                                               int(headers['MGN']), int(headers['TRI']),
                                               int(headers['ORI']), int(headers['BMN']),
                                               int(headers['BMR']))
                if i > 0:
                    current_time = datetime.datetime.strptime(clk, "%Y-%m-%d %H:%M:%S")
                    current_time += datetime.timedelta(seconds=big_i * i)
                    for j, (time, pattern) in enumerate(pattern_iterator):
                        if data[total_size:total_size+14] == END_MARKER:
                            run = False
                            break
                            offset = datetime.timedelta(microseconds=time)
                            time = current_time + offset
                            
                size = struct.calcsize(pattern)
                vals = struct.unpack(pattern, data[total_size:total_size + size])
                total_size += size
                page.append((time.isoformat(), vals))

            i += 1
            [o.write("%s: %s\n" % (time, parse_function(vals))) for time, vals in page]
