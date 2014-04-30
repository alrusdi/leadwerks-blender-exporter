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

bl_info = {
    "name": "Leadwerks game engine formats",
    "author": "Josh Klint",
    "blender": (2, 70, 0),
    "location": "File > Import-Export",
    "description": "Export Leadwerks meshes, UV's, vertex colors, materials, "
                   "textures, physics collision mesh",
    "warning": "",
    "tracker_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}


if "bpy" in locals():
    import imp
    if "export_leadwerks" in locals():
        imp.reload(export_leadwerks)

import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       FloatProperty,
                       EnumProperty,
                       )

from bpy_extras.io_utils import ExportHelper

class ExportLeadwerks(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.mdl"
    bl_label = "Export Leadwerks"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".mdl"
    filter_glob = StringProperty(default="*.mdl", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    use_selection = BoolProperty(
            name="Selected Objects",
            description="Export selected objects on visible layers",
            default=False,
            )
    global_scale = FloatProperty(
            name="Scale",
            description=("Scale all data"),
            min=0.001, max=1000.0,
            soft_min=0.01, soft_max=1000.0,
            default=1.0,
            )
    object_types = EnumProperty(
            name="Object Types",
            options={'ENUM_FLAG'},
            items=(('EMPTY', "Empty", ""),
                   ('ARMATURE', "Armature", ""),
                   ('MESH', "Mesh", ""),
                   ),
            default={'EMPTY', 'ARMATURE', 'MESH'},
            )

    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply modifiers to mesh objects",
            default=True,
            )
    use_mesh_edges = BoolProperty(
            name="Include Loose Edges",
            default=False,
            )
    use_custom_properties = BoolProperty(
            name="Custom Properties",
            description="Export custom properties",
            default=False,
            )
    use_armature_deform_only = BoolProperty(
            name="Only Deform Bones",
            description="Only write deforming bones",
            default=False,
            )
    use_anim = BoolProperty(
            name="Include Animation",
            description="Export keyframe animation",
            default=True,
            )
    use_anim_action_all = BoolProperty(
            name="All Actions",
            description=("Export all actions for armatures or just the "
                         "currently selected action"),
            default=True,
            )
    use_anim_optimize = BoolProperty(
            name="Optimize Keyframes",
            description="Remove double keyframes",
            default=True,
            )
    anim_optimize_precision = FloatProperty(
            name="Precision",
            description=("Tolerance for comparing double keyframes "
                        "(higher for greater accuracy)"),
            min=0.0, max=20.0,  # from 10^2 to 10^-18 frames precision.
            soft_min=1.0, soft_max=16.0,
            default=6.0,  # default: 10^-4 frames.
            )

    def execute(self, context):
        raise Exception("Not implemented yet, sorry")
        from . import export_leadwerks
        # @TODO Implement the export procedure


def menu_func_export(self, context):
    self.layout.operator(ExportLeadwerks.bl_idname, text="Leadwerks (.mdl, .tex, .phy)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
