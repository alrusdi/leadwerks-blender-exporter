# -*- coding: utf-8 -*-
from collections import OrderedDict
import json
import sys
import os
from leadwerks import streams
from leadwerks.mdl import constants
from lxml import etree


class MdlCompiller(object):
    def __init__(self, path):
        with open(path, 'r') as f:
            self.source = etree.fromstring(f.read())
        path = '.'.join(path.split('.')[0:-1])
        if not path.endswith('.mdl'):
            path = '%s.mdl' % path
        self.writer = streams.BinaryStreamWriter(path)
        self.writer.open()

    def compile(self):
        self.compile_node(self.source)

    def compile_node(self, node):
        code = node.attrib.get('code')
        compile = self.get_node_compiller(code)

        if not compile:
            raise NotImplementedError('Compiller not found for code %s' % code)

        compile(node)

        sub = self.get_subnode_by_name(node, 'subnodes')
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
        subs = self.get_subnode_by_name(node, 'subnodes')
        return 0 if subs is None else len(subs)

    def get_node_compiller(self, code):
        amap = {
            str(constants.MDL_FILE): self.header_compiller,
            str(constants.MDL_MESH): self.mesh_compiller,
            str(constants.MDL_PROPERTIES): self.props_compiller,
            str(constants.MDL_SURFACE): self.surface_compiller,
            str(constants.MDL_VERTEXARRAY): self.vertex_compiller,
            str(constants.MDL_INDICEARRAY): self.indices_compiller,
            str(constants.MDL_BONE): self.bone_compiller,
            str(constants.MDL_ANIMATIONKEYS): self.anim_compiller,
            str(constants.MDL_NODE): self.node_compiller,
        }
        return amap.get(code)

    def get_value(self, node, name):
        node = self.get_subnode_by_name(node, name)
        return self.get_subnode_by_name(node, 'value').text


    def header_compiller(self, node):
        self.writer.write_batch(
            'I',
            [
                constants.MDL_FILE,
                1,  # kids count
                4,  # block size
                constants.MDL_VERSION
            ]
        )

    def _parse_list(self, items_list, convert_fn):
        ret = []
        for mv in items_list.split(','):
            ret.append(convert_fn(mv.strip()))
        return ret

    def _matrix_compiller(self, node, node_code):
        matrix = self.get_subnode_by_name(node, 'matrix').text
        matrix = self._parse_list(matrix, float)

        self.writer.write_batch(
            'I',
            [
                node_code,
                self.count_subnodes(node),  # kids count
                64,  # block size
            ]
        )

        self.writer.write_batch('f', matrix)


    def mesh_compiller(self, node):
        self._matrix_compiller(node, constants.MDL_MESH)

    def node_compiller(self, node):
        self._matrix_compiller(node, constants.MDL_NODE)

    def props_compiller(self, node):
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
            v = p.text
            props.extend([k,v])
            size = size + len(k) + len(v) + 2
        return size, props

    def surface_compiller(self, node):
        self.writer.write_batch(
            'I',
            [
                constants.MDL_SURFACE,
                self.count_subnodes(node),  # kids count
                0
            ]
        )

    def vertex_compiller(self, node):
        data = self._parse_vertex_data(node)
        self.writer.write_batch(
            'I',
            [
                constants.MDL_VERTEXARRAY,
                self.count_subnodes(node),  # kids count
                data['count'] * 3 * 4 + 4 * 4,  # block size
                data['type'],  # type of data
                int(self.get_value(node, 'variable_type')),
                int(self.get_subnode_by_name(node, 'number_of_vertices').text),
                data['count'],  # elements
            ]
        )

        self.writer.write_batch('f', data['items'])

    def indices_compiller(self, node):
        data = self.get_subnode_by_name(node, 'data').text
        data = self._parse_list(data, int)
        ct = len(data)
        self.writer.write_batch(
            'I',
            [
                constants.MDL_INDICEARRAY,
                self.count_subnodes(node),  # kids count
                ct * 2 + 3 * 4,  # block size
                ct, # indexes count
                int(self.get_subnode_by_name(node, 'primitive_type').text),
                int(self.get_value(node, 'variable_type'))
            ]
        )

        self.writer.write_batch('H', data)

    def bone_compiller(self, node):
        self._matrix_compiller(node, constants.MDL_BONE)
        self.writer.write_int(int(self.get_value(node, 'bone_id')))

    def anim_compiller(self, node):
        frames_list = self.get_subnode_by_name(node, 'frames')
        ct = len(frames_list)
        self.writer.write_batch(
            'I',
            [
                constants.MDL_ANIMATIONKEYS,
                self.count_subnodes(node),  # kids count
                ct*64 + 4,  # block size
                ct,
                int(self.get_value(node, 'variable_type'))
            ]
        )
        for f in frames_list:
            data = f.text
            data = self._parse_list(data, float)
            self.writer.write_batch('f', data)

    def _parse_vertex_data(self, node):
        data_type = int(self.get_value(node, 'data_type'))
        elements_count = 2 if data_type == constants.MDL_TEXTURE_COORD else 3
        data = self.get_subnode_by_name(node, 'data').text
        data = self._parse_list(data, float)
        return {
            'count': elements_count,
            'type': data_type,
            'items': data
        }


