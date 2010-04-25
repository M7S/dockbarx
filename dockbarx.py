#!/usr/bin/python


#	Copyright 2008, 2009, 2010 Aleksey Shaferov and Matias Sars
#
#	DockBar is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	DockBar is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with dockbar.  If not, see <http://www.gnu.org/licenses/>.



# A try to fix the random crashes on start-up, no idea if it works.
from time import sleep

try:
    import pygtk
except:
    sleep(5)
    import pygtk
try:
    pygtk.require('2.0')
except:
    sleep(5)
    pygtk.require('2.0')
try:
    import gtk
except:
    sleep(5)
    import gtk
try:
    import gobject
except:
    sleep(5)
    import gobject
try:
    import sys
except:
    sleep(5)
    import sys
try:
    import wnck
except:
    sleep(5)
    import wnck
try:
    import gnomeapplet
except:
    sleep(5)
    import gnomeapplet
try:
    import gconf
except:
    sleep(5)
    import gconf
try:
    import os
except:
    sleep(5)
    import os
try:
    from xdg.DesktopEntry import DesktopEntry
except:
    sleep(5)
    from xdg.DesktopEntry import DesktopEntry
try:
    import dbus
except:
    sleep(5)
    import dbus
try:
    import pango
except:
    sleep(5)
    import pango
try:
    from cStringIO import StringIO
except:
    sleep(5)
    from cStringIO import StringIO
try:
    from tarfile import open as taropen
except:
    sleep(5)
    from tarfile import open as taropen
try:
    from xml.sax import make_parser
except:
    sleep(5)
    from xml.sax import make_parser
try:
    from xml.sax.handler import ContentHandler
except:
    sleep(5)
    from xml.sax.handler import ContentHandler
try:
    from math import pi
except:
    sleep(5)
    from math import pi
try:
    import cairo
except:
    sleep(5)
    import cairo
try:
    from time import time
except:
    sleep(5)
    from time import time
try:
    import gio
except:
    sleep(5)
    import gio


import Image
import array

import gc
gc.enable()

try:
    import ctypes
    libgdk = ctypes.cdll.LoadLibrary("libgdk-x11-2.0.so")
    libX11 = ctypes.cdll.LoadLibrary("libX11.so")
    libXcomposite = ctypes.cdll.LoadLibrary("libXcomposite.so")
except:
    libgdk = None
    libX11 = None
    libXcomposite = None


VERSION = 'x.0.24.1-1'

TARGET_TYPE_GROUPBUTTON = 134 # Randomly chosen number, is it used anymore?

GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = '/apps/dockbarx'

BUS = dbus.SessionBus()


DEFAULT_SETTINGS = {  "theme": "default",
                      "groupbutton_attention_notification_type": "red",
                      "workspace_behavior": "switch",
                      "popup_delay": 250,
                      "popup_align": "center",
                      "no_popup_for_one_window": False,
                      "show_only_current_desktop": True,
                      "preview": False,
                      "remember_previews": False,

                      "select_one_window": "select or minimize window",
                      "select_multiple_windows": "select all",

                      "opacify": False,
                      "opacify_group": False,
                      "opacify_alpha": 11,

                      "separate_wine_apps": True,
                      "separate_ooo_apps": True,

                      "groupbutton_left_click_action":"select or minimize group",
                      "groupbutton_shift_and_left_click_action":"launch application",
                      "groupbutton_middle_click_action":"close all windows",
                      "groupbutton_shift_and_middle_click_action": "no action",
                      "groupbutton_right_click_action": "show menu",
                      "groupbutton_shift_and_right_click_action": "no action",
                      "groupbutton_scroll_up": "select next window",
                      "groupbutton_scroll_down": "select previous window",
                      "groupbutton_left_click_double": False,
                      "groupbutton_shift_and_left_click_double": False,
                      "groupbutton_middle_click_double": True,
                      "groupbutton_shift_and_middle_click_double": False,
                      "groupbutton_right_click_double": False,
                      "groupbutton_shift_and_right_click_double": False,
                      "windowbutton_left_click_action":"select or minimize window",
                      "windowbutton_shift_and_left_click_action":"no action",
                      "windowbutton_middle_click_action":"close window",
                      "windowbutton_shift_and_middle_click_action": "no action",
                      "windowbutton_right_click_action": "show menu",
                      "windowbutton_shift_and_right_click_action": "no action",
                      "windowbutton_scroll_up": "shade window",
                      "windowbutton_scroll_down": "unshade window" }
settings = DEFAULT_SETTINGS.copy()

DEFAULT_COLORS={
                      "color1": "#333333",
                      "color1_alpha": 170,
                      "color2": "#FFFFFF",
                      "color3": "#FFFF75",
                      "color4": "#9C9C9C",

                      "color5": "#FFFF75",
                      "color5_alpha": 160,
                      "color6": "#000000",
                      "color7": "#000000",
                      "color8": "#000000",

               }
colors={}


def compiz_call(obj_path, func_name, *args):
    # Returns a compiz function call.
    # No errors are dealt with here,
    # error handling are left to the calling function.
    path = '/org/freedesktop/compiz'
    if obj_path:
        path += '/' + obj_path
    obj = BUS.get_object('org.freedesktop.compiz', path)
    iface = dbus.Interface(obj, 'org.freedesktop.compiz')
    func = getattr(iface, func_name)
    if func:
        return func(*args)
    return None


class ODict():
    """An ordered dictionary.

    Has only the most needed functions of a dict, not all."""
    def __init__(self, d=[]):
        if not type(d) in (list, tuple):
            raise TypeError('The argument has to be a list or a tuple or nothing.')
        self.list = []
        for t in d:
            if not type(d) in (list, tuple):
                raise ValueError('Every item of the list has to be a list or a tuple.')
            if not len(t) == 2:
                raise ValueError('Every tuple in the list needs to be two items long.')
            self.list.append(t)

    def __getitem__(self, key):
        for t in self.list:
            if t[0] == key:
                return t[1]

    def __setitem__(self, key, value):
        t = (key, value)
        self.list.append(t)

    def __contains__(self, key):
        for t in self.list:
            if t[0] == key:
                return True
        else:
            return False

    def __iter__(self):
        return self.keys().__iter__()

    def __eq__(self, x):
        if type(x) == dict:
            d = {}
            for t in self.list:
                d[t[0]] = t[1]
            return (d == x)
        elif x.__class__ == self.__class__:
            return (self.list == x.list)
        else:
            return (self.list == x)

    def __len__(self):
        return len(self.list)

    def values(self):
        values = []
        for t in self.list:
            values.append(t[1])
        return values

    def keys(self):
        keys = []
        for t in self.list:
            keys.append(t[0])
        return keys

    def items(self):
        return self.list

    def add_at_index(self, index, key, value):
        t = (key, value)
        self.list.insert(index, t)

    def get_index(self, key):
        for t in self.list:
            if t[0] == key:
                return self.list.index(t)

    def move(self, key, index):
        for t in self.list:
            if key == t[0]:
                self.list.remove(t)
                self.list.insert(index, t)

    def remove(self, key):
        for t in self.list:
            if key == t[0]:
                self.list.remove(t)

    def has_key(self, key):
        for t in self.list:
            if key == t[0]:
                return True
        else:
            return False


class ThemeHandler(ContentHandler):
    """Reads the xml-file into a ODict"""
    def __init__(self):
        self.dict = ODict()
        self.name = None
        self.nested_contents = []
        self.nested_contents.append(self.dict)
        self.nested_attributes = []

    def startElement(self, name, attrs):
        name = name.lower().encode()
        if name == 'theme':
            for attr in attrs.keys():
                if attr.lower() == 'name':
                    self.name = attrs[attr]
            return
        # Add all attributes to a dictionary
        d = {}
        for attr in attrs.keys():
            # make sure that all text is in lower
            d[attr.encode().lower()] = attrs[attr].encode().lower()
        # Add a ODict to the dictionary in which all
        # content will be put.
        d['content'] = ODict()
        self.nested_contents[-1][name] = d
        # Append content ODict to the list so that it
        # next element will be put there.
        self.nested_contents.append(d['content'])

        self.nested_attributes.append(d)

    def endElement(self, name):
        if name == 'theme':
            return
        # Pop the last element of nested_contents
        # so that the new elements won't show up
        # as a content to the ended element.
        if len(self.nested_contents)>1:
            self.nested_contents.pop()
        # Remove Content Odict if the element
        # had no content.
        d = self.nested_attributes.pop()
        if d['content'].keys() == []:
                d.pop('content')

    def get_dict(self):
        return self.dict

    def get_name(self):
        return self.name

class Theme():
    @staticmethod
    def check(path_to_tar):
        #TODO: Optimize this
        tar = taropen(path_to_tar)
        config = tar.extractfile('config')
        parser = make_parser()
        theme_handler = ThemeHandler()
        try:
            parser.setContentHandler(theme_handler)
            parser.parse(config)
        except:
            config.close()
            tar.close()
            raise
        config.close()
        tar.close()
        return theme_handler.get_name()

    def __init__(self, path_to_tar):
        tar = taropen(path_to_tar)
        config = tar.extractfile('config')

        # Parse
        parser = make_parser()
        theme_handler = ThemeHandler()
        parser.setContentHandler(theme_handler)
        parser.parse(config)
        self.theme = theme_handler.get_dict()

        # Name
        self.name = theme_handler.get_name()

        # Pixmaps
        self.surfaces = {}
        pixmaps = {}
        if self.theme.has_key('pixmaps'):
            pixmaps = self.theme['pixmaps']['content']
        for (type, d) in pixmaps.items():
            if type == 'pixmap_from_file':
                self.surfaces[d['name']] = self.load_surface(tar, d['file'])

        # Colors
        self.color_names = {}
        self.default_colors = {}
        self.default_alphas = {}
        colors = {}
        if self.theme.has_key('colors'):
            colors = self.theme['colors']['content']
        for i in range(1, 9):
            c = 'color%s'%i
            if colors.has_key(c):
                d = colors[c]
                if d.has_key('name'):
                    self.color_names[c] = d['name']
                if d.has_key('default'):
                    if self.test_color(d['default']):
                        self.default_colors[c] = d['default']
                    else:
                        print 'Theme error: %s\'s default for theme %s cannot be read.'%(c, self.name)
                        print 'A default color should start with an "#" and be followed by six hex-digits, ' + \
                              'for example "#FF13A2".'
                if d.has_key('opacity'):
                    alpha = d['opacity']
                    if self.test_alpha(alpha):
                        self.default_alphas[c] = alpha
                    else:
                        print 'Theme error: %s\'s opacity for theme %s cannot be read.'%(c, self.name)
                        print 'The opacity should be a number ("0"-"100") or the words "not used".'

        config.close()
        tar.close()

    def print_dict(self, d, indent=""):
        for key in d.keys():
            if key == 'content' or type(d[key]) == dict:
                print "%s%s={"%(indent,key)
                self.print_dict(d[key], indent+"   ")
                print "%s}"%indent
            else:
                print '%s%s = %s'%(indent,key,d[key])

    def load_pixbuf(self, tar, name):
        f = tar.extractfile('pixmaps/'+name)
        buffer=f.read()
        pixbuf_loader=gtk.gdk.PixbufLoader()
        pixbuf_loader.write(buffer)
        pixbuf_loader.close()
        f.close()
        pixbuf=pixbuf_loader.get_pixbuf()
        return pixbuf

    def load_surface(self, tar, name):
        f = tar.extractfile('pixmaps/'+name)
        surface = cairo.ImageSurface.create_from_png(f)
        f.close()
        return surface

    def has_surface(self, name):
        if name in self.surfaces:
            return True
        else:
            return False

    def get_surface(self, name):
        return self.surfaces[name]

    def get_icon_dict(self):
        return self.theme['button_pixmap']['content']

    def get_name(self):
        return self.name

    def get_gap(self):
        return int(self.theme['button_pixmap'].get('gap', 0))

    def get_windows_cnt(self):
        return int(self.theme['button_pixmap'].get('windows_cnt', 1))

    def get_aspect_ratio(self):
        ar = self.theme['button_pixmap'].get('aspect_ratio', "1")
        l = ar.split('/',1)
        if len(l) == 2:
            ar = float(l[0])/float(l[1])
        else:
            ar = float(ar)
        return ar

    def get_default_colors(self):
        return self.default_colors

    def get_default_alphas(self):
        return self.default_alphas

    def get_color_names(self):
        return self.color_names

    def test_color(self, color):
        if len(color) != 7:
            return False
        try:
            t = int(color[1:], 16)
        except:
            return False
        return True

    def test_alpha(self, alpha):
        if 'no' in alpha:
            return True
        try:
            t = int(alpha)
        except:
            return False
        if t<0 or t>100:
            return False
        return True

    def remove(self):
        del self.color_names
        del self.default_colors
        del self.default_alphas
        del self.surfaces

class IconFactory():
    """IconFactory takes care of finding the right icon for a program and prepares the cairo surface."""
    icon_theme = gtk.icon_theme_get_default()
    # Constants
    # Icon types
    SOME_MINIMIZED = 1<<4
    ALL_MINIMIZED = 1<<5
    LAUNCHER = 1<<6
    # Icon effects
    MOUSE_OVER = 1<<7
    NEEDS_ATTENTION = 1<<8
    BLINK  = 1<<9
    # ACTIVE_WINDOW
    ACTIVE = 1<<10
    LAUNCH_EFFECT = 1<<11
    # Double width/height icons for drag and drop situations.
    DRAG_DROPP = 1<<12
    TYPE_DICT = {'some_minimized':SOME_MINIMIZED,
                 'all_minimized':ALL_MINIMIZED,
                 'launcher':LAUNCHER,
                 'mouse_over':MOUSE_OVER,
                 'needs_attention':NEEDS_ATTENTION,
                 'blink':BLINK,
                 'active':ACTIVE,
                 'launching':LAUNCH_EFFECT}

    def __init__(self, dockbar, class_group=None, launcher=None, app=None, identifier=None):
        self.dockbar = dockbar
        self.app = app
        self.launcher = launcher
        self.identifier = identifier
        if self.launcher and self.launcher.app:
            self.app = self.launcher.app
            self.launcher = None
        self.class_group = class_group

        self.size = 0

        self.icon = None
        self.surfaces = None

        self.average_color = None

        self.max_win_nr = self.dockbar.theme.get_windows_cnt()

    def remove(self):
        del self.app
        del self.launcher
        del self.class_group
        del self.icon
        del self.surfaces
        del self.dockbar

    def remove_launcher(self, class_group = None, app = None):
        self.launcher = None
        self.class_group = class_group
        self.app = app
        self.surfaces = {}
        del self.icon
        self.icon = None


    def set_size(self, size):
        self.size = size
        self.surfaces = {}
        self.average_color = None

    def get_size(self, size):
        return self.size

    def reset_surfaces(self):
        self.surfaces = {}
        self.average_color = None


    def surface_update(self, type = 0):
        # Checks if the requested pixbuf is already drawn and returns it if it is.
        # Othervice the surface is drawn, saved and returned.
        self.win_nr = type & 15
        if self.win_nr > self.max_win_nr:
            type = (type - self.win_nr) | self.max_win_nr
            self.win_nr = self.max_win_nr
        self.temp = {}
        if type in self.surfaces:
            return self.surfaces[type]
        surface = None
        commands = self.dockbar.theme.get_icon_dict()
        self.ar = self.dockbar.theme.get_aspect_ratio()
        self.type = type
        for command, args in commands.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                surface = f(surface, **args)
        # Todo: add size correction.
        if type & self.DRAG_DROPP:
            surface = self.dd_highlight(surface, self.dockbar.orient)
        self.surfaces[type] = surface
        del self.temp
        gc.collect()
        return surface


    def dd_highlight(self, surface, direction = 'h'):
        w = surface.get_width()
        h = surface.get_height()
        # Make a background almost twice as wide or high
        # as the surface depending on panel orientation.
        if direction == 'v':
            h = h + 4
        else:
            w = w + 4
        bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(bg)

        # Put arrow pointing to the empty part on it.
        if direction == 'v':
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


        # And put the surface on the left/upper half of it.
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint()
        return bg

    def get_color(self, color):
        if color == "active_color":
            color = 'color5'
        if color in ['color%s'%i for i in range(1, 9)]:
            color = colors[color]
        if color == "icon_average":
            color = self.get_average_color()
        else:
            try:
                if len(color) != 7:
                    raise ValueError('The string has the wrong lenght')
                t = int(color[1:], 16)
            except:
                print "Theme error: the color attribute for a theme command should be a six" + \
                      " digit hex string eg. \"#FFFFFF\" or the a dockbarx color (\"color1\"-\"color8\")."
                color = "#000000"
        return color

    def get_alpha(self, alpha):
        # Transparency
        if alpha == "active_opacity":
            # For backwards compability
            alpha = "color5"

        for i in range(1, 9):
            if alpha in ('color%s'%i, 'opacity%s'%i):
                if colors.has_key('color%s_alpha'%i):
                    a = float(colors['color%s_alpha'%i])/255
                else:
                    print "Theme error: The theme has no opacity option for color%s."%i
                    a = 1.0
                break
        else:
            try:
                a = float(alpha)/100
                if a > 1.0 or a < 0:
                    raise
            except:
                print "Theme error: The opacity attribute of a theme command should be a number" + \
                      " between \"0\" and \"100\" or \"color1\" to \"color8\"."
                a = 1.0
        return a

    def get_average_color(self):
        if self.average_color != None:
            return self.average_color
        r = 0
        b = 0
        g = 0
        i = 0
        pb = self.surface2pixbuf(self.icon)
        for row in pb.get_pixels_array():
            for pix in row:
                if pix[3] > 30:
                    i += 1
                    r += pix[0]
                    g += pix[1]
                    b += pix[2]
        if i > 0:
            r = int(float(r) / i + 0.5)
            g = int(float(g) / i + 0.5)
            b = int(float(b) / i + 0.5)
        r = ("0%s"%hex(r)[2:])[-2:]
        g = ("0%s"%hex(g)[2:])[-2:]
        b = ("0%s"%hex(b)[2:])[-2:]
        self.average_color = "#"+r+g+b
        del pb
        return self.average_color


    #### Flow commands
    def command_if(self, surface, type=None, windows=None, size=None, content=None):
        if content == None:
            return surface
        # TODO: complete this
