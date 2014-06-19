import bpy
from . import utils
from .config import CONFIG
from mathutils import Matrix


class Bone(object):
    """
    Helper class to store Bone hierarhy data, animations and generate
    Leadwerks compatible indexes for them
    """
    def __init__(self, blender_data=None):
        self.index = 0
        self.name = ''
        self.parent = None
        self.children = []
        self.animations = []
        self.matrix_basis = Matrix((
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ))

        if blender_data:
            self.blender_data = blender_data
            self.name = blender_data.name

    def setup_matrix(self):
        if self.animations:
            self.matrix_basis = self.animations[0]['keyframes'][0]


class Armature(object):
    """
    Helper class to retrieve Skeletons and from blender
    and bake bone animations
    """

    def __init__(self, blender_data, target_mesh):
        # @TODO cache parsed armature data in global scope to avoid baking the same animation multiple times
        self.blender_data = blender_data
        self.current_bone_index = 1

        self._name_map = {}
        self._anims_map = {}
        self.target_mesh = target_mesh
        # Baking animations
        self.parse_animations()

        # Building bones hierarchy

        second_level_bones = []
        self.__needs_export = []
        for b in blender_data.data.bones:
            if not b.parent:
                second_level_bones.append(b)
            if b.use_deform and not b.name in self.__needs_export:
                self.__needs_export.append(b.name)
                for pb in b.parent_recursive:
                    self.__needs_export.append(pb.name)
        topmost_bone = Bone()
        topmost_bone.name = blender_data.name
        anim_tpl = list(self._anims_map.values())[0]
        anims = []
        for a in anim_tpl:
            anims.append({
                'name': a['name'],
                'keyframes': [topmost_bone.matrix_basis] * len(a['keyframes'])
            })
        topmost_bone.animations = anims
        topmost_bone.children = self.parse_bones(second_level_bones)
        self.bones = [topmost_bone]

    def __fake_keyframe(self):
        return Matrix.Identity(4)

    def parse_bones(self, bones):
        ret = []
        for b in bones:
            if not b.name in self.__needs_export:
                continue
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
        """
        Conversion of bone matrix to Leadwerks order
        taken from fbx exporter
        """
        mtx = pose_bone.matrix.copy()
        if not pose_bone.parent:
            mtx = mtx * utils.mtx4_z90
        else:
            par = pose_bone.parent.matrix.copy()
            mtx = (par * utils.mtx4_z90).inverted() * mtx * utils.mtx4_z90
        mtx.transpose()
        mtx = utils.magick_convert(mtx)
        return mtx

    def parse_animations(self):
         # get current context and then switch to dopesheet temporarily
        current_context = bpy.context.area.type
        bpy.context.area.type = "DOPESHEET_EDITOR"
        bpy.context.space_data.mode = "ACTION"

        # For each action retrieving bone matrixes

        actions = self.__get_needed_actions()
        for idx, action in enumerate(actions):
            if not action:
                break
            baking_step = CONFIG.anim_baking_step
            # set active action
            bpy.context.area.spaces.active.action = action

            start_frame = action.frame_range[0]-baking_step
            end_frame = action.frame_range[1]+baking_step

            for frame in range(int(start_frame), int(end_frame), baking_step):
                bpy.context.scene.frame_set(frame)

                for b in self.blender_data.data.bones:
                    pose_bone = self.blender_data.pose.bones[b.name]
                    mtx = self.__get_mtx(pose_bone)

                    if not b.name in self._anims_map:
                        self._anims_map[b.name] = []

                    if len(self._anims_map[b.name]) == idx:
                        self._anims_map[b.name].append({
                            'name': action.name,
                            'keyframes': []
                        })

                    self._anims_map[b.name][idx]['keyframes'].append(mtx)

        bpy.data.scenes[0].frame_set(1)
        bpy.context.area.type = current_context

    def __get_needed_actions(self):
        all_actions = bpy.data.actions.values()
        if not all_actions:
            return []

        if CONFIG.export_all_actions:
            return all_actions

        active_action = bpy.context.area.spaces.active.action
        return [active_action] if active_action else [all_actions[0]]

    def get_bone_by_name(self, bone_name):
        """
        Used to find needed Bone by VertexGroup name to assign bone weights
        to vertice
        """
        return self._name_map.get(bone_name)