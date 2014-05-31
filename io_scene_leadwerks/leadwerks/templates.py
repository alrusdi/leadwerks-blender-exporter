import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jinja2.zip'))
from jinja2 import Template


sources = {
'VERTEXARRAY':
'''
<block name="VERTEXARRAY" code="{{ code }}">
    <num_kids>0</num_kids>
    <number_of_vertices>{{ number_of_vertices }}</number_of_vertices>
    <elements_count>{{ elements_count }}</elements_count>
    <data_type>
        <value means="{{ data_type.0 }}">{{ data_type.1 }}</value>
    </data_type>
    <variable_type>
        <value means="{{ variable_type.0 }}">{{ variable_type.1 }}</value>
    </variable_type>
    <data>{{ data }}</data>
</block>
''',

'INDICEARRAY':
'''
<block name="INDICEARRAY" code="{{ code }}">
    <num_kids>0</num_kids>
    <number_of_indexes>{{ number_of_indexes }}</number_of_indexes>
    <primitive_type>{{ primitive_type }}</primitive_type>
    <variable_type>
        <value means="{{ variable_type.0 }}">{{ variable_type.1 }}</value>
    </variable_type>
    <data>{{ data }}</data>
</block>
''',

'PROPERTIES':
'''
<block name="PROPERTIES" code="{{ code }}">
    <num_kids>0</num_kids>
    <count>{{ props|length }}</count>
    <properties>
        {% for k, v in props %}
        <value means="{{ k }}">{{ v }}</value>
        {% endfor %}
    </properties>
</block>
''',

'SURFACE':
'''
<block name="SURFACE" code="{{ code }}">
    <num_kids>{{ num_kids }}</num_kids>
    <subblocks>
        {{ props }}
        {{ vertexarray }}
        {{ indice_array }}
    </subblocks>
</block>
''',

'ANIMATIONKEYS':
'''
<block name="ANIMATIONKEYS" code="{{ code }}">
    <num_kids>0</num_kids>
    <number_of_frames>{{ keyframes|length }}</number_of_frames>
    {% if animation_name %}
    <animation_name>{{ animation_name }}</animation_name>
    {% endif %}
    <frames>
        {% for frame in keyframes %}
        <frame>
            {{ frame }}
        </frame>
        {% endfor %}
    </frames>
</block>
''',

'BONE':
'''
<block name="BONE" code="{{ code }}">
    <num_kids>{{ num_kids }}</num_kids>
    <bone_id>{{ bone_id }}</bone_id>
    <matrix>
        {{ matrix }}
    </matrix>
    <subblocks>
        {{ props }}
        {{ animations }}
        {{ childs }}
    </subblocks>
</block>
''',

'NODE':
'''
<block name="NODE" code="{{ code }}">
    <num_kids>{{ num_kids }}</num_kids>
    <matrix>
        {{ matrix }}
    </matrix>
    <subblocks>
        {{ props }}
        {{ childs }}
    </subblocks>
</block>
''',

'MESH':
'''
<block name="MESH" code="{{ code }}">
    <num_kids>{{ num_kids }}</num_kids>
    <matrix>
        {{ matrix }}
    </matrix>
    <subblocks>
        {{ props }}
        {{ surfaces }}
        {{ bones }}
        {{ childs }}
    </subblocks>
</block>
''',

'FILE':
'''
<block name="FILE" code="{{ code }}">
    <num_kids>1</num_kids>
    <version>{{ version }}</version>
    <subblocks>
        {{ childs }}
    </subblocks>
</block>
'''
}

def render(template, context):
    t = Template(sources.get(template))
    return t.render(**context)