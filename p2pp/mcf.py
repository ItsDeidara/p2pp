__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import io
import os
import re
import time

import p2pp.gcode as gcode
import p2pp.gui as gui
import p2pp.p2_m4c as m4c
import p2pp.parameters as parameters
import p2pp.pings as pings
import p2pp.purgetower as purgetower
import p2pp.variables as v
from p2pp.gcodeparser import parse_slic3r_config
from p2pp.omega import header_generate_omega, algorithm_process_material_configuration
from p2pp.sidewipe import create_side_wipe, create_sidewipe_BigBrain3D

layer_regex = re.compile("\s*;\s*(LAYER|LAYERHEIGHT)\s+(\d+(\.\d+)?)\s*")


def remove_previous_move_in_tower():
    idx = len(v.processed_gcode) - 10

    while idx < len(v.processed_gcode):
        line = v.processed_gcode[idx]
        tmp = gcode.GCodeCommand(line)
        if tmp.X and tmp.Y:
            if coordinate_in_tower(tmp.X, tmp.Y):
                if tmp.is_movement_command() and tmp.has_E():
                    v.total_material_extruded -= tmp.E
                    v.material_extruded_per_color[v.current_tool] -= tmp.E
                tmp.move_to_comment("tower skipped")
                v.processed_gcode[idx] = tmp.__str__()
        idx = idx + 1


def optimize_tower_skip(skipmax, layersize):

    skipped = 0.0
    skipped_num = 0
    if v.side_wipe or v.bigbrain3d_purge_enabled:
        base = -1
    else:
        base = 0

    for idx in range(len(v.skippable_layer) - 1, base, -1):
        if skipped + 0.005 >= skipmax:
            v.skippable_layer[idx] = False
        elif v.skippable_layer[idx]:
            skipped = skipped + layersize
            skipped_num += 1

    if v.tower_delta:
        if skipped > 0:
            gui.log_warning(
                "Warning: Purge Tower delta in effect: {} Layers or {:-6.2f}mm".format(skipped_num, skipped))
        else:
            gui.create_logitem("Tower Purge Delta could not be applied to this print")
            for idx in range(len(v.skippable_layer)):
                v.skippable_layer[idx] = False
            v.tower_delta = False

    if not v.side_wipe and not v.bigbrain3d_purge_enabled:
        v.skippable_layer[0] = False


def convert_to_absolute():
    absolute = -9999

    for i in range(len(v.processed_gcode)):

        if absolute > 3000.0:
            v.processed_gcode.insert(i, "G92 E0.000    ;Extruder counter reset ")
            absolute = 0.00

        line = gcode.GCodeCommand(v.processed_gcode[i])

        if line.is_movement_command():
            if line.has_E():

                # if there is no filament reset code, make sure one is inserted before first extrusion
                # this should not be needed
                if absolute == -9999:
                    v.processed_gcode.insert(i, "G92 E0.00")
                    absolute = 0.0
                    i += 1

                absolute += line.E
                line.update_parameter("E", absolute)
                v.processed_gcode[i] = line.__str__()

        if line.fullcommand == "M83":
            v.processed_gcode[i] = "M82\n"

        if line.fullcommand == "G92":
            absolute = line.E


