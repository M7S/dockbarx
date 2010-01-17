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


# A try to fix the random crashes on start-up
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
##import pdb


VERSION = 'x.0.24.0'

TARGET_TYPE_GROUPBUTTON = 134 # Randomly chosen number, is it used anymore?

GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = '/apps/dockbarx'

BUS = dbus.SessionBus()

PREFDIALOG = None # Non-constant! Remove or rename!?

DEFAULT_SETTINGS = {  "theme": "default",
                      "groupbutton_attention_notification_type": "red",
                      "workspace_behavior": "switch",
                      "popup_delay": 250,
                      "popup_align": "center",
                      "no_popup_for_one_window": False,

                      "select_one_window": "select or minimize window",
                      "select_multiple_windows": "select all",

                      "active_glow_color": "#FFFF75",
                      "active_glow_alpha": 160,
                      "popup_color": "#333333",
                      "popup_alpha": 205,

                      "active_text_color": "#FFFF75",
                      "minimized_text_color": "#9C9C9C",
                      "normal_text_color": "#FFFFFF",

                      "opacify": False,
                      "opacify_group": False,
                      "opacify_alpha": 11,

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
            tar.close()
            raise
        tar.close()
        return theme_handler.get_name()

    def __init__(self, path_to_tar):
        tar = taropen(path_to_tar)
        config = tar.extractfile('config')

        parser = make_parser()
        theme_handler = ThemeHandler()
        parser.setContentHandler(theme_handler)
        parser.parse(config)
        self.theme = theme_handler.get_dict()
        self.name = theme_handler.get_name()
##        self.print_dict(self.theme)

        self.pixbufs = {}
        pixmaps = {}
        if self.theme.has_key('pixmaps'):
            pixmaps = self.theme['pixmaps']['content']
        for (type, d) in pixmaps.items():
            if type == 'pixmap_from_file':
                self.pixbufs[d['name']] = self.load_pixbuf(tar, d['file'])

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

    def has_pixbuf(self, name):
        if name in self.pixbufs:
            return True
        else:
            return False

    def get_pixbuf(self, name):
        return self.pixbufs[name]

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

class IconFactory():
    """IconFactory takes care of finding the right icon pixbuf for a program and prepares the pixbuf."""
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
    # Double width/height icons for drag and drop situations.
    DRAG_DROPP = 1<<11
    TYPE_DICT = {'some_minimized':SOME_MINIMIZED,
                 'all_minimized':ALL_MINIMIZED,
                 'launcher':LAUNCHER,
                 'mouse_over':MOUSE_OVER,
                 'needs_attention':NEEDS_ATTENTION,
                 'blink':BLINK,
                 'active':ACTIVE}

    def __init__(self, dockbar, class_group=None, launcher=None, app=None):
        self.dockbar = dockbar
        self.theme = dockbar.theme
        self.app = app
        self.launcher = launcher
        if self.launcher and self.launcher.app:
            self.app = self.launcher.app
            self.launcher = None
        self.class_group = class_group

        self.pixbuf = None
        self.pixbufs = None

        self.max_win_nr = self.theme.get_windows_cnt()

    def __del__(self):
        self.app = None
        self.launcher = None
        self.class_group = None
        self.pixbuf = None
        self.pixbufs = None
        self.dockbar = None
        self.theme = None

    def remove_launcher(self, class_group = None, app = None):
        self.launcher = None
        self.class_group = class_group
        self.app = app
        self.pixbufs = {}
        self.pixbuf = None


    def set_size(self, size):
        # Sets the icon size to size - 2 (to make room for a glow
        # around the icon), loads the icon in that size
        # and empties the pixbufs so that new pixbufs will be made in
        # the right size when requested.
        self.size = size
        self.pixbufs = {}

    def reset_active_pixbufs(self):
        pixbufs = self.pixbufs.keys()
        for pixbuf in pixbufs:
            if pixbuf & self.ACTIVE:
                self.pixbufs.pop(pixbuf)


    def pixbuf_update(self, type = 0):
        # Checks if the requested pixbuf is already drawn and returns it if it is.
        # Othervice the pixbuf is drawn, saved and returned.
        self.win_nr = type & 15
        if self.win_nr > self.max_win_nr:
            type = (type - self.win_nr) | self.max_win_nr
            self.win_nr = self.max_win_nr
        if self.pixbufs.has_key(type):
            return self.pixbufs[type]
        self.temp = {}
        pixbuf = None
        commands = self.theme.get_icon_dict()
        self.ar = self.theme.get_aspect_ratio()
        self.type = type
        for command, args in commands.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                pixbuf = f(pixbuf, **args)
        # Todo: add size correction.
        if type & self.DRAG_DROPP:
            pixbuf = self.double_pixbuf(pixbuf, self.dockbar.orient)
        self.temp = None
        self.pixbufs[type] = pixbuf
        return pixbuf

    def double_pixbuf(self, pixbuf, direction = 'h'):
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        # Make a background almost twice as wide or high
        # as the pixbuf depending on panel orientation.
        if direction == 'v':
            h = h * 2 - 2
        else:
            w = w * 2 - 2
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        context = cairo.Context(surface)
        ctx = gtk.gdk.CairoContext(context)
        # Put arrow pointing to the empty part on it.
        if direction == 'v':
            ctx.move_to(2, h / 2 + 2)
            ctx.line_to(w - 2, h / 2 + 2)
            ctx.line_to(w / 2, 0.65 * h + 2)
            ctx.close_path()
        else:
            ctx.move_to(w / 2 + 2, 2)
            ctx.line_to(w / 2 + 2, h - 2)
            ctx.line_to(0.65 * w, h / 2)
            ctx.close_path()
        ctx.set_source_rgb(0, 0, 0)
        ctx.fill()
        sio = StringIO()
        surface.write_to_png(sio)
        sio.seek(0)
        loader = gtk.gdk.PixbufLoader()
        loader.write(sio.getvalue())
        loader.close()
        sio.close()
        background = loader.get_pixbuf()
        # And put the pixbuf on the left/upper half of it.
        pixbuf.composite(background, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        return background


    #### Flow commands
    def command_if(self, pixbuf, type=None, windows=None, content=None):
        if content == None:
            return pixbuf
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
        # Check if the type is right
        if type != None:
            negation = False
            if type[0] == "!" :
                type = type[1:]
                negation = True
            is_type = bool(type in self.TYPE_DICT \
                      and self.type & self.TYPE_DICT[type])
            if (is_type ^ negation):
                type = True
            else:
                type = False
        else:
            type = True

        #Check if the numbers of windows is right
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
                return pixbuf
            if len(l) == 1:
                if (l[0] == self.win_nr) ^ negation:
                    windows = True
                else:
                    windows = False
            elif (l[0]<=self.win_nr and self.win_nr<=l[1]) ^ negation:
                windows = True
            else:
                windows = False
        else:
            windows = True

        if type and windows:
            for command,args in content.items():
                try:
                    f = getattr(self,"command_%s"%command)
                except:
                    raise
                else:
                    pixbuf = f(pixbuf, **args)
        return pixbuf

    def command_pixmap_from_self(self, pixbuf, name, content=None):
        if not name:
            print "Theme Error: no name given for pixbuf_from_self"
            raise Exeption
        self.temp[name]=pixbuf.copy()
        if content == None:
            return pixbuf
        for command,args in content.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                self.temp[name] = f(self.temp[name], **args)
        return pixbuf

    def command_pixmap(self, pixbuf, name, content=None, size=None):
        if size != None:
            # TODO: Fix for different height and width
            w = h = self.size + int(size)
        elif pixbuf == None:
            w = h = self.size
        else:
            w = pixbuf.get_width()
            h = pixbuf.get_height()
        empty = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
        empty.fill(0x00000000)
        self.temp[name]=empty
        if content == None:
            return pixbuf
        for command,args in content.items():
            try:
                f = getattr(self,"command_%s"%command)
            except:
                raise
            else:
                self.temp[name] = f(self.temp[name], **args)
        return pixbuf


    #### Get icon
    def command_get_icon(self,pixbuf=None, size=0):
        size = int(size)
        if size < 0:
            size = self.size + size
        else:
            size = self.size
        if not self.pixbuf or not (self.pixbuf.get_width() == size or self.pixbuf.get_height() == size):
            self.pixbuf = self.find_icon_pixbuf(size)
        if self.pixbuf.get_width() != self.pixbuf.get_height():
            if self.pixbuf.get_width() < self.pixbuf.get_height():
                h = size
                w = self.pixbuf.get_width() * size/self.pixbuf.get_height()
            elif self.pixbuf.get_width() > self.pixbuf.get_height():
                w = size
                h = self.pixbuf.get_height() * size/self.pixbuf.get_width()
            background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size, size)
            background.fill(0x00000000)
            self.pixbuf = self.pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
            woffset = int(float(size - w) / 2 + 0.5)
            hoffset = int(float(size - h) / 2 + 0.5)
            self.pixbuf.composite(background, woffset, hoffset, w, h, woffset, hoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
            self.pixbuf = background
        elif self.pixbuf.get_width() != size:
            self.pixbuf = self.pixbuf.scale_simple(size, size, gtk.gdk.INTERP_BILINEAR)
        return self.pixbuf.copy()


    def find_icon_pixbuf(self, size):
        # Returns the icon pixbuf for the program. Uses the following metods:

        # 1) If it is a launcher, return the icon from the launcher's desktopfile
        # 2) Match the res_class against gio app ids to try to get a desktopfile
        #    that way.
        # 3) Check if the res_class fits an iconname.
        # 4) Search in path after a icon matching reclass.
        pixbuf = None
        if self.class_group:
            name = self.class_group.get_res_class().lower()
        else:
            name = "" # Is this clever? Can there be a "" icon?

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
                icon_name = name
            elif icon.__class__ == gio.ThemedIcon:
                icon_name = icon.get_names()[0]
            else:
                icon_name = name
        else:
            icon_name = name

        if self.icon_theme.has_icon(icon_name):
            pixbuf = self.icon_theme.load_icon(icon_name,size,0)
            return pixbuf
        if icon_name[-4:] == ".svg" or icon_name[-4:] == ".png" or icon_name[-4:] == ".xpm":
            icon_name = icon_name[:-4]
            if self.icon_theme.has_icon(icon_name):
                pixbuf = self.icon_theme.load_icon(icon_name,size,0)
                if pixbuf != None:
                    return pixbuf

        pixbuf = self.icon_search_in_data_path(icon_name, size)

        if pixbuf == None and self.class_group:
            pixbuf = self.class_group.get_icon().copy()
        elif pixbuf == None:
            # If no pixbuf has been found (can only happen for an unlaunched
            # launcher), make an empty pixbuf and show a warning.
            if self.icontheme.has_icon('application-default-icon'):
                pixbuf = self.icontheme.load_icon('application-default-icon',size,0)
            else:
                pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size,size)
                pixbuf.fill(0x00000000)
            dialog = gtk.MessageDialog(parent=None,
                                  flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_WARNING,
                                  buttons=gtk.BUTTONS_OK,
                                  message_format='Cannot load icon for launcher '+ self.launcher.get_res_class()+'.')
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
    def command_get_pixmap(self, pixbuf, name, size=0):
        if pixbuf == None:
            if self.dockbar.orient == 'v':
                width = int(self.size * ar)
                height = self.size
            else:
                width = self.size
                height = int(self.size * ar)
        else:
            width = self.pixbuf.get_width()
            height = self.pixbuf.get_height()
        if self.theme.has_pixbuf(name):
            pixbuf = self.theme.get_pixbuf(name)
            pixbuf = temp.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
        else:
            print "theme error: pixmap %s not found"%name
        return pixbuf

    def command_fill(self, pixbuf, color, opacity=100):
        if color == "active_color":
            color = settings['active_glow_color']
        if color[0]=="#":
            color = color[1:]
        try:
            f = int(color,16)<<8
        except ValueError:
            print "Theme error: the color attribute for fill should be a six digit hex string eg. \"#FFFFFF\" or the name of a DockBarX color eg. \"active_color\"."
            raise
        if opacity == "active_opacity":
            opacity = settings['active_glow_alpha']
        else:
            opacity = int(int(opacity)*2.55 + 0.4)
        f += opacity
        pixbuf.fill(f)
        return pixbuf

    def command_combine(self, pixbuf, pix1, pix2, degrees=90):
        # Combines left half of pixbuf with right half of pixbuf2.
        # The transition between the two halves are soft.
        if pix1=="self":
            p1 = pixbuf
        elif pix1 in self.temp:
            p1 = self.temp[pix1]
        elif self.theme.has_pixbuf(pix1):
            bg = self.theme.get_pixbuf(pix1)
        else:
            print "theme error: pixmap %s not found"%pix1
        if pix2=="self":
            p2 = pixbuf
        elif pix2 in self.temp:
            p2 = self.temp[pix2]
        elif self.theme.has_pixbuf(pix2):
            bg = self.theme.get_pixbuf(pix2)
        else:
            print "theme error: pixmap %s not found"%pix2

        #TODO: Add degrees
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, p1.get_width(), p1.get_height())
        context = cairo.Context(surface)
        ctx = gtk.gdk.CairoContext(context)

        linear = cairo.LinearGradient(0, 0, p1.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 0.5)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 1)
        ctx.set_source_pixbuf(p2, 0, 0)
        #ctx.mask(linear)
        ctx.paint()

        linear = cairo.LinearGradient(0, 0, p1.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 1)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 0)
        ctx.set_source_pixbuf(p1, 0, 0)
        ctx.mask(linear)

        sio = StringIO()
        surface.write_to_png(sio)
        sio.seek(0)
        loader = gtk.gdk.PixbufLoader()
        loader.write(sio.getvalue())
        loader.close()
        sio.close()
        return loader.get_pixbuf()

    def command_transp_sat(self, pixbuf, opacity=100, saturation=100):
        # Makes the icon desaturized and/or transparent.
        opacity = min(255, int(int(opacity)*2.55 + 0.5))
        saturation = min(1.0, float(saturation)/100)
        icon_transp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        icon_transp.fill(0x00000000)
        pixbuf.composite(icon_transp, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, opacity)
        icon_transp.saturate_and_pixelate(icon_transp, saturation, False)
        return icon_transp

    def command_composite(self, pixbuf, bg, fg, opacity=100, xoffset=0, yoffset=0):
        if fg=="self":
            fg = pixbuf
        elif fg in self.temp:
            fg = self.temp[fg]
        elif self.theme.has_pixbuf(fg):
            fg = self.theme.get_pixbuf(fg)
            fg = fg.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        else:
            print "theme error: pixmap %s not found"%fg
        if bg=="self":
            bg = pixbuf
        elif bg in self.temp:
            bg = self.temp[bg]
        elif self.theme.has_pixbuf(bg):
            bg = self.theme.get_pixbuf(bg)
            bg = bg.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        else:
            print "theme error: pixmap %s not found"%bg
        opacity = min(255, int(int(opacity)*2.55 + 0.5))
        xoffset = int(xoffset)
        yoffset = int(yoffset)
        if xoffset >= 0:
            if xoffset + fg.get_width() > bg.get_width():
                w = fg.get_width() - xoffset
            else:
                w = fg.get_width()
        else:
            w = fg.get_width() + xoffset
        if yoffset >= 0:
            if yoffset + fg.get_height() > bg.get_height():
                h = fg.get_height() - yoffset

            else:
                h = fg.get_height()
        else:
            h = fg.get_height() + yoffset
        x = max(xoffset, 0)
        y = max(yoffset, 0)
        if w <= 0 or h <=0 or x > bg.get_width or y > bg.get_height:
            # Fg is offset out of the picture.
            return bg
        fg.composite(bg, x, y, w, h, xoffset, yoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, opacity)
        return bg

    def command_shrink(self, pixbuf, percent=0, pixels=0):
        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        background.fill(0x00000000)
        w0 = pixbuf.get_width()
        h0 = pixbuf.get_height()
        w = int(((100-int(percent)) * w0)/100)-int(pixels)
        h = int(((100-int(percent)) * h0)/100)-int(pixels)
        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
        x = int(float(w0 - w) / 2 + 0.5)
        y = int(float(h0 - h) / 2 + 0.5)
        pixbuf.composite(background, x, y, w, h, x, y, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
        return background

    def command_correct_size(self, pixbuf):
        if self.dockbar.orient == 'v':
            width = self.size
            height = int(self.size * self.ar)
        else:
            width = int(self.size * self.ar)
            height = self.size
        if pixbuf.get_width() == width and pixbuf.get_height() == height:
            return pixbuf
        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, height)
        background.fill(0x00000000)
        woffset = int(float(width - pixbuf.get_width()) / 2 + 0.5)
        hoffset = int(float(height - pixbuf.get_height()) / 2 + 0.5)
        pixbuf.composite(background, woffset, hoffset, pixbuf.get_width(), pixbuf.get_height(), \
                         woffset, hoffset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
        return background

    def command_glow(self, pixbuf, color, opacity=100):
        # Adds a glow around the parts of the pixbuf that isn't completely
        # transparent.


        # Transparency
        if opacity == "active_opacity":
            alpha = settings['active_glow_alpha']
        else:
            alpha = int(int(opacity) * 2.55 + 0.2)
        # Thickness (pixels)
        tk = 2

        colorpb = self.command_colorize(pixbuf, color)
        bg = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        bg.fill(0x00000000)
        glow = bg.copy()
        # Prepare the glow that should be put bind the icon
        tk1 = tk - int(tk/2)
        for x, y in ((-tk1,-tk1), (-tk1,tk1), (tk1,-tk1), (tk1,tk1)):
            colorpb.composite(glow, 0, 0, pixbuf.get_width(), pixbuf.get_height(), x, y, 1, 1, gtk.gdk.INTERP_BILINEAR, 170)
        for x, y in ((-tk,-tk), (-tk,tk), (tk,-tk), (tk,tk)):
            colorpb.composite(glow, 0, 0, pixbuf.get_width(), pixbuf.get_height(), x, y, 1, 1, gtk.gdk.INTERP_BILINEAR, 70)
        glow.composite(bg, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, alpha)
        # Now add the pixbuf above the glow
        pixbuf.composite(bg, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        return bg

    def command_colorize(self, pixbuf, color):
        # Changes the color of all pixels to color.
        # The pixels alpha values are unchanged.

        # Convert color hex-string (format '#FFFFFF')to int r, g, b
        if color == "active_color":
            color = settings['active_glow_color']
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        except ValueError:
            print "Theme error: the color attribute for glow command should be a six digit hex string eg. \"#FFFFFF\" or the name of a DockBarX color eg. \"active_color\"."
            return pixbuf

        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = r
                pix[1] = g
                pix[2] = b
        return pixbuf

    def command_bright(self, pixbuf, strength = None, strenght = None):
        # Makes the pixbuf shift lighter.
        if strength == None and strenght != None:
            # For compability with older themes.
            strength = strenght
        strength = int(int(strength) * 2.55 + 0.4)
        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = min(255, int(pix[0]) + strength)
                pix[1] = min(255, int(pix[1]) + strength)
                pix[2] = min(255, int(pix[2]) + strength)
        return pixbuf

    def command_alpha_mask(self, pixbuf, mask):
        if mask in self.temp:
            mask = self.temp[mask]
        elif self.theme.has_pixbuf(mask):
            mask = self.theme.get_pixbuf(mask)
        mask = mask.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        pixbuf = pixbuf.copy()
        rows = pixbuf.get_pixels_array()
        mask_rows = mask.get_pixels_array()
        for m in range(len(rows)):
            for n in range(len(rows[m])):
                rows[m, n][3] = int(rows[m, n][3]) * int(mask_rows[m, n][0]) / 255
        return pixbuf

class CairoPopup():
    """CairoPopup is a transparent popup window with rounded corners"""
    def __init__(self, colormap):
        gtk.widget_push_colormap(colormap)
        self.window = gtk.Window(gtk.WINDOW_POPUP)
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        gtk.widget_pop_colormap()
        self.vbox = gtk.VBox()

        # Initialize colors, alpha transparency
        self.window.set_app_paintable(1)

        self.window.connect("expose_event", self.expose)


    def expose(self, widget, event):
        self.setup()
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

    def setup(self):
        # Set window shape from alpha mask of background image
        w,h = self.window.get_size()
        if w==0: w = 800
        if h==0: h = 600
        self.pixmap = gtk.gdk.Pixmap (None, w, h, 1)
        ctx = self.pixmap.cairo_create()
        ctx.save()
        ctx.set_source_rgba(1, 1, 1,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()
        ctx.restore()
        self.draw_frame(ctx, w, h)

        if self.window.is_composited():
            self.window.window.shape_combine_mask(None, 0, 0)
            ctx.rectangle(0,0,w,h)
            ctx.fill()
            self.window.input_shape_combine_mask(self.pixmap,0,0)
        else:
            self.window.shape_combine_mask(self.pixmap, 0, 0)

    def draw_frame(self, ctx, w, h):
        ctx.save()
        r = 6
        bg = 0.2
        color = settings['popup_color']
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255

        alpha= float(settings['popup_alpha']) / 255

        ctx.move_to(0,r)
        ctx.arc(r, r, r, -pi, -pi/2)
        ctx.arc(w-r, r, r, -pi/2, 0)
        ctx.arc(w-r, h-r, r, 0, pi/2)
        ctx.arc(r, h-r, r, pi/2, pi)
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
        ctx.restore()
        ctx.clip()

    def __del__(self):
        self.window = None
        self.ctx = None
        self.pixmap = None
        self.vbox = None


class Launcher():
    def __init__(self, res_class, path, dockbar=None):
        self.res_class = res_class
        self.lastlaunch = None
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


    def get_res_class(self):
        return self.res_class

    def set_res_class(self, res_class):
        self.res_class = res_class

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
        if self.lastlaunch != None:
            if time() - self.lastlaunch < 2:
                return
        os.chdir(os.path.expanduser('~'))
        if self.app:
            print "Executing", self.app.get_name()
            self.lastlaunch = time()
            return self.app.launch(None, None)
        else:
            print 'Executing ' + self.desktop_entry.getExec()
            self.execute(self.desktop_entry.getExec())
            self.lastlaunch = time()

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
    """GroupList contains a list with touples containing resclass, group button and launcherpath."""
    def __init__(self):
        self.list = []

    def __del__(self):
        self.list = None

    def __getitem__(self, name):
        return self.get_group(name)

    def __setitem__(self, res_class, group_button):
        self.add_group(res_class, group_button)

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
        return self.get_res_classes().__iter__()

    def add_group(self, res_class, group_button, path_to_launcher=None, index=None):
        t = (res_class, group_button, path_to_launcher)
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

    def set_launcher_path(self, res_class, path):
        if not res_class:
            return
        for t in self.list:
            if t[0] == res_class:
                n = [t[0], t[1], path]
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                return True

    def set_res_class(self, path, res_class):
        for t in self.list:
            if t[2] == path:
                n = (res_class, t[1], t[2])
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                n[1].res_class_changed(res_class)
                return True

    def get_groups(self):
        grouplist = []
        for t in self.list:
            grouplist.append(t[1])
        return grouplist

    def get_res_classes(self):
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

    def remove_launcher(self, res_class):
        if not res_class:
            return
        for t in self.list:
            if res_class == t[0]:
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
        self.name = window.get_name()
        self.window = window
        self.locked = False
        self.is_active_window = False
        self.needs_attention = False
        self.opacified = False
        self.button_pressed = False

        self.window_button = gtk.EventBox()
        self.window_button.set_visible_window(False)
        self.label = gtk.Label()
        self.on_window_name_changed(self.window)

        if window.needs_attention():
            self.needs_attention = True
            self.groupbutton.needs_attention_changed()

        self.window_button_icon = gtk.Image()
        self.on_window_icon_changed(window)
        hbox = gtk.HBox()
        hbox.pack_start(self.window_button_icon, False, padding = 2)
        hbox.pack_start(self.label, False)
        self.window_button.add(hbox)


        self.update_label_state()

        groupbutton.winlist.pack_start(self.window_button,False)

        #--- Events
        self.window_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.window_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.window_button.connect("button-press-event",self.on_window_button_press_event)
        self.window_button.connect("button-release-event",self.on_window_button_release_event)
        self.window_button.connect("scroll-event",self.on_window_button_scroll_event)
        self.window.connect("state-changed",self.on_window_state_changed)
        self.window.connect("icon-changed",self.on_window_icon_changed)
        self.window.connect("name-changed",self.on_window_name_changed)

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
        if mouseover:
            attr_list.insert(pango.AttrUnderline(pango.UNDERLINE_SINGLE, 0, 50))
        if self.needs_attention:
            attr_list.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, 50))
        if self.is_active_window:
            color = settings['active_text_color']
        elif self.window.is_minimized():
            color = settings['minimized_text_color']
        else:
            color = settings['normal_text_color']
        # color is a hex-string (like '#FFFFFF').
        r = int(color[1:3], 16)*256
        g = int(color[3:5], 16)*256
        b = int(color[5:7], 16)*256
        attr_list.insert(pango.AttrForeground(r, g, b, 0, 50))
        self.label.set_attributes(attr_list)

    def del_button(self):
        self.window_button.destroy()
        self.groupbutton.disconnect(self.sid1)
        self.groupbutton.disconnect(self.sid2)
        self.groupbutton.disconnect(self.sid4)
        self.groupbutton.dockbar.disconnect(self.sid3)
        del self.groupbutton.windows[self.window]
        self.window = None


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
        elif state_minimized & changed_mask:
            self.window_button_icon.set_from_pixbuf(self.icon)
            self.groupbutton.minimized_windows_count-=1
            if self.locked:
                self.locked = False
                self.groupbutton.locked_windows_count -= 1
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
        if pixbuf.get_height != lock.get_height or pixbuf.get_width != lock.get_width:
            lock = lock.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        self.icon_locked = self.icon_transp.copy()
        lock.composite(self.icon_locked, 0, 0, lock.get_width(), lock.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)

        if self.locked:
            self.window_button_icon.set_from_pixbuf(self.icon_locked)
        elif window.is_minimized():
            self.window_button_icon.set_from_pixbuf(self.icon_transp)
        else:
            self.window_button_icon.set_from_pixbuf(self.icon)

    def on_window_name_changed(self, window):
        name = u""+window.get_name()
        # TODO: fix a better way to shorten names.
        if len(name) > 40:
            name = name[0:37]+"..."
        self.name = name
        self.label.set_label(name)

    #### Grp signals
    def on_set_icongeo_win(self,arg=None):
        alloc = self.window_button.get_allocation()
        x,y = self.window_button.window.get_origin()
        x += alloc.x
        y += alloc.y
        self.window.set_icon_geometry(x,y,alloc.width,alloc.height)

    def on_set_icongeo_grp(self,arg=None):
        alloc = self.groupbutton.button.get_allocation()
        if self.groupbutton.button.window:
            x,y = self.groupbutton.button.window.get_origin()
            x += alloc.x
            y += alloc.y
            self.window.set_icon_geometry(x,y,alloc.width,alloc.height)

    def on_set_icongeo_delay(self,arg=None):
        # This one is used during popup delay to aviod
        # thumbnails on group buttons.
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
            self.window_button.drag_highlight()
            self.button_drag_entered = True
            self.dnd_select_window = \
                gobject.timeout_add(600,self.action_select_window)
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.button_drag_entered = False
        gobject.source_remove(self.dnd_select_window)
        self.window_button.drag_unhighlight()
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

    def __init__(self,dockbar,class_group=None, launcher=None, index=None, app=None):
        # Todo: replace class_group with res_class
        gobject.GObject.__init__(self)

        self.launcher = launcher
        self.class_group = class_group
        self.dockbar = dockbar
        self.app = app
        if class_group:
            self.res_class = class_group.get_res_class()
            if self.res_class == "":
                self.res_class = class_group.get_name()
        elif launcher:
            self.res_class = launcher.get_res_class()
            # launcher.get_res_class() returns None
            # if the resclass is still unknown
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
        # Compiz sends out false mouse enter messages after button is pressed.
        # This works around that bug.
        self.button_pressed = False

        self.screen = wnck.screen_get_default()
        self.root_xid = self.dockbar.root_xid


        #--- Button
        self.image = gtk.Image()
        self.icon_factory = IconFactory(self.dockbar, class_group, launcher, app)
        self.button = gtk.EventBox()
        self.button.set_visible_window(False)

        hbox = gtk.HBox()
        hbox.add(self.image)
        self.button.add(hbox)
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
        self.dockbar.container.show_all()
        self.dockbar.container.show()


        # Make sure that the first size-allocate call has
        # the right width or height, depending on applet orient.
        # (May not always work.)
        # TODO: should this be removed? Find out.
        gobject.idle_add(self.dockbar.container.resize_children)

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

        self.winlist = cairo_popup.vbox
        self.winlist.set_border_width(5)
        self.popup_label = gtk.Label()
        self.update_name()
        self.popup_label.set_use_markup(True)
        if self.res_class:
            # Todo: add tooltip when res_class is added.
            self.popup_label.set_tooltip_text("Resource class name: "+self.res_class)
        self.winlist.pack_start(self.popup_label,False)


        self.popup = cairo_popup.window
        self.popup_showing = False
        self.popup.connect("leave-notify-event",self.on_popup_mouse_leave)
        self.popup.add(self.winlist)


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

    def __del__(self):
        if self.button:
            self.button.destroy()
        self.button = None
        self.popup = None
        self.windows = None
        self.winlist = None
        self.dockbar = None
        self.drag_pixbuf = None

    def res_class_changed(self, res_class):
        self.res_class = res_class
        self.launcher.set_res_class(res_class)
        self.popup_label.set_tooltip_text("Resource class name: "+self.res_class)

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
        self.popup_label.set_label("<span foreground='"+settings['normal_text_color']+"'><big><b>"+self.name+"</b></big></span>")

    #### State
    def update_popup_label(self):
        self.popup_label.set_text("<span foreground='"+settings['normal_text_color']+"'><big><b>"+self.name+"</b></big></span>")
        self.popup_label.set_use_markup(True)

    def update_state(self):
        # Checks button state and set the icon accordingly.
        if self.has_active_window:
            icon_active = IconFactory.ACTIVE
        else:
            icon_active = 0

        if self.launcher and not self.windows:
            icon_mode = IconFactory.LAUNCHER
        elif len(self.windows) - self.minimized_windows_count == 0:
            icon_mode = IconFactory.ALL_MINIMIZED
        elif (self.minimized_windows_count - self.locked_windows_count) > 0:
            icon_mode = IconFactory.SOME_MINIMIZED
        else:
            icon_mode = 0

        if self.needs_attention:
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

        if self.dnd_highlight:
            dd_effect = IconFactory.DRAG_DROPP
        else:
            dd_effect = 0

        win_nr = min(len(self.windows), 15)
        self.state_type = icon_mode | icon_effect | icon_active | mouse_over| dd_effect | win_nr
        pixbuf = self.icon_factory.pixbuf_update(self.state_type)
        self.image.set_from_pixbuf(pixbuf)
        self.image.show()
        pixbuf = None
        return False

    def update_state_request(self):
        #Update state if the button is shown.
        a = self.button.get_allocation()
        if a.width>1 and a.height>1:
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
                    pixbuf = self.icon_factory.pixbuf_update(IconFactory.BLINK | self.state_type)
                    self.image.set_from_pixbuf(pixbuf)
                else:
                    self.needs_attention_anim_trigger = False
                    pixbuf = self.icon_factory.pixbuf_update(self.state_type)
                    self.image.set_from_pixbuf(pixbuf)
                pixbuf = None
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False

    #### Window handling
    def add_window(self,window):
        if window in self.windows:
            return
        self.windows[window] = WindowButton(window,self)
        if window.is_minimized():
            self.minimized_windows_count += 1
        if (self.launcher and len(self.windows)==1):
            self.class_group = window.get_class_group()
        # Update state unless the button hasn't been shown yet.
        self.update_state_request()

        #Update popup-list if it is being shown.
        if self.popup_showing:
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
        self.update_state_request()
        if self.needs_attention:
            self.needs_attention_changed()
        if not self.windows and not self.launcher:
            self.hide_list()
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            self.dockbar.groups.remove(self.res_class)
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
        self.winlist.show_all()
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
        self.popup.show_all()
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
        if self.res_class:
            name = self.res_class
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
        if self.res_class:
            name = self.res_class
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
            self.dnd_show_popup = gobject.timeout_add(settings['popup_delay'], self.show_list)
            for target in ('text/uri-list', 'text/groupbutton_name'):
                if target in drag_context.targets and \
                   not self.is_current_drag_source:
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
        gobject.source_remove(self.dnd_show_popup)
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
##        # Just as fail-safe
##        self.dnd_highlight = False
##        self.update_state()


    #### Events
    def on_sizealloc(self,applet,allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        if self.button_old_alloc != self.button.get_allocation():
            if self.dockbar.orient == "v":
                if allocation.width<=1:
                    return
                if not self.image.get_pixbuf() or self.image.get_pixbuf().get_width() != allocation.width:
                    self.icon_factory.set_size(self.button.get_allocation().width)
                    self.update_state()
            else:
                if allocation.height<=1:
                    return
                if not self.image.get_pixbuf() or self.image.get_pixbuf().get_height() != allocation.height:
                    self.icon_factory.set_size(self.button.get_allocation().height)
                    self.update_state()
            self.button_old_alloc = self.button.get_allocation()
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

        if len(self.windows)<=1 and settings['no_popup_for_one_window']:
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
        for window in self.windows:
            if window.is_minimized():
                window.unminimize(t)

    def change_res_class(self, widget=None, event=None):
        self.dockbar.change_res_class(self.launcher.get_path(), self.res_class)

    def add_launcher(self, widget=None, event=None):
        path = "gio:" + self.app.get_id()[:self.app.get_id().rfind('.')].lower()
        self.launcher = Launcher(self.res_class, path, self.dockbar)
        self.dockbar.groups.set_launcher_path(self.res_class, path)
        self.dockbar.update_launchers_list()

    #### Actions
    def action_select(self, widget, event):
        if (self.launcher and not self.windows):
            self.launcher.launch()
        # One window
        elif len(self.windows) == 1:
            if settings["select_one_window"] == "select window":
                self.windows.values()[0].action_select_window(widget, event)
            elif settings["select_one_window"] == "select or minimize window":
                self.windows.values()[0].action_select_or_minimize_window(widget, event)
        # Multiple windows
        elif len(self.windows) > 1:
            if settings["select_multiple_windows"] == "select all":
                self.action_select_or_minimize_group(widget, event, minimize=False)
            elif settings["select_multiple_windows"] == "select or minimize all":
                self.action_select_or_minimize_group(widget, event, minimize=True)
            elif settings["select_multiple_windows"] == "compiz scale":
                if len(self.windows) - self.minimized_windows_count == 1:
                    if settings["select_one_window"] == "select window":
                        self.windows.values()[0].action_select_window(widget, event)
                    elif settings["select_one_window"] == "select or minimize window":
                        self.windows.values()[0].action_select_or_minimize_window(widget, event)
                elif len(self.windows) - self.minimized_windows_count == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif settings["select_multiple_windows"] == "cycle through windows":
                self.action_select_next(widget, event)

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if (self.launcher and not self.windows):
            self.launcher.launch()
            return

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
                        if settings['workspace_behavior'] == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                        else: # settings['workspace_behavior'] == 'ignore' or 'switch'
                            ignored = True
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if settings['workspace_behavior'] == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                        else: # settings['workspace_behavior'] == 'ignore' or 'switch'
                            ignored = True
                    if not ignored:
                        win.unminimize(event.time)
                        unminimized = True
        if unminimized:
            return

        # Make a list of the windows in group with the bottom most
        # first and top most last.
        # If settings['workspace_behavior'] is other than move
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
                        if settings['workspace_behavior'] == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                            moved = True
                        else: # settings['workspace_behavior'] == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if settings['workspace_behavior'] == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                            moved = True
                        else: # settings['workspace_behavior'] == 'ignore' or 'switch'
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

        if not grp_win_stacked and settings['workspace_behavior'] == 'switch':
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
        win_nr = len(self.windows)
        if  win_nr > 1 and (win_nr - self.minimized_windows_count) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif win_nr > 1 and (win_nr - self.minimized_windows_count) == 1:
            for win in self.windows:
                if not win.is_minimized():
                    self.windows[win].action_select_window(widget, event)
                    break
        else:
            self.action_select_or_minimize_group(widget, event)

    def action_minimize_all_windows(self,widget=None, event=None):
        for window in self.windows:
            window.minimize()

    def action_maximize_all_windows(self,widget=None, event=None):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        maximized = False
        for window in self.windows:
            if not window.is_maximized() \
            and window.get_actions() & action_maximize:
                window.maximize()
                maximized = True
        if not maximized:
            for window in self.windows:
                window.unmaximize()

    def action_select_next(self, widget=None, event=None, previous=False):
        if not self.windows:
            return
        if self.nextlist_time == None or time() - self.nextlist_time > 2 \
        or self.nextlist == None:
            self.nextlist = []
            minimized_list = []
            screen = self.screen
            windows_stacked = screen.get_windows_stacked()
            for win in windows_stacked:
                    if win in self.windows:
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
        for window in self.windows:
            window.close(t)

    def action_launch_application(self, widget=None, event=None):
        if self.launcher:
            self.launcher.launch()
        elif self.app:
            self.app.launch(None, None)

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
            #Edit res_class item
            edit_res_class_item = gtk.MenuItem('Edit Resource Name')
            menu.append(edit_res_class_item)
            edit_res_class_item.connect("activate", self.change_res_class)
            edit_res_class_item.show()
        if (self.launcher or self.app) and self.windows:
            #Separator
            sep = gtk.SeparatorMenuItem()
            menu.append(sep)
            sep.show()
        #Close all windows item
        if self.windows:
            if len(self.windows) - self.minimized_windows_count == 0:
                # Unminimize all
                unminimize_all_windows_item = gtk.MenuItem('Un_minimize all windows')
                menu.append(unminimize_all_windows_item)
                unminimize_all_windows_item.connect("activate", self.unminimize_all_windows)
                unminimize_all_windows_item.show()
            else:
                # Minimize all
                minimize_all_windows_item = gtk.MenuItem('_Minimize all windows')
                menu.append(minimize_all_windows_item)
                minimize_all_windows_item.connect("activate", self.action_minimize_all_windows)
                minimize_all_windows_item.show()
            # (Un)Maximize all
            for window in self.windows:
                if not window.is_maximized() \
                and window.get_actions() & action_maximize:
                    maximize_all_windows_item = gtk.MenuItem('Ma_ximize all windows')
                    break
            else:
                maximize_all_windows_item = gtk.MenuItem('Unma_ximize all windows')
            menu.append(maximize_all_windows_item)
            maximize_all_windows_item.connect("activate", self.action_maximize_all_windows)
            maximize_all_windows_item.show()
            # Close all
            close_all_windows_item = gtk.MenuItem('_Close all windows')
            menu.append(close_all_windows_item)
            close_all_windows_item.connect("activate", self.action_close_all_windows)
            close_all_windows_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.dockbar.right_menu_showing = True

    def action_remove_launcher(self, widget=None, event = None):
        print 'Removing launcher ', self.res_class
        if self.res_class:
            name = self.res_class
        else:
            name = self.launcher.get_path()
        self.launcher = None
        if not self.windows:
            self.dockbar.groups.remove(name)
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
        else:
            self.dockbar.groups.remove_launcher(name)
            if self.app == None:
                # The launcher is not of gio-app type.
                # The group button will be reset with its
                # non-launcher name and icon.
                self.app = self.dockbar.find_gio_app(self.res_class)
                self.icon_factory.remove_launcher(class_group=self.class_group, app = self.app)
                self.update_name()
                self.update_state()
        self.dockbar.update_launchers_list()

    def action_minimize_all_other_groups(self, widget, event):
        self.hide_list()
        for gr in self.dockbar.groups.get_groups():
            if self != gr:
                for win in gr.windows:
                    gr.windows[win].window.minimize()

    def action_compiz_scale_windows(self, widget, event):
        if not self.res_class or \
           len(self.windows) - self.minimized_windows_count == 0:
            return
        if len(self.windows) - self.minimized_windows_count == 1:
            for win in self.windows:
                if not win.is_minimized():
                    self.windows[win].action_select_window(widget, event)
                    break
            return
        try:
            compiz_call('scale/allscreens/initiate_all_key','activate','root', self.root_xid,'match','iclass='+self.res_class)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay']+ 200, self.hide_list)

    def action_compiz_shift_windows(self, widget, event):
        if not self.res_class or \
           len(self.windows) - self.minimized_windows_count == 0:
            return
        if len(self.windows) - self.minimized_windows_count == 1:
            for win in self.windows:
                if not win.is_minimized():
                    self.windows[win].action_select_window(widget, event)
                    break
            return
        try:
            compiz_call('shift/allscreens/initiate_all_key','activate','root', self.root_xid,'match','iclass='+self.res_class)
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
        self.about.set_copyright("Copyright (c) 2008-2009 Aleksey Shaferov and Matias S\xc3\xa4rs)")
        self.about.connect("response",self.about_close)
        self.about.show()

    def about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None


class PrefDialog():
    __instance = None

    def __init__ (self, dockbar=None):
        global PREFDIALOG
        self.dockbar = dockbar
        if PrefDialog.__instance == None:
            PrefDialog.__instance = self
        else:
            PrefDialog.__instance.dialog.present()
            return

        PREFDIALOG = self
        self.dialog = gtk.Dialog("DockBarX preferences")
        self.dialog.connect("response",self.dialog_close)

        try:
            ca = self.dialog.get_content_area()
        except:
            ca = self.dialog.vbox
        notebook = gtk.Notebook()
        notebook.set_tab_pos(gtk.POS_TOP)
        appearance_box = gtk.VBox()
        windowbutton_box = gtk.VBox()
        groupbutton_box = gtk.VBox()

        #--- WindowButton page
        label = gtk.Label("<b>Windowbutton actions</b>")
        label.set_alignment(0,0.5)
        label.set_use_markup(True)
        table = gtk.Table(4,4)
        table.attach(label, 0, 4, 0, 1)

        # A directory of combobox names and the name of corresponding setting
        self.wb_labels_and_settings = ODict((
                    ('Left mouse button', "windowbutton_left_click_action"),
                    ('Shift + left mouse button', "windowbutton_shift_and_left_click_action"),
                    ('Middle mouse button', "windowbutton_middle_click_action"),
                    ('Shift + middle mouse button', "windowbutton_shift_and_middle_click_action"),
                    ('Right mouse button', "windowbutton_right_click_action"),
                    ('Shift + right mouse button', "windowbutton_shift_and_right_click_action"),
                    ('Scroll up', "windowbutton_scroll_up"),
                    ('Scroll down', "windowbutton_scroll_down")
                                           ))

        self.wb_combos = {}
        for text in self.wb_labels_and_settings:
            label = gtk.Label(text)
            label.set_alignment(1,0.5)
            self.wb_combos[text] = gtk.combo_box_new_text()
            for action in WindowButton.action_function_dict.keys():
                self.wb_combos[text].append_text(action)
            self.wb_combos[text].connect('changed', self.cb_changed)

            i = self.wb_labels_and_settings.get_index(text)
            # Every second label + combobox on a new row
            row = i // 2 + 1
            # Pack odd numbered comboboxes from 3rd column
            column = (i % 2) * 2
            table.attach(label, column, column + 1, row, row + 1 )
            table.attach(self.wb_combos[text], column + 1, column + 2, row, row + 1 )

        windowbutton_box.pack_start(table, False, padding=5)

        #--- Appearance page
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        label1 = gtk.Label("<b><big>Needs attention effect</big></b>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        self.rb1_1 = gtk.RadioButton(None, "Blinking")
        self.rb1_1.connect("toggled", self.rb_toggled, "rb1_blink")
        self.rb1_2 = gtk.RadioButton(self.rb1_1, "Compiz water")
        self.rb1_2.connect("toggled", self.rb_toggled, "rb1_compwater")
        self.rb1_3 = gtk.RadioButton(self.rb1_1, "Red background")
        self.rb1_3.connect("toggled", self.rb_toggled, "rb1_red")
        self.rb1_4 = gtk.RadioButton(self.rb1_1, "Nothing")
        self.rb1_4.connect("toggled", self.rb_toggled, "rb1_nothing")
        vbox.pack_start(self.rb1_1, False)
        vbox.pack_start(self.rb1_2, False)
        vbox.pack_start(self.rb1_3, False)
        vbox.pack_start(self.rb1_4, False)
        hbox.pack_start(vbox, True, padding=5)

        vbox = gtk.VBox()
        label1 = gtk.Label("<b><big>Popup Settings</big></b>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        self.rb3_1 = gtk.RadioButton(None, "Align left")
        self.rb3_1.connect("toggled", self.rb_toggled, "rb3_left")
        self.rb3_2 = gtk.RadioButton(self.rb3_1, "Align center")
        self.rb3_2.connect("toggled", self.rb_toggled, "rb3_center")
        self.rb3_3 = gtk.RadioButton(self.rb3_1, "Align right")
        self.rb3_3.connect("toggled", self.rb_toggled, "rb3_right")
        vbox.pack_start(self.rb3_1, False)
        vbox.pack_start(self.rb3_2, False)
        vbox.pack_start(self.rb3_3, False)
        hbox.pack_start(vbox, True, padding=5)

        vbox = gtk.VBox()
        label1 = gtk.Label("<b><big>Opacify</big></b>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        self.opacify_cb = gtk.CheckButton('Opacify')
        self.opacify_cb.connect('toggled', self.checkbutton_toggled, 'opacify')
        vbox.pack_start(self.opacify_cb, False)
        self.opacify_group_cb = gtk.CheckButton('Opacify group')
        self.opacify_group_cb.connect('toggled', self.checkbutton_toggled, 'opacify_group')
        vbox.pack_start(self.opacify_group_cb, False)
        scalebox = gtk.HBox()
        scalelabel = gtk.Label("Opacity:")
        scalelabel.set_alignment(0,0.5)
        adj = gtk.Adjustment(0, 0, 100, 1, 10, 0)
        self.opacify_scale = gtk.HScale(adj)
        self.opacify_scale.set_digits(0)
        self.opacify_scale.set_value_pos(gtk.POS_RIGHT)
        adj.connect("value_changed", self.adjustment_changed, 'opacify_alpha')
        scalebox.pack_start(scalelabel, False)
        scalebox.pack_start(self.opacify_scale, True)
        vbox.pack_start(scalebox, False)
        hbox.pack_start(vbox, True, padding=5)

        appearance_box.pack_start(hbox, False, padding=5)

        hbox = gtk.HBox()
        label = gtk.Label('Theme:')
        label.set_alignment(1,0.5)
        themes = self.find_themes()
        self.theme_combo = gtk.combo_box_new_text()
        for theme in themes.keys():
                self.theme_combo.append_text(theme)
        self.theme_combo.connect('changed', self.cb_changed)
        button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_REFRESH,gtk.ICON_SIZE_SMALL_TOOLBAR)
        button.add(image)
        button.connect("clicked", self.reload_dockbar)
        hbox.pack_start(label, False)
        hbox.pack_start(self.theme_combo, False)
        hbox.pack_start(button, False)

        appearance_box.pack_start(hbox, False, padding=5)

        frame = gtk.Frame('Colors')
        frame.set_border_width(5)
        table = gtk.Table(True)
        # A directory of combobox names and the name of corresponding setting
        self.color_labels_and_settings = {'Active glow': "active_glow",
                                          'Popup background': "popup",
                                          'Active window text': "active_text",
                                          'Minimized window text': "minimized_text",
                                          'Normal text': "normal_text"}
        # A list to ensure that the order is kept correct
        color_labels = ['Active glow',
                        'Popup background',
                        'Active window text',
                        'Minimized window text',
                        'Normal text']
        self.color_buttons = {}
        self.clear_buttons = {}
        for i in range(len(color_labels)):
            text = color_labels[i]
            label = gtk.Label(text)
            label.set_alignment(1,0.5)
            self.color_buttons[text] = gtk.ColorButton()
            self.color_buttons[text].set_title(text)
            self.color_buttons[text].connect("color-set",  self.color_set, text)
            self.clear_buttons[text] = gtk.Button()
            image = gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_SMALL_TOOLBAR)
            self.clear_buttons[text].add(image)
            self.clear_buttons[text].connect("clicked", self.color_reset, text)
            # Every second label + combobox on a new row
            row = i // 2
            # Pack odd numbered comboboxes from 3rd column
            column = (i % 2)*3
            table.attach(label, column, column + 1, row, row + 1, xoptions = gtk.FILL, xpadding = 5)
            table.attach(self.color_buttons[text], column+1, column+2, row, row + 1)
            table.attach(self.clear_buttons[text], column+2, column+3, row, row + 1, xoptions = gtk.FILL)

        table.set_border_width(5)
        frame.add(table)
        appearance_box.pack_start(frame, False, padding=5)

        #--- Groupbutton page
        table = gtk.Table(6,4)
        label = gtk.Label("<b>Groupbutton actions</b>")
        label.set_alignment(0,0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 6, 0, 1)

        # A directory of combobox names and the name of corresponding setting
        self.gb_labels_and_settings = ODict((
                                             ('Left mouse button', "groupbutton_left_click_action"),
                                             ('Shift + left mouse button', "groupbutton_shift_and_left_click_action"),
                                             ('Middle mouse button', "groupbutton_middle_click_action"),
                                             ('Shift + middle mouse button', "groupbutton_shift_and_middle_click_action"),
                                             ( 'Right mouse button', "groupbutton_right_click_action"),
                                             ('Shift + right mouse button', "groupbutton_shift_and_right_click_action"),
                                             ('Scroll up', "groupbutton_scroll_up"),
                                             ('Scroll down', "groupbutton_scroll_down")
                                           ))

        self.gb_combos = {}
        for text in self.gb_labels_and_settings:
            label = gtk.Label(text)
            label.set_alignment(1,0.5)
            self.gb_combos[text] = gtk.combo_box_new_text()
            for action in GroupButton.action_function_dict.keys():
                self.gb_combos[text].append_text(action)
            self.gb_combos[text].connect('changed', self.cb_changed)

            i = self.gb_labels_and_settings.get_index(text)
            # Every second label + combobox on a new row
            row = i // 2 + 1
            # Pack odd numbered comboboxes from 3rd column
            column = (i % 2) * 3
            table.attach(label, column, column + 1, row, row + 1, xpadding = 5 )
            table.attach(self.gb_combos[text],column + 1, column + 2, row, row + 1 )

        self.gb_doubleclick_checkbutton_names = ['groupbutton_left_click_double',
                            'groupbutton_shift_and_left_click_double',
                            'groupbutton_middle_click_double',
                            'groupbutton_shift_and_middle_click_double',
                            'groupbutton_right_click_double',
                            'groupbutton_shift_and_right_click_double']
        self.gb_doubleclick_checkbutton = {}
        for i in range(len(self.gb_doubleclick_checkbutton_names)):
            name = self.gb_doubleclick_checkbutton_names[i]
            self.gb_doubleclick_checkbutton[name] = gtk.CheckButton('Double click')

            self.gb_doubleclick_checkbutton[name].connect('toggled', self.checkbutton_toggled, name)
            # Every second label + combobox on a new row
            row = i // 2 + 1
            # Pack odd numbered comboboxes from 3rd column
            column = (i % 2) * 3
            table.attach(self.gb_doubleclick_checkbutton[name], column + 2, column + 3, row, row + 1, xpadding = 5 )

        groupbutton_box.pack_start(table, False, padding=5)

        hbox = gtk.HBox()
        table = gtk.Table(2,4)
        label = gtk.Label("<b>\"Select\" action options</b>")
        label.set_alignment(0,0.5)
        label.set_use_markup(True)
        table.attach(label,0,2,0,1)

        label = gtk.Label("One window open:")
        label.set_alignment(1,0.5)
        self.select_one_cg = gtk.combo_box_new_text()
        self.select_one_cg.append_text("select window")
        self.select_one_cg.append_text("select or minimize window")
        self.select_one_cg.connect('changed', self.cb_changed)
        table.attach(label,0,1,1,2)
        table.attach(self.select_one_cg,1,2,1,2)

        label = gtk.Label("Multiple windows open:")
        label.set_alignment(1,0.5)
        self.select_multiple_cg = gtk.combo_box_new_text()
        self.select_multiple_cg.append_text("select all")
        self.select_multiple_cg.append_text("select or minimize all")
        self.select_multiple_cg.append_text("compiz scale")
        self.select_multiple_cg.append_text("cycle through windows")
        self.select_multiple_cg.connect('changed', self.cb_changed)
        table.attach(label,0,1,2,3)
        table.attach(self.select_multiple_cg,1,2,2,3)

        label = gtk.Label("Workspace behavior:")
        label.set_alignment(1,0.5)
        self.select_workspace_cg = gtk.combo_box_new_text()
        self.select_workspace_cg.append_text("Ignore windows on other workspaces")
        self.select_workspace_cg.append_text("Switch workspace when needed")
        self.select_workspace_cg.append_text("Move windows from other workspaces")
        self.select_workspace_cg.connect('changed', self.cb_changed)
        table.attach(label,0,1,3,4)
        table.attach(self.select_workspace_cg,1,2,3,4)

        hbox.pack_start(table, False, padding=5)


        vbox = gtk.VBox()
        label1 = gtk.Label("<b>Popup</b>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        spinbox = gtk.HBox()
        spinlabel = gtk.Label("Delay:")
        spinlabel.set_alignment(0,0.5)
        adj = gtk.Adjustment(0, 0, 2000, 1, 50)
        self.delay_spin = gtk.SpinButton(adj, 0.5, 0)
        adj.connect("value_changed", self.adjustment_changed, 'popup_delay')
        spinbox.pack_start(spinlabel, False)
        spinbox.pack_start(self.delay_spin, False)
        vbox.pack_start(spinbox, False)

        self.no_popup_cb = gtk.CheckButton('Show popup only if more than one window is open')
        self.no_popup_cb.connect('toggled', self.checkbutton_toggled, 'no_popup_for_one_window')
        vbox.pack_start(self.no_popup_cb, False)
        hbox.pack_start(vbox, False, padding=20)
        groupbutton_box.pack_start(hbox, False, padding=10)

        label = gtk.Label("Appearance")
        notebook.append_page(appearance_box, label)
        ca.pack_start(notebook)
        label = gtk.Label("Group Button")
        notebook.append_page(groupbutton_box, label)
        label = gtk.Label("Window Button")
        notebook.append_page(windowbutton_box, label)

        self.update()

        self.dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.dialog.show_all()


    def update(self):
        """Set widgets according to settings."""

        # Attention notification
        settings_attention = settings["groupbutton_attention_notification_type"]
        if settings_attention == 'blink':
            self.rb1_1.set_active(True)
        elif settings_attention == 'compwater':
            self.rb1_2.set_active(True)
        elif settings_attention == 'red':
            self.rb1_3.set_active(True)
        elif settings_attention == 'nothing':
            self.rb1_4.set_active(True)

        # Popup alignment
        settings_align = settings["popup_align"]
        if settings_align == 'left':
            self.rb3_1.set_active(True)
        elif settings_align == 'center':
            self.rb3_2.set_active(True)
        elif settings_align == 'right':
            self.rb3_3.set_active(True)

        # Popup
        self.delay_spin.set_value(settings['popup_delay'])
        self.no_popup_cb.set_active(settings['no_popup_for_one_window'])

        # Group button keys
        for cb_name, setting_name in self.gb_labels_and_settings.items():
            value = settings[setting_name]
            combobox = self.gb_combos[cb_name]
            model = combobox.get_model()
            for i in range(len(combobox.get_model())):
                if model[i][0] == value:
                    combobox.set_active(i)
                    break

        # Window button keys
        for cb_name, setting_name in self.wb_labels_and_settings.items():
            value = settings[setting_name]
            combobox = self.wb_combos[cb_name]
            model = combobox.get_model()
            for i in range(len(combobox.get_model())):
                if model[i][0] == value:
                    combobox.set_active(i)
                    break

        for name in self.gb_doubleclick_checkbutton_names:
            self.gb_doubleclick_checkbutton[name].set_active(settings[name])

        # Opacify
        self.opacify_cb.set_active(settings['opacify'])
        self.opacify_group_cb.set_active(settings['opacify_group'])
        self.opacify_scale.set_value(settings['opacify_alpha'])

        self.opacify_group_cb.set_sensitive(settings['opacify'])
        self.opacify_scale.set_sensitive(settings['opacify'])

        # Colors
        for name, setting_base in self.color_labels_and_settings.items():
            color = gtk.gdk.color_parse(settings[setting_base+'_color'])
            self.color_buttons[name].set_color(color)
            if settings.has_key(setting_base+"_alpha"):
                alpha = settings[setting_base+"_alpha"] * 256
                self.color_buttons[name].set_use_alpha(True)
                self.color_buttons[name].set_alpha(alpha)

        #Select action
        model = self.select_one_cg.get_model()
        for i in range(len(self.select_one_cg.get_model())):
                if model[i][0] == settings['select_one_window'].lower():
                    self.select_one_cg.set_active(i)
                    break

        model = self.select_multiple_cg.get_model()
        for i in range(len(self.select_multiple_cg.get_model())):
                if model[i][0] == settings['select_multiple_windows'].lower():
                    self.select_multiple_cg.set_active(i)
                    break

        model = self.select_workspace_cg.get_model()
        wso={
             "ignore":"Ignore windows on other workspaces",
             "switch":"Switch workspace when needed",
             "move":"Move windows from other workspaces"
            }
        for i in range(len(self.select_workspace_cg.get_model())):
                if model[i][0] == wso[settings['workspace_behavior'].lower()]:
                    self.select_workspace_cg.set_active(i)
                    break

        # Themes
        model = self.theme_combo.get_model()
        for i in range(len(self.theme_combo.get_model())):
            if model[i][0].lower() == settings['theme'].lower():
                self.theme_combo.set_active(i)
                break



    def dialog_close (self,par1,par2):
        global PREFDIALOG
        PREFDIALOG = None
        self.dialog.destroy()
        PrefDialog.__instance = None

    def rb_toggled (self,button,par1):
        # Read the value of the toggled radio button and write to gconf
        rb1_toggled = False
        rb2_toggled = False
        rb3_toggled = False

        if par1 == 'rb1_blink' and button.get_active():
            value = 'blink'
            rb1_toggled = True
        if par1 == 'rb1_compwater' and button.get_active():
            value = 'compwater'
            rb1_toggled = True
        if par1 == 'rb1_red' and button.get_active():
            value = 'red'
            rb1_toggled = True
        if par1 == 'rb1_nothing' and button.get_active():
            value = 'nothing'
            rb1_toggled = True

        if rb1_toggled and value != settings["groupbutton_attention_notification_type"]:
            GCONF_CLIENT.set_string(GCONF_DIR+'/groupbutton_attention_notification_type', value)

        if par1 == 'rb3_left' and button.get_active():
            value = 'left'
            rb3_toggled = True
        if par1 == 'rb3_center' and button.get_active():
            value = 'center'
            rb3_toggled = True
        if par1 == 'rb3_right' and button.get_active():
            value = 'right'
            rb3_toggled = True

        if rb3_toggled and value != settings["popup_align"]:
            GCONF_CLIENT.set_string(GCONF_DIR+'/popup_align', value)

    def checkbutton_toggled (self,button,name):
        # Read the value of the toggled check button/box and write to gconf
        if button.get_active() != settings[name]:
            GCONF_CLIENT.set_bool(GCONF_DIR+'/'+name, button.get_active())


    def cb_changed(self, combobox):
        # Read the value of the combo box and write to gconf
        # Groupbutton settings
        for name, cb in self.gb_combos.items():
            if cb == combobox:
                setting_name = self.gb_labels_and_settings[name]
                value = combobox.get_active_text()
                if value == None:
                    return
                if value != settings[setting_name]:
                    GCONF_CLIENT.set_string(GCONF_DIR+'/'+setting_name, value)

        # Windowbutton settings
        for name, cb in self.wb_combos.items():
            if cb == combobox:
                setting_name = self.wb_labels_and_settings[name]
                value = combobox.get_active_text()
                if value == None:
                    return
                if value != settings[setting_name]:
                    GCONF_CLIENT.set_string(GCONF_DIR+'/'+setting_name, value)

        if combobox == self.theme_combo:
            value = combobox.get_active_text()
            if value == None:
                return
            if value != settings['theme']:
                GCONF_CLIENT.set_string(GCONF_DIR+'/theme', value)

        if combobox == self.select_one_cg:
            value = combobox.get_active_text()
            if value == None:
                return
            if value != settings['select_one_window']:
                GCONF_CLIENT.set_string(GCONF_DIR+'/select_one_window', value)

        if combobox == self.select_multiple_cg:
            value = combobox.get_active_text()
            if value == None:
                return
            if value != settings['select_multiple_windows']:
                GCONF_CLIENT.set_string(GCONF_DIR+'/select_multiple_windows', value)

        if combobox == self.select_workspace_cg:
            value = combobox.get_active_text()
            wso={
                 "Ignore windows on other workspaces":"ignore",
                 "Switch workspace when needed":"switch",
                 "Move windows from other workspaces":"move"
                }
            if value == None:
                return
            if value != settings['workspace_behavior']:
                GCONF_CLIENT.set_string(GCONF_DIR+'/workspace_behavior', wso[value])

    def adjustment_changed(self, widget, setting):
        # Read the value of the adjustment and write to gconf
        value = int(widget.get_value())
        if value != settings[setting]:
            GCONF_CLIENT.set_int(GCONF_DIR+'/'+setting, value)

    def color_set(self, button, text):
        # Read the value from color (and aplha) and write
        # it as 8-bit/channel hex string for gconf.
        # (Alpha is written like int (0-255).)
        setting_base = self.color_labels_and_settings[text]
        color_string = settings[setting_base+"_color"]
        color = button.get_color()
        cs = color.to_string()
        # cs has 16-bit per color, we want 8.
        new_color = cs[0:3] + cs[5:7] + cs[9:11]
        if new_color != color_string:
            GCONF_CLIENT.set_string(GCONF_DIR+'/'+setting_base+"_color", new_color)
        if settings.has_key(setting_base+"_alpha"):
            alpha = settings[setting_base+"_alpha"]
            new_alpha = min(int(float(button.get_alpha()) / 256 + 0.5), 255)
            if new_alpha != alpha:
                GCONF_CLIENT.set_int(GCONF_DIR+'/'+setting_base+"_alpha", new_alpha)

    def color_reset(self, button, text):
        # Reset gconf color setting to default.
        setting_base = self.color_labels_and_settings[text]
        color_string = DEFAULT_SETTINGS[setting_base+"_color"]
        GCONF_CLIENT.set_string(GCONF_DIR+'/'+setting_base+"_color", color_string)
        if DEFAULT_SETTINGS.has_key(setting_base+"_alpha"):
            alpha = DEFAULT_SETTINGS[setting_base+"_alpha"]
            GCONF_CLIENT.set_int(GCONF_DIR+'/'+setting_base+"_alpha", alpha)

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
            if os.path.exists(dir):
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
        return themes

    def reload_dockbar(self, button=None):
        if self.dockbar:
            self.dockbar.reload()


class DockBar(gobject.GObject):
    __gsignals__ = {
        "db-move": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
    }
    def __init__(self,applet):
        gobject.GObject.__init__(self)
        global settings
        print "dockbar init"
        self.applet = applet
        self.dockbar_folder = self.ensure_dockbar_folder()
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

        wnck.set_client_type(wnck.CLIENT_TYPE_PAGER)
        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.screen.force_update()
        self.screen.connect("window-opened",self.on_window_opened)
        self.screen.connect("window-closed",self.on_window_closed)
        self.screen.connect("active-window-changed", self.on_active_window_changed)

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
            self.applet.show_all()
            self.applet_origin_x = -1000 # off screen. there is no 'window' prop
            self.applet_origin_y = -1000 # at this step
        else:
            self.container = gtk.HBox()
            self.orient = "h"

        self.reload()


    def reload(self, event=None, data=None):
        if self.groups != None:
            for group in self.groups.get_groups():
                group.hide_list()
        del self.groups
        del self.windows
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

        #--- Load theme
        self.themes = self.find_themes()
        default_theme_path = None
        for theme, path in self.themes.items():
            if theme.lower() == settings['theme'].lower():
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

        # Remove all old groupbuttons.
        for child in self.container.get_children():
            self.container.remove(child)

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
        # Initiate launcher group buttons
        for launcher in gconf_launchers:
            res_class, path = launcher.split(';')
            if res_class == '':
                res_class = None
            self.add_launcher(res_class, path)

        #--- Initiate windows
        # Initiate group buttons with windows
        for window in self.screen.get_windows():
            self.on_window_opened(self.screen, window)

        self.on_active_window_changed(self.screen, None)

    def ensure_dockbar_folder(self):
        # Check if ~/.dockbarx exist and make it if not.
        homeFolder = os.path.expanduser("~")
        dockbar_folder = homeFolder + "/.dockbarx"
        if not os.path.exists(dockbar_folder):
            os.mkdir(dockbar_folder)
        if not os.path.isdir(dockbar_folder):
            raise Exception(dockbar_folder + "is not a directory!")
        return dockbar_folder

    def find_themes(self):
        # Reads the themes from /usr/share/dockbarx/themes and ~/.dockbarx/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        dirs = ["/usr/share/dockbarx/themes", self.dockbar_folder+"/themes"]
        for dir in dirs:
            if os.path.exists(dir):
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
##            raise Exception('No working themes found in "/usr/share/dockbarx/themes" or "~/.dockbarx/themes"')
            sys.exit(1)
        return themes

    #### GConf
    def on_gconf_changed(self, client, par2, entry, par4):
        global settings
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
                pref_update = True
        if pref_update and PREFDIALOG:
            PREFDIALOG.update()

        #TODO: Add check for sane values for critical settings.

        if 'active_glow_color' in changed_settings \
           or 'active_glow_alpha'  in changed_settings:
            self.reset_all_active_pixbufs()

        if 'normal_text_color' in changed_settings:
            self.update_all_popup_labels()

        for key in changed_settings:
            if 'text_color' in key:
                self.all_windowbuttons_update_state()
                break

    def reset_all_active_pixbufs(self):
        # Removes all saved pixbufs with active glow in groupbuttons iconfactories.
        # Use this def when the looks of active glow has been changed.
        for group in self.groups.get_groups():
            group.icon_factory.reset_active_pixbufs()

        active_window = self.screen.get_active_window()
        if active_window in self.windows:
            active_group_name = self.windows[active_window]
            active_group = self.groups.get_group(active_group_name)
            if active_group:
                active_group.update_state_request()

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
        PrefDialog(self)

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
        if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN or self.applet.get_orient() == gnomeapplet.ORIENT_UP:
            self.container = gtk.HBox()
            self.orient = "h"
        else:
            self.container = gtk.VBox()
            self.orient = "v"
        self.applet.add(self.container)
        for group in self.groups.get_groups():
            self.container.pack_start(group.button,False)
        self.container.set_spacing(self.theme.get_gap())
        self.container.show_all()


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

    def on_window_opened(self,screen,window):
        if window.is_skip_tasklist() \
        or not (window.get_window_type() in [wnck.WINDOW_NORMAL, wnck.WINDOW_DIALOG]):
            return

        class_group = window.get_class_group()
        class_group_name = class_group.get_res_class()
        if class_group_name == "":
            class_group_name = class_group.get_name()
        self.windows[window]=class_group_name
        if class_group_name in self.groups.get_res_classes():
            self.groups[class_group_name].add_window(window)
            return
        id = None
        rc = u""+class_group_name.lower()
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
                    # with res_class like this 'App 1.2.3' (name with ver)
                    if rc in self.launchers_by_id:
                        id = rc
                        print "Partial name for open window matched with id:", rc
                    elif rc in self.launchers_by_name:
                        id = self.launchers_by_name[rc]
                        print "Partial name for open window matched with name:", rc
                    elif rc in self.launchers_by_exec:
                        id = self.launchers_by_exec[rc]
                        print "Partial name for open window matched with executable:", rc
        if id:
            # The window is matching a launcher!
            path = self.launchers_by_id[id].get_path()
            self.groups.set_res_class(path, class_group_name)
            self.groups[class_group_name].add_window(window)
            self.update_launchers_list()
            self.remove_launcher_id_from_undefined_list(id)
        else:
            # First window of a new group.
            app = self.find_gio_app(class_group_name)
            self.groups[class_group_name] = GroupButton(self,class_group, app=app)
            self.groups[class_group_name].add_window(window)


    def on_window_closed(self,screen,window):
        if window in self.windows:
            class_group_name = self.windows[window]
            if self.groups.get_group(class_group_name):
                self.groups.get_group(class_group_name).del_window(window)
            del self.windows[window]

    def find_gio_app(self, res_class):
        app = None
        app_id = None
        rc = u""+res_class.lower()
        if rc != "":
            # WM_CLASS res_class exists.
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
                    # with res_class like this 'App 1.2.3' (name with ver)
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

    #### Launchers
    def add_launcher(self, res_class, path):
        """Adds a new launcher from a desktop file located at path and from the name"""
        try:
            launcher = Launcher(res_class, path, dockbar=self)
        except:
            print "ERROR: Couldn't read desktop entry for " + name
            print "path: "+ path
            return

        self.groups.add_group(res_class, GroupButton(self, launcher=launcher), path)
        if res_class == None:
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
        for res_class in self.groups.get_non_launcher_names():
            rc = u""+res_class.lower()
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
                    # with res_class like this 'App 1.2.3' (name with ver)
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
            res_class = None
            self.launchers_by_id[id] = launcher
            if lname:
                self.launchers_by_longname[name] = id
            else:
                self.launchers_by_name[name] = id
            self.launchers_by_exec[exe] = id

        class_group = None
        if res_class:
            launcher.set_res_class(res_class)
        # Remove existing groupbutton for the same program
        winlist = []
        if calling_button in (res_class, path):
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
            if res_class in self.groups.get_res_classes():
                group = self.groups[res_class]
                class_group = group.get_class_group()
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(res_class)
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
        button = GroupButton(self, class_group=class_group, launcher=launcher, index=index)
        self.groups.add_group(res_class, button, path, index)
        self.update_launchers_list()
        for window in winlist:
            self.on_window_opened(self.screen, window)
        return True

    def class_name_dialog(self, res_class=None):
        # Input dialog for inputting the res_class_name.
        dialog = gtk.MessageDialog(
            None,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL,
            None)
        dialog.set_title('Resource Class')
        dialog.set_markup('<b>Enter the resource class name here</b>')
        dialog.format_secondary_markup(
            'You should have to do this only if the program fails to recognice its windows. '+ \
            'If the program is already running you should be able to find the resource class name of the program from the dropdown list.')
        #create the text input field
        #entry = gtk.Entry()
        combobox = gtk.combo_box_entry_new_text()
        entry = combobox.get_child()
        if res_class:
            entry.set_text(res_class)
        # Fill the popdown list with the names of all class names of buttons that hasn't got a launcher already
        for name in self.groups.get_non_launcher_names():
            combobox.append_text(name)
        entry = combobox.get_child()
        #entry.set_text('')
        #allow the user to press enter to do ok
        entry.connect("activate", lambda widget: dialog.response(gtk.RESPONSE_OK))
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label('Class Name:'), False, 5, 5)
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

    def change_res_class(self, path, res_class=None):
        res_class = self.class_name_dialog(res_class)
        if not res_class:
            return False
        winlist = []
        if res_class in self.groups.get_res_classes():
                group = self.groups[res_class]
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(res_class)
        self.groups.set_res_class(path, res_class)
        for window in winlist:
            self.on_window_opened(self.screen, window)
        self.update_launchers_list()

    def update_launchers_list(self):
        # Saves launchers_list to gconf.
        launchers_list = self.groups.get_launchers_list()
        gconf_launchers = []
        for res_class, path in launchers_list:
            if res_class == None:
                res_class = ''
            gconf_launchers.append(res_class + ';' + path)
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
