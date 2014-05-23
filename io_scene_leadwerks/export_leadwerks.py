# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>
from copy import copy
import os

from xml.dom import minidom
import bpy
import bmesh
from bpy_extras.io_utils import axis_conversion
import subprocess
from .leadwerks.mdl import constants
from .xml_tool import compiler
from mathutils import Vector, Matrix


class LeadwerksExporter(object):
    FLOAT_EPSILON = 0.000000001

    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')
        self.options = kwargs
        self.context = kwargs.get('context')
        self.cvt_matrix = self.get_conversion_matrix()
        self.out_xml = ''
        self.meshes = []
        self.materials = {}

    def export(self):
        '''
        Entry point
        '''
        self.append(self.get_header())

        exportables = self.get_exportables()
        for e in exportables:
            if e.type == 'MESH':
                self.append(self.format_mesh(e))

        self.append('</subblocks></block>')

        doc = minidom.parseString(self.out_xml)
        self.out_xml = doc.toprettyxml()

        out_path = self.options['filepath']

        with open('%s.xml' % out_path, 'w') as f:
            f.write(self.out_xml)

        cc = compiler.MdlCompiler(self.out_xml, out_path)
        cc.compile()

        textures = []
        for m in self.materials.values():
            dir = os.path.dirname(out_path)
            fname = os.path.join(dir, '%s.mat' % m['name'])
            bd = m['blender_data']
            out = '''//Leadwerks Material File
            blendmode=0
            castshadows=1
            zsort=0
            cullbackfaces=1
            depthtest=1
            depthmask=1
            alwaysuseshader=0
            drawmode=-1
            shader="Shaders/Model/diffuse.shader"
            '''

            out += 'diffuse: %s\n' % ','.join(['%.9f' % c for c in list(bd.diffuse_color)])
            out += 'specular: %s\n' % ','.join(['%.9f' % c for c in list(bd.specular_color)])

            for i, ts in enumerate(bd.texture_slots):
                try:
                    texture_name = ts.name.lower()
                    i = ts.texture.image
                    i.filepath_raw = os.path.join(dir, '%s.png' % texture_name)
                    i.file_format = 'PNG'
                    i.save()
                    textures.append(i.filepath_raw)
                    out += 'texture%s="./%s.tex"' % (i, texture_name)
                except:
                    pass
            with open(fname, 'w') as f:
                f.write(out.replace('    ', ''))

        for t in textures:
            subprocess.call(
                '/home/alrusdi/dev/Leadwerks/Tools/img2tex.linux "%s"' % t,
                shell=True
            )

        return {'FINISHED'}

    def get_conversion_matrix(self):
        cvt_matrix = axis_conversion(
            from_forward='X',
            to_forward='-Z',
            from_up='Z',
            to_up='-Y'
        ).to_4x4()

        mirror_z = Matrix.Scale(-1, 4, Vector((0.0, 0.0, 1.0)))

        return cvt_matrix * mirror_z


    def get_header(self):
        return '<block name="FILE" code="1"><num_kids>1</num_kids><version>2</version><subblocks>'

    def append(self, data):
        self.out_xml = '%s%s' % (self.out_xml, data)

    def get_exportables(self):
        """
        Collect topmost exportable objects in current scene
        """
        for ob in self.context.scene.objects:
            if ob.parent:
                continue

            if ob.type == 'MESH':
                self.meshes.append(ob)

        return self.meshes

    def format_matrix(self, matrix):
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
        materials = [
            {'index': None, 'name': 'default', 'material': None}
        ]

        for idx, m in enumerate(mesh.data.materials):
            materials.append({
                'index': idx,
                'name': '%s_%s' % (mesh.name.lower(), m.name.lower()),
                'blender_data': m
            })

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
                tcoords[str(face_idx)] = [
                    self.to_str_list(list(coords.uv1)),
                    self.to_str_list(list(coords.uv2)),
                    self.to_str_list(list(coords.uv3)),
                ]
            break

        faces_map = {}
        total = len(mesh.tessfaces)
        verts_by_tc = {}
        for i, face in enumerate(mesh.tessfaces):
            idx = face.index
            k = str(face.material_index)

            if not k in faces_map:
                faces_map[k] = []

            f_verts = list(map(str, list(face.vertices)))

            coords = tcoords.get(str(idx))

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

    def format_floats(self, floats):
        return ','.join(floats)

    def format_ints(self, ints):
        return ','.join('%s' % i for i in ints)

    def format_surface(self, surface):
        ret = '<block name="SURFACE" code="%s">' % constants.MDL_SURFACE
        ret += '<num_kids>7</num_kids>'
        ret += '<subblocks>'
        ret += self.format_props([['material', 'green']])

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

    def format_mesh(self, m):
        ret = '<block name="MESH" code="%s">' % constants.MDL_MESH
        ret += '<num_kids>2</num_kids>'
        ret += self.format_matrix(m.matrix_basis)
        ret += '<subblocks>'
        ret += self.format_props([['name', m.name]])

        for surf in self.get_surfaces(m):
            ret += self.format_surface(surf)

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