# ################### GCODE PROCESSING ###########################
def gcode_process_toolchange(new_tool, location, current_layer):
    # some commands are generated at the end to unload filament,
    # they appear as a reload of current filament - messing up things
    if new_tool == v.current_tool:
        return

    location += v.splice_offset

    if new_tool == -1:
        location += v.extra_runout_filament
        v.material_extruded_per_color[v.current_tool] += v.extra_runout_filament
        v.total_material_extruded += v.extra_runout_filament
    else:
        v.palette_inputs_used[new_tool] = True

    length = location - v.previous_toolchange_location

    if v.current_tool != -1:

        v.splice_extruder_position.append(location)
        v.splice_length.append(length)
        v.splice_used_tool.append(v.current_tool)

        v.autoadded_purge = 0

        if len(v.splice_extruder_position) == 1:
            if v.splice_length[0] < v.min_start_splice_length:
                if v.autoaddsplice and (v.full_purge_reduction or v.side_wipe):
                    v.autoadded_purge = v.min_start_splice_length - length
                else:
                    gui.log_warning("Warning : Short first splice (<{}mm) Length:{:-3.2f}".format(length,
                                                                                              v.min_start_splice_length))

                    filamentshortage = v.min_start_splice_length - v.splice_length[0]
                    v.filament_short[new_tool] = max(v.filament_short[new_tool], filamentshortage)
        else:
            if v.splice_length[-1] < v.min_splice_length:
                if v.autoaddsplice and (v.full_purge_reduction or v.side_wipe):
                    v.autoadded_purge = v.min_splice_length - v.splice_length[-1]
                else:
                    gui.log_warning("Warning: Short splice (<{}mm) Length:{:-3.2f} Layer:{} Input:{}".
                                    format(v.min_splice_length, length, current_layer, v.current_tool + 1))
                    filamentshortage = v.min_splice_length - v.splice_length[-1]
                    v.filament_short[new_tool] = max(v.filament_short[new_tool], filamentshortage)

        v.side_wipe_length += v.autoadded_purge
        v.splice_extruder_position[-1] += v.autoadded_purge
        v.splice_length[-1] += v.autoadded_purge

        v.previous_toolchange_location = v.splice_extruder_position[-1]

    v.previous_tool = v.current_tool
    v.current_tool = new_tool


def inrange(number, low, high):
    if number is None:
        return True
    return low <= number <= high


def y_on_bed(y):
    return inrange(y, v.bed_origin_y, v.bed_origin_y + v.bed_size_y)


def x_on_bed(x):
    return inrange(x, v.bed_origin_x, v.bed_origin_x + v.bed_size_x)


def coordinate_on_bed(x, y):
    return x_on_bed(x) and y_on_bed(y)


def x_coordinate_in_tower(x):
    if x == None:
        return False
    return inrange(x, v.wipe_tower_info['minx'], v.wipe_tower_info['maxx'])


def y_coordinate_in_tower(y):
    if y == None:
        return False
    return inrange(y, v.wipe_tower_info['miny'], v.wipe_tower_info['maxy'])


def coordinate_in_tower(x, y):
    return x_coordinate_in_tower(x) and y_coordinate_in_tower(y)

def entertower(layer_hght):
    purgeheight = layer_hght - v.cur_tower_z_delta
    if v.current_position_z != purgeheight:
        v.max_tower_delta = max(v.cur_tower_z_delta, v.max_tower_delta)
        gcode.issue_code(";------------------------------\n")
        gcode.issue_code(";  P2PP DELTA ENTER\n")
        gcode.issue_code(
            ";  Current Z-Height = {:.2f};  Tower height = {:.2f}; delta = {:.2f} [ {} ]".format(v.current_position_z,
                                                                                          purgeheight,
                                                                                          v.current_position_z - purgeheight, layer_hght))
        if v.retraction >= 0:
            purgetower.retract(v.current_tool)
        gcode.issue_code(
            "G1 Z{:.2f} F10810\n".format(purgeheight))

        # purgetower.unretract(v.current_tool)

        gcode.issue_code(";------------------------------\n")
        if purgeheight <= 0.21:
            gcode.issue_code("G1 F{}\n".format(min(1200, v.wipe_feedrate)))
        else:
            gcode.issue_code("G1 F{}\n".format(v.wipe_feedrate))


def leavetower():
    gcode.issue_code(";------------------------------\n")
    gcode.issue_code(";  P2PP DELTA LEAVE\n")
    gcode.issue_code(
        ";  Returning to Current Z-Height = {:.2f}; ".format(v.current_position_z))
    gcode.issue_code(
        "G1 Z{:.2f} F10810\n".format(v.current_position_z))
    gcode.issue_code(";------------------------------\n")

CLS_UNDEFINED = 0
CLS_NORMAL = 1
CLS_TOOL_START = 2
CLS_TOOL_UNLOAD = 3
CLS_TOOL_PURGE = 4
CLS_EMPTY = 5
CLS_BRIM = 7
CLS_BRIM_END = 8
CLS_ENDGRID = 9
CLS_COMMENT = 10
CLS_ENDPURGE = 11
CLS_TONORMAL = 99
CLS_TOOLCOMMAND = 12

