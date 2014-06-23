#!/usr/bin/python2

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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
import cairo
from math import pi, tan
from xml.sax.saxutils import escape
from gi.repository import GObject
from gi.repository import Pango

from common import Globals, connect, disconnect
from theme import PopupStyle
from log import logger



class CairoAppButton(Gtk.EventBox):
    __gsignals__ = {"draw" : "override",
                    "size_allocate": "override"}
    def __init__(self, surface=None, expose_on_clear=False):
        GObject.GObject.__init__(self)
        self.set_visible_window(False)
        self.area = Gtk.Alignment.new(0, 0, 1, 1)
        self.add(self.area)
        self.area.show()
        self.globals = Globals()
        self.surface = surface
        self.expose_on_clear = expose_on_clear
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
        if self.expose_on_clear:
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

    def do_draw(self, event):
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
        Gtk.EventBox.do_size_allocate(self, allocation)
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
        ctx = Gdk.CairoContext(cairo.Context(self.badge))
        layout = ctx.create_layout()
        if self.globals.settings["badge_use_custom_font"]:
            font = self.globals.settings["badge_font"]
            font_base, font_size = font.rsplit(" ", 1)
            font_size = int(font_size)
        else:
            font_size = max(int(round(0.2 * a.height)), 6)
            font_base = "sans bold"
            font = "%s %s" % (font_base, font_size)
        layout.set_font_description(Pango.FontDescription(font))
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
            layout.set_font_description(Pango.FontDescription(font))
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
        Gtk.EventBox.destroy(self, *args, **kwargs)

    def pointer_is_inside(self):
        b_m_x,b_m_y = self.get_pointer()
        b_r = self.get_allocation()

        if b_m_x >= 0 and b_m_x < b_r.width and \
           b_m_y >= 0 and b_m_y < b_r.height:
            return True
        else:
            return False

class CairoSmallButton(Gtk.Button):
    __gsignals__ = {"draw": "override",
                    "enter-notify-event": "override",
                    "leave-notify-event": "override",
                    "button-press-event": "override",
                    "button-release-event": "override",}
    def __init__(self, width, height=None):
        GObject.GObject.__init__(self)
        if height is None:
            height = width
        self.set_size_request(width, height)
        self.mousedown = False
        self.mouseover = False

    def do_enter_notify_event(self, *args):
        self.mouseover = True
        Gtk.Button.do_enter_notify_event(self, *args)

    def do_leave_notify_event(self, *args):
        self.mouseover = False
        Gtk.Button.do_leave_notify_event(self, *args)

    def do_button_press_event(self, *args):
        self.mousedown = True
        Gtk.Button.do_button_press_event(self, *args)

    def do_button_release_event(self, *args):
        self.mousedown = False
        Gtk.Button.do_button_release_event(self, *args)

    def do_draw(self, event, arg=None):
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_button(ctx, a.x, a.y, a.width, a.height)

    def draw_button(self, x, y, width, height): abstract

