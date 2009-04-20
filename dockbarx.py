#!/usr/bin/python

#	Copyright 2008, Aleksey Shaferov 
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
#	along with media-applet.  If not, see <http://www.gnu.org/licenses/>.

# Exmperimental features by Matias Sars

# Some code is borrowed from Ubuntu system panel (c) 2007 S. Chanderbally
# (http://code.google.com/p/ubuntu-system-panel/)

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import sys
import wnck
import gnomeapplet
import gnome
import gconf
import os
import pickle
from xdg.DesktopEntry import DesktopEntry
import gnome.ui
import gnomevfs
import dbus
import pango
from cStringIO import StringIO

from math import pi
import cairo

try:
    import gio
except:
    pass


##import pdb

VERSION = 'Experimental 0.21.3'

TARGET_TYPE_GROUPBUTTON = 134 # Randomly chosen number

GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = '/apps/dockbarx'

BUS = dbus.SessionBus()

PREFDIALOG = None # Non-constant! Remove or rename!?

DEFAULT_SETTINGS = { "groupbutton_attention_notification_type": "red",
                      "workspace_behavior": "switch",
                      "popup_delay": 250,
                      "popup_align": "center",
                    
                      "active_glow_color": "#FFFF75",
                      "active_glow_alpha": 160,
                      "popup_color": "#333333",
                      "popup_alpha": 205,
                    
                      "active_text_color": "#FFFF75",
                      "minimized_text_color": "#9C9C9C",
                      "normal_text_color": "#FFFFFF",
                    
                      "groupbutton_left_click_action":"select or minimize group",
                      "groupbutton_shift_and_left_click_action":"launch application",
                      "groupbutton_middle_click_action":"close all windows",
                      "groupbutton_shift_and_middle_click_action": "no action",
                      "groupbutton_right_click_action": "show menu",
                      "groupbutton_shift_and_right_click_action": "no action",
                      "groupbutton_scroll_up": "no action",
                      "groupbutton_scroll_down": "no action",
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
                      "windowbutton_right_click_action": "lock or unlock window",
                      "windowbutton_shift_and_right_click_action": "no action",
                      "windowbutton_scroll_up": "shade window",
                      "windowbutton_scroll_down": "unshade window" }
settings = DEFAULT_SETTINGS.copy()

def compiz_call(obj_path, func_name, *args):
	path = '/org/freedesktop/compiz'
	if obj_path:
		path += '/' + obj_path
	obj = BUS.get_object('org.freedesktop.compiz', path)
	iface = dbus.Interface(obj, 'org.freedesktop.compiz')
	func = getattr(iface, func_name)
	if func:
		try:
			return func(*args)
		except Exception, ex:
			print "Compiz Error: " + str(ex)
	return None

class IconFactory():
    icon_theme = gtk.icon_theme_get_default()
    # Icon types
    NORMAL = 0
    HALF_TRANSPARENT = 1
    TRANSPARENT = 2
    LAUNCHER = 3
    # Icon effect
    NO_EFFECT = 0
    BRIGHT = 1
    RED_BACKGROUND = 2
    # ACTIVE_WINDOW
    NOT_ACTIVE = 0
    ACTIVE = 1
    
        
    
    def __load_pixbufs():
        # Loads pixbufs to self.launcher_icon and self.active_icon
        try:
            homeFolder = os.path.expanduser("~")
            dockbar_folder = homeFolder + "/.dockbar"
            if not os.path.exists(dockbar_folder):
                os.mkdir(dockbar_folder)
            if not os.path.isdir(dockbar_folder):
                raise Exception(dockbar_folder + "is not a directory!")
        except:
            pass
            
        try:
            launcher_icon = gtk.gdk.pixbuf_new_from_file(dockbar_folder + '/launcher_icon.png')
        except:
            try:
                # Load from /usr/share/pixmaps/dockbar
                # (Can this be done in a more elegant way?)
                launcher_icon = gtk.gdk.pixbuf_new_from_file('/usr/share/pixmaps/dockbar/launcher_icon.png')
            except:
                #Make an empty pixbuf
                launcher_icon = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 24,24)
                launcher_icon.fill(0x00000000)
##                dialog = gtk.MessageDialog(parent=None, 
##                                  flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
##                                  type=gtk.MESSAGE_WARNING, 
##                                  buttons=gtk.BUTTONS_OK, 
##                                  message_format='Cannot load ~/.dockbar/launcher_icon.png or /usr/share/pixmaps/dockbar/launcher_icon.png. DockBar will work but will not look as good.')
##                dialog.set_title('DockBar')
##                dialog.run()
##                dialog.destroy()
                
        try:
            # Load from ~/.dockbar
            active_icon = gtk.gdk.pixbuf_new_from_file(dockbar_folder + '/active_icon.png')
        except:
            try:
                # Load from /usr/share/pixmaps/dockbar
                # (Can this be done in a more elegant way?)
                active_icon = gtk.gdk.pixbuf_new_from_file('/usr/share/pixmaps/dockbar/active_icon.png')
            except:
                # Make a light yellow overlay
                active_icon = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 24,24)
                active_icon.fill(0xFFFF0033)
