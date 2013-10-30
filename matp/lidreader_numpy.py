import datetime
import numpy as np
import pandas as pd
import os

# Given a series of bytes
# look for your start and end
# 

class Header(object):
    SPLIT_BYTES = '\x0d\x0a'

    def split_header(self, header_bytes):
        '''Split a byte array into header pieces'''
        return header_bytes.split(self.SPLIT_BYTES)[:-1]

    def make_settings(self, split_headers):
        '''Given split headers, return a dict representing the settings'''
        return dict(
            (str(setting).split(' ', 1) for setting in split_headers if ' ' in setting)
        )
        
    @property
    def types(self):
        '''return a list of tuples
        Each tuple contains a conversion function and a list of keys to convert
        '''
        return [
            (int, self.INT_TYPES),
        ]

    def convert_types(self):
        '''Convert types we care about'''
        for fn, keys in self.types:
            for key in keys:
                self.settings[key] = fn(self.settings[key])

class MiniHeader(Header):
    INT_TYPES = ['TMP', 'ACL', 'MGN', 'BMR', 'BMN', 'TRI', 'ORI']
    def __init__(self, mini_header_bytes):
        '''Given the bytes from MHS to MHE'''
        self.dtype_bytes = len(mini_header_bytes)
        split_header = self.split_header(mini_header_bytes)
        self.settings = self.make_settings(split_header)
        self.convert_types()

    @property
    def dtype(self):
        return np.dtype([('s', np.str_, self.dtype_bytes)])


class Settings(Header):
    INT_TYPES = ['LED', 'DPL']
    def __init__(self, header_bytes):
        # find the end of the header
        index = header_bytes.rfind('HDE')
        # only use the important bytes +3 for HDE +2 for \x0d\x0a
        header_bytes = header_bytes[:index+5]
        # start and end adjusted for the mini header
        start, end = self.mini_header_indicies(header_bytes)
        self.mini_header = MiniHeader(header_bytes[start:end])
        # pull out the mini header
        header_bytes = header_bytes[:start] + header_bytes[end:]
        # split the settings on the expected bytes
        settings = self.split_header(header_bytes)
        # build a dict of settings ignoring empty values
        self.settings = self.make_settings(settings)
        self.convert_types()
            
    def mini_header_indicies(self, header_bytes):
        start = header_bytes.rfind('MHS')
        # +3 for MHE +2 for \x0d\x0a
        end = header_bytes.rfind('MHE') + 5
        return start, end


# TODO: parse host storage space
def get_settings(header_bytes):
    # Split on the \x0d\x0a byte
    settings = header_bytes.split('\x0d\x0a')[:-1]
    # Parse Host Storage here
    # ignore settings with no value
    dict(str(setting).split(' ', 1) for setting in settings if ' ' in setting)
    return s

def split_page_bytes(data_bytes):
    '''Split on MHE\x0d\x0a'''
    return data_bytes.split('\x4d\x48\x45\x0d\x0a', 1)

def get_miniheader(header_bytes):
    headers = header_bytes.split('\x0d\x0a')
    return dict(str(header).split(' ', 1) for header in headers if ' ' in header)


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
TMA = DEFAULT_HOST_STORAGE['TMA']
TMB = DEFAULT_HOST_STORAGE['TMB']
TMC = DEFAULT_HOST_STORAGE['TMC']
TMO = DEFAULT_HOST_STORAGE['TMO']
TMR = DEFAULT_HOST_STORAGE['TMR']
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
MAX_UNSIGNED_SHORT = 65535


def accel(v, m, b):
    '''Calculate an acceleration
    
    Arguments:
    v -- Measured value
    m -- Device constant (AXS, AYS, AYZ)
    b -- Device constant (AXA, AYA, AZA)
    '''
    return (1.0/m * v) + b
vaccel = np.vectorize(accel)

def magne(v, m, b):
    return m * v + b
vmagne = np.vectorize(magne, otypes='f')

def k_to_c(kelvin):
    '''kelvin to celcius'''
    return kelvin - 273.15
vk_to_c = np.vectorize(k_to_c)

def temp(num):
    return s(t_measure_to_resistance(num))

def t_measure_to_resistance(t):
    r_adj = t + TMO
    return TMR * r_adj / (MAX_UNSIGNED_SHORT - r_adj)
vresistance = np.vectorize(t_measure_to_resistance)

