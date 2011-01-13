#!/usr/bin/python

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

import wnck
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango
import weakref
import gc
gc.enable()

from common import ODict, Globals, Opacify, connect, disconnect
from cairowidgets import CairoWindowItem

import i18n
_ = i18n.language.gettext


try:
    WNCK_WINDOW_ACTION_MINIMIZE = wnck.WINDOW_ACTION_MINIMIZE
    WNCK_WINDOW_ACTION_UNMINIMIZE = wnck.WINDOW_ACTION_UNMINIMIZE
    WNCK_WINDOW_ACTION_MAXIMIZE = wnck.WINDOW_ACTION_MAXIMIZE
    WNCK_WINDOW_STATE_MINIMIZED = wnck.WINDOW_STATE_MINIMIZED
except:
    WNCK_WINDOW_ACTION_MINIMIZE = 1 << 12
    WNCK_WINDOW_ACTION_UNMINIMIZE = 1 << 13
    WNCK_WINDOW_ACTION_MAXIMIZE = 1 << 14
    WNCK_WINDOW_STATE_MINIMIZED = 1 << 0


class WindowButton():

    def __init__(self, groupbutton, window):
        self.groupbutton_r = weakref.ref(groupbutton)
        self.globals = Globals()
        self.opacify_obj = Opacify()
        connect(self.globals, "show-only-current-monitor-changed",
                             self.__on_show_only_current_monitor_changed)
        self.screen = wnck.screen_get_default()
        self.name = window.get_name()
        self.window = window
        self.button_pressed = False
        self.deopacify_request_sid = None
        self.deopacify_sid = None
        self.opacify_request_sid = None
        self.xid = window.get_xid()

        self.button = CairoWindowItem(u"" + window.get_name(),
                                      window.get_mini_icon(),
                                      window.get_icon())
        self.needs_attention = window.needs_attention()
        self.button.set_needs_attention(self.needs_attention)
        self.button.show()
        self.geometry_changed_event = None
        self.__on_show_only_current_monitor_changed()


        #--- Events
        connect(self.button, "enter-notify-event",
                                   self.__on_button_mouse_enter)
        connect(self.button, "leave-notify-event",
                                   self.__on_button_mouse_leave)
        connect(self.button, "button-press-event",
                                   self.__on_window_button_press_event)
        connect(self.button, "clicked", self.__on_clicked)
        connect(self.button, "scroll-event",
                                   self.__on_window_button_scroll_event)
        connect(self.button, "close-clicked", self.__on_close_clicked)
        self.state_changed_event = self.window.connect("state-changed",
                                                self.__on_window_state_changed)
        self.icon_changed_event = self.window.connect("icon-changed",
                                                self.__on_window_icon_changed)
        self.name_changed_event = self.window.connect("name-changed",
                                                self.__on_window_name_changed)
        self.button_press_sid = None

        #--- D'n'D
        self.button.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT, [], 0)
        connect(self.button, "drag_motion", self.__on_button_drag_motion)
        connect(self.button, "drag_leave", self.__on_button_drag_leave)
        self.button_drag_entered = False
        self.dnd_select_window = None

    def set_button_active(self, mode):
        self.button.set_is_active_window(mode)


    def is_on_current_desktop(self):
        if (self.window.get_workspace() is None \
        or self.screen.get_active_workspace() == self.window.get_workspace()) \
        and self.window.is_in_viewport(self.screen.get_active_workspace()):
            return True
        else:
            return False

    def get_monitor(self):
        if not self.globals.settings["show_only_current_monitor"]:
            return 0
        gdk_screen = gtk.gdk.screen_get_default()
        win = gtk.gdk.window_lookup(self.window.get_xid())
        if win is None:
            print "Error: couldn't find out on which " + \
                  "monitor window \"%s\" is located" % self.window.get_name()
            print "Guessing it's monitor 0"
            return 0
        x, y, w, h, bit_depth = win.get_geometry()
        return gdk_screen.get_monitor_at_point(x + (w / 2), y  + (h / 2))

    def __on_show_only_current_monitor_changed(self, arg=None):
        if self.globals.settings["show_only_current_monitor"]:
            if self.geometry_changed_event is None:
                self.geometry_changed_event = self.window.connect(
                                "geometry-changed", self.__on_geometry_changed)
        else:
            if self.geometry_changed_event is not None:
                self.window.disconnect(self.geometry_changed_event)
        self.monitor = self.get_monitor()

    def del_button(self):
        if self.deopacify_sid:
            gobject.source_remove(self.deopacify_sid)
            self.deopacify()
        elif self.deopacify_request_sid:
            self.deopacify()
        if self.opacify_request_sid:
            gobject.source_remove(self.opacify_request_sid)
        if self.button_press_sid:
            gobject.source_remove(self.button_press_sid)

        self.button.destroy()
        self.window.disconnect(self.state_changed_event)
        self.window.disconnect(self.icon_changed_event)
        self.window.disconnect(self.name_changed_event)
        if self.geometry_changed_event is not None:
            self.window.disconnect(self.geometry_changed_event)
        del self.screen
        del self.window
        del self.globals
        gc.collect()

    #### Previews

    def get_preview_alloc(self):
        return self.button.get_preview_allocation()


    #### Windows's Events
    def __on_window_state_changed(self, window,changed_mask, new_state):

        if WNCK_WINDOW_STATE_MINIMIZED & changed_mask & new_state:
            self.button.set_minimized(True)
            self.groupbutton_r().update_state_request()
        elif WNCK_WINDOW_STATE_MINIMIZED & changed_mask:
            self.button.set_minimized(False)
            self.groupbutton_r().update_state_request

        # Check if the window needs attention
        if window.needs_attention() != self.needs_attention:
            self.needs_attention = window.needs_attention()
            self.button.set_needs_attention(self.needs_attention)
            self.groupbutton_r().need_attention_changed()

    def __on_window_icon_changed(self, window):
        # Creates pixbufs for minimized and normal icons
        # from the window's mini icon and set the one that should
        # be used as window_button_icon according to window state.
        self.button.set_icon(window.get_mini_icon(), window.get_icon())

    def __on_window_name_changed(self, window):
        name = u""+window.get_name()
        self.button.set_name(name)


    def __on_geometry_changed(self, *args):
        monitor = self.get_monitor()
        if monitor != self.monitor:
            self.monitor = monitor
            self.groupbutton_r().window_monitor_changed()

    #### Opacify
    def opacify(self):
        self.xid = self.window.get_xid()
        self.opacify_obj.opacify(self.xid, self.xid)

    def deopacify(self):
        if self.deopacify_request_sid:
            gobject.source_remove(self.deopacify_request_sid)
            self.deopacify_request_sid = None
        if self.deopacify_sid:
            self.deopacify_sid = None
        self.opacify_obj.deopacify(self.xid)

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
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            self.opacify()
            # Just for safety in case no leave-signal is sent
            self.deopacify_request_sid = \
                            gobject.timeout_add(500, self.deopacify_request)
        return False

    def deopacify_request(self):
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            return True
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        self.deopacify_sid = gobject.timeout_add(110, self.deopacify)
        return False

    #### D'n'D
    def __on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.groupbutton_r().popup_expose_request()
            self.button_drag_entered = True
            self.dnd_select_window = \
                gobject.timeout_add(600, self.action_select_window)
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def __on_button_drag_leave(self, widget, drag_context, t):
        self.button_drag_entered = False
        gobject.source_remove(self.dnd_select_window)
        self.groupbutton_r().popup_expose_request()
        self.groupbutton_r().hide_list_dnd()


    #### Events
    def __on_button_mouse_enter(self, widget, event):
        # In compiz there is a enter and
        # a leave event before a button_press event.
        # Keep that in mind when coding this def!
        if self.button_pressed :
            return
        if self.globals.settings["opacify"]:
            self.opacify_request_sid = \
                gobject.timeout_add(100, self.opacify_request)

    def __on_button_mouse_leave(self, widget, event):
        # In compiz there is a enter and a leave
        # event before a button_press event.
        # Keep that in mind when coding this def!
        self.button_pressed = False
        if self.globals.settings["opacify"]:
            self.deopacify_request_sid = \
                            gobject.timeout_add(200, self.deopacify_request)

    def __on_window_button_press_event(self, widget,event):
        # In compiz there is a enter and a leave event before
        # a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.__on_button_mouse_enter
        # or self.__on_button_mouse_leave.
        self.button_pressed = True
        self.button_press_sid = \
                        gobject.timeout_add(600, self.__set_button_pressed_false)

    def __set_button_pressed_false(self):
        # Helper function for __on_window_button_press_event.
        self.button_pressed = False
        self.button_press_sid = None
        return False

    def __on_window_button_scroll_event(self, widget, event):
        if self.globals.settings["opacify"]:
            self.deopacify()
        if not event.direction in (gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_DOWN):
            return
        direction = {gtk.gdk.SCROLL_UP: "scroll_up",
                     gtk.gdk.SCROLL_DOWN: "scroll_down"}[event.direction]
        action = self.globals.settings["windowbutton_%s"%direction]
        self.action_function_dict[action](self, widget, event)
        if self.globals.settings["windowbutton_close_popup_on_%s"%direction]:
            self.groupbutton_r().hide_list()

    def __on_clicked(self, widget, event):
        if self.globals.settings["opacify"]:
            self.deopacify()

        if not event.button in (1, 2, 3):
            return
        button = {1:"left", 2: "middle", 3: "right"}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        action_str = "windowbutton_%s%s_click_action"%(mod, button)
        action = self.globals.settings[action_str]
        self.action_function_dict[action](self, widget, event)

        popup_close = "windowbutton_close_popup_on_%s%s_click"%(mod, button)
        if self.globals.settings[popup_close]:
            self.groupbutton_r().hide_list()

    def __on_close_clicked(self, *args):
        if self.globals.settings["opacify"]:
            self.deopacify()
        self.action_close_window()

    #### Menu functions
    def __menu_closed(self, menushell):
        self.globals.gtkmenu_showing = False
        self.groupbutton_r().hide_list()
        menushell.destroy()

    def __menu_minimize_window(self, widget=None, event=None):
        if self.window.is_minimized():
            self.window.unminimize(gtk.get_current_event_time())
        else:
            self.window.minimize()

    #### Actions
    def action_select_or_minimize_window(self, widget=None,
                                         event=None, minimize=True):
        # The window is activated, unless it is already
        # activated, then it's minimized. Minimized
        # windows are unminimized. The workspace
        # is switched if the window is on another
        # workspace.
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        if self.window.get_workspace() is not None \
        and self.screen.get_active_workspace() != self.window.get_workspace():
            self.window.get_workspace().activate(t)
        if not self.window.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.window.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),
                                      win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            # which means popup list can be left open.
            groupbutton = self.groupbutton_r
            if groupbutton.hide_list_sid is None:
                groupbutton.hide_list()
        if self.window.is_minimized():
            self.window.unminimize(t)
        elif self.window.is_active() and minimize:
            self.window.minimize()
        else:
            self.window.activate(t)
        # Deopacify is needed here since this function is called from
        # the group button class as well.
        self.deopacify()

    def action_select_window(self, widget = None, event = None):
        self.action_select_or_minimize_window(widget, event, False)

    def action_close_window(self, widget=None, event=None):
        self.window.close(gtk.get_current_event_time())

    def action_maximize_window(self, widget=None, event=None):
        if self.window.is_maximized():
            self.window.unmaximize()
        else:
            self.window.maximize()

    def action_shade_window(self, widget, event):
        self.window.shade()

    def action_unshade_window(self, widget, event):
        self.window.unshade()

    def action_show_menu(self, widget, event):
        #Creates a popup menu
        menu = gtk.Menu()
        menu.connect("selection-done", self.__menu_closed)
        #(Un)Minimize
        minimize_item = None
        if self.window.get_actions() & WNCK_WINDOW_ACTION_MINIMIZE \
        and not self.window.is_minimized():
            minimize_item = gtk.MenuItem(_("_Minimize"))
        elif self.window.get_actions() & WNCK_WINDOW_ACTION_UNMINIMIZE \
        and self.window.is_minimized():
            minimize_item = gtk.MenuItem(_("Un_minimize"))
        if minimize_item:
            menu.append(minimize_item)
            minimize_item.connect("activate", self.__menu_minimize_window)
            minimize_item.show()
        # (Un)Maximize
        maximize_item = None
        if not self.window.is_maximized() \
        and self.window.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
            maximize_item = gtk.MenuItem(_("Ma_ximize"))
        elif self.window.is_maximized() \
        and self.window.get_actions() & WNCK_WINDOW_ACTION_UNMINIMIZE:
            maximize_item = gtk.MenuItem(_("Unma_ximize"))
        if maximize_item:
            menu.append(maximize_item)
            maximize_item.connect("activate", self.action_maximize_window)
            maximize_item.show()
        # Close
        close_item = gtk.MenuItem(_("_Close"))
        menu.append(close_item)
        close_item.connect("activate", self.action_close_window)
        close_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.globals.gtkmenu_showing = True

    def action_none(self, widget = None, event = None):
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


