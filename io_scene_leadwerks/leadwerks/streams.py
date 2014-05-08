# -*- coding: utf-8 -*-
from struct import pack
from array import array

class BinaryStream(object):
    mode = 'rb'

    def __init__(self, file_name):
        self.file_name = file_name

    def open(self):
        self.stream = open(self.file_name, self.mode, buffering=0)

    def close(self):
        self.stream.close()

    def cur_pos(self):
        return self.stream.tell()


class BinaryStreamReader(BinaryStream):
    mode = 'rb'

    def read_byte(self, ct=1):
        return self.__reader('B', ct)

    def seek(self, ct=1):
        self.stream.seek(ct, 1)

    def read_int(self, ct=1):
        return self.__reader('I', ct)

    def read_sint(self, ct=1):
        # Signed int
        return self.__reader('i', ct)

    def read_long(self, ct=1):
        return self.__reader('L', ct)

    def read_slong(self, ct=1):
        return self.__reader('l', ct)

    def read_float(self, ct=1):
        return self.__reader('f', ct)

    def read_short(self, ct=1):
        return self.__reader('h', ct)

    def read_str(self, ct=None):
        res = ''
        i = 0
        while True:
            c = self.stream.read(1)
            s = c.decode('ascii')
            res = '%s%s' % (res, s)
            i += 1

            if ct:
                if i == ct:
                    return str(res)
            elif not ord(s):
                return res[0:-1]
        return res

    def read_nt_str(self):
        '''
        Null terminated string
        '''
        ret = self.read_str()
        return ret

    def read_batch(self, *args, **kwargs):
        return self.__reader(*args, **kwargs)

    def __reader(self, mod='B', ct=1):
        f = array(mod)
        f.fromfile(self.stream, ct)
        if ct == 1:
            return f[0]
        return list(f)


class BinaryStreamWriter(BinaryStream):
    mode = 'wb'

    def write_int(self, val):
        assert(isinstance(val, int))
        self.stream.write(pack('<i', val))

    def write_nt_str(self, val):
        '''
        Writes Null-terminated string
        '''
        assert(isinstance(val, str))
        self.stream.write(bytes(val, encoding='ascii'))
        self.stream.write(pack('1B', 0))

    def write_batch(self, modifier, elements_list):
        mod = '%s%s' % (len(elements_list), modifier)
        self.stream.write(pack(mod, *elements_list))
