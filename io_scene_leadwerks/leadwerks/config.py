# <pep8 compliant>


class CONFIG(object):
    """
    This values are managed by user from GUI
    """
    file_version = 2
    file_extension = '.mdl'
    export_selection = False
    export_animation = True
    export_materials = True
    overwrite_textures = False
    export_specular_color = False
    write_debug_xml = True
    anim_baking_step = 5
    export_all_actions = False


    @classmethod
    def update(cls, options):
        for k, v in cls.values().items():
            default = v
            val = options.get(k, default)
            setattr(cls, k, val)
        if cls.file_extension == '.gmf':
            cls.file_version = 1

    @classmethod
    def values(cls):
        vals = {}
        types = [bool, str, int, float, dict]
        for k, v in cls.__dict__.items():
            if k.startswith('_') or type(v) not in types:
                continue
            vals[k] = v
        return vals
