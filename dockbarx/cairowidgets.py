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
pygtk.require("2.0")
import gtk
import cairo
from math import pi
from common import Globals
from xml.sax.saxutils import escape
import gobject
import pango

from common import connect, disconnect
from log import logger

class CairoAppButton(gtk.EventBox):
    __gsignals__ = {"expose-event" : "override",
                    "size_allocate": "override"}
    def __init__(self, surface=None, in_dock=False):
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.area = gtk.Alignment(0, 0, 1, 1)
        self.add(self.area)
        self.area.show()
        self.globals = Globals()
        self.surface = surface
        self.in_dock = in_dock
        self.badge = None
        self.badge_text = None
        self.progress_bar = None
        self.progress = None
        self.bl_sid = self.globals.connect("badge-look-changed",
                                           self.__on_badge_look_changed)
        self.pbl_sid = self.globals.connect("progress-bar-look-changed",
                                        self.__on_progress_bar_look_changed)

    def update(self, surface=None):
        a = self.area.get_allocation()
        if surface is not None:
            self.surface = surface
        if self.window is None:
            return
        if self.in_dock:
            self.area.window.clear_area_e(a.x, a.y, a.width, a.height)
        else:
            self.area.window.clear_area(a.x, a.y, a.width, a.height)
        ctx = self.area.window.cairo_create()
        ctx.rectangle(a.x, a.y, a.width, a.height)
        ctx.clip()
        ctx.set_source_surface(self.surface, a.x, a.y)
        ctx.paint()
        for surface in (self.badge, self.progress_bar):
            if surface is not None:
                ctx.rectangle(a.x, a.y, a.width, a.height)
                ctx.clip()
                ctx.set_source_surface(surface, a.x, a.y)
                ctx.paint()
        child = self.area.get_child()
        if child:
            child.queue_draw()

    def do_expose_event(self, event):
        if self.surface is not None:
            ctx = self.area.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
            ctx.clip()
            a = self.get_allocation()
            ctx.set_source_surface(self.surface, a.x, a.y)
            ctx.paint()
            for surface in (self.badge, self.progress_bar):
                if surface is not None:
                    ctx.rectangle(event.area.x, event.area.y,
                                  event.area.width, event.area.height)
                    ctx.clip()
                    ctx.set_source_surface(surface, a.x, a.y)
                    ctx.paint()
            self.propagate_expose(self.area, event)

    def do_size_allocate(self, allocation):
        gtk.EventBox.do_size_allocate(self, allocation)
        if self.badge:
            self.make_badge(self.badge_text)
        if self.progress_bar:
            self.make_progress_bar(self.progress)

    def make_badge(self, text):
        if not text:
            self.badge_text = None
            self.badge = None
            return
        self.badge_text = text
        a = self.area.get_allocation()
        self.badge = cairo.ImageSurface(cairo.FORMAT_ARGB32, a.width, a.height)
        ctx = gtk.gdk.CairoContext(cairo.Context(self.badge))
        layout = ctx.create_layout()
        if self.globals.settings["badge_use_custom_font"]:
            font = self.globals.settings["badge_font"]
            font_base, font_size = font.rsplit(" ", 1)
            font_size = int(font_size)
        else:
            font_size = max(int(round(0.2 * a.height)), 6)
            font_base = "sans bold"
            font = "%s %s" % (font_base, font_size)
        layout.set_font_description(pango.FontDescription(font))
        layout.set_text(text)
        te = layout.get_pixel_extents()
        w = te[1][2]
        h = te[0][1] + te[0][3]
        size = min(a.width, a.height)
        p = 2
        d = int(round(0.05 * size))
        # Make sure the badge isn't too wide.
        while w + 2 * p + d >= a.width and font_size > 4:
            font_size = max(4, font_size - max(2, int(font_size * 0.2)))
            font = "%s %s" % (font_base, font_size)
            layout.set_font_description(pango.FontDescription(font))
            te = layout.get_pixel_extents()
            w = te[1][2]
            h = te[0][1] + te[0][3]
        x = a.width - w - p - d
        y = a.height - h - p - d
        make_path(ctx, x - p, y + te[0][1] - (p + 1), 
                  w + 2 * p, h - te[0][1] + 2 * (p + 1), r=4)
        if self.globals.settings["badge_custom_bg_color"]:
            color = self.globals.settings["badge_bg_color"]
            alpha = float(self.globals.settings["badge_bg_alpha"]) / 255
        else:
            color = "#CDCDCD"
            alpha = 1.0
        r = int(color[1:3], 16)/255.0
        g = int(color[3:5], 16)/255.0
        b = int(color[5:7], 16)/255.0
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.fill_preserve()
        if self.globals.settings["badge_custom_fg_color"]:
            color = self.globals.settings["badge_fg_color"]
            alpha = float(self.globals.settings["badge_fg_alpha"]) / 255
        else:
            color = "#020202"
            alpha = 1.0
        r = int(color[1:3], 16)/255.0
        g = int(color[3:5], 16)/255.0
        b = int(color[5:7], 16)/255.0
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.set_line_width(0.8)
        ctx.stroke() 
        ctx.move_to(x,y)
        ctx.show_layout(layout)

    def make_progress_bar(self, progress):
        if progress is None:
            self.progress = None
            self.progress_bar = None
            return
        self.progress = progress
        a = self.area.get_allocation()
        x = max(0.1 * a.width, 2)
        y = max(0.15 * a.height, 3)
        w = min(max (0.60 * a.width, 20), a.width - 2 * x)
        h = max(0.10 * a.height, 3.0)
        ro = h / 2
        self.progress_bar = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                               a.width, a.height)
        ctx = cairo.Context(self.progress_bar)
        ctx.move_to(x,y)
        ctx.line_to(x + w * progress, y)
        ctx.line_to(x + w * progress, y + h)
        ctx.line_to(x, y + h)
        ctx.close_path()
        ctx.clip()
        if self.globals.settings["progress_custom_fg_color"]:
            color = self.globals.settings["progress_fg_color"]
            alpha = float(self.globals.settings["progress_fg_alpha"]) / 255
        else:
            color = "#772953"
            alpha = 1.0
        r = int(color[1:3], 16)/255.0
        g = int(color[3:5], 16)/255.0
        b = int(color[5:7], 16)/255.0
        ctx.set_source_rgba(r, g, b, alpha)
        make_path(ctx, x, y, w, h, r=ro, b=0)
        ctx.fill()
        ctx.reset_clip()
        ctx.move_to(x + w * progress,y)
        ctx.line_to(x + w, y)
        ctx.line_to(x + w, y + h)
        ctx.line_to(x + w * progress, y + h)
        ctx.clip()
        make_path(ctx, x, y, w, h, r=ro, b=0)
        if self.globals.settings["progress_custom_bg_color"]:
            color = self.globals.settings["progress_bg_color"]
            bg_alpha = float(self.globals.settings["progress_bg_alpha"]) / 255
            print bg_alpha
        else:
            color = "#CDCDCD"
            bg_alpha = 0.25
        br = int(color[1:3], 16)/255.0
        bg = int(color[3:5], 16)/255.0
        bb = int(color[5:7], 16)/255.0
        ctx.set_source_rgba(br, bg, bb, bg_alpha)
        ctx.fill_preserve()
        ctx.reset_clip()
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.set_line_width(0.8)
        ctx.stroke_preserve()
        
        
    def __on_badge_look_changed(self, *args):
        if self.badge:
            self.make_badge(self.badge_text)
            self.update()
        
    def __on_progress_bar_look_changed(self, *args):
        if self.progress_bar:
            self.make_progress_bar(self.progress)
            self.update()

    def destroy(self, *args, **kwargs):
        if self.bl_sid:
            self.globals.disconnect(self.bl_sid)
            self.bl_sid = None
        if self.pbl_sid:
            self.globals.disconnect(self.pbl_sid)
            self.pbl_sid = None
        if self.surface:
            self.surface = None
        gtk.EventBox.destroy(self, *args, **kwargs)

    def pointer_is_inside(self):
        b_m_x,b_m_y = self.get_pointer()
        b_r = self.get_allocation()

        if b_m_x >= 0 and b_m_x < b_r.width and \
           b_m_y >= 0 and b_m_y < b_r.height:
            return True
        else:
            return False