##        l = []
##        splits = ['!', '(', ')', '&', '|']
##        for c in type:
##            if c in splits:
##                l.append(c)
##            elif l[-1] in splits:
##                l.append(c)
##            elif not l:
##                l.append(c)
##            else:
##                l[-1] += c
        # Check if the type condition is satisfied
        if type != None:
            negation = False
            if type[0] == "!" :
                type = type[1:]
                negation = True
            is_type = bool(type in self.TYPE_DICT \
                      and self.type & self.TYPE_DICT[type])
            if not (is_type ^ negation):
                return surface

        #Check if the window number condition is satisfied
        if windows != None:
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
                print 'Theme Error: The windows attribute of ' + \
                      'an <if> statement can\'t look like this:' + \
                      ' "%s". See Theming HOWTO for more information'%windows
                return surface
            if len(l) == 1:
                if not ((l[0] == self.win_nr) ^ negation):
                    return surface
            else:
                if not ((l[0]<=self.win_nr and self.win_nr<=l[1]) ^ negation):
                    return surface

        #Check if the icon size condition is satisfied
        if size != None:
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
                print 'Theme Error: The size attribute of ' + \
                      'an <if> statement can\'t look like this:' + \
                      ' "%s". See Theming HOWTO for more information'%size
                return surface
            if len(l) == 1:
                if not ((l[0] == self.win_nr) ^ negation):
                    return surface
            else:
                if not ((l[0]<=self.size and self.size<=l[1]) ^ negation):
                    return surface

        # All tests passed, proceed.
        for command, args in content.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                surface = f(surface, **args)
        return surface

    def command_pixmap_from_self(self, surface, name, content=None):
        if not name:
            print "Theme Error: no name given for pixmap_from_self"
            raise Exeption
        w = int(surface.get_width())
        h = int(surface.get_height())
        self.temp[name] = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(self.temp[name])
        ctx.set_source_surface(surface)
        ctx.paint()
        if content == None:
            return surface
        for command,args in content.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                self.temp[name] = f(self.temp[name], **args)
        return surface

    def command_pixmap(self, surface, name, content=None, size=None):
        if size != None:
            # TODO: Fix for different height and width
            w = h = self.size + int(size)
        elif surface == None:
            w = h = self.size
        else:
            w = surface.get_width()
            h = surface.get_height()
        self.temp[name] = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        if content == None:
            return surface
        for command,args in content.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                self.temp[name] = f(self.temp[name], **args)
        return surface


    #### Get icon
    def command_get_icon(self,surface=None, size=0):
        size = int(size)
        if size < 0:
            size = self.size + size
        else:
            size = self.size
        if self.icon \
        and self.icon.get_width() == size \
        and self.icon.get_height() == size:
            return self.icon
        del self.icon
        pb = self.find_icon_pixbuf(size)
        if pb.get_width() != pb.get_height():
            if pb.get_width() < pb.get_height():
                h = size
                w = pb.get_width() * size/pb.get_height()
            elif pb.get_width() > pb.get_height():
                w = size
                h = pb.get_height() * size/pb.get_width()
            self.icon = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            ctx = gtk.gdk.CairoContext(cairo.Context(self.icon))
            pbs = pb.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
            woffset = int(float(size - w) / 2 + 0.5)
            hoffset = int(float(size - h) / 2 + 0.5)
##            pb.composite(background, woffset, hoffset, w, h, woffset, hoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
##            pb = background
            ctx.set_source_pixbuf(pb, woffset, hoffset)
            ctx.paint()
            del pb
            del pbs
        elif pb.get_width() != size:
            pbs = pb.scale_simple(size, size, gtk.gdk.INTERP_BILINEAR)
            self.icon = self.pixbuf2surface(pbs)
            del pb
            del pbs
        else:
            self.icon = self.pixbuf2surface(pb)
            del pb
        return self.icon


    def find_icon_pixbuf(self, size):
        # Returns the icon pixbuf for the program. Uses the following metods:

        # 1) If it is a launcher, return the icon from the launcher's desktopfile
        # 2) Get the icon from the gio app
        # 3) Check if the res_class fits an themed icon.
        # 4) Search in path after a icon matching reclass.
        # 5) Use the mini icon for the class

        pixbuf = None
        icon_name = None
        if self.launcher:
            icon_name = self.launcher.get_icon_name()
            if os.path.isfile(icon_name):
                pixbuf = self.icon_from_file_name(icon_name, size)
                if pixbuf != None:
                    return pixbuf
        elif self.app:
            icon = self.app.get_icon()
            if icon.__class__ == gio.FileIcon:
                if icon.get_file().query_exists(None):
                    pixbuf = self.icon_from_file_name(icon.get_file().get_path(), size)
                    if pixbuf != None:
                        return pixbuf
            elif icon.__class__ == gio.ThemedIcon:
                icon_name = icon.get_names()[0]

        if not icon_name:
            if self.identifier:
                icon_name = self.identifier.lower()
            elif self.class_group:
                icon_name = self.class_group.get_res_class().lower()
            else:
                icon_name = ""

            # Special cases
            if icon_name.startswith("wine__"):
                for win in self.class_group.get_windows():
                    if self.identifier[6:] in win.get_name():
                        return win.get_icon().copy()
                else:
                    return self.class_group.get_icon().copy()
            if icon_name.startswith('openoffice'):
                # Makes sure openoffice gets a themed icon
                icon_name = "ooo-writer"

        if self.icon_theme.has_icon(icon_name):
            return self.icon_theme.load_icon(icon_name,size,0)

        if icon_name[-4:] in (".svg", ".png", ".xpm"):
            if self.icon_theme.has_icon(icon_name[:-4]):
                pixbuf = self.icon_theme.load_icon(icon_name[:-4],size,0)
                if pixbuf != None:
                    return pixbuf

        pixbuf = self.icon_search_in_data_path(icon_name, size)
        if pixbuf != None:
            return pixbuf

        if self.class_group:
            return self.class_group.get_icon().copy()


        # If no pixbuf has been found (can only happen for an unlaunched
        # launcher), make an empty pixbuf and show a warning.
        if self.icon_theme.has_icon('application-default-icon'):
            pixbuf = self.icon_theme.load_icon('application-default-icon',size,0)
        else:
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size,size)
            pixbuf.fill(0x00000000)
        dialog = gtk.MessageDialog(parent=None,
                              flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                              type=gtk.MESSAGE_WARNING,
                              buttons=gtk.BUTTONS_OK,
                              message_format='Cannot load icon for launcher '+ self.launcher.get_identifier()+'.')
        dialog.set_title('DockBarX')
        dialog.run()
        dialog.destroy()
        return pixbuf

    def icon_from_file_name(self, icon_name, icon_size = -1):
        if os.path.isfile(icon_name):
            try:
                return gtk.gdk.pixbuf_new_from_file_at_size(icon_name, -1, icon_size)
            except:
                pass
        return None

    def icon_search_in_data_path(self, icon_name, icon_size):
        data_folders = None

        if os.environ.has_key("XDG_DATA_DIRS"):
            data_folders = os.environ["XDG_DATA_DIRS"]

        if not data_folders:
            data_folders = "/usr/local/share/:/usr/share/"

        for data_folder in data_folders.split(':'):
            #The line below line used datafolders instead of datafolder.
            #I changed it because I suspect it was a bug.
            paths = (os.path.join(data_folder, "pixmaps", icon_name),
                     os.path.join(data_folder, "icons", icon_name))
            for path in paths:
                if os.path.isfile(path):
                    icon = self.icon_from_file_name(path, icon_size)
                    if icon:
                        return icon
        return None


    #### Other commands
    def command_get_pixmap(self, surface, name, size=0):
        if surface == None:
            if self.dockbar.orient == 'h':
                width = int(self.size * ar)
                height = self.size
            else:
                width = self.size
                height = int(self.size * ar)
        else:
            width = surface.get_width()
            height = surface.get_height()
        if self.dockbar.theme.has_surface(name):
            surface = self.resize_surface(self.dockbar.theme.get_surface(name), width, height)
        else:
            print "theme error: pixmap %s not found"%name
        return surface

    def command_fill(self, surface, color, opacity=100):
        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface)
        ctx.paint()

        alpha = self.get_alpha(opacity)
        c = self.get_color(color)
        r = float(int(c[1:3], 16))/255
        g = float(int(c[3:5], 16))/255
        b = float(int(c[5:7], 16))/255
        ctx.set_source_rgba(r, g, b)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint_with_alpha(alpha)
        return new


    def command_combine(self, surface, pix1, pix2, degrees=90):
        # Combines left half of surface with right half of surface2.
        # The transition between the two halves are soft.
        w = surface.get_width()
        h = surface.get_height()
        if pix1=="self":
            p1 = surface
        elif pix1 in self.temp:
            p1 = self.temp[pix1]
        elif self.dockbar.theme.has_surface(pix1):
            w = surface.get_width()
            h = surface.get_height()
            p1 = self.resize_surface(self.dockbar.theme.get_surface(bg), w, h)
        else:
            print "theme error: pixmap %s not found"%pix1
        if pix2=="self":
            p2 = surface
        elif pix2 in self.temp:
            p2 = self.temp[pix2]
        elif self.dockbar.theme.has_surface(pix2):
            w = surface.get_width()
            h = surface.get_height()
            p2 = self.resize_surface(self.dockbar.theme.get_surface(bg), w, h)
        else:
            print "theme error: pixmap %s not found"%pix2

        #TODO: Add degrees
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, p1.get_width(), p1.get_height())
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

    def command_transp_sat(self, surface, opacity=100, saturation=100):
        # Makes the icon desaturized and/or transparent.
        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = gtk.gdk.CairoContext(cairo.Context(new))
        alpha = self.get_alpha(opacity)
        # Todo: Add error check for saturation
        if int(saturation) < 100:
            sio = StringIO()
            surface.write_to_png(sio)
            sio.seek(0)
            loader = gtk.gdk.PixbufLoader()
            loader.write(sio.getvalue())
            loader.close()
            sio.close()
            pixbuf = loader.get_pixbuf()
            saturation = min(1.0, float(saturation)/100)
            pixbuf.saturate_and_pixelate(pixbuf, saturation, False)
            ctx.set_source_pixbuf(pixbuf, 0, 0)
            ctx.paint_with_alpha(alpha)
            del loader
            del sio
            del pixbuf
            gc.collect()
        else:
            ctx.set_source_surface(surface)
            ctx.paint_with_alpha(alpha)
##        icon_transp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
##        icon_transp.fill(0x00000000)
##        pixbuf.composite(icon_transp, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, opacity)
##        icon_transp.saturate_and_pixelate(icon_transp, saturation, False)
        return new

    def command_composite(self, surface, bg, fg, opacity=100, xoffset=0, yoffset=0):
        if fg=="self":
            foreground = surface
        elif fg in self.temp:
            foreground = self.temp[fg]
        elif self.dockbar.theme.has_surface(fg):
            w = surface.get_width()
            h = surface.get_height()
            foreground = self.resize_surface(self.dockbar.theme.get_surface(fg), w, h)
        else:
            print "theme error: pixmap %s not found"%fg
            return surface

        if bg=="self":
            background = surface
        elif bg in self.temp:
            w = self.temp[bg].get_width()
            h = self.temp[bg].get_height()
            background = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            ctx = cairo.Context(background)
            ctx.set_source_surface(self.temp[bg])
            ctx.paint()
        elif self.dockbar.theme.has_surface(bg):
            w = surface.get_width()
            h = surface.get_height()
            background = self.resize_surface(self.dockbar.theme.get_surface(bg), w, h)
        else:
            print "theme error: pixmap %s not found"%bg
            return surface

        opacity = self.get_alpha(opacity)
        xoffset = float(xoffset)
        yoffset = float(yoffset)
        ctx = cairo.Context(background)
        ctx.set_source_surface(foreground, xoffset, yoffset)
        ctx.paint_with_alpha(opacity)
##        if xoffset >= 0:
##            if xoffset + foreground.get_width() > background.get_width():
##                w = foreground.get_width() - xoffset
##            else:
##                w = foreground.get_width()
##        else:
##            w = foreground.get_width() + xoffset
##        if yoffset >= 0:
##            if yoffset + foreground.get_height() > background.get_height():
##                h = foreground.get_height() - yoffset
##
##            else:
##                h = foreground.get_height()
##        else:
##            h = foreground.get_height() + yoffset
##        x = max(xoffset, 0)
##        y = max(yoffset, 0)
##        if w <= 0 or h <=0 or x > background.get_width or y > background.get_height:
##            # Fg is offset out of the picture.
##            return background
##        foreground.composite(background, x, y, w, h, xoffset, yoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, opacity)
##        del surface
##        surface = self.pixbuf2surface(background)
        return background

    def command_shrink(self, surface, percent=0, pixels=0):
##        pixbuf = self.surface2pixbuf(surface)
##        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
##        background.fill(0x00000000)
        w0 = surface.get_width()
        h0 = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w0, h0)
        ctx = cairo.Context(new)

        w = int(((100-int(percent)) * w0)/100)-int(pixels)
        h = int(((100-int(percent)) * h0)/100)-int(pixels)
##        shrinked = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
        shrinked = self.resize_surface(surface, w, h)
        x = int(float(w0 - w) / 2 + 0.5)
        y = int(float(h0 - h) / 2 + 0.5)
        ctx.set_source_surface(shrinked, x, y)
        ctx.paint()
##        pixbuf.composite(background, x, y, w, h, x, y, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
##        del pixbuf
        del shrinked
        return new

    def command_correct_size(self, surface):
        if surface == None:
            return
        if self.dockbar.orient == 'v':
            width = self.size
            height = int(self.size * self.ar)
        else:
            width = int(self.size * self.ar)
            height = self.size
        if surface.get_width() == width and surface.get_height() == height:
            return surface
##        pixbuf = self.surface2pixbuf(surface)
##        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, height)
##        background.fill(0x00000000)
        woffset = int(float(width - surface.get_width()) / 2 + 0.5)
        hoffset = int(float(height - surface.get_height()) / 2 + 0.5)
##        pixbuf.composite(background, woffset, hoffset, pixbuf.get_width(), pixbuf.get_height(), \
##                         woffset, hoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
##        del surface
##        new = self.pixbuf2surface(background)
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface, woffset, hoffset)
        ctx.paint()
        return new

    def command_glow(self, surface, color, opacity=100):
        # Adds a glow around the parts of the surface
        # that isn't completely transparent.

        alpha = self.get_alpha(opacity)
        # Thickness (pixels)
        tk = 1.5


        # Prepare the glow that should be put behind the icon
        cs = self.command_colorize(surface, color)
        w = surface.get_width()
        h = surface.get_height()
        glow = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(glow)
        tk1 = tk/2.0
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

    def command_colorize(self, surface, color):
        # Changes the color of all pixels to color.
        # The pixels alpha values are unchanged.

        # Convert color hex-string (format '#FFFFFF')to int r, g, b
        color = self.get_color(color)
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


    def command_bright(self, surface, strength = None, strenght = None):
##        pixbuf = self.surface2pixbuf(surface)
##        # Makes the pixbuf shift lighter.
        if strength == None and strenght != None:
            # For compability with older themes.
            strength = strenght
##        strength = int(int(strength) * 2.55 + 0.4)
##        pixbuf = pixbuf.copy()
##        for row in pixbuf.get_pixels_array():
##            for pix in row:
##                pix[0] = min(255, int(pix[0]) + strength)
##                pix[1] = min(255, int(pix[1]) + strength)
##                pix[2] = min(255, int(pix[2]) + strength)
##        del surface
##        surface = self.pixbuf2surface(pixbuf)
##        del pixbuf
        alpha = self.get_alpha(strength)
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

    def command_alpha_mask(self, surface, mask):
        if mask in self.temp:
            mask = self.temp[mask]
        elif self.dockbar.theme.has_surface(mask):
            m = self.surface2pixbuf(self.dockbar.theme.get_surface(mask))
            m = m.scale_simple(surface.get_width(), surface.get_height(), gtk.gdk.INTERP_BILINEAR)
            mask = self.pixbuf2surface(m)
        w = surface.get_width()
        h = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(new)
        ctx.set_source_surface(surface)
        ctx.mask_surface(mask)
        return new

