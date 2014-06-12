from copy import copy

from mathutils import Vector, Matrix

from .armature import Armature
from .config import CONFIG
from .material import Material
from . import utils, texspace


class Mesh(object):
    """
    Helper class for Mesh data extraction and decomposition it to surfaces
    """
    def __init__(self, blender_data):
        self.name = blender_data.name
        self.is_animated = False
        self.blender_data = blender_data
        self.armature = self.parse_armature()

        self.__verts = {}
        self.materials = {}
        self.surfaces = self.parse_surfaces()

    def parse_armature(self):
        # Getting first available Armature of object
        # No multiple armatures supported
        for mod in self.blender_data.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                return Armature(mod.object)

    def parse_bone_weights(self, mesh):
        weights = {}

        if not self.armature:
            return {}

        # Matching VertexGroups to bones of current Armature
        vg_data = {}
        for vg in self.blender_data.vertex_groups:

            bone = self.armature.get_bone_by_name(vg.name)
            bone_index = bone.index if bone else 0
            vg_data[str(vg.index)] = bone_index

        # Constructing a pairs [bone_index, bone_weight]
        for v in self.triangulated_mesh.vertices:
            iws = []
            for g in v.groups:
                bone_index = vg_data.get(str(g.group))
                if bone_index is None:
                    raise Exception()
                w = g.weight
                iws.append([bone_index, w])
            # Sorting by weight
            iws = sorted(iws, key=lambda d: d[1], reverse=True)

            # Supporting only 4 top weighted bones (some weights may lost)
            if len(iws) > 4 and iws[4][1]:
                print('Lost weight', v.index, iws)
            iws = iws[0:4]

            wsum = sum([i[1] for i in iws])
            if wsum:
                # Normalizing weights
                # Sum of all bone weights should be 255
                for i, iv in enumerate(iws):
                    w = int(iv[1]*255.0/wsum)
                    iws[i][1] = w
            else:
                # Default value for non weight painted vertex
                # This vertex will just follow bone in first available group
                print('Fallback for', v.index)
                iws[0][1] = 255

            weights[str(v.index)] = iws

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
        trans = Matrix.Scale(-1, 4, Vector((0.0, 0.0, 1.0))) * self.blender_data.matrix_world
        mesh.transform(trans)
        #mesh.calc_normals()
        self.triangulated_mesh = mesh

        verts = {}
        for vert in mesh.vertices:
            verts[str(vert.index)] = {
                'position': utils.to_str_list(list(vert.co)),
                'normals': utils.to_str_list(
                    [vert.normal.x, vert.normal.y, vert.normal.z]
                ),
                'bone_indexes': ['0', '0', '0', '0'],
                'bone_weights': ['0', '0', '0', '0'],
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
        has_texture_coords = False
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
                        has_texture_coords = True
                        hash = '%s_%s' % (vert_idx, '_'.join(coords[vpos]))
                        if verts_by_tc.get(hash):
                            continue

                        new_vert = copy(v)
                        new_vert['texture_coords'] = icoords
                        new_vert['original_index'] = vert_idx
                        new_idx = str(len(verts.keys()))
                        new_hash = '%s_%s' % (new_idx, '_'.join(icoords))
                        verts_by_tc[new_hash] = new_idx
                        verts[new_idx] = new_vert
                        f_verts[vpos] = new_idx
                    else:
                        verts_by_tc[hash] = vert_idx
                        verts[vert_idx]['texture_coords'] = icoords

            faces_map[k].append({
                'material_index': face.material_index,
                'vertex_indices': list(reversed(f_verts)),
            })

        self.__verts = verts

        # Calculating Tangents and Binormals
        if has_texture_coords:
            for faces in faces_map.values():
                for face in faces:
                    iverts = utils.mget(verts, face['vertex_indices'])
                    texspace.update_tangents_and_binormals(iverts)

        if CONFIG.export_animation:
            # Extracting bone weights
            weights = self.parse_bone_weights(mesh)
            if weights:
                self.is_animated = True
                for k, v in verts.items():
                    if 'original_index' in v:
                        idata = weights.get(v['original_index'], [])
                    else:
                        idata = weights.get(k, [])

                    if not idata:
                        print('Empty weights:', k)


                    ivw = copy(v['bone_weights'])
                    ivi = copy(v['bone_indexes'])
                    pos = 0

                    for i, w in idata:
                        ivw[pos] = str(w)
                        ivi[pos] = str(i)
                        pos += 1

                    if ''.join(ivw) == '0000':
                        print('-'*50)
                        print(k, v)
                        print(idata)
                        raise Exception('Empty weights detected')

                    verts[k].update({
                        'bone_indexes': ivi,
                        'bone_weights': ivw
                    })


        surfaces = []
        # Splitting up mesh to multiple surfaces by material
        # because only one material per surface if allowed
        for mat_idx, surface_data in faces_map.items():
            vertices_map = {}

            vertices = []
            normals = []
            texture_coords = []
            indices = []
            bone_weights = []
            bone_indexes = []
            tangents = []
            binormals = []

            for face in surface_data:
                for v in face['vertex_indices']:
                    idx = vertices_map.get(str(v))
                    if idx is None:
                        real_vert = verts[v]
                        idx = len(vertices_map.values())
                        vertices_map[str(v)] = idx

                        # Distributing texture coordinates

                        texture_coords.extend(real_vert.get('texture_coords', []))
                        orig_vert = verts.get(str(v))
                        vertices.extend(orig_vert['position'])
                        normals.extend(orig_vert['normals'])
                        bone_weights.extend(orig_vert['bone_weights'])
                        bone_indexes.extend(orig_vert['bone_indexes'])
                        if 'tangent' in orig_vert:
                            tangents.extend(utils.to_str_list(list(orig_vert['tangent'])))
                            binormals.extend(utils.to_str_list(list(orig_vert['binormal'])))



                    indices.append(idx)

            try:
                mat = materials[int(mat_idx)+1]
            except IndexError:
                mat = materials[0]
            surf = {
                'material': mat,
                'vertices': vertices,
                'normals': normals,
                'indices': indices,
                'texture_coords': texture_coords,
                'bone_weights': bone_weights,
                'bone_indexes': bone_indexes,
                'tangents': tangents,
                'binormals': binormals
            }
            surfaces.append(surf)

        for s in surfaces:
            m = s['material']
            if not m.name in self.materials.keys():
                if self.is_animated:
                    m.is_animated = True
                self.materials[m.name] = m

        return surfaces
