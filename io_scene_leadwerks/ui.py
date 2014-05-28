# -*- coding: utf-8 -*-
import bpy
from bpy_extras.io_utils import ExportHelper
from .export_leadwerks import LeadwerksExporter

bpy.types.Material.leadwerks_base_shader = bpy.props.StringProperty(name='Shader Name')


class LeadwerksMaterialPanel(bpy.types.Panel):
    '''
    Materials panel addition to allow choose a very Leadwerks specific
    settings (like shader name etc.) per material basis
    '''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_label = "Leadwerks"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}

    @classmethod
    def poll(cls, context):
        return context.material

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(context.material, "leadwerks_base_shader")


class ExportLeadwerks(bpy.types.Operator, ExportHelper):
    bl_idname = "export.mdl"
    bl_label = "Export Leadwerks"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".mdl"
    filter_glob = bpy.props.StringProperty(default="*.mdl", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    export_selection = bpy.props.BoolProperty(
        name="Export only selected objects",
        description="Export selected objects on visible layers",
        default=False,
    )
    export_materials = bpy.props.BoolProperty(
        name='Export materials',
        default=True
    )
    overwrite_textures = bpy.props.BoolProperty(
        name='Overwrite existing textures',
        default=True
    )
    export_animation = bpy.props.BoolProperty(
        name='Overwrite existing textures',
        default=True
    )
    export_specular_color = bpy.props.BoolProperty(
        name='Export specular color',
        default=False
    )
    write_debug_xml = bpy.props.BoolProperty(
        name='Write debug XML',
        default=False
    )
    file_extension = bpy.props.EnumProperty(
        name="File extension",
        items=(
            ('MDL', ".mdl", ""),
            ('GMF', ".gmf", ""),
        ),
        default='MDL',
    )
    file_version = bpy.props.EnumProperty(
        name="File version",
        items=(
            ('1', "1", ""),
            ('2', "2", ""),
        ),
        default='2',
    )

    def execute(self, context):
        from . import export_leadwerks

        kwargs = self.as_keywords()

        kwargs.update({
            'context': context
        })

        return LeadwerksExporter(**kwargs).export()