#!/usr/bin/python

#   iconfactory.py
#
#	Copyright 2009, 2010 Matias Sars
#
#	DockbarX is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	DockbarX is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

import pygtk
pygtk.require('2.0')
import gtk
import gc
gc.enable()
import Image
import array
import cairo
import gio
import os
from cStringIO import StringIO

from theme import Theme
from common import Globals

import i18n
_ = i18n.language.gettext

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

    def __init__(self, class_group=None, launcher=None, app=None, identifier=None):
        self.theme = Theme()
        self.globals = Globals()
        self.globals.connect('color-changed', self.reset_surfaces)
        self.app = app
        self.launcher = launcher
        self.identifier = identifier
        if self.launcher and self.launcher.app:
            self.app = self.launcher.app
            self.launcher = None
        self.class_group = class_group

        # Setting size to something other than zero to
        # avoid crashes if surface_update() is runned
        # before the size is set.
        self.size = 15

        self.icon = None
        self.surfaces = {}

        self.average_color = None

        self.max_win_nr = self.theme.get_windows_cnt()

    def remove(self):
        del self.app
        del self.launcher
        del self.class_group
        del self.icon
        del self.surfaces
        del self.theme

    def remove_launcher(self, class_group = None, app = None):
        self.launcher = None
        self.class_group = class_group
        self.app = app
        self.surfaces = {}
        del self.icon
        self.icon = None


    def set_size(self, size):
        if size <= 0:
            # To avoid chrashes.
            size = 15
        self.size = size
        self.surfaces = {}
        self.average_color = None

    def get_size(self):
        return self.size

    def reset_surfaces(self, arg=None):
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
        commands = self.theme.get_icon_dict()
        self.ar = self.theme.get_aspect_ratio()
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
            surface = self.dd_highlight(surface, self.globals.orient)
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
            color = self.globals.colors[color]
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
                if self.globals.colors.has_key('color%s_alpha'%i):
                    a = float(self.globals.colors['color%s_alpha'%i])/255
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
        if size <= 0:
            # To avoid chrashes.
            size = 15
        if self.icon \
        and self.icon.get_width() == size \
        and self.icon.get_height() == size:
            return self.icon
        del self.icon
        self.icon = None
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
        dialog = gtk.MessageDialog(
                    parent=None,
                    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    type=gtk.MESSAGE_WARNING,
                    buttons=gtk.BUTTONS_OK,
                    message_format='%s %s.'%(_("Cannot load icon for launcher"), self.launcher.get_identifier())
                                  )
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
            if self.globals.orient == 'h':
                width = int(self.size * ar)
                height = self.size
            else:
                width = self.size
                height = int(self.size * ar)
        else:
            width = surface.get_width()
            height = surface.get_height()
        if self.theme.has_surface(name):
            surface = self.resize_surface(self.theme.get_surface(name), width, height)
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
        elif self.theme.has_surface(pix1):
            w = surface.get_width()
            h = surface.get_height()
            p1 = self.resize_surface(self.theme.get_surface(bg), w, h)
        else:
            print "theme error: pixmap %s not found"%pix1
        if pix2=="self":
            p2 = surface
        elif pix2 in self.temp:
            p2 = self.temp[pix2]
        elif self.theme.has_surface(pix2):
            w = surface.get_width()
            h = surface.get_height()
            p2 = self.resize_surface(self.theme.get_surface(bg), w, h)
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
        return new

    def command_composite(self, surface, bg, fg, opacity=100, xoffset=0, yoffset=0):
        if fg=="self":
            foreground = surface
        elif fg in self.temp:
            foreground = self.temp[fg]
        elif self.theme.has_surface(fg):
            w = surface.get_width()
            h = surface.get_height()
            foreground = self.resize_surface(self.theme.get_surface(fg), w, h)
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
        elif self.theme.has_surface(bg):
            w = surface.get_width()
            h = surface.get_height()
            background = self.resize_surface(self.theme.get_surface(bg), w, h)
        else:
            print "theme error: pixmap %s not found"%bg
            return surface

        opacity = self.get_alpha(opacity)
        xoffset = float(xoffset)
        yoffset = float(yoffset)
        ctx = cairo.Context(background)
        ctx.set_source_surface(foreground, xoffset, yoffset)
        ctx.paint_with_alpha(opacity)
        return background

    def command_shrink(self, surface, percent=0, pixels=0):
        w0 = surface.get_width()
        h0 = surface.get_height()
        new = cairo.ImageSurface(cairo.FORMAT_ARGB32, w0, h0)
        ctx = cairo.Context(new)

        w = int(((100-int(percent)) * w0)/100)-int(pixels)
        h = int(((100-int(percent)) * h0)/100)-int(pixels)
        shrinked = self.resize_surface(surface, w, h)
        x = int(float(w0 - w) / 2 + 0.5)
        y = int(float(h0 - h) / 2 + 0.5)
        ctx.set_source_surface(shrinked, x, y)
        ctx.paint()
        del shrinked
        return new

    def command_correct_size(self, surface):
        if surface == None:
            return
        if self.globals.orient == 'v':
            width = self.size
            height = int(self.size * self.ar)
        else:
            width = int(self.size * self.ar)
            height = self.size
        if surface.get_width() == width and surface.get_height() == height:
            return surface
        woffset = int(float(width - surface.get_width()) / 2 + 0.5)
        hoffset = int(float(height - surface.get_height()) / 2 + 0.5)
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
        if strength == None and strenght != None:
            # For compability with older themes.
            strength = strenght
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
        elif self.theme.has_surface(mask):
            m = self.surface2pixbuf(self.theme.get_surface(mask))
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
        return self.pil2surface(im)