#### Format conversions
    def pixbuf2surface(self, pixbuf):
        if pixbuf == None:
            return None
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = gtk.gdk.CairoContext(cairo.Context(surface))
        ctx.set_source_pixbuf(pixbuf, 0, 0)
        ctx.paint()
        del pixbuf
        return surface

    def surface2pixbuf(self, surface):
        if surface == None:
            return None
        sio = StringIO()
        surface.write_to_png(sio)
        sio.seek(0)
        loader = gtk.gdk.PixbufLoader()
        loader.write(sio.getvalue())
        loader.close()
        sio.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf

    def surface2pil(self, surface):
        w = surface.get_width()
        h = surface.get_height()
        return Image.frombuffer("RGBA", (w, h), surface.get_data(), "raw", "RGBA", 0,1)


    def pil2surface(self, im):
        imgd = im.tostring("raw","RGBA",0,1)
        a = array.array('B',imgd)
        w = im.size[0]
        h = im.size[1]
        stride = im.size[0] * 4
        surface = cairo.ImageSurface.create_for_data (a, cairo.FORMAT_ARGB32,
                                                      w, h, stride)
        return surface

    def resize_surface(self, surface, w, h):
        im = self.surface2pil(surface)
        im = im.resize((w, h), Image.ANTIALIAS)
##        pb = self.surface2pixbuf(surface)
##        pbs = pb.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
##        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
##        ctx = gtk.gdk.CairoContext(cairo.Context(s))
##        ctx.set_source_pixbuf(pbs, 0, 0)
##        ctx.paint()
##        del pb
##        del pbs
##        return s
        return self.pil2surface(im)



class CairoButton(gtk.Button):
    """CairoButton is a gtk button with a cairo surface painted over it."""
    __gsignals__ = {'expose-event' : 'override',}
    def __init__(self, surface=None):
        gtk.Button.__init__(self)
        self.surface = surface
        self.connect('delete-event', self.cleanup)

    def update(self, surface):
        a = self.get_allocation()
        self.surface = surface
        if self.window == None:
            # Find out why is window == None sometimes?
            return
        self.window.clear_area(a.x, a.y, a.width, a.height)
        ctx = self.window.cairo_create()
        ctx.rectangle(a.x, a.y, a.width, a.height)
        ctx.clip()
        ctx.set_source_surface(self.surface, a.x, a.y)
        ctx.paint()

    def do_expose_event(self, event):
        if self.surface != None:
            ctx = self.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                           event.area.width, event.area.height)
            ctx.clip()
            a = self.get_allocation()
            ctx.set_source_surface(self.surface, a.x, a.y)
            ctx.paint()
        return

    def cleanup(self, event):
        del self.surface

class CairoPopup():
    """CairoPopup is a transparent popup window with rounded corners"""
    def __init__(self, colormap):
        gtk.widget_push_colormap(colormap)
        self.window = gtk.Window(gtk.WINDOW_POPUP)
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        gtk.widget_pop_colormap()

        self.window.set_app_paintable(1)

        self.window.connect("expose_event", self.expose)


    def expose(self, widget, event):
        self.set_shape_mask()
        w,h = self.window.get_size()
        self.ctx = self.window.window.cairo_create()
        # set a clip region for the expose event, XShape stuff
        self.ctx.save()
        if self.window.is_composited():
            self.ctx.set_source_rgba(1, 1, 1,0)
        else:
            self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.ctx.paint()
        self.ctx.restore()
        self.ctx.rectangle(event.area.x, event.area.y,
                           event.area.width, event.area.height)
        self.ctx.clip()
        self.draw_frame(self.ctx, w, h)

    def set_shape_mask(self):
        # Set window shape from alpha mask of background image
        w,h = self.window.get_size()
        if w==0: w = 800
        if h==0: h = 600
        pixmap = gtk.gdk.Pixmap (None, w, h, 1)
        ctx = pixmap.cairo_create()
        ctx.set_source_rgba(1, 1, 1,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()

        r = 6
        lt = 0.5
        rt = w - 0.5
        up = 0.5
        dn = h - 0.5
        ctx.move_to(lt, up + r)
        ctx.arc(lt + r, up + r, r, -pi, -pi/2)
        ctx.arc(rt - r, up + r, r, -pi/2, 0)
        ctx.arc(rt - r, dn - r, r, 0, pi/2)
        ctx.arc(lt + r, dn - r, r, pi/2, pi)
        ctx.close_path()

        if self.window.is_composited():
            ctx.set_source_rgba(1, 1, 1, 1)
        else:
            ctx.set_source_rgb(1, 1, 1)
        ctx.fill()

        if self.window.is_composited():
            self.window.window.shape_combine_mask(None, 0, 0)
            ctx.rectangle(0,0,w,h)
            ctx.fill()
            self.window.input_shape_combine_mask(pixmap,0,0)
        else:
            self.window.shape_combine_mask(pixmap, 0, 0)
        del pixmap

    def draw_frame(self, ctx, w, h):
        r = 6
        color = colors['color1']
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255

        alpha= float(colors['color1_alpha']) / 255

        lt = 0.5
        rt = w - 0.5
        up = 0.5
        dn = h - 0.5
        ctx.move_to(lt, up + r)
        ctx.arc(lt + r, up + r, r, -pi, -pi/2)
        ctx.arc(rt - r, up + r, r, -pi/2, 0)
        ctx.arc(rt - r, dn - r, r, 0, pi/2)
        ctx.arc(lt + r, dn - r, r, pi/2, pi)
        ctx.close_path()

        if self.window.is_composited():
            ctx.set_source_rgba(red, green, blue, alpha)
        else:
            ctx.set_source_rgb(red, green, blue)
        ctx.fill_preserve()
        if self.window.is_composited():
            ctx.set_source_rgba(0.0, 0.0, 0.0, alpha)
        else:
            ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.set_line_width(1)
        ctx.stroke()

class CairoWindowButton(gtk.Button):
    """CairoButton is a gtk button with a cairo surface painted over it."""
    __gsignals__ = {'expose-event' : 'override',}
    def __init__(self):
        gtk.Button.__init__(self)

    def do_expose_event(self, event):
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                       event.area.width, event.area.height)
        ctx.clip()
        a = self.get_allocation()
        mx , my = self.get_pointer()
        if mx >= 0 and mx < a.width and my >= 0 and my < a.height:
            self.draw_frame(ctx, a.x, a.y, a.width, a.height)
        self.get_child().send_expose(event)
        return

    def draw_frame(self, ctx, x, y, w, h):
        r = 6
        bg = 0.2
        color = colors['color1']
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255

        alpha= float(colors['color1_alpha']) / 255
        lt = x + 0.5
        rt = x + w - 0.5
        up = y + 0.5
        dn = y + h - 0.5
        ctx.move_to(lt, up + r)
        ctx.arc(lt + r, up + r, r, -pi, -pi/2)
        ctx.arc(rt - r, up + r, r, -pi/2, 0)
        ctx.arc(rt - r, dn - r, r, 0, pi/2)
        ctx.arc(lt + r, dn - r, r, pi/2, pi)
        ctx.close_path()

        ctx.set_source_rgba(red, green, blue, alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.0, 0.0, 0.0, alpha)
        ctx.set_line_width(1)
        ctx.stroke()

class Launcher():
    def __init__(self, identifier, path, dockbar=None):
        self.identifier = identifier
        self.path = path
        self.app = None
        if path[:4] == "gio:":
            if path[4:] in dockbar.apps_by_id:
                self.app = dockbar.apps_by_id[path[4:]]
            else:
                raise Exception("gio-app "+path[4:]+" doesn't exist.")
        elif os.path.exists(path):
            self.desktop_entry = DesktopEntry(path)
        else:
            raise Exception("DesktopFile "+path+" doesn't exist.")


    def get_identifier(self):
        return self.identifier

    def set_identifier(self, identifier):
        self.identifier = identifier

    def get_path(self):
        return self.path

    def get_icon_name(self):
        if self.app:
            return self.app.get_icon()
        else:
            return self.desktop_entry.getIcon()

    def get_entry_name(self):
        if self.app:
            return self.app.get_name()
        else:
            return self.desktop_entry.getName()

    def get_executable(self):
        if self.app:
            return self.app.get_executable()

        exe = self.desktop_entry.getExec()
        l= exe.split()
        if l[0] in ('sudo','gksudo', 'gksu',
                    'java','mono',
                    'ruby','python'):
            exe = l[1]
        else:
            exe = l[0]
        exe = exe[exe.rfind('/')+1:]
        if exe.find('.')>-1:
            exe = exe[:exe.rfind('.')]
        return exe

    def launch(self):
        os.chdir(os.path.expanduser('~'))
        if self.app:
            print "Executing", self.app.get_name()

            return self.app.launch(None, None)
        else:
            print 'Executing ' + self.desktop_entry.getExec()
            self.execute(self.desktop_entry.getExec())

    def remove_args(self, stringToExecute):
        specials = ["%f","%F","%u","%U","%d","%D","%n","%N","%i","%c","%k","%v","%m","%M", "-caption","--view", "\"%c\""]
        return [element for element in stringToExecute.split() if element not in specials]

    def execute(self, command):
        command = self.remove_args(command)
        if os.path.isdir(command[0]):
            command = "xdg-open '" + " ".join(command) + "' &"
        else:
            command = "/bin/sh -c '" + " ".join(command) + "' &"
        os.system(command)


class GroupList():
    """GroupList contains a list with touples containing identifier, group button and launcherpath."""
    def __init__(self):
        self.list = []