class CairoSmallButton(gtk.Button):
    __gsignals__ = {"expose-event": "override",
                    "enter-notify-event": "override",
                    "leave-notify-event": "override",
                    "button-press-event": "override",
                    "button-release-event": "override",}
    def __init__(self, size):
        gtk.Button.__init__(self)
        self.set_size_request(size, size)
        self.mousedown = False
        self.mouseover = False

    def do_enter_notify_event(self, *args):
        self.mouseover = True
        gtk.Button.do_enter_notify_event(self, *args)

    def do_leave_notify_event(self, *args):
        self.mouseover = False
        gtk.Button.do_leave_notify_event(self, *args)

    def do_button_press_event(self, *args):
        self.mousedown = True
        gtk.Button.do_button_press_event(self, *args)

    def do_button_release_event(self, *args):
        self.mousedown = False
        gtk.Button.do_button_release_event(self, *args)

    def do_expose_event(self, event, arg=None):
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_button(ctx, a.x, a.y, a.width, a.height)

    def draw_button(self, x, y, width, height): abstract

class CairoCloseButton(CairoSmallButton):
    def __init__(self):
        CairoSmallButton.__init__(self, 14)

    def draw_button(self, ctx, x, y, w, h):
        if self.mouseover:
            alpha = 1
        else:
            alpha = 0.5
        button_source = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                       w, h)
        bctx = cairo.Context(button_source)
        make_path(bctx, 0, 0, w, h, 5)
        bctx.set_source_rgba(1, 0, 0, alpha)
        bctx.fill()
        bctx.scale(w, h)
        bctx.move_to(0.3, 0.3)
        bctx.line_to(0.7, 0.7)
        bctx.move_to(0.3, 0.7)
        bctx.line_to(0.7, 0.3)
        bctx.set_line_width(2.0/w)
        if self.mousedown and self.mouseover:
            bctx.set_source_rgba(1, 1, 1, 1)
        else:
            bctx.set_source_rgba(1, 1, 1, 0)
        bctx.set_operator(cairo.OPERATOR_SOURCE)
        bctx.stroke()

        ctx.set_source_surface(button_source, x, y)
        ctx.paint()

