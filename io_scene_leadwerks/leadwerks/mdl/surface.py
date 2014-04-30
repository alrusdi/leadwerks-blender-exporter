# -*- coding: utf-8 -*-
from . import constants
from .node import Node
from array import array


class Surface(Node):

    def __init__(self):
        super().__init__()
        self.vertices = array('f')  # x, y, z
        self.normals = array('f')  # nx, ny, nz
        self.colors = array('B')  # r, g, b, a
        self.tex_coords1 = array('f')  # u, v
        self.tex_coords2 = array('f')  # u, v
        self.binormals = []  # not used
        self.tangents = []  # not used

        self.bone_indexes = array('B')  # 4 values
        self.bone_weights = array('B')  # 4 values

        self.indexes = []
        self.collision = None

    def count_vertices(self):
        return len(self.vertices)

    def count_triangles(self):
        if self.indexes:
            return self.indexes / 3
        else:
            return 0

    def save(self, stream):
        kids = 1 + self.has_properties()

        pnames = [
            'normals', 'colors', 'tex_coords1', 'tex_coords2', 'binormals',
            'tangents', 'bone_indexes', 'bone_weights',
            'indexes', 'collision'
        ]

        for pname in pnames:
            if len(getattr(self, pname)):
                kids += 1

        stream.write_int(constants.MDL_SURFACE)
        stream.write_int(kids)
        stream.write_int(0)

        if self.has_properties():
            self.save_properties(stream)


        stream.write_int(constants.MDL_VERTEXARRAY)
        stream.write_int(0)  # kids
        stream.write_int(self.count_vertices()*12 + 16)  # size
        stream.write_int(self.count_vertices())
        stream.write_int(constants.MDL_POSITION)
        stream.write_int(constants.MDL_FLOAT)
        stream.write_int(3)  # num elements
        stream.write_batch('f', self.vertices)

        if len(self.normals):
            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_vertices()*12 + 16)  # size
            stream.write_int(self.count_vertices())
            stream.write_int(constants.MDL_NORMAL)
            stream.write_int(constants.MDL_FLOAT)
            stream.write_int(3)  # num elements
            stream.write_batch('f', self.normals)

        if len(self.colors):
            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_vertices()*4 + 16)  # size
            stream.write_int(self.count_vertices())
            stream.write_int(constants.MDL_COLOR)
            stream.write_int(constants.MDL_UNSIGNED_BYTE)
            stream.write_int(4)  # num elements
            stream.write_batch('B', self.colors)

        for tex in [self.tex_coords1, self.tex_coords2]:
            if not len(tex):
                continue

            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_vertices()*8 + 16)  # size
            stream.write_int(self.count_vertices())
            stream.write_int(constants.MDL_TEXTURE_COORD)
            stream.write_int(constants.MDL_FLOAT)
            stream.write_int(2)  # num elements
            stream.write_batch('f', tex)

        if len(self.bone_indexes):
            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_vertices()*4 + 16)  # size
            stream.write_int(self.count_vertices())
            stream.write_int(constants.MDL_BONEINDICE)
            stream.write_int(constants.MDL_UNSIGNED_BYTE)
            stream.write_int(4)  # num elements
            stream.write_batch('B', self.bone_indexes)

        if len(self.bone_weights):
            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_vertices()*4 + 16)  # size
            stream.write_int(self.count_vertices())
            stream.write_int(constants.MDL_BONEWEIGHT)
            stream.write_int(constants.MDL_UNSIGNED_BYTE)
            stream.write_int(4)  # num elements
            stream.write_batch('B', self.bone_weights)

        if len(self.indexes):
            stream.write_int(constants.MDL_VERTEXARRAY)
            stream.write_int(0)  # kids
            stream.write_int(self.count_triangles()*6 + 12)  # size
            stream.write_int(self.count_triangles()*3)
            stream.write_int(constants.MDL_TRIANGLES)
            stream.write_int(constants.MDL_UNSIGNED_SHORT)
            stream.write_batch('H', self.indexes)
