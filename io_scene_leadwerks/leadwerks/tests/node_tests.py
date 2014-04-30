# -*- coding: utf-8 -*-
import unittest
import os

from mdl import node
from streams import BinaryStreamWriter

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

class NodeTests(unittest.TestCase):

    def setUp(self):
        self.tempfile = '/tmp/props.bin'
        self.stream = BinaryStreamWriter(self.tempfile)
        self.stream.open()

        n = node.Node()
        n.set_property('one', 'two')
        n.set_property('three', 'Four')
        self.node = n

    def tearDown(self):
        self.stream.close()
        self.rm_file(self.tempfile)

    def test_save_properties(self):
        self.node.save_properties(self.stream)
        self.assertEqual(
            self.read_file(self.tempfile),
            self.read_file(os.path.join(DATA_DIR, 'props.bin'))
        )

    def rm_file(self, path):
        try:
            os.remove(path)
        except:
            pass

    def read_file(self, path):
        f = open(path, 'rb')
        res = f.read()
        f.close()
        return res


def main():
    unittest.main()

if __name__ == '__main__':
    unittest.main()