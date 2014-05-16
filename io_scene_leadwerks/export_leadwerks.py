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
from .leadwerks.mdl import constants


class LeadwerksExporter(object):

    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        self.options = kwargs
        self.context = kwargs.get('context')
        self.cvt_matrix = axis_conversion(from_forward='-X', from_up='-Z').to_4x4()
        self.out_xml = ''
        self.meshes = []

    def get_header(self):
        return '<block name="FILE" code="1"><num_kids>1</num_kids><version>1</version><subblocks>'

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
            verts[str(vert.index)] = list(vert.undeformed_co)

        faces_map = {}
        for face in mesh.tessfaces:
            k = str(face.material_index)

            if not k in faces_map:
                faces_map[k] = []

            faces_map[k].append({
                'material_index': face.material_index,
                'vertex_indices': list(face.vertices)
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

            for face in surface_data:
                for v in face['vertex_indices']:
                    idx = vertices_map.get(str(v))
                    if idx is None:
                        idx = len(vertices_map.values())
                        vertices_map[str(v)] = idx
                    indices.append(idx)

            vert_ids = list(set(map(int, vertices_map.keys())))
            vert_ids.sort()

            for vert_id in map(str, vert_ids):
                vertices.extend(verts.get(vert_id))

            try:
                mat = materials[int(mat_idx)+1]
            except ValueError:
                mat = materials[0]
            surfaces.append({
                'material': mat,
                'vertices': vertices,
                'indices': indices
            })

    def format_mesh(self, m):
        ret = '<block name="MESH" code="%s">' % constants.MDL_MESH
        ret += '<num_kids>2</num_kids>'
        ret += self.format_matrix(m.matrix_basis)
        ret += '<subblocks>'
        ret += self.format_props([['name', m.name]])
        ret += '</subblocks>'
        ret += '</block>'
        return ret

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

    def triangulate_mesh(meshable_obj):
        bm = bmesh.new()

        mesh = meshable_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')

        bm.from_object(meshable_obj, bpy.context.scene, deform=True, render=False)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        mesh.update(calc_tessface=True, calc_edges=True)
        mesh.calc_normals()

        return mesh
