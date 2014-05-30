import bpy
import bmesh
from mathutils import Matrix


def to_str_list(floats_list):
    return ['%.9f' % f for f in floats_list]


def format_floats_box(floats):
    """
    Formats two dimensional array of floats (like matrix) to
    string with comma separated formated values like '0.1,0.2,0.3'
    """
    ret = ''
    flat_list = []
    for v in floats:
        flat_list.extend([f for f in v])
    ret += ','.join(to_str_list(flat_list))
    return ret


def join_map(fn, data):
    d = list(map(fn, data))
    return ''.join(d)


def magick_convert(matrix):
        inv = [[0, 2], [1, 2], [2, 0], [2, 1], [3, 2]]
        mtx = list(matrix)
        for i in inv:
            v = -mtx[i[0]][i[1]]
            mtx[i[0]][i[1]] = v
        matrix = Matrix(mtx)
        return matrix

# 1.5707963267948966 = PI/2
mtx4_z90 = Matrix.Rotation(1.5707963267948966, 4, 'Z')

def triangulate_mesh(meshable_obj):
    bm = bmesh.new()

    mesh = meshable_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')

    bm.from_object(meshable_obj, bpy.context.scene, deform=True, render=False)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    mesh.update(calc_tessface=True, calc_edges=True)
    return mesh
