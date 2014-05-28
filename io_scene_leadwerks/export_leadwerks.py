# <pep8 compliant>
from copy import copy
import os

from xml.dom import minidom

from bpy_extras.io_utils import axis_conversion
from mathutils import Vector, Matrix

from .leadwerks.mdl import constants
from . import utils
from . import templates

from .mesh import Mesh

from .xml_tool import compiler


class CONFIG(object):
    """
    This values are managed by user from GUI
    """
    file_version = 2
    file_extension = '.mdl'
    export_selection = False
    export_animation = True
    export_materials = True
    overwrite_textures = False
    export_specular_color = False
    write_debug_xml = False

    @classmethod
    def update(cls, options):
        for k, v in cls.values().items():
            default = v
            val = options.get(k, default)
            setattr(cls, k, val)
        if cls.file_extension == '.gmf':
            cls.file_version = 1

    @classmethod
    def values(cls):
        vals = {}
        types = [bool, str, int, float, dict]
        for k, v in cls.__dict__.items():
            if k.startswith('_') or type(v) not in types:
                continue
            vals[k] = v
        return vals


class LeadwerksExporter(object):
    def __init__(self, **kwargs):
        # Changes Blender to "object" mode
        # bpy.ops.object.mode_set(mode='OBJECT')
        self.options = kwargs
        self.context = kwargs.get('context')
        self.materials = {}
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

    def magick_convert(self, matrix):
            inv = [[0, 2], [1, 2], [2, 0], [2, 1], [3, 2]]
            mtx = list(matrix)
            for i in inv:
                v = -mtx[i[0]][i[1]]
                mtx[i[0]][i[1]] = v
            matrix = Matrix(mtx)
            return matrix

    def get_topmost_matrix(self, exportable):
        mtx = exportable['object'].matrix_world.copy()
        mtx.transpose()
        mtx = mtx * axis_conversion(
            from_forward='X',
            to_forward='X',
            from_up='Y',
            to_up='Z'
        ).to_4x4()

        mtx = self.magick_convert(mtx)
        return mtx

    def format_block(self, exportable, is_topmost=False):
        if is_topmost:
            matrix = self.get_topmost_matrix(exportable)
        else:
            matrix = exportable['object'].matrix_basis.copy()
            matrix.transpose()
            matrix = self.magick_convert(matrix)
        if exportable['type'] == 'MESH':
            return self.format_mesh(exportable, matrix)
        else:
            return self.format_node(exportable, matrix)
        return ''

    def export_materials(self):
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
                        break  # only one mesh per armature supported
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

    def format_ints(self, ints):
        return ','.join('%s' % i for i in ints)

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
        ]

        context = {
            'code': constants.MDL_SURFACE,
            'props': self.format_props([['material', surface['material'].name]]),
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
                'data': self.format_ints(surface['indices'])

            },
        )

        return templates.render('SURFACE', context)

    def format_mesh(self, exportable, matrix):

        m = Mesh(exportable['object'])
        surfaces = m.surfaces
        num_kids = len(surfaces)+len(exportable['children'])+1

        bones = ''
        arm = m.get_armature()
        if arm and CONFIG.export_animation:
            arm = m.get_armature()
            bones = self.format_bone(arm.root_bone)
            if bones:
                num_kids += 1

        context = {
            'code': constants.MDL_MESH,
            'num_kids': num_kids,
            'matrix': utils.format_floats_box(matrix),
            'props': self.format_props([['name', m.name]]),
            'surfaces': map(self.format_surface, surfaces),
            'bones': bones,
            'childs': map(self.format_block, exportable['children'])
        }

        return templates.render('MESH', context)

    def format_node(self, exportable, matrix):
        context = {
            'code': constants.MDL_NODE,
            'num_kids': len(exportable['children'])+1,
            'matrix': utils.format_floats_box(matrix),
            'props': self.format_props([['name', exportable['object'].name]]),
            'childs': map(self.format_block, exportable['children'])
        }
        return templates.render('NODE', context)

    def format_bone(self, bone):
        context = {
            'code': constants.MDL_BONE,
            'num_kids': len(bone['children'])+1,
            'bone_id': bone.index,
            'matrix': utils.format_floats_box(bone.matrix_basis),
            'props': self.format_props([['name', bone.name]]),
            'animations': map(self.format_animation_keys, bone.animations),
            'childs': map(self.format_bone, bone.children)
        }
        return templates.render('BONE', context)

    def format_animation_keys(self, data):
        context = {
            'code': constants.MDL_ANIMATIONKEYS,
            'keyframes': map(utils.format_floats_box, data['keyframes']),
            'animation_name': data['name'] if CONFIG.file_version > 1 else ''
        }
        return templates.render('ANIMATIONKEYS', context)