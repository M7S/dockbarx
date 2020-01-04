#!/usr/bin/python3

#   iconfactory.py
#
#   Copyright 2009, 2010 Matias Sars
#
#   DockbarX is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DockbarX is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import gc
gc.enable()
import cairo
from gi.repository import Gio
import os
import weakref
import array
from math import pi, cos, sin
from PIL import Image

from .theme import Theme
from .common import Globals, connect, disconnect
from .log import logger

from . import i18n
_ = i18n.language.gettext

class IconFactory():
    """IconFactory finds the icon for a program and prepares the cairo surface."""
    icon_theme = Gtk.IconTheme.get_default()
    # Constants
    # Icon types
    SOME_MINIMIZED = 1<<4
    ALL_MINIMIZED = 1<<5
    LAUNCHER = 1<<6
    # Icon effects
    MOUSE_OVER = 1<<7
    MOUSE_BUTTON_DOWN = 1<<8
    NEEDS_ATTENTION = 1<<9
    BLINK  = 1<<10
    # ACTIVE_WINDOW
    ACTIVE = 1<<11
    LAUNCH_EFFECT = 1<<12
    # Double width/height icons for drag and drop situations.
    DRAG_DROPP_START = 1<<13
    DRAG_DROPP_END = 1<<14
    TYPE_DICT = {"some_minimized":SOME_MINIMIZED,
                 "all_minimized":ALL_MINIMIZED,
                 "launcher":LAUNCHER,
                 "mouse_over":MOUSE_OVER,
                 "needs_attention":NEEDS_ATTENTION,
                 "blink":BLINK,
                 "active":ACTIVE,
                 "launching":LAUNCH_EFFECT,
                 "mouse_button_down":MOUSE_BUTTON_DOWN}

    def __init__(self, group, class_group=None,
                 desktop_entry=None, identifier=None, size=None):
        self.dockbar_r = weakref.ref(group.dockbar_r())
        self.theme = Theme()
        self.globals = Globals()
        connect(self.globals, "color-changed", self.reset_surfaces)
        self.desktop_entry = desktop_entry
        self.identifier = identifier
        self.class_group = class_group

        # Setting size to something other than zero to
        # avoid crashes if surface_update() is runned
        # before the size is set.
        if size is None or size <=0:
            self.size = 15
        else:
            self.size = size

        self.icon = None
        self.surfaces = {}

        self.average_color = None

        self.max_win_nr = self.theme.get_windows_cnt()
        self.types_in_theme = 0
        for type_ in self.theme.get_types():
            if not type_ in self.TYPE_DICT:
                continue
            self.types_in_theme = self.types_in_theme | self.TYPE_DICT[type_]

    def remove(self):
        del self.desktop_entry
        del self.class_group
        del self.icon
        del self.surfaces
        del self.theme

    def set_desktop_entry(self, desktop_entry):
        self.desktop_entry = desktop_entry
        self.surfaces = {}
        del self.icon
        self.icon = None

    def set_class_group(self, class_group):
        if not self.desktop_entry and not self.class_group:
            self.surfaces = {}
            del self.icon
            self.icon = None
        self.class_group = class_group

    def set_size(self, size):
        if size <= 0:
            # To avoid crashes.
            size = 15
        self.size = size
        self.surfaces = {}
        self.average_color = None

    def get_size(self):
        return self.size

    def get_icon(self, size):
        return self.__find_icon_pixbuf(size)


    def reset_icon(self):
        self.icon = None


    def reset_surfaces(self, arg=None):
        self.surfaces = {}
        self.average_color = None


    def surface_update(self, type_ = 0):
        # Checks if the requested pixbuf is already
        # drawn and returns it if it is.
        # Othervice the surface is drawn, saved and returned.

        #The first four bits of type_ is for telling the number of windows
        self.win_nr = min(type_ & 15, self.max_win_nr)
        # Remove all types that are not used by the theme (saves memory)
        dnd = (type_ & self.DRAG_DROPP_START and "start") or \
              (type_ & self.DRAG_DROPP_END and "end")
        type_ = type_ & self.types_in_theme
        type_ += self.win_nr
        self.orient = self.dockbar_r().orient
        is_vertical = self.orient in ("left", "right")
        if type_ in self.surfaces:
            surface = self.surfaces[type_]
        else:
            self.temp = {}
            surface = None
            commands = self.theme.get_icon_dict()
            self.ar = self.theme.get_aspect_ratio(is_vertical)
            self.type_ = type_
            surface = self.__do_commands(surface, commands)
            # Todo: add size correction.
            self.surfaces[type_] = surface
            del self.temp
            gc.collect()
        if dnd:
            print
            surface = self.__dd_highlight(surface, is_vertical, dnd)
            gc.collect()
        return surface

    def __do_commands(self, surface, commands):
        for command, args in list(commands.items()):
            try:
                f = getattr(self, "_IconFactory__command_%s"%command)
            except:
                raise
            else:
                if "type" in args:
                    args["type_"] = args.pop("type")
                surface = f(surface, **args)
        return surface


    def __dd_highlight(self, surface, is_vertical, position="start"):
        w = surface.get_width()
        h = surface.get_height()
        if is_vertical:
            h = h + 4
        else:
            w = w + 4
        bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(bg)

        if is_vertical and position == "start":
            ctx.move_to(1, 1.5)
            ctx.line_to(w - 1, 1.5)
            ctx.set_source_rgba(1, 1, 1, 0.2)
            ctx.set_line_width(2)
            ctx.stroke()
            ctx.move_to(2, 1.5)
            ctx.line_to(w - 2, 1.5)
            ctx.set_source_rgba(0, 0, 0, 0.7)
            ctx.set_line_width(1)
            ctx.stroke()
        elif is_vertical:
            ctx.move_to(1, h - 1.5)
            ctx.line_to(w - 1, h - 1.5)
            ctx.set_source_rgba(1, 1, 1, 0.2)
            ctx.set_line_width(2)
            ctx.stroke()
            ctx.move_to(2, h - 1.5)
            ctx.line_to(w - 2, h - 1.5)
            ctx.set_source_rgba(0, 0, 0, 0.7)
            ctx.set_line_width(1)
            ctx.stroke()
        elif position == "start":
            ctx.move_to(1.5, 1)
            ctx.line_to(1.5, h - 1)
            ctx.set_source_rgba(1, 1, 1, 0.2)
            ctx.set_line_width(2)
            ctx.stroke()
            ctx.move_to(1.5, 2)
            ctx.line_to(1.5, h - 2)
            ctx.set_source_rgba(0, 0, 0, 0.7)
            ctx.set_line_width(1)
            ctx.stroke()
        else:
            ctx.move_to(w - 1.5, 1)
            ctx.line_to(w - 1.5, h - 1)
            ctx.set_source_rgba(1, 1, 1, 0.2)
            ctx.set_line_width(2)
            ctx.stroke()
            ctx.move_to(w - 1.5, 2)
            ctx.line_to(w - 1.5, h - 2)
            ctx.set_source_rgba(0, 0, 0, 0.7)
            ctx.set_line_width(1)
            ctx.stroke()

        x, y  = 0, 0
        if is_vertical and position == "start":
            y = 4
        elif position == "start":
            x = 4
        ctx.set_source_surface(surface, x, y)
        ctx.paint()
        return bg

    def __get_color(self, color):
        if color == "active_color":
            color = "color5"
        if color in ["color%s"%i for i in range(1, 9)]:
            color = self.globals.colors[color]
        if color == "icon_average":
            color = self.__get_average_color()
        else:
            try:
                if len(color) != 7:
                    raise ValueError("The string has the wrong lenght")
                t = int(color[1:], 16)
            except:
                logger.exception("Theme error: the color attribute " +
                      "for a theme command"+ \
                      " should be a six digit hex string eg. \"#FFFFFF\" or"+ \
                      " the a dockbarx color (\"color1\"-\"color8\").")
                color = "#000000"
        return color

    def __get_alpha(self, alpha):
        # Transparency
        if alpha == "active_opacity":
            # For backwards compability
            alpha = "color5"

        for i in range(1, 9):
            if alpha in ("color%s"%i, "opacity%s"%i):
                if "color%s_alpha"%i in self.globals.colors:
                    a = float(self.globals.colors["color%s_alpha"%i])/255
                else:
                    logger.warning("Theme error: The theme has no" + \
                          " opacity option for color%s." % i)
                    a = 1.0
                break
        else:
            try:
                a = float(alpha)/100
                if a > 1.0 or a < 0:
                    raise
            except:
                logger.exception("Theme error: The opacity attribute of a theme " + \
                      "command should be a number between \"0\" " + \
                      " and \"100\" or \"color1\" to \"color8\".")
                a = 1.0
        return a

    def __get_average_color(self):
        if self.average_color is not None:
            return self.average_color
        r = 0
        b = 0
        g = 0
        i = 0
        im = self.__surface2pil(self.icon)
        pixels = im.load()
        width, height = im.size
        for x in range(width):
            for y in range(height):
                pix = pixels[x, y]
                if pix[3] > 30:
                    i += 1
                    r += pix[0]
                    g += pix[1]
                    b += pix[2]
        if i > 0:
            r = int(round(float(r) / i))
            g = int(round(float(g) / i))
            b = int(round(float(b) / i))
        r = ("0%s"%hex(r)[2:])[-2:]
        g = ("0%s"%hex(g)[2:])[-2:]
        b = ("0%s"%hex(b)[2:])[-2:]
        self.average_color = "#"+r+g+b
        return self.average_color


    #### Flow commands
    def __command_if(self, surface, type_=None, windows=None,
                     size=None, orient=None, content=None):
        if content is None:
            return surface
        # TODO: complete this