##    def __del__(self):
##        self.list = None

    def __getitem__(self, name):
        return self.get_group(name)

    def __setitem__(self, identifier, group_button):
        self.add_group(identifier, group_button)

    def __contains__(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return True
        for t in self.list:
            if t[2] == name:
                return True
        return False

    def __iter__(self):
        return self.get_identifiers().__iter__()

    def add_group(self, identifier, group_button, path_to_launcher=None, index=None):
        t = (identifier, group_button, path_to_launcher)
        if index:
            self.list.insert(index, t)
        else:
            self.list.append(t)

    def get_group(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return t[1]
        for t in self.list:
            if t[2] == name:
                return t[1]

    def get_launcher_path(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return t[2]
            if t[2] == name:
                return t[2]

    def set_launcher_path(self, identifier, path):
        if not identifier:
            return
        for t in self.list:
            if t[0] == identifier:
                n = [t[0], t[1], path]
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                return True

    def set_identifier(self, path, identifier):
        for t in self.list:
            if t[2] == path:
                n = (identifier, t[1], t[2])
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                n[1].identifier_changed(identifier)
                return True

    def get_groups(self):
        grouplist = []
        for t in self.list:
            grouplist.append(t[1])
        return grouplist

    def get_identifiers(self):
        namelist = []
        for t in self.list:
            if t[0]:
                namelist.append(t[0])
        return namelist

    def get_undefined_launchers(self):
        namelist = []
        for t in self.list:
            if t[0] == None:
                namelist.append(t[2])
        return namelist

    def get_identifiers_or_paths(self):
        namelist = []
        for t in self.list:
            if t[0] == None:
                namelist.append(t[2])
            else:
                namelist.append(t[0])
        return namelist

    def get_non_launcher_names(self):
        #Get a list of names of all buttons without launchers
        namelist = []
        for t in self.list:
            if not t[2]:
                namelist.append(t[0])
        return namelist

    def get_index(self, name):
        if not name:
            return
        for t in self.list:
            if t[0]==name:
                return self.list.index(t)
        for t in self.list:
            if t[2]==name:
                return self.list.index(t)

    def move(self, name, index):
        if not name:
            return
        for t in self.list:
            if name == t[0]:
                self.list.remove(t)
                self.list.insert(index, t)
                return True
        for t in self.list:
            if name == t[2]:
                self.list.remove(t)
                self.list.insert(index, t)
                return True

    def remove_launcher(self, identifier):
        if not identifier:
            return
        for t in self.list:
            if identifier == t[0]:
                n = (t[0], t[1], None)
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                return True

    def remove(self,name):
        if not name:
            return
        for t in self.list:
            if name == t[0]:
                self.list.remove(t)
                return True
        for t in self.list:
            if name == t[2] and not t[0]:
                self.list.remove(t)
                return True

    def get_launchers_list(self):
        #Returns a list of name and launcher paths tuples
        launcherslist = []
        for t in self.list:
            #if launcher exist
            if t[2]:
                launchertuple = (t[0],t[2])
                launcherslist.append(launchertuple)
        return launcherslist


class WindowButton():
    """WindowButton takes care of a window, shows up an icon and name in popup window."""
    def __init__(self,window,groupbutton):
        self.groupbutton = groupbutton
        self.dockbar = groupbutton.dockbar
        self.screen = self.groupbutton.screen
        self.preview = False
        self.name = window.get_name()
        self.window = window
        self.locked = False
        self.is_active_window = False
        self.needs_attention = False
        self.opacified = False
        self.button_pressed = False

        self.window_button = CairoWindowButton()
        self.label = gtk.Label()
        self.label.set_alignment(0, 0.5)
        self.on_window_name_changed(self.window)

        if window.needs_attention():
            self.needs_attention = True
            self.groupbutton.needs_attention_changed()

        self.window_button_icon = gtk.Image()
        self.on_window_icon_changed(window)
        hbox = gtk.HBox()
        hbox.pack_start(self.window_button_icon, False, padding = 2)
        hbox.pack_start(self.label, True, True)
        if settings["preview"]:
            self.preview = True
            vbox = gtk.VBox()
            vbox.pack_start(hbox, False)
            self.preview_image =  gtk.Image()
            vbox.pack_start(self.preview_image, True, True, padding = 4)
            self.window_button.add(vbox)
            # Fixed with of self.label.
            self.label.set_ellipsize(pango.ELLIPSIZE_END)
        else:
            self.window_button.add(hbox)


        self.update_label_state()

        groupbutton.winlist.pack_start(self.window_button,True)

        #--- Events
        self.window_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.window_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.window_button.connect("button-press-event",self.on_window_button_press_event)
        self.window_button.connect("button-release-event",self.on_window_button_release_event)
        self.window_button.connect("scroll-event",self.on_window_button_scroll_event)
        self.state_changed_event = self.window.connect("state-changed",self.on_window_state_changed)
        self.icon_changed_event = self.window.connect("icon-changed",self.on_window_icon_changed)
        self.name_changed_event = self.window.connect("name-changed",self.on_window_name_changed)

        #--- D'n'D
        self.window_button.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT, [], 0)
        self.window_button.connect("drag_motion", self.on_button_drag_motion)
        self.window_button.connect("drag_leave", self.on_button_drag_leave)
        self.button_drag_entered = False
        self.dnd_select_window = None

        #--- Minimization target:
        self.sid1 = self.groupbutton.connect('set-icongeo-win',self.on_set_icongeo_win)
        self.sid2 = self.groupbutton.connect('set-icongeo-grp',self.on_set_icongeo_grp)
        self.sid3 = self.groupbutton.dockbar.connect('db-move',self.on_db_move)
        self.sid4 = self.groupbutton.connect('set-icongeo-delay',self.on_set_icongeo_delay)
        self.on_set_icongeo_grp()


    def set_button_active(self, mode):
        """Use set_button_active to tell WindowButton that it's window is the active one."""
        self.is_active_window = mode
        self.update_label_state()

    def update_label_state(self, mouseover=False):
        """Updates the style of the label according to window state."""
        attr_list = pango.AttrList()
##        if mouseover:
##            attr_list.insert(pango.AttrUnderline(pango.UNDERLINE_SINGLE, 0, 50))
        if self.needs_attention:
            attr_list.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, 50))
        if self.is_active_window:
            color = colors['color3']
        elif self.window.is_minimized():
            color = colors['color4']
        else:
            color = colors['color2']
        # color is a hex-string (like '#FFFFFF').
        r = int(color[1:3], 16)*256
        g = int(color[3:5], 16)*256
        b = int(color[5:7], 16)*256
        attr_list.insert(pango.AttrForeground(r, g, b, 0, 50))
        self.label.set_attributes(attr_list)



    def is_on_current_desktop(self):
        if (self.window.get_workspace() == None \
        or self.screen.get_active_workspace() == self.window.get_workspace()) \
        and self.window.is_in_viewport(self.screen.get_active_workspace()):
            return True
        else:
            return False

    def del_button(self):
        self.window_button.destroy()
        self.groupbutton.disconnect(self.sid1)
        self.groupbutton.disconnect(self.sid2)
        self.groupbutton.disconnect(self.sid4)
        self.groupbutton.dockbar.disconnect(self.sid3)
        self.window.disconnect(self.state_changed_event)
        self.window.disconnect(self.icon_changed_event)
        self.window.disconnect(self.name_changed_event)
        del self.icon
        del self.icon_locked
        del self.icon_transp
        del self.screen
        del self.window
        del self.dockbar
        del self.groupbutton

    #### Previews
    def get_screenshot_xcomposite(self, screen, window, size=200):
        ''' Get the window pixmap of window from the X compositor extension, return
            it as a gdk.pixbuf.
        '''
        # Parts of this are ported from Talika (C) 2009-2010 Sinew Software Systems
        if None in [libgdk, libXcomposite, libX11]:
            return None
        display = screen.get_display()
        xdisplay = libgdk.gdk_x11_display_get_xdisplay(hash(display))
        xid = window.get_xid()

        libgdk.gdk_error_trap_push()
        # Call the X function which may cause an error here ...
        p_xid = libXcomposite.XCompositeNameWindowPixmap(xdisplay, xid)
        # Flush the X queue to catch errors now.
        libgdk.gdk_flush()
        errors = libgdk.gdk_error_trap_pop()
        if errors:
            pixmap = None
        else:
            pixmap = gtk.gdk.pixmap_foreign_new_for_display(display, p_xid)
        if not pixmap:
            return None

        depth = pixmap.get_depth()
        if depth <= 24:
            cmap = screen.get_rgb_colormap()
        else:
            cmap = screen.get_rgba_colormap()
        w, h = pixmap.get_size()
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
        pixbuf.get_from_drawable(pixmap, cmap, 0, 0, 0, 0, w, h)

        if w >= h:
            if w > size:
                h = int(h * size/w)
                w = size
        else:
            if h > size:
                w = int(w * size/h)
                h = size
        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)

        del pixmap
        libX11.XFreePixmap(xdisplay, p_xid)
        return pixbuf

    def update_preview(self, size=200):
        if not self.preview:
            return False
        pixbuf = None
        scn = gtk.gdk.screen_get_default()
        if not self.window.is_minimized() and scn.is_composited():
            pixbuf = self.get_screenshot_xcomposite(scn, self.window, size)
        else:
            pixbuf = self.preview_image.get_pixbuf()
        if pixbuf == None:
            pixbuf = self.window.get_icon()
        self.preview_image.set_from_pixbuf(pixbuf)
        self.preview_image.set_size_request(size,size)
        del pixbuf
        gc.collect()

    def clear_preview_image(self):
        if not self.preview:
            return False
        self.preview_image.clear()
        gc.collect()

    #### Windows's Events
    def on_window_state_changed(self, window,changed_mask, new_state):
        try:
            state_minimized = wnck.WINDOW_STATE_MINIMIZED
        except:
            state_minimized = 1 << 0
        if state_minimized & changed_mask & new_state:
            if self.locked:
                self.window_button_icon.set_from_pixbuf(self.icon_locked)
            else:
                self.window_button_icon.set_from_pixbuf(self.icon_transp)
            self.groupbutton.minimized_windows_count+=1
            self.groupbutton.update_state()
            self.update_label_state()
            if self.groupbutton.popup_showing:
                self.update_preview()
        elif state_minimized & changed_mask:
            self.window_button_icon.set_from_pixbuf(self.icon)
            self.groupbutton.minimized_windows_count-=1
            if self.locked:
                self.locked = False
                self.groupbutton.locked_windows_count -= 1
            if self.groupbutton.popup_showing:
                gobject.timeout_add(200, self.update_preview)
            self.groupbutton.update_state()
            self.update_label_state()

        # Check if the window needs attention
        if window.needs_attention() != self.needs_attention:
            self.needs_attention = window.needs_attention()
            self.update_label_state()
            self.groupbutton.needs_attention_changed()

    def on_window_icon_changed(self, window):
        # Creates pixbufs for minimized, locked and normal icons
        # from the window's mini icon and set the one that should
        # be used as window_button_icon according to window state.
        self.icon = window.get_mini_icon()
        pixbuf = self.icon.copy()
        self.icon_transp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        self.icon_transp.fill(0x00000000)
        pixbuf.composite(self.icon_transp, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 190)
        self.icon_transp.saturate_and_pixelate(self.icon_transp, 0.12, False)

        i = gtk.Invisible()
        lock = i.render_icon(gtk.STOCK_DIALOG_AUTHENTICATION,gtk.ICON_SIZE_BUTTON)
        if pixbuf.get_height() != lock.get_height() or pixbuf.get_width() != lock.get_width():
            lock = lock.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        self.icon_locked = self.icon_transp.copy()
        lock.composite(self.icon_locked, 0, 0, lock.get_width(), lock.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)

        if self.locked:
            self.window_button_icon.set_from_pixbuf(self.icon_locked)
        elif window.is_minimized():
            self.window_button_icon.set_from_pixbuf(self.icon_transp)
        else:
            self.window_button_icon.set_from_pixbuf(self.icon)
        del pixbuf
        del lock

    def on_window_name_changed(self, window):
        name = u""+window.get_name()
        # TODO: fix a better way to shorten names.
        if len(name) > 40 and not self.preview:
            name = name[0:37]+"..."
        self.name = name
        self.label.set_label(name)

    #### Grp signals
    def on_set_icongeo_win(self,arg=None):
        if settings["show_only_current_desktop"] \
        and not self.is_on_current_desktop():
            self.window.set_icon_geometry(0, 0, 0, 0)
            return
        alloc = self.window_button.get_allocation()
        w = alloc.width
        h = alloc.height
        x,y = self.window_button.window.get_origin()
        x += alloc.x
        y += alloc.y
        self.window.set_icon_geometry(x, y, w, h)

    def on_set_icongeo_grp(self,arg=None):
        if settings["show_only_current_desktop"] \
        and not self.is_on_current_desktop():
            self.window.set_icon_geometry(0, 0, 0, 0)
            return
        alloc = self.groupbutton.button.get_allocation()
        if self.groupbutton.button.window:
            x,y = self.groupbutton.button.window.get_origin()
            x += alloc.x
            y += alloc.y
            self.window.set_icon_geometry(x,y,alloc.width,alloc.height)

    def on_set_icongeo_delay(self,arg=None):
        # This one is used during popup delay to aviod
        # thumbnails on group buttons.
        if settings["show_only_current_desktop"] \
        and not self.is_on_current_desktop():
            self.window.set_icon_geometry(0, 0, 0, 0)
            return
        alloc = self.groupbutton.button.get_allocation()
        if self.groupbutton.button.window:
            x,y = self.groupbutton.button.window.get_origin()
            x += alloc.x
            y += alloc.y
            if self.dockbar.orient == "h":
                w = alloc.width
                h = 2
                if y<5:
                        # dockbar applet is at top of screen
                        # the area should be below the button
                        y += alloc.height + 1
                else:
                    # the area should be above the button
                    y -= 2
            else:
                w = 2
                h = alloc.height
                if x<5:
                        # dockbar applet is at the left egde of screen
                        # the area should be to the right ofthe button
                        x += alloc.width + 1
                else:
                    # the area should be to the right of the button
                    x -= 2
            self.window.set_icon_geometry(x,y,w,h)

    def on_db_move(self,arg=None):
        self.on_set_icongeo_grp()


    #### Opacify
    def opacify(self):
        # Makes all windows but the one connected to this windowbutton transparent
        if self.dockbar.opacity_values == None:
            try:
                self.dockbar.opacity_values = compiz_call('obs/screen0/opacity_values','get')
            except:
                try:
                    self.dockbar.opacity_values = compiz_call('core/screen0/opacity_values','get')
                except:
                    return
        if self.dockbar.opacity_matches == None:
            try:
                self.dockbar.opacity_matches = compiz_call('obs/screen0/opacity_matches','get')
            except:
                try:
                    self.dockbar.opacity_values = compiz_call('core/screen0/opacity_matches','get')
                except:
                    return
        self.dockbar.opacified = True
        self.opacified = True
        ov = [settings['opacify_alpha']]
        om = ["!(title="+self.window.get_name()+") & !(class=Dockbarx.py)  & (type=Normal | type=Dialog)"]
        try:
            compiz_call('obs/screen0/opacity_values','set', ov)
            compiz_call('obs/screen0/opacity_matches','set', om)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', ov)
                compiz_call('core/screen0/opacity_matches','set', om)
            except:
                return

    def opacify_request(self):
        if self.window.is_minimized():
            return False
        # if self.button_pressed is true, opacity_request is called by an
        # wrongly sent out enter_notification_event sent after a
        # button_press (because of a bug in compiz).
        if self.button_pressed:
            self.button_pressed = False
            return False
        # Check if mouse cursor still is over the window button.
        b_m_x,b_m_y = self.window_button.get_pointer()
        b_r = self.window_button.get_allocation()
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            self.opacify()
        return False


    def deopacify(self):
        # always called from deopacify_request (with timeout)
        # If another window button has called opacify, don't deopacify.
        if self.dockbar.opacified and not self.opacified:
            return False
        if self.dockbar.opacity_values == None:
            return False
        try:
            compiz_call('obs/screen0/opacity_values','set', self.dockbar.opacity_values)
            compiz_call('obs/screen0/opacity_matches','set', self.dockbar.opacity_matches)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', self.dockbar.opacity_values)
                compiz_call('core/screen0/opacity_matches','set', self.dockbar.opacity_matches)
            except:
                pass
        self.dockbar.opacity_values = None
        self.dockbar.opacity_matches = None
        return False

    def deopacify_request(self):
        if not self.opacified:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.window_button.get_pointer()
        b_r = self.window_button.get_allocation()
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            return True
        self.dockbar.opacified = False
        self.opacified = False
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        gobject.timeout_add(110, self.deopacify)
        return False

    #### D'n'D
    def on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
##            self.window_button.drag_highlight()
            event = gtk.gdk.Event(gtk.gdk.EXPOSE)
            event.window = self.groupbutton.popup.window
            event.area = self.groupbutton.popup.get_allocation()
            self.groupbutton.popup.send_expose(event)
            self.button_drag_entered = True
            self.dnd_select_window = \
                gobject.timeout_add(600,self.action_select_window)
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.button_drag_entered = False
        gobject.source_remove(self.dnd_select_window)