class CairoCloseButton(CairoSmallButton):
    def __init__(self):
        self.popup_style = PopupStyle()
        self.size = int(self.popup_style.get("close_button_size", 14))
        CairoSmallButton.__init__(self, self.size)
        self.popup_reloaded_sid = self.popup_style.connect(
                                                "popup-style-reloaded",
                                                self.__on_popup_style_reloaded)

    def draw_button(self, ctx, x, y, w, h):
        button_source = None
        if self.mousedown and self.mouseover:
            if self.popup_style.cb_pressed_pic:
                button_source = self.popup_style.cb_pressed_pic
            else:
                bgc = self.popup_style.get("close_button_pressed_bg_color",
                                           "#FF0000")
                bga = self.popup_style.get("close_button_pressed_bg_alpha",
                                           100)
                xc = self.popup_style.get("close_button_pressed_x_color",
                                           "#FFFFFF")
                xa = self.popup_style.get("close_button_pressed_x_alpha", 100)
        elif self.mouseover:
            if self.popup_style.cb_hover_pic:
                button_source = self.popup_style.cb_hover_pic
            else:
                bgc = self.popup_style.get("close_button_hover_bg_color",
                                           "#FF0000")
                bga = self.popup_style.get("close_button_hover_bg_alpha", 100)
                xc = self.popup_style.get("close_button_hover_x_color",
                                           "#FFFFFF")
                xa = self.popup_style.get("close_button_hover_x_alpha", 0)
        else:
            if self.popup_style.cb_normal_pic:
                button_source = self.popup_style.cb_normal_pic
            else:
                bgc = self.popup_style.get("close_button_bg_color",
                                           "#FF0000")
                bga = self.popup_style.get("close_button_bg_alpha", 50)
                xc = self.popup_style.get("close_button_x_color",
                                           "#FFFFF")
                xa = self.popup_style.get("close_button_x_alpha", 0)

        if button_source is None:
            button_source = self.__make_button_surface(w, h, bgc, bga, xc, xa)
        ctx.set_source_surface(button_source, x, y)
        ctx.paint()

    def __make_button_surface(self, w, h, bgc, bga, xc, xa):
        button_source = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        bctx = cairo.Context(button_source)
        r = int(self.popup_style.get("close_button_roundness", 5))
        make_path(bctx, 0, 0, w, h, r)
        red, green, blue = parse_color(bgc)
        alpha = min(max(float(bga) / 100, 0), 1)
        bctx.set_source_rgba(red, green, blue, alpha)
        bctx.fill()
        bctx.scale(w, h)
        bctx.move_to(0.3, 0.3)
        bctx.line_to(0.7, 0.7)
        bctx.move_to(0.3, 0.7)
        bctx.line_to(0.7, 0.3)
        bctx.set_line_width(2.0/w)
        red, green, blue = parse_color(xc)
        alpha = min(max(float(xa) / 100, 0), 1)
        bctx.set_source_rgba(red, green, blue, alpha)
        bctx.set_operator(cairo.OPERATOR_SOURCE)
        bctx.stroke()
        return button_source

    def __on_popup_style_reloaded(self, *args):
        size = int(self.popup_style.get("close_button_size", 14))
        if size != self.size:
            self.set_size_request(size, size)
            self.size = size
            self.queue_draw()

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
        
class CairoArrowButton(CairoSmallButton):
    def __init__(self, direction="right"):
        self.direction = direction
        CairoSmallButton.__init__(self, 14, 14)

    def draw_button(self, ctx, x, y, w, h):
        if self.mouseover and self.get_sensitive():
            alpha = 1
        elif not self.get_sensitive():
            alpha = 0.05
        else:
            alpha = 0.5
        button_source = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        bctx = cairo.Context(button_source)
        if self.mousedown and self.mouseover:
            bctx.set_source_rgba(1, 0.4, 0.2, alpha)
        else:
            bctx.set_source_rgba(1, 1, 1, alpha)
        bctx.scale(w, h)
        bctx.set_operator(cairo.OPERATOR_SOURCE)
        bctx.translate(0.5, 0.5)
        if self.direction == "left":
            bctx.rotate(pi)
        elif self.direction == "up":
            bctx.rotate(-pi/2)
        elif self.direction == "down":
            bctx.rotate(pi/2)
        bctx.translate(-0.5, -0.5)
            
        bctx.move_to(0.2, 0.0)
        bctx.line_to(0.8, 0.5)
        bctx.line_to(0.2, 1.0)
        bctx.close_path()
        bctx.fill_preserve()
        bctx.set_line_width(2.0/w)
        bctx.set_source_rgba(1, 1, 1, 0)
        bctx.stroke()

        ctx.set_source_surface(button_source, x, y)
        ctx.paint()


class CairoPopup(Gtk.Window):
    """CairoPopup is a transparent popup window with rounded corners"""
    __gsignals__ = {"draw": "override",
                    "enter-notify-event": "override",
                    "leave-notify-event": "override"}
    def __init__(self, orient="down", no_arrow=False, type_="popup"):
        GObject.GObject.__init__(self, Gtk.WindowType.POPUP)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        gtk_screen = Gdk.Screen.get_default()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap is None:
            colormap = gtk_screen.get_rgb_colormap()
        self.set_colormap(colormap)
        self.set_app_paintable(1)
        self.globals = Globals()
        self.popup_style = PopupStyle()
        self.popup_type = type_
        self._pointer_is_inside = False

        self.alignment = Gtk.Alignment.new(0, 0, 0, 0)
        Gtk.Window.add(self, self.alignment)
        self.alignment.show()
        self.pointer = ""
        self.no_arrow = no_arrow
        if orient in ("down", "up"):
            # The direction of the pointer isn't important here we only need
            # the right amount of padding so that the popup has right width and
            # height for placement calculations.
            self.point("down")
        else:
            self.point("left")
        self.popup_reloaded_sid = self.popup_style.connect(
                                                "popup-style-reloaded",
                                                self.__on_popup_style_reloaded)

    def destroy(self):
        self.popup_style.disconnect(self.popup_reloaded_sid)
        self.popup_style = None
        Gtk.Window.destroy(self)

    def __get_arrow_size(self):
        if self.no_arrow:
            return 0
        else:
            return int(self.popup_style.get("arrow_size", 9))

    def add(self, child):
        self.alignment.add(child)

    def remove(self, child):
        self.alignment.remove(child)

    def point(self, new_pointer, ap=0):
        self.ap = ap
        p = int(self.popup_style.get("%s_padding" % self.popup_type, 7))
        a = self.__get_arrow_size()
        if new_pointer != self.pointer:
            self.pointer = new_pointer
            padding = {"up":(p+a, p, p, p),
                       "down":(p, p+a, p, p),
                       "left":(p, p, p+a, p),
                       "right":(p, p, p, p+a)}[self.pointer]
            self.alignment.set_padding(*padding)

    def do_draw(self, event):
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
        Gtk.Window.do_draw(self, event)

    def set_shape_mask(self):
        # Set window shape from alpha mask of background image
        w,h = self.get_size()
        if w==0: w = 800
        if h==0: h = 600
        pixmap = Gdk.Pixmap (None, w, h, 1)
        ctx = pixmap.cairo_create()
        ctx.set_source_rgba(0, 0, 0,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()
        r = int(self.popup_style.get("popup_roundness", 6))
        if self.is_composited():
            make_path(ctx, 0, 0, w, h, r, 0,
                      self.__get_arrow_size(), self.pointer, self.ap)
            ctx.set_source_rgba(1, 1, 1, 1)
            ctx.fill()
            self.input_shape_combine_mask(pixmap, 0, 0)
        else:
            make_path(ctx, 0, 0, w, h, r, 1,
                      self.__get_arrow_size(), self.pointer, self.ap)
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
        
        r = int(self.popup_style.get("popup_roundness", 6))
        make_path(ctx, 0, 0, w, h, r, 2.5,
                  self.__get_arrow_size(), self.pointer, self.ap)
        if self.is_composited():
            ctx.set_source_rgba(red, green, blue, alpha)
        else:
            ctx.set_source_rgb(red, green, blue)
        ctx.fill_preserve()
        # Linear gradients
        for n in (1, 2, 3):
            name = "popup_linear_gradient%s" % n
            if not int(self.popup_style.get("use_%s" % name, 0)):
                continue
            angle = int(self.popup_style.get("%s_angle" % name, 0))
            start = float(self.popup_style.get("%s_start" % name, 0))
            stop = float(self.popup_style.get("%s_stop" % name, 100))
            pattern = self.__make_linear_pattern(angle, start, stop, w, h)
            rpc1 = self.popup_style.get("%s_start_color" % name, "#FFFFFF")
            if not rpc1[0] == "#":
                rpc1 = "#%s" % rpc1
            red, green, blue = parse_color(rpc1)
            alpha = self.popup_style.get("%s_start_alpha" % name, 20)
            alpha = float(alpha) / 100
            pattern.add_color_stop_rgba(0.0, red, green, blue, alpha)
            
            rpc2 = self.popup_style.get("%s_stop_color" % name, "#FFFFFF")
            if not rpc2[0] == "#":
                rpc2 = "#%s" % rpc2
            red, green, blue = parse_color(rpc2)
            alpha = self.popup_style.get("%s_stop_alpha" % name, 0)
            alpha = float(alpha) / 100
            pattern.add_color_stop_rgba(1.0, red, green, blue, alpha)
            ctx.set_source(pattern)
            ctx.fill_preserve()
        # Radial gradients
        for n in (1, 2, 3):
            name = "popup_radial_gradient%s" % n
            if not int(self.popup_style.get("use_%s" % name, 0)):
                continue
            args = self.popup_style.get(name, "50,30,10,50,30,100")
            args = args.split(",")
            args = [int(arg) for arg in args]
            pattern = cairo.RadialGradient(*args)
            rpc1 = self.popup_style.get("%s_color1" % name, "#FFFFFF")
            if not rpc1[0] == "#":
                rpc1 = "#%s" % rpc1
            red, green, blue = parse_color(rpc1)
            alpha = self.popup_style.get("%s_alpha1" % name, 20)
            alpha = float(alpha) / 100
            pattern.add_color_stop_rgba(0.0, red, green, blue, alpha)
            
            rpc2 = self.popup_style.get("%s_color2" % name, "#FFFFFF")
            if not rpc2[0] == "#":
                rpc2 = "#%s" % rpc2
            red, green, blue = parse_color(rpc2)
            alpha = self.popup_style.get("%s_alpha2" % name, 0)
            alpha = float(alpha) / 100
            pattern.add_color_stop_rgba(1.0, red, green, blue, alpha)
            ctx.set_source(pattern)
            
            ctx.fill_preserve()
        # Background picture
        if self.popup_style.bg is not None:
            pattern = cairo.SurfacePattern(self.popup_style.bg)
            pattern.set_extend(cairo.EXTEND_REPEAT)
            ctx.set_source(pattern)
            ctx.fill_preserve()
        if self.is_composited():
            ctx.set_source_rgba(0.0, 0.0, 0.0, 0.8)
        else:
            ctx.set_source_rgb(0, 0, 0)
        bw = float(self.popup_style.get("border_width", 3))
        if "border_color2" in self.popup_style.settings:
            bc = self.popup_style.settings["border_color2"]
        else:
            bc = self.popup_style.get("border_color", "#FFFFFF")
        if bc[0] != "#":
            bc = "#%s" % bc
        alpha = self.popup_style.get("border_alpha", 80)
        alpha = float(alpha) / 100
        red = float(int(bc[1:3], 16))/255
        green = float(int(bc[3:5], 16))/255
        blue = float(int(bc[5:7], 16))/255
        if self.is_composited():
            ctx.set_source_rgba(red, green, blue, alpha)
        else:
            ctx.set_source_rgb(red, green, blue)
        ctx.set_line_width(bw)
        if not ("border_color2" in self.popup_style.settings):
            ctx.stroke()
            return
        else:
            ctx.stroke_preserve()
            bc = self.popup_style.get("border_color", "#FFFFFF")
            if bc[0] != "#":
                bc = "#%s" % bc
            red = float(int(bc[1:3], 16))/255
            green = float(int(bc[3:5], 16))/255
            blue = float(int(bc[5:7], 16))/255
            alpha = self.popup_style.get("border_alpha2", 100)
            alpha = float(alpha) / 100
            if self.is_composited():
                ctx.set_source_rgba(red, green, blue, alpha)
            else:
                ctx.set_source_rgb(red, green, blue)
            ctx.set_line_width(max(bw - 1, 0.5))
            ctx.stroke()

    def __make_linear_pattern(self, angle, start, stop, w, h):
        start_x = None
        angle =  angle % 360
        if angle < 0:
            angle += 360
        if angle == 0:
            start_x = start * w / 100.0
            start_y = 0
            stop_x = stop * w / 100.0
            stop_y = 0
        if angle == 180:
            start_x = w - (start * w / 100.0)
            start_y = 0
            stop_x = w - (stop * w / 100.0)
            stop_y = 0
        elif angle == 270:
            start_x = 0
            start_y = start * h / 100.0
            stop_x = 0
            stop_y = stop * h / 100.0
        elif angle == 90:
            start_x = 0
            start_y = h - (start * h / 100.0)
            stop_x = 0
            stop_y = h - (stop * h / 100.0)
        elif angle < 90:
            x1 = w * start / 100.0
            y1 = h - h * start / 100.0
            x2 = w * stop / 100.0
            y2 = h - h * stop / 100.0
        elif 90 < angle  and angle < 180:
            x1 = w - (w * start / 100.0)
            y1 = h - h * start / 100.0
            x2 = w - (w * stop / 100.0)
            y2 = h - h * stop / 100.0
        elif 180 < angle and angle < 270: 
            x1 = w - (w * start / 100.0)
            y1 = h * start / 100.0
            x2 = w - (w * stop / 100.0)
            y2 = h * stop / 100.0
        elif 270 < angle:
            x1 = w * start / 100.0
            y1 = h * start / 100.0
            x2 = w * stop / 100.0
            y2 = h * stop / 100.0
        if start_x is None:
            k1 = -tan(angle * pi / 180.0 )
            k2 = -1 / k1
            start_x = x1
            start_y = y1
            stop_x = (k1 * x1 - k2 * x2 + y2 - y1) / (k1 - k2)
            stop_y = k1 * (stop_x - x1) + y1
        return cairo.LinearGradient(start_x, start_y, stop_x, stop_y)
         
    def __on_popup_style_reloaded(self, *args):
        a = self.__get_arrow_size()
        p = int(self.popup_style.get("%s_padding" % self.popup_type, 7))
        padding = {"up":(p+a, p, p, p),
                   "down":(p, p+a, p, p),
                   "left":(p, p, p+a, p),
                   "right":(p, p, p, p+a)}[self.pointer]
        self.alignment.set_padding(*padding)
        if self.popup_type == "locked_list":
            self.resize(10, 10)

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
        Gtk.Window.do_enter_notify_event(self, *args)

    def do_leave_notify_event(self, *args):
        self._pointer_is_inside = False
        Gtk.Window.do_leave_notify_event(self, *args)

class CairoButton(Gtk.EventBox):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST,
                                None,(Gdk.Event, )),
                    "enter-notify-event": "override",
                    "leave-notify-event": "override",
                    "button-release-event": "override",
                    "button-press-event": "override"}

    def __init__(self, label=None, button_type="window_item"):
        GObject.GObject.__init__(self)
        self.set_visible_window(False)
        self.set_above_child(False)
        self.area = CairoArea(label, button_type)
        self.label = self.area.label
        Gtk.EventBox.add(self, self.area)
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

class CairoArea(Gtk.Alignment):
    __gsignals__ = {"draw" : "override"}
    def __init__(self, text=None, area_type="window_item"):
        self.type = area_type
        self.text = text
        GObject.GObject.__init__(self, 0, 0, 1, 1)
        self.popup_style = PopupStyle()
        lrp = int(self.popup_style.get("%s_lr_padding" % self.type,
                                                5))
        tdp = int(self.popup_style.get("%s_td_padding" % self.type,
                                                5))
        self.set_padding(lrp, lrp, tdp, tdp)
        self.set_app_paintable(1)
        self.globals = Globals()
        self.highlighted = False
        self.pressed_down = False
        self.active_window = False
        self.needs_attention = False
        self.minimized = False
        self.preview_allocation = [0, 0, 0, 0]
        if text:
            self.label = Gtk.Label()
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
        Gtk.Alignment.set_padding(self, top, bottom, left, right)

    def set_label_color(self, color):
        label = "<span foreground=\"" + color + "\">" + escape(self.text) + \
                "</span>"
        self.label.set_text(label)
        self.label.set_use_markup(True)
        self.label.set_use_underline(True)

    def do_draw(self, event, arg=None):
        a = self.get_allocation()
        mx , my = self.get_pointer()
        preview = self.globals.settings["preview"] and \
                  self.globals.get_compiz_version() >= "0.9" and \
                  (self.globals.settings["preview_minimized"] or \
                   not self.minimized)
        highlighted = self.highlighted or \
                      (mx >= 0 and mx < a.width and my >= 0 and my < a.height)
            
        if preview or self.active_window or \
           highlighted or self.needs_attention:
            ctx = self.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
            ctx.clip()
        if self.needs_attention:
            self.draw_type_frame(ctx, a.x, a.y, a.width, a.height,
                                 "needs_attention_item")
        if self.active_window:
            self.draw_type_frame(ctx, a.x, a.y, a.width, a.height,
                                 "active_item")
        if highlighted:
            self.draw_frame(ctx, a.x, a.y, a.width, a.height)
        # Empty preview space
        if preview:
            ctx.rectangle(*self.preview_allocation)
            ctx.set_source_rgba(1, 1, 1, 0)
            ctx.set_operator(cairo.OPERATOR_SOURCE)
            ctx.fill()
        self.propagate_expose(self.get_child(), event)
        return

    def draw_frame(self, ctx, x, y, w, h):
        if self.is_composited():
            r, g, b = parse_color(self.globals.colors["color1"])
            alpha = parse_alpha(self.globals.colors["color1_alpha"])
        else:
            r = g = b = 0.0
            alpha = 0.25
        roundness = int(self.popup_style.get("%s_roundness" % \
                                                      self.type, 5))
        make_path(ctx, x, y, w, h, roundness)


        ctx.set_source_rgba(r, g, b, alpha)
        ctx.fill_preserve()
        bc = self.popup_style.get("%s_border_color" % self.type,
                                           "#FFFFFF")
        if not bc[0] == "#":
            bc = "#%s" % bc
        alpha = self.popup_style.get("%s_border_alpha" % self.type,
                                              80)
        alpha = float(alpha) / 100
        r, g, b = parse_color(bc)
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.set_line_width(1)
        ctx.stroke()

    def draw_type_frame(self, ctx, x, y, w, h, type_):
        # Todo: make colors themable?
        if type_ == "active_item":
            color = self.globals.colors["color3"]
        elif type_ == "needs_attention_item":
            color = self.popup_style.get("%s_color" % type_,
                                                  "#FF0000")
        roundness = int(self.popup_style.get("%s_roundness" % \
                                                      self.type, 5))
        make_path(ctx, x, y, w, h, roundness)

        if color[0] != "#":
            color = "#%s" % color
        r, g, b = parse_color(color)
        # Todo: make alpha adjustable from theme.
        alpha = self.popup_style.get("%s_alpha" % type_, 15)
        alpha = float(alpha) / 100
        ctx.set_source_rgba(r, g, b, 0.25)
        ctx.fill_preserve()
        
        bc = self.popup_style.get("%s_border_color" % type_,
                                           "#FFFFFF")
        if not bc[0] == "#":
            bc = "#%s" % bc
        # Todo: make alpha adjustable from theme.
        r, g, b = parse_color(bc)
        alpha = self.popup_style.get("%s_border_alpha" % type_, 15)
        alpha = float(alpha) / 100
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.set_line_width(1)
        ctx.stroke()

    def set_pressed_down(self, pressed):
        p = self.get_padding()
        if pressed and not self.pressed_down:
            Gtk.Alignment.set_padding(self, p[0] + 1, p[1] - 1, p[2], p[3])
        elif self.pressed_down and not pressed:
            Gtk.Alignment.set_padding(self, p[0] - 1, p[1] + 1, p[2], p[3])
        self.pressed_down = pressed

    def set_highlighted(self, highlighted):
        self.highlighted = highlighted
        self.queue_draw()

    def set_active_window(self, active):
        self.active_window = active
        self.queue_draw()

    def set_needs_attention(self, needs_attention):
        self.needs_attention = needs_attention
        self.queue_draw()

    def set_minimized(self, minimized):
        self.minimized = minimized
        self.queue_draw()

    def set_preview_allocation(self, allocation):
        self.preview_allocation = allocation

    def pointer_is_inside(self):
        mx,my = self.get_pointer()
        a = self.get_allocation()

        if mx >= 0 and mx < a.width \
        and my >= 0 and my < a.height:
            # Mouse pointer is inside the "rectangle"
            # but check if it's still outside the rounded corners
            x = None
            y = None
            r = int(self.popup_style.get("%s_roundness" % self.type,
                                                  5))
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
        CairoButton.__init__(self, label, button_type="menu_item")
        

