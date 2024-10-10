__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

# HTML COLORS - see https://en.wikipedia.org/wiki/Web_colors
color_names_sorted = ["White", "Snow", "GhostWhite", "Azure", "Ivory", "MintCream", "FloralWhite", "AliceBlue",
                      "LavenderBlush", "SeaShell", "HoneyDew", "WhiteSmoke", "LightCyan", "LightYellow", "OldLace",
                      "Cornsilk", "Linen", "Beige", "Lavender", "LemonChiffon", "LightGoldenrodYellow", "MistyRose",
                      "PapayaWhip", "AntiqueWhite", "BlanchedAlmond", "Bisque", "Moccasin", "Gainsboro", "PeachPuff",
                      "PaleTurquoise", "NavajoWhite", "Pink", "Wheat", "PaleGoldenrod", "LightGray", "LightPink",
                      "PowderBlue", "Thistle", "LightBlue", "Khaki", "Violet", "Plum", "Aquamarine", "LightSteelBlue",
                      "LightSkyBlue", "Silver", "SkyBlue", "PaleGreen", "Orchid", "BurlyWood", "HotPink", "LightSalmon",
                      "Tan", "LightGreen", "Aqua", "Cyan", "Fuchsia", "Magenta", "Yellow", "DarkGray", "DarkSalmon",
                      "SandyBrown", "LightCoral", "Turquoise", "Salmon", "CornflowerBlue", "MediumTurquoise",
                      "MediumOrchid", "DarkKhaki", "MediumPurple", "PaleVioletRed", "MediumAquaMarine", "GreenYellow",
                      "DarkSeaGreen", "RosyBrown", "Gold", "MediumSlateBlue", "Coral", "DeepSkyBlue", "DodgerBlue",
                      "Tomato", "DeepPink", "Orange", "DarkTurquoise", "Goldenrod", "CadetBlue", "YellowGreen",
                      "LightSlateGray", "BlueViolet", "DarkOrchid", "MediumSpringGreen", "Peru", "SlateBlue",
                      "DarkOrange", "RoyalBlue", "IndianRed", "Gray", "SlateGray", "Chartreuse", "SpringGreen",
                      "LightSeaGreen", "SteelBlue", "LawnGreen", "DarkViolet", "MediumVioletRed", "MediumSeaGreen",
                      "Chocolate", "DarkGoldenrod", "OrangeRed", "DimGray", "RebeccaPurple", "LimeGreen", "Crimson",
                      "Sienna", "OliveDrab", "DarkCyan", "DarkMagenta", "DarkSlateBlue", "SeaGreen", "Olive", "Purple",
                      "Teal", "Blue", "Lime", "Red", "Brown", "FireBrick", "DarkOliveGreen", "SaddleBrown",
                      "ForestGreen", "DarkSlateGray", "Indigo", "MediumBlue", "MidnightBlue", "DarkBlue", "DarkRed",
                      "Green", "Maroon", "Navy", "DarkGreen", "Black"]
color_values_hex = ["#FFFFFF", "#FFFAFA", "#F8F8FF", "#F0FFFF", "#FFFFF0", "#F5FFFA", "#FFFAF0", "#F0F8FF", "#FFF0F5",
                    "#FFF5EE", "#F0FFF0", "#F5F5F5", "#E0FFFF", "#FFFFE0", "#FDF5E6", "#FFF8DC", "#FAF0E6", "#F5F5DC",
                    "#E6E6FA", "#FFFACD", "#FAFAD2", "#FFE4E1", "#FFEFD5", "#FAEBD7", "#FFEBCD", "#FFE4C4", "#FFE4B5",
                    "#DCDCDC", "#FFDAB9", "#AFEEEE", "#FFDEAD", "#FFC0CB", "#F5DEB3", "#EEE8AA", "#D3D3D3", "#FFB6C1",
                    "#B0E0E6", "#D8BFD8", "#ADD8E6", "#F0E68C", "#EE82EE", "#DDA0DD", "#7FFFD4", "#B0C4DE", "#87CEFA",
                    "#C0C0C0", "#87CEEB", "#98FB98", "#DA70D6", "#DEB887", "#FF69B4", "#FFA07A", "#D2B48C", "#90EE90",
                    "#00FFFF", "#00FFFF", "#FF00FF", "#FF00FF", "#FFFF00", "#A9A9A9", "#E9967A", "#F4A460", "#F08080",
                    "#40E0D0", "#FA8072", "#6495ED", "#48D1CC", "#BA55D3", "#BDB76B", "#9370DB", "#DB7093", "#66CDAA",
                    "#ADFF2F", "#8FBC8F", "#BC8F8F", "#FFD700", "#7B68EE", "#FF7F50", "#00BFFF", "#1E90FF", "#FF6347",
                    "#FF1493", "#FFA500", "#00CED1", "#DAA520", "#5F9EA0", "#9ACD32", "#778899", "#8A2BE2", "#9932CC",
                    "#00FA9A", "#CD853F", "#6A5ACD", "#FF8C00", "#4169E1", "#CD5C5C", "#808080", "#708090", "#7FFF00",
                    "#00FF7F", "#20B2AA", "#4682B4", "#7CFC00", "#9400D3", "#C71585", "#3CB371", "#D2691E", "#B8860B",
                    "#FF4500", "#696969", "#663399", "#32CD32", "#DC143C", "#A0522D", "#6B8E23", "#008B8B", "#8B008B",
                    "#483D8B", "#2E8B57", "#808000", "#800080", "#008080", "#0000FF", "#00FF00", "#FF0000", "#A52A2A",
                    "#B22222", "#556B2F", "#8B4513", "#228B22", "#2F4F4F", "#4B0082", "#0000CD", "#191970", "#00008B",
                    "#8B0000", "#008000", "#800000", "#000080", "#006400", "#000000"]


def colour_dist(r1, g1, b1, r2, g2, b2):
    r = r1 - r2
    g = g1 - g2
    b = b1 - b2
    return r * r + g * g + b * b


def hex2int(hexnum):
    try:
        return int(hexnum, 16)
    except:
        return 0


def color2rgb(c):
    if c[0] == "#":
        c = c[1:]
    c = ("000000" + c)[-6:]
    r = hex2int(c[0:1])
    g = hex2int(c[2:4])
    b = hex2int(c[4:6])
    return {'r': r, 'g': g, 'b': b}


def find_nearest_colour(user_colour):
    threshold = 256 * 256 * 3
    color_name = "Unknown"

    converted_user_color = color2rgb(user_colour)

    for colour_num in range(len(color_values_hex)):
        test_colour = color2rgb(color_values_hex[colour_num])
        col_dist = colour_dist(converted_user_color["r"], converted_user_color["g"], converted_user_color["b"],
                               test_colour["r"], test_colour["g"], test_colour["b"])
        if col_dist < threshold:
            threshold = col_dist
            color_name = color_names_sorted[colour_num]

    return color_name