##                dialog = gtk.MessageDialog(parent=None, 
##                                  flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
##                                  type=gtk.MESSAGE_WARNING, 
##                                  buttons=gtk.BUTTONS_OK, 
##                                  message_format='Cannot load ~/.dockbar/active_icon.png or /usr/share/pixmaps/dockbar/active_icon.png. DockBar will work but will not look as good.')
##                dialog.set_title('DockBar')
##                dialog.run()
##                dialog.destroy()
        return (launcher_icon, active_icon)
    
    launcher_icon, active_icon = __load_pixbufs()
    
    def __init__(self, apps_by_id, class_group, launcher = None):
        self.apps_by_id = apps_by_id
        self.launcher = launcher
        self.class_group = class_group 
        
        self.pixbuf = None
        # Pixbuf matrix (NORMAL, HALFTRANSPARENT, TRANSPARENT, LAUNCHER)x(NO_EFFECT, BRIGHT, RED_BACKGROUND)x(NOT_ACTIVE, ACTIVE)
        self.pixbuf_matrix = ( ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]) )
                            
    def __del__(self):
        self.apps_by_id = None
        self.launcher = None
        self.class_group = None
        self.pixbuf = None
        del self.pixbuf_matrix
        self.pixbuf_matrix = None
                            
    def set_size(self, size):
        # The icons should be smaller than the given size 
        # to make room for glow effect outside of the icon
        self.size = max(size - 2, 1) 
        # Reload the icon in the right size.
        self.pixbuf = self.find_icon_pixbuf(self.size)
        if (self.pixbuf.get_width() != self.size or self.pixbuf.get_height() != self.size):
            self.pixbuf = self.pixbuf.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
        # Empty the pixbuf matrix so that the pixbufs will be drawn again 
        # in their right size when requested
        self.pixbuf_matrix = ( ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]),
                               ([None, None], [None, None], [None, None]) )
                            
    def reset_active_pixbufs(self):
        for tpix in self.pixbuf_matrix:
            for epix in tpix:
                epix[1] = None
        
        
    def pixbuf_update(self, type = NORMAL, effect = NO_EFFECT, active = NOT_ACTIVE):
        if self.pixbuf_matrix[type][effect][active]:
            return self.pixbuf_matrix[type][effect][active]
        else:
            # Get the icon (a copy just in case to avoid possible segfault).
            pixbuf = self.get_icon_pixbuf().copy()
                
            if type == self.LAUNCHER:
                pixbuf = self.make_launcher_icon(pixbuf)
                
            pixbuf =  self.pixbuf_add_border(pixbuf, 1)
            
            if active == self.ACTIVE:
                pixbuf = self.add_glow(pixbuf)
            
            if type == self.HALF_TRANSPARENT:
                pixbuf2 = self.get_icon_pixbuf().copy()
                pixbuf2 = self.pixbuf_add_border(pixbuf2, 1)
                pixbuf2 = self.add_full_transparency(pixbuf2)
                pixbuf = self.combine_icons(pixbuf,pixbuf2)
            elif type == self.TRANSPARENT:
                pixbuf = self.add_full_transparency(pixbuf)
            
            if effect == self.BRIGHT: 
                pixbuf = self.colorshift(pixbuf, 50)
            elif effect == self.RED_BACKGROUND:
                pixbuf = self.add_red_background(pixbuf)
            
            self.pixbuf_matrix[type][effect][active] = pixbuf
            return pixbuf
            
        
    def get_icon_pixbuf(self):
        if not self.pixbuf:
            self.pixbuf = self.find_icon_pixbuf(self.size)
        if (self.pixbuf.get_width() != self.size or self.pixbuf.get_height() != self.size):
            self.pixbuf = self.pixbuf.scale_simple(iconSize, iconSize, gtk.gdk.INTERP_BILINEAR)
        return self.pixbuf
        
        
    def find_icon_pixbuf(self, size):
        pixbuf = None
        if self.class_group:
            name = self.class_group.get_res_class().lower()
        if isinstance(size, gtk.IconSize):
            iconSize = gtk.icon_size_lookup(iconSize)[0]
        
        if self.launcher:
            icon_name = self.launcher.get_icon_name()
            if os.path.isfile(icon_name):
                pixbuf = self.icon_from_file_name(icon_name, size)
                return pixbuf
        elif name+".desktop" in self.apps_by_id:
            icon = self.apps_by_id[name+".desktop"].get_icon()
            if icon.__class__ == gio.FileIcon:
                if icon.get_file().query_exists(None):
                    pixbuf = self.icon_from_file_name(icon.get_file().get_path(), size)
                    return pixbuf
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
                return pixbuf
        
        pixbuf = self.icon_search_in_data_path(icon_name, size)
        
        if pixbuf == None and self.class_group:
            pixbuf = self.class_group.get_icon().copy()
        elif pixbuf == None:
            # If no pixbuf has been found (can only happen for an unlaunched
            #launcher), make an empty pixbuf and show a warning.
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size,size)
            pixbuf.fill(0x00000000)
            dialog = gtk.MessageDialog(parent=None, 
                                  flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  type=gtk.MESSAGE_WARNING, 
                                  buttons=gtk.BUTTONS_OK, 
                                  message_format='Cannot load icon for launcher '+ self.launcher.get_name()+'.')
            dialog.set_title('DockBar')
            dialog.run()
            dialog.destroy()
        return pixbuf

    def icon_from_file_name(self, iconName, iconSize = -1):
        if os.path.isfile(iconName):
            try:
                return gtk.gdk.pixbuf_new_from_file_at_size(iconName, -1, iconSize)
            except:
                pass
        return None
    
    def icon_search_in_data_path(self, iconName, iconSize):
        dataFolders = None
        
        if os.environ.has_key("XDG_DATA_DIRS"):
            dataFolders = os.environ["XDG_DATA_DIRS"]
            
        if not dataFolders:
            dataFolders = "/usr/local/share/:/usr/share/"
            
        for dataFolder in dataFolders.split(':'):
            #The line below line used datafolders instead of datafolder.
            #I changed it because I suspect it was a bug.
            paths = (os.path.join(dataFolder, "pixmaps", iconName), 
                     os.path.join(dataFolder, "icons", iconName)) 
            for path in paths:
                if os.path.isfile(path):
                    icon = self.icon_from_file_name(path, iconSize)
                    if icon:
                        return icon
        return None
    
    def pixbuf_add_border(self, pixbuf, b):
        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width() + b*2, pixbuf.get_height() + b*2)
        background.fill(0x00000000)
        pixbuf.composite(background, b, b, pixbuf.get_width(), pixbuf.get_height(), b, b, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        return background
    
    def combine_icons(self, pixbuf, pixbuf2):
        if self.size <= 1:
            return pixbuf
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixbuf.get_width(), pixbuf.get_height())
        context = cairo.Context(surface)
        ctx = gtk.gdk.CairoContext(context)

        linear = cairo.LinearGradient(0, 0, pixbuf.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 0.5)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 1)
        ctx.set_source_pixbuf(pixbuf2, 0, 0)
        #ctx.mask(linear)
        ctx.paint()

        linear = cairo.LinearGradient(0, 0, pixbuf.get_width(), 0)
        linear.add_color_stop_rgba(0.4, 0, 0, 0, 1)
        linear.add_color_stop_rgba(0.6, 0, 0, 0, 0)
        ctx.set_source_pixbuf(pixbuf, 0, 0)
        ctx.mask(linear)
        

        
        sio = StringIO()
        surface.write_to_png(sio)
        sio.seek(0)
        loader = gtk.gdk.PixbufLoader()
        loader.write(sio.getvalue())
        loader.close()
        sio.close()
        return loader.get_pixbuf()

    
    def add_full_transparency(self, pixbuf):
        icon_transp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        icon_transp.fill(0x00000000)
        pixbuf.composite(icon_transp, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 190)
        icon_transp.saturate_and_pixelate(icon_transp, 0.14, False)
        return icon_transp
    
    def make_launcher_icon(self, pixbuf):
        # make icon smaller than pixbuf
        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        background.fill(0x00000000)
        size =pixbuf.get_width()
        small_size = int(0.80 * size)
        pixbuf = pixbuf.scale_simple(small_size, small_size, gtk.gdk.INTERP_BILINEAR)
        offset = int((size - small_size) / 2 + 0.5)
        pixbuf.composite(background, offset, offset, small_size, small_size, offset ,offset, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
        # add the overlay
        overlay = self.launcher_icon.scale_simple(size, size, gtk.gdk.INTERP_BILINEAR)
        overlay.composite(background, 0, 0, overlay.props.width, overlay.props.height, 0, 0, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
        return background
    
    def add_active_icon(self, pixbuf):
        overlay = self.active_icon.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        overlay.composite(pixbuf, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1.0, 1.0, gtk.gdk.INTERP_BILINEAR, 255)
        return pixbuf
    
    def add_glow(self, pixbuf):
        # Convert color hex-string (format '#FFFFFF')to int r, g, b
        color = settings['active_glow_color']
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        # Transparency
        alpha = settings['active_glow_alpha']
        # Thickness (pixels)
        tk = 2
        
        colorpb = self.colorize_pixbuf(pixbuf, r, g, b)
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
        
    def add_red_background(self, pixbuf):
        background = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        #Red background
        background.fill(0xFF000088)
        pixbuf.composite(background, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        return background
        
    def greyscale(self, pixbuf):
        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = pix[1] = pix[2] = (int(pix[0]) + int(pix[1]) + int(pix[2])) / 3
        return pixBuf
    
    def colorshift(self, pixbuf, shift):
        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = min(255, int(pix[0]) + shift)
                pix[1] = min(255, int(pix[1]) + shift)
                pix[2] = min(255, int(pix[2]) + shift)
        return pixbuf
    
    def colorize_pixbuf(self, pixbuf, r, g, b):
        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = r
                pix[1] = g
                pix[2] = b
        return pixbuf

    
class CairoPopup():
    def __init__(self, colormap):
        gtk.widget_push_colormap(colormap)
        self.window = gtk.Window(gtk.WINDOW_POPUP)
        gtk.widget_pop_colormap()
        self.vbox = gtk.VBox()
        
        # Initialize colors, alpha transparency         
        self.window.set_app_paintable(1)
        if not self.window.is_composited():
            self.supports_alpha = False
        else:
            self.supports_alpha = True
        
        self.window.connect("expose_event", self.expose)
        
        
    def expose(self, widget, event):
        self.setup()
        w,h = self.window.get_size()
        self.ctx = self.window.window.cairo_create()
        # set a clip region for the expose event, XShape stuff
        self.ctx.save()
        if self.supports_alpha == False:
                self.ctx.set_source_rgb(1, 1, 1)
        else:
                self.ctx.set_source_rgba(1, 1, 1,0)
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
        
        if self.supports_alpha == False:
                ctx.set_source_rgb(red, green, blue)
        else:
                ctx.set_source_rgba(red, green, blue, alpha)
        ctx.fill_preserve()
        if self.supports_alpha == False:
                ctx.set_source_rgb(0.0, 0.0, 0.0)
        else:
                ctx.set_source_rgba(0.0, 0.0, 0.0, alpha)
        ctx.set_line_width(1)
        ctx.stroke()
        ctx.restore()
        ctx.clip()
        
    def __del__(self):
        self.window = None
        self.ctx = None
        self.pixmap = None
        self.vbox = None
        self.supports_alpha = None

class PersistentList():
    @staticmethod
    def create_new_list_with(file, list):
        try:
            fd = open(file, "wb")
        except IOError:
            raise Exception("Can't open file for writing!")
        else:
            pickle.dump(list, fd)
            fd.close()
            
    def __init__(self, path_to_list):
        if not os.path.exists(path_to_list):
            self.create_new(path_to_list)
        
        if not os.path.isfile(path_to_list):
            raise Exception("Path '"+ path_to_list +"' is not a file!")
        
        self.path_to_list = path_to_list
    
    def create_new(self, path_to_list):
        try:
            file = open(path_to_list, "wb")
        except IOError:
            raise Exception("Can't open file for writing!")
        else:
            pickle.dump([], file)
            file.close()
            
    def read_list(self):
        listToReturn = []
        try:
            file = open(self.path_to_list, "rb")
        except IOError:
            raise Exception("Can't open file for reading!")
        else:
            listToReturn = pickle.load(file)
            file.close()
        return listToReturn
        
    def write_list(self, inList):
        if not isinstance(inList, list):
            raise Exception("Given object is not a list!")
        try:
            file = open(self.path_to_list, "wb")
        except IOError:
            raise Exception("Can't open file for writing!")
        else:
            pickle.dump(inList, file)
            file.close()



class Launcher():
    def __init__(self, name, path):
        self.name = name
        if not os.path.exists(path):
            raise Exception, "DesktopFile "+fileName+" doesn't exist."
        
        self.desktopEntry = DesktopEntry(path)
        
    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name=name
        
    def get_icon_name(self):
        return self.desktopEntry.getIcon()
    
    def get_entry_name(self):
        return self.desktopEntry.getName()
    
    def launch(self):
        print 'Executing ' + self.desktopEntry.getExec()
        self.execute(self.desktopEntry.getExec())

    def remove_args(self, stringToExecute):
        specials = ["%f","%F","%u","%U","%d","%D","%n","%N","%i","%c","%k","%v","%m","%M", "-caption","--view", "\"%c\""]
        return [element for element in stringToExecute.split() if element not in specials]

    def execute(self, command, runInTerminal=False, useXdgOpen=False):
        command = self.remove_args(command)
        os.chdir(os.path.expanduser("~"))
        if runInTerminal == True:
            command.insert(0, '-x')
            command.insert(0, 'gnome-terminal')
            pid = os.spawnvp(os.P_NOWAIT, '/usr/bin/gnome-terminal', command)
        else:
            if useXdgOpen == True:
                command.insert(0, 'xdg-open')
            #print command[0]
            #print command
            pid = os.fork()
            if pid:
                os.spawnvp(os.P_NOWAIT,command[0], command)
                os._exit(0)
                
                
class GroupList():
    # A class to replace a dictionary since dictionaries are bad at order
    def __init__(self):
        self.list = []
        
    def __getitem__(self, name):
        return self.get_group(name)
    
    def __setitem__(self, name, group_button):
        self.add_group(name, group_button)
        
    def __contains__(self, name):
        for tuple in self.list:
            if tuple[0] == name: 
                return True
        else:
            return False
        
    def __iter__(self):
        return self.get_names().__iter__()
        
    def add_group(self, name, group_button, path_to_launcher=None, index=None):
        tuple = (name, group_button, path_to_launcher)
        if index:
            self.list.insert(index, tuple)
        else:
            self.list.append(tuple)
            
        
    def get_group(self, name):
        for tuple in self.list:
            if tuple[0] == name: 
                return tuple[1]
    
    def get_path(self, name):
        for tuple in self.list:
            if tuple[0] == name: 
                return tuple[2]
            
    def get_groups(self):
        grouplist = []
        for tuple in self.list:
            grouplist.append(tuple[1])
        return grouplist
        
    def get_names(self):
        namelist = []
        for tuple in self.list:
            namelist.append(tuple[0])
        return namelist
    
    def get_non_launcher_names(self):
        #Get a list of names of all buttons without launchers
        namelist = []
        for tuple in self.list:
            if not tuple[2]:
                namelist.append(tuple[0])
        return namelist
                
    def get_index(self, name):
        for tuple in self.list:
            if tuple[0]==name: 
                return self.list.index(tuple)
            
    def move(self, name, index):
        for tuple in self.list:
            if name == tuple[0]: 
                self.list.remove(tuple)
                self.list.insert(index, tuple)
                
    def remove(self,name):
        for tuple in self.list:
            if name == tuple[0]: 
                self.list.remove(tuple)
                return True
            
    def get_launchers_list(self):
        #Returns a list of name and launcher paths tuples
        launcherslist = []
        for tuple in self.list:
            #if launcher exist
            if tuple[2]: 
                launchertuple = (tuple[0],tuple[2])
                launcherslist.append(launchertuple)
        return launcherslist
    
class WindowButton():
    def __init__(self,window,groupbutton):
        self.groupbutton = groupbutton
        self.screen = self.groupbutton.screen
        self.name = window.get_name()
        self.window = window
        self.locked = False
        self.is_active_window = False
        self.needs_attention = False
        
        self.window.connect("state-changed",self.window_state_changed)
        self.window.connect("icon-changed",self.window_icon_changed)
        self.window.connect("name-changed",self.window_name_changed)
        
        #self.window_button = gtk.ToggleButton()
        #self.window_button.set_relief(gtk.RELIEF_NONE)
        self.window_button = gtk.EventBox()
        self.window_button.set_visible_window(False)
        self.window_button.connect("enter-notify-event",self.button_mouse_enter)
        self.window_button.connect("leave-notify-event",self.button_mouse_leave)
        ##self.button.connect("button-press-event",self.window_button_press_event)
        self.window_button.connect("button-release-event",self.window_button_release_event)
        self.window_button.connect("scroll-event",self.window_button_scroll_event)
        
        
        self.label = gtk.Label()
        self.window_name_changed(self.window)
            
        if window.needs_attention():
            self.needs_attention = True
            self.groupbutton.needs_attention_changed()
        
        ##self.window_button.set_alignment(0, 0.5)
        self.window_button_icon = gtk.Image()
        self.window_icon_changed(window)
        ##self.window_button.set_image(self.window_button_icon)
        hbox = gtk.HBox()
        hbox.pack_start(self.window_button_icon, False, padding = 2)
        hbox.pack_start(self.label, False)
        self.window_button.add(hbox)
        
        
        self.update_state()
        
        groupbutton.winlist.pack_start(self.window_button,False)
        
    
    def set_button_active(self, mode):
        self.is_active_window = mode
        self.update_state()
        
    def update_state(self, mouseover=False):
        attr_list = pango.AttrList()
        if mouseover:
            attr_list.insert(pango.AttrUnderline(pango.UNDERLINE_SINGLE, 0, 50))
        if self.needs_attention:
            attr_list.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, 50))
            ##attr_list.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 50))
            ##attr_list.insert(pango.AttrForeground(40000, 5000, 5000, 0, 50))
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
            
            
        
    def __del__ (self):
        ##print "window_button __del__"
        pass
        
    def del_button(self):
        ##print "WindowButton del_button"
        self.window_button.destroy()
        del self.groupbutton.windows[self.window]
        self.window = None
        
    def window_state_changed(self, window,changed_mask, new_state):
        if wnck.WINDOW_STATE_MINIMIZED & changed_mask & new_state:
            if self.locked:
                self.window_button_icon.set_from_pixbuf(self.icon_locked)
            else:
                self.window_button_icon.set_from_pixbuf(self.icon_transp)
            self.groupbutton.minimized_windows_count+=1
            self.groupbutton.update_state()
            self.update_state()
        elif wnck.WINDOW_STATE_MINIMIZED & changed_mask:
            self.window_button_icon.set_from_pixbuf(self.icon)
            self.groupbutton.minimized_windows_count-=1
            if self.locked:
                self.locked = False
                ##self.window_button.set_property("image-position",gtk.POS_LEFT)
                self.groupbutton.locked_windows_count -= 1
            self.groupbutton.update_state()
            self.update_state()
            
        # Check if the window needs attention
        if window.needs_attention() != self.needs_attention:
            self.needs_attention = window.needs_attention()
            self.update_state()
            self.groupbutton.needs_attention_changed()
        
                            
    def window_icon_changed(self, window):
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
        
    def window_name_changed(self, window):
        name = u""+window.get_name()
        if len(name) > 40:
            name = name[0:37]+"..."
        self.name = name
        self.label.set_label(name)
        
    def button_mouse_enter(self, widget, event):
        self.update_state(True)
        
    def button_mouse_leave(self, widget, event):
        self.update_state(False)
        
    def window_button_scroll_event(self, widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = settings['windowbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = settings['windowbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)
        
    def window_button_release_event(self, widget,event):
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


        
    #### Actions
    
    def select_or_minimize_window(self, widget, event):
        if self.screen.get_active_workspace() != self.window.get_workspace():
            self.window.get_workspace().activate(event.time)
        if not self.window.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.window.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            self.groupbutton.popup.hide()
            self.groupbutton.popup_showing = False
            
        if self.window.is_minimized():              
            if self.locked:
                self.locked = False
                self.window_button.set_property("image-position",gtk.POS_LEFT)
                self.groupbutton.locked_windows_count -= 1
            self.window.unminimize(event.time)
        elif self.window.is_active():
            self.window.minimize()
        else:
            self.window.activate(event.time)
            
    def close_window(self, widget, event):
        self.window.close(event.time)
        
    def lock_or_unlock_window(self, widget, event):
        if self.locked == False:
            self.locked = True
            
            ##self.window_button.set_property("image-position",gtk.POS_RIGHT)
            self.groupbutton.locked_windows_count += 1
            if not self.window.is_minimized():
                self.window.minimize()
            else:
                self.window_button_icon.set_from_pixbuf(self.icon_locked)
                self.groupbutton.update_state()
        else:
            self.locked = False
            ##self.window_button.set_property("image-position",gtk.POS_LEFT)
            self.groupbutton.locked_windows_count -= 1
            self.window.unminimize(event.time)
            
    def shade_window(self, widget, event):
        self.window.shade()
        
    def unshade_window(self, widget, event):
        self.window.unshade()
    
    def no_action(self, widget = None, event = None):
        pass
        
    action_function_dict = { 'select or minimize window': select_or_minimize_window,
                             'close window': close_window,
                             'lock or unlock window': lock_or_unlock_window,
                             'shade window': shade_window,
                             'unshade window': unshade_window,
                             'no action': no_action }
        

class GroupButton ():
    def __init__(self,dockbar,class_group=None, launcher=None, index=None): 
        
        self.launcher = launcher
        self.class_group = class_group
        self.dockbar = dockbar
        self.windows = {}
        self.minimized_windows_count = 0
        self.minimized_state = 0
        self.locked_windows_count = 0
        self.has_active_window = False
        self.needs_attention = False
        self.attention_effect_running = False
        if class_group: 
            self.res_class = class_group.get_res_class()
            if self.res_class == "":
                self.res_class = class_group.get_name()
        elif launcher:
            self.res_class = launcher.get_name()
        else:
            raise Exception, "Can't initiate Group button without class_group or launcher."
        self.get_group_name()
        self.screen = wnck.screen_get_default()
        self.root_xid = self.dockbar.root_xid
        
        self.image = gtk.Image()
        self.icon_factory = IconFactory(self.dockbar.apps_by_id, class_group, launcher)
        self.button = gtk.EventBox()
        self.button.set_visible_window(False)
        self.button.connect("enter-notify-event",self.button_mouse_enter)
        self.button.connect("leave-notify-event",self.button_mouse_leave)
        self.button.connect("button-release-event",self.group_button_release_event)
        self.button.connect("button-press-event",self.group_button_press_event)
        self.button.connect("scroll-event",self.group_button_scroll_event)
        
        self.menu = self.create_menu()
        hbox = gtk.HBox()
##        if self.dockbar.orient == "v":
##            size = self.button.get_allocation().width
##        else:
##            size = self.button.get_allocation().height
##        self.icon_factory.set_size(size)
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
        
        gtk_screen = self.dockbar.container.get_screen()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap == None:
            colormap = gtk_screen.get_rgb_colormap()
        cairo_popup = CairoPopup(colormap)    
        
        self.winlist = cairo_popup.vbox
        self.winlist.set_border_width(5)
        self.popup_label = gtk.Label("<span foreground='"+settings['normal_text_color']+"'><big><b>"+self.name+"</b></big></span>")
        self.popup_label.set_use_markup(True)
        self.popup_label.set_tooltip_text("Resource class name: "+self.res_class)
        self.winlist.pack_start(self.popup_label,False)
        
        
        self.popup =  cairo_popup.window
        self.popup_showing = False
        self.popup.connect("leave-notify-event",self.popup_mouse_leave)
        self.popup.add(self.winlist)
        
        self.button.connect("size-allocate", self.sizealloc)
        
        #Setup buttons as a drop zone for desktop configuration files
        self.button.connect("drag_data_received", self.drag_data_received)
        self.button.drag_dest_set(gtk.DEST_DEFAULT_ALL, 
                                  [('text/uri-list', 0, 0), ('text/groupbutton_name', 0, TARGET_TYPE_GROUPBUTTON)],
                                  gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        
        #Make buttons drag-able
        self.button.connect("drag_data_get", self.drag_data_get)
        self.button.drag_source_set(gtk.gdk.BUTTON1_MASK, [('text/groupbutton_name', 0, TARGET_TYPE_GROUPBUTTON)], gtk.gdk.ACTION_MOVE)
        self.button.drag_source_set_icon_pixbuf(self.icon_factory.find_icon_pixbuf(32))
        
        self.button.connect("drag_begin", self.drag_begin)
        ##self.button.connect("drag_end", self.drag_end)
        
        
        
    def create_menu(self):
        #Creates a popup menu
        menu = gtk.Menu()
        #Tell the program that popups can be shown again after the menu is closed
        menu.connect('selection-done', self.menu_closed)
        if self.launcher:
            #Launch program item
            launch_program_item = gtk.MenuItem('Launch program')
            menu.append(launch_program_item)
            launch_program_item.connect("activate", self.launch_application)
            launch_program_item.show()
            #Remove launcher item
            remove_launcher_item = gtk.MenuItem('Remove launcher')
            menu.append(remove_launcher_item)
            remove_launcher_item.connect("activate", self.remove_launcher)
            remove_launcher_item.show()
        #Close all windows item
        close_all_windows_item = gtk.MenuItem('Close all windows')
        menu.append(close_all_windows_item)
        close_all_windows_item.connect("activate", self.close_all_windows)
        close_all_windows_item.show()
        
        return menu
    
    def menu_closed(self, menushell):
        self.dockbar.right_menu_showing = False
        
    def get_group_name(self):
        if self.launcher:
            self.name = self.launcher.get_entry_name()
        elif self.res_class.lower()+".desktop" in self.dockbar.apps_by_id:
            self.name = self.dockbar.apps_by_id[self.res_class.lower()+".desktop"].get_name()
        else:
            self.name = self.class_group.get_name().split(" - ", 1)[0]
        return self.name
        
        
    def sizealloc(self,applet,allocation):
        if allocation.height<=1:
            return
        if self.dockbar.orient == "v":
            if not self.image.get_pixbuf() or self.image.get_pixbuf().get_width() != allocation.width:
                self.icon_factory.set_size(self.button.get_allocation().width)
                self.update_state()
        else:
            if not self.image.get_pixbuf() or self.image.get_pixbuf().get_height() != allocation.height:
                self.icon_factory.set_size(self.button.get_allocation().height)
                self.update_state()
        
        # Change to where the minimize animation is drawn.
        x, y = self.button.window.get_origin()
        a = self.button.get_allocation()
        x += a.x
        y += a.y
        for window in self.windows.keys():
            window.set_icon_geometry(x, y, a.width, a.height)
            
    def update_popup_label(self):
        self.popup_label.set_text("<span foreground='"+settings['normal_text_color']+"'><big><b>"+self.name+"</b></big></span>")
        self.popup_label.set_use_markup(True)
            
    def update_state(self):
        if self.has_active_window:
            self.icon_active = IconFactory.ACTIVE
        else:
            self.icon_active = IconFactory.NOT_ACTIVE
            
        if self.launcher and not self.windows:
            self.icon_mode = IconFactory.LAUNCHER
        elif len(self.windows) - self.minimized_windows_count == 0:
            self.icon_mode = IconFactory.TRANSPARENT
        elif (self.minimized_windows_count - self.locked_windows_count) > 0:
            self.icon_mode = IconFactory.HALF_TRANSPARENT
        else:
            self.icon_mode = IconFactory.NORMAL
            
        if self.needs_attention:
            if settings["groupbutton_attention_notification_type"] == 'red':
                self.icon_effect = IconFactory.RED_BACKGROUND
            else:
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    gobject.timeout_add(700, self.attention_effect)
                self.icon_effect = IconFactory.NO_EFFECT
        else:
            self.icon_effect = IconFactory.NO_EFFECT
            
        self.image.set_from_pixbuf(self.icon_factory.pixbuf_update(self.icon_mode, self.icon_effect, self.icon_active))
        self.image.show()
        
    def request_update_state(self):
        if self.button.get_allocation().width>1:
            self.update_state()
            
    def attention_effect (self):
        self.attention_effect_running = True
        if self.needs_attention:
            if settings["groupbutton_attention_notification_type"] == 'compwater':
                x,y = self.button.window.get_origin()
                alloc = self.button.get_allocation()
                x = x + alloc.x + alloc.width/2
                y = y + alloc.y + alloc.height/2
                compiz_call('water/allscreens/point','activate','root',self.root_xid,'x',x,'y',y)
            elif settings["groupbutton_attention_notification_type"] == 'blink':
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    pixbuf = self.icon_factory.pixbuf_update(self.icon_mode, IconFactory.BRIGHT, self.icon_active)
                    self.image.set_from_pixbuf(pixbuf)
                else:
                    self.needs_attention_anim_trigger = False
                    pixbuf = self.icon_factory.pixbuf_update(self.icon_mode, IconFactory.NO_EFFECT, self.icon_active)
                    self.image.set_from_pixbuf(pixbuf)
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False
        



    def show_list(self):
        offset = 3
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if self.popup_showing or ((b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height) \
           and not self.dockbar.right_menu_showing and not self.dockbar.dragging):
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
                    self.popup.move(x-w,y)
                else:
                    self.popup.move(x+b_alloc.width,y)
            self.popup.show_all()
            self.popup_showing = True
        return False

    def hide_list(self):
        p_m_x,p_m_y = self.popup.get_pointer()
        p_w,p_h = self.popup.get_size()
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if ((p_m_x<0 or p_m_x>(p_w-1))or(p_m_y<0 or p_m_y>(p_h-1))) and \
        ((b_m_x<0 or b_m_x>(b_r.width-1)) or (b_m_y<0 or b_m_y>(b_r.height-1))):
            self.popup.hide()
            self.popup_showing = False
        return False
    
    def hide_list_no_check(self):
        self.popup.hide()
        self.popup_showing = False
        return False

    def button_mouse_enter (self,widget,event):
        if not self.dockbar.right_menu_showing and not self.dockbar.dragging: 
            gobject.timeout_add(settings['popup_delay'], self.show_list)

    def button_mouse_leave (self,widget,event):
        gobject.timeout_add(100,self.hide_list)

    def popup_mouse_leave (self,widget,event):
        self.hide_list()
        if not self.windows: 
            self.image.set_from_pixbuf(self.icon_factory.pixbuf_update(IconFactory.LAUNCHER))
            self.image.show() 
        
    def drag_begin(self, widget, drag_context):
        self.dockbar.dragging = True
        self.hide_list_no_check()
        
    def drag_end(self, widget, drag_context):
        #self.dockbar.dragging = False
        pass
        
    def drag_data_get(self, widget, context, selection, targetType, eventTime):
        selection.set(selection.target, 8, self.res_class)
        
    def drag_data_received(self, wid, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_GROUPBUTTON:
            if selection.data != self.res_class:
                self.dockbar.move_groupbutton(selection.data, calledFrom=self.res_class)
        else:
            #remove 'file://' and '/n' from the URI
            path = selection.data[7:-2] 
            print path
            self.dockbar.make_new_launcher(path, self.res_class)


    def __del__(self):
        if self.button:
            self.button.destroy()
        self.button = None
        self.popup = None
        self.windows = None
        self.winlist = None
        self.dockbar = None
        self.menu = None
        self.drag_pixbuf = None

    def add_window(self,window):
        #print "add_window"
        self.windows[window] = WindowButton(window,self)
        if window.is_minimized():
            self.minimized_windows_count += 1
        if (self.launcher and len(self.windows)==1):
            self.class_group = window.get_class_group()
        # Update state unless the button hasn't been shown yet.
        self.request_update_state()
        
        #Update popup-list if it is being shown.
        if self.popup_showing:
            self.winlist.show_all()
            gobject.idle_add(self.show_list)
        
        # Set minimize animation 
        # (if the eventbox is created already, otherwice the icon animation is set in sizealloc())
        if self.button.window:
            x, y = self.button.window.get_origin()
            a = self.button.get_allocation()
            x += a.x
            y += a.y
            window.set_icon_geometry(x, y, a.width, a.height)
        
    def del_window(self,window):
        if window.is_minimized():
            self.minimized_windows_count -= 1
        self.windows[window].del_button()
        self.request_update_state()
        if not self.windows and not self.launcher:
            self.hide_list_no_check()
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            self.dockbar.groups.remove(self.res_class)
        elif not self.windows and self.launcher and self.popup_showing:
            self.popup.resize(10,10)
            gobject.idle_add(self.show_list)
            

            
    def set_has_active_window(self, mode):
        if mode != self.has_active_window:
            self.has_active_window = mode 
            if mode == False:
                for window_button in self.windows.values():
                    window_button.set_button_active(False) 
            self.request_update_state()
            
    def needs_attention_changed(self):
        # Checks if there are any urgent windows and changes 
        # the group button looks if there are at least one
        for window in self.windows.keys():
            if window.needs_attention():
                self.needs_attention = True
                self.request_update_state()
                return True
        else:
            if self.windows.keys() == []:
                # The window needs attention already when it's added,
                # before it's been added to the list.
                self.needs_attention = True
                # Update state unless the button hasn't been shown yet.
                self.request_update_state()
                return True
            else:
                self.needs_attention = False
                # Update state unless the button hasn't been shown yet.
                self.request_update_state()
                return False
        
    def group_button_scroll_event (self,widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = settings['groupbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = settings['groupbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)
        
    def group_button_release_event(self, widget, event):
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
        
    
    def group_button_press_event(self,widget,event):
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
        elif event.button == 1: return False 
        return True
        
    #### Actions
    def select_or_minimize_group(self, widget, event):
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
        
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized():
                    ignored = False
                    if not win.is_pinned() and screen.get_active_workspace() != win.get_workspace():
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
        
        for win in windows_stacked:
            if (not win.is_skip_tasklist()) and (not win.is_minimized()) \
               and (win.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() and active_workspace != win.get_workspace():
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
            ignorelist.reverse()
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
                self.hide_list_no_check()
            for win in grp_win_stacked:
                if win.is_minimized():
                    win.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            ordered_list = []
            # Ignorelist was reversed earlier.
            ignorelist.reverse()
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list
            
        if grtop and not moved:
            for win in grp_win_stacked:
                self.windows[win].window.minimize()
        if not grtop:
            for win in grp_win_stacked:
                self.windows[win].window.activate(event.time)
                        
    def select_only(self, widget, event):
        # Brings up all windows, does nothing if they are already brought up.
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
        
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized():
                    ignored = False
                    if not win.is_pinned() and screen.get_active_workspace() != win.get_workspace():
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
        
        for win in windows_stacked:
            if (not win.is_skip_tasklist()) and (not win.is_minimized()) \
               and (win.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() and active_workspace != win.get_workspace():
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
            ignorelist.reverse()
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
                self.hide_list_no_check()
            for win in grp_win_stacked:
                if win.is_minimized():
                    win.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            ordered_list = []
            # Ignorelist was reversed earlier.
            ignorelist.reverse()
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list
                
        for win in grp_win_stacked:
                self.windows[win].window.activate(event.time)
                    
    def minimize_all_windows(self,widget, event):
        for win in self.windows:
            self.windows[win].window.minimize()

    def close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            #What should really be put here instead of 0?
            t = 0
        for window in self.windows:
            window.close(t) 
            
    def launch_application(self, widget=None, event=None):
        if self.launcher:
            self.launcher.launch()
            
    def show_menu(self, widget, event):
        self.hide_list_no_check()
        self.menu.popup(None, None, None, event.button, event.time)
        self.dockbar.right_menu_showing = True

    def remove_launcher(self, widget=None, event = None):
        print 'Removing launcher ' + self.res_class
        self.launcher = None
        self.close_all_windows()
        self.popup.destroy()
        self.button.destroy()
        self.winlist.destroy()
        self.dockbar.groups.remove(self.res_class)
        self.dockbar.save_launchers_persistentlist()
        
    def minimize_all_other_groups(self, widget, event):
        self.hide_list_no_check()
        for gr in self.dockbar.groups.get_groups():
            if self != gr:
                for win in gr.windows:
                    gr.windows[win].window.minimize()
                    
    def compiz_scale_windows(self, widget, event):
        if not self.class_group or \
           len(self.windows) - self.minimized_windows_count == 0:
            return
        
        compiz_call('scale/allscreens/initiate_key','activate','root', self.root_xid,'match','iclass='+self.class_group.get_res_class())
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay']+ 200, self.hide_list_no_check)

    def compiz_shift_windows(self, widget, event):
        if not self.class_group or \
           len(self.windows) - self.minimized_windows_count == 0:
            return
        
        compiz_call('shift/allscreens/initiate_key','activate','root', self.root_xid,'match','iclass='+self.class_group.get_res_class())
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(settings['popup_delay']+ 200, self.hide_list_no_check)
        
    def no_action(self, widget = None, event = None):
        pass

    action_function_dict = { "select or minimize group": select_or_minimize_group,
                             "select group": select_only,
                             "close all windows": close_all_windows,
                             "minimize all windows": minimize_all_windows,
                             "launch application": launch_application,
                             "show menu": show_menu,
                             "remove launcher": remove_launcher,
                             "minimize all other groups": minimize_all_other_groups,
                             "compiz scale windows": compiz_scale_windows,
                             "compiz shift windows": compiz_shift_windows,
                             "no action": no_action }


class AboutDialog():
    __instance = None
    
    def __init__ (self):
        if AboutDialog.__instance == None:
            AboutDialog.__instance = self
        else:
            AboutDialog.__instance.about.present()
            return
        self.about = gtk.AboutDialog()
        self.about.set_name("DockBar Applet")
        self.about.set_version(VERSION)
        self.about.set_copyright("Copyright (c) 2008-2009 Aleksey Shaferov (Experimental features by Matias S\xc3\xa4rs)")
        self.about.connect("response",self.about_close)
        self.about.show()
    
    def about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None


class PrefDialog():
    __instance = None

    def __init__ (self):
        global PREFDIALOG
        if PrefDialog.__instance == None:
            PrefDialog.__instance = self
        else:
            PrefDialog.__instance.dialog.present()
            return
        
        PREFDIALOG = self
        self.dialog = gtk.Dialog("DockBar preferences")
        self.dialog.connect("response",self.dialog_close)
        
        ca = self.dialog.get_content_area()
        notebook = gtk.Notebook()
        notebook.set_tab_pos(gtk.POS_TOP)
        appearance_box = gtk.VBox()
        behavior_box = gtk.VBox()
        
        # Behavior page
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        label1 = gtk.Label("<big>Workspace behavior on Select group</big>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        self.rb2_1 = gtk.RadioButton(None, "Ignore windows on other workspaces")
        self.rb2_1.connect("toggled", self.rb_toggled, "rb2_ignore")
        self.rb2_2 = gtk.RadioButton(self.rb2_1, "Switch workspace when needed")
        self.rb2_2.connect("toggled", self.rb_toggled, "rb2_switch")
        self.rb2_3 = gtk.RadioButton(self.rb2_1, "Move windows from other workspaces")
        self.rb2_3.connect("toggled", self.rb_toggled, "rb2_move")
        vbox.pack_start(self.rb2_1, False)
        vbox.pack_start(self.rb2_2, False)
        vbox.pack_start(self.rb2_3, False)
        hbox.pack_start(vbox, True)
        
        vbox = gtk.VBox()
        label1 = gtk.Label("<big>Popup delay</big>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        spinbox = gtk.HBox()
        spinlabel = gtk.Label("Delay:")
        spinlabel.set_alignment(0,0.5)
        adj = gtk.Adjustment(0, 0, 2000, 1, 50)
        self.delay_spin = gtk.SpinButton(adj, 0.5, 0)
        adj.connect("value_changed", self.spin_changed, self.delay_spin)
        spinbox.pack_start(spinlabel, False)
        spinbox.pack_start(self.delay_spin, False)
        vbox.pack_start(spinbox, False)
        hbox.pack_start(vbox, True)
        behavior_box.pack_start(hbox, False, padding=5)
        
        label2 = gtk.Label("<big>Button configuration</big>")
        label2.set_alignment(0,0.5)
        label2.set_use_markup(True)
        behavior_box.pack_start(label2,False, padding=5)
        
        table = gtk.Table(10,6)
        label = gtk.Label("Groupbutton actions")
        label.set_alignment(0,0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 6, 0, 1)
        
        # A directory of combobox names and the name of corresponding setting
        self.gb_labels_and_settings = {'Left mouse button': "groupbutton_left_click_action",
                                       'Shift + left mouse button': "groupbutton_shift_and_left_click_action",
                                       'Middle mouse button': "groupbutton_middle_click_action",
                                       'Shift + middle mouse button': "groupbutton_shift_and_middle_click_action",
                                       'Right mouse button': "groupbutton_right_click_action",
                                       'Shift + right mouse button': "groupbutton_shift_and_right_click_action",
                                       'Scroll up': "groupbutton_scroll_up", 
                                       'Scroll down': "groupbutton_scroll_down" }
        # A list to ensure that the order is kept correct
        gb_button_labels = ['Left mouse button',
                            'Shift + left mouse button',
                            'Middle mouse button',
                            'Shift + middle mouse button',
                            'Right mouse button',
                            'Shift + right mouse button',
                            'Scroll up',
                            'Scroll down' ]
        self.gb_combos = {}
        for i in range(len(gb_button_labels)):
            text = gb_button_labels[i]
            label = gtk.Label(text)
            label.set_alignment(1,0.5)
            self.gb_combos[text] = gtk.combo_box_new_text()
            for action in GroupButton.action_function_dict.keys():
                self.gb_combos[text].append_text(action)
            self.gb_combos[text].connect('changed', self.cb_changed)
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

        
        label = gtk.Label("Windowbutton actions")
        label.set_alignment(0,0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 6, 5, 6)
        
        # A directory of combobox names and the name of corresponding setting
        self.wb_labels_and_settings = {'Left mouse button': "windowbutton_left_click_action",
                                  'Shift + left mouse button': "windowbutton_shift_and_left_click_action",
                                  'Middle mouse button': "windowbutton_middle_click_action",
                                  'Shift + middle mouse button': "windowbutton_shift_and_middle_click_action",
                                  'Right mouse button': "windowbutton_right_click_action",
                                  'Shift + right mouse button': "windowbutton_shift_and_right_click_action",
                                  'Scroll up': "windowbutton_scroll_up", 
                                  'Scroll down': "windowbutton_scroll_down"}
        # A list to ensure that the order is kept correct
        wb_button_labels = ['Left mouse button',
                            'Shift + left mouse button',
                            'Middle mouse button',
                            'Shift + middle mouse button',
                            'Right mouse button',
                            'Shift + right mouse button',
                            'Scroll up',
                            'Scroll down' ]
        self.wb_combos = {}
        for i in range(len(wb_button_labels)):
            text = wb_button_labels[i]
            label = gtk.Label(text)
            label.set_alignment(1,0.5)
            self.wb_combos[text] = gtk.combo_box_new_text()
            for action in WindowButton.action_function_dict.keys():
                self.wb_combos[text].append_text(action)
            self.wb_combos[text].connect('changed', self.cb_changed)
            # Every second label + combobox on a new row
            row = i // 2 + 6
            # Pack odd numbered comboboxes from 3rd column
            column = (i % 2) * 3
            table.attach(label, column, column + 1, row, row + 1 )
            table.attach(self.wb_combos[text], column + 1, column + 2, row, row + 1 )
            
        behavior_box.pack_start(table, False, padding=5)
        
        # Appearance page
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        label1 = gtk.Label("<big>Needs attention effect</big>")
        label1.set_alignment(0,0.5)
        label1.set_use_markup(True)
        vbox.pack_start(label1,False)
        self.rb1_1 = gtk.RadioButton(None, "Blinking")
        self.rb1_1.connect("toggled", self.rb_toggled, "rb1_blink")
        self.rb1_2 = gtk.RadioButton(self.rb1_1, "Compiz water")
        self.rb1_2.connect("toggled", self.rb_toggled, "rb1_compwater")
        self.rb1_3 = gtk.RadioButton(self.rb1_1, "Red background")
        self.rb1_3.connect("toggled", self.rb_toggled, "rb1_red")
        vbox.pack_start(self.rb1_1, False)
        vbox.pack_start(self.rb1_2, False)
        vbox.pack_start(self.rb1_3, False)
        hbox.pack_start(vbox, True, padding=5)
        
        vbox = gtk.VBox()
        label1 = gtk.Label("<big>Popup Settings</big>")
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
            
        frame.add(table)
        appearance_box.pack_start(frame, False, padding=5)
        
        label = gtk.Label("Behavior")
        notebook.append_page(behavior_box, label)
        label = gtk.Label("Appearance")
        notebook.append_page(appearance_box, label)
        ca.pack_start(notebook)
        self.update()
        
        self.dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.dialog.show_all()
        
        
    def update(self):
        settings_attention = settings["groupbutton_attention_notification_type"]
            
        if settings_attention == 'blink':
            self.rb1_1.set_active(True)
        elif settings_attention == 'compwater':
            self.rb1_2.set_active(True)
        elif settings_attention == 'red':
            self.rb1_3.set_active(True)
            
        settings_workspace = settings["workspace_behavior"]
        
        if settings_workspace == 'ignore':
            self.rb2_1.set_active(True)
        elif settings_workspace == 'switch':
            self.rb2_2.set_active(True)
        elif settings_workspace == 'move':
            self.rb2_3.set_active(True)
            
        settings_align = settings["popup_align"]
        
        if settings_align == 'left':
            self.rb3_1.set_active(True)
        elif settings_align == 'center':
            self.rb3_2.set_active(True)
        elif settings_align == 'right':
            self.rb3_3.set_active(True)
            
        self.delay_spin.set_value(settings['popup_delay'])
        
            
        for cb_name, setting_name in self.gb_labels_and_settings.items():
            value = settings[setting_name]
            combobox = self.gb_combos[cb_name]
            model = combobox.get_model()
            for i in range(len(combobox.get_model())):
                if model[i][0] == value:
                    combobox.set_active(i)
                    break
        
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
            
        for name, setting_base in self.color_labels_and_settings.items():
            color = gtk.gdk.Color(settings[setting_base+'_color'])
            self.color_buttons[name].set_color(color)
            if settings.has_key(setting_base+"_alpha"):
                alpha = settings[setting_base+"_alpha"] * 256
                self.color_buttons[name].set_use_alpha(True)
                self.color_buttons[name].set_alpha(alpha)
                
            
    
    def dialog_close (self,par1,par2):
        global PREFDIALOG
        PREFDIALOG = None
        self.dialog.destroy()
        PrefDialog.__instance = None
        
    def rb_toggled (self,button,par1):
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
            
        if rb1_toggled and value != settings["groupbutton_attention_notification_type"]:
            GCONF_CLIENT.set_string(GCONF_DIR+'/groupbutton_attention_notification_type', value)
            
        if par1 == 'rb2_ignore' and button.get_active(): 
            value = 'ignore'
            rb2_toggled = True
        if par1 == 'rb2_move' and button.get_active(): 
            value = 'move'
            rb2_toggled = True
        if par1 == 'rb2_switch' and button.get_active(): 
            value = 'switch'
            rb2_toggled = True
            
        if rb2_toggled and value != settings["workspace_behavior"]:
            GCONF_CLIENT.set_string(GCONF_DIR+'/workspace_behavior', value)
            
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
        if button.get_active() != settings[name]:
            GCONF_CLIENT.set_bool(GCONF_DIR+'/'+name, button.get_active())


    def cb_changed(self, combobox):
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
                    
    def spin_changed(self, widget, spin):
        if spin == self.delay_spin:
            value = spin.get_value_as_int()
            if value != settings['popup_delay']:
                GCONF_CLIENT.set_int(GCONF_DIR+'/popup_delay', value)
                
    def color_set(self, button, text):
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
            setting_base = self.color_labels_and_settings[text]
            color_string = DEFAULT_SETTINGS[setting_base+"_color"]
            GCONF_CLIENT.set_string(GCONF_DIR+'/'+setting_base+"_color", color_string)
            if DEFAULT_SETTINGS.has_key(setting_base+"_alpha"):
                alpha = DEFAULT_SETTINGS[setting_base+"_alpha"]
                GCONF_CLIENT.set_int(GCONF_DIR+'/'+setting_base+"_alpha", alpha)
            
            



class DockBar():
    def __init__(self,applet):
        global settings
        print "dockbar init"
        self.groups = GroupList()
        self.windows = {}
        self.apps_by_id = {}
        self.launchers = {}
        # self.dragging is used to tell functions wheter 
        # a drag-and-drop is going
        self.dragging = False
        self.right_menu_showing = False
        try:
            for app in gio.app_info_get_all():
                self.apps_by_id[app.get_id()] = app
        except:
            pass
        wnck.set_client_type(wnck.CLIENT_TYPE_PAGER);
        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.screen.force_update()
        
        self.applet = applet
        
        # Gconf settings
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
        GCONF_CLIENT.notify_add(GCONF_DIR, self.gconf_changed, None)
                
        if applet != None:
            applet.set_applet_flags(gnomeapplet.HAS_HANDLE|gnomeapplet.EXPAND_MINOR)
            if applet.get_orient() == gnomeapplet.ORIENT_DOWN or applet.get_orient() == gnomeapplet.ORIENT_UP:
                self.orient = "h"
                self.container = gtk.HBox()
            else:
                self.orient = "v"
                self.container = gtk.VBox()
            applet.connect("change-orient",self.change_orient)
            applet.connect("delete-event",self.cleanup)
            applet.add(self.container)
            ##applet.connect("size-allocate",self.applet_size_alloc)
            self.pp_menu_xml = """
            <popup name="button3">
                <menuitem name="About Item" verb="About" stockid="gtk-about" />
                <menuitem name="Preferences" verb="Pref" stockid="gtk-properties" />
            </popup>
            """
            
            self.pp_menu_verbs = [("About", self.on_ppm_about),("Pref", self.on_ppm_pref)]
            self.applet.setup_menu(self.pp_menu_xml, self.pp_menu_verbs,None)
        else:
            self.container = gtk.HBox()
            self.orient = "h"
        self.container.set_spacing(0)
        self.container.show()
        
        # Get list of launchers
        self.dockbar_folder = self.ensure_dockbar_folder()
        self.launchers_persistentlist = PersistentList(self.dockbar_folder + "/launchers.list")
        self.launchers = self.launchers_persistentlist.read_list()
        
        self.screen.connect("window-opened",self.window_opened)
        self.screen.connect("window-closed",self.window_closed)
        self.screen.connect("active-window-changed", self.active_window_changed)  
        
        # Initiate launcher group buttons
        for (launcher,name) in self.launchers:
            self.make_launcher(launcher, name)
        # Initiate group buttons with windows
        for window in self.screen.get_windows():
            self.window_opened(self.screen, window)

    def gconf_changed(self, client, par2, entry, par4):
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
        for group in self.groups.get_groups():
            group.icon_factory.reset_active_pixbufs()
            
        active_window = self.screen.get_active_window()
        if active_window in self.windows:
            active_group_name = self.windows[active_window]
            active_group = self.groups.get_group(active_group_name)
            if active_group:
                active_group.request_update_state()
    
    def all_windowbuttons_update_state(self):
        for group in self.groups.get_groups():
            for winb in group.windows.values():
                winb.update_state()
                
    def update_all_popup_labels(self):
        for group in self.groups.get_groups():
            group.update_popup_label()
            
    def on_ppm_pref(self,event,data=None):
        PrefDialog()
            
    def on_ppm_about(self,event,data=None):
        AboutDialog()

    def ensure_dockbar_folder(self):
        homeFolder = os.path.expanduser("~")
        dockbar_folder = homeFolder + "/.dockbar"
        if not os.path.exists(dockbar_folder):
            os.mkdir(dockbar_folder)
        if not os.path.isdir(dockbar_folder):
            raise Exception(dockbar_folder + "is not a directory!")
        return dockbar_folder

    def applet_size_alloc(self,applet,allocation):
        pass

    def change_orient(self,arg1,data):
        for group in self.groups.get_names():
            self.container.remove(self.groups.get_group(group).button)
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
        for group in self.groups.get_names():
            self.container.pack_start(self.groups.get_group(group).button,False)
        self.container.set_spacing(2)
        self.container.show_all()
        
    def make_launcher(self, name, path):
        try:
            launcher = Launcher(name, path)
        except:
            print "ERROR: Couldn't read desktop entry for " + name
            print "path: "+ path
        else:
            self.groups.add_group(name, GroupButton(self, launcher = launcher), path)
        
    def make_new_launcher(self, path,calledFrom):
        try:
            launcher = Launcher(None, path)
        except:
            print "ERROR: Couldn't read dropped file. Was it a desktop entry?"
            return False
        name = self.class_name_dialog()
        if not name:
            print 'No name entered, aborting launcher creation'
            return False
        launcher.set_name(name)
        # Remove existing groupbutton for the same program
        winlist = []
        if name == calledFrom: index = self.groups.get_index(calledFrom)
        if name in self.groups.get_names():
            # Get the windows for repopulation of the new button
            winlist = self.groups.get_group(name).windows.keys()
            #Destroy the group button
            self.groups.get_group(name).popup.destroy()
            self.groups.get_group(name).button.destroy()
            self.groups.get_group(name).winlist.destroy()
            self.groups.remove(name)
        # Insert the new button after 
        # (to the right of or under) the calling button
        if name != calledFrom: index = self.groups.get_index(calledFrom) + 1 
        button = GroupButton(self, launcher = launcher, index = index)
        self.groups.add_group(name, button, path, index)
        self.save_launchers_persistentlist()
        for window in winlist:
            self.window_opened(self.screen, window)
        return True
    
    def class_name_dialog(self):  
        #base this on a message dialog  
        dialog = gtk.MessageDialog(  
            None,  
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,  
            gtk.MESSAGE_QUESTION,  
            gtk.BUTTONS_OK_CANCEL,  
            None)  
        dialog.set_title('Group Name')  
        dialog.set_markup('<b>Please enter the resource class name of the program.</b>')
        dialog.format_secondary_markup('You can find out the class name by howering over the icon of an open instance of the program. If the program is already running you can choose it\'s name from the dropdown list.')
        #create the text input field
        #entry = gtk.Entry()
        combobox = gtk.combo_box_entry_new_text()
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
    
    def move_groupbutton(self, name, calledFrom=None, index=None):
        #Remove the groupbutton that should be moved
        move_group = self.groups.get_group(name)
        move_path = self.groups.get_path(name)
        self.container.remove(move_group.button)
        self.groups.remove(name)
        
        # index is not checking buttonposition as of now. 
        # If posible use calledFrom instead
        if index: 
            pass 
        elif calledFrom:
            index = self.groups.get_index(calledFrom) + 1
        else:
            print "Error: cant move button without either a index or the calling button's name"
            return False
        # Insterts the button on it's index by removing 
        # and repacking the buttons that should come after it
        repack_list = self.groups.get_groups()[index:]
        for group in repack_list:
            self.container.remove(group.button)
        self.container.pack_start(move_group.button, False)
        for group in repack_list:
            self.container.pack_start(group.button, False)
        self.groups.add_group(name, move_group, move_path, index)
        self.save_launchers_persistentlist()
                
    def active_window_changed(self, screen, previous_active_window):
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
    

    def window_opened(self,screen,window):
        if not window.is_skip_tasklist() and (window.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
            class_group = window.get_class_group()
            class_group_name = class_group.get_res_class()
            if class_group_name == "":
                class_group_name = class_group.get_name()
            self.windows[window]=class_group_name
            if not class_group_name in self.groups.get_names():
                self.groups.add_group(class_group_name, GroupButton(self,class_group))
                self.groups.get_group(class_group_name).add_window(window)
            else:
                self.groups[class_group_name].add_window(window)
        
    def window_closed(self,screen,window):
        if window in self.windows:
            class_group_name = self.windows[window]
            #Don't call if groupbutton already has been removed elsewhere
            if self.groups.get_group(class_group_name): 
                self.groups.get_group(class_group_name).del_window(window)
            del self.windows[window]
            
    def save_launchers_persistentlist(self):
        list = self.groups.get_launchers_list()
        #print list
        self.launchers_persistentlist.write_list(list)
        
    def cleanup(self,event):
        del self.applet
            
        
    def debug_list(self):
        print "debug_list"
        for grp in self.groups.get_names():
            print self.groups.get_group(grp).name
            for win in self.groups.get_group(grp).windows:
                print "  ",self.groups.get_group(grp).windows[win].name
                
class DockBarWindow():
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(200,40)
        self.window.show()
        self.window.set_property("skip-taskbar-hint",True)
        self.window.set_keep_above(True)
        self.window.connect ("delete_event",self.delete_event)
        self.window.connect ("destroy",self.destroy)
        
        self.dockbar = DockBar(None)
        #self.dockbar.debug_list()
        hbox = gtk.HBox()
        button = gtk.Button('Pref')
        button.connect('clicked', self.dockbar.on_ppm_pref)
        hbox.pack_start(button, False)
        hbox.pack_start(self.dockbar.container, False)
        self.window.add(hbox)
        hbox.show_all()
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
    
#gc.enable()

if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":
    dockbarwin = DockBarWindow()
    dockbarwin.main()
else:
    gnomeapplet.bonobo_factory("OAFIID:GNOME_DockBarXApplet_Factory", 
                                     gnomeapplet.Applet.__gtype__, 
                                     "dockbar applet", "0", dockbar_factory)
