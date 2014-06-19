import bpy
import bmesh
from mathutils import Matrix, Vector, Euler


def mget(inp_dict, inp_keys):
    ret = []
    for k in inp_keys:
        ret.append(inp_dict.get(k))
    return ret


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
mtx4_z180 = Matrix.Rotation(1.5707963267948966*2, 4, 'Z')
mtx_mesh = Matrix.Rotation(-1.5707963267948966, 4, 'Y') * Matrix.Rotation(1.5707963267948966, 4, 'X')
mtx_node = Matrix.Rotation(1.5707963267948966, 4, 'Z')

mtx4_z90 = Matrix.Rotation(1.5707963267948966, 4, 'Z')

def triangulate_mesh(meshable_obj):
    is_editmode = (meshable_obj.mode == 'EDIT')
    if is_editmode:
        bpy.ops.object.editmode_toggle()

    bm = bmesh.new()
    mesh = meshable_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')

    bm.from_mesh(mesh)

    #bm.from_object(meshable_obj, bpy.context.scene, deform=True, render=False)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    mesh.update(calc_tessface=True, calc_edges=True)

    if is_editmode:
        bpy.ops.object.editmode_toggle()
    return mesh

def convert_to_lw_matrix(mtx):
    pos, rot, scale = mtx.decompose()

    mat_trans = Matrix.Translation(Vector((pos[1], pos[2], pos[0]))).to_4x4()
    eul = rot.to_euler('XYZ')

    mat_rot = Euler((-eul[1], eul[2], eul[0]), 'XYZ').to_matrix().to_4x4()

    mat_scale = Matrix.Identity(4)
    mat_scale[0][0] = scale[1]
    mat_scale[1][1] = scale[2]
    mat_scale[2][2] = scale[0]

    mtx = Matrix.Identity(4) * mat_scale
    mtx = mtx * mat_rot
    mtx = mtx * mat_trans

    mtx[3][0] = -mtx[0][3]
    mtx[3][1] = mtx[1][3]
    mtx[3][2] = mtx[2][3]

    mtx[0][3] = 0.0
    mtx[1][3] = 0.0
    mtx[2][3] = 0.0

    return mtx
