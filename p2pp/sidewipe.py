__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.purgetower as purgetower
import p2pp.variables as v
from p2pp.gcode import issue_code


#
# to be implemented - Big Brain 3D purge mechanism support
#

def setfanspeed(n):
    if n == 0:
        issue_code("M107                ; Turn FAN OFF\n")
    else:
        issue_code("M106 S{}           ; Set FAN Power\n".format(n))


def resetfanspeed():
    setfanspeed(v.saved_fanspeed)


def generate_blob(length, count):
    issue_code("\n;---- BIGBRAIN3D SIDEWIPE BLOB {} -- purge {:.3f}mm\n".format(count + 1, length))
    # issue_code("M907 X{} ; set motor power\n".format(int(v.purgemotorpower)))

    setfanspeed(0)
    if v.bigbrain3d_fanoffdelay > 0:
        issue_code("G4 P{} ; delay to let the fan spinn down".format(v.bigbrain3d_fanoffdelay))

    issue_code(
        "G1 X{:.3f} F3000   ; go near the edge of the print\n".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 10))
    issue_code(
        "G1 X{:.3f} F1000   ; go to the actual wiping position\n".format(v.bigbrain3d_x_position))  # takes 2.5 seconds

    if v.retraction < 0:
        purgetower.unretract(v.current_tool, 1200)
    if v.bigbrain3d_smartfan:
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN OFF \n".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(32)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 12% \n".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(64)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 25% \n".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(96)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 37% \n".format(length / 4, v.bigbrain3d_blob_speed))
    else:
        issue_code("G1 E{:6.3f} F{}     ; UNRETRACT/PURGE/RETRACT \n".format(length, v.bigbrain3d_blob_speed))
    purgetower.largeretract()
    setfanspeed(255)
    issue_code(
        "G4 S{0:.0f}              ; blob {0}s cooling time\n".format(v.bigbrain3d_blob_cooling_time))
    issue_code("G1 X{:.3f} F10800  ; activate flicker\n".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))

    for i in range(v.bigbrain3d_whacks):
        issue_code(
            "G4 S1               ; Mentally prep for second whack\n".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))
        issue_code("G1 X{:.3f} F3000   ; approach for second whach\n".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 10))
        issue_code("G1 X{:.3f} F1000   ; final position for whack and......\n".format(
            v.bigbrain3d_x_position))  # takes 2.5 seconds
        issue_code("G1 X{:.3f} F10800  ; WHACKAAAAA!!!!\n".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))



def create_sidewipe_BigBrain3D():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

    # purge blobs should all be same size
    purgeleft = v.side_wipe_length % v.bigbrain3d_blob_size
    purgeblobs = int(v.side_wipe_length / v.bigbrain3d_blob_size)

    if purgeleft > 1:
        purgeblobs += 1

    keepe = v.total_material_extruded
    correction = v.bigbrain3d_blob_size * purgeblobs - v.side_wipe_length

    issue_code(";-------------------------------\n")
    issue_code("; P2PP BB3DBLOBS: {:.0f} BLOBS\n".format(purgeblobs))
    issue_code(";-------------------------------\n")

    issue_code(
        "; Req={:.2f}mm  Act={:.2f}mm\n".format(v.side_wipe_length, v.side_wipe_length + correction))
    issue_code("; Purge difference {:.2f}mm\n".format(correction))
    issue_code(";-------------------------------\n")

    if v.retraction == 0:
        purgetower.largeretract()

    keep_xpos = v.current_position_x
    keep_ypos = v.current_position_y

    if (v.current_position_z < 20):
        issue_code("\nG1 Z20.000 F8640    ; Increase Z to prevent collission with bed\n")

    if (v.bigbrain3d_y_position is not None):
        issue_code("\nG1 Y{:.3f} F8640    ; change Y position to purge equipment\n".format(v.bigbrain3d_y_position))

    issue_code("G1 X{:.3f} F10800  ; go near edge of bed\n".format(v.bigbrain3d_x_position - 30))
    issue_code("G4 S0               ; wait for the print buffer to clear\n")
    issue_code("M907 X{}           ; increase motor power\n".format(v.bigbrain3d_motorpower_high))
    issue_code("; Generating {} blobs for {}mm of purge".format(purgeblobs, v.side_wipe_length))

    for i in range(purgeblobs):
        generate_blob(v.bigbrain3d_blob_size, i)

    if (v.current_position_z < 20):

        if v.retraction != 0:
            purgetower.retract(v.current_tool)

        issue_code("\nG1 X{:.3f} Y{:.3f} F8640".format(keep_xpos, keep_ypos))
        issue_code("\nG1 Z{:.4f} F8640    ; Reset correct Z height to continue print\n".format(v.current_position_z))

    resetfanspeed()
    issue_code("\nM907 X{}           ; reset motor power\n".format(v.bigbrain3d_motorpower_normal))
    issue_code("\n;-------------------------------\n\n")

    v.side_wipe_length = 0




def create_side_wipe():
    if not v.side_wipe or v.side_wipe_length == 0:
        return

    issue_code(";---------------------------\n")
    issue_code(";  P2PP SIDE WIPE: {:7.3f}mm\n".format(v.side_wipe_length))

    for line in v.before_sidewipe_gcode:
        issue_code(line + "\n")

    if v.retraction == 0:
        purgetower.retract(v.current_tool)

    issue_code("G1 F8640\n")
    issue_code("G0 {} Y{}\n".format(v.side_wipe_loc, v.sidewipe_miny))

    sweep_base_speed = v.wipe_feedrate * 20 * abs(v.sidewipe_maxy - v.sidewipe_miny) / 150
    sweep_length = 20

    yrange = [v.sidewipe_maxy, v.sidewipe_miny]
    rangeidx = 0
    movefrom = v.sidewipe_miny
    moveto = yrange[rangeidx]
    numdiffs = 20
    purgetower.unretract(v.current_tool)


    while v.side_wipe_length > 0:
        sweep = min(v.side_wipe_length, sweep_length)
        v.side_wipe_length -= sweep_length
        wipe_speed = min(5000, int(sweep_base_speed / sweep))


        # split this move in very short moves to allow for faster planning buffer depletion
        diff = (moveto - movefrom) / numdiffs

        for i in range(numdiffs):
            issue_code("G1 {} Y{:.3f} E{:.5f} F{}\n".format(v.side_wipe_loc, movefrom + (i+1)*diff, sweep/numdiffs * v.sidewipe_correction, wipe_speed))

        # issue_code(
        #     "G1 {} Y{} E{:.5f} F{}\n".format(v.side_wipe_loc, moveto, sweep * v.sidewipe_correction, wipe_speed))

        rangeidx += 1
        movefrom = moveto
        moveto = yrange[rangeidx % 2]

    for line in v.after_sidewipe_gcode:
        issue_code(line + "\n")

    purgetower.retract(v.current_tool)
    issue_code("G1 F8640\n")
    issue_code(";---------------------------\n")

    v.side_wipe_length = 0