##        self.window_button.drag_unhighlight()
        event = gtk.gdk.Event(gtk.gdk.EXPOSE)
        event.window = self.groupbutton.popup.window
        event.area = self.groupbutton.popup.get_allocation()
        self.groupbutton.popup.send_expose(event)
        self.groupbutton.hide_list_request()


    #### Events
    def on_button_mouse_enter(self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        # Keep that in mind when coding this def!
        if self.button_pressed :
            return
        self.update_label_state(True)
        if settings["opacify"]:
            gobject.timeout_add(100,self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(500, self.deopacify_request)

    def on_button_mouse_leave(self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        # Keep that in mind when coding this def!
        self.button_pressed = False
        self.update_label_state(False)
        if settings["opacify"]:
            self.deopacify_request()

    def on_window_button_press_event(self, widget,event):
        # In compiz there is a enter and a leave event before a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.on_button_mouse_enter or self.on_button_mouse_leave.
        self.button_pressed = True
        gobject.timeout_add(600, self.set_button_pressed_false)

    def set_button_pressed_false(self):
        # Helper function for on_window_button_press_event.
        self.button_pressed = False
        return False

    def on_window_button_scroll_event(self, widget,event):
        if settings["opacify"]and self.opacified:
            self.dockbar.opacified = False
            self.opacified = False
            self.deopacify()
        if event.direction == gtk.gdk.SCROLL_UP:
            action = settings['windowbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = settings['windowbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)

    def on_window_button_release_event(self, widget,event):
        if settings["opacify"]and self.opacified:
            self.dockbar.opacified = False
            self.opacified = False
            self.deopacify()
        if event.button == 1 and event.state & gtk.gdk.SHIFT_MASK :
            action = settings['windowbutton_shift_and_left_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 1:
            action = settings['windowbutton_left_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 2 and event.state & gtk.gdk.SHIFT_MASK:
            action = settings['windowbutton_shift_and_middle_click_action']
            self.action_function_dict[action](self, widget,event)
        elif event.button == 2:
            action = settings['windowbutton_middle_click_action']
            self.action_function_dict[action](self, widget,event)
        elif event.button == 3 and event.state & gtk.gdk.SHIFT_MASK:
            action = settings['windowbutton_shift_and_right_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 3:
            action = settings['windowbutton_right_click_action']
            self.action_function_dict[action](self, widget, event)

    #### Menu functions
    def menu_closed(self, menushell):
        self.dockbar.right_menu_showing = False
        self.groupbutton.popup.hide()

    def minimize_window(self, widget=None, event=None):
        if self.window.is_minimized():
            self.window.unminimize(gtk.get_current_event_time())
        else:
            self.window.minimize()

    #### Actions
    def action_select_or_minimize_window(self, widget=None, event=None, minimize=True):
        # The window is activated, unless it is already
        # activated, then it's minimized. Minimized
        # windows are unminimized. The workspace
        # is switched if the window is on another
        # workspace.
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        if self.window.get_workspace() != None \
        and self.screen.get_active_workspace() != self.window.get_workspace():
            self.window.get_workspace().activate(t)
        if not self.window.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.window.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            # which means popup list can be left open.
            self.groupbutton.popup.hide()
            self.groupbutton.popup_showing = False
        if self.window.is_minimized():
            self.window.unminimize(t)
        elif self.window.is_active() and minimize:
            self.window.minimize()
        else:
            self.window.activate(t)

    def action_select_window(self, widget = None, event = None):
        self.action_select_or_minimize_window(widget, event, False)

    def action_close_window(self, widget=None, event=None):
        self.window.close(gtk.get_current_event_time())

    def action_maximize_window(self, widget=None, event=None):
        if self.window.is_maximized():
            self.window.unmaximize()
        else:
            self.window.maximize()

    def action_lock_or_unlock_window(self, widget=None, event=None):
        if settings["opacify"]and self.opacified:
            self.dockbar.opacified = False
            self.opacified = False
            self.deopacify()
        if self.locked == False:
            self.locked = True
            self.groupbutton.locked_windows_count += 1
            if not self.window.is_minimized():
                self.window.minimize()
            else:
                self.window_button_icon.set_from_pixbuf(self.icon_locked)
                self.groupbutton.update_state()
        else:
            self.locked = False
            self.groupbutton.locked_windows_count -= 1
            self.groupbutton.update_state()
            self.update_label_state()
            self.window_button_icon.set_from_pixbuf(self.icon_transp)

    def action_shade_window(self, widget, event):
        self.window.shade()

    def action_unshade_window(self, widget, event):
        self.window.unshade()

    def action_show_menu(self, widget, event):
        try:
            action_minimize = wnck.WINDOW_ACTION_MINIMIZE
            action_unminimize = wnck.WINDOW_ACTION_UNMINIMIZE
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_minimize = 1 << 12
            action_unminimize = 1 << 13
            action_maximize = 1 << 14
        #Creates a popup menu
        menu = gtk.Menu()
        menu.connect('selection-done', self.menu_closed)
        #(Un)Lock
        lock_item = None
        if self.window.get_actions() & action_minimize \
        and not self.locked:
            lock_item = gtk.MenuItem('_Lock')
        elif self.locked:
            lock_item = gtk.MenuItem('Un_lock')
        if lock_item:
            menu.append(lock_item)
            lock_item.connect("activate", self.action_lock_or_unlock_window)
            lock_item.show()
        #(Un)Minimize
        minimize_item = None
        if self.window.get_actions() & action_minimize \
        and not self.window.is_minimized():
            minimize_item = gtk.MenuItem('_Minimize')
        elif self.window.get_actions() & action_unminimize \
        and self.window.is_minimized():
            minimize_item = gtk.MenuItem('Un_minimize')
        if minimize_item:
            menu.append(minimize_item)
            minimize_item.connect("activate", self.minimize_window)
            minimize_item.show()
        # (Un)Maximize
        maximize_item = None
        if not self.window.is_maximized() \
        and self.window.get_actions() & action_maximize:
            maximize_item = gtk.MenuItem('Ma_ximize')
        elif self.window.is_maximized() \
        and self.window.get_actions() & action_unminimize:
            maximize_item = gtk.MenuItem('Unma_ximize')
        if maximize_item:
            menu.append(maximize_item)
            maximize_item.connect("activate", self.action_maximize_window)
            maximize_item.show()
        # Close
        close_item = gtk.MenuItem('_Close')
        menu.append(close_item)
        close_item.connect("activate", self.action_close_window)
        close_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.dockbar.right_menu_showing = True

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = ODict((
                                  ('select or minimize window', action_select_or_minimize_window),
                                  ('select window', action_select_window),
                                  ('maximize window', action_maximize_window),
                                  ('close window', action_close_window),
                                  ('show menu', action_show_menu),
                                  ('lock or unlock window', action_lock_or_unlock_window),
                                  ('shade window', action_shade_window),
                                  ('unshade window', action_unshade_window),
                                  ('no action', action_none)
                                ))


class GroupButton (gobject.GObject):
    """Group button takes care of a program's "button" in dockbar.

    It also takes care of the popup window and all the window buttons that
    populates it."""

    __gsignals__ = {
        "set-icongeo-win": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "set-icongeo-grp": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "set-icongeo-delay": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
    }

    def __init__(self,dockbar,class_group=None, identifier=None, launcher=None, index=None, app=None):
        gobject.GObject.__init__(self)

        self.launcher = launcher
        self.class_group = class_group
        self.dockbar = dockbar
        self.app = app
        if identifier:
            self.identifier = identifier
        elif launcher:
            self.identifier = launcher.get_identifier()
            # launcher.get_identifier() returns None
            # if the identifier is still unknown
        else:
            raise Exception, "Can't initiate Group button without class_group or launcher."


        # Variables
        self.windows = {}
        self.minimized_windows_count = 0
        self.minimized_state = 0
        self.locked_windows_count = 0
        self.has_active_window = False
        self.needs_attention = False
        self.attention_effect_running = False
        self.nextlist = None
        self.nextlist_time = None
        self.mouse_over = False
        self.opacified = False
        self.lastlaunch = None
        self.launch_effect = False
        # Compiz sends out false mouse enter messages after button is pressed.
        # This works around that bug.
        self.button_pressed = False

        self.screen = wnck.screen_get_default()
        self.root_xid = self.dockbar.root_xid


        #--- Button
        self.icon_factory = IconFactory(self.dockbar, class_group, launcher, app, self.identifier)
        self.image = gtk.Image() # Todo: REmove
        gtk_screen = self.dockbar.container.get_screen()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap == None:
            colormap = gtk_screen.get_rgb_colormap()
        gtk.widget_push_colormap(colormap)
        self.button = CairoButton()
        gtk.widget_pop_colormap()
        self.button.show_all()
        if index == None:
            self.dockbar.container.pack_start(self.button, False)
        else:
            # Insterts the button on it's index by removing
            # and repacking the buttons that should come after it
            repack_list = self.dockbar.groups.get_groups()[index:]
            for group in repack_list:
                self.dockbar.container.remove(group.button)
            self.dockbar.container.pack_start(self.button, False)
            for group in repack_list:
                self.dockbar.container.pack_start(group.button, False)
##        self.dockbar.container.show_all()
        self.dockbar.container.show()


        # Button events
        self.button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.button.connect("button-release-event",self.on_group_button_release_event)
        self.button.connect("button-press-event",self.on_group_button_press_event)
        self.button.connect("scroll-event",self.on_group_button_scroll_event)
        self.button.connect("size-allocate", self.on_sizealloc)
        self.button_old_alloc = self.button.get_allocation()


        #--- Popup window
        gtk_screen = self.dockbar.container.get_screen()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap == None:
            colormap = gtk_screen.get_rgb_colormap()
        cairo_popup = CairoPopup(colormap)

        if settings["preview"]:
            self.winlist = gtk.HBox()
            self.winlist.set_spacing(4)
        else:
            self.winlist = gtk.VBox()
            self.winlist.set_spacing(2)
        self.popup_box = gtk.VBox()
        self.popup_box.set_border_width(5)
        self.popup_box.set_spacing(2)
        self.popup_label = gtk.Label()
        self.update_name()
        self.popup_label.set_use_markup(True)
        if self.identifier:
            # Todo: add tooltip when identifier is added.
            self.popup_label.set_tooltip_text("Identifier: "+self.identifier)
        self.popup_box.pack_start(self.popup_label, False)
        self.popup_box.pack_start(self.winlist, False)


        self.popup = cairo_popup.window
        self.popup_showing = False
        self.popup.connect("leave-notify-event",self.on_popup_mouse_leave)
        self.popup.add(self.popup_box)


        #--- D'n'D
        # Drag and drop should handel buttons that are moved,
        # launchers that is dropped, and open popup window
        # to enable drag and drops to windows that has to be
        # raised.
        self.button.drag_dest_set(0, [], 0)
        self.button.connect("drag_motion", self.on_button_drag_motion)
        self.button.connect("drag_leave", self.on_button_drag_leave)
        self.button.connect("drag_drop", self.on_drag_drop)
        self.button.connect("drag_data_received", self.on_drag_data_received)
        self.button_drag_entered = False
        self.dnd_highlight = False
        self.dnd_show_popup = None
        self.dnd_select_window = None

        # The popup needs to have a drag_dest just to check
        # if the mouse is howering it during a drag-drop.
        self.popup.drag_dest_set(0, [], 0)
        self.popup.connect("drag_motion", self.on_popup_drag_motion)
        self.popup.connect("drag_leave", self.on_popup_drag_leave)

        #Make buttons drag-able
        self.button.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                    [('text/groupbutton_name', 0, TARGET_TYPE_GROUPBUTTON)],
                                    gtk.gdk.ACTION_MOVE)
        self.button.drag_source_set_icon_pixbuf(self.icon_factory.find_icon_pixbuf(32))
        self.button.connect("drag_begin", self.on_drag_begin)
        self.button.connect("drag_data_get", self.on_drag_data_get)
        self.button.connect("drag_end", self.on_drag_end)
        self.is_current_drag_source = False

##    def __del__(self):
##        if self.button:
##            self.button.destroy()
##        self.button = None
##        self.popup = None
##        self.windows = None
##        self.winlist = None
##        self.dockbar = None
##        self.drag_pixbuf = None

    def identifier_changed(self, identifier):
        self.identifier = identifier
        self.launcher.set_identifier(identifier)
        self.popup_label.set_tooltip_text("Identifier: "+self.identifier)

    def update_class_group(self, class_group):
        self.class_group = class_group

    def get_class_group(self):
        return self.class_group

    def update_name(self):
        if self.launcher:
            self.name = self.launcher.get_entry_name()
        elif self.app:
            self.name = u"" + self.app.get_name()
        else:
            # Uses first half of the name, like "Amarok" from "Amarok - [SONGNAME]"
            # A program that uses a name like "[DOCUMENT] - [APPNAME]" would be
            # totally screwed up. So far no such program has been reported.
            self.name = self.class_group.get_name().split(" - ", 1)[0]
        self.popup_label.set_label("<span foreground='"+colors['color2']+"'><big><b>"+self.name+"</b></big></span>")

    def remove_launch_effect(self):
        self.launch_effect = False
        self.update_state()
        return False

    #### State
    def update_popup_label(self):
        self.popup_label.set_text("<span foreground='"+colors['color2']+"'><big><b>"+self.name+"</b></big></span>")
        self.popup_label.set_use_markup(True)

    def update_state(self):
        # Checks button state and set the icon accordingly.
        win_nr = min(self.get_windows_count(), 15)
        if win_nr == 0 and not self.launcher:
            self.button.hide()
            return
        else:
            self.button.show()

        mwc = self.get_minimized_windows_count()
        if self.launcher and win_nr == 0:
            icon_mode = IconFactory.LAUNCHER
        elif (win_nr - mwc) == 0:
            icon_mode = IconFactory.ALL_MINIMIZED
        elif mwc > 0:
            icon_mode = IconFactory.SOME_MINIMIZED
        else:
            icon_mode = 0

        if self.has_active_window and win_nr>0:
            icon_active = IconFactory.ACTIVE
        else:
            icon_active = 0

        if self.needs_attention and win_nr>0:
            if settings["groupbutton_attention_notification_type"] == 'red':
                icon_effect = IconFactory.NEEDS_ATTENTION
            elif settings["groupbutton_attention_notification_type"] == 'nothing':
                # Do nothing
                icon_effect = 0
            else:
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    gobject.timeout_add(700, self.attention_effect)
                icon_effect = 0
        else:
            icon_effect = 0

        if self.mouse_over:
            mouse_over = IconFactory.MOUSE_OVER
        else:
            mouse_over = 0

        if self.launch_effect:
            launch_effect = IconFactory.LAUNCH_EFFECT
        else:
            launch_effect = 0

        if self.dnd_highlight:
            dd_effect = IconFactory.DRAG_DROPP
        else:
            dd_effect = 0


        self.state_type = icon_mode | icon_effect | icon_active | mouse_over | launch_effect | dd_effect | win_nr
        surface = self.icon_factory.surface_update(self.state_type)
        # Set the button size to the size of the surface
        if self.button.allocation.width != surface.get_width() \
        or self.button.allocation.height != surface.get_height():
            self.button.set_size_request(surface.get_width(), surface.get_height())
        self.button.update(surface)
        return

    def update_state_request(self):
        #Update state if the button is shown.
        a = self.button.get_allocation()
        if a.width>10 and a.height>10:
            self.update_state()

    def attention_effect (self):
        self.attention_effect_running = True
        if self.needs_attention:
            if settings["groupbutton_attention_notification_type"] == 'compwater':
                x,y = self.button.window.get_origin()
                alloc = self.button.get_allocation()
                x = x + alloc.x + alloc.width/2
                y = y + alloc.y + alloc.height/2
                try:
                    compiz_call('water/allscreens/point','activate','root',self.root_xid,'x',x,'y',y)
                except:
                    pass
            elif settings["groupbutton_attention_notification_type"] == 'blink':
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    surface = self.icon_factory.surface_update(IconFactory.BLINK | self.state_type)
                    self.button.update(surface)
                else:
                    self.needs_attention_anim_trigger = False
                    surface = self.icon_factory.surface_update(self.state_type)
                    self.button.update(surface)
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False

    #### Window counts
    def get_windows_count(self):
        if not settings["show_only_current_desktop"]:
            return len(self.windows)
        nr = 0
        for win in self.windows:
            if not self.windows[win].is_on_current_desktop():
                continue
            nr += 1
        return nr

    def get_minimized_windows_count(self):
        nr = 0
        for win in self.windows:
            if settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if win.is_minimized():
                nr += 1
        return nr

    def get_unminimized_windows_count(self):
        nr = 0
        for win in self.windows:
            if settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if not win.is_minimized():
                nr += 1
        return nr

    #### Window handling
    def add_window(self,window):
        if window in self.windows:
            return
        self.windows[window] = WindowButton(window,self)
        if window.is_minimized():
            self.minimized_windows_count += 1
        if (self.launcher and len(self.windows)==1):
            self.class_group = window.get_class_group()
        if self.launch_effect:
            self.launch_effect = False
            gobject.source_remove(self.launch_effect_timeout)
        # Update state unless the button hasn't been shown yet.
        self.update_state_request()

        #Update popup-list if it is being shown.
        if self.popup_showing:
            if settings["show_only_current_desktop"]:
                self.winlist.show()
                self.popup_label.show()
                for win in self.windows.values():
                    if win.is_on_current_desktop():
                        win.window_button.show_all()
                    else:
                        win.window_button.hide_all()
            else:
                self.winlist.show_all()
            gobject.idle_add(self.show_list_request)

        # Set minimize animation
        # (if the eventbox is created already, otherwice the icon animation is set in sizealloc())
        if self.button.window:
            x, y = self.button.window.get_origin()
            a = self.button.get_allocation()
            x += a.x
            y += a.y
            window.set_icon_geometry(x, y, a.width, a.height)

        if not self.class_group:
            self.update_classgroup(window.get_class_group())

    def del_window(self,window):
        if window.is_minimized():
            self.minimized_windows_count -= 1
        if self.nextlist and window in self.nextlist:
            self.nextlist.remove(window)
        self.windows[window].del_button()
        del self.windows[window]
        if self.needs_attention:
            self.needs_attention_changed()
        self.update_state_request()
        if not self.windows and not self.launcher:
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            del self.dockbar
        elif not self.windows and self.launcher and self.popup_showing:
            self.popup.resize(10,10)
            gobject.idle_add(self.show_list_request)

    def set_has_active_window(self, mode):
        if mode != self.has_active_window:
            self.has_active_window = mode
            if mode == False:
                for window_button in self.windows.values():
                    window_button.set_button_active(False)
            self.update_state_request()

    def get_windows(self):
        if settings["show_only_current_desktop"]:
            wins = []
            for win in self.windows:
                if self.windows[win].is_on_current_desktop():
                    wins.append(win)
            return wins
        else:
            return self.windows.keys()

    def get_unminimized_windows(self):
        wins = []
        for win in self.windows:
            if settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if not win.is_minimized():
                wins.append(win)
        return wins

    def needs_attention_changed(self):
        # Checks if there are any urgent windows and changes
        # the group button looks if there are at least one
        for window in self.windows.keys():
            if window.needs_attention():
                self.needs_attention = True
                self.update_state_request()
                return True
        else:
            if self.windows.keys() == []:
                # The window needs attention already when it's added,
                # before it's been added to the list.
                self.needs_attention = True
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return True
            else:
                self.needs_attention = False
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return False

    #### Show/hide list
    def show_list_request(self):
        # If mouse cursor is over the button, show popup window.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if self.popup_showing or ((b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height) \
           and not self.dockbar.right_menu_showing and not self.dockbar.dragging):
            self.show_list()
        return False

    def show_list(self):
        # Move popup to it's right spot and show it.
        offset = 3

        if settings["preview"]:
            #Update previews
            for win in self.get_windows():
                self.windows[win].update_preview()
        if settings["show_only_current_desktop"]:
            self.popup_box.show()
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if win.is_on_current_desktop():
                    win.window_button.show_all()
                else:
                    win.window_button.hide_all()
        else:
            self.popup_box.show_all()
        self.popup.resize(10,10)
        x,y = self.button.window.get_origin()
        b_alloc = self.button.get_allocation()
        w,h = self.popup.get_size()
        if self.dockbar.orient == "h":
            if settings['popup_align'] == 'left':
                x = b_alloc.x + x
            if settings['popup_align'] == 'center':
                x = b_alloc.x + x + (b_alloc.width/2)-(w/2)
            if settings['popup_align'] == 'right':
                x = b_alloc.x + x + b_alloc.width - w
            y = b_alloc.y + y-offset
            if x+(w)>self.screen.get_width():
                x=self.screen.get_width()-w
            if x<0:
                x = 0
            if y-h >= 0:
                self.popup.move(x,y-h)
            else:
                self.popup.move(x,y+b_alloc.height+(offset*2))
        else:
            x = b_alloc.x + x
            y = b_alloc.y + y
            if y+h>self.screen.get_height():
                y=self.screen.get_height()-h
            if x+w >= self.screen.get_width():
                self.popup.move(x - w - offset,y)
            else:
                self.popup.move(x + b_alloc.width + offset,y)

        self.popup.show()
        self.popup_showing = True
        self.emit('set-icongeo-win')
        return False

    def hide_list_request(self):
        if self.popup.window == None:
            return
        # Checks if mouse cursor really isn't hovering the button
        # or the popup window anymore and hide the popup window
        # if so.
        p_m_x,p_m_y = self.popup.get_pointer()
        p_w,p_h = self.popup.get_size()
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        r = 5 #radius for the rounded corner of popup window

        # Make sure that the popup list isn't closed when
        # howering the gap between button and list.
        w,h = self.popup.get_size()
        p_x,p_y = self.popup.window.get_origin()
        offset = 3
        b_x,b_y = self.button.window.get_origin()
        if self.dockbar.orient == 'h' and b_m_x>=0 and b_m_x<=(b_r.width-1):
            if (p_y < b_y and b_m_y>=-offset and b_m_y<=0) \
            or (p_y > b_y and b_m_y>=(b_r.height-1) and b_m_y<=(b_r.height-1+offset)):
                gobject.timeout_add(50, self.hide_list_request)
                return
        elif self.dockbar.orient == 'v' and b_m_y>=0 and b_m_y<=(b_r.height-1):
            if (p_x < b_x and b_m_x>=-offset and b_m_x<=0) \
            or (p_x > b_x and b_m_x>=(b_r.width-1) and b_m_x<=(b_r.width-1+offset)):
                gobject.timeout_add(50, self.hide_list_request)
                return

        if not ((p_m_x<0 or p_m_x>(p_w-1))or(p_m_y<0 or p_m_y>(p_h-1))):
            # Mouse pointer is inside the "rectangle"
            # but check if it's still outside the rounded corners
            x = None
            y = None
            if p_m_x < r:
                x = r - p_m_x
            if (p_w - p_m_x) < r:
                x = p_m_x - (p_w - r)
            if p_m_y < r:
                y = r - p_m_y
            if (p_h - p_m_y) < r:
                y = p_m_y - (p_h - r)
            if x == None or y == None \
            or (x**2 + y**2) < (r-1)**2:
                # It's inside the rounded corners!
                return
        if not ((b_m_x<0 or b_m_x>(b_r.width-1)) or (b_m_y<0 or b_m_y>(b_r.height-1))):
            # Mouse pointer is over the group button.
            gobject.timeout_add(50, self.hide_list_request)
            # This timeout add is needed if mouse cursor leaves the
            # screen following the screen edge.
            return
        self.hide_list()
        return

    def hide_list(self):
        self.popup.hide()
        self.popup_showing = False
        self.emit('set-icongeo-grp')
        if settings["preview"] and not settings["remember_previews"]:
            # Remove previews to save memory.
            for win in self.get_windows():
                self.windows[win].clear_preview_image()
            gc.collect()
        return False

    #### Opacify
    def opacify(self):
        # Makes all windows but the one connected to this windowbutton transparent
        if self.dockbar.opacity_values == None:
            try:
                self.dockbar.opacity_values = compiz_call('obs/screen0/opacity_values','get')
            except:
                try:
                    self.dockbar.opacity_values = compiz_call('core/screen0/opacity_values','get')
                except:
                    return
        if self.dockbar.opacity_matches == None:
            try:
                self.dockbar.opacity_matches = compiz_call('obs/screen0/opacity_matches','get')
            except:
                try:
                    self.dockbar.opacity_values = compiz_call('core/screen0/opacity_matches','get')
                except:
                    return
        self.dockbar.opacified = True
        self.opacified = True
        ov = [settings['opacify_alpha']]
        om = ["!(class="+self.class_group.get_res_class()+" | class=Dockbarx.py)  & (type=Normal | type=Dialog)"]
        try:
            compiz_call('obs/screen0/opacity_values','set', ov)
            compiz_call('obs/screen0/opacity_matches','set', om)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', ov)
                compiz_call('core/screen0/opacity_matches','set', om)
            except:
                return

    def opacify_request(self):
        if len(self.windows) - self.minimized_windows_count == 0:
            return False
        # if self.button_pressed is true, opacity_request is called by an
        # wrongly sent out enter_notification_event sent after a
        # button_press (because of a bug in compiz).
        if self.button_pressed:
            self.button_pressed = False
            return False
        # Check if mouse cursor still is over the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            self.opacify()
        return False


    def deopacify(self):
        # always called from deopacify_request (with timeout)
        # If another window button has called opacify, don't deopacify.
        if self.dockbar.opacified and not self.opacified:
            return False
        if self.dockbar.opacity_values == None:
            return False
        try:
            compiz_call('obs/screen0/opacity_values','set', self.dockbar.opacity_values)
            compiz_call('obs/screen0/opacity_matches','set', self.dockbar.opacity_matches)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', self.dockbar.opacity_values)
                compiz_call('core/screen0/opacity_matches','set', self.dockbar.opacity_matches)
            except:
                pass
        self.dockbar.opacity_values = None
        self.dockbar.opacity_matches = None
        return False

    def deopacify_request(self):
        if not self.opacified:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            return True
        self.dockbar.opacified = False
        self.opacified = False
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        gobject.timeout_add(110, self.deopacify)
        return False

    #### DnD
    def on_drag_begin(self, widget, drag_context):
        self.is_current_drag_source = True
        self.dockbar.dragging = True
        self.hide_list()

    def on_drag_data_get(self, widget, context, selection, targetType, eventTime):
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        selection.set(selection.target, 8, name)


    def on_drag_end(self, widget, drag_context, result = None):
        self.is_current_drag_source = False
        # A delay is needed to make sure the button is
        # shown after button_drag_end has hidden it and
        # not the other way around.
        gobject.timeout_add(30, self.button.show)

    def on_drag_drop(self, wid, drag_context, x, y, t):
        for target in ('text/groupbutton_name', 'text/uri-list'):
            if target in drag_context.targets:
                self.button.drag_get_data(drag_context, target, t)
                drag_context.finish(True, False, t)
                break
        else:
            drag_context.finish(False, False, t)
        return True

    def on_drag_data_received(self, wid, context, x, y, selection, targetType, t):
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        if selection.target == 'text/groupbutton_name':
            if selection.data != name:
                self.dockbar.move_groupbutton(selection.data, calling_button=name)
        elif selection.target == 'text/uri-list':
            #remove 'file://' and '/n' from the URI
            path = selection.data[7:-2]
            path = path.replace("%20"," ")
            print path
            self.dockbar.make_new_launcher(path, name)

    def on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.button_drag_entered = True
            if not 'text/groupbutton_name' in drag_context.targets:
                win_nr = self.get_windows_count()
                if len(self.windows) == 1:
                    self.dnd_select_window = gobject.timeout_add(600, self.windows.values()[0].action_select_window)
                elif len(self.windows) > 1:
                    self.dnd_show_popup = gobject.timeout_add(settings['popup_delay'], self.show_list)
            for target in ('text/uri-list', 'text/groupbutton_name'):
                if target in drag_context.targets \
                and not self.is_current_drag_source:
                    self.dnd_highlight = True
                    self.update_state()
        if 'text/groupbutton_name' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_MOVE, t)
        elif 'text/uri-list' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_COPY, t)
        else:
            drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.dnd_highlight = False
        self.button_drag_entered = False
        self.update_state()
        self.hide_list_request()
        if self.dnd_show_popup != None:
            gobject.source_remove(self.dnd_show_popup)
            self.dnd_show_popup = None
        if self.dnd_select_window != None:
            gobject.source_remove(self.dnd_select_window)
            self.dnd_select_window = None
        if self.is_current_drag_source:
            # If drag leave signal is given because of a drop,
            # a small delay is needed since
            # drag-end isn't called if
            # the destination is hidden just before
            # the drop is completed.
            gobject.timeout_add(20, self.button.hide)

    def on_popup_drag_motion(self, widget, drag_context, x, y, t):
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_popup_drag_leave(self, widget, drag_context, t):
        self.hide_list_request()


    #### Events
    def on_sizealloc(self,applet,allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        if self.button_old_alloc != self.button.get_allocation():
            if self.dockbar.orient == "v" \
            and allocation.width>10 and allocation.width < 220 \
            and allocation.width != self.button_old_alloc.width:
                # A minimium size on 11 is set to stop unnecessary calls
                # work when the button is created
                self.icon_factory.set_size(allocation.width)
                self.update_state()
            elif self.dockbar.orient == "h" \
            and allocation.height>10 and allocation.height<220\
            and allocation.height != self.button_old_alloc.height:
                self.icon_factory.set_size(allocation.height)
                self.update_state()
            self.button_old_alloc = allocation

            # Update icon geometry
            self.emit('set-icongeo-grp')

    def on_button_mouse_enter (self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        if self.button_pressed :
            return
        self.mouse_over = True
        self.update_state()
        if settings["opacify"] and settings["opacify_group"]:
            gobject.timeout_add(settings['popup_delay'],self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(settings['popup_delay']+500, self.deopacify_request)

        if self.get_windows_count() <= 1 and settings['no_popup_for_one_window']:
            return
        # Prepare for popup window
        if settings["popup_delay"]>0:
            self.emit('set-icongeo-delay')
        if not self.dockbar.right_menu_showing and not self.dockbar.dragging:
            gobject.timeout_add(settings['popup_delay'], self.show_list_request)

    def on_button_mouse_leave (self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        self.button_pressed = False
        self.mouse_over = False
        self.update_state()
        self.hide_list_request()
        if self.popup.window == None:
            # self.hide_list takes care of emitting 'set-icongeo-grp' normally
            # but if no popup window exist its taken care of here.
            self.emit('set-icongeo-grp')
        if settings["opacify"] and settings["opacify_group"]:
            self.deopacify_request()

    def on_popup_mouse_leave (self,widget,event):
        self.hide_list_request()

    def on_group_button_scroll_event (self,widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = settings['groupbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = settings['groupbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)

    def on_group_button_release_event(self, widget, event):
        # Connects right button with right action.
        if event.state & gtk.gdk.SHIFT_MASK:
            if event.button == 1 and settings['groupbutton_shift_and_left_click_double'] == False \
               and not self.dockbar.dragging:
                action = settings['groupbutton_shift_and_left_click_action']
                self.action_function_dict[action](self, widget, event)
            elif event.button == 2 and settings['groupbutton_shift_and_middle_click_double'] == False:
                action = settings['groupbutton_shift_and_middle_click_action']
                self.action_function_dict[action](self, widget,event)
            elif event.button == 3 and settings['groupbutton_shift_and_right_click_double'] == False:
                action = settings['groupbutton_shift_and_right_click_action']
                self.action_function_dict[action](self, widget, event)

        else:
            if event.button == 1 and settings['groupbutton_left_click_double'] == False \
                 and not self.dockbar.dragging :
                action = settings['groupbutton_left_click_action']
                self.action_function_dict[action](self, widget, event)

            elif event.button == 2 and settings['groupbutton_middle_click_double'] == False:
                action = settings['groupbutton_middle_click_action']
                self.action_function_dict[action](self, widget,event)

            elif event.button == 3 and settings['groupbutton_right_click_double'] == False:
                action = settings['groupbutton_right_click_action']
                self.action_function_dict[action](self, widget, event)
        # If a drag and drop just finnished set self.draggin to false
        # so that left clicking works normally again
        if event.button == 1 and self.dockbar.dragging:
            self.dockbar.dragging = False


    def on_group_button_press_event(self,widget,event):
        # In compiz there is a enter and a leave event before a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.button_mouse_enter or self.on_button_mouse_leave.
        self.button_pressed = True
        gobject.timeout_add(600, self.set_button_pressed_false)

        if event.type == gtk.gdk._2BUTTON_PRESS and event.state & gtk.gdk.SHIFT_MASK:
            if event.button == 1 and settings['groupbutton_shift_and_left_click_double'] == True:
                action = settings['groupbutton_shift_and_left_click_action']
                self.action_function_dict[action](self, widget, event)
            elif event.button == 2 and settings['groupbutton_shift_and_middle_click_double'] == True:
                action = settings['groupbutton_shift_and_middle_click_action']
                self.action_function_dict[action](self, widget,event)
            elif event.button == 3 and settings['groupbutton_shift_and_right_click_double'] == True:
                action = settings['groupbutton_shift_and_right_click_action']
                self.action_function_dict[action](self, widget, event)
        elif event.type == gtk.gdk._2BUTTON_PRESS:
            if event.button == 1 and settings['groupbutton_left_click_double'] == True:
                action = settings['groupbutton_left_click_action']
                self.action_function_dict[action](self, widget, event)
            elif event.button == 2 and settings['groupbutton_middle_click_double'] == True:
                action = settings['groupbutton_middle_click_action']
                self.action_function_dict[action](self, widget,event)
            elif event.button == 3 and settings['groupbutton_right_click_double'] == True:
                action = settings['groupbutton_right_click_action']
                self.action_function_dict[action](self, widget, event)
        # Return False so that a drag-and-drop can be initiated if needed
        elif event.button == 1:
            return False
        return True

    def set_button_pressed_false(self):
        # Helper function to group_button_press_event
        self.button_pressed = False
        return False

    #### Menu functions
    def menu_closed(self, menushell):
        self.dockbar.right_menu_showing = False

    def unminimize_all_windows(self, widget=None, event=None):
        t = gtk.get_current_event_time()
        for window in self.get_windows():
            if window.is_minimized():
                window.unminimize(t)

    def change_identifier(self, widget=None, event=None):
        self.dockbar.change_identifier(self.launcher.get_path(), self.identifier)

    def add_launcher(self, widget=None, event=None):
        path = "gio:" + self.app.get_id()[:self.app.get_id().rfind('.')].lower()
        self.launcher = Launcher(self.identifier, path, self.dockbar)
        self.dockbar.groups.set_launcher_path(self.identifier, path)
        self.dockbar.update_launchers_list()

    #### Actions
    def action_select(self, widget, event):
        wins = self.get_windows()
        if (self.launcher and not wins):
            self.action_launch_application()
        # One window
        elif len(wins) == 1:
            if settings["select_one_window"] == "select window":
                self.windows[wins[0]].action_select_window(widget, event)
            elif settings["select_one_window"] == "select or minimize window":
                self.windows[wins[0]].action_select_or_minimize_window(widget, event)
        # Multiple windows
        elif len(wins) > 1:
            if settings["select_multiple_windows"] == "select all":
                self.action_select_or_minimize_group(widget, event, minimize=False)
            elif settings["select_multiple_windows"] == "select or minimize all":
                self.action_select_or_minimize_group(widget, event, minimize=True)
            elif settings["select_multiple_windows"] == "compiz scale":
                umw = self.get_unminimized_windows()
                if len(umw) == 1:
                    if settings["select_one_window"] == "select window":
                        self.windows[umw[0]].action_select_window(widget, event)
                    elif settings["select_one_window"] == "select or minimize window":
                        self.windows[umw[0]].action_select_or_minimize_window(widget, event)
                elif len(umw) == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif settings["select_multiple_windows"] == "cycle through windows":
                self.action_select_next(widget, event)
            elif settings["select_multiple_windows"] == "show popup":
                self.action_select_popup(widget, event)

    def action_select_popup(self, widget, event):
        if self.popup_showing is True:
            self.hide_list()
        else:
            self.show_list()

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if settings['show_only_current_desktop']:
            mode = 'ignore'
        else:
            mode = settings['workspace_behavior']
        screen = self.screen
        windows_stacked = screen.get_windows_stacked()
        grp_win_stacked = []
        ignorelist = []
        minimized_win_cnt = self.minimized_windows_count
        moved = False
        grtop = False
        wingr = False
        active_workspace = screen.get_active_workspace()

        # Check if there are any uminimized windows, unminimize
        # them (unless they are on another workspace and work-
        # space behavior is somehting other than move) and
        # return.
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized() \
                and not self.windows[win].locked:
                    ignored = False
                    if not win.is_pinned() and win.get_workspace() != None \
                       and screen.get_active_workspace() != win.get_workspace():
                        if mode == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not ignored:
                        win.unminimize(event.time)
                        unminimized = True
        if unminimized:
            return

        # Make a list of the windows in group with the bottom most
        # first and top most last.
        # If mode is other than move
        # windows on other workspaces is put in a separate list instead.
        # grtop is set to true if not all windows in the group is the
        # topmost windows.
        for win in windows_stacked:
            if (not win.is_skip_tasklist()) and (not win.is_minimized()) \
            and (win.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() and win.get_workspace() != None \
                       and active_workspace != win.get_workspace():
                        if mode == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)

                    if not ignored:
                        grp_win_stacked.append(win)
                        if wingr == False:
                            wingr = True
                            grtop = True
                else:
                    if wingr:
                        grtop = False

        if not grp_win_stacked and mode == 'switch':
            # Put the windows in dictionaries according to workspace and viewport
            # so we can compare which workspace and viewport that has most windows.
            workspaces ={}
            for win in self.windows:
                if win.get_workspace() == None:
                    continue
                if self.windows[win].locked:
                    continue
                workspace = win.get_workspace()
                win_x,win_y,win_w,win_h = win.get_geometry()
                vpx = win_x/screen.get_width()
                vpy = win_y/screen.get_height()
                if not workspace in workspaces:
                    workspaces[workspace] = {}
                if not vpx in workspaces[workspace]:
                    workspaces[workspace][vpx] = {}
                if not vpy in workspaces[workspace][vpx]:
                    workspaces[workspace][vpx][vpy] = []
                workspaces[workspace][vpx][vpy].append(win)
            max = 0
            x = 0
            y = 0
            new_workspace = None
            # Compare which workspace and viewport that has most windows.
            ignorelist.reverse() # Topmost window first.
            for workspace in workspaces:
                for xvp in workspaces[workspace]:
                    for yvp in workspaces[workspace][xvp]:
                        nr = len (workspaces[workspace][xvp][yvp])
                        if nr > max:
                            max = nr
                            x = screen.get_width() * xvp
                            y = screen.get_height() * yvp
                            new_workspace = workspace
                            grp_win_stacked = workspaces[workspace][xvp][yvp]
                        elif nr == max:
                            # Check wether this workspace or previous workspace
                            # with the same amount of windows has been activated
                            # later.
                            for win in ignorelist:
                                if win in grp_win_stacked:
                                    break
                                if win in workspaces[workspace][xvp][yvp]:
                                    x = screen.get_width() * xvp
                                    y = screen.get_height() * yvp
                                    new_workspace = workspace
                                    grp_win_stacked = workspaces[workspace][xvp][yvp]
                                    break
            if new_workspace != screen.get_active_workspace():
                new_workspace.activate(event.time)
            screen.move_viewport(x, y)
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            if not (x == 0 and y == 0):
                self.hide_list()
            for win in grp_win_stacked:
                if win.is_minimized():
                    win.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            ordered_list = []
            ignorelist.reverse() #Bottommost window fist again.
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list

        if grtop and not moved and minimize:
            for win in grp_win_stacked:
                self.windows[win].window.minimize()
        if not grtop:
            for win in grp_win_stacked:
                self.windows[win].window.activate(event.time)

    def action_select_only(self, widget, event):
        self.action_select_or_minimize_group(widget, event, False)

    def action_select_or_compiz_scale(self, widget, event):
        wins = self.get_unminimized_windows()
        if  len(wins) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)

    def action_minimize_all_windows(self,widget=None, event=None):
        for window in self.get_windows():
            window.minimize()

    def action_maximize_all_windows(self,widget=None, event=None):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        maximized = False
        for window in self.get_windows():
            if not window.is_maximized() \
            and window.get_actions() & action_maximize:
                window.maximize()
                maximized = True
        if not maximized:
            for window in self.windows:
                window.unmaximize()

    def action_select_next(self, widget=None, event=None, previous=False):
        if not self.get_windows():
            return
        if self.nextlist_time == None or time() - self.nextlist_time > 2 \
        or self.nextlist == None:
            self.nextlist = []
            minimized_list = []
            screen = self.screen
            windows_stacked = screen.get_windows_stacked()
            wins = self.get_windows()
            for win in windows_stacked:
                    if win in wins:
                        if win.is_minimized():
                            minimized_list.append(win)
                        else:
                            self.nextlist.append(win)
            # Reverse -> topmost window first
            self.nextlist.reverse()
            # Add minimized windows last.
            self.nextlist.extend(minimized_list)
        self.nextlist_time = time()

        if previous:
            win = self.nextlist.pop(-1)
            if win.is_active():
                self.nextlist.insert(0, win)
                win = self.nextlist.pop(-1)
        else:
            win = self.nextlist.pop(0)
            if win.is_active():
                self.nextlist.append(win)
                win = self.nextlist.pop(0)
        # Just a safety check
        if not win in self.windows:
            return
        self.windows[win].action_select_window(widget, event)
        if previous:
            self.nextlist.insert(0, win)
        else:
            self.nextlist.append(win)

    def action_select_previous(self, widget=None, event=None):
        self.action_select_next(widget, event, previous=True)

    def action_close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        for window in self.get_windows():
            window.close(t)

    def action_launch_application(self, widget=None, event=None):
        if self.lastlaunch != None \
        and time() - self.lastlaunch < 2:
                return
        if self.launcher:
            self.launcher.launch()
        elif self.app:
            self.app.launch(None, None)
        else:
            return
        self.lastlaunch = time()
        self.launch_effect = True
        self.update_state()
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000, self.remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000, self.remove_launch_effect)


    def action_show_menu(self, widget, event):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        self.hide_list()
        #Creates a popup menu
        menu = gtk.Menu()
        menu.connect('selection-done', self.menu_closed)
        if self.app and not self.launcher:
            #Add launcher item
            add_launcher_item = gtk.MenuItem('_Pin application')
            menu.append(add_launcher_item)
            add_launcher_item.connect("activate", self.add_launcher)
            add_launcher_item.show()
        if self.launcher or self.app:
            #Launch program item
            launch_program_item = gtk.MenuItem('_Launch application')
            menu.append(launch_program_item)
            launch_program_item.connect("activate", self.action_launch_application)
            launch_program_item.show()
        if self.launcher:
            #Remove launcher item
            remove_launcher_item = gtk.MenuItem('Unpin application')
            menu.append(remove_launcher_item)
            remove_launcher_item.connect("activate", self.action_remove_launcher)
            remove_launcher_item.show()
            #Edit identifier item
            edit_identifier_item = gtk.MenuItem('Edit Identifier')
            menu.append(edit_identifier_item)
            edit_identifier_item.connect("activate", self.change_identifier)
            edit_identifier_item.show()
        if (self.launcher or self.app) and self.windows:
            #Separator
            sep = gtk.SeparatorMenuItem()
            menu.append(sep)
            sep.show()
        win_nr = self.get_windows_count()
        if win_nr:
            if win_nr == 1:
                t = "window"
            else:
                t = "all windows"
            if self.get_unminimized_windows_count() == 0:
                # Unminimize all
                unminimize_all_windows_item = gtk.MenuItem('Un_minimize %s'%t)
                menu.append(unminimize_all_windows_item)
                unminimize_all_windows_item.connect("activate", self.unminimize_all_windows)
                unminimize_all_windows_item.show()
            else:
                # Minimize all
                minimize_all_windows_item = gtk.MenuItem('_Minimize %s'%t)
                menu.append(minimize_all_windows_item)
                minimize_all_windows_item.connect("activate", self.action_minimize_all_windows)
                minimize_all_windows_item.show()
            # (Un)Maximize all
            for window in self.windows:
                if not window.is_maximized() \
                and window.get_actions() & action_maximize:
                    maximize_all_windows_item = gtk.MenuItem('Ma_ximize %s'%t)
                    break
            else:
                maximize_all_windows_item = gtk.MenuItem('Unma_ximize %s'%t)
            menu.append(maximize_all_windows_item)
            maximize_all_windows_item.connect("activate", self.action_maximize_all_windows)
            maximize_all_windows_item.show()
            # Close all
            close_all_windows_item = gtk.MenuItem('_Close %s'%t)
            menu.append(close_all_windows_item)
            close_all_windows_item.connect("activate", self.action_close_all_windows)
            close_all_windows_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.dockbar.right_menu_showing = True

    def action_remove_launcher(self, widget=None, event=None):
        print 'Removing launcher ', self.identifier
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        self.launcher = None
        if not self.windows:
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            self.dockbar.groups.remove(name)
        else:
            self.dockbar.groups.remove_launcher(name)
            if self.app == None:
                # The launcher is not of gio-app type.
                # The group button will be reset with its
                # non-launcher name and icon.
                self.app = self.dockbar.find_gio_app(self.identifier)
                self.icon_factory.remove_launcher(class_group=self.class_group, app = self.app)
                self.update_name()
            self.update_state()
        self.dockbar.update_launchers_list()

    def action_minimize_all_other_groups(self, widget, event):
        self.hide_list()
        for gr in self.dockbar.groups.get_groups():
            if self != gr:
                for win in gr.get_windows():
                    win.minimize()

    def action_compiz_scale_windows(self, widget, event):
        wins = self.get_unminimized_windows()
        if not self.class_group or not wins:
            return
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return
        if settings['show_only_current_desktop']:
            path = 'scale/allscreens/initiate_key'
        else:
            path = 'scale/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                        'iclass='+self.class_group.get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay'] + 200, self.hide_list)

    def action_compiz_shift_windows(self, widget, event):
        wins = self.get_unminimized_windows()
        if not self.class_group or not wins:
            return
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return

        if settings['show_only_current_desktop']:
            path = 'shift/allscreens/initiate_key'
        else:
            path = 'shift/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                        'iclass='+self.class_group.get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay']+ 200, self.hide_list)

    def action_compiz_scale_all(self, widget, event):
        try:
            compiz_call('scale/allscreens/initiate_key','activate','root', self.root_xid)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay']+ 200, self.hide_list)

    def action_dbpref (self,widget=None, event=None):
        # Preferences dialog
        self.dockbar.on_ppm_pref(event)

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = ODict((
                                  ("select", action_select),
                                  ("close all windows", action_close_all_windows),
                                  ("minimize all windows", action_minimize_all_windows),
                                  ("maximize all windows", action_maximize_all_windows),
                                  ("launch application", action_launch_application),
                                  ("show menu", action_show_menu),
                                  ("remove launcher", action_remove_launcher),
                                  ("select next window", action_select_next),
                                  ("select previous window", action_select_previous),
                                  ("minimize all other groups", action_minimize_all_other_groups),
                                  ("compiz scale windows", action_compiz_scale_windows),
                                  ("compiz shift windows", action_compiz_shift_windows),
                                  ("compiz scale all", action_compiz_scale_all),
                                  ("show preference dialog", action_dbpref),
                                  ("no action", action_none)
                                ))


class AboutDialog():
    __instance = None

    def __init__ (self):
        if AboutDialog.__instance == None:
            AboutDialog.__instance = self
        else:
            AboutDialog.__instance.about.present()
            return
        self.about = gtk.AboutDialog()
        self.about.set_name("DockBarX Applet")
        self.about.set_version(VERSION)
        self.about.set_copyright("Copyright (c) 2008-2009 Aleksey Shaferov and Matias S\xc3\xa4rs")
        self.about.connect("response",self.about_close)
        self.about.show()

    def about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None





class DockBar(gobject.GObject):
    __gsignals__ = {
        "db-move": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
    }
    def __init__(self,applet):
        gobject.GObject.__init__(self)
        global settings
        print "Dockbarx init"
        self.applet = applet
        # self.dragging is used to tell functions wheter
        # a drag-and-drop is going on
        self.dragging = False
        self.right_menu_showing = False
        self.opacified = False
        self.opacity_values = None
        self.opacity_matches = None
        self.groups = None
        self.windows = None
        self.container = None
        self.theme = None

        wnck.set_client_type(wnck.CLIENT_TYPE_PAGER)
        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.screen.force_update()


        #--- Gconf settings
        gconf_set = { str: GCONF_CLIENT.set_string,
                     bool: GCONF_CLIENT.set_bool,
                     int: GCONF_CLIENT.set_int }
        for name, value in settings.items():
            gc_value = None
            try:
                gc_value = GCONF_CLIENT.get_value(GCONF_DIR + '/' + name)
            except:
                gconf_set[type(value)](GCONF_DIR + '/' + name , value)
            else:
                if type(gc_value) != type(value):
                    gconf_set[type(value)](GCONF_DIR + '/' + name , value)
                else:
                    settings[name] = gc_value
        GCONF_CLIENT.add_dir(GCONF_DIR, gconf.CLIENT_PRELOAD_NONE)
        GCONF_CLIENT.notify_add(GCONF_DIR, self.on_gconf_changed, None)

        # Change old settings
        group_button_actions_d = {"select or minimize group": "select",
                                  "select group": "select",
                                  "select or compiz scale group": "select"}
        for name, value in settings.items():
            if ("groupbutton" in name) and ("click" in name or "scroll" in name) \
            and value in group_button_actions_d:
                settings[name] = group_button_actions_d[value]
                GCONF_CLIENT.set_string(GCONF_DIR + '/' + name , settings[name])


        #--- Applet / Window container
        if self.applet != None:
            self.applet.set_applet_flags(gnomeapplet.HAS_HANDLE|gnomeapplet.EXPAND_MINOR)
            if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN or applet.get_orient() == gnomeapplet.ORIENT_UP:
                self.orient = "h"
                self.container = gtk.HBox()
            else:
                self.orient = "v"
                self.container = gtk.VBox()
            self.applet.connect("change-orient",self.on_change_orient)
            self.applet.connect("delete-event",self.cleanup)
            self.applet.add(self.container)
            self.applet.connect("size-allocate",self.on_applet_size_alloc)
            self.applet.connect("change_background", self.on_change_background)
            self.pp_menu_xml = """
            <popup name="button3">
                <menuitem name="About Item" verb="About" stockid="gtk-about" />
                <menuitem name="Preferences" verb="Pref" stockid="gtk-properties" />
                <menuitem name="Reload" verb="Reload" stockid="gtk-refresh" />
            </popup>
            """

            self.pp_menu_verbs = [("About", self.on_ppm_about),
                                  ("Pref", self.on_ppm_pref),
                                  ("Reload", self.reload)]
            self.applet.setup_menu(self.pp_menu_xml, self.pp_menu_verbs,None)
            self.applet_origin_x = -1000 # off screen. there is no 'window' prop
            self.applet_origin_y = -1000 # at this step
            self.applet.set_background_widget(applet) # background bug workaround
            self.applet.show_all()
        else:
            self.container = gtk.HBox()
            self.orient = "h"

        # Wait until everything is loaded
        # before adding groupbuttons
        while gtk.events_pending():
            gtk.main_iteration(False)

        self.reload()


    def reload(self, event=None, data=None):
##        pdb.set_trace()
        # Remove all old groupbuttons from container.
        for child in self.container.get_children():
            self.container.remove(child)
        if self.windows:
            # Removes windows and non-launcher group buttons
            for win in self.screen.get_windows():
                self.on_window_closed(None, win)
        if self.groups != None:
            # Removes launcher group buttons
            for name in self.groups.get_identifiers_or_paths():
                self.groups[name].hide_list()
                self.groups[name].icon_factory.remove()
                self.groups.remove(name)

        del self.groups
        del self.windows
        if self.theme:
            self.theme.remove()
        del self.theme
        gc.collect()
        print "Dockbarx reload"
        self.groups = GroupList()
        self.windows = {}
        self.apps_by_id = {}
        #--- Generate Gio apps
        self.apps_by_id = {}
        self.apps_by_exec={}
        self.apps_by_name = {}
        self.apps_by_longname={}
        for app in gio.app_info_get_all():
            id = app.get_id()
            id = id[:id.rfind('.')].lower()
            name = u""+app.get_name().lower()
            exe = app.get_executable()
            if id[:5] != 'wine-' and exe:
                # wine not supported.
                # skip empty exec
                self.apps_by_id[id] = app
                if name.find(' ')>-1:
                    self.apps_by_longname[name] = id
                else:
                    self.apps_by_name[name] = id
                if exe not in ('sudo','gksudo',
                                'java','mono',
                                'ruby','python'):
                    if exe[0] == '/':
                        exe = exe[exe.rfind('/')+1:]
                        self.apps_by_exec[exe] = id
                    else:
                        self.apps_by_exec[exe] = id


##        pdb.set_trace()
        #--- Load theme
        self.themes = self.find_themes()
        default_theme_path = None
        for theme, path in self.themes.items():
            if theme.lower() == settings['theme'].lower():
##                pdb.set_trace()
                self.theme = Theme(path)
                break
            if theme.lower == DEFAULT_SETTINGS['theme'].lower():
                default_theme_path = path
        else:
            if default_theme_path:
                # If the current theme according to gconf couldn't be found,
                # the default theme is used.
                self.theme = Theme(default_theme_path)
            else:
                # Just use one of the themes that where found if default
                # theme couldn't be found either.
                path = self.themes.values()[0]
                self.theme = Theme(path)

##        pdb.set_trace()
        #--- Set colors
        theme_colors = self.theme.get_default_colors()
        theme_alphas = self.theme.get_default_alphas()
        theme_name = self.theme.get_name().replace(' ', '_').encode()
        try:
            theme_name = theme_name.translate(None, '!?*()/#"@')
        except:
            # Todo: better error handling here.
            pass
        color_dir = GCONF_DIR + '/themes/' + theme_name
        colors.clear()
        for i in range(1, 9):
            c = 'color%s'%i
            a = 'color%s_alpha'%i
            try:
                colors[c] = GCONF_CLIENT.get_value(color_dir + '/' + c)
            except:
                if c in theme_colors:
                    colors[c] = theme_colors[c]
                else:
                    colors[c] = DEFAULT_COLORS[c]
                GCONF_CLIENT.set_string(color_dir + '/' + c , colors[c])
            try:
                colors[a] = GCONF_CLIENT.get_value(color_dir + '/' + a)
            except:
                if c in theme_alphas:
                    if'no' in theme_alphas[c]:
                        continue
                    else:
                        colors[a] = int(int(theme_alphas[c]) * 2.55 + 0.4)
                elif a in DEFAULT_COLORS:
                    colors[a] = DEFAULT_COLORS[a]
                else:
                    continue
                GCONF_CLIENT.set_int(color_dir + '/' + a , colors[a])

##        pdb.set_trace()

        self.container.set_spacing(self.theme.get_gap())
        self.container.show()

        #--- Initiate launchers
        self.launchers_by_id = {}
        self.launchers_by_exec={}
        self.launchers_by_name = {}
        self.launchers_by_longname={}

        # Get list of launchers
        gconf_launchers = []
        try:
            gconf_launchers = GCONF_CLIENT.get_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING)
        except:
            GCONF_CLIENT.set_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING, gconf_launchers)


