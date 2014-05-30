# -*- coding: utf-8 -*-

from . import streams
try:
    import bpy
    from io_scene_leadwerks.leadwerks.mdl import constants
except ImportError:
    from leadwerks.mdl import constants
import xml.etree.ElementTree as ET


class MdlCompiler(object):
    def __init__(self, path_or_xml, output_path):
        if path_or_xml.startswith('<'):
            _xml = path_or_xml
        else:
            with open(path_or_xml, 'r') as f:
                _xml = f.read()

        self.source = ET.fromstring(_xml)

        self.writer = streams.BinaryStreamWriter(output_path)
        self.writer.open()
        self.FILE_FORMAT_VERSION = constants.MDL_VERSION

    def compile(self):
        self.compile_node(self.source)

    def compile_node(self, node):
        code = node.attrib.get('code')
        compile = self.get_node_compiler(code)
        if not compile:
            raise NotImplementedError('compiler not found for code %s' % code)

        compile(node)

        sub = self.get_subnode_by_name(node, 'subblocks')
        if sub is None:
            return True

        for s in sub:
            self.compile_node(s)

        return True

    def get_subnode_by_name(self, node, name):
        for i in node:
            if i.tag == name:
                return i

    def count_subnodes(self, node, name='subnodes'):
        subs = self.get_subnode_by_name(node, 'subblocks')
        return 0 if subs is None else len(subs)

    def get_node_compiler(self, code):
        amap = {
            str(constants.MDL_FILE): self.header_compiler,
            str(constants.MDL_MESH): self.mesh_compiler,
            str(constants.MDL_PROPERTIES): self.props_compiler,
            str(constants.MDL_SURFACE): self.surface_compiler,
            str(constants.MDL_VERTEXARRAY): self.vertex_compiler,
            str(constants.MDL_INDICEARRAY): self.indices_compiler,
            str(constants.MDL_BONE): self.bone_compiler,
            str(constants.MDL_ANIMATIONKEYS): self.anim_compiler,
            str(constants.MDL_NODE): self.node_compiler,
        }
        return amap.get(code)

    def get_value(self, node, name):
        node = self.get_subnode_by_name(node, name)
        return self.get_subnode_by_name(node, 'value').text

    def header_compiler(self, node):
        v = int(self.get_subnode_by_name(node, 'version').text)
        self.FILE_FORMAT_VERSION = v
        self.writer.write_batch(
            'I',
            [
                constants.MDL_FILE,
                1,  # kids count
                4,  # block size
                v   # version
            ]
        )

    def _parse_list(self, items_list, convert_fn):
        ret = []
        for mv in items_list.split(','):
            ret.append(convert_fn(mv.strip()))
        return ret

    def _matrix_compiler(self, node, node_code, block_size=64):
        matrix = self.get_subnode_by_name(node, 'matrix').text
        matrix = self._parse_list(matrix, float)

        self.writer.write_batch(
            'I',
            [
                node_code,
                self.count_subnodes(node),  # kids count
                block_size,  # block size
            ]
        )

        self.writer.write_batch('f', matrix)

    def mesh_compiler(self, node):
        self._matrix_compiler(node, constants.MDL_MESH)

    def node_compiler(self, node):
        self._matrix_compiler(node, constants.MDL_NODE)

    def props_compiler(self, node):
        size, props = self._parse_props(node)
        self.writer.write_batch(
            'I',
            [
                constants.MDL_PROPERTIES,
                self.count_subnodes(node),  # kids count
                size + 4,  # block size
                int(len(props)/2)  # count of properties (key/value pairs)
            ]
        )

        for p in props:
            self.writer.write_nt_str(p)

    def _parse_props(self, node):
        props = []
        size = 0
        for p in self.get_subnode_by_name(node, 'properties'):
            k = p.attrib.get('means')
            v = p.text or ''
            props.extend([k,v])
            size = size + len(k) + len(v) + 2
        return size, props

    def surface_compiler(self, node):
        self.writer.write_batch(
            'I',
            [
                constants.MDL_SURFACE,
                self.count_subnodes(node),  # kids count
                0
            ]
        )

    def vertex_compiler(self, node):
        data = self._parse_vertex_data(node)

        self.writer.write_batch(
            'I',
            [
                constants.MDL_VERTEXARRAY,
                self.count_subnodes(node),  # kids count
                data['block_size'],  # block size
                data['verts_count'],  # number_of_vertices
                data['type'],  # type of data
                int(self.get_value(node, 'variable_type')),
                data['count'],  # elements
            ]
        )

        self.writer.write_batch(data['mod'], data['items'])

    def _parse_vertex_data(self, node):
        data_type = int(self.get_value(node, 'data_type'))
        verts_count = int(self.get_subnode_by_name(node, 'number_of_vertices').text)
        elements_count = 3
        el_sz = 4
        cvt_fn = float
        mod = 'f'
        if data_type == constants.MDL_TEXTURE_COORD:
            elements_count = 2
        elif data_type in [constants.MDL_BONEINDICE, constants.MDL_BONEWEIGHT, constants.MDL_COLOR]:
            elements_count = 4
            el_sz = 1
            cvt_fn = int
            mod = 'B'

        data = self.get_subnode_by_name(node, 'data').text
        data = self._parse_list(data, cvt_fn)
        ret = {
            'count': elements_count,
            'type': data_type,
            'items': data,
            'block_size': verts_count * elements_count * el_sz + 4 * 4,
            'verts_count': verts_count,
            'mod': mod
        }
        return ret

    def indices_compiler(self, node):
        data = self.get_subnode_by_name(node, 'data').text
        data = self._parse_list(data, int)
        ct = len(data)
        self.writer.write_batch(
            'I',
            [
                constants.MDL_INDICEARRAY,
                self.count_subnodes(node),  # kids count
                ct * 2 + 3 * 4,  # block size
                ct,  # indexes count
                int(self.get_subnode_by_name(node, 'primitive_type').text),
                int(self.get_value(node, 'variable_type'))
            ]
        )

        self.writer.write_batch('H', data)

    def bone_compiler(self, node):
        self._matrix_compiler(node, constants.MDL_BONE, block_size=68)
        self.writer.write_int(int(self.get_subnode_by_name(node, 'bone_id').text))

    def anim_compiler(self, node):
        frames_subnode = self.get_subnode_by_name(node, 'frames')
        frames_list = frames_subnode if not frames_subnode is None else []
        ct = len(frames_list)

        sz = ct*64 + 4
        if self.FILE_FORMAT_VERSION == 2:
            anim_name = self.get_subnode_by_name(node, 'animation_name').text
            if anim_name:
                sz += len(anim_name) + 1
            else:
                anim_name = ''
                sz += 2

        self.writer.write_batch(
            'I',
            [
                constants.MDL_ANIMATIONKEYS,
                self.count_subnodes(node),  # kids count
                sz,  # block size
                ct
            ]
        )
        for f in frames_list:
            data = f.text
            data = self._parse_list(data, float)
            self.writer.write_batch('f', data)

        if self.FILE_FORMAT_VERSION == 2:
            self.writer.write_nt_str(anim_name)
