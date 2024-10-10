__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3 '
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

XAXIS = "X"
YAXIS = "Y"
ZAXIS = "Z"
SPEED = "F"
EXTRUDER = "E"
RELATIVE = True
ABSOLUTE = False

import p2pp.gui as gui
import p2pp.variables as v


class GCodeCommand:
    Command = None
    fullcommand = None
    Command_value = None
    Parameters = {}
    Class = 0
    Comment = None
    Layer = None
    Tool = None
    X = None
    Y = None
    Z = None
    E = None

    def __init__(self, gcode_line):
        self.Command = None
        self.fullcommand = None
        self.Command_value = None
        self.Parameters = {}
        self.Comment = None
        self.Layer = v.parsedlayer
        gcode_line = gcode_line.strip()
        pos = gcode_line.find(";")

        if pos != -1:
            self.Comment = gcode_line[pos + 1:]
            gcode_line = (gcode_line.split(';')[0]).strip()

        fields = gcode_line.split(' ')

        if len(fields[0]) > 0:
            command = fields[0]
            self.Command = command[0]
            self.Command_value = command[1:]
            self.fullcommand = fields[0]
            fields = fields[1:]

            while len(fields) > 0:
                param = fields[0].strip()
                if len(param) > 0:
                    p = param[0]
                    val = param[1:]

                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass

                    self.Parameters[p] = val

                fields = fields[1:]

            self.X = self.get_parameter("X", None)
            self.Y = self.get_parameter("Y", None)
            self.Z = self.get_parameter("Z", None)
            self.E = self.get_parameter("E", None)

    def __str__(self):
        p = ""

        # use the same formatting as prusa to ease file compares (X, Y, Z, E, F)

        sorted_keys = "XYZE"
        if self.is_movement_command():
            for key in sorted_keys:
                if key in self.Parameters:
                    form = ""
                    if key in "XYZ":
                        form = "{}{:0.3f} "
                    if key == "E":
                        form = "{}{:0.5f} "
                    value = self.Parameters[key]
                    if value == None:
                        gui.log_warning("GCode error detected, file might not print correctly")
                        value = ""

                    p = p + form.format(key, value)

        for key in self.Parameters:
            if not self.is_movement_command() or key not in sorted_keys:
                value = self.Parameters[key]
                if value == None:
                    value = ""

                p = p + "{}{} ".format(key, value)

        c = self.fullcommand
        if not c:
            c = ""

        if not self.Comment:
            co = ""
        else:
            co = ";" + self.Comment

        return ("{} {} {}".format(c, p, co)).strip() + "\n"

    def update_parameter(self, parameter, value):
        self.Parameters[parameter] = value
        if parameter == "X":
            self.X = value
        if parameter == "Y":
            self.Y = value
        if parameter == "Z":
            self.Z = value
        if parameter == "E":
            self.E = value

    def remove_parameter(self, parameter):
        if parameter in self.Parameters:
            if self.Comment:
                self.Comment = "[R_{}{}] ".format(parameter, self.Parameters[parameter]) + self.Comment
            else:
                self.Comment = "[R_{}{}] ".format(parameter, self.Parameters[parameter])
            self.Parameters.pop(parameter)

            if parameter == "X":
                self.X = None
            if parameter == "Y":
                self.Y = None
            if parameter == "Z":
                self.Z = None
            if parameter == "E":
                self.E = None


    def move_to_comment(self, text):
        if self.Command:
            self.Comment = "-- P2PP -- removed [{}] - {}".format(text, self)

        self.Command = None
        self.Command_value = None
        self.fullcommand = None
        self.X = None
        self.Y = None
        self.Z = None
        self.E = None
        self.Parameters.clear()

    def has_E(self):
        return self.E is not None

    def has_X(self):
        return self.X is not None

    def has_Y(self):
        return self.Y is not None

    def has_Z(self):
        return self.Z is not None

    def get_comment(self):
        if not self.Comment:
            return ""
        else:
            return self.Comment

    def has_parameter(self, parametername):
        return parametername in self.Parameters

    def get_parameter(self, parm , defaultvalue = 0 ):
        if self.has_parameter(parm):
            return self.Parameters[parm]
        return defaultvalue

    def issue_command(self):
        if self.E is not None and self.is_movement_command():
            v.total_material_extruded += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
            v.material_extruded_per_color[
                v.current_tool] += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
            v.purge_count += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
        v.processed_gcode.append(str(self))
        # v.processed_gcode.append(  "[{}]  {} ".format(v.classes[self.Class],str(self)))

    def issue_command_speed(self, speed):
        s = str(self)
        s = s.replace("%SPEED%", "{:0.0f}".format(speed))
        if self.E is not None and self.is_movement_command():
            v.total_material_extruded += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
            v.material_extruded_per_color[
                v.current_tool] += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction
            v.purge_count += self.E * v.extrusion_multiplier * v.extrusion_multiplier_correction

        v.processed_gcode.append(s)

    def add_comment(self, text):
        if self.Comment:
            self.Comment += text
        else:
            self.Comment = text

    def is_comment(self):
        return self.Command is None and not (self.Comment is None)

    def is_movement_command(self):
        return self.Command == "G" and self.Command_value in ['0', '1', '2', '3', '5', '10', '11']

    def is_z_positioning(self):
        return self.is_movement_command() and self.has_Z()

    def is_xy_positioning(self):
        return self.is_movement_command() and self.has_X() and self.has_Y() and not self.has_E()

    def is_retract_command(self):
        if self.has_E():
            return (self.is_movement_command() and self.E < 0)
        else:
            return self.fullcommand == "G10"


    def is_unretract_command(self):
        if self.has_E():
            return (self.is_movement_command() and self.E > 0 and self.X is None and self.Y is None and self.Z is None)
        else:
            return self.fullcommand == "G11"


def issue_code(s):
    GCodeCommand(s).issue_command()

