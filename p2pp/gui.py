__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

try:
    # p ython version 2.x
    import Tkinter as tkinter
    import ttk
    import tkMessageBox
except ImportError:
    # python version 3.x
    import tkinter
    from tkinter import ttk
    from tkinter import messagebox as tkMessageBox

import os
import sys
from platform import system

import p2pp.colornames as colornames
import p2pp.variables as v
import version

platformD = system()

last_pct = -1


def print_summary(summary):
    create_logitem("")
    create_logitem("-" * 19, "blue")
    create_logitem("   Print Summary", "blue")
    create_logitem("-" * 19, "blue")
    create_emptyline()
    create_logitem("Number of splices:    {0:5}".format(len(v.splice_extruder_position)))
    create_logitem("Number of pings:      {0:5}".format(len(v.ping_extruder_position)))
    create_logitem("Total print length {:-8.2f}mm".format(v.total_material_extruded))
    create_emptyline()
    if v.full_purge_reduction or v.tower_delta:
        create_logitem("Tower Delta Range  {:.2f}mm -  {:.2f}mm".format(v.min_tower_delta, v.max_tower_delta))
    create_emptyline()

    if v.m4c_numberoffilaments <= 4:

        create_logitem("Inputs/Materials used:")

        for i in range(len(v.palette_inputs_used)):
            if v.palette_inputs_used[i]:
                create_colordefinition(0, i + 1, v.filament_type[i], v.filament_color_code[i],
                                       v.material_extruded_per_color[i])

    else:
        create_logitem("Materials used:")
        for i in range(v.m4c_numberoffilaments):
            create_colordefinition(1, i + 1, v.filament_type[0], v.filament_color_code[i], 0)

        create_emptyline()

        create_logitem("Required Toolchanges: {}".format(len(v.m4c_headerinfo)))
        for i in v.m4c_headerinfo:
            create_logitem("      " + i)

    create_emptyline()
    for line in summary:
        create_logitem(line[1:].strip(), "black", False)
    create_emptyline()


def progress_string(pct):
    global last_pct
    if last_pct == pct:
        return
    if pct == 100:
        if len(v.process_warnings) == 0:
            completed("  COMPLETED OK", '#008000')
        else:
            completed("  COMPLETED WITH WARNINGS",'#800000')
    else:
       progress.set(pct)
    mainwindow.update()
    last_pct = pct

def completed(text, color):
    progressbar.destroy()
    progress_field = tkinter.Label(infosubframe , text=text, font=boldfont, foreground=color,  background="#808080")
    progress_field.grid(row=3, column=2, sticky="ew")

color_count = 0


def create_logitem(text, color="black", force_update=True, position=tkinter.END):
    text = text.strip()
    global color_count
    color_count += 1
    tagname = "color"+str(color_count)
    loglist.tag_configure(tagname, foreground=color)
    loglist.insert(position, "  " + text + "\n", tagname)
    if force_update:
        mainwindow.update()


def create_colordefinition(reporttype, input, filament_type, color_code, filamentused):
    global color_count
    if reporttype == 0:
        name = "Input"
    if reporttype == 1:
        name = "Filament"

    color_count += 1
    tagname = "color" + str(color_count)
    color_count += 1
    tagname2 = "color" + str(color_count)
    loglist.tag_configure(tagname, foreground='black')
    loglist.tag_configure(tagname2, foreground="#"+color_code)

    try:
        filament_id = v.filament_ids[input - 1]
    except IndexError:
        filament_id = ""

    if reporttype == 0:
        loglist.insert(tkinter.END, "  \t{}  {} {:-8.2f}mm - {}".format(name, input, filamentused, filament_type),
                       tagname)
    if reporttype == 1:
        loglist.insert(tkinter.END, "  \t{}  {}  - {}".format(name, input, filament_type), tagname)

    loglist.insert(tkinter.END, "  \t[####]\t", tagname2)
    loglist.insert(tkinter.END, "  \t{:15} {} \n".format(colornames.find_nearest_colour(color_code), filament_id),
                   tagname)


def create_emptyline():
    create_logitem('')

def close_window():
    mainwindow.destroy()

def update_button_pressed():
    v.upgradeprocess(version.latest_stable_version, [])

def close_button_enable():
    closebutton.config(state=tkinter.NORMAL)
    # WIP disable upgrade for now
    # if not (v.upgradeprocess == None):
    #     tkinter.Button(buttonframe, text='Upgrade to '+version.latest_stable_version, command=update_button_pressed).pack(side=tkinter.RIGHT)
    mainwindow.mainloop()


