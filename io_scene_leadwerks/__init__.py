# -*- coding: utf-8 -*-

import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

bl_info = {
    "name": "Leadwerks game engine formats",
    "author": "Josh Klint",
    "blender": (2, 70, 0),
    "location": "File > Import-Export",
    "description": "Export Leadwerks meshes, UV's, vertex colors, materials, "
                   "textures",
    "warning": "",
    "tracker_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}


if "bpy" in locals():
    import imp
    imp.reload(leadwerks.ui)
else:
    import bpy
    from .leadwerks.ui import *


def menu_func_export(self, context):
    self.layout.operator("export.mdl", text="Leadwerks (.mdl, .tex)")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