def steinhart(r):
    l = np.log(r)
    inv_temp = TMA + TMB * l + TMC * np.power(l, 3)
    return vk_to_c(np.power(inv_temp, -1))
vsteinhart = np.vectorize(steinhart)
def s(r):
    l = np.log(r)
    i = TMA + TMB * l + TMC * np.power(l, 3)
    return k_to_c(np.power(i, -1))

MIN_SIGNED_SHORT = -32768
ACCELS = [accel(x, AXB, AXA) for x in range(-32768, 32768)]
MAGNES = [magne(x, MXS, MXA) for x in range(-32768, 32768)]
TEMPS = [temp(x) for x in range(0, 65535)]
def lookup_acl(v):
    return ACCELS[v + MIN_SIGNED_SHORT]
vla = np.vectorize(lookup_acl)
def lookup_mag(v):
    return MAGNES[v + MIN_SIGNED_SHORT]
vlm = np.vectorize(lookup_mag)
def lookup_tmp(t):
    return TEMPS[t]
vlt = np.vectorize(lookup_tmp)

def measurements_to_data(data_tuple):
    '''((t, [a, a, a, m, m, m]), (t, [...]), ... ,)'''
    temp = vlt(data_tuple[:]['t'])
    #res = vresistance(data_tuple[:]['t'])
    #temp = vsteinhart(res)
    accelx = vla(data_tuple[:]['o'][:,0::6].flatten())
    accely = vla(data_tuple[:]['o'][:,1::6].flatten())
    accelz = vla(data_tuple[:]['o'][:,2::6].flatten())
    magnex = vlm(data_tuple[:]['o'][:,3::6].flatten())
    magney = vlm(data_tuple[:]['o'][:,4::6].flatten())
    magnez = vlm(data_tuple[:]['o'][:,5::6].flatten())
    '''
    accelx = vaccel(data_tuple[:]['o'][:,0::6].flatten(), AXB, AXA).round(decimals=5)
    accely = vaccel(data_tuple[:]['o'][:,1::6].flatten(), AYB, AYA).round(decimals=5)
    accelz = vaccel(data_tuple[:]['o'][:,2::6].flatten(), AZB, AZA).round(decimals=5)
    magnex = vmagne(data_tuple[:]['o'][:,3::6].flatten(), MXS, MXA)
    magney = vmagne(data_tuple[:]['o'][:,4::6].flatten(), MYS, MYA)
    magnez = vmagne(data_tuple[:]['o'][:,5::6].flatten(), MZS, MZA)
    '''
    return temp, accelx, accely, accelz, magnex, magney, magnez

#vdata = np.vectorize(measurements_to_data)

def build_t(t, clk, rate):
    start = np.datetime64(clk)
    delta = np.timedelta64(rate, 's')
    end = start + delta * t.shape[0]
    clock = np.arange(start, end, delta)

    s = pd.Series(t, index=clock)
    return s

def build_o(ax, ay, az, mx, my, mz, clk, rate):
    start = np.datetime64(clk)
    # get a good python timedelta
    delta = datetime.timedelta(seconds=1.0/rate)
    # convert to numpy timedelta
    d = np.timedelta64(delta)
    end = start + d * ax.shape[0]
    clock = np.arange(start, end, d)
    # make the measurements one dimensional
    d = np.core.records.fromarrays([ax, ay, az, mx, my, mz], dtype=('float,float,float,float,float,float'))
    # get it to a dataframe with a clock
    s = pd.DataFrame(d, index=clock)
    return s

def print_temps(t, clk, rate, f):
    '''Print an array of temperature measurements to a file
    
    Arguments:
    t -- numpy aray of temperatures
    clk -- clock when the temperature measurements started
    rate -- rate at which measurements were taken (in seconds)
    f -- filehandle to write to
    '''
    start = np.datetime64(clk)
    delta = np.timedelta64(rate, 's')
    end = start + delta * t.shape[0]
    clock = np.arange(start, end, delta)

    s = pd.Series(t, index=clock)
    s.to_csv(f)
    #    rng = pd.date_range(clk, periods=t.shape[0], 
  
  
    #d = np.core.records.fromarrays([clock, t], dtype=('datetime64[ms],float'))
    #np.savetxt(f, d, fmt='%s %f')


