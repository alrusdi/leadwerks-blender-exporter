from mathutils import Vector


def __to_floats(tex_coords_as_str):
    fcoords = list(map(float, tex_coords_as_str))
    return fcoords


def update_tangents_and_binormals(verts):

    p0, p1, p2 = [Vector(__to_floats(v['position'])) for v in verts]
    u0, u1, u2 = __to_floats([v['texture_coords'][0] for v in verts])
    v0, v1, v2 = __to_floats([v['texture_coords'][1] for v in verts])

    tangent = None
    binormal = None

    try:
        tangent = ((v2 - v0) * (p1 - p0) - (v1 - v0) * (p2 - p0)) / ((u1 - u0) * (v2 - v0) - (v1 - v0) * (u2 - u0))
    except Exception:
        tangent = None

    try:
        binormal = ((u2 - u0) * (p1 - p0) - (u1 - u0) * (p2 - p0)) / ((v1 - v0) * (u2 - u0) - (u1 - u0) * (v2 - v0))
    except Exception:
        binormal = None

    # Update tangent and binormal
    for v in verts:
        if not 'tangent' in v:
            v['tangent'] = Vector((0,0,0))

        if not 'binormal' in v:
            v['binormal'] = Vector((0,0,0))

        if tangent:
            v['tangent'] = v['tangent'] + tangent
            v['tangent'].normalize()

        if binormal:
            v['binormal'] = v['binormal'] + binormal
            v['binormal'].normalize()
