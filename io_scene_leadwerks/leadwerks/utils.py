import math
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

class Scale():
    x = 1.0
    y = 1.0
    z = 1.0

    def __init__(self, vec):
        self.x = vec[1]
        self.y = vec[2]
        self.z = vec[0]

class Rot():
    x = 1.0
    y = 1.0
    z = 1.0
    w = 1.0

    def __init__(self, vec):
        self.x = vec[1]
        self.y = vec[0]
        self.z = vec[2]
        self.w = -vec[3]

def convert_to_lw_matrix(mtx):
    mtx = mtx * Matrix.Rotation(1.5707963267948966*2, 4, 'Z')
    pos, rot, rscale = mtx.decompose()
    rrot = mtx.to_quaternion()

    scale = Scale(rscale)
    rot = Rot(rrot)

    xx = rot.x * rot.x
    yy = rot.y * rot.y
    zz = rot.z * rot.z
    xy = rot.x * rot.y
    xz = rot.x * rot.z
    yz = rot.y * rot.z
    wx = rot.w * rot.x
    wy = rot.w * rot.y
    wz = rot.w * rot.z

    ret = []

    ret.append([
        (1.0 - 2.0 * ( yy + zz )) * scale.x,
        (2.0 * ( xy - wz )) * scale.x,
        (2.0 * ( xz + wy )) * scale.x,
        0.0,
    ])

    ret.append([
        (2.0 * ( xy + wz )) * scale.y,
        (1.0 - 2.0 * ( xx + zz )) * scale.y,
        (2.0 * ( yz - wx )) * scale.y,
        0.0,
    ])

    ret.append([
        (2.0 * ( xz - wy )) * scale.z,
        (2.0 * ( yz + wx )) * scale.z,
        (1.0 - 2.0 * ( xx + yy )) * scale.z,
        0.0,
    ])

    ret.append([-pos[1], pos[2], pos[0], 1.0])

    return Matrix(ret)