def print_orientation(ax, ay, az, mx, my, mz, clk, rate, f):
    '''Print orientation measurements

    Arguments:
    ax - mz -- Device measurements
    clk -- current clock reading
    rate -- rate at which measurements were taken (in decimal seconds?)
    f -- filehandle to write to
    '''

    start = np.datetime64(clk)
    # get a good python timedelta
    delta = datetime.timedelta(seconds=1.0/rate)
    # convert to numpy timedelta
    d = np.timedelta64(delta)
    end = start + d * ax.shape[0]
    clock = np.arange(start, end, d)
    # make the measurements one dimensional
    d = np.core.records.fromarrays([ax, ay, az, mx, my, mz], dtype=('float,float,float,float,float,float'))
    # get it to a dataframe with a clock
    s = pd.DataFrame(d, index=clock)
    s.to_csv(f)

class RequiredKeyException(Exception):
    pass

def build_dtype(TRI=None, ORI=None, BMN=None, TMP=None, ACL=None, MGN=None, **kwargs):
    '''Incoming are all ints
    return dtype and bytesize
    '''
    required_keys = [TRI, ORI, BMN, TMP, ACL, MGN]
    if not all(required_keys):
        raise RequiredKeyException('Missing key(s): {}'.format(
            [x for x in required_keys if not x]))
    
    # TRI is a multiple of ORI
    if TRI >= ORI:
        tmp = ('t', '<H', 1)
        o = ('o', '<h', 6 * BMN * TRI/ORI)
    
    # 1 unsigned short, 6 * bmn * tri/ori signed shorts. short == 2 bytes
    return np.dtype([tmp, o]), ((1 + (6 * BMN * TRI/ORI)) * 2)
    

if __name__ == '__main__':
    print(TEMPS);exit()
    K = 1024 # 1 kb in bytes
    HEADER_PAGE_SIZE = 32 * K # 32 kb in bytes
    DATA_PAGE_SIZE = 1024 * K # 1024 kb in bytes
    # FILE = 'simple.ld' # 104
    FILE = 'big/Big_File.lid' # 109
    TMP_OUT = 'tmp_out.txt'
    ORI_OUT = 'ori_out.txt'
    SIZE = os.path.getsize(FILE)
#    TRUE_SIZE = SIZE - 109
    with open(FILE, 'rb') as f, open(TMP_OUT, 'w') as tmp_out, open(ORI_OUT, 'w') as ori_out:
        header_bytes = bytearray(f.read(HEADER_PAGE_SIZE))
        s = Settings(header_bytes)
        dtype, pattern_size = build_dtype(**s.mini_header.settings)
        print dtype, pattern_size

        patterns_per_page = DATA_PAGE_SIZE/pattern_size
        # we fit this many iterations into one page
        print("there are this may data patterns in a page: {}".format(DATA_PAGE_SIZE/pattern_size))
        # we know there are this many pages:
        num_data_pages = (SIZE - HEADER_PAGE_SIZE)/DATA_PAGE_SIZE
        print("there are this many data pages: {}".format(num_data_pages))
        x = 0
        append = False
        for i in range(num_data_pages):
            print("{}".format(i))
            mh_bytes = np.fromfile(f, dtype=s.mini_header.dtype, count=1)
            mh = MiniHeader(bytearray(mh_bytes))
            clk = mh.settings['CLK']
            data = np.fromfile(f, dtype=dtype, count=patterns_per_page-1)
            f.seek(HEADER_PAGE_SIZE + DATA_PAGE_SIZE * i)
            
            t, ax, ay, az, mx, my, mz = measurements_to_data(data)
            if append:
                holder_t = holder_t.append(build_t(t, clk, mh.settings['TRI']))
                holder_o = holder_o.append(build_o(ax, ay, az, mx, my, mz,
                                                   clk, mh.settings['BMR']))
            else:
                holder_t = build_t(t, clk, mh.settings['TRI'])
                holder_o = build_o(ax, ay, az, mx, my, mz, clk, mh.settings['BMR'])
            if x % 10 == 0:
#                holder_t.to_csv(tmp_out)
#                holder_o.to_csv(ori_out)
                append = False
                holder_t = None
                holder_o = None
                #print_tempst, clk, mh.settings['TRI'], tmp_out)
                #print_orientation(ax, ay, az, mx, my, mz, clk, mh.settings['BMR'], ori_out)

            x += 1