class CairoPlayPauseButton(CairoSmallButton):
    def __init__(self):
        self.pause = False
        CairoSmallButton.__init__(self, 26)

    def set_pause(self, pause):
        self.pause = pause
        self.queue_draw()

    def draw_button(self, ctx, x, y, w, h):
        if self.mouseover:
            alpha = 1
        else:
            alpha = 0.5
        button_source = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                       w, h)
        bctx = cairo.Context(button_source)
        if self.mousedown and self.mouseover:
            bctx.set_source_rgba(1, 0.4, 0.2, alpha)
        else:
            bctx.set_source_rgba(1, 1, 1, alpha)
        bctx.scale(w, h)
        bctx.set_operator(cairo.OPERATOR_SOURCE)
        if not self.pause:
            bctx.move_to(0.2, 0.0)
            bctx.line_to(1.0, 0.5)
            bctx.line_to(0.2, 1.0)
            bctx.close_path()
        else:
            bctx.move_to(0.2, 0.1)
            bctx.line_to(0.45, 0.1)
            bctx.line_to(0.45, 0.9)
            bctx.line_to(0.2, 0.9)
            bctx.close_path()
            bctx.move_to(0.55, 0.1)
            bctx.line_to(0.8, 0.1)
            bctx.line_to(0.8, 0.9)
            bctx.line_to(0.55, 0.9)
            bctx.close_path()
        bctx.fill_preserve()
        bctx.set_line_width(2.0/w)
        bctx.set_source_rgba(1, 1, 1, 0)
        bctx.stroke()

        ctx.set_source_surface(button_source, x, y)
        ctx.paint()

class CairoNextButton(CairoSmallButton):
    def __init__(self, previous=False):
        self.previous = previous
        CairoSmallButton.__init__(self, 26)

    def draw_button(self, ctx, x, y, w, h):
        if self.mouseover:
            alpha = 1
        else:
            alpha = 0.5
        button_source = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                       w, h)
        bctx = cairo.Context(button_source)
        bctx.scale(w, h)

        for p in [0.4, 0.0]:
            if self.previous:
                bctx.move_to(1.0-p, 0.0)
                bctx.line_to(0.4-p, 0.5)
                bctx.line_to(1.0-p, 1.0)
            else:
                bctx.move_to(0.0+p, 0.0)
                bctx.line_to(0.6+p, 0.5)
                bctx.line_to(0.0+p, 1.0)
            bctx.close_path()
            bctx.set_operator(cairo.OPERATOR_SOURCE)
            if self.mousedown and self.mouseover:
                bctx.set_source_rgba(1, 0.4, 0.2, alpha)
            else:
                bctx.set_source_rgba(1, 1, 1, alpha)
            bctx.fill_preserve()
            bctx.set_line_width(2.0/w)
            bctx.set_source_rgba(1, 1, 1, 0)
            bctx.stroke()

        ctx.set_source_surface(button_source, x, y)
        ctx.paint()


