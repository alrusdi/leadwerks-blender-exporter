# -*- coding: utf-8 -*-
from struct import pack


class BinaryStream(object):
    mode = 'rb'

    def __init__(self, file_name):
        self.file_name = file_name

    def open(self):
        self.stream = open(self.file_name, self.mode, buffering=0)

    def close(self):
        self.stream.close()


class BinaryStreamWriter(BinaryStream):
    mode = 'wb'

    def write_int(self, val):
        assert(isinstance(val, int))
        self.stream.write(pack('<i', val))

    def write_nt_string(self, val):
        '''
        Writes Null-terminated string
        '''
        assert(isinstance(val, str))
        self.stream.write(bytes(val, 'ascii'))
        self.stream.write(pack('1B', 0))

    def write_batch(self, modifier, elements_list):
        mod = '%s%s' % (len(elements_list), modifier)
        self.stream.write(pack(mod, *elements_list))
