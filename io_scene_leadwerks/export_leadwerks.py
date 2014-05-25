# <pep8 compliant>
from copy import copy
import os

from xml.dom import minidom
import bpy
import bmesh
from bpy_extras.io_utils import axis_conversion
import subprocess
import mathutils
from leadwerks.mdl import constants
from material import Material
from xml_tool import compiler
from mathutils import Vector, Matrix


class LeadwerksExporter(object):
    FLOAT_EPSILON = 0.0000000001

    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        # bpy.ops.object.mode_set(mode='OBJECT')
        self.options = kwargs
        self.context = kwargs.get('context')
        self.cvt_matrix = self.get_conversion_matrix()
        self.materials = {}

    def export(self):
        '''
        Entry point
        '''


        exportables = self.get_exportables()

        for e in exportables:
            name = None
            if len(exportables) > 1:
                wanted_name = os.path.basename(self.options['filepath'])
                wanted_name = wanted_name[0:-4]
                name = '%s_%s' % (wanted_name, e['object'].name.lower())
            self.save_exportable(e, name)

        self.export_materials()
        return {'FINISHED'}

    def save_exportable(self, e, name=None):
        res = self.get_header()
        res += self.format_block(e, is_topmost=True)
        res += '</subblocks></block>'

        out_path = self.options['filepath']
        if name:
            out_path = os.path.join(os.path.dirname(out_path), '%s.mdl' % name)

        doc = minidom.parseString(res)
        res = doc.toprettyxml()

        with open('%s.xml' % out_path, 'w') as f:
            f.write(res)

        cc = compiler.MdlCompiler(res, out_path)
        cc.compile()

    def get_topmost_matrix(self, exportable):
        mtx = exportable['object'].matrix_world.copy()
        mtx.transpose()
        mtx = mtx * axis_conversion(
            from_forward='X',
            to_forward='X',
            from_up='Y',
            to_up='Z'
        ).to_4x4()

        inv = [[0,2],[1,2],[2,0],[2,1],[3,2]]
        mtx = list(mtx)
        for i in inv:
            v = -mtx[i[0]][i[1]]
            mtx[i[0]][i[1]] = v
        mtx = Matrix(mtx)
        print(mtx)
        return Matrix(mtx)

    def format_block(self, exportable, is_topmost=False):
        if is_topmost:
            matrix = self.get_topmost_matrix(exportable)
        else:
            matrix = exportable['object'].matrix_basis.copy()
            matrix.transpose()
            inv = [[0,2],[1,2],[2,0],[2,1],[3,2]]
            mtx = list(matrix)
            for i in inv:
                v = -mtx[i[0]][i[1]]
                mtx[i[0]][i[1]] = v
            matrix = Matrix(mtx)
        if exportable['type'] == 'MESH':
            return self.format_mesh(exportable, matrix)
        else:
            return self.format_node(exportable, matrix)
        return ''

    def export_materials(self):
        textures = []
        for m in self.materials.values():
            dir = os.path.dirname(self.options['filepath'])
            m.save(dir)

    def get_conversion_matrix(self):
        cvt_matrix = axis_conversion(
            from_forward='X',
            to_forward='Z',
            from_up='Z',
            to_up='-Y'
        ).to_4x4()

        mirror_z = Matrix.Scale(-1, 4, Vector((0.0, 0.0, 1.0)))
        return mirror_z

    def get_header(self):
        ret = '<block name="FILE" code="%s">' % constants.MDL_FILE
        ret += '<num_kids>1</num_kids>'
        ret += '<version>2</version><subblocks>'
        return ret

    def append(self, data):
        self.out_xml = '%s%s' % (self.out_xml, data)

    def get_exportables(self, target=None):
        """
        Collect exportable objects in current scene
        """
        exportables = []
        items = []
        if not target:
            for o in self.context.scene.objects:
                if o.parent:
                    continue
                items.append(o)
        else:
            items = list(target.children)

        for ob in items:
            is_meshable = self.is_meshable(ob)
            if not is_meshable and not self.has_meshables(ob):
                continue
            item = {}
            if ob.type == 'ARMATURE':
                for m in ob.children:
                    if self.is_meshable(m):
                        item.update({
                            'type': 'MESH',
                            'object': m,
                        })
                        ob = m
                        break # only one mesh per armature supported
            elif is_meshable:
                item.update({
                    'type': 'MESH',
                    'object': ob,
                })
            else:
                item.update({
                    'type': 'NODE',
                    'object': ob,
                })
            item['children'] = self.get_exportables(ob)
            exportables.append(item)
        return exportables

    def is_meshable(self, obj):
        return obj.type == 'MESH'

    def has_meshables(self, obj):
        for ob in obj.children:
            if self.is_meshable(ob) or self.has_meshables(ob):
                return True
        return False


    def format_matrix(self, matrix):
        print(matrix)
        ret = '<matrix>'
        floats = []
        for v in matrix:
            floats.extend([f for f in v])
        ret += ','.join(map(str, floats))
        ret += '</matrix>'
        return ret

    def format_props(self, props):
        """
        Formating a list of properties like:
        [
            ['name', 'Cube'],
            ['key', 'value'],
            ...
        ]
        into valid xml reprezentation
        """
        ret = '<block name="PROPERTIES" code="%s">' % constants.MDL_PROPERTIES
        ret += '<num_kids>0</num_kids>'
        ret += '<count>%s</count>' % len(props)
        ret += '<properties>'
        for k, v in props:
            ret += '<value means="%s">%s</value>' % (k, v)
        ret += '</properties>'
        ret += '</block>'
        return ret

    def to_str_list(self, floats_list):
        return ['%.9f' % f for f in floats_list]

    def get_surfaces(self, mesh):
        '''
        Split the single mesh into list of surfaces by materials
        '''
        materials = [Material(
            name='default'
        )]

        for idx, m in enumerate(mesh.data.materials):
            materials.append(Material(blender_data=m))

        mesh = self.triangulate_mesh(mesh)
        mesh.transform(self.cvt_matrix)
        mesh.calc_normals()

        verts = {}
        for vert in mesh.vertices:
            verts[str(vert.index)] = {
                'position': self.to_str_list(list(vert.co)),
                'normals': self.to_str_list(
                    [vert.normal.x, vert.normal.y, vert.normal.z]
                )
            }

        tcoords = {}
        for l in mesh.tessface_uv_textures:
            for face_idx, coords in l.data.items():
                ic = [
                    self.to_str_list([coords.uv1[0], 1 - coords.uv1[1]]),
                    self.to_str_list([coords.uv2[0], 1 - coords.uv2[1]]),
                    self.to_str_list([coords.uv3[0], 1 - coords.uv3[1]]),
                ]
                tcoords[str(face_idx)] = ic
            break

        faces_map = {}
        verts_by_tc = {}
        for i, face in enumerate(mesh.tessfaces):
            idx = face.index
            k = str(face.material_index)

            if not k in faces_map:
                faces_map[k] = []

            f_verts = list(map(str, list(face.vertices)))

            coords = tcoords.get(str(idx))

            if coords:
                for vpos, vert_idx in enumerate(f_verts):
                    icoords = coords[vpos]
                    hash = '%s_%s' % (vert_idx, '_'.join(icoords))

                    v = verts.get(vert_idx)
                    if v.get('texture_coords'):
                        hash = '%s_%s' % (vert_idx, '_'.join(coords[vpos]))
                        if verts_by_tc.get(hash):
                            continue

                        new_vert = copy(v)
                        new_vert['texture_coords'] = icoords
                        new_idx = str(len(verts.keys()))
                        new_hash = '%s_%s' % (new_idx, '_'.join(icoords))
                        verts_by_tc[new_hash] = new_idx
                        verts[new_idx] = new_vert
                        f_verts[vpos] = new_idx
                    else:
                        verts_by_tc[hash] = vert_idx
                        verts[vert_idx]['texture_coords'] =icoords

            faces_map[k].append({
                'material_index': face.material_index,
                'vertex_indices': list(reversed(f_verts)),
            })

        surfaces = []

        for mat_idx, surface_data in faces_map.items():
            vertices_map = {}

            vertices = []
            normals = []
            texture_coords = []
            tangents = []
            binormals = []
            indices = []
            bone_weights = []
            bone_indexes = []

            for face in surface_data:
                for v in face['vertex_indices']:
                    idx = vertices_map.get(str(v))
                    if idx is None:
                        real_vert = verts[v]
                        idx = len(vertices_map.values())
                        vertices_map[str(v)] = idx

                        # Distributing texture coordinates
                        texture_coords.extend(real_vert.get('texture_coords', ['0.0', '0.0']))
                        orig_vert = verts.get(str(v))
                        vertices.extend(orig_vert['position'])
                        normals.extend(orig_vert['normals'])

                    indices.append(idx)
            vert_ids = list(set(map(int, vertices_map.keys())))
            vert_ids.sort()

            for vert_id in map(str, vert_ids):
                bone_weights.extend([0,0,0,0])
                bone_indexes.extend([0,0,0,0])
                tangents.extend(['0.0']*3)
                binormals.extend(['0.0']*3)

            try:
                mat = materials[int(mat_idx)+1]
            except IndexError:
                mat = materials[0]
            surfaces.append({
                'material': mat,
                'vertices': vertices,
                'normals': normals,
                'indices': indices,
                'texture_coords': texture_coords,
                'tangents': tangents,
                'binormals': binormals,
                'bone_weights': bone_weights,
                'bone_indexes': bone_indexes,

            })

        for s in surfaces:
            m = s['material']
            if m['index'] is None:
                continue

            bd = m['blender_data']
            self.materials[bd] = m

        return surfaces

    def get_bone_weights(self, obj, verts):
        weights = {}

        if obj.parent is not None and obj.parent.type == 'ARMATURE':
            arm_obj = obj.parent
            for vertex_index, v in verts.items():
                int_vertex_index = int(vertex_index)
                iws = weights.get(vertex_index, [])
                for vertex_group in obj.vertex_groups:
                    try:
                        bone = arm_obj.data.bones[vertex_group.name]
                    except:
                        continue

                    try:
                        bone_weight = vertex_group.weight(int_vertex_index)
                        bone_weight = '%.9f' % bone_weight
                        iws.append(
                            [bone.name, bone_weight]
                        )
                        weights[vertex_index] = iws
                    except:
                        continue

    def format_floats(self, floats):
        return ','.join(floats)

    def format_ints(self, ints):
        return ','.join('%s' % i for i in ints)

    def format_surface(self, surface):
        ret = '<block name="SURFACE" code="%s">' % constants.MDL_SURFACE
        ret += '<num_kids>7</num_kids>'
        ret += '<subblocks>'
        ret += self.format_props([['material', surface['material']['name']]])

        vcount = int(len(surface['vertices'])/3)

        # Vertices
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>3</elements_count>'
        ret += '<data_type><value means="POSITION">%s</value></data_type>' % constants.MDL_POSITION
        ret += '<variable_type><value means="FLOAT">8</value></variable_type>'
        ret += '<data>%s</data>' % self.format_floats(surface['vertices'])
        ret += '</block>'

        # Normals
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>3</elements_count>'
        ret += '<data_type><value means="NORMAL">%s</value></data_type>' % constants.MDL_NORMAL
        ret += '<variable_type><value means="FLOAT">8</value></variable_type>'
        ret += '<data>%s</data>' % self.format_floats(surface['normals'])
        ret += '</block>'

        # Texture coords
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>2</elements_count>'
        ret += '<data_type><value means="TEXTURE_COORD">%s</value></data_type>' % constants.MDL_TEXTURE_COORD
        ret += '<variable_type><value means="FLOAT">8</value></variable_type>'
        ret += '<data>%s</data>' % self.format_floats(surface['texture_coords'])
        ret += '</block>'

        # Tangents
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>3</elements_count>'
        ret += '<data_type><value means="TANGENT">%s</value></data_type>' % constants.MDL_TANGENT
        ret += '<variable_type><value means="FLOAT">8</value></variable_type>'
        ret += '<data>%s</data>' % self.format_floats(surface['tangents'])
        ret += '</block>'

        # Binormals
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>3</elements_count>'
        ret += '<data_type><value means="BINORMAL">%s</value></data_type>' % constants.MDL_BINORMAL
        ret += '<variable_type><value means="FLOAT">8</value></variable_type>'
        ret += '<data>%s</data>' % self.format_floats(surface['binormals'])
        ret += '</block>'

        '''
        # Bone indexes
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>4</elements_count>'
        ret += '<data_type><value means="BONEWEIGHT">%s</value></data_type>' % constants.MDL_BONEINDICE
        ret += '<variable_type><value means="BYTE">2</value></variable_type>'
        ret += '<data>%s</data>' % self.format_ints(surface['bone_indexes'])
        ret += '</block>'


        # Bone weights
        ret += '<block code="%s" name="VERTEXARRAY">' % constants.MDL_VERTEXARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_vertices>%s</number_of_vertices>' % vcount
        ret += '<elements_count>4</elements_count>'
        ret += '<data_type><value means="BONEWEIGHT">%s</value></data_type>' % constants.MDL_BONEWEIGHT
        ret += '<variable_type><value means="BYTE">2</value></variable_type>'
        ret += '<data>%s</data>' % self.format_ints(surface['bone_weights'])
        ret += '</block>'
        '''

        # Vertex indexes (faces)
        ret += '<block code="%s" name="INDICEARRAY">' % constants.MDL_INDICEARRAY
        ret += '<num_kids>0</num_kids>'
        ret += '<number_of_indexes>%s</number_of_indexes>' % len(surface['indices'])
        ret += '<primitive_type>%s</primitive_type>' % constants.MDL_TRIANGLES
        ret += '<variable_type><value means="SHORT">4</value></variable_type>'
        ret += '<data>%s</data>' % self.format_ints(surface['indices'])
        ret += '</block>'
        ret += '</subblocks>'
        ret += '</block>'
        return ret

    def format_mesh(self, exportable, matrix):
        ret = '<block name="MESH" code="%s">' % constants.MDL_MESH
        m = exportable['object']
        surfaces = self.get_surfaces(exportable['object'])
        num_kids = len(surfaces)+len(exportable['children'])+1
        ret += '<num_kids>%s</num_kids>' % num_kids
        ret += self.format_matrix(matrix)
        ret += '<subblocks>'
        ret += self.format_props([['name', m.name]])

        for surf in surfaces:
            ret += self.format_surface(surf)

        # here should be BONE formatter somehow

        for block in exportable['children']:
            ret += self.format_block(block)

        ret += '</subblocks>'
        ret += '</block>'
        return ret

    def format_node(self, exportable, matrix):
        ret = '<block name="NODE" code="%s">' % constants.MDL_NODE
        num_kids = len(exportable['children'])+1
        ret += '<num_kids>%s</num_kids>' % num_kids

        ret += self.format_matrix(matrix)
        ret += '<subblocks>'
        ret += self.format_props([['name', exportable['object'].name]])
        for block in exportable['children']:
            ret += self.format_block(block)

        ret += '</subblocks>'
        ret += '</block>'
        return ret

    def triangulate_mesh(self, meshable_obj):
        bm = bmesh.new()

        mesh = meshable_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')

        bm.from_object(meshable_obj, bpy.context.scene, deform=True, render=False)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        mesh.update(calc_tessface=True, calc_edges=True)
        return mesh