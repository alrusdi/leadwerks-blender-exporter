# -*- coding: utf-8 -*-
"""
Tool for dumping .mdl files into custom XML format for debugging purposes.
It also can compile .xml to .mdl again.
Usage:
python3 -m xml_tool whatever.mdl whatever.mod.xml
python3 -m xml_tool whatever.mod.xml whatever.new.mdl
"""
import sys
import os
from xml_tool.compiler import MdlCompiler
from xml_tool.dumper import MdlDumper

if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        print('Pass a .mdl file as parameter please')
        sys.exit(1)
    path = args[1]

    if not os.access(path, os.R_OK):
        print('Cannot access file %s' % path)
        sys.exit(1)

    if path.endswith('.xml'):
        if len(args) > 2:
            output_path = args[2]
        else:
            output_path = path[0:-4]
            if not output_path.endswith('.mdl'):
                output_path = '%s.mdl' % output_path

        compiler = MdlCompiler(path, output_path)
        compiler.compile()
    elif path.endswith('.mdl'):
        dumper = MdlDumper(path)
        dumper.read()

        if len(args) > 2:
            output = args[2]
        else:
            output = '%s.xml' % path

        with open(output, 'w') as f:
            f.write(dumper.as_xml())
    else:
        print('Please provide .xml or .mdl file as argument')
        sys.exit(1)