class CairoPopup(gtk.Window):
    """CairoPopup is a transparent popup window with rounded corners"""
    __gsignals__ = {"expose-event": "override",
                    "enter-notify-event": "override",
                    "leave-notify-event": "override"}
    def __init__(self, arrow_size=9, orient="h"):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        gtk_screen = gtk.gdk.screen_get_default()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap is None:
            colormap = gtk_screen.get_rgb_colormap()
        self.set_colormap(colormap)
        self.set_app_paintable(1)
        self.globals = Globals()
        self._pointer_is_inside = False

        self.alignment = gtk.Alignment(0, 0, 0, 0)
        gtk.Window.add(self, self.alignment)
        self.alignment.show()
        self.pointer = ""
        self.arrow_size = arrow_size
        if orient == "h":
            # The direction of the pointer isn't important here we only need
            # the right amount of padding so that the popup has right width and
            # height for placement calculations.
            self.point("down")
        else:
            self.point("left")

    def add(self, child):
        self.alignment.add(child)

    def remove(self, child):
        self.alignment.remove(child)

    def point(self, new_pointer, ap=0):
        self.ap = ap
        p = 7
        a = self.arrow_size
        if new_pointer != self.pointer:
            self.pointer = new_pointer
            padding = {"up":(p+a, p, p, p),
                       "down":(p, p+a, p, p),
                       "left":(p, p, p+a, p),
                       "right":(p, p, p, p+a)}[self.pointer]
            self.alignment.set_padding(*padding)

    def do_expose_event(self, event):
        self.set_shape_mask()
        w,h = self.get_size()
        self.ctx = self.window.cairo_create()
        # set a clip region for the expose event, XShape stuff
        self.ctx.save()
        if self.is_composited():
            self.ctx.set_source_rgba(1, 1, 1,0)
        else:
            self.ctx.set_source_rgb(0.8, 0.8, 0.8)
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.ctx.paint()
        self.ctx.restore()
        self.ctx.rectangle(event.area.x, event.area.y,
                           event.area.width, event.area.height)
        self.ctx.clip()
        self.draw_frame(self.ctx, w, h)
        gtk.Window.do_expose_event(self, event)

    def set_shape_mask(self):
        # Set window shape from alpha mask of background image
        w,h = self.get_size()
        if w==0: w = 800
        if h==0: h = 600
        pixmap = gtk.gdk.Pixmap (None, w, h, 1)
        ctx = pixmap.cairo_create()
        ctx.set_source_rgba(0, 0, 0,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()
        if self.is_composited():
            make_path(ctx, 0, 0, w, h, 6, 0,
                      self.arrow_size, self.pointer, self.ap)
            ctx.set_source_rgba(1, 1, 1, 1)
        else:
            make_path(ctx, 0, 0, w, h, 6, 1,
                      self.arrow_size, self.pointer, self.ap)
            ctx.set_source_rgb(0, 0, 0)
        ctx.fill()
        self.shape_combine_mask(pixmap, 0, 0)
        del pixmap

    def draw_frame(self, ctx, w, h):
        color = self.globals.colors["color1"]
        red = float(int(color[1:3], 16))/255
        green = float(int(color[3:5], 16))/255
        blue = float(int(color[5:7], 16))/255
        alpha= float(self.globals.colors["color1_alpha"]) / 255
        make_path(ctx, 0, 0, w, h, 6, 2.5,
                  self.arrow_size, self.pointer, self.ap)
        if self.is_composited():
            ctx.set_source_rgba(red, green, blue, alpha)
        else:
            ctx.set_source_rgb(red, green, blue)
        ctx.fill_preserve()
        if self.is_composited():
            ctx.set_source_rgba(0.0, 0.0, 0.0, 0.8)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(3)
        ctx.stroke_preserve()
        if self.is_composited():
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        else:
            ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.set_line_width(2)
        ctx.stroke()

    def pointer_is_inside(self):
        ax, ay, width, height = self.alignment.get_allocation()
        top, bottom, left, right = self.alignment.get_padding()
        x, y = self.get_pointer()
        if x >= left and x < width - right and \
           y >= top and y <= height - bottom:
            return True
        else:
            return self._pointer_is_inside

    def do_enter_notify_event(self, *args):
        self._pointer_is_inside = True
        gtk.Window.do_enter_notify_event(self, *args)

    def do_leave_notify_event(self, *args):
        self._pointer_is_inside = False
        gtk.Window.do_leave_notify_event(self, *args)

class CairoButton(gtk.EventBox):
    __gsignals__ = {"clicked": (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,(gtk.gdk.Event, )),
                    "enter-notify-event": "override",
                    "leave-notify-event": "override",
                    "button-release-event": "override",
                    "button-press-event": "override"}

    def __init__(self, label=None, border_width=5, roundness=5):
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.set_above_child(False)
        self.area = CairoArea(label, border_width, roundness)
        self.label = self.area.label
        gtk.EventBox.add(self, self.area)
        self.area.show()
        self.mousedown = False
        self.prevent_click = False

    def do_leave_notify_event(self, *args):
        if self.mousedown:
            self.area.set_pressed_down(False)
        self.area.queue_draw()

    def do_enter_notify_event(self, *args):
        if self.mousedown:
            self.area.set_pressed_down(True)
        self.area.queue_draw()

    def add(self, child):
        self.area.add(child)

    def remove(self, child):
        self.area.remove(child)

    def get_child(self):
        return self.area.get_child()

    def set_label(self, text, color=None):
        self.area.set_label(text, color)

    def set_label_color(self, color):
        self.area.set_label_color(color)

    def get_label(self):
        return self.area.text

    def redraw(self):
        self.area.queue_draw()

    def do_button_release_event(self, event):
        if self.area.pointer_is_inside() and not self.prevent_click:
            self.emit("clicked", event)
        self.area.set_pressed_down(False)
        self.mousedown=False
        self.prevent_click = False

    def do_button_press_event(self, event):
        if self.area.pointer_is_inside() and not self.prevent_click:
            self.mousedown = True
            self.area.set_pressed_down(True)

    def disable_click(self, *args):
        # A "hack" to avoid CairoButton from reacting to clicks on
        # buttons inside the CairoButton. (The button on top should
        # have it's press-button-event connected to this function.)
        self.area.set_pressed_down(False)
        self.mousedown = False
        self.prevent_click = True

    def pointer_is_inside(self):
        return self.area.pointer_is_inside()

class CairoArea(gtk.Alignment):
    __gsignals__ = {"expose-event" : "override"}
    def __init__(self, text=None, border_width=5, roundness=5):
        self.r = roundness
        self.b = border_width
        self.text = text
        gtk.Alignment.__init__(self, 0, 0, 1, 1)
        self.set_padding(self.b, self.b, self.b, self.b)
        self.set_app_paintable(1)
        self.globals = Globals()
        self.highlighted = False
        self.pressed_down = False
        if text:
            self.label = gtk.Label()
            self.add(self.label)
            self.label.show()
            color = self.globals.colors["color2"]
            self.set_label(text, color)
        else:
            self.label = None

    def set_label(self, text, color=None):
        self.text = text
        if color:
            text = "<span foreground=\"" + color + "\">" + escape(text) + \
                   "</span>"
        self.label.set_text(text)
        self.label.set_use_markup(True)
        self.label.set_use_underline(True)

    def set_padding(self, top, bottom, left, right):
        self.pressed_down = False
        gtk.Alignment.set_padding(self, top, bottom, left, right)

    def set_label_color(self, color):
        label = "<span foreground=\"" + color + "\">" + escape(self.text) + \
                "</span>"
        self.label.set_text(label)
        self.label.set_use_markup(True)
        self.label.set_use_underline(True)

    def do_expose_event(self, event, arg=None):
        a = self.get_allocation()
        mx , my = self.get_pointer()
        if (mx >= 0 and mx < a.width and my >= 0 and my < a.height) or \
            self.highlighted:
            ctx = self.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
            ctx.clip()
            self.draw_frame(ctx, a.x, a.y, a.width, a.height, self.r)
        self.propagate_expose(self.get_child(), event)
        return

    def draw_frame(self, ctx, x, y, w, h, roundness=6, border_color="#FFFFFF"):
        if self.is_composited():
            r, g, b = parse_color(self.globals.colors["color1"])
            alpha = parse_alpha(self.globals.colors["color1_alpha"])
        else:
            r = g = b = 0.0
            alpha = 0.25
        make_path(ctx, x, y, w, h, roundness)


        ctx.set_source_rgba(r, g, b, alpha)
        ctx.fill_preserve()

        r, g, b = parse_color(border_color)
        ctx.set_source_rgba(r, g, b, 0.8)
        ctx.set_line_width(1)
        ctx.stroke()

    def set_pressed_down(self, pressed):
        p = self.get_padding()
        if pressed and not self.pressed_down:
            gtk.Alignment.set_padding(self, p[0] + 1, p[1] - 1, p[2], p[3])
        elif self.pressed_down and not pressed:
            gtk.Alignment.set_padding(self, p[0] - 1, p[1] + 1, p[2], p[3])
        self.pressed_down = pressed

    def set_highlighted(self, highlighted):
        self.highlighted = highlighted
        self.queue_draw()

    def pointer_is_inside(self):
        mx,my = self.get_pointer()
        a = self.get_allocation()

        if mx >= 0 and mx < a.width \
        and my >= 0 and my < a.height:
            # Mouse pointer is inside the "rectangle"
            # but check if it's still outside the rounded corners
            x = None
            y = None
            r = self.r
            if mx < r:
                x = r - mx
            if (a.width - mx) < r:
                x = mx - (a.width - r)
            if my < r:
                y = r - my
            if (a.height - my) < r:
                y = my - (a.height - r)
            if x is None or y is None \
            or (x**2 + y**2) < (r-1)**2:
                return True
        else:
            return False


class CairoMenuItem(CairoButton):
    def __init__(self, label):
        CairoButton.__init__(self, label)
        self.area.set_padding(3, 3, 5, 5)
        

class CairoCheckMenuItem(CairoMenuItem):
    def __init__(self, label, toggle_type="checkmark"):
        self.globals = Globals()
        CairoMenuItem.__init__(self, None)
        self.indicator = gtk.CheckMenuItem()
        self.indicator.set_draw_as_radio(toggle_type == "radio")
        #~ if toggle_type == "radio":
            #~ self.indicator = gtk.RadioButton()
        #~ else:
            #~ self.indicator = gtk.CheckButton()
        self.area.label = gtk.Label()
        hbox = gtk.HBox()
        hbox.pack_start(self.indicator, False, padding=2)
        hbox.pack_start(self.area.label, False, padding=2)
        alignment = gtk.Alignment(0.5,0.5,0,0)
        alignment.add(hbox)
        alignment.show_all()
        self.area.add(alignment)
        color = self.globals.colors["color2"]
        self.set_label(label, color)
        
    def set_active(self, active):
        self.indicator.set_active(active)
        
    def get_active(self):
        return self.indicator.get_active()
        
    def set_inconsistent(self, inconsistent):
        self.indicator.set_inconsistent(inconsistent)
        
    def get_inconsistent(self):
        return self.indicator.set_inconsistent()
        

class CairoToggleMenu(gtk.VBox):
    __gsignals__ = {"toggled": (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,(bool, ))}

    def __init__(self, label=None, show_menu=False):
        gtk.VBox.__init__(self)
        self.globals = Globals()

        self.set_spacing(0)
        self.set_border_width(0)
        self.toggle_button = CairoMenuItem(label)
        if label:
            if show_menu:
                color = self.globals.colors["color4"]
            else:
                color = self.globals.colors["color2"]
            self.toggle_button.set_label(label, color)
        self.pack_start(self.toggle_button)
        self.toggle_button.show()
        self.toggle_button.connect("clicked", self.toggle)
        self.menu = CairoVBox()
        self.menu.set_no_show_all(True)
        self.pack_start(self.menu)
        self.menu.set_border_width(10)
        self.show_menu = show_menu
        if show_menu:
            self.menu.show()

    def add_item(self, item):
        self.menu.pack_start(item)

    def remove_item(self, item):
        self.menu.remove(item)

    def get_items(self):
        return self.menu.get_children()

    def toggle(self, *args):
        if self.show_menu:
            self.menu.hide()
            color = self.globals.colors["color2"]
        else:
            self.menu.show()
            color = self.globals.colors["color4"]
        if self.toggle_button.label:
            self.toggle_button.set_label_color(color)
        self.show_menu = not self.show_menu
        self.emit("toggled", self.show_menu)
        
    def get_toggled(self):
        return self.show_menu


class CairoVBox(gtk.VBox):
    __gsignals__ = {"expose-event" : "override"}

    def __init__(self, label=None, show_menu=False):
        gtk.VBox.__init__(self)
        self.globals = Globals()

    def do_expose_event(self, event, arg=None):
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_frame(ctx, a.x, a.y, a.width, a.height, 6)
        for child in self.get_children():
            self.propagate_expose(child, event)

    def draw_frame(self, ctx, x, y, w, h, roundness=6, color="#000000"):
        r, g, b = parse_color(color)

        make_path(ctx, x, y, w, h, roundness)
        ctx.set_source_rgba(r, g, b, 0.20)
        ctx.fill_preserve()

        ctx.set_source_rgba(r, g, b, 0.20)
        ctx.set_line_width(1)
        ctx.stroke()


def make_path(ctx, x=0, y=0, w=0, h=0, r=6, b=0.5,
              arrow_size=0, arrow_direction=None, arrow_position=0):
    a = arrow_size
    ap = arrow_position
    lt = x + b
    rt = x + w - b
    up = y + b
    dn = y + h - b

    if arrow_direction == "up":
        up += a
    if arrow_direction == "down":
        dn -= a
    if arrow_direction == "left":
        lt += a
    if arrow_direction == "right":
        rt -= a
    ctx.move_to(lt, up + r)
    ctx.arc(lt + r, up + r, r, -pi, -pi/2)
    if arrow_direction == "up":
        ctx.line_to (ap-a, up)
        ctx.line_to(ap, up-a)
        ctx.line_to(ap+a, up)
    ctx.arc(rt - r, up + r, r, -pi/2, 0)
    if arrow_direction == "right":
        ctx.line_to (rt, ap-a)
        ctx.line_to(rt+a, ap)
        ctx.line_to(rt, ap+a)
    ctx.arc(rt - r, dn - r, r, 0, pi/2)
    if arrow_direction == "down":
        ctx.line_to (ap+a, dn)
        ctx.line_to(ap, dn+a)
        ctx.line_to(ap-a, dn)
    ctx.arc(lt + r, dn - r, r, pi/2, pi)
    if arrow_direction == "left":
        ctx.line_to (lt, ap+a)
        ctx.line_to(lt-a, ap)
        ctx.line_to(lt, ap-a)
    ctx.close_path()

def parse_color(color):
    r = float(int(color[1:3], 16))/255
    g = float(int(color[3:5], 16))/255
    b = float(int(color[5:7], 16))/255
    return r, g, b

def parse_alpha(alpha):
    return float(alpha)/255

