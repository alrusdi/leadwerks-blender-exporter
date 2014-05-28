import bpy


class Bone(object):
    def __init__(self, blender_data):
        self.index = 0
        self.name = ''
        self.parent = None
        self.children = []
        self.animations = []

        if blender_data:
            self.name = blender_data.name
            self.parent = blender_data.parent
            self.matrix_basis = blender_data.matrix_local


class Armature(object):

    def __init__(self, armature):
        self.armature = armature
        self.current_bone_index = 0

        self.parse_animations()

        b = Bone(armature.data.bones[0])
        b.index = self.current_bone_index
        b.children = self.get_bones(b)



        self.root_bone = b

        self._name_map = {}
        self._anims_map = {}

    def get_bones(self, parent):
        ret = []
        for b in parent.children:
            new_bone = Bone(blender_data=b)
            new_bone.children = self.get_bones(b)
            self.current_bone_index += 1
            new_bone.index = self.current_bone_index
            new_bone.animations = self._anims_map.get(b.name, [])
            self._name_map[b.name] = new_bone
            ret.append(new_bone)
        return ret

    def parse_animations(self):
         # get current context and then switch to dopesheet temporarily
        current_context = bpy.context.area.type

        bpy.context.area.type = "DOPESHEET_EDITOR"
        bpy.context.space_data.mode = "ACTION"
        for b in self.armature.data.bones:
            actions = bpy.data.actions.values()
            pose_bone = self.armature.pose.bones[b.name]
            data = []
            for action in actions:
                keyframes = []

                # set active action
                bpy.context.area.spaces.active.action = action

                start_frame = action.frame_range[0]
                end_frame = action.frame_range[1]

                for frame in range(int(start_frame), int(end_frame)):
                    bpy.data.scenes[0].frame_set(frame)
                    keyframes.append(pose_bone.matrix_local)
                data.append({
                    'name': action.name,
                    'keyframes': keyframes
                })
            self._anims_map[b.name] = data

        bpy.context.area.type = current_context

    def get_bone_by_name(self, bone_name):
        return self.name_map.get(bone_name)