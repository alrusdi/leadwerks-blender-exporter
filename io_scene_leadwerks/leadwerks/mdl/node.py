# -*- coding: utf-8 -*-
from . import constants
from collections import OrderedDict


class Node(object):
    """
	Node is container for other elements (including other nodes)
    """
    def __init__(self):
        self.properties = OrderedDict()

    def get_property(self, key):
        return self.properties.get(key.lower())

    def set_property(self, key, value):
        self.properties[key.lower()] = str(value)
    
    def has_properties(self):
        return bool(self.properties)

    def save_properties(self, stream):
        size = 4
        count = len(self.properties.values())

        stream.write_int(constants.MDL_PROPERTIES)
        stream.write_int(0)  # Number of kids

        for key, value in self.properties.items():
            size += len(key)+1
            size += len(value) + 1

        stream.write_int(size)
        stream.write_int(count)

        for key, value in self.properties.items():
            stream.write_nt_string(key)
            stream.write_nt_string(value)