def center(win, width, height):
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)  # center horizontally in screen
    y = (win.winfo_screenheight() // 2) - (height // 2)  # center vertically in screen
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    win.minsize(int(width / 1.2), int(height / 1.2))
    win.maxsize(width * 4, height * 4)


def set_printer_id(text):
    printerid.set(text)
    mainwindow.update()


def setfilename(text):
    filename.set(text)
    mainwindow.update()


def user_error(header, body_text):
    tkMessageBox.showinfo(header, body_text)


def ask_yes_no(title, message):
    return (tkMessageBox.askquestion(title, message).upper()=="YES")


def log_warning(text):
    v.process_warnings.append(";" + text)
    create_logitem(text, "red")

def configinfo():
    global infosubframe
    infosubframe.destroy()
    infosubframe = tkinter.Frame(infoframe, border=3, relief='sunken', background="#909090")
    infosubframe.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
    tkinter.Label(infosubframe, text='CONFIGURATION  INFO', font=boldfontlarge, background="#909090").pack(side=tkinter.TOP, expand=1)

    tkinter.Label(infosubframe, text="P2PP Version "+version.Version+"\n", font=boldfont, background="#909090").pack( side=tkinter.BOTTOM)


mainwindow = tkinter.Tk()
mainwindow.title("Palette2 Post Processing for PrusaSliceer")
center(mainwindow, 800, 620)

if platformD == 'Windows':
    logo_image = os.path.dirname(sys.argv[0]) + '\\favicon.ico'
    mainwindow.iconbitmap(logo_image)
    mainwindow.update()

mainwindow['padx'] = 10
mainwindow['pady'] = 10
boldfontlarge = 'Helvetica 30 bold'
normalfont = 'Helvetica 15'
boldfont = 'Helvetica 15 bold'
fixedfont = 'Courier 14'
fixedsmallfont = 'Courier 12'

# Top Information Frqme
infoframe = tkinter.Frame(mainwindow, border=3, relief='flat', background="#808080")
infoframe.pack(side=tkinter.TOP, fill=tkinter.X)

# logo
logoimage = tkinter.PhotoImage(file=os.path.dirname(sys.argv[0]) + "/appicon.ppm")
logofield = tkinter.Label(infoframe, image=logoimage)
logofield.pack(side=tkinter.LEFT, fill=tkinter.Y)

infosubframe = tkinter.Frame(infoframe, relief='flat', background="#808080")
infosubframe.pack(side=tkinter.LEFT, fill=tkinter.X, )
infosubframe["padx"] = 20

# file name display
tkinter.Label(infosubframe, text='Filename:', font=boldfont, background="#808080").grid(row=0, column=1, sticky="w")
filename = tkinter.StringVar()
setfilename("-----")
tkinter.Label(infosubframe, textvariable=filename, font=normalfont, background="#808080").grid(row=0, column=2,
                                                                                               sticky="w")

# printer ID display
printerid = tkinter.StringVar()
set_printer_id("-----")

tkinter.Label(infosubframe, text='Printer ID:', font=boldfont, background="#808080").grid(row=1, column=1, sticky="w")
tkinter.Label(infosubframe, textvariable=printerid, font=normalfont, background="#808080").grid(row=1, column=2,
                                                                                                sticky="w")


tkinter.Label(infosubframe, text="P2PP Version:", font=boldfont, background="#808080").grid(row=2, column=1,
                                                                                            sticky="w")
tkinter.Label(infosubframe, text=version.Version, font=normalfont, background="#808080").grid(row=2, column=2,
                                                                                              sticky="w")

# progress bar
progress = tkinter.IntVar()
progress.set(0)
tkinter.Label(infosubframe, text='Progress:', font=boldfont, background="#808080").grid(row=3, column=1, sticky="w")
progressbar = ttk.Progressbar(infosubframe ,orient='horizontal', mode='determinate', length=500, maximum=100, variable=progress)
progressbar.grid(row=3, column=2,  sticky='ew')


# Log frame
logframe = tkinter.Frame(mainwindow, border=3, relief="sunken")
logframe.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

yloglistscroll = tkinter.Scrollbar(logframe, orient=tkinter.VERTICAL)
yloglistscroll.pack(side='right', fill=tkinter.Y)

xloglistscroll = tkinter.Scrollbar(logframe, orient=tkinter.HORIZONTAL)
xloglistscroll.pack(side='bottom', fill=tkinter.X)

loglist = tkinter.Text(logframe, yscrollcommand=yloglistscroll.set, xscrollcommand=xloglistscroll.set, wrap="none",
                       font=fixedsmallfont)
loglist.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)

yloglistscroll.config(command=loglist.yview)
xloglistscroll.config(command=loglist.xview)

# Button frame
buttonframe = tkinter.Frame(mainwindow, border=1, relief="flat")
buttonframe.pack(side=tkinter.BOTTOM, fill=tkinter.X)

closebutton = tkinter.Button(buttonframe, text="Exit", state=tkinter.DISABLED, command=close_window, height=2)
closebutton.pack(fill=tkinter.BOTH, expand=True)

mainwindow.rowconfigure(0, weight=1000)
mainwindow.rowconfigure(1, weight=2)
mainwindow.rowconfigure(2, weight=1000)

mainwindow.lift()
mainwindow.attributes('-topmost', True)
mainwindow.after_idle(mainwindow.attributes, '-topmost', False)
mainwindow.update()

