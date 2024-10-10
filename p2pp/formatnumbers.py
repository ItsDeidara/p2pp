__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import struct


def hexify_byte(num):
    # hexify_short: Converts a short integer into the specific notation used by Mosaic
    if num < 0:
        num += 256
    return "D" + '{0:02x}'.format(num)


def hexify_short(num):
    # hexify_short: Converts a short integer into the specific notation used by Mosaic
    if num < 0:
        num += 65536
    return "D" + '{0:04x}'.format(num)


def hexify_long(num):
    # hexify_long: Converts a 32-bit integer into the specific notation used by Mosaic
    return "D" + '{0:08x}'.format(num)


def hexify_float(f):
    # hexify_float: Converts a 32-bit floating point number into the specific notation used by Mosaic
    _number = (hex(struct.unpack('<I', struct.pack('<f', f))[0]))[2:]

    return "D{:0>8}".format(_number)


def hours(sec):
    return int(sec / 3600)


def minutes(sec):
    return int((sec % 3600) / 60)


def seconds(sec):
    return int(sec % 60)


def comment_out(line):
    return "; -- P2PP removed" + line