class MdlDumper(object):
    def __init__(self, path):
        self.reader = streams.BinaryStreamReader(path)
        self.reader.open()
        self.data = OrderedDict()

    def read(self):
        self.data = self.read_node()
        self.reader.close()

    def read_node(self):
        data, read_fn = self.read_header()
        data.update(read_fn())
        if data['num_kids']:
            data['nodes'] = []
        for i in range(0, data['num_kids']):
            data['nodes'].append(self.read_node())
        return data

    def read_header(self):
        node_code = self.reader.read_int()
        header = OrderedDict({
            'code': node_code,
            'num_kids': self.reader.read_int(),
            '_block_size': self.reader.read_int()
        })

        reader = self.get_node_reader(node_code)
        if not reader:
            print('ERROR! Node reader not found:', node_code)
            sys.exit(1)

        return header, reader

    def get_node_reader(self, node_code):
        amap = {
            str(constants.MDL_FILE): self.header_reader,
            str(constants.MDL_MESH): self.mesh_reader,
            str(constants.MDL_PROPERTIES): self.props_reader,
            str(constants.MDL_SURFACE): self.surface_reader,
            str(constants.MDL_VERTEXARRAY): self.vertex_array_reader,
            str(constants.MDL_INDICEARRAY): self.indices_reader,
            str(constants.MDL_BONE): self.bone_reader,
            str(constants.MDL_ANIMATIONKEYS): self.anim_reader,
            str(constants.MDL_NODE): self.node_reader,
        }
        return amap.get(str(node_code))

    def fmt_batch(self, data, modifier='s'):
        ret = []
        for d in data:
            ret.append(format(d, modifier))
        return ret

    def fmt_var_type(self, dt):
        var_type_map = {
            str(constants.MDL_FLOAT): 'FLOAT',
            str(constants.MDL_INT): 'INT',
            str(constants.MDL_UNSIGNED_BYTE): 'BYTE',
            str(constants.MDL_UNSIGNED_SHORT): 'SHORT',
        }
        return {'name': var_type_map.get(str(dt), 'UNKNOWN'), 'value': dt}

    def fmt_data_type(self, dt):
        data_type_map = {
            str(constants.MDL_POSITION): 'POSITION',
            str(constants.MDL_NORMAL): 'NORMAL',
            str(constants.MDL_TEXTURE_COORD): 'TEXTURE_COORD',
            str(constants.MDL_COLOR): 'COLOR',
            str(constants.MDL_TANGENT): 'TANGENT',
            str(constants.MDL_BINORMAL): 'BINORMAL',
            str(constants.MDL_BONEINDICE): 'BONEINDICE',
            str(constants.MDL_BONEWEIGHT): 'BONEWEIGHT',
        }

        return {'name': data_type_map.get(str(dt), 'UNKNOWN'), 'value': dt}



    def mesh_reader(self):
        ret = {
            'name': 'MESH',
            'matrix': self.fmt_batch(self.reader.read_batch('f', 16), 'f')
        }
        return ret

    def surface_reader(self):
        return {
            'name': 'SURFACE'
        }

    def header_reader(self):
        ret = {
            'name': 'FILE',
            'version': self.reader.read_int()
        }
        return ret

    def props_reader(self):
        count = self.reader.read_int()
        ret = {
            'name': 'PROPERTIES',
            'count': count,
            'properties': []
        }

        for i in range(0, count):
            ret['properties'].append({
                'name': self.reader.read_nt_str(),
                'value': self.reader.read_nt_str(),
            })
        return ret

    def vertex_array_reader(self):
        count = self.reader.read_int()
        ret = {
            'name': 'VERTEXARRAY',
            'number_of_vertices': count,
            'data_type': self.fmt_data_type(self.reader.read_int()),
            'variable_type': self.fmt_var_type(self.reader.read_int()),
            'elements_count': self.reader.read_int(),
        }
        vt = ret['variable_type']['value']
        mod = 'f' if vt == constants.MDL_FLOAT else 'H'

        if ret['data_type']['name'] in ['COLOR', 'BONEINDICE', 'BONEWEIGHT']:
            ret['elements_count'] = 4
            mod = 'B'

        ret['data'] = self.reader.read_batch(
            mod,
            ret['elements_count'] * ret['number_of_vertices']
        )

        return ret

    def indices_reader(self):
        count = self.reader.read_int()
        ret = {
            'name': 'INDICEARRAY',
            'number_of_indexes': count,
            'primitive_type': self.reader.read_int(),
            'variable_type': self.fmt_var_type(self.reader.read_int()),
            'data': self.reader.read_batch('H', count)
        }
        return ret

    def bone_reader(self):
        ret = {
            'name': 'BONE',
            'matrix': self.fmt_batch(self.reader.read_batch('f', 16), 'f'),
            'bone_id': self.reader.read_int()
        }
        return ret

    def node_reader(self):
        ret = {
            'name': 'NODE',
            'matrix': self.fmt_batch(self.reader.read_batch('f', 16), 'f'),
        }
        return ret

    def anim_reader(self):
        ret = OrderedDict({'name': 'ANIMATIONKEYS'})
        ret['number_of_frames'] = self.reader.read_int()
        ret['frames'] = []

        for i in range(0, ret['number_of_frames']):
            ret['frames'].append(
                self.reader.read_batch('f', 16)
            )

        return ret

    def as_xml(self):
        return self.__convert_node_to_xml(self.data)

    def __convert_node_to_xml(self, node):
        xml = '<node'
        for k in ['name', '_num_kids', '_block_size', 'code']:
            v = node.get(k)
            if v:
                xml = '%s %s="%s"' % (xml, k, v)
        xml = '%s>' % xml

        for k, v in node.items():
            if k in ['name', 'nodes', '_num_kids', '_block_size', 'code']:
                continue
            if type(v) is list:
                if not v:
                    continue

                res = ''
                if type(v[0]) is dict or type(v[0]) is OrderedDict:
                    for iv in v:
                        res = '%s%s' % (res, self.__fmt_kv(iv))

                if type(v[0]) is list:
                    for l in v:
                        res = '%s<frame>%s</frame>' % (res, ', '.join(map(str, l)))

                if not res:
                    res = ','.join(map(str, v))
                v = res
            elif type(v) is dict or type(v) is OrderedDict:
                v = self.__fmt_kv(v)
            xml = '%s<%s>%s</%s>' % (xml, k, v, k)

        if node.get('nodes'):
            xml = '%s<subnodes>' % xml
            for n in node['nodes']:
                xml = '%s%s' % (xml, self.__convert_node_to_xml(n))
            xml = '%s</subnodes>' % xml

        xml = '%s</node>' % xml
        return xml

    def __fmt_kv(self, v):
        if v.get('value'):
            v = '<value means="%s">%s</value>' % (v.get('name'), v.get('value'))
        return v

if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        print('Pass a .mdl file as parameter please')
        sys.exit(1)
    path = args[1]

    if not path.startswith('/'):
        cur_dir = os.path.dirname(__file__)
        path = os.path.join(cur_dir, path)

    if not os.access(path, os.R_OK):
        print('Cannot access file %s' % path)
        sys.exit(1)

    if path.endswith('.xml'):
        compiller = MdlCompiller(path)
        compiller.compile()
    else:
        dumper = MdlDumper(path)
        dumper.read()

        print(dumper.as_xml())