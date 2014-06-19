# <pep8 compliant>

import os

from xml.dom import minidom

from mathutils import Vector, Matrix, Euler

from . import constants
from . import utils
from . import templates

from .mesh import Mesh
from .config import CONFIG

from xml_tool import compiler


class LeadwerksExporter(object):
    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        # bpy.ops.object.mode_set(mode='OBJECT')
        self.options = kwargs
        self.context = kwargs.get('context')
        self.materials = {}
        self.out_xml = ''
        CONFIG.update(self.options)

    def update_config(self):
        for k, v in dict(CONFIG.__dict__).items():
            default = v
            val = self.options.get(k, default)
            setattr(CONFIG, k, val)

    def export(self):
        """
        Entry point
        """

        exportables = self.get_exportables()

        if not exportables:
            self.options['operator'].report(
                {'ERROR'},
                "Couldn't find any exportable objects"
            )
            return {'CANCELLED'}

        for e in exportables:
            wanted_name = os.path.basename(self.options['filepath'])
            name = wanted_name[0:-4]
            if len(exportables) > 1:
                name = '%s_%s' % (name, e['object'].name.lower())
            self.save_exportable(e, name)

        self.export_materials()
        return {'FINISHED'}

    def save_exportable(self, e, name=None):
        context = {
            'code': constants.MDL_FILE,
            'version': CONFIG.file_version,
            'childs': self.format_block(e, is_topmost=True)
        }
        res = templates.render('FILE', context)

        out_path = self.options['filepath']
        if name:
            name = '%s%s' % (name, CONFIG.file_extension)
            out_path = os.path.join(os.path.dirname(out_path), name)

        doc = minidom.parseString(res)
        res = doc.toprettyxml()

        if CONFIG.write_debug_xml:
            with open('%s.xml' % out_path, 'w') as f:
                f.write(res)

        cc = compiler.MdlCompiler(res, out_path)
        cc.compile()

    def get_topmost_matrix(self, exportable):
        obj = exportable['object']
        mtx = obj.matrix_world.copy()
        mtx = utils.convert_to_lw_matrix(mtx)
        return mtx

    def format_block(self, exportable, is_topmost=False):
        if is_topmost:
            matrix = self.get_topmost_matrix(exportable)
        else:
            matrix = exportable['object'].matrix_local.copy()
            #matrix.transpose()
            #matrix = utils.magick_convert(matrix)
            matrix = utils.convert_to_lw_matrix(matrix)

        if exportable['type'] == 'MESH':
            return self.format_mesh(exportable, matrix)
        else:
            return self.format_node(exportable, matrix)

    def export_materials(self):
        if not CONFIG.export_materials:
            return
        for m in self.materials.values():
            dir = os.path.dirname(self.options['filepath'])
            m.save(dir)

    def append(self, data):
        self.out_xml = '%s%s' % (self.out_xml, data)

    def get_exportables(self, target=None):
        """
        Collect exportable objects in current scene
        """
        exportables = []
        items = []
        if not target:
            if CONFIG.export_selection:
                objs = self.context.selected_objects
            else:
                objs = self.context.scene.objects

            for o in objs:
                if o.parent:
                    continue
                items.append(o)
        else:
            items = list(target.children)

        for ob in items:
            is_meshable = self.is_meshable(ob)
            if not is_meshable and not self.has_meshables(ob):
                continue
            if ob.type == 'ARMATURE':
                exportables.extend(
                    self.get_exportables(ob)
                )
                continue
            elif is_meshable:
                    item = {
                        'type': 'MESH',
                        'object': ob,
                    }
            else:
                item = {
                    'type': 'NODE',
                    'object': ob,
                }
            item['children'] = self.get_exportables(ob)
            exportables.append(item)
        return exportables

    def is_meshable(self, obj):
        """
        Detects if exporter can convert this type of object into mesh
        """
        if obj.type == 'MESH':
            return True

        try:
            od = obj.data

            # Support of mesh-like curves
            if obj.type == 'CURVE' and (od.bevel_depth > 0 or od.extrude):
                return True
        except:
            raise

        return False

    def has_meshables(self, obj):
        for ob in obj.children:
            if self.is_meshable(ob) or self.has_meshables(ob):
                return True
        return False

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
        return templates.render(
            'PROPERTIES',
            {'code': constants.MDL_PROPERTIES, 'props': props}
        )

    def format_surface(self, surface):
        vc = int(len(surface['vertices'])/3)

        vertexarray = [
            templates.render(
                # Vertices
                'VERTEXARRAY',
                {
                    'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                    'elements_count': 3,
                    'data_type': ['POSITION', constants.MDL_POSITION],
                    'variable_type': ['FLOAT', constants.MDL_FLOAT],
                    'data': ','.join(surface['vertices'])

                },
            ),

            templates.render(
                # Normals
                'VERTEXARRAY',
                {
                    'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                    'elements_count': 3,
                    'data_type': ['NORMAL', constants.MDL_NORMAL],
                    'variable_type': ['FLOAT', constants.MDL_FLOAT],
                    'data': ','.join(surface['normals'])

                },
            ),
        ]

        if surface['texture_coords']:
            vertexarray.append(
                templates.render(
                    # Texture coords
                    'VERTEXARRAY',
                    {
                        'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                        'elements_count': 2,
                        'data_type': ['TEXTURE_COORD', constants.MDL_TEXTURE_COORD],
                        'variable_type': ['FLOAT', constants.MDL_FLOAT],
                        'data': ','.join(surface['texture_coords'])

                    },
                ),
            )

        if surface['tangents']:
            vertexarray.extend([
                templates.render(
                    # Tangents
                    'VERTEXARRAY',
                    {
                        'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                        'elements_count': 3,
                        'data_type': ['TANGENT', constants.MDL_TANGENT],
                        'variable_type': ['FLOAT', constants.MDL_FLOAT],
                        'data': ','.join(surface['tangents'])
                    },
                ),
                templates.render(
                    # Binormals
                    'VERTEXARRAY',
                    {
                        'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                        'elements_count': 3,
                        'data_type': ['BINORMAL', constants.MDL_BINORMAL],
                        'variable_type': ['FLOAT', constants.MDL_FLOAT],
                        'data': ','.join(surface['binormals'])
                    },
                ),
            ])

        if CONFIG.export_animation:
            vertexarray.extend([
                templates.render(
                    # Bone indexes
                    'VERTEXARRAY',
                    {
                        'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                        'elements_count': 4,
                        'data_type': ['BONEINDICE', constants.MDL_BONEINDICE],
                        'variable_type': ['BYTE', constants.MDL_UNSIGNED_BYTE],
                        'data': ','.join(surface['bone_indexes'])

                    },
                ),
                templates.render(
                    # Bone weights
                    'VERTEXARRAY',
                    {
                        'code': constants.MDL_VERTEXARRAY, 'number_of_vertices': vc,
                        'elements_count': 4,
                        'data_type': ['BONEWEIGHT', constants.MDL_BONEWEIGHT],
                        'variable_type': ['BYTE', constants.MDL_UNSIGNED_BYTE],
                        'data': ','.join(surface['bone_weights'])

                    },
                )
            ])

        mat = surface['material']
        if not mat.name in self.materials.keys():
            self.materials[mat.name] = mat

        context = {
            'code': constants.MDL_SURFACE,
            'props': self.format_props([['material', mat.name]]),
            'vertexarray': vertexarray,
            'num_kids': len(vertexarray) + 1
        }



        # Vertex indexes (faces)
        context['indice_array'] = templates.render(
            'INDICEARRAY',
            {
                'code': constants.MDL_INDICEARRAY,
                'number_of_indexes': len(surface['indices']),
                'primitive_type': constants.MDL_TRIANGLES,
                'data_type': ['TEXTURE_COORD', constants.MDL_TEXTURE_COORD],
                'variable_type': ['SHORT', constants.MDL_SHORT],
                'data': ','.join(map(str, surface['indices']))

            },
        )

        return templates.render('SURFACE', context)

    def format_mesh(self, exportable, matrix):

        m = Mesh(exportable['object'])
        surfaces = m.surfaces
        num_kids = len(surfaces)+len(exportable['children'])+1

        bones = ''
        arm = m.armature
        if arm and CONFIG.export_animation:
            bones = utils.join_map(self.format_bone, arm.bones)
            if bones:
                num_kids += len(arm.bones)
            matrix = Matrix.Identity(4)

        context = {
            'code': constants.MDL_MESH,
            'num_kids': num_kids,
            'matrix': utils.format_floats_box(matrix),
            'props': self.format_props([['name', m.name]]),
            'surfaces': utils.join_map(self.format_surface, surfaces),
            'bones': bones,
            'childs': utils.join_map(self.format_block, exportable['children'])
        }

        return templates.render('MESH', context)

    def format_node(self, exportable, matrix):
        context = {
            'code': constants.MDL_NODE,
            'num_kids': len(exportable['children'])+1,
            'matrix': utils.format_floats_box(matrix),
            'props': self.format_props([['name', exportable['object'].name]]),
            'childs': utils.join_map(self.format_block, exportable['children'])
        }
        return templates.render('NODE', context)

    def format_bone(self, bone):
        context = {
            'code': constants.MDL_BONE,
            'num_kids': len(bone.children)+len(bone.animations)+1,
            'bone_id': bone.index,
            'matrix': utils.format_floats_box(bone.matrix_basis),
            'props': self.format_props([['name', bone.name]]),
            'animations': utils.join_map(self.format_animation_keys, bone.animations),
            'childs': utils.join_map(self.format_bone, bone.children)
        }
        return templates.render('BONE', context)

    def format_animation_keys(self, data):
        context = {
            'code': constants.MDL_ANIMATIONKEYS,
            'keyframes': list(map(utils.format_floats_box, data['keyframes'])),
            'animation_name': data['name'] if int(CONFIG.file_version) > 1 else ''
        }
        return templates.render('ANIMATIONKEYS', context)