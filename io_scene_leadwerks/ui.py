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

    use_selection = bpy.props.BoolProperty(
        name="Selected Objects",
        description="Export selected objects on visible layers",
        default=False,
    )
    object_types = bpy.props.EnumProperty(
        name="Object Types",
        options={'ENUM_FLAG'},
        items=(('EMPTY', "Empty", ""),
               ('MATERIAL', "Material", ""),
               ('ARMATURE', "Armature", ""),
               ('MESH', "Mesh", ""),
               ),
        default={'EMPTY', 'MATERIAL', 'ARMATURE', 'MESH'},
    )

    use_mesh_modifiers = bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects",
        default=True,
    )

    sdk_path = bpy.props.StringProperty(
        name="SDK path",
        description="SDK root path",
        default=""
    )

    def execute(self, context):
        from . import export_leadwerks

        kwargs = self.as_keywords()

        kwargs.update({
            'context': context
        })

        return LeadwerksExporter(**kwargs).export()