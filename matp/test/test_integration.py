import os
import datetime
import StringIO

from matp import mat

def find_sample_dirs(dirname):
    '''returns a list of directories which contain each test case

    >>> dirs = find_sample_dirs('samples')
    >>> 'samples/sample1' in dirs
    True
    >>> 'samples/sample2' in dirs
    True
    >>> 'samples/__init__.py' in dirs
    False
    '''
    return [os.path.join(dirname, name) for name in os.listdir(dirname)]

def get_file_with_ending(directory, ending):
    '''returns the first file in the directory with the given ending

    >>> get_file_with_ending('samples/sample1', '.lid')
    'samples/sample1/s1_1-60-2-2.lid'
    >>> get_file_with_ending('samples/sample2', '.lid')
    'samples/sample2/s2_1-60-2-2.lid'
    '''
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(ending)][0]

def get_expected_files(directory):
    '''return the temperature and orientation output files

    >>> get_expected_files('samples/sample1')
    ('samples/sample1/s1_1-60-2-2_temperature.txt', 'samples/sample1/s1_1-60-2-2_orientation.txt')
    '''
    return (get_file_with_ending(directory, '_temperature.txt'), get_file_with_ending(directory, '_orientation.txt'))

def parse_file(lidfile):
    '''returns the output of matp

    >>> t = StringIO.StringIO()
    >>> o = StringIO.StringIO()
    >>> mat.parse_file('samples/sample1/s1_1-60-2-2.lid', t, o, default_host_storage=False)
    '''
    t = StringIO.StringIO()
    o = StringIO.StringIO()
    mat.parse_file(lidfile, o, t, default_host_storage=False)
    return (t.getvalue().strip().split(os.linesep), o.getvalue().strip().split(os.linesep))

def compare_data_lines(actual_line, expected_line):
    '''return the equality of two lines
    
    >>> a = '2013-11-15,09:05:40.5000,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00'
    >>> b = '2013-11-15,09:05:41.500,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00'
    >>> compare_data_lines(a, b)
    True
    >>> a = '2013-11-15,'
    >>> b = '2013-11-15,09:05:41.500,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00'
    >>> compare_data_lines(a, b)
    False
    '''
    actual = actual_line.strip().split(',')
    expected = expected_line.strip().split(',')
    if len(actual) != len(expected):
        return False
    actual_time = datetime.datetime.strptime(actual[0] + 'T' + actual[1], "%Y-%m-%dT%H:%M:%S.%f")
    # Todo: probably get rid of the seconds off by one when the firmware gets fixed
    expected_time = datetime.datetime.strptime(expected[0] + 'T' + expected[1], "%Y-%m-%dT%H:%M:%S.%f") - datetime.timedelta(seconds=1)
    actual = actual[2:]
    expected = expected[2:]
    same = True
    if actual_time != expected_time:
        print("Times are different")
        print("Expected: {}{}Got:       {}".format(expected_time, os.linesep, actual_time))
        same = False
    for i in range(len(actual)):
        if actual[i] != expected[i]:
            same = False
            print("Values are different")
            print("Expected: {}{}Got:      {}".format(expected[i], os.linesep, actual[i]))
    return same

def compare_simple_lines(actual_line, expected_line):
    '''return true if lines are equal

    >>> compare_simple_lines("hello\\r\\n", "hello\\r")
    True
    '''
    return actual_line.rstrip() == expected_line.rstrip()

def compare_lines(actual_lines, expected_lines):
    '''Return true if actual lines is the same as expected lines
    
    >>> first_file = ['1','2013-11-15,09:05:41.5000,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00','2013-11-15,09:05:42.5000,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00']
    >>> second_file = ['1','2013-11-15,09:05:42.500,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00','2013-11-15,09:05:43.500,-0.88086,0.45020,0.00879,414.00,-96.00,-48.00']
    >>> compare_lines(first_file, second_file)
    True
    '''
    if not compare_simple_lines(actual_lines[0], expected_lines[0]):
        return False
    if len(actual_lines) != len(expected_lines):
        return False
    linenos = 1, len(actual_lines)/2, -1
    same = True
    for i in linenos:
        if not compare_data_lines(actual_lines[i], expected_lines[i]):
            same = False
            print("These lines are different:{}Expected: {}{}Got:      {}".format(os.linesep, expected_lines[i], os.linesep, actual_lines[i]))
    return same

def get_lines(fh):
    return [line.strip() for line in fh]

def main():
    for directory in find_sample_dirs('samples'):
        if "sample4" in directory:
            continue
        lidfile = get_file_with_ending(directory, '.lid')
        print("=== {} ===".format(lidfile))
        t, o = parse_file(lidfile)
        t_file, o_file = get_expected_files(directory)
        t_e = get_lines(open(t_file, 'r'))
        if len(t) != len(t_e):
            print("Line lengths are different in temperature file.")
            print("Expected: {}, Got: {}".format(len(t_e), len(t)))
            exit(1)
        o_e = get_lines(open(o_file, 'r'))
        if len(o) != len(o_e):
            print("Line lengths are different in orientation file.")
            print("Expected: {}, Got: {}".format(len(o_e), len(o)))
            exit(1)
        if compare_lines(t, t_e):
            print("pass")
            continue
    
# for each sample directory
#   get the lid file
#   run the lid file through matp

# Walk through all samples
# for each lid file
#   Run that lid file against mat
#   Get an output and input
#   Compare against each expected file


if __name__ == "__main__":
    #import doctest
    #doctest.testmod()
    main()