##        l = []
##        splits = ["!", "(", ")", "&", "|"]
##        for c in type_:
##            if c in splits:
##                l.append(c)
##            elif l[-1] in splits:
##                l.append(c)
##            elif not l:
##                l.append(c)
##            else:
##                l[-1] += c
        # Check if the type_ condition is satisfied
        if type_ is not None:
            negation = False
            if type_[0] == "!" :
                type_ = type_[1:]
                negation = True
            is_type = bool(type_ in self.TYPE_DICT \
                      and self.type_ & self.TYPE_DICT[type_])
            if not (is_type ^ negation):
                return surface

        #Check if the window number condition is satisfied
        if windows is not None:
            arg = windows
            negation = False
            if arg[0] == "!" :
                arg = windows[1:]
                negation = True
            if arg[0] == ":":
                arg = "0" + arg
            elif arg[-1] == ":":
                arg = arg +"15"
            l = arg.split(":", 1)
            try:
                l = [int(n) for n in l]
            except ValueError:
                logger.exception("Theme Error: The windows attribute of " + \
                      "an <if> statement can\'t look like this:" + \
                      " \"%s\"." % windows + \
                      "See Theming HOWTO for more information")
                return surface
            if len(l) == 1:
                if not ((l[0] == self.win_nr) ^ negation):
                    return surface
            else:
                if not ((l[0]<=self.win_nr and self.win_nr<=l[1]) ^ negation):
                    return surface

        #Check if the icon size condition is satisfied
        if size is not None:
            arg = size
            negation = False
            if arg[0] == "!" :
                arg = size[1:]
                negation = True
            if arg[0] == ":":
                arg = "0" + arg
            elif arg[-1] == ":":
                arg = arg +"200"
            l = arg.split(":", 1)
            try:
                l = [int(n) for n in l]
            except ValueError:
                logger.exception("Theme Error: The size attribute of " + \
                      "an <if> statement can\'t look like this:" + \
                      " \"%s\". See Theming HOWTO for more information" % size)
                return surface
            us = int(round(self.__get_use_size()))
            if len(l) == 1:
                if not ((l[0] == self.win_nr) ^ negation):
                    return surface
            else:
                if not ((l[0]<=us and us<=l[1]) ^ negation):
                    return surface

        # Test if the orient condition is satisfied.
        if orient is not None:
            orients = orient.split(",")
            if not self.orient in orients:
                return surface

        # All tests passed, proceed.
        surface = self.__do_commands(surface, content)
        return surface

    def __command_pixmap_from_self(self, surface, name, content=None):
        if not name:
            logger.warning("Theme Error: no name given for pixmap_from_self")
            raise Exeption
        w = int(surface.get_width())
        h = int(surface.get_height())
        self.temp[name] = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(self.temp[name])
        ctx.set_source_surface(surface)
        ctx.paint()
        if content is None:
            return surface
        for command,args in list(content.items()):
            try:
                f = getattr(self,"_IconFactory__command_%s"%command)
            except:
                raise
            else:
                if "type" in args:
                        args["type_"] = args.pop("type")
                self.temp[name] = f(self.temp[name], **args)
        return surface

    def __command_pixmap(self, surface, name, content=None, size=None):
        if size is not None:
            # TODO: Fix for different height and width
            w = h = int(round(self.__get_use_size() + \
                              self.__process_size(size)))
        elif surface is None:
            w = h = int(round(self.__get_use_size()))
        else:
            w = surface.get_width()
            h = surface.get_height()
        self.temp[name] = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        if content is None:
            return surface
        for command,args in list(content.items()):
            try:
                f = getattr(self,"_IconFactory__command_%s"%command)
            except:
                raise
            else:
                if "type" in args:
                    args["type_"] = args.pop("type")
                self.temp[name] = f(self.temp[name], **args)
        return surface


    #### Get icon
    def __command_get_icon(self,surface=None, size="0"):
        size = int(self.__get_use_size() + self.__process_size(size))
        if size <= 0:
            # To avoid crashes.
            size = 15
        if self.icon and\
           self.icon.get_width() == size and \
           self.icon.get_height() == size:
            return self.icon
        del self.icon
        self.icon = None
        pb = self.__find_icon_pixbuf(size)

        if pb.get_width() != pb.get_height():
            if pb.get_width() < pb.get_height():
                h = size
                w = pb.get_width() * size // pb.get_height()
            elif pb.get_width() > pb.get_height():
                w = size
                h = pb.get_height() * size // pb.get_width()
            self.icon = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            ctx = cairo.Context(self.icon)
            pbs = pb.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
            woffset = round((size - w) / 2.0)
            hoffset = round((size - h) / 2.0)
            ctx.set_source_pixbuf(pb, woffset, hoffset)
            ctx.paint()
            del pb
            del pbs
        elif pb.get_width() != size:
            pbs = pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            self.icon = self.__pixbuf2surface(pbs)
            del pb
            del pbs
        else:
            self.icon = self.__pixbuf2surface(pb)
            del pb
        return self.icon


    def __find_icon_pixbuf(self, size):
        # Returns the icon pixbuf for the program. Uses the following metods:

        # 1) If it is a launcher, return the icon from the
        #    launcher's desktopfile
        # 2) Get the icon from the gio app
        # 3) Check if the res_class fits an themed icon.
        # 4) Search in path after a icon matching reclass.
        # 5) Use the mini icon for the class

        pixbuf = None
        icon_name = None
        if self.desktop_entry:
            icon_name = self.desktop_entry.getIcon()
            if icon_name is not None and os.path.isfile(icon_name):
                pixbuf = self.__icon_from_file_name(icon_name, size)
                if pixbuf is not None:
                    return pixbuf

        if not icon_name:
            if self.identifier:
                icon_name = self.identifier.lower()
            elif self.class_group:
                icon_name = self.class_group.get_res_class().lower()
            else:
                icon_name = ""

            # Special cases
            if icon_name.startswith("openoffice"):
                icon_name = "ooo-writer"
            if icon_name.startswith("libreoffice"):
                icon_name = "libreoffice-writer"

        if self.icon_theme.has_icon(icon_name):
            return self.icon_theme.load_icon(icon_name,size,0)

        if icon_name[-4:] in (".svg", ".png", ".xpm"):
            if self.icon_theme.has_icon(icon_name[:-4]):
                pixbuf = self.icon_theme.load_icon(icon_name[:-4],size,0)
                if pixbuf is not None:
                    return pixbuf

        pixbuf = self.__icon_search_in_data_path(icon_name, size)
        if pixbuf is not None:
            return pixbuf

        if self.class_group:
            return self.class_group.get_icon().copy()


        # If no pixbuf has been found (can only happen for an unlaunched
        # launcher), make an empty pixbuf and show a warning.
        if self.icon_theme.has_icon("application-default-icon"):
            pixbuf = self.icon_theme.load_icon("application-default-icon",
                                                size, 0)
        else:
            pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
            pixbuf.fill(0x00000000)
        if self.desktop_entry:
            name = self.desktop_entry.getName()
        else:
            name = None
        return pixbuf

    def __icon_from_file_name(self, icon_name, icon_size = -1):
        if os.path.isfile(icon_name):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, -1,
                                                            icon_size)
            except:
                pass
        return None

    def __icon_search_in_data_path(self, icon_name, icon_size):
        data_folders = None

        if "XDG_DATA_DIRS" in os.environ:
            data_folders = os.environ["XDG_DATA_DIRS"]

        if not data_folders:
            data_folders = "/usr/local/share/:/usr/share/"

        for data_folder in data_folders.split(":"):
            #The line below line used datafolders instead of datafolder.
            #I changed it because I suspect it was a bug.
            paths = (os.path.join(data_folder, "pixmaps", icon_name),
                     os.path.join(data_folder, "icons", icon_name))
            for path in paths:
                if os.path.isfile(path):
                    icon = self.__icon_from_file_name(path, icon_size)
                    if icon:
                        return icon
        return None


    #### Other commands
    def __command_clear(self, surface):
        if self.dockbar_r().orient in ("left", "right"):
            w = self.size
            h = int(self.size * self.ar)
        else:
            w = int(self.size * self.ar)
            h = self.size
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_rgba(0, 0, 0)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint_with_alpha(0)
        return new

    def __command_get_pixmap(self, surface, name):
        if surface is None:
            if self.dockbar_r().orient in ("left", "right"):
                width = self.size
                height = int(self.size * self.ar)
            else:
                width = int(self.size * self.ar)
                height = self.size
        else:
            width = surface.get_width()
            height = surface.get_height()
        if self.theme.has_surface(name):
            surface = self.__resize_surface(self.theme.get_surface(name),
                                            width, height)
        else:
            logger.warning("theme error: pixmap %s not found" % name)
        return surface

    def __command_fill(self, surface, color, opacity="100"):
        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface)
        ctx.paint()

        alpha = self.__get_alpha(opacity)
        c = self.__get_color(color)
        r = float(int(c[1:3], 16))/255
        g = float(int(c[3:5], 16))/255
        b = float(int(c[5:7], 16))/255
        ctx.set_source_rgba(r, g, b)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint_with_alpha(alpha)
        return new


    def __command_combine(self, surface, pix1, pix2, degrees=None):
        # Combines left half of surface with right half of surface2.
        # The transition between the two halves are soft.

        # Degrees keyword are kept of compability reasons.
        w = surface.get_width()
        h = surface.get_height()
        if pix1=="self":
            p1 = surface
        elif pix1 in self.temp:
            p1 = self.temp[pix1]
        elif self.theme.has_surface(pix1):
            w = surface.get_width()
            h = surface.get_height()
            p1 = self.__resize_surface(self.theme.get_surface(bg), w, h)
        else:
            logger.warning("theme error: pixmap %s not found"%pix1)
        if pix2=="self":
            p2 = surface
        elif pix2 in self.temp:
            p2 = self.temp[pix2]
        elif self.theme.has_surface(pix2):
            w = surface.get_width()
            h = surface.get_height()
            p2 = self.__resize_surface(self.theme.get_surface(bg), w, h)
        else:
            logger.warning("theme error: pixmap %s not found" % pix2)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     p1.get_width(), p1.get_height())
        ctx = cairo.Context(surface)

        linear = cairo.LinearGradient(0, 0, p1.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 0.5)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 1)
        ctx.set_source_surface(p2, 0, 0)
        #ctx.mask(linear)
        ctx.paint()

        linear = cairo.LinearGradient(0, 0, p1.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 1)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 0)
        ctx.set_source_surface(p1, 0, 0)
        ctx.mask(linear)
        try:
            del pb
            del pbs
        except:
            pass
        return surface

    def __command_transp_sat(self, surface, opacity="100", saturation="100"):
        # Makes the icon desaturized and/or transparent.
        alpha = self.__get_alpha(opacity)
        # Todo: Add error check for saturation
        sat = float(saturation)
        if sat != 100:
            im = self.__surface2pil(surface)
            w, h = im.size
            pixels = im.load()
            for x in range(w):
                for y in range(h):
                    r, g, b, a = pixels[x, y]
                    l = (r + g + b) / 3.0 * (100 - sat) / 100.0
                    r = int(r * sat / 100.0 + l)
                    g = int(g * sat / 100.0 + l)
                    b = int(b * sat / 100.0 + l)
                    a = int(a * alpha)
                    pixels[x, y] = (r, g, b, a)
            return self.__pil2surface(im)
        else:
            w = surface.get_width()
            h = surface.get_height()
            new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            ctx = cairo.Context(new)
            ctx.set_source_surface(surface)
            ctx.paint_with_alpha(alpha)
            return new


    def __command_composite(self, surface, bg, fg, opacity="100",
                            xoffset="0", yoffset="0", angle="0"):
        if fg == "self":
            foreground = surface
            if angle and angle != "0":
                foreground = self.__command_rotate(foreground,
                                                   angle, True)
        elif fg in self.temp:
            foreground = self.temp[fg]
            if angle and angle != "0":
                foreground = self.__command_rotate(foreground,
                                                   angle, True)
        elif self.theme.has_surface(fg):
            foreground = self.theme.get_surface(fg)
            if angle and angle != "0":
                foreground = self.__command_rotate(foreground,
                                                   angle, True)
            w = surface.get_width()
            h = surface.get_height()
            foreground = self.__resize_surface(foreground, w, h)
        else:
            logger.warning("theme error: pixmap %s not found" % fg)
            return surface
        if bg == "self":
            background = surface
        elif bg in self.temp:
            w = self.temp[bg].get_width()
            h = self.temp[bg].get_height()
            background = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            ctx = cairo.Context(background)
            ctx.set_source_surface(self.temp[bg])
            ctx.paint()
        elif self.theme.has_surface(bg):
            w = surface.get_width()
            h = surface.get_height()
            background = self.__resize_surface(self.theme.get_surface(bg), w, h)
        else:
            logger.warning("theme error: pixmap %s not found" % bg)
            return surface

        xoffset = self.__get_from_set(xoffset)
        yoffset = self.__get_from_set(yoffset)
        opacity = self.__get_alpha(opacity)
        xoffset = self.__process_size(xoffset)
        yoffset = self.__process_size(yoffset)
        ctx = cairo.Context(background)
        ctx.set_source_surface(foreground, xoffset, yoffset)
        ctx.paint_with_alpha(opacity)
        return background

    def __command_shrink(self, surface, percent="0", pixels="0"):
        w0 = surface.get_width()
        h0 = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w0, h0)
        ctx = cairo.Context(new)

        pixels = self.__get_from_set(pixels)
        percent = self.__get_from_set(percent)
        w = int(((100-int(percent)) * w0)/100)-int(pixels)
        h = int(((100-int(percent)) * h0)/100)-int(pixels)
        shrinked = self.__resize_surface(surface, w, h)
        x = round((w0 - w) / 2.0)
        y = round((h0 - h) / 2.0)
        ctx.set_source_surface(shrinked, x, y)
        ctx.paint()
        del shrinked
        return new

    def __command_rotate(self, surface, angle="0", resize="False"):
        w0 = surface.get_width()
        h0 = surface.get_height()
        # Check if the angle should be taken from a set.
        angle = self.__get_from_set(angle)
        a =  float(angle) / 180 * pi
        if not resize or resize in ("False", "0"):
            w = w0
            h = h0
        else:
            w = abs(int(round(cos(a) * w0 + sin(a) * h0)))
            h = abs(int(round(cos(a) * h0 + sin(a) * w0)))
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)

        ctx.translate(w / 2.0, h / 2.0)
        ctx.rotate(a)
        ctx.translate(-w0 / 2.0, -h0 / 2.0)
        ctx.set_source_surface(surface, 0,0)
        ctx.paint()
        return new

    def __command_correct_size(self, surface):
        if surface is None:
            return
        if self.dockbar_r().orient in ("left", "right"):
            width = self.size
            height = int(self.size * self.ar)
        else:
            width = int(self.size * self.ar)
            height = self.size
        if surface.get_width() == width and surface.get_height() == height:
            return surface
        woffset = round((width - surface.get_width()) / 2.0)
        hoffset = round((height - surface.get_height()) / 2.0)
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface, woffset, hoffset)
        ctx.paint()
        return new

    def __command_glow(self, surface, color, opacity="100"):
        # Adds a glow around the parts of the surface
        # that isn't completely transparent.

        alpha = self.__get_alpha(opacity)
        # Thickness (pixels)
        tk = 1.5


        # Prepare the glow that should be put behind the icon
        cs = self.__command_colorize(surface, color)
        w = surface.get_width()
        h = surface.get_height()
        glow = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(glow)
        tk1 = tk / 2.0
        for x, y in ((-tk1,-tk1), (-tk1,tk1), (tk1,-tk1), (tk1,tk1)):
            ctx.set_source_surface(cs, x, y)
            ctx.paint_with_alpha(0.66)
        for x, y in ((-tk,-tk), (-tk,tk), (tk,-tk), (tk,tk)):
            ctx.set_source_surface(cs, x, y)
            ctx.paint_with_alpha(0.27)

        # Add glow and icon to a new canvas
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(glow)
        ctx.paint_with_alpha(alpha)
        ctx.set_source_surface(surface)
        ctx.paint()
        return new

    def __command_colorize(self, surface, color):
        # Changes the color of all pixels to color.
        # The pixels alpha values are unchanged.

        # Convert color hex-string (format "#FFFFFF")to int r, g, b
        color = self.__get_color(color)
        r = int(color[1:3], 16)/255.0
        g = int(color[3:5], 16)/255.0
        b = int(color[5:7], 16)/255.0

        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_rgba(r,g,b,1.0)
        ctx.mask_surface(surface)
        return new


    def __command_bright(self, surface, strength = None, strenght = None):
        if strength is None and strenght is not None:
            # For compability with older themes.
            strength = strenght
        alpha = self.__get_alpha(strength)
        w = surface.get_width()
        h = surface.get_height()
        # Colorize white
        white = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(white)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        ctx.mask_surface(surface)
        # Apply the white version over the icon
        # with the chosen alpha value
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface)
        ctx.paint()
        ctx.set_source_surface(white)
        ctx.paint_with_alpha(alpha)
        return new

    def __command_alpha_mask(self, surface, mask, angle="0"):
        if mask in self.temp:
            mask = self.temp[mask]
            if angle and angle != "0":
                mask = self.__command_rotate(mask, angle, True)
        elif self.theme.has_surface(mask):
            mask = self.theme.get_surface(mask)
            if angle and angle != "0":
                mask = self.__command_rotate(mask, angle, True)
            w = surface.get_width()
            h = surface.get_height()
            mask = self.__resize_surface(mask, w, h)
        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface)
        ctx.mask_surface(mask)
        return new

