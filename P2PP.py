#!/usr/bin/pythonw
__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'Beta'

import argparse
import os
import platform
import sys

import p2pp.checkversion as checkversion
import p2pp.gui as gui
import p2pp.mcf as mcf
import p2pp.variables as v
import version as ver

arguments = argparse.ArgumentParser(description='Generates MCF/Omega30 headers from an multi-tool/multi-extruder'
                                                ' GCODE derived from Slic3r.')

arguments.add_argument('-i',
                       '--input-file',
                       required=True)
arguments.add_argument('-d',
                       '--output-file',
                       required=False)
arguments.add_argument('-o',
                       '--splice-offset',
                       type=float,
                       required=False,
                       default=40.00,
                       help='Offset position in the purge tower '
                            'where transition occurs. Similar to transition offset in Chroma.'
                            ' GCODE ;P2PP SPLICEOFFSET=xxx takes precedence over anything set here'
                       )
arguments.add_argument('-n',
                       '--nogui',
                       action='store_true',
                       required=False
                       )

arguments.add_argument('-p',
                       '--printer-profile',
                       required=False,
                       default='',
                       help='A unique ID linked to a printer configuration'
                            ' profile in the Palette 2 hardware.'
                       )
arguments.add_argument('-s',
                       '--silent',
                       default=False,
                       help='Omits Summary page after processing from being printed to STDOUT'
                       )

arguments.add_argument('-v',
                       '--versioncheck',
                       default=False,
                       help='Check and reports new online versions of P2PP [-v 0|1]'
                       )

arguments.add_argument('-w',
                       '--wait',
                       required=False,
                       help='Wait for the user to press enter after processing the file. -w [0|1]'
                       )


def main(args):
    if not args['nogui']:
        v.gui = True
    else:
        v.gui = False

    v.filename = args['input_file']

    if args["versioncheck"] == "1":
        v.versioncheck = True

    if args['wait'] == "1":
        v.consolewait = True

    mcf.generate(v.filename,
                 args['output_file'],
                 args['printer_profile'],
                 args['splice_offset'],
                 args['silent']
                 )



if __name__ == "__main__":
    v.version = ver.Version

    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "-i"):
        platformD = platform.system()

        MASTER_VERSION = checkversion.get_version(checkversion.MASTER)
        DEV_VERSION = checkversion.get_version(checkversion.DEV)

        if MASTER_VERSION and DEV_VERSION:

            if v.version > MASTER_VERSION:
                if v.version < DEV_VERSION:
                    v.version += " (New dev version {} available)".format(DEV_VERSION)
                    color = "red"
                else:
                    v.version += " (Dev version up to date)"
                    color = "green"
            else:
                if v.version < MASTER_VERSION:
                    v.version += " (New stable version {} available)".format(MASTER_VERSION)
                    color = "red"
                else:
                    v.version += " (Version up to date)"
                    color = "green"
            gui.create_logitem(v.version, color , True)

        gui.configinfo()
        gui.create_emptyline()
        gui.create_logitem("Line to be used in PrusaSlicer [Print Settings][Output Options][Post Processing Script]",
                           "blue")
        gui.create_emptyline()

        if platformD == 'Darwin':
            gui.create_logitem("{}/p2pp.command".format(os.path.dirname(sys.argv[0])), "red")
        elif platformD == 'Windows':
            gui.create_logitem("{}\\p2pp.bat".format(os.path.dirname(sys.argv[0])), "red")

        gui.create_emptyline()
        gui.create_logitem("This requires ADVANCED/EXPERT settings to be enabled", "blue")
        gui.create_emptyline()
        gui.create_emptyline()
        gui.create_logitem("Don't forget to complete the remaining Prusaslicer Configuration", "blue")
        gui.create_logitem("More info on: https://github.com/tomvandeneede/p2pp", "blue")
        gui.close_button_enable()
    else:
        gui.create_logitem("Python Version Information: "+platform.python_version() ,
                           "blue")
        main(vars(arguments.parse_args()))