SPEC_INTOWER = 16




def update_class(gcode_line):

    v.previous_block_classification = v.block_classification

    if gcode_line[0] == "T":
        v.block_classification = CLS_TOOL_PURGE

    if gcode_line.startswith("; CP"):
        if "TOOLCHANGE START" in gcode_line:
            v.block_classification = CLS_TOOL_START

        if "TOOLCHANGE UNLOAD" in gcode_line:
            v.block_classification = CLS_TOOL_UNLOAD

        if "TOOLCHANGE WIPE" in gcode_line:
            v.block_classification = CLS_TOOL_PURGE

        if "TOOLCHANGE END" in gcode_line:
            if v.previous_block_classification == CLS_TOOL_UNLOAD:
                v.block_classification = CLS_NORMAL
            else:
                v.block_classification = CLS_TONORMAL

        if "WIPE TOWER FIRST LAYER BRIM START" in gcode_line:
            v.block_classification = CLS_BRIM
            v.tower_measure = True

        if "WIPE TOWER FIRST LAYER BRIM END" in gcode_line:
            v.tower_measure = False
            v.block_classification = CLS_BRIM_END


        if "EMPTY GRID START" in gcode_line:
            v.block_classification = CLS_EMPTY

        if "EMPTY GRID END" in gcode_line:
            v.block_classification = CLS_ENDGRID

        if v.block_classification == CLS_TONORMAL and v.previous_block_classification == CLS_TOOL_PURGE:
            v.block_classification = CLS_ENDPURGE

    return


def backpass(currentclass):

    if v.wipe_remove_sparse_layers:
        return

    idx = len(v.parsed_gcode) - 2

    end_search = idx - 10
    while idx > end_search:
        if v.parsed_gcode[idx].Class != CLS_NORMAL:
            return

        v.parsed_gcode[idx].Class = currentclass

        if v.parsed_gcode[idx].is_unretract_command():
            if (v.parsed_gcode[idx].fullcommand == "G11"):
                v.retraction = 0
            else:
                v.retraction -= v.parsed_gcode[idx].E

        if v.parsed_gcode[idx].is_xy_positioning():
            return

        idx = idx - 1


def calculate_tower(x, y):
    if x is not None:
        v.wipe_tower_info['minx'] = min(v.wipe_tower_info['minx'], x - 4 * v.extrusion_width)
        v.wipe_tower_info['maxx'] = max(v.wipe_tower_info['maxx'], x + 4 * v.extrusion_width)
    if y is not None:
        v.wipe_tower_info['miny'] = min(v.wipe_tower_info['miny'], y - 8 * v.extrusion_width)
        v.wipe_tower_info['maxy'] = max(v.wipe_tower_info['maxy'], y + 8 * v.extrusion_width)


def create_tower_gcode():
    # generate a purge tower alternative
    _x = v.wipe_tower_info['minx']
    _y = v.wipe_tower_info['miny']
    _w = v.wipe_tower_info['maxx'] - v.wipe_tower_info['minx']
    _h = v.wipe_tower_info['maxy'] - v.wipe_tower_info['miny']

    purgetower.purge_create_layers(_x, _y, _w, _h)
    # generate og items for the new purge tower
    gui.create_logitem(
        " Purge Tower :Loc X{:.2f} Y{:.2f}  W{:.2f} H{:.2f}".format(_x, _y, _w, _h))
    gui.create_logitem(
        " Layer Length Solid={:.2f}mm   Sparse={:.2f}mm".format(purgetower.sequence_length_solid,
                                                                purgetower.sequence_length_empty))


