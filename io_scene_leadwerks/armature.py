import bpy
from . import utils
from mathutils import Matrix


class Bone(object):
    def __init__(self, blender_data):
        self.index = 0
        self.name = ''
        self.parent = None
        self.children = []
        self.animations = []
        self.matrix_basis = Matrix.Identity(4)

        if blender_data:
            self.blender_data = blender_data
            self.name = blender_data.name

    def setup_matrix(self):
        if self.animations:
            self.matrix_basis = self.animations[0]['keyframes'][0]


class Armature(object):

    def __init__(self, blender_data):
        # @TODO cache parsed armature data in global scope to avoid
        # baking the same animation multiple times
        self.blender_data = blender_data
        self.current_bone_index = 0

        self._name_map = {}
        self._anims_map = {}

        self.parse_animations()

        root_bones = []
        for b in blender_data.data.bones:
            if not b.parent:
                root_bones.append(b)
        self.bones = self.parse_bones(root_bones)

        self.parse_animations()

    def parse_bones(self, bones):
        ret = []
        for b in bones:
            new_bone = Bone(blender_data=b)
            new_bone.index = self.current_bone_index
            self.current_bone_index += 1
            new_bone.animations = self._anims_map.get(b.name, [])
            new_bone.setup_matrix()
            new_bone.children = self.parse_bones(b.children)
            self._name_map[b.name] = new_bone
            ret.append(new_bone)
        return ret

    def __get_mtx(self, pose_bone):
        mtx = pose_bone.matrix.copy()
        if not pose_bone.parent:
            mtx = mtx * utils.mtx4_z90
        else:
            par = pose_bone.parent.matrix.copy()
            mtx = (par * utils.mtx4_z90).inverted() * mtx * utils.mtx4_z90
        mtx.transpose()
        return utils.magick_convert(mtx)

    def parse_animations(self):
         # get current context and then switch to dopesheet temporarily
        current_context = bpy.context.area.type

        bpy.context.area.type = "DOPESHEET_EDITOR"
        bpy.context.space_data.mode = "ACTION"
        for b in self.blender_data.data.bones:
            actions = bpy.data.actions.values()
            pose_bone = self.blender_data.pose.bones[b.name]
            data = []
            for action in actions:
                keyframes = []

                # set active action
                bpy.context.area.spaces.active.action = action

                start_frame = action.frame_range[0]-1
                end_frame = action.frame_range[1]+1

                for frame in range(int(start_frame), int(end_frame), 1):
                    bpy.data.scenes[0].frame_set(frame)
                    keyframes.append(self.__get_mtx(pose_bone))
                data.append({
                    'name': action.name,
                    'keyframes': keyframes
                })
            self._anims_map[b.name] = data

        bpy.data.scenes[0].frame_set(1)
        bpy.context.area.type = current_context

    def get_bone_by_name(self, bone_name):
        return self._name_map.get(bone_name)