class CairoCheckMenuItem(CairoMenuItem):
    def __init__(self, label, toggle_type="checkmark"):
        self.globals = Globals()
        CairoMenuItem.__init__(self, None)
        self.indicator = Gtk.CheckMenuItem()
        self.indicator.set_draw_as_radio(toggle_type == "radio")
        self.area.label = Gtk.Label()
        hbox = Gtk.HBox()
        hbox.pack_start(self.indicator, False, False, 2)
        hbox.pack_start(self.area.label, False, False, 2)
        alignment = Gtk.Alignment.new(0.5,0.5,0,0)
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
        

class CairoToggleMenu(Gtk.VBox):
    __gsignals__ = {"toggled": (GObject.SignalFlags.RUN_FIRST,
                                None,(bool, ))}

    def __init__(self, label=None, show_menu=False):
        GObject.GObject.__init__(self)
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
        self.pack_start(self.toggle_button, True, True, 0)
        self.toggle_button.show()
        self.toggle_button.connect("clicked", self.toggle)
        self.menu = CairoVBox()
        self.menu.set_no_show_all(True)
        self.pack_start(self.menu, True, True, 0)
        self.menu.set_border_width(10)
        self.show_menu = show_menu
        if show_menu:
            self.menu.show()

    def add_item(self, item):
        self.menu.pack_start(item, True, True, 0)

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


