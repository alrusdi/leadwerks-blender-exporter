from copy import copy

from mathutils import Vector, Matrix

from .armature import Armature
from .material import Material
from . import utils


class Mesh(object):
    def __init__(self, blender_data):
        self.name = blender_data.name
        self.is_animated = False
        self.blender_data = blender_data
        self.armature = self.parse_armature()

        self.__verts = {}
        self.materials = {}
        self.surfaces = self.parse_surfaces()

    def parse_armature(self):
        p = self.blender_data.parent
        if p and p.type == 'ARMATURE':
            return Armature(self.parent)

    def parse_bone_weights(self):
        weights = {}

        if self.armature:
            arm_obj = self.armature.blender_data
            for vertex_index, v in self.__verts.items():
                int_vertex_index = int(vertex_index)
                iws = weights.get(vertex_index, [])
                for vertex_group in self.blender_data.vertex_groups:
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
        return weights

    def parse_surfaces(self):
        '''
        Split the single mesh into list of surfaces by materials
        '''

        mesh = self.blender_data

        materials = [Material(
            name='default'
        )]

        for idx, m in enumerate(mesh.data.materials):
            materials.append(Material(blender_data=m))

        mesh = utils.triangulate_mesh(mesh)
        # Mirroring mesh by Z axis to match Leadwerks coordinate system
        mesh.transform(Matrix.Scale(-1, 4, Vector((0.0, 0.0, 1.0))))
        mesh.calc_normals()

        verts = {}
        for vert in mesh.vertices:
            verts[str(vert.index)] = {
                'position': utils.to_str_list(list(vert.co)),
                'normals': utils.to_str_list(
                    [vert.normal.x, vert.normal.y, vert.normal.z]
                )
            }

        tcoords = {}
        for l in mesh.tessface_uv_textures:
            for face_idx, coords in l.data.items():
                ic = []
                for uv in [coords.uv1, coords.uv2, coords.uv3]:
                    ic.append([uv[0], 1 - uv[1]])
                tcoords[str(face_idx)] = list(map(utils.to_str_list, ic))
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

        self.__verts = verts

        surfaces = []

        for mat_idx, surface_data in faces_map.items():
            vertices_map = {}

            vertices = []
            normals = []
            texture_coords = []
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
                        texture_coords.extend(real_vert.get('texture_coords', ['0.0']*2))
                        orig_vert = verts.get(str(v))
                        vertices.extend(orig_vert['position'])
                        normals.extend(orig_vert['normals'])

                    indices.append(idx)
            vert_ids = list(set(map(int, vertices_map.keys())))
            vert_ids.sort()

            for vert_id in map(str, vert_ids):
                bone_weights.extend([0]*4)
                bone_indexes.extend([0]*4)

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
                'bone_weights': bone_weights,
                'bone_indexes': bone_indexes,

            })

        for s in surfaces:
            m = s['material']
            if not m.name in self.materials.keys():
                self.materials[m.name] = m

        return surfaces
