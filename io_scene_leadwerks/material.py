"""
Classes representing Leadwerks materials
"""
import os

class Texture(object):
    name = ''
    blender_data = None
    filename = ''
    slot = 'diffuse'
    needs_write=False

    def __init__(self, blender_texture_slot):
        self.blender_data = blender_texture_slot
        props_to_slot = [
            ('use_map_color_diffuse', 'diffuse'),
            ('use_map_normal', 'normal'),
            ('use_map_color_spec', 'specular'),
            ('use_map_color_displacement', 'displacement'),
        ]
        for p, slot in props_to_slot:
            if getattr(self.blender_data, p):
                self.slot = slot
                break

        self.name = blender_texture_slot.name

    def save(self, dir_name):

        save_path = os.path.abspath(
            os.path.join(dir_name, '%s.png' % self.name)
        )
        if not os.path.exists(save_path):
            img = self.blender_data.texture.image
            img.save_render(save_path)


class Material(object):
    is_animated = False
    use_specular = True
    name = 'default'
    blender_data = None
    blendmode=0
    castshadows=1
    zsort=0
    cullbackfaces=1
    depthtest=1
    depthmask=1
    alwaysuseshader=0
    drawmode=-1
    diffuse = '1.0,1.0,1.0,1.0'
    specular = '0.0,0.0,0.0,1.0'
    shader = ''
    textures = []

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if not self.blender_data:
            return

        self.name = self.blender_data.name

        for i, ts in enumerate(self.blender_data.texture_slots):
            if not ts or ts.texture.type != 'IMAGE':
                continue
            self.textures.append(Texture(ts))

        self.diffuse = '%s,1.0' % ','.join(map('str', self.blender_data.diffuse_color))
        # self.specular = '%s,1.0' % ','.join(map('str', self.blender_data.specular_color))


    def save(self, base_dir, save_textures=True):
        """
        Saves material to a .mat file in given directory
        overwrites existing
        """
        direct_props = [
            'blendmode',
            'castshadows',
            'zsort',
            'cullbackfaces',
            'depthtest',
            'depthmask',
            'alwaysuseshader',
            'drawmode',
            'diffuse',
            'specular'
        ]

        out = ['//Leadwerks Material File']

        for prop in direct_props:
            out.append('%s=%s' % (prop, getattr(self, prop)))


        if self.shader:
            out.append('shader=%s' % self.shader)
        else:
            shader_name = self.guess_shader_name()
            if shader_name:
                out.append(self.make_shader_path(shader_name))

        if self.textures:
            still_used = []
            order = ['diffuse', 'normal', 'specular', 'displacement']
            for idx, texture_slot in enumerate(order):
                tx = self.find_texture_by_slot(texture_slot)
                if tx:
                    out.append('texture%s=%s.name' % (idx, tx.name))
                    still_used.append(tx.name)

            next_idx = 4
            for tx in self.textures:
                if not tx.name in still_used:
                    out.append('texture%s=%s.name' % (next_idx, tx.name))
                    next_idx +=1
                    if save_textures:
                        tx.save(base_dir)
                    if next_idx > 8:
                        break


        path = os.path.abspath(os.path.join(base_dir, '%s.mat' % self.name))

        with open(path, 'w') as f:
            f.write(out)

    def make_shader_path(self, shader_name):
        base_path = 'shaders/model/'
        if self.is_animated:
            base_path = 'animated/%s/' % base_path
        return '%s.shader' % shader_name


    def guess_shader_name(self):
        if not self.textures or not self.find_texture_by_slot('diffuse'):
            return ''

        shader_name = 'diffuse'

        if self.find_texture_by_slot('normal'):
            shader_name = '%s+normal' % shader_name
        else:
            return shader_name

        if self.find_texture_by_slot('specular'):
            shader_name = '%s+specular' % shader_name
        else:
            return shader_name

        if self.is_animated:
            return shader_name

        if self.find_texture_by_slot('displacement'):
            shader_name = '%s+displacement' % shader_name

        return shader_name

    def find_texture_by_slot(self, slot_name):
        for t in self.textures:
            if t.slot == slot_name:
                return t

