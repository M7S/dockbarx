#!/usr/bin/python

#   cairowidgets.py
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
import cairo
from math import pi
from common import Globals

class CairoButton(gtk.Button):
    """CairoButton is a gtk button with a cairo surface painted over it."""
    __gsignals__ = {'expose-event' : 'override',}
    def __init__(self, surface=None):
        gtk.Button.__init__(self)
        self.globals = Globals()
        self.surface = surface
        self.connect('delete-event', self.cleanup)

    def update(self, surface):
        a = self.get_allocation()
        self.surface = surface
        if self.window is None:
            # TODO: Find out why is window is None sometimes?
            return
        self.window.clear_area(a.x, a.y, a.width, a.height)
        ctx = self.window.cairo_create()
        ctx.rectangle(a.x, a.y, a.width, a.height)
        ctx.clip()
        ctx.set_source_surface(self.surface, a.x, a.y)
        ctx.paint()

    def do_expose_event(self, event):
        if self.surface is not None:
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

    def pointer_is_inside(self):
        b_m_x,b_m_y = self.get_pointer()
        b_r = self.get_allocation()

        if b_m_x >= 0 and b_m_x < b_r.width and \
           b_m_y >= 0 and b_m_y < b_r.height:
            return True
        else:
            return False

class CairoPopup(gtk.Window):
    """CairoPopup is a transparent popup window with rounded corners"""
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        gtk_screen = gtk.gdk.screen_get_default()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap is None:
            colormap = gtk_screen.get_rgb_colormap()
        self.set_colormap(colormap)
        self.set_app_paintable(1)
        self.connect("expose_event", self.expose)
        self.globals = Globals()


    def expose(self, widget, event):
        self.set_shape_mask()
        w,h = self.get_size()
        self.ctx = self.window.cairo_create()
        # set a clip region for the expose event, XShape stuff
        self.ctx.save()
        if self.is_composited():
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
        w,h = self.get_size()
        if w==0: w = 800
        if h==0: h = 600
        pixmap = gtk.gdk.Pixmap (None, w, h, 1)
        ctx = pixmap.cairo_create()
        ctx.set_source_rgba(1, 1, 1,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()

        r = 6
        lt = 0
        rt = w
        up = 0
        dn = h
        ctx.move_to(lt, up + r)
        ctx.arc(lt + r, up + r, r, -pi, -pi/2)
        ctx.arc(rt - r, up + r, r, -pi/2, 0)
        ctx.arc(rt - r, dn - r, r, 0, pi/2)
        ctx.arc(lt + r, dn - r, r, pi/2, pi)
        ctx.close_path()

        if self.is_composited():
            ctx.set_source_rgba(1, 1, 1, 1)
        else:
            # A grey color makes the "semi transparent"
            # rounded corners look most transparent
            ctx.set_source_rgb(0.5, 0.5, 0.5)
        ctx.fill()

        if self.is_composited():
            self.window.shape_combine_mask(None, 0, 0)
            ctx.rectangle(0,0,w,h)
            ctx.fill()
            self.input_shape_combine_mask(pixmap,0,0)
        else:
            self.shape_combine_mask(pixmap, 0, 0)
        del pixmap

    def draw_frame(self, ctx, w, h):
        r = 6
        color = self.globals.colors['color1']
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255

        alpha= float(self.globals.colors['color1_alpha']) / 255

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

        if self.is_composited():
            ctx.set_source_rgba(red, green, blue, alpha)
        else:
            ctx.set_source_rgb(red, green, blue)
        ctx.fill_preserve()
        if self.is_composited():
            ctx.set_source_rgba(0.0, 0.0, 0.0, alpha)
        else:
            ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.set_line_width(1)
        ctx.stroke()

    def pointer_is_inside(self):
        p_m_x, p_m_y = self.get_pointer()
        p_w, p_h = self.get_size()
        r = 6 #radius for the rounded corner of popup window

        if p_m_x >= 0 and p_m_x < p_w \
        and p_m_y >= 0 and p_m_y < p_h:
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
            if x is None or y is None \
            or (x**2 + y**2) < (r-1)**2:
                return True
        else:
            return False

class CairoWindowButton(gtk.Button):
    """CairoButton is a gtk button with a cairo surface painted over it."""
    __gsignals__ = {'expose-event' : 'override',}
    def __init__(self):
        gtk.Button.__init__(self)
        self.globals = Globals()

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
        color = self.globals.colors['color1']
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255

        alpha= float(self.globals.colors['color1_alpha']) / 255
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