def parse_gcode():
    cur_tool = 0
    toolchange = 0
    emptygrid = 0

    v.block_classification = CLS_NORMAL
    v.previous_block_classification = CLS_NORMAL
    total_line_count = len(v.input_gcode)

    index = 0
    for line in v.input_gcode:

        gui.progress_string(4 + 46 * index // total_line_count)


        if line.startswith(';'):

            m = v.regex_p2pp.match(line)
            if m:
                parameters.check_config_parameters(m.group(1), m.group(2))


            if line.startswith(";P2PP MATERIAL_"):
                algorithm_process_material_configuration(line[15:])

            layer = -1
            # if not supports are printed or layers are synced, there is no need to look at the layerheight,
            # otherwise look at the layerheight to determine the layer progress

            lm = layer_regex.match(line)
            if lm is not None:
                llm = len(lm.group(1))
                lmv = float(lm.group(2))
                if v.synced_support or not v.prints_support:
                    if llm == 5:  # LAYER
                        layer = int(lmv)
                else:
                    if llm == 11:  # LAYERHEIGHT
                        layer = int((lmv - v.first_layer_height + 0.005) / v.layer_height)

            if layer == v.parsedlayer:
                layer = -1

            if layer >= 0:
                v.parsedlayer = layer

            if layer > 0:
                v.skippable_layer.append((emptygrid > 0) and (toolchange == 0))
                toolchange = 0
                emptygrid = 0

            update_class(line)

        code = gcode.GCodeCommand(line)

        if code.Command == 'T':
            cur_tool = int(code.Command_value)
            v.m4c_toolchanges.append(cur_tool)
            v.m4c_toolchange_source_positions.append(len(v.parsed_gcode))


        code.Tool = cur_tool
        code.Class = v.block_classification


        # code.add_comment("[{}]".format(v.classes[v.block_classification]))
        v.parsed_gcode.append(code)

        if v.block_classification != v.previous_block_classification:

            if v.block_classification == CLS_TOOL_START:
                toolchange += 1

            if v.block_classification == CLS_EMPTY:
                emptygrid += 1

            if v.block_classification == CLS_BRIM or v.block_classification == CLS_TOOL_START or v.block_classification == CLS_TOOL_UNLOAD or v.block_classification == CLS_EMPTY:
                backpass(v.block_classification)

        if v.tower_measure:
            calculate_tower(code.X, code.Y)

        if v.block_classification == CLS_ENDGRID or v.block_classification == CLS_ENDPURGE:
            if code.has_X() and code.has_Y():
                if not coordinate_in_tower(code.X, code.Y):
                    v.parsed_gcode[-1].Class = CLS_NORMAL
                    v.block_classification = CLS_NORMAL

        if v.block_classification == CLS_BRIM_END:
            v.block_classification = CLS_NORMAL

        index += 1



def gcode_parseline(index):
    g = v.parsed_gcode[index]

    if g.Command == 'T':
        gcode_process_toolchange(int(g.Command_value), v.total_material_extruded, g.Layer)
        if not v.debug_leaveToolCommands:
            g.move_to_comment("Color Change")
        g.issue_command()
        v.toolchange_processed = True
        return

    if g.fullcommand in ["M104", "M109", "M140", "M190", "M73", "M84", "M201", "M204"]:
        g.issue_command()
        return

    # fan speed command

    if g.fullcommand == "M107":
        g.issue_command()
        v.saved_fanspeed = 0
        return

    if g.fullcommand == "M106":
        g.issue_command()
        v.saved_fanspeed = g.get_parameter("S", v.saved_fanspeed)
        return

    # flow rate changes have an effect on the filament consumption.  The effect is taken into account for ping generation
    if g.fullcommand == "M221":
        v.extrusion_multiplier = float(g.get_parameter("S", v.extrusion_multiplier * 100)) / 100
        g.issue_command()
        return

    # feed rate changes in the code are removed as they may interfere with the Palette P2 settings
    if g.fullcommand in ["M220"]:
        g.move_to_comment("Feed Rate Adjustments are removed")
        g.issue_command()
        return

    if g.is_movement_command():
        if g.has_X():
            v.previous_purge_keep_x = v.purge_keep_x
            v.purge_keep_x = g.X

        if g.has_Y():
            v.previous_purge_keep_y = v.purge_keep_y
            v.purge_keep_y = g.Y

        v.keep_speed = g.get_parameter("F", v.keep_speed)

    previous_block_class = v.parsed_gcode[max(0, index - 1)].Class
    classupdate = g.Class != previous_block_class

    if classupdate and previous_block_class in [CLS_TOOL_PURGE, CLS_EMPTY]:
        if v.purge_count > 0:
            gcode.issue_code(
                ";>>> Total purge {:4.0f}mm3 - {:4.0f}mm <<<\n".format(purgetower.volfromlength(v.purge_count),
                                                                       v.purge_count))

    if classupdate and g.Class in [CLS_TOOL_PURGE, CLS_EMPTY]:
        v.purge_count = 0

    if classupdate and g.Class == CLS_BRIM and v.side_wipe and v.bigbrain3d_purge_enabled:
        v.side_wipe_length = v.bigbrain3d_prime * v.bigbrain3d_blob_size
        create_sidewipe_BigBrain3D()

    if not v.side_wipe:
        if x_coordinate_in_tower(g.X):
            v.keep_x = g.X
        if y_coordinate_in_tower(g.Y):
            v.keep_y = g.Y

    # remove M900 K0 commands during unload
    if g.Class == CLS_TOOL_UNLOAD:
        if (g.fullcommand == "G4" or (g.fullcommand in ["M900"] and g.get_parameter("K", 0) == 0)):
            g.move_to_comment("tool unload")


    ## ALL SITUATIONS
    ##############################################
    if g.Class in [CLS_TOOL_START, CLS_TOOL_UNLOAD]:

        if g.is_movement_command():
            if v.side_wipe or v.tower_delta or v.full_purge_reduction:
                g.move_to_comment("tool unload")

            else:
                if g.has_Z():
                    g.remove_parameter("X")
                    g.remove_parameter("Y")
                    g.remove_parameter("F")
                    g.remove_parameter("E")
                else:
                    g.move_to_comment("tool unload")

            g.issue_command()
            return

    if g.Class == CLS_TOOL_PURGE and not (v.side_wipe or v.full_purge_reduction):



        if g.is_movement_command() and g.has_E():
            _x = g.get_parameter("X", v.current_position_x)
            _y = g.get_parameter("Y", v.current_position_y)
            # removepositive extrusions while moving into the tower
            if not (coordinate_in_tower(_x, _y) and coordinate_in_tower(v.purge_keep_x, v.purge_keep_y)) and g.E > 0:
                g.remove_parameter("E")

    if v.side_wipe:

        _x = g.get_parameter("X", v.current_position_x)
        _y = g.get_parameter("Y", v.current_position_y)
        if not coordinate_on_bed(_x, _y):
            g.remove_parameter("X")
            g.remove_parameter("Y")

    # top off the purge speed in the tower during tower delta or during no tower processing
    if not v.full_purge_reduction and not v.side_wipe and g.is_movement_command() and g.has_E() and g.has_parameter(
            "F"):
        f = int(g.get_parameter("F", 0))
        if f > v.purgetopspeed:
            g.update_parameter("F", v.purgetopspeed)
            g.add_comment(" prugespeed topped")

    ## SIDEWIPE / FULLPURGEREDUCTION / TOWER DELTA
    ###############################################
    if v.pathprocessing:

        if g.Class == CLS_TONORMAL:
            if not g.is_comment():
                g.move_to_comment("post block processing")
            g.issue_command()
            return

        # remove any commands that are part of the purge tower and still perofrm actions WITHIN the tower

        if g.is_movement_command() and g.Class in [CLS_ENDPURGE, CLS_ENDGRID] and g.has_X() and g.has_Y():
            if coordinate_in_tower(g.X, g.Y):
                g.remove_parameter("X")
                g.remove_parameter("Y")

        ###################################
        # sepcific for FULL_PURGE_REDUCTION
        ###################################

        if v.full_purge_reduction:

            if g.Class == CLS_BRIM_END:
                create_tower_gcode()
                purgetower.purge_generate_brim()

        ###################################
        # sepcific for SIDEWIPE
        ###################################

        if v.side_wipe:

            # side wipe does not need a brim
            if g.Class == CLS_BRIM:
                g.move_to_comment("side wipe - removed")
                g.issue_command()
                return

        #######################################
        # specific for TOWER DELTA
        #######################################

        if v.tower_delta:

            if classupdate and g.Class == CLS_TOOL_PURGE:
                g.issue_command()
                gcode.issue_code("G1 X{} Y{} F8640;\n".format(v.keep_x, v.keep_y))
                v.current_position_x = v.keep_x
                v.current_position_x = v.keep_y
                entertower(g.Layer * v.layer_height + v.first_layer_height)
                return

            if classupdate and previous_block_class == CLS_TOOL_PURGE:
                leavetower()

        ################################################################
        # EMPTY GRID SKIPPING CHECK FOR SIDE WIPE/TOWER DELTA/FULLPURGE
        ################################################################
        if g.Class == CLS_EMPTY and "EMPTY GRID START" in g.get_comment():
            if g.Layer < len(v.skippable_layer) and v.skippable_layer[g.Layer]:
                v.towerskipped = True
                remove_previous_move_in_tower()
                if v.tower_delta:
                    v. cur_tower_z_delta += v.layer_height
                    gcode.issue_code(";-------------------------------------\n")
                    gcode.issue_code(";  GRID SKIP --TOWER DELTA {:6.2f}mm\n".format(v.cur_tower_z_delta))
                    gcode.issue_code(";-------------------------------------\n")
            else:
                if "EMPTY GRID START" in g.get_comment() and not v.side_wipe:
                    entertower(g.Layer * v.layer_height + v.first_layer_height)


        # changing from EMPTY to NORMAL
        ###############################
        if (previous_block_class == CLS_ENDGRID) and (g.Class == CLS_NORMAL):
            v.towerskipped = False

        if v.towerskipped:
            if not g.is_comment():
                g.move_to_comment("tower skipped")
            g.issue_command()
            return
    else:
        if classupdate and g.Class in [CLS_TOOL_PURGE, CLS_EMPTY]:

            if v.acc_ping_left <= 0:
                pings.check_accessorymode_first()
            v.enterpurge = True

        if v.enterpurge and g.is_movement_command():

            v.enterpurge = False

            if g.has_X():
                _x = v.previous_purge_keep_x
            else:
                _x = v.purge_keep_x

            if g.has_Y():
                _y = v.previous_purge_keep_y
            else:
                _y = v.purge_keep_y

            if not coordinate_in_tower(_x, _y):
                _x = v.purge_keep_x
                _y = v.purge_keep_y

            if v.retraction == 0:
                purgetower.retract(v.current_tool, 3000)

            gcode.issue_code(
                "G1 X{:.3f} Y{:.3f} F8640; P2PP Inserted to realign\n".format(v.purge_keep_x, v.purge_keep_y))
            v.current_position_x = _x
            v.current_position_x = _y

            g.remove_parameter("E")
            if g.get_parameter("X") == _x:
                g.remove_parameter("X")
            if len(g.Parameters) == 0:
                g.move_to_comment("-useless command-")

    if v.tower_delta:
        if g.has_E() and g.Class in [CLS_TOOL_UNLOAD, CLS_TOOL_PURGE]:
            if not inrange(g.X, v.wipe_tower_info['minx'], v.wipe_tower_info['maxx']):
                g.remove_parameter("E")
            if not inrange(g.Y, v.wipe_tower_info['miny'], v.wipe_tower_info['maxy']):
                g.remove_parameter("E")

    # process movement commands
    ###########################

    if not g.has_E():
        g.E = 0

    if v.full_purge_reduction and g.Class == CLS_NORMAL and classupdate:
        purgetower.purge_generate_sequence()

    if g.is_movement_command():

        if v.expect_retract and g.has_X() or g.has_Y():
            if not v.retraction < 0:
                if not g.has_E and g.E < 0:
                    purgetower.retract(v.current_tool)
            v.expect_retract = False


        if v.retract_move and g.is_retract_command():
            # This is going to break stuff, G10 cannot take X and Y, what to do?
            if v.retract_x:
                g.update_parameter("X", v.retract_x)
            else:
                g.remove_parameter("X")
            if v.retract_y:
                g.update_parameter("Y", v.retract_y)
            else:
                g.remove_parameter("Y")
            v.retract_move = False

        v.current_position_x = g.get_parameter("X", v.current_position_x)
        v.current_position_y = g.get_parameter("Y", v.current_position_y)
        v.current_position_z = g.get_parameter("Z", v.current_position_z)

        if g.Class == CLS_BRIM and v.full_purge_reduction:
            g.move_to_comment("replaced by P2PP brim code")
            g.remove_parameter("E")


    if v.side_wipe or v.full_purge_reduction:
        if g.Class in [CLS_TOOL_PURGE, CLS_ENDPURGE, CLS_EMPTY]:
            if g.Layer < len(v.skippable_layer) and v.skippable_layer[g.Layer]:
                g.move_to_comment("skipped purge")
            else:
                v.side_wipe_length += g.E
                g.move_to_comment("side wipe/full purge")

    if v.toolchange_processed:
        if v.side_wipe and g.Class == CLS_NORMAL and classupdate:
            if v.bigbrain3d_purge_enabled:
                create_sidewipe_BigBrain3D()
            else:
                create_side_wipe()
            v.toolchange_processed = False

        if g.Class == CLS_NORMAL:
            gcode.GCodeCommand(";TOOLCHANGE PROCESSED").issue_command()
            v.toolchange_processed = False

    # check here issue with unretract
    #################################

    # g.Comment = " ; - {}".format(v.total_material_extruded)



    if g.is_retract_command():
        if v.retraction <= - (v.retract_length[v.current_tool] - 0.02):
            g.move_to_comment("Double Retract")
        else:
            if g.has_E():
                v.retraction += g.E
            else:
                v.retraction -= 1

    if g.is_unretract_command():
        if g.has_E():
            g.update_parameter("E", min(-v.retraction, g.E))
            v.retraction += g.E
        else:
            v.retraction = 0

    if (g.has_X() or g.has_Y()) and (g.has_E() and g.E > 0) and v.retraction < 0 and abs(v.retraction) > 0.01:
        gcode.issue_code(";fixup retracts\n")
        purgetower.unretract(v.current_tool)
        # v.retracted = False

    g.issue_command()

    ### PING PROCESSING
    ###################

    if v.accessory_mode:
        pings.check_accessorymode_second(g.E)

    if (g.has_E() and g.E > 0) and v.side_wipe_length == 0:
        pings.check_connected_ping()

    v.previous_position_x = v.current_position_x
    v.previous_position_y = v.current_position_y


# Generate the file and glue it all together!
# #####################################################################
def generate(input_file, output_file, printer_profile, splice_offset, silent):
    starttime = time.time()
    v.printer_profile_string = printer_profile
    basename = os.path.basename(input_file)
    _taskName = os.path.splitext(basename)[0].replace(" ", "_")
    _taskName = _taskName.replace(".mcf", "")

    v.splice_offset = splice_offset

    try:
        # python 3.x
        opf = open(input_file, encoding='utf-8')
    except TypeError:
        try:
            # python 2.x
            opf = open(input_file)
        except IOError:
            if v.gui:
                gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
            else:
                print ("Could not read input file\n'{}".format(input_file))
            return
    except IOError:
        if v.gui:
            gui.user_error("P2PP - Error Occurred", "Could not read input file\n'{}'".format(input_file))
        else:
            print ("Could not read input file\n'{}".format(input_file))
        return

    gui.setfilename(input_file)
    gui.set_printer_id(v.printer_profile_string)
    gui.create_logitem("Reading File " + input_file)
    gui.progress_string(1)

    v.input_gcode = opf.readlines()
    opf.close()

    v.input_gcode = [item.strip() for item in v.input_gcode]

    gui.create_logitem("Analyzing slicer parameters")
    gui.progress_string(2)
    parse_slic3r_config()

    gui.create_logitem("Pre-parsing GCode")
    gui.progress_string(4)
    parse_gcode()
    if v.palette_plus:
        if v.palette_plus_ppm == -9:
            gui.log_warning("P+ parameter P+PPM not set correctly in startup GCODE")
        if v.palette_plus_loading_offset == -9:
            gui.log_warning("P+ parameter P+LOADINGOFFSET not set correctly in startup GCODE")

    v.side_wipe = not coordinate_on_bed(v.wipetower_posx, v.wipetower_posy)
    v.tower_delta = v.max_tower_z_delta > 0

    gui.create_logitem("Creating tool usage information")
    m4c.calculate_loadscheme()



    if v.side_wipe:

        if v.skirts and v.ps_version > "2.2":
            gui.log_warning("SIDEWIPE and SKIRTS are NOT compatible in PS2.2 or later")
            gui.log_warning("THIS FILE WILL NOT PRINT CORRECTLY")

        if v.wipe_remove_sparse_layers:
            gui.log_warning("SIDE WIPE mode not compatible with sparse wipe tower in PS")
            gui.log_warning("THIS FILE WILL NOT PRINT CORRECTLY")

        gui.create_logitem("Side wipe activated", "blue")
        if v.full_purge_reduction:
            gui.log_warning("Full Purge Reduction is not compatible with Side Wipe, performing Side Wipe")
            v.full_purge_reduction = False

    if v.full_purge_reduction:
        v.side_wipe = False
        gui.create_logitem("Full Tower Reduction activated", "blue")
        if v.tower_delta:
            gui.log_warning("Full Purge Reduction is not compatible with Tower Delta, performing Full Purge Reduction")
            v.tower_delta = False

    v.pathprocessing = (v.tower_delta or v.full_purge_reduction or v.side_wipe)

    if v.autoaddsplice and not v.full_purge_reduction and not v.side_wipe:
        gui.log_warning("AUTOEDDPURGE only works with side wipe and fullpurgereduction at this moment")

    if (len(v.skippable_layer) == 0) and v.pathprocessing:
        gui.log_warning("LAYER configuration is missing. NO OUTPUT FILE GENERATED.")
        gui.log_warning("Check the P2PP documentation for furhter info.")
    else:

        if v.tower_delta:
            optimize_tower_skip(v.max_tower_z_delta, v.layer_height)

        if v.side_wipe:
            optimize_tower_skip(999, v.layer_height)

        gui.create_logitem("Generate processed GCode")

        total_line_count = len(v.input_gcode)
        v.retraction = 0
        for process_line_count in range(total_line_count):
            gcode_parseline(process_line_count)
            gui.progress_string(50 + 50 * process_line_count // total_line_count)

        v.processtime = time.time() - starttime

        gcode_process_toolchange(-1, v.total_material_extruded, 0)
        omega_result = header_generate_omega(_taskName)
        header = omega_result['header'] + omega_result['summary'] + omega_result['warnings']

        if v.absolute_extruder and v.gcode_has_relative_e:
            gui.create_logitem("Converting to absolute extrusion")
            convert_to_absolute()

        # write the output file
        ######################

        if not output_file:
            output_file = input_file
        gui.create_logitem("Generating GCODE file: " + output_file)
        opf = open(output_file, "w")
        if not v.accessory_mode:
            opf.writelines(header)
            opf.write("\n\n;--------- START PROCESSED GCODE ----------\n\n")
        if v.accessory_mode:
            opf.write("M0\n")
            opf.write("T0\n")

        if v.splice_offset == 0:
            gui.log_warning("SPLICE_OFFSET not defined")
        opf.writelines(v.processed_gcode)
        opf.close()

        if v.accessory_mode:

            pre, ext = os.path.splitext(output_file)
            if v.palette_plus:
                maffile = pre + ".msf"
            else:
                maffile = pre + ".maf"
            gui.create_logitem("Generating PALETTE MAF/MSF file: " + maffile)


            maf = open(maffile, 'w')

            for h in header:
                h = h.strip('\r\n')
                maf.write(unicode(h))
                maf.write('\r\n')
            maf.close()
            #
            # with io.open(maffile, 'w', newline='\r\n') as maf:
            #
            #     for i in range(len(header)):
            #         h = header[i].strip('\n\r') + "\n"
            #         if not h.startswith(";"):
            #             try:
            #                 maf.write(unicode(h))
            #             except:
            #                 maf.write(h)


        gui.print_summary(omega_result['summary'])

    gui.progress_string(100)
    if (len(v.process_warnings) > 0 and not v.ignore_warnings) or v.consolewait:
        gui.close_button_enable()
