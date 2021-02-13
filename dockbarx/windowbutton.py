#!/usr/bin/python3

#   windowbutton.py
#
#	Copyright 2008, 2009, 2010 Aleksey Shaferov and Matias Sars
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
from gi.repository import GdkX11
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Pango
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck
import weakref
import gc
gc.enable()
import Xlib
from PIL import Image

from .common import ODict, Globals, Opacify
from .common import opacify, deopacify
from .common import XDisplay
from .cairowidgets import *
from .log import logger

from . import i18n
_ = i18n.language.gettext


try:
    WNCK_WINDOW_ACTION_MINIMIZE = Wnck.WindowType.ACTION_MINIMIZE
    WNCK_WINDOW_ACTION_UNMINIMIZE = Wnck.WindowType.ACTION_UNMINIMIZE
    WNCK_WINDOW_ACTION_MAXIMIZE = Wnck.WindowType.ACTION_MAXIMIZE
    WNCK_WINDOW_STATE_MINIMIZED = Wnck.WindowType.STATE_MINIMIZED
except:
    WNCK_WINDOW_ACTION_MINIMIZE = 1 << 12
    WNCK_WINDOW_ACTION_UNMINIMIZE = 1 << 13
    WNCK_WINDOW_ACTION_MAXIMIZE = 1 << 14
    WNCK_WINDOW_STATE_MINIMIZED = 1 << 0