##        pdb.set_trace()
        # Initiate launcher group buttons
        for launcher in gconf_launchers:
            identifier, path = launcher.split(';')
            if identifier == '':
                identifier = None
            self.add_launcher(identifier, path)

##        pdb.set_trace()
        #--- Initiate windows
        # Initiate group buttons with windows
        for window in self.screen.get_windows():
            self.on_window_opened(self.screen, window)

##        pdb.set_trace()

        self.screen.connect("window-opened", self.on_window_opened)
        self.screen.connect("window-closed", self.on_window_closed)
        self.screen.connect("active-window-changed", self.on_active_window_changed)
        self.screen.connect("viewports-changed", self.on_desktop_changed)
        self.screen.connect("active-workspace-changed", self.on_desktop_changed)

        self.on_active_window_changed(self.screen, None)

    def find_themes(self):
        # Reads the themes from /usr/share/dockbarx/themes and ~/.dockbarx/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        homeFolder = os.path.expanduser("~")
        theme_folder = homeFolder + "/.dockbarx/themes"
        dirs = ["/usr/share/dockbarx/themes", theme_folder]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == '.tar.gz':
                        theme_paths.append(dir+"/"+f)
        for theme_path in theme_paths:
            try:
                name = Theme.check(theme_path)
            except Exception, detail:
                print "Error loading theme from %s"%theme_path
                print detail
                name = None
            if name != None:
                name = str(name)
                themes[name] = theme_path
        if not themes:
            md = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                'No working themes found in "/usr/share/dockbarx/themes" or "~/.dockbarx/themes"')
            md.run()
            md.destroy()
            print 'No working themes found in "/usr/share/dockbarx/themes" or "~/.dockbarx/themes"'
            sys.exit(1)
        return themes

    #### GConf
    def on_gconf_changed(self, client, par2, entry, par4):
        if entry.get_value() == None:
            return
        pref_update = False
        changed_settings = []
        entry_get = { str: entry.get_value().get_string,
                      bool: entry.get_value().get_bool,
                      int: entry.get_value().get_int }
        key = entry.get_key().split('/')[-1]
        if key in settings:
            value = settings[key]
            if entry_get[type(value)]() != value:
                changed_settings.append(key)
                settings[key] = entry_get[type(value)]()

        theme_name = self.theme.get_name().replace(' ', '_').encode()
        try:
            theme_name = theme_name.translate(None, '!?*()/#"@')
        except:
            pass
        for i in range(1, 9):
            c = 'color%s'%i
            a = 'color%s_alpha'%i
            for k in (c, a):
                if entry.get_key() == "%s/themes/%s/%s"%(GCONF_DIR, theme_name, k):
                    value = colors[k]
                    if entry_get[type(value)]() != value:
                        changed_settings.append(key)
                        colors[k] = entry_get[type(value)]()

        #TODO: Add check for sane values for critical settings.

        if 'color2' in changed_settings:
            self.update_all_popup_labels()

        if 'show_only_current_desktop' in changed_settings:
            for group in self.groups.get_groups():
                group.update_state()
                group.emit('set-icongeo-grp')
                group.nextlist = None

        for key in changed_settings:
            if key == 'theme':
                self.reload()
                break
            if 'color' in key:
                self.all_windowbuttons_update_label_state()
                self.reset_all_surfaces()
                break



    def reset_all_surfaces(self):
        # Removes all saved pixbufs with active glow in groupbuttons iconfactories.
        # Use this def when the looks of active glow has been changed.
        for group in self.groups.get_groups():
            group.icon_factory.reset_surfaces()

    def all_windowbuttons_update_label_state(self):
        # Updates all window button labels. To be used when
        # settings has been changed for the labels.
        for group in self.groups.get_groups():
            for winb in group.windows.values():
                winb.update_label_state()

    def update_all_popup_labels(self):
        # Updates all popup windows' titles. To be used when
        # settings has been changed for the labels.
        for group in self.groups.get_groups():
            group.update_popup_label()


    #### Applet events
    def on_ppm_pref(self,event,data=None):
        # Starts the preference dialog
        os.spawnlp(os.P_NOWAIT,'/usr/bin/dbx_preference.py',
                    '/usr/bin/dbx_preference.py')

    def on_ppm_about(self,event,data=None):
        AboutDialog()

    def on_applet_size_alloc(self, widget, allocation):
        if widget.window:
            x,y = widget.window.get_origin()
            if x!=self.applet_origin_x or y!=self.applet_origin_y:
                # Applet and/or panel moved
                self.applet_origin_x = x
                self.applet_origin_y = y
                self.emit('db-move')

    def on_change_orient(self,arg1,data):
        for group in self.groups.get_groups():
            self.container.remove(group.button)
        self.applet.remove(self.container)
        self.container.destroy()
        self.container = None
        if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN \
        or self.applet.get_orient() == gnomeapplet.ORIENT_UP:
            self.container = gtk.HBox()
            self.orient = "h"
        else:
            self.container = gtk.VBox()
            self.orient = "v"
        self.applet.add(self.container)
        for group in self.groups.get_groups():
            self.container.pack_start(group.button,False)
        self.container.set_spacing(self.theme.get_gap())
        if settings["show_only_current_desktop"]:
            self.container.show()
            self.on_desktop_changed()
        else:
            self.container.show_all()

    def on_change_background(self, applet, type, color, pixmap):
        applet.set_style(None)
        rc_style = gtk.RcStyle()
        applet.modify_style(rc_style)
        if type == gnomeapplet.COLOR_BACKGROUND:
            applet.modify_bg(gtk.STATE_NORMAL, color)
        elif type == gnomeapplet.PIXMAP_BACKGROUND:
            style = applet.style
            style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
            applet.set_style(style)
        return


    #### Wnck events
    def on_active_window_changed(self, screen, previous_active_window):
        # Sets the right window button and group button active.
        for group in self.groups.get_groups():
            group.set_has_active_window(False)
        # Activate new windowbutton
        active_window = screen.get_active_window()
        if active_window in self.windows:
            active_group_name = self.windows[active_window]
            active_group = self.groups.get_group(active_group_name)
            if active_group:
                active_group.set_has_active_window(True)
                window_button = active_group.windows[active_window]
                window_button.set_button_active(True)

    def on_window_closed(self,screen,window):
        if window in self.windows:
            class_group_name = self.windows[window]
            group = self.groups[class_group_name]
            if group:
                group.del_window(window)
                if not group.windows and not group.launcher:
                    self.groups.remove(class_group_name)
            del self.windows[window]

    def on_window_opened(self,screen,window):
        if window.is_skip_tasklist() \
        or not (window.get_window_type() in [wnck.WINDOW_NORMAL, wnck.WINDOW_DIALOG]):
            return

        class_group = window.get_class_group()
        class_group_name = class_group.get_res_class()
        if class_group_name == "":
            class_group_name = class_group.get_name()
        # Special cases
        if class_group_name == "Wine" \
        and settings['separate_wine_apps']:
            class_group_name = self.get_wine_app_name(window)
        if class_group_name.startswith("OpenOffice.org"):
            class_group_name = self.get_ooo_app_name(window)
            if settings['separate_ooo_apps']:
                window.connect("name-changed", self.on_ooo_window_name_changed)
        self.windows[window] = class_group_name
        if class_group_name in self.groups.get_identifiers():
            # This isn't the first open window of this group.
            self.groups[class_group_name].add_window(window)
            return

        id = self.find_matching_launcher(class_group_name)
        if id:
            # The window is matching a launcher without open windows.
            path = self.launchers_by_id[id].get_path()
            self.groups.set_identifier(path, class_group_name)
            self.groups[class_group_name].add_window(window)
            self.update_launchers_list()
            self.remove_launcher_id_from_undefined_list(id)
        else:
            # First window of a new group.
            app = self.find_gio_app(class_group_name)
            self.groups[class_group_name] = GroupButton(self,class_group, identifier=class_group_name, app=app)
            self.groups[class_group_name].add_window(window)

    def find_matching_launcher(self, identifier):
        id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.launchers_by_id:
                id = rc
                print "Opened window matched with launcher on id:", rc
            elif rc in self.launchers_by_name:
                id = self.launchers_by_name[rc]
                print "Opened window matched with launcher on name:", rc
            elif rc in self.launchers_by_exec:
                id = self.launchers_by_exec[rc]
                print "Opened window matched with launcher on executable:", rc
            else:
                for lname in self.launchers_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == ' ') \
                        or (pos+len(rc) == len(lname) and lname[pos-1] == ' ') \
                        or (lname[pos-1] == ' ' and lname[pos+len(rc)] == ' '):
                            id = self.launchers_by_longname[lname]
                            print "Opened window matched with launcher on long name:", rc
                            break

            if id == None and rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    if rc in self.launchers_by_id:
                        id = rc
                        print "Partial name for open window matched with id:", rc
                    elif rc in self.launchers_by_name:
                        id = self.launchers_by_name[rc]
                        print "Partial name for open window matched with name:", rc
                    elif rc in self.launchers_by_exec:
                        id = self.launchers_by_exec[rc]
                        print "Partial name for open window matched with executable:", rc
        return id

    def find_gio_app(self, identifier):
        app = None
        app_id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.apps_by_id:
                app_id = rc
                print "Opened window matched with gio app on id:", rc
            elif rc in self.apps_by_name:
                app_id = self.apps_by_name[rc]
                print "Opened window matched with gio app on name:", rc
            elif rc in self.apps_by_exec:
                app_id = self.apps_by_exec[rc]
                print "Opened window matched with gio app on executable:", rc
            else:
                for lname in self.apps_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == ' ') \
                        or (pos+len(rc) == len(lname) and lname[pos-1] == ' ') \
                        or (lname[pos-1] == ' ' and lname[pos+len(rc)] == ' '):
                            app_id = self.apps_by_longname[lname]
                            print "Opened window matched with gio app on longname:", rc
                            break
            if not app_id:
                if rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    print " trying to find as",rc
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    ### keys()
                    if rc in self.apps_by_id.keys():
                        app_id = rc
                        print " found in apps id list as",rc
                    elif rc in self.apps_by_name.keys():
                        app_id = self.apps_by_name[rc]
                        print " found in apps name list as",rc
                    elif rc in self.apps_by_exec.keys():
                        app_id = self.apps_by_exec[rc]
                        print " found in apps exec list as",rc
            if app_id:
                app = self.apps_by_id[app_id]
        return app

    def get_wine_app_name(self, window):
        # This function guesses an application name base on the window name
        # since all wine applications are has the identifier "Wine".
        name = window.get_name()
        # if the name has " - " in it the application is usually the part after it.
        name = name.split(" - ")[-1]
        return "Wine__" + name

    def get_ooo_app_name(self, window):
        # Separates the differnt openoffice applications from each other
        # The names are chosen to match the gio app ids.
        if not settings['separate_ooo_apps']:
            return "openoffice.org-writer"
        name = window.get_name()
        for app in ['Calc', 'Impress', 'Draw', 'Math']:
            if name.endswith(app):
                return "openoffice.org-" + app.lower()
        else:
            return "openoffice.org-writer"

    def on_ooo_window_name_changed(self, window):
        identifier = None
        for group in self.groups.get_groups():
            if window in group.windows:
                identifier = group.identifier
                break
        else:
            print "OOo app error: Name changed but no group found."
        if identifier != self.get_ooo_app_name(window):
            self.on_window_closed(self.screen, window)
            self.on_window_opened(self.screen, window)
            if window == self.screen.get_active_window():
                self.on_active_window_changed(self.screen, None)


    #### Desktop events
    def on_desktop_changed(self, screen=None, workspace=None):
        if not settings['show_only_current_desktop']:
            return
        for group in self.groups.get_groups():
            group.update_state()
            group.emit('set-icongeo-grp')
            group.nextlist = None




    #### Launchers
    def add_launcher(self, identifier, path):
        """Adds a new launcher from a desktop file located at path and from the name"""
        try:
            launcher = Launcher(identifier, path, dockbar=self)
        except:
            print "ERROR: Couldn't read desktop entry for " + identifier
            print "path: "+ path
            return

        self.groups.add_group(identifier, GroupButton(self, launcher=launcher), path)
        if identifier == None:
            id = path[path.rfind('/')+1:path.rfind('.')].lower()
            name = u""+launcher.get_entry_name().lower()
            exe = launcher.get_executable()
            self.launchers_by_id[id] = launcher
            if name.find(' ')>-1:
                self.launchers_by_longname[name] = id
            else:
                self.launchers_by_name[name] = id
            self.launchers_by_exec[exe] = id

    def make_new_launcher(self, path, calling_button):
        # Creates a new launcher with a desktop file located at path
        # and lets the user enter the proper res class name in a
        # dialog. The new laucnher is inserted at the right (or under)
        # the group button that the launcher was dropped on.
        try:
            launcher = Launcher(None, path, dockbar=self)
        except Exception, detail:
            print "ERROR: Couldn't read dropped file. Was it a desktop entry?"
            print "Error message:", detail
            return False

        id = path[path.rfind('/')+1:path.rfind('.')].lower()
        name = u""+launcher.get_entry_name().lower()
        exe = launcher.get_executable()

        if name.find(' ')>-1:
            lname = name
        else:
            lname = None

        if exe[0] == '/':
            exe = exe[exe.rfind('/')+1:]

        print "New launcher dropped"
        print "id: ", id
        if lname:
            print "long name: ", name
        else:
            print "name: ", name
        print "executable: ", exe
        print
        for identifier in self.groups.get_non_launcher_names():
            rc = u""+identifier.lower()
            if not rc:
                continue
            if rc == id:
                break
            if rc == name:
                break
            if rc == exe:
                break
            if lname:
                pos = lname.find(rc)
                if pos>-1: # Check that it is not part of word
                    if (pos==0) and (lname[len(rc)] == ' '):
                        break
                    elif (pos+len(rc) == len(lname)) and (lname[pos-1] == ' '):
                        break
                    elif (lname[pos-1] == ' ') and (lname[pos+len(rc)] == ' '):
                        break
            if rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    if rc == id:
                        break
                    elif rc == name:
                        break
                    elif rc == exe:
                        break
        else:
            # No open windows where found that could be connected
            # with the new launcher. Id, name and exe will be stored
            # so that it can be checked against new windows later.
            identifier = None
            self.launchers_by_id[id] = launcher
            if lname:
                self.launchers_by_longname[name] = id
            else:
                self.launchers_by_name[name] = id
            self.launchers_by_exec[exe] = id

        class_group = None
        if identifier:
            launcher.set_identifier(identifier)
        # Remove existing groupbutton for the same program
        winlist = []
        if calling_button in (identifier, path):
            index = self.groups.get_index(calling_button)
            group = self.groups[calling_button]
            class_group = group.get_class_group()
            # Get the windows for repopulation of the new button
            winlist = group.windows.keys()
            # Destroy the group button
            group.popup.destroy()
            group.button.destroy()
            group.winlist.destroy()
            self.groups.remove(calling_button)
        else:
            if identifier in self.groups.get_identifiers():
                group = self.groups[identifier]
                class_group = group.get_class_group()
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(identifier)
            elif path in self.groups.get_undefined_launchers():
                group = self.groups[path]
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(path)

            # Insert the new button after (to the
            # right of or under) the calling button
            index = self.groups.get_index(calling_button) + 1
        button = GroupButton(self, class_group=class_group, identifier=identifier, launcher=launcher, index=index)
        self.groups.add_group(identifier, button, path, index)
        self.update_launchers_list()
        for window in winlist:
            self.on_window_opened(self.screen, window)
        return True

    def identifier_dialog(self, identifier=None):
        # Input dialog for inputting the identifier.
        dialog = gtk.MessageDialog(
            None,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL,
            None)
        dialog.set_title('Identifier')
        dialog.set_markup('<b>Enter the identifier here</b>')
        dialog.format_secondary_markup(
            'You should have to do this only if the program fails to recognice its windows. '+ \
            'If the program is already running you should be able to find the identifier of the program from the dropdown list.')
        #create the text input field
        #entry = gtk.Entry()
        combobox = gtk.combo_box_entry_new_text()
        entry = combobox.get_child()
        if identifier:
            entry.set_text(identifier)
        # Fill the popdown list with the names of all class names of buttons that hasn't got a launcher already
        for name in self.groups.get_non_launcher_names():
            combobox.append_text(name)
        entry = combobox.get_child()
        #entry.set_text('')
        #allow the user to press enter to do ok
        entry.connect("activate", lambda widget: dialog.response(gtk.RESPONSE_OK))
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label('Identifier:'), False, 5, 5)
        hbox.pack_end(combobox)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            text = entry.get_text()
        else:
            text = ''
        dialog.destroy()
        return text

    def move_groupbutton(self, name, calling_button=None, index=None):
        # Moves the button to the right of the calling button or to
        # index.

        #Remove the groupbutton that should be moved
        move_group = self.groups.get_group(name)
        move_path = self.groups.get_launcher_path(name)
        self.container.remove(move_group.button)
        self.groups.remove(name)

        # index is not checking buttonposition as of now.
        # If posible use calling_button instead
        if index:
            pass
        elif calling_button:
            index = self.groups.get_index(calling_button) + 1
        else:
            print "Error: cant move button without either a index or the calling button's name"
            return
        # Insterts the button on it's index by removing
        # and repacking the buttons that should come after it
        repack_list = self.groups.get_groups()[index:]
        for group in repack_list:
            self.container.remove(group.button)
        self.container.pack_start(move_group.button, False)
        for group in repack_list:
            self.container.pack_start(group.button, False)
        self.groups.add_group(name, move_group, move_path, index)
        self.update_launchers_list()

    def change_identifier(self, path, identifier=None):
        identifier = self.identifier_dialog(identifier)
        if not identifier:
            return False
        winlist = []
        if identifier in self.groups.get_identifiers():
                group = self.groups[identifier]
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(identifier)
        self.groups.set_identifier(path, identifier)
        for window in winlist:
            self.on_window_opened(self.screen, window)
        self.update_launchers_list()

    def update_launchers_list(self):
        # Saves launchers_list to gconf.
        launchers_list = self.groups.get_launchers_list()
        gconf_launchers = []
        for identifier, path in launchers_list:
            if identifier == None:
                identifier = ''
            gconf_launchers.append(identifier + ';' + path)
        GCONF_CLIENT.set_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING, gconf_launchers)

    def remove_launcher_id_from_undefined_list(self, id):
        self.launchers_by_id.pop(id)
        for l in (self.launchers_by_name, self.launchers_by_exec,
                     self.launchers_by_longname):
            for key, value in l.items():
                if value == id:
                    l.pop(key)
                    break

    def cleanup(self,event):
        del self.applet