#### Format conversions
    def __pixbuf2surface(self, pixbuf):
        if pixbuf is None:
            return None
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
        ctx.paint()
        del pixbuf
        return surface

    def __surface2pil(self, surface):
        w = surface.get_width()
        h = surface.get_height()
        return Image.frombuffer("RGBA", (w, h), surface.get_data().obj,
                                "raw", "BGRA", 0,1)

    def __pil2surface(self, im):
        """Transform a PIL Image into a Cairo ImageSurface."""

        # This function is only supposed to work with little endinan
        # systems. Could that be a problem ever?
        if im.mode != 'RGBA':
            im = im.convert('RGBA')

        s = im.tobytes('raw', 'BGRA')
        a = array.array('B', s)
        dest = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                  im.size[0], im.size[1])
        ctx = cairo.Context(dest)
        non_premult_src_wo_alpha = cairo.ImageSurface.create_for_data(
            a, cairo.FORMAT_RGB24, im.size[0], im.size[1])
        non_premult_src_alpha = cairo.ImageSurface.create_for_data(
            a, cairo.FORMAT_ARGB32, im.size[0], im.size[1])
        ctx.set_source_surface(non_premult_src_wo_alpha)
        ctx.mask_surface(non_premult_src_alpha)
        return dest

    def __process_size(self, size_str):
        us = self.__get_use_size()
        size = 0
        size_str = size_str.replace("-", "+-")
        for s in size_str.split("+"):
            if s=="":
                continue
            if s[-1] == "%":
                # Rounding to whole pixels to avoid uninteded bluring.
                size += round(float(s[:-1]) / 100 * us)
                continue
            if s.endswith("px"):
                s = s[:-2]
            # Here no rounding is done. Let's assume that the
            # theme maker knows what he is doing if he chooses
            # to use decimal pixel values.
            size += float(s)
        return size

    def __get_use_size(self):
        is_vertical = self.dockbar_r().orient in ("left", "right")
        if "aspect_ratio_v" in self.theme.theme["button_pixmap"] or \
           not is_vertical:
            us = self.size * self.ar if self.ar < 1 else self.size
        else:
            # For old vertical themes
            us = self.size
        return us

    def __get_from_set(self, setname):
        s = self.theme.get_from_set(setname, self.orient)
        if s is not None:
            return s
        else:
            return setname

    def __resize_surface(self, surface, w, h):
        im = self.__surface2pil(surface)
        im = im.resize((w, h), Image.ANTIALIAS)
        return self.__pil2surface(im)

    def __command_print_size(self, surface):
        w = surface.get_width()
        h = surface.get_height()
        print(w, h)
        return surface



