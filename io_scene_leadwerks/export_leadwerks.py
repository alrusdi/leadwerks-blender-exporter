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
from collections import OrderedDict

import bpy
import bmesh
import math
import time
from bpy_extras.io_utils import axis_conversion
from leadwerks.mdl import constants


class LeadwerksExporter(object):

    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        self.options = kwargs
        self.context = kwargs.get('context')
        self.cvt_matrix = axis_conversion(from_forward='-X', from_up='-Z').to_4x4()
        self.out_xml = ''
        self.meshes = []

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
        print(self.out_xml)
        return {'FINISHED'}

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

    def get_surfaces(self, mesh):
        '''
        Split the single mesh by used materials into list of surfaces
        '''
        materials = [
            {'index': 'None', 'name': 'default.mat', 'material': None}
        ]

        for idx, m in enumerate(mesh.data.materials):
            materials.append({
                'index': idx,
                'name': '',
                'material': m
            })

        mesh = self.triangulate_mesh(mesh)

        verts = {}
        for vert in mesh.vertices:
            verts[str(vert.index)] = {
                'position': list(vert.co),
                'normals': [vert.normal.x, vert.normal.y, vert.normal.z]
            }

        faces_map = {}
        for face in mesh.tessfaces:
            idx = face.index
            k = str(face.material_index)

            if not k in faces_map:
                faces_map[k] = []

            f_verts = list(face.vertices)

            face_tex_coords = []
            for l in mesh.tessface_uv_textures:
                for face_idx, coords in l.data.items():
                    if face_idx != idx:
                        continue
                    # face.loop_indices[vertex] ?
                    face_tex_coords.append({
                       str(f_verts[0]): list(coords.uv[0]),
                       str(f_verts[1]): list(coords.uv[1]),
                       str(f_verts[2]): list(coords.uv[2])
                    })

            faces_map[k].append({
                'material_index': face.material_index,
                'vertex_indices': f_verts,
                'texture_coords': face_tex_coords
            })

        #from pprint import pprint
        #pprint(faces_map)
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
                        idx = len(vertices_map.values())
                        vertices_map[str(v)] = idx

                        # Distributing texture coordinates
                        tc = [0.0] * 2
                        ct = 0
                        for i, itc in enumerate(face['texture_coords']):
                            itc = itc.get(str(v), [0.0]*2)
                            if i < 1:
                                tc[ct] = itc[0]
                                tc[ct+1] = itc[1]
                                ct += 2
                        texture_coords.extend(tc)

                    indices.append(idx)
            vert_ids = list(set(map(int, vertices_map.keys())))
            vert_ids.sort()

            for vert_id in map(str, vert_ids):
                data = verts.get(vert_id)
                vertices.extend(data['position'])
                normals.extend(data['normals'])
                bone_weights.extend([0,0,0,0])
                bone_indexes.extend([0,0,0,0])
                tangents.extend([0.0]*3)
                binormals.extend([0.0]*3)

            try:
                mat = materials[int(mat_idx)+1]
            except ValueError:
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
        #pprint(surfaces)
        return surfaces

    def format_floats(self, floats):
        return ','.join('%f' % f for f in floats)

    def format_ints(self, ints):
        return ','.join('%s' % i for i in ints)

    def format_surface(self, surface):
        ret = '<block name="SURFACE" code="%s">' % constants.MDL_SURFACE
        ret += '<num_kids>7</num_kids>'
        ret += '<subblocks>'
        ret += self.format_props([['material', 'default.mat']])

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
        mesh.calc_normals()

        return mesh