class DockBarWindow():
    """DockBarWindow sets up the window if run-in-window is used."""
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(200,40)
        self.window.show()
        self.window.set_property("skip-taskbar-hint",True)
        self.window.set_keep_above(True)
        self.window.connect ("delete_event",self.delete_event)
        self.window.connect ("destroy",self.destroy)

        self.dockbar = DockBar(None)
        hbox = gtk.HBox()
        button = gtk.Button('Pref')
        button.connect('clicked', self.dockbar.on_ppm_pref)
        hbox.pack_start(button, False)
        hbox.pack_start(self.dockbar.container, False)
        eb = gtk.EventBox()
##        eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#2E2E2E"))
        eb.add(hbox)
        self.window.add(eb)
        eb.show_all()
        ##self.window.add(self.dockbar.container)

    def delete_event (self,widget,event,data=None):
        return False

    def destroy (self,widget,data=None):
        gtk.main_quit()

    def main(self):
        gtk.main()


def dockbar_factory(applet, iid):
    dockbar = DockBar(applet)
    applet.set_background_widget(applet)
    applet.show_all()
    return True

##gc.enable()

if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":
    dockbarwin = DockBarWindow()
    dockbarwin.main()
else:
    gnomeapplet.bonobo_factory("OAFIID:GNOME_DockBarXApplet_Factory",
                                     gnomeapplet.Applet.__gtype__,
                                     "dockbar applet", "0", dockbar_factory)