class Window():
    def __init__(self, wnck_window, group):
        self.group_r = weakref.ref(group)
        self.globals = Globals()
        self.opacify_obj = Opacify()
        self.screen = Wnck.Screen.get_default()
        self.wnck = wnck_window
        self.deopacify_sid = None
        self.opacify_sid = None
        self.select_sid = None
        self.xid = self.wnck.get_xid()
        self.is_active_window = False
        self.on_current_desktop = self.is_on_current_desktop()
        self.monitor = self.get_monitor()

        self.globals_event = self.globals.connect("show-only-current-monitor-changed",
                                                self.__on_show_only_current_monitor_changed)
        self.state_changed_event = self.wnck.connect("state-changed",
                                                self.__on_window_state_changed)
        self.icon_changed_event = self.wnck.connect("icon-changed",
                                                self.__on_window_icon_changed)
        self.name_changed_event = self.wnck.connect("name-changed",
                                                self.__on_window_name_changed)
        self.geometry_changed_event = self.wnck.connect("geometry-changed",
                                                self.__on_geometry_changed)

        self.item = WindowItem(self, group)
        self.needs_attention = self.wnck.needs_attention()
        self.item.show()
        self.__on_show_only_current_monitor_changed()

    def __ne__(self, window):
        if isinstance(window, Wnck.Window):
            return self.wnck != window
        else:
            return window is not self

    def __eq__(self, window):
        if isinstance(window, Wnck.Window):
            return self.wnck == window
        else:
            return window is self

    def set_active(self, mode):
        if self.is_active_window != mode:
            self.is_active_window = mode
            self.item.active_changed()

    def is_on_current_desktop(self):
        aws = self.screen.get_active_workspace()
        if (self.wnck.get_workspace() is None or \
           self.wnck.get_workspace() == aws) and \
           self.wnck.is_in_viewport(aws):
            return True
        else:
            return False

    def is_on_monitor(self, monitor):
        if not self.globals.settings["show_only_current_monitor"]:
            return True
        return monitor.get_geometry().equal(self.get_monitor().get_geometry())

    def get_monitor(self):
        if not self.globals.settings["show_only_current_monitor"]:
            return 0
        x, y, w, h = self.wnck.get_geometry()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            gdk_display = Gdk.Screen.get_default().get_display()
            return gdk_display.get_monitor_at_point(x + (w // 2), y  + (h // 2))
        else:
            gdk_screen = Gdk.Screen.get_default()
            return gdk_screen.get_monitor_at_point(x + (w // 2), y  + (h // 2))

    def destroy(self):
        if self.deopacify_sid:
            GLib.source_remove(self.deopacify_sid)
            self.deopacify()
        self.remove_delayed_select()

        self.item.clean_up()
        self.item.destroy()
        self.globals.disconnect(self.globals_event)
        self.wnck.disconnect(self.state_changed_event)
        self.wnck.disconnect(self.icon_changed_event)
        self.wnck.disconnect(self.name_changed_event)
        if self.geometry_changed_event is not None:
            self.wnck.disconnect(self.geometry_changed_event)
        del self.screen
        del self.wnck
        del self.globals

    def __on_show_only_current_monitor_changed(self, arg=None):
        self.monitor = self.get_monitor()

    def select_after_delay(self, delay):
        if self.select_sid:
            GLib.source_remove(self.select_sid)
        self.select_sid = GLib.timeout_add(delay, self.action_select_window)

    def remove_delayed_select(self):
        if self.select_sid:
            GLib.source_remove(self.select_sid)
            self.select_sid = None

    #### Windows's Events
    def __on_window_state_changed(self, wnck_window,changed_mask, new_state):
        if WNCK_WINDOW_STATE_MINIMIZED & changed_mask:
            self.item.minimized_changed()
            self.group_r().button.update_state_if_shown()

        # Check if the window needs attention
        if self.wnck.needs_attention() != self.needs_attention:
            self.needs_attention = self.wnck.needs_attention()
            self.item.needs_attention_changed()
            self.group_r().needs_attention_changed()

    def __on_window_icon_changed(self, window):
        self.item.icon_changed()

    def __on_window_name_changed(self, window):
        self.item.name_changed()

    def __on_geometry_changed(self, *args):
        group = self.group_r()
        if self.globals.settings["show_only_current_monitor"]:
            monitor = self.get_monitor()
            if monitor != self.monitor:
                self.monitor = monitor
                self.item.update_show_state()
                group.window_monitor_changed()
        if self.globals.settings["show_only_current_desktop"]:
            onc = self.is_on_current_desktop()
            if self.on_current_desktop != onc:
                self.on_current_desktop = onc
                self.item.update_show_state()
                group.window_desktop_changed()
        if self.globals.settings["preview"]:
            self.item.update_preview()

    def desktop_changed(self):
        self.on_current_desktop = self.is_on_current_desktop()
        if self.on_current_desktop:
            self.item.show()
        else:
            self.item.hide()

    #### Opacify
    def opacify(self):
        self.xid = self.wnck.get_xid()
        opacify(self.xid, self.xid)

    def deopacify(self):
        if self.item.deopacify_sid:
            GLib.source_remove(self.item.deopacify_sid)
            self.item.deopacify_sid = None
        if self.deopacify_sid:
            self.deopacify_sid = None
        deopacify(self.xid)

    #### Actions
    def action_select_or_minimize_window(self, widget=None,
                                         event=None, minimize=True):
        # The window is activated, unless it is already
        # activated, then it's minimized. Minimized
        # windows are unminimized. The workspace
        # is switched if the window is on another
        # workspace.
        self.remove_delayed_select()
        if event:
            t = event.time
        else:
            t = GdkX11.x11_get_server_time(Gdk.get_default_root_window())
        if self.wnck.get_workspace() is not None \
        and self.screen.get_active_workspace() != self.wnck.get_workspace():
            self.wnck.get_workspace().activate(t)
        if not self.wnck.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.wnck.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),
                                      win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movement won't
            # be tracked during compiz move effect
            # which means popup list can be left open.
            group = self.group_r()
            group.popup.hide()
        if self.wnck.is_minimized():
            self.wnck.unminimize(t)
        elif self.wnck.is_active() and minimize:
            self.wnck.minimize()
        else:
            self.wnck.activate(t)
        # Deopacify is needed here since this function is called from
        # the group button class as well.
        self.deopacify()

    def action_select_window(self, widget = None, event = None):
        self.action_select_or_minimize_window(widget, event, False)

    def action_close_window(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = 0
        self.wnck.close(t)

    def action_maximize_window(self, widget=None, event=None):
        if self.wnck.is_maximized():
            self.wnck.unmaximize()
        else:
            self.wnck.maximize()

    def action_shade_window(self, widget, event=None):
        self.wnck.shade()

    def action_unshade_window(self, widget, event=None):
        self.wnck.unshade()

    def action_show_menu(self, widget, event=None):
        self.item.show_menu(event)

    def action_minimize_window(self, widget=None, event=None):
        if self.wnck.is_minimized():
            if event:
                t = event.time
            else:
                t = 0
            self.wnck.unminimize(t)
        else:
            self.wnck.minimize()

    def action_none(self, widget=None, event=None):
        pass

    action_function_dict = ODict((
                                  ("select or minimize window",
                                            action_select_or_minimize_window),
                                  ("select window", action_select_window),
                                  ("maximize window", action_maximize_window),
                                  ("close window", action_close_window),
                                  ("show menu", action_show_menu),
                                  ("shade window", action_shade_window),
                                  ("unshade window", action_unshade_window),
                                  ("no action", action_none)
                                ))


class WindowItem(CairoButton):
    def __init__(self, window, group):
        CairoButton.__init__(self)
        self.set_no_show_all(True)

        self.window_r = weakref.ref(window)
        self.group_r = weakref.ref(group)
        self.globals = Globals()

        self.opacify_sid = None
        self.deopacify_sid = None
        self.press_sid = None
        self.pressed = False

        self.area.set_needs_attention(window.wnck.needs_attention())

        self.close_button = CairoCloseButton()
        self.close_button.set_halign(Gtk.Align.START)
        self.close_button.set_valign(Gtk.Align.CENTER)
        self.close_button.set_no_show_all(True)
        if self.globals.settings["show_close_button"]:
            self.close_button.show()

        self.label = Gtk.Label()
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_halign(Gtk.Align.START)
        self.label.set_valign(Gtk.Align.CENTER)

        icon = window.wnck.get_mini_icon()
        self.icon_image = Gtk.Image()
        self.icon_image.set_from_pixbuf(icon)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            self.icon_image.set_margin_start(2)
        else:
            self.icon_image.set_margin_left(2)

        self.header_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
        self.header_box.pack_start(self.icon_image, False, False, 0)
        self.header_box.pack_start(self.label, True, True, 0)
        self.header_box.pack_start(self.close_button, False, False, 0)

        vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        vbox.pack_start(self.header_box, False, False, 0)
        self.preview = Gtk.Image()
        self.preview.set_halign(Gtk.Align.CENTER)
        self.preview.set_valign(Gtk.Align.CENTER)
        self.preview.set_margin_top(4)
        self.preview.set_margin_bottom(2)
        vbox.pack_start(self.preview, True, True, 0)
        self.add(vbox)
        self.preview.set_no_show_all(True)
        vbox.show_all()

        self.show_all()
        self.__update_label()
        self.update_show_state()

        self.drag_dest_set(0, [], 0)
        self.drag_entered = False

        # Make scroll events work.
        self.add_events(Gdk.EventMask.SCROLL_MASK)
        
        self.connect("enter-notify-event", self.on_enter_notify_event)
        self.connect("leave-notify-event", self.on_leave_notify_event)
        self.connect("button-press-event", self.on_button_press_event)
        self.connect("scroll-event", self.on_scroll_event)
        self.connect("clicked", self.on_clicked)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-leave", self.on_drag_leave)
        self.close_button.connect("button-press-event", self.disable_click)
        self.close_button.connect("clicked", self.__on_close_button_clicked)
        self.close_button.connect("leave-notify-event",
                                  self.__on_close_button_leave)

        self.globals_events = []
        self.globals_events.append(self.globals.connect("show-close-button-changed",
                                    self.__on_show_close_button_changed))
        self.globals_events.append(self.globals.connect("color-changed",
                                    self.__update_label))
        self.globals_events.append(self.globals.connect("preview-size-changed",
                                    self.update_preview))
        self.globals_events.append(self.globals.connect("window-title-width-changed",
                                    self.__update_label))

    def clean_up(self):
        window = self.window_r()
        if self.deopacify_sid:
            GLib.source_remove(self.deopacify_sid)
            self.deopacify_sid = None
            window.deopacify()
        if self.opacify_sid:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None
        if self.press_sid:
            GLib.source_remove(self.press_sid)
            self.press_sid = None
        while self.globals_events:
            self.globals.disconnect(self.globals_events.pop())
        self.close_button.destroy()

    def show(self):
        if self.globals.settings["preview"]:
            self.update_preview()
        CairoButton.show(self)

    def __on_show_close_button_changed(self, *args):
        if self.globals.settings["show_close_button"]:
            self.close_button.show()
        else:
            self.close_button.hide()
            self.label.queue_resize()

    #### Appearance
    def __update_label(self, arg=None):
        """Updates the style of the label according to window state."""
        window = self.window_r()
        text = escape(str(window.wnck.get_name()))
        if window.wnck.is_minimized():
            color = self.globals.colors["color4"]
        else:
            color = self.globals.colors["color2"]
        text = "<span foreground=\"" + color + "\">" + text + "</span>"
        self.label.set_text(text)
        self.label.set_use_markup(True)
        if self.globals.settings["preview"]:
            # The label should be 140px wide unless there are more room
            # because the preview takes up more.
            label_size = 140
        else:
            label_size = self.globals.settings["window_title_width"]

        size = label_size + self.icon_image.get_pixel_size() + \
                self.close_button.get_allocation().width + \
                self.header_box.get_spacing() * 2
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            size += self.icon_image.get_margin_start()
        else:
            size += self.icon_image.get_margin_left()
        self.header_box.set_size_request(size, -1)

    def __make_minimized_icon(self, icon):
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, icon.get_width(), icon.get_height())
        pixbuf.fill(0x00000000)
        minimized_icon = pixbuf.copy()
        icon.composite(pixbuf, 0, 0, pixbuf.get_width(), pixbuf.get_height(),
                       0, 0, 1, 1, GdkPixbuf.InterpType.BILINEAR, 190)
        pixbuf.saturate_and_pixelate(minimized_icon, 0.12, False)
        return minimized_icon

    def __update_icon(self):
        window = self.window_r()
        icon = window.wnck.get_mini_icon()
        if window.wnck.is_minimized():
            pixbuf = self.__make_minimized_icon(icon)
            self.icon_image.set_from_pixbuf(pixbuf)
        else:
            self.icon_image.set_from_pixbuf(icon)

    def minimized_changed(self):
        window = self.window_r()
        self.__update_label()
        self.__update_icon()
        self.area.set_minimized(window.wnck.is_minimized())

    def active_changed(self):
        window = self.window_r()
        self.area.set_active_window(window.is_active_window)
        self.__update_label()

    def icon_changed(self):
        self.__update_icon()

    def needs_attention_changed(self):
        window = self.window_r()
        self.area.set_needs_attention(window.wnck.needs_attention())
        self.__update_label()

    def name_changed(self):
        self.__update_label()

    def set_highlighted(self, highlighted):
        self.area.set_highlighted(highlighted)

    def update_show_state(self):
        window = self.window_r()
        if (self.globals.settings["show_only_current_desktop"] and \
           not window.on_current_desktop) or \
           (self.globals.settings["show_only_current_monitor"] and \
           window.monitor != self.group_r().monitor):
            self.hide()
        else:
            self.show()

    ####Preview
    def update_preview(self, *args):
        window = self.window_r()
        group = self.group_r()
        width = window.wnck.get_geometry()[2]
        height = window.wnck.get_geometry()[3]
        ar = group.monitor_aspect_ratio
        size = self.globals.settings["preview_size"]
        if width*ar < size and height < size:
            pass
        elif float(width) / height > ar:
            height = int(round(size * ar * height / width))
            width = int(round(size * ar))
        else:
            width = int(round(float(size) * width / height))
            height = size
        self.preview.set_size_request(width, height)
        return width, height

    def set_show_preview(self, show_preview):
        if show_preview:
            if self.group_r().popup.popup_showing:
                self.set_preview_image()
            self.preview.show()
        else:
            self.preview.hide()

    def get_preview_allocation(self):
        a = self.preview.get_allocation()
        self.area.set_preview_allocation(a)
        return a

    def set_preview_image(self):
        window = self.window_r()
        try:
            xwin = XDisplay.create_resource_object('window', window.xid)
            # window.wnck.is_minimized() may not work with some wine program windows
            if xwin.get_wm_state().state == Xlib.Xutil.IconicState:
                # TODO: self.globals.settings["preview_minimized"]
                self.preview.set_from_pixbuf(window.wnck.get_icon())
                return
            xwin.composite_redirect_window(Xlib.ext.composite.RedirectAutomatic)
            geo = xwin.get_geometry()
            pixmap = xwin.composite_name_window_pixmap()
            image_object = pixmap.get_image(0, 0, geo.width, geo.height, Xlib.X.ZPixmap, 0xffffffff)
            pixmap.free()
            xwin.composite_unredirect_window(Xlib.ext.composite.RedirectAutomatic)
        except:
            self.preview.set_from_pixbuf(window.wnck.get_icon())
            return;
        im = Image.frombuffer("RGBX", (geo.width, geo.height), image_object.data, "raw", "BGRX").convert("RGB")
        data = im.tobytes()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 14:
            data = GLib.Bytes.new(data)
            pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB, False, 8, geo.width, geo.height, geo.width * 3)
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(data, GdkPixbuf.Colorspace.RGB, False, 8, geo.width, geo.height, geo.width * 3)
        w, h = self.preview.get_size_request()
        self.preview.set_from_pixbuf(pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR))

    #### Events
    def on_enter_notify_event(self, widget, event):
        # In compiz there is a enter and
        # a leave event before a press event.
        # Keep that in mind when coding this def!
        CairoButton.on_enter_notify_event(self, widget, event)
        if self.pressed :
            return
        if self.globals.settings["opacify"]:
            self.opacify_sid = \
                GLib.timeout_add(100, self.__opacify)

    def on_leave_notify_event(self, widget, event):
        # In compiz there is a enter and a leave
        # event before a press event.
        # Keep that in mind when coding this def!
        CairoButton.on_leave_notify_event(self, widget, event)
        self.pressed = False
        if self.globals.settings["opacify"]:
            self.deopacify_sid = \
                            GLib.timeout_add(200, self.__deopacify)

    def on_button_press_event(self, widget, event):
        # In compiz there is a enter and a leave event before
        # a press event.
        # self.pressed is used to stop functions started with
        # GLib.timeout_add from self.__on_mouse_enter
        # or self.__on_mouse_leave.
        CairoButton.on_button_press_event(self, widget, event)
        self.pressed = True
        self.press_sid = GLib.timeout_add(600, self.__set_pressed_false)

    def __set_pressed_false(self):
        # Helper function for __on_press_event.
        self.pressed = False
        self.press_sid = None
        return False

    def on_scroll_event(self, widget, event):
        window = self.window_r()
        if self.globals.settings["opacify"]:
            window.deopacify()
        if not event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            return
        direction = {Gdk.ScrollDirection.UP: "scroll_up",
                     Gdk.ScrollDirection.DOWN: "scroll_down"}[event.direction]
        action = self.globals.settings["windowbutton_%s"%direction]
        window.action_function_dict[action](window, self, event)
        if self.globals.settings["windowbutton_close_popup_on_%s"%direction]:
            self.group_r().popup.hide()

    def on_clicked(self, widget, button_nr, state):
        window = self.window_r()
        if self.globals.settings["opacify"]:
            window.deopacify()

        if not button_nr in (1, 2, 3):
            return
        button = {1:"left", 2: "middle", 3: "right"}[button_nr]
        if state & Gdk.ModifierType.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        action_str = "windowbutton_%s%s_click_action"%(mod, button)
        action = self.globals.settings[action_str]
        window.action_function_dict[action](window, self)

        popup_close = "windowbutton_close_popup_on_%s%s_click"%(mod, button)
        if self.globals.settings[popup_close]:
            self.group_r().popup.hide()

    def __on_close_button_clicked(self, *args):
        window = self.window_r()
        if self.globals.settings["opacify"]:
            window.deopacify()
        window.action_close_window()

    def __on_close_button_leave(self, widget, event):
        if not self.pointer_is_inside():
            self.on_leave_notify_event(widget, event)

    #### D'n'D
    def on_drag_motion(self, widget, drag_context, x, y, t):
        if not self.drag_entered:
            self.group_r().popup.expose()
            self.drag_entered = True
            self.dnd_select_window = \
                GLib.timeout_add(600, self.window_r().action_select_window)
        Gdk.drag_status(drag_context, Gdk.DragAction.PRIVATE, t)
        return True

    def on_drag_leave(self, widget, drag_context, t):
        self.drag_entered = False
        GLib.source_remove(self.dnd_select_window)
        self.group_r().popup.expose()
        self.group_r().popup.hide_if_not_hovered()

    #### Opacify
    def __opacify(self):
        self.opacify_sid = None
        window = self.window_r()
        if window is None or window.wnck.is_minimized():
            return False
        # if self.pressed is true, opacity_request is called by an
        # wrongly sent out enter_notification_event sent after a
        # press (because of a bug in compiz).
        if self.pressed:
            self.pressed = False
            return False
        # Check if mouse cursor still is over the window button.
        if self.pointer_is_inside():
            window.opacify()
            # Just for safety in case no leave-signal is sent
            self.deopacify_sid = \
                            GLib.timeout_add(500, self.__deopacify)
        return False

    def __deopacify(self):
        self.deopacify_sid = None
        window = self.window_r()
        if window is None:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.get_pointer()
        b_r = self.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            return True
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        window.deopacify_sid = GLib.timeout_add(150, window.deopacify)
        return False

    #### Menu functions
    def show_menu(self, event):
        window = self.window_r()
        #Creates a popup menu
        menu = Gtk.Menu()
        menu.connect("selection-done", self.__menu_closed)
        #(Un)Minimize
        minimize_item = None
        if window.wnck.get_actions() & WNCK_WINDOW_ACTION_MINIMIZE \
        and not window.wnck.is_minimized():
            minimize_item = Gtk.MenuItem.new_with_mnemonic(_("_Minimize"))
        elif window.wnck.get_actions() & WNCK_WINDOW_ACTION_UNMINIMIZE \
        and window.wnck.is_minimized():
            minimize_item = Gtk.MenuItem.new_with_mnemonic(_("Un_minimize"))
        if minimize_item:
            menu.append(minimize_item)
            minimize_item.connect("activate", window.action_minimize_window)
            minimize_item.show()
        # (Un)Maximize
        maximize_item = None
        if not window.wnck.is_maximized() \
        and window.wnck.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
            maximize_item = Gtk.MenuItem.new_with_mnemonic(_("Ma_ximize"))
        elif window.wnck.is_maximized() \
        and window.wnck.get_actions() & WNCK_WINDOW_ACTION_UNMINIMIZE:
            maximize_item = Gtk.MenuItem.new_with_mnemonic(_("Unma_ximize"))
        if maximize_item:
            menu.append(maximize_item)
            maximize_item.connect("activate", window.action_maximize_window)
            maximize_item.show()
        # Close
        close_item = Gtk.MenuItem.new_with_mnemonic(_("_Close"))
        menu.append(close_item)
        close_item.connect("activate", window.action_close_window)
        close_item.show()
        if event is None:
            button = 0
            time = Gtk.get_current_event_time()
        else:
            button = event.button
            time = event.time
        menu.popup(None, None, None, None, button, time)
        self.globals.gtkmenu = menu

    def __menu_closed(self, menushell):
        self.globals.gtkmenu = None
        self.group_r().popup.hide()
        menushell.destroy()