class CairoVBox(Gtk.VBox):
    __gsignals__ = {"draw" : "override"}

    def __init__(self, label=None, show_menu=False):
        GObject.GObject.__init__(self)
        self.set_app_paintable(1)
        self.globals = Globals()
        self.popup_style = PopupStyle()

    def do_draw(self, event, arg=None):
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_frame(ctx, a.x, a.y, a.width, a.height)
        for child in self.get_children():
            self.propagate_expose(child, event)

    def draw_frame(self, ctx, x, y, w, h):
        color = "#000000"
        r, g, b = parse_color(color)
        rd = int(self.popup_style.get("menu_item_roundness", 5))
        make_path(ctx, x, y, w, h, rd)
        ctx.set_source_rgba(r, g, b, 0.20)
        ctx.fill_preserve()

        ctx.set_source_rgba(r, g, b, 0.20)
        ctx.set_line_width(1)
        ctx.stroke()

class CairoPreview(Gtk.Image):
    _gsignals__ = {"draw" : "override",
                   "visibility-notify-event": "override"}
    def __init__(self):
        GObject.GObject.__init__(self)
        GObject.timeout_add(100, self.draw)

    def draw(self):
        if self.window is None:
            return True
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(a.x, a.y,
                      a.width, a.height)
        ctx.clip()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(1,1,1,0)
        ctx.paint()

    def do_draw(self, event, arg=None):
        a = self.get_allocation()
        ctx = self.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(1,1,1,0)
        ctx.paint()

    def do_visibility_notify_event(self, *args):
        self.draw()

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

