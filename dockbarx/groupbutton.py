#!/usr/bin/python

#   groupbutton.py
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


import pygtk
pygtk.require("2.0")
import gtk
import gobject
import gconf
import wnck
from time import time
from time import sleep
import os
import pango
from xml.sax.saxutils import escape
import weakref

from windowbutton import WindowButton
from iconfactory import IconFactory
from cairowidgets import CairoButton, CairoMenuItem
from cairowidgets import CairoPopup, CairoToggleMenu
from dockmanager import DockManagerItem
from common import *
import zg

import i18n
_ = i18n.language.gettext

ATOM_PREVIEWS = gtk.gdk.atom_intern("_KDE_WINDOW_PREVIEW")

try:
    WNCK_WINDOW_ACTION_MAXIMIZE = wnck.WINDOW_ACTION_MAXIMIZE
except:
    WNCK_WINDOW_ACTION_MAXIMIZE = 1 << 14

class WindowDict(ODict):
    def __init__(self, monitor=1, **kvargs):
        ODict.__init__(self, **kvargs)
        self.globals = Globals()
        self.monitor = monitor

    def get_list(self):
        # Returns a list of windows that are in current use
        wins = []
        for win in self:
            if self.globals.settings["show_only_current_desktop"] and \
               not self[win].is_on_current_desktop():
                continue
            if self.globals.settings["show_only_current_monitor"] and \
               self.monitor != self[win].monitor:
                continue
            wins.append(win)
        return wins

    def get_unminimized(self):
        return [win for win in self.get_list() if not win.is_minimized()]

    def get_minimized(self):
        return [win for win in self.get_list() if win.is_minimized()]

    def get_count(self):
        return len(self.get_list())

    def get_minimized_count(self):
        return len(self.get_minimized())

    def get_unminimized_count(self):
        return len(self.get_unminimized())

class GroupButton():
    """
    Group button takes care of a program's "button" in dockbar.

    It also takes care of the popup window and all the window buttons that
    populates it.
    """

    def __init__(self, dockbar, identifier=None, desktop_entry=None,
                 pinned=False, monitor=0):
        self.dockbar_r = weakref.ref(dockbar)

        self.globals = Globals()
        connect(self.globals, "show-only-current-desktop-changed",
                self.__on_show_only_current_desktop_changed)
        connect(self.globals, "color2-changed", self.__update_popup_label)
        connect(self.globals, "show-previews-changed",
                self.__on_show_previews_changed)
        connect(self.globals, "show-tooltip-changed",
                self.__update_tooltip)
        self.opacify_obj = Opacify()
        self.pinned = pinned
        self.desktop_entry = desktop_entry
        self.monitor = monitor
        self.identifier = identifier
        if identifier is None and desktop_entry is None:
            raise Exception, \
                "Can't initiate Group button without identifier or launcher."



        # Variables
        self.has_active_window = False
        self.needs_attention = False
        self.attention_effect_running = False
        self.nextlist = None
        self.nextlist_time = None
        self.mouse_over = False
        self.pressed = False
        self.lastlaunch = None
        self.launch_effect = False
        self.hide_list_sid = None
        self.show_list_sid = None
        self.opacify_request_sid = None
        self.deopacify_request_sid = None
        self.opacified = False
        self.scrollpeak_sid = None
        self.scrollpeak_wb = None
        self.launch_sid = None
        self.menu_is_shown = False
        self.menu = None
        self.media_buttons = None
        self.launch_program_item = None
        self.window_connects = []

        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.windows = WindowDict(self.monitor)
        mgeo = gtk.gdk.screen_get_default().get_monitor_geometry(self.monitor)
        self.monitor_aspect_ratio = float(mgeo.width) / mgeo.height


        #--- Button
        self.icon_factory = IconFactory(identifier=self.identifier,
                                        desktop_entry=self.desktop_entry)
        self.button = CairoButton()
        self.button.show_all()



        # Button events
        connect(self.button, "enter-notify-event", self.__on_button_mouse_enter)
        connect(self.button, "leave-notify-event", self.__on_button_mouse_leave)
        connect(self.button, "button-release-event",
                self.__on_group_button_release_event)
        connect(self.button, "button-press-event",
                self.__on_group_button_press_event)
        connect(self.button, "scroll-event", self.__on_group_button_scroll_event)
        connect(self.button, "size-allocate", self.__on_sizealloc)
        self.button_old_alloc = self.button.get_allocation()


        #--- Popup window
        self.popup = CairoPopup()
        self.popup_showing = False
        connect(self.popup, "leave-notify-event",self.__on_popup_mouse_leave)
        connect_after(self.popup, "size-allocate", self.__on_popup_size_allocate)

        self.popup_box = gtk.VBox()
        self.popup_box.set_border_width(0)
        self.popup_box.set_spacing(2)
        self.winbox = gtk.Alignment(0.5, 0.5, 1, 1)
        self.popup_label = gtk.Label()
        self.popup_label.set_use_markup(True)
        self.update_name()
        if self.identifier:
            self.popup_label.set_tooltip_text(
                                    "%s: %s"%(_("Identifier"),self.identifier))
        self.popup_box.pack_start(self.popup_label, False)
        self.popup_box.pack_start(self.winbox)
        # Initiate the windowlist
        self.winlist = None
        self.set_show_previews(self.globals.settings["preview"])
        self.popup.add(self.popup_box)



        #--- D'n'D
        # Drag and drop should handel buttons that are moved,
        # launchers that is dropped, and open popup window
        # to enable drag and drops to windows that has to be
        # raised.
        self.button.drag_dest_set(0, [], 0)
        connect(self.button, "drag_motion", self.__on_button_drag_motion)
        connect(self.button, "drag_leave", self.__on_button_drag_leave)
        connect(self.button, "drag_drop", self.__on_drag_drop)
        connect(self.button, "drag_data_received", self.__on_drag_data_received)
        self.button_drag_entered = False
        self.launcher_drag = False
        self.dnd_show_popup = None
        self.dnd_select_window = None
        self.dd_uri = None

        # The popup needs to have a drag_dest just to check
        # if the mouse is howering it during a drag-drop.
        self.popup.drag_dest_set(0, [], 0)
        connect(self.popup, "drag_motion", self.__on_popup_drag_motion)
        connect(self.popup, "drag_leave", self.__on_popup_drag_leave)

        #Make buttons drag-able
        self.button.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                    [("text/groupbutton_name", 0, 47593)],
                                    gtk.gdk.ACTION_MOVE)
        self.button.drag_source_set_icon_pixbuf(self.icon_factory.get_icon(32))
        connect(self.button, "drag_begin", self.__on_drag_begin)
        connect(self.button, "drag_data_get", self.__on_drag_data_get)
        connect(self.button, "drag_end", self.__on_drag_end)
        self.is_current_drag_source = False

        #--- Dockmanager
        try:
            self.dockmanager = DockManagerItem(self)
        except:
            raise
            self.dockmanager = None


    def set_identifier(self, identifier):
        if self.identifier == get_opacifier():
            set_opacifier(identifier)
        self.identifier = identifier
        self.popup_label.set_tooltip_text(
                                "%s: %s"%(_("Identifier"), self.identifier))

    def update_name(self):
        self.name = None
        if self.desktop_entry:
            try:
                self.name = self.desktop_entry.getName()
            except:
                pass
        if self.name is None and self.windows:
            # Uses first half of the name,
            # like "Amarok" from "Amarok - [SONGNAME]"
            # A program that uses a name like "[DOCUMENT] - [APPNAME]" would be
            # totally screwed up. So far no such program has been reported.
            self.name = self.windows.keys()[0].get_class_group().get_name()
            self.name = self.name.split(" - ", 1)[0]
        if self.name is None and self.identifier:
            self.name = self.identifier
        if self.name is None:
            return
        self.popup_label.set_label(
                    "<span foreground='%s'>"%self.globals.colors["color2"] + \
                    "<big><b>%s</b></big></span>"%escape(self.name))
        self.__update_tooltip()

    def set_show_previews(self, show_previews):
        if show_previews:
            mgeo = gtk.gdk.screen_get_default().get_monitor_geometry(
                                                                self.monitor)
            if self.globals.orient == "h":
                width = 10
                for win in self.windows.get_list():
                    wb = self.windows[win]
                    width += max(190, wb.button.set_preview_aspect(
                                                 win.get_geometry()[2],
                                                 win.get_geometry()[3],
                                                 self.monitor_aspect_ratio)[0])
                    width += 16
                if width > mgeo.width:
                    show_previews = False
            else:
                height = 12 + self.popup_label.size_request()[1]
                for win in self.windows.get_list():
                    wb = self.windows[win]
                    height += wb.button.set_preview_aspect(
                                                 win.get_geometry()[2],
                                                 win.get_geometry()[3],
                                                 self.monitor_aspect_ratio)[1]
                    height += 24 + wb.button.label.size_request()[1]
                if height > mgeo.height:
                    show_previews = False
        self.show_previews = show_previews
        oldbox = self.winlist
        if show_previews and self.globals.orient == "h":
            self.winlist = gtk.HBox()
            self.winlist.set_spacing(4)
        else:
            self.winlist = gtk.VBox()
            self.winlist.set_spacing(2)
        if oldbox:
            for c in oldbox.get_children():
                oldbox.remove(c)
                self.winlist.pack_start(c, True, True)
            self.winbox.remove(oldbox)
        self.winbox.add(self.winlist)
        self.winlist.show()
        for win in self.windows.get_list():
            self.windows[win].button.set_show_preview(show_previews)

    def dockbar_moved(self, arg=None):
        self.__set_icongeo()

    def desktop_changed(self):
        self.update_state()
        self.__set_icongeo()
        self.nextlist = None

    def launch_item(self, button, event, uri):
        self.desktop_entry.launch(uri)
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000,
                                                self.__remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000,
                                                self.__remove_launch_effect)

    def remove(self):
        # Remove group button.
        if self.media_buttons:
            self.remove_media_buttons()
        if self.launch_sid:
            gobject.source_remove(self.launch_sid)
            self.launch_sid = None
        if self.scrollpeak_sid is not None:
            gobject.source_remove(self.scrollpeak_sid)
        if self.show_list_sid is not None:
            gobject.source_remove(self.show_list_sid)
            self.show_list_sid = None
        if self.hide_list_sid is not None:
            gobject.source_remove(self.hide_list_sid)
            self.hide_list_sid = None
        if self.deopacify_request_sid is not None:
            self.deopacify()
            gobject.source_remove(self.deopacify_request_sid)
            self.opacify_request_sid = None
        if self.opacify_request_sid is not None:
            gobject.source_remove(self.opacify_request_sid)
            self.opacify_request_sid = None
        if self.launch_program_item:
            self.launch_program_item.destroy()
        if self.popup:
            disconnect(self.popup)
            self.popup.destroy()
        if self.button:
            disconnect(self.button)
            self.button.cleanup()
            self.button.destroy()
        if self.menu:
            disconnect(self.menu)
        self.hide_list()
        self.icon_factory.remove()
        del self.icon_factory
        self.popup_box.destroy()
        self.popup_label.destroy()
        self.winlist.destroy()

    #### State
    def __update_popup_label(self, arg=None):
        if self.name is None:
            return
        self.popup_label.set_text(
                    "<span foreground='%s'>"%self.globals.colors["color2"] + \
                    "<big><b>%s</b></big></span>"%self.name
                                 )
        self.popup_label.set_use_markup(True)

    def update_state(self):
        # Checks button state and set the icon accordingly.
        win_nr = min(self.windows.get_count(), 15)
        if win_nr == 0 and not self.pinned:
            self.button.hide()
            return
        else:
            self.button.show()


        self.state_type = 0
        mwc = self.windows.get_minimized_count()
        if self.pinned and win_nr == 0:
            self.state_type = self.state_type | IconFactory.LAUNCHER
        elif (win_nr - mwc) <= 0:
            self.state_type = self.state_type | IconFactory.ALL_MINIMIZED
        elif mwc > 0:
            self.state_type = self.state_type | IconFactory.SOME_MINIMIZED

        if self.has_active_window and win_nr > 0:
            self.state_type = self.state_type | IconFactory.ACTIVE

        if self.needs_attention and win_nr > 0:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if  gant == "red":
                self.state_type = self.state_type | IconFactory.NEEDS_ATTENTION
            elif gant != "nothing":
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    gobject.timeout_add(700, self.__attention_effect)

        if self.pressed:
            self.state_type = self.state_type | IconFactory.MOUSE_BUTTON_DOWN

        if self.mouse_over or \
           (self.button_drag_entered and not self.launcher_drag):
            self.state_type = self.state_type | IconFactory.MOUSE_OVER

        if self.launch_effect:
            self.state_type = self.state_type | IconFactory.LAUNCH_EFFECT

        if self.launcher_drag:
            self.state_type = self.state_type | IconFactory.DRAG_DROPP

        # Add the number of windows
        self.state_type = self.state_type | win_nr
        surface = self.icon_factory.surface_update(self.state_type)

        # Set the button size to the size of the surface
        if self.button.allocation.width != surface.get_width() or \
           self.button.allocation.height != surface.get_height():
            self.button.set_size_request(
                                    surface.get_width(), surface.get_height())
        self.button.update(surface)
        return

    def update_state_request(self, *args):
        #Update state if the button is shown.
        a = self.button.get_allocation()
        if a.width>10 and a.height>10:
            self.update_state()

    def __attention_effect(self):
        self.attention_effect_running = True
        if self.needs_attention:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if gant == "compwater":
                x,y = self.button.window.get_origin()
                alloc = self.button.get_allocation()
                x = x + alloc.x + alloc.width/2
                y = y + alloc.y + alloc.height/2
                try:
                    compiz_call_async("water/allscreens/point", "activate",
                                "root", self.root_xid, "x", x, "y", y)
                except:
                    pass
            elif gant == "blink":
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    surface = self.icon_factory.surface_update(
                                        IconFactory.BLINK | self.state_type)
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

    def __on_show_only_current_desktop_changed(self, arg):
        self.update_state()
        self.nextlist = None
        self.__set_icongeo()

    def __on_show_previews_changed(self, arg=None):
        self.set_show_previews(self.globals.settings["preview"])

    def __set_icongeo(self, arg=None):
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] and \
               not self.windows[win].is_on_current_desktop():
                # Todo: Fix this for multiple dockbarx:s
                win.set_icon_geometry(0, 0, 0, 0)
                continue
            if self.globals.settings["show_only_current_desktop"] and \
               self.windows[win].monitor != self.monitor:
                continue
            alloc = self.button.get_allocation()
            if self.button.window:
                x,y = self.button.window.get_origin()
                x += alloc.x
                y += alloc.y
                win.set_icon_geometry(x, y, alloc.width, alloc.height)

    def __remove_launch_effect(self):
        self.launch_effect = False
        self.update_state()
        return False

    def __update_tooltip(self, arg=None):
        if self.globals.settings["groupbutton_show_tooltip"] and \
           self.windows.get_count() == 0 and \
           (self.globals.settings["no_popup_for_one_window"] \
            or not self.media_buttons):
            try:
                comment = self.desktop_entry.getComment()
            except:
                comment = None
            if comment:
                text = "\n".join((self.name, comment))
            else:
                text = self.name
            self.button.set_tooltip_text(text)
        else:
            self.button.set_has_tooltip(False)

    #### Window handling
    def add_window(self,window):
        if window in self.windows:
            return
        wb = WindowButton(self, window)
        self.windows[window] = wb
        wb.button.set_show_preview(self.show_previews)
        self.winlist.pack_start(wb.button, True, True)
        if len(self.windows)==1:
            if self.name is None:
                self.update_name()
            self.icon_factory.set_class_group(window.get_class_group())
        if self.launch_effect:
            self.launch_effect = False
            gobject.source_remove(self.launch_effect_timeout)
        if window.needs_attention():
            self.needs_attention_changed(state_update=False)

        # Update state unless the button hasn't been shown yet.
        self.update_state_request()

        #Update popup-list if it is being shown.
        if self.popup_showing:
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if (self.globals.settings["show_only_current_desktop"] and \
                   not win.is_on_current_desktop()) or \
                   (self.globals.settings["show_only_current_monitor"] and \
                   self.monitor != win.monitor):
                    win.button.hide_all()
                else:
                    win.button.show_all()
            gobject.idle_add(self.show_list)

        self.__update_tooltip()

        # Set minimize animation
        # (if the eventbox is created already,
        # otherwice the icon animation is set in sizealloc())
        if self.button.window:
            x, y = self.button.window.get_origin()
            a = self.button.get_allocation()
            x += a.x
            y += a.y
            window.set_icon_geometry(x, y, a.width, a.height)

        if self.launch_sid:
            gobject.source_remove(self.launch_sid)
            self.launch_sid = None

    def del_window(self, window):
        if self.nextlist and window in self.nextlist:
            self.nextlist.remove(window)
        self.winlist.remove(self.windows[window].button)
        self.windows[window].del_button()
        del self.windows[window]
        if self.needs_attention:
            self.needs_attention_changed(state_update=False)
        if self.pinned or self.windows:
            self.set_show_previews(self.globals.settings["preview"])
            self.update_state_request()
            self.__update_tooltip()
        if self.windows.get_unminimized_count() == 0:
            if self.opacified:
                self.deopacify()
        if self.popup_showing:
            if self.windows.get_count() > 0:
                self.popup.resize(10, 10)
            else:
                self.hide_list()

    def set_has_active_window(self, mode):
        if mode != self.has_active_window:
            self.has_active_window = mode
            if mode == False:
                for window_button in self.windows.values():
                    window_button.set_button_active(False)
            self.update_state_request()

    def needs_attention_changed(self, arg=None, state_update=True):
        # Checks if there are any urgent windows and changes
        # the group button looks if there are at least one
        for window in self.windows:
            if window.needs_attention():
                self.needs_attention = True
                break
        else:
            self.needs_attention = False
        # Update state unless the button hasn't been shown yet.
        if state_update:
            self.update_state_request()

    def window_monitor_changed(self):
        self.update_state_request()
        self.on_set_geo_grp()
        #Update popup-list if it is being shown.
        if self.popup_showing:
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if (self.globals.settings["show_only_current_desktop"] and \
                   not win.is_on_current_desktop()) or \
                   (self.globals.settings["show_only_current_monitor"] and \
                   self.monitor != win.monitor):
                    win.button.hide_all()
                else:
                    win.button.show_all()
            gobject.idle_add(self.show_list_request)




    #### Show/hide list
    def show_list_request(self):
        # If mouse cursor is over the button, show popup window.
        if self.popup_showing or \
           (self.button.pointer_is_inside() and \
            not self.globals.gtkmenu_showing and \
            not self.globals.dragging):
            self.show_list()
        return False

    def show_list(self):
        if self.globals.gtkmenu_showing:
            return
        win_cnt = self.windows.get_count()
        if win_cnt == 0 and not self.media_buttons and not self.menu_is_shown:
            self.hide_list()
            return
        if self.globals.settings["preview"]:
            # Set hint type so that previews can be used.
            if not self.popup.get_property("visible"):
                self.popup.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_MENU)
        else:
            if not self.popup.get_property("visible"):
                self.popup.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)

        self.popup_box.show()
        self.winbox.show()
        self.winlist.show()
        self.popup_label.show()
        for window, wb in self.windows.items():
            if (self.globals.settings["show_only_current_desktop"] and \
               not wb.is_on_current_desktop()) or \
               (self.globals.settings["show_only_current_monitor"] and \
               self.monitor != wb.monitor):
                wb.button.hide()
            else:
                wb.button.show()
        self.popup.show()
        self.popup_showing = True

        # Hide other popup if open.
        if self.globals.gb_showing_popup is not None and \
           self.globals.gb_showing_popup != self:
            self.globals.gb_showing_popup.hide_list()
        self.globals.gb_showing_popup = self

        self.__set_previews()
        self.popup.resize(10,10)
        return False

    def hide_list_request(self):
        if self.popup.window is None:
            # Popup isn't shown.
            return
        display = gtk.gdk.display_get_default()
        pos = display.get_pointer()
        button_list = gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON2_MASK | \
                      gtk.gdk.BUTTON3_MASK | gtk.gdk.BUTTON4_MASK | \
                      gtk.gdk.BUTTON5_MASK
        if not pos[3] & button_list and time() - self.hide_time < 0.6:
            # No mouse button is pressed and less than 600 ms has passed.
            # Check again in 10 ms.
            gobject.timeout_add(10, self.hide_list_request)
            return
        if self.popup.pointer_is_inside() or self.button.pointer_is_inside():
            return
        self.hide_list()
        return

    def hide_list(self):
        if self.globals.gtkmenu_showing:
            return
        if self.popup.window:
            self.popup.window.property_change(ATOM_PREVIEWS,
                                              ATOM_PREVIEWS,
                                              32,
                                              gtk.gdk.PROP_MODE_REPLACE,
                                              [0,5,0,0,0,0,0])
        self.popup.hide()
        self.popup_showing = False
        if self.show_list_sid is not None:
            gobject.source_remove(self.show_list_sid)
            self.show_list_sid = None
        if self.hide_list_sid is not None:
            gobject.source_remove(self.hide_list_sid)
            self.hide_list_sid = None
        if self.globals.gb_showing_popup == self:
            self.globals.gb_showing_popup = None
        if self.menu is not None:
            self.menu.delete_menu()
            self.menu = None
        popup_child = self.popup.alignment.get_child()
        if popup_child:
            self.popup.remove(popup_child)
        self.popup.add(self.popup_box)
        self.menu_is_shown = False

    def popup_expose_request(self):
        event = gtk.gdk.Event(gtk.gdk.EXPOSE)
        event.window = self.popup.window
        event.area = self.popup.get_allocation()
        self.popup.send_expose(event)

    def hide_list_dnd(self, arg=None):
        self.hide_time = time()
        self.hide_list_request()

    def __on_popup_size_allocate(self, widget, allocation):
        # Move popup to it's right spot
        offset = -7
        wx, wy = self.button.window.get_origin()
        b_alloc = self.button.get_allocation()
        width, height = self.popup.get_size()
        mgeo = gtk.gdk.screen_get_default().get_monitor_geometry(self.monitor)
        if self.globals.orient == "h":
            if width > mgeo.width and self.show_previews:
                self.set_show_previews(False)
                gobject.idle_add(self.popup.resize, 10, 10)
                return
            if self.globals.settings["popup_align"] == "left":
                x = b_alloc.x + wx
            if self.globals.settings["popup_align"] == "center":
                x = b_alloc.x + wx + (b_alloc.width / 2) - (width / 2)
            if self.globals.settings["popup_align"] == "right":
                x = b_alloc.x + wx + b_alloc.width - width
            y = b_alloc.y + wy - offset
            # Check that the popup is within the monitor
            if x + width > mgeo.x + mgeo.width:
                x = mgeo.x + mgeo.width - width
            if x < mgeo.x:
                x = mgeo.x
            if y >= mgeo.y + (mgeo.height / 2):
                direction = "down"
                y = y - height
            else:
                direction = "up"
                y = y + b_alloc.height + (offset * 2)
            p = wx + b_alloc.x + (b_alloc.width / 2) - x
        else:
            if height > mgeo.height and self.show_previews:
                self.set_show_previews(False)
                gobject.idle_add(self.popup.resize, 10, 10)
                return
            # Set position in such a way that the arrow is splits the
            # height at golden ratio...
            y = b_alloc.y + wy + (b_alloc.height / 2) - int(height * 0.382)
            # ..but don't allow the popup to be lower than the upper egde of
            # the button.
            if y > b_alloc.y + wy:
                y = b_alloc.y + wy
            # Check that the popup is within the monitor
            if y + height > mgeo.y + mgeo.height:
                y = mgeo.y + mgeo.height - height
            if y < mgeo.y:
                y = mgeo.y
            x = b_alloc.x + wx
            if x >= mgeo.x + (mgeo.width / 2):
                direction = "right"
                x = x - width - offset
            else:
                direction = "left"
                x = x + b_alloc.width + offset
            p = wy + b_alloc.y + (b_alloc.height / 2) - y
        self.popup.point(direction, p)
        self.popup.move(x, y)

    def __set_previews(self):
        for win in self.windows.get_list():
            wb = self.windows[win]
            wb.button.set_preview_aspect(win.get_geometry()[2],
                                         win.get_geometry()[3],
                                         self.monitor_aspect_ratio)
        # The popup must be shown before the
        # preview can be set. Iterate gtk events.
        while gtk.events_pending():
                gtk.main_iteration(False)
        # Tell the compiz/kwin where to put the previews.
        if self.show_previews and not self.menu_is_shown and \
           self.windows.get_count() > 0:
            previews = []
            previews.append(self.windows.get_count())
            for win in self.windows.get_list():
                wb = self.windows[win]
                previews.append(5)
                previews.append(win.get_xid())
                (x, y, w, h) = wb.get_preview_alloc()
                previews.append(x)
                previews.append(y)
                previews.append(w)
                previews.append(h)
                # The button needs to be drawn again to ensure that
                # the preview is shown correctly.
                # Todo: Make sure if this is the best solution!
                #       What is the connection between redrawing and previews?
                wb.button.redraw()
        else:
            previews = [0,5,0,0,0,0,0]
        if self.popup.window:
            self.popup.window.property_change(ATOM_PREVIEWS,
                                              ATOM_PREVIEWS,
                                              32,
                                              gtk.gdk.PROP_MODE_REPLACE,
                                              previews)

    def show_launch_popup(self):
        if self.popup.window:
            self.popup.window.property_change(ATOM_PREVIEWS,
                                              ATOM_PREVIEWS,
                                              32,
                                              gtk.gdk.PROP_MODE_REPLACE,
                                              [0,5,0,0,0,0,0])
        self.menu_is_shown = False
        menu = gtk.VBox()
        menu.set_spacing(2)
        #Launch program item
        if not self.launch_program_item:
            self.launch_program_item = CairoMenuItem(_("_Launch application"))
            self.launch_program_item.connect("clicked",
                                self.action_launch_application)
            self.launch_program_item.show()
        menu.pack_start(self.launch_program_item)
        popup_child = self.popup.alignment.get_child()
        if popup_child:
            self.popup.remove(popup_child)
        self.popup.add(menu)
        menu.show()
        self.popup.show()
        self.popup.resize(10,10)
        # Hide other popup if open.
        if self.globals.gb_showing_popup is not None and \
           self.globals.gb_showing_popup != self:
            self.globals.gb_showing_popup.hide_list()
        self.globals.gb_showing_popup = self

    #### Opacify
    def opacify(self):
        xids = [window.get_xid() for window in self.windows]
        opacify(xids, self.identifier)
        self.opacified = True

    def deopacify(self):
        if self.opacify_request_sid is not None:
            gobject.source_remove(self.opacify_request_sid)
            self.opacify_request_sid = None
        deopacify(self.identifier)

    def opacify_request(self):
        if self.windows.get_unminimized_count() > 0 and \
           self.button.pointer_is_inside():
            self.opacify()
            # This is a safety check to make sure that opacify won't stay on
            # forever when it shouldn't be.
            self.deopacify_request_sid = gobject.timeout_add(500,
                                                        self.deopacify_request)
        self.opacify_request_sid = None

    def deopacify_request(self):
        # Make sure that mouse cursor really has left the window button.
        if self.button.pointer_is_inside():
            return True
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        self.deopacify_request_sid = \
            gobject.timeout_add(110, self.deopacify)


    #### Media Buttons
    def add_media_buttons(self, media_buttons):
        if self.media_buttons:
            self.remove_media_buttons()
        self.media_buttons = media_buttons
        self.popup_box.pack_start(self.media_buttons)
        self.media_buttons.show()
        self.__update_tooltip()

    def remove_media_buttons(self):
        if self.media_buttons:
            self.popup_box.remove(self.media_buttons)
            self.media_buttons = None
            self.__update_tooltip()

    #### DockManager
    def get_dm_path(self, match=None):
        if self.dockmanager is None:
            return None
        return self.dockmanager.get_path()

    def get_dm_path_by_name(self, name):
        if self.dockmanager is None:
            return None
        if name == self.identifier:
            return self.dockmanager.get_path()

    def get_dm_path_by_desktop_file(self, name):
        if self.dockmanager is None:
            return None
        df_name = self.desktop_entry.getFileName().rsplit('/')[-1]
        if name == df_name:
            return self.dockmanager.get_path()

    def get_dm_path_by_pid(self, pid):
        if self.dockmanager is None:
            return None
        pids = [window.get_pid() for window in self.windows]
        if pid in pids:
            return self.dockmanager.get_path()

    def get_dm_path_by_xid(self, xid):
        if self.dockmanager is None:
            return None
        xids = [window.get_xid() for window in self.windows]
        if xid in xids:
            return self.dockmanager.get_path()

    def get_desktop_entry_file_name(self):
        if self.desktop_entry:
            file_name = self.desktop_entry.getFileName()
        else:
            file_name = ''
        return file_name

    #### DnD (source)
    def __on_drag_begin(self, widget, drag_context):
        self.is_current_drag_source = True
        self.globals.dragging = True
        self.hide_list()

    def __on_drag_data_get(self, widget, context,
                         selection, targetType, eventTime):
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        selection.set(selection.target, 8, name)


    def __on_drag_end(self, widget, drag_context, result = None):
        self.is_current_drag_source = False
        # A delay is needed to make sure the button is
        # shown after on_drag_end has hidden it and
        # not the other way around.
        gobject.timeout_add(30, self.button.show)

    #### DnD (target)
    def __on_drag_drop(self, wid, drag_context, x, y, t):
        if "text/groupbutton_name" in drag_context.targets:
            self.button.drag_get_data(drag_context, "text/groupbutton_name", t)
            drag_context.finish(True, False, t)
        elif "text/uri-list" in drag_context.targets:
            #Drag data should already be stored in self.dd_uri
            if ".desktop" in self.dd_uri:
                # .desktop file! This is a potential launcher.
                if self.identifier:
                    name = self.identifier
                else:
                    name = self.desktop_entry.getFileName()
                #remove "file://" and "/n" from the URI
                path = self.dd_uri[7:-2]
                path = path.replace("%20"," ")
                self.dockbar_r().launcher_dropped(path, name)
            else:
                uri = self.dd_uri
                # Remove the new line at the end
                uri = uri.rstrip()
                self.launch_item(None, None, uri)
            drag_context.finish(True, False, t)
        else:
            drag_context.finish(False, False, t)
        self.dd_uri = None
        return True

    def __on_drag_data_received(self, wid, context,
                              x, y, selection, targetType, t):
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        if selection.target == "text/groupbutton_name":
            if selection.data != name:
                self.dockbar_r().groupbutton_moved(selection.data, name)
        elif selection.target == "text/uri-list":
            # Uri lists are tested on first motion instead on drop
            # to check if it's a launcher.
            # The data is saved in self.dd_uri to be used again
            # if the file is dropped.
            self.dd_uri = selection.data
            if ".desktop" in selection.data:
                # .desktop file! This is a potential launcher.
                self.launcher_drag = True
            self.update_state()

    def __on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.button_drag_entered = True
            if not "text/groupbutton_name" in drag_context.targets:
                win_nr = self.windows.get_count()
                if win_nr == 1:
                    self.dnd_select_window = gobject.timeout_add(600,
                                self.windows.values()[0].action_select_window)
                elif win_nr > 1:
                    self.dnd_show_popup = gobject.timeout_add(
                        self.globals.settings["popup_delay"], self.show_list)
            if "text/groupbutton_name" in drag_context.targets \
            and not self.is_current_drag_source:
                self.launcher_drag = True
                self.update_state()
            elif "text/uri-list" in drag_context.targets:
                # We have to get the data to find out if this
                # is a launcher or something else.
                self.button.drag_get_data(drag_context, "text/uri-list", t)
                # No update_state() here!
            else:
                self.update_state()
        if "text/groupbutton_name" in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_MOVE, t)
        elif "text/uri-list" in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_COPY, t)
        else:
            drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def __on_button_drag_leave(self, widget, drag_context, t):
        self.launcher_drag = False
        self.button_drag_entered = False
        self.update_state()
        self.hide_time = time()
        gobject.timeout_add(100, self.hide_list_request)
        if self.dnd_show_popup is not None:
            gobject.source_remove(self.dnd_show_popup)
            self.dnd_show_popup = None
        if self.dnd_select_window is not None:
            gobject.source_remove(self.dnd_select_window)
            self.dnd_select_window = None
        if self.is_current_drag_source:
            # If drag leave signal is given because of a drop,
            # a small delay is needed since
            # drag-end isn't called if
            # the destination is hidden just before
            # the drop is completed.
            gobject.timeout_add(20, self.button.hide)

    def __on_popup_drag_motion(self, widget, drag_context, x, y, t):
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def __on_popup_drag_leave(self, widget, drag_context, t):
        self.hide_time = time()
        gobject.timeout_add(100, self.hide_list_request)


    #### Events
    def __on_sizealloc(self, button, allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        if self.button_old_alloc != self.button.get_allocation():
            if self.globals.orient == "v" \
            and allocation.width > 10 and allocation.width < 220 \
            and allocation.width != self.button_old_alloc.width:
                # A minimium size on 11 is set to stop unnecessary calls
                # work when the button is created
                self.icon_factory.set_size(allocation.width)
                self.update_state()
            elif self.globals.orient == "h" \
            and allocation.height>10 and allocation.height<220\
            and allocation.height != self.button_old_alloc.height:
                self.icon_factory.set_size(allocation.height)
                self.update_state()
            self.button_old_alloc = allocation

            # Update icon geometry
            self.__set_icongeo()

    def __on_button_mouse_enter (self, widget, event):
        if self.mouse_over:
            # False mouse enter event. Probably because a mouse button has been
            # pressed (compiz bug).
            return
        self.mouse_over = True
        self.update_state()
        win_cnt = self.windows.get_count()
        if win_cnt <= 1 and \
           self.globals.settings["no_popup_for_one_window"]:
            return
        if  win_cnt == 0 and not self.media_buttons:
            return

        if self.globals.gb_showing_popup is None:
            delay = self.globals.settings["popup_delay"]
        else:
            delay = self.globals.settings["second_popup_delay"]
        # Opacify
        if self.globals.settings["opacify"] and \
           self.globals.settings["opacify_group"]:
            self.opacify_request_sid = gobject.timeout_add(delay,
                                                          self.opacify_request)

        # Prepare for popup window
        if not self.globals.gtkmenu_showing and not self.globals.dragging:
            self.show_list_sid = gobject.timeout_add(delay,
                                                     self.show_list_request)


    def __on_button_mouse_leave (self, widget, event):
        if self.button.pointer_is_inside():
            # False mouse_leave event, the cursor might be on a screen edge
            # or the mouse has been clicked (compiz bug).
            # A timeout is set so that the real mouse leave won't be missed.
            gobject.timeout_add(50,
                                self.__on_button_mouse_leave, widget, event)
            return
        self.mouse_over = False
        self.pressed = False
        self.update_state()
        self.hide_time = time()
        self.hide_list_request()
        if self.globals.settings["opacify"] \
        and self.globals.settings["opacify_group"]:
            gobject.timeout_add(100, self.deopacify_request)
        if not self.globals.settings["select_next_activate_immediately"] and \
           self.scrollpeak_sid is not None:
            self.scrollpeak_select()

    def __on_popup_mouse_leave(self,widget,event):
        self.hide_time = time()
        self.hide_list_request()

    def __on_group_button_scroll_event(self,widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = self.globals.settings["groupbutton_scroll_up"]
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = self.globals.settings["groupbutton_scroll_down"]
            self.action_function_dict[action](self, widget, event)

    def __on_group_button_release_event(self, widget, event):
        self.pressed = False
        self.update_state()
        # If a drag and drop just finnished set self.draggin to false
        # so that left clicking works normally again
        if event.button == 1 and self.globals.dragging:
            self.globals.dragging = False
            return

        if not self.button.pointer_is_inside():
            return

        if not event.button in (1, 2, 3):
            return
        button = {1:"left", 2: "middle", 3: "right"}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        if not self.globals.settings[
                                "groupbutton_%s%s_click_double"%(mod, button)]:
            # No double click required, go ahead and do the action.
            action = self.globals.settings[
                                "groupbutton_%s%s_click_action"%(mod, button)]
            self.action_function_dict[action](self, widget, event)


    def __on_group_button_press_event(self,widget,event):
        if not event.button in (1, 2, 3):
            return True
        button = {1:"left", 2: "middle", 3: "right"}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        if event.type == gtk.gdk._2BUTTON_PRESS:
            if self.globals.settings["groupbutton_%s%s_click_double"%(mod,
                                                                      button)]:
                # This is a double click and the
                # action requires a double click.
                # Go ahead and do the action.
                action = self.globals.settings[
                                "groupbutton_%s%s_click_action"%(mod, button)]
                self.action_function_dict[action](self, widget, event)

        elif event.button == 1:
            self.pressed = True
            self.update_state()
            # Return False so that a drag-and-drop can be initiated if needed.
            return False
        return True


    #### Menu
    def menu_show(self, event=None):
        if self.globals.gtkmenu_showing:
            return
        if self.menu is not None:
            self.menu.delete_menu()
            self.menu = None
        if self.menu_is_shown and not self.globals.settings["old_menu"]:
            # The menu is already shown, show the window list instead.
            self.menu_is_shown = False
            popup_child = self.popup.alignment.get_child()
            if popup_child:
                self.popup.remove(popup_child)
            self.popup.add(self.popup_box)
            self.show_list()
            return
        if self.globals.settings["old_menu"]:
            self.hide_list()
        else:
            self.menu_is_shown = True
            if self.popup.window:
                self.popup.window.property_change(ATOM_PREVIEWS,
                                                  ATOM_PREVIEWS,
                                                  32,
                                                  gtk.gdk.PROP_MODE_REPLACE,
                                                  [0,5,0,0,0,0,0])
        # Build menu
        self.menu = GroupMenu(self.globals.settings["old_menu"])
        # Launcher stuff
        if self.desktop_entry:
            self.menu.add_item(_("_Launch application"))
        if self.desktop_entry and not self.pinned:
            self.menu.add_item(_("_Pin application"))
        if not self.pinned:
            self.menu.add_item(_("Make custom launcher"))
        if self.pinned:
            self.menu.add_item(_("Unpin application"))
            self.menu.add_submenu(_("Properties"))
            self.menu.add_item(_("Edit Identifier"), _("Properties"))
            self.menu.add_item(_("Edit Launcher"), _("Properties"))
        # DockManager
        dm_menu_items = self.dockmanager.get_menu_items()
        if dm_menu_items:
            self.menu.add_separator()
        for item in dm_menu_items.values():
            submenu = item.get("container-title", None)
            if submenu and not self.menu.has_submenu(submenu):
                self.menu.add_submenu(submenu)
            if item["label"]:
                self.menu.add_item(item["label"], submenu)
        # Recent and most used files
        if self.desktop_entry:
            recent, most_used, related = self.__menu_get_zg_files()
            if recent or most_used or related:
                self.menu.add_separator()
            self.zg_files = {}
            for files, name in ((recent, _("Recent")),
                                (most_used, _("Most used")),
                                (related, _("Related"))):
                if files:
                    self.menu.add_submenu(name)
                    for text, uri in files:
                        label = text or uri
                        if len(label)>40:
                            label = label[:20]+"..."+label[-17:]
                        self.zg_files[label] = uri
                        self.menu.add_item(label, name)
        # Windows stuff
        win_nr = self.windows.get_count()
        if win_nr:
            self.menu.add_separator()
            if win_nr == 1:
                t = ""
            else:
                t = _(" all windows")
            if self.windows.get_unminimized_count() == 0:
                self.menu.add_item(_("Un_minimize") + t)
            else:
                self.menu.add_item(_("_Minimize") + t)
            for window in self.windows:
                if not window.is_maximized() \
                and window.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
                    self.menu.add_item(_("Ma_ximize") + t)
                    break
            else:
                self.menu.add_item(_("Unma_ximize") + t)
            self.menu.add_item(_("_Close") + t)

        connect(self.menu, "item-activated", self.__on_menuitem_activated)
        connect(self.menu, "menu-resized", self.__on_menu_resized)
        if self.globals.settings["old_menu"]:
            menu = self.menu.get_menu()
            menu.popup(None, None,
                       self.__menu_position, event.button, event.time)
            self.globals.gtkmenu_showing = True
            # TODO: check is this connection destroyed when done?
            menu.connect("selection-done", self.__menu_closed)
        else:
            popup_child = self.popup.alignment.get_child()
            if popup_child:
                self.popup.remove(popup_child)
            self.popup.add(self.menu.get_menu())
            self.popup.show()
            self.popup.resize(10,10)
            # Hide other popup if open.
            if self.globals.gb_showing_popup is not None and \
               self.globals.gb_showing_popup != self:
                self.globals.gb_showing_popup.hide_list()
            self.globals.gb_showing_popup = self


    def __menu_get_zg_files(self):
        # Get information from zeitgeist
        appname = self.desktop_entry.getFileName().split("/")[-1]
        recent_files = zg.get_recent_for_app(appname,
                                             days=30,
                                             number_of_results=8)
        most_used_files = zg.get_most_used_for_app(appname,
                                                   days=30,
                                                   number_of_results=8)
        # For programs that work badly with zeitgeist (openoffice for now),
        # mimetypes should be used to identify recent and most used as well.
        if self.identifier in zg.workrounds:
            if self.identifier == "openoffice-writer" and \
               not self.globals.settings["separate_ooo_apps"]:
                mimetypes = zg.workrounds["openoffice-writer"] + \
                            zg.workrounds["openoffice-calc"] + \
                            zg.workrounds["openoffice-presentation"] + \
                            zg.workrounds["openoffice-draw"]
            else:
                mimetypes = zg.workrounds[self.identifier]
            recent_files += zg.get_recent_for_mimetypes(mimetypes,
                                                        days=30,
                                                        number_of_results=8)
            most_used_files += zg.get_most_used_for_mimetypes(mimetypes,
                                                              days=30,
                                                           number_of_results=8)
        # Related files contains files that can be used by the program and
        # has been used by other programs (but not this program) today.
        related_files = []
        try:
            mimetypes = self.desktop_entry.getMimeTypes()
        except AttributeError:
            mimetypes = None
        if mimetypes:
            related_candidates = zg.get_recent_for_mimetypes(mimetypes,
                                                             days=1,
                                                        number_of_results=20)
            other_recent = zg.get_recent_for_app(appname,
                                                 days=1,
                                                 number_of_results=20)
            related_files = [rf for rf in related_candidates \
                             if not (rf in recent_files or \
                                     rf in other_recent)]
            related_files = related_files[:3]
        return recent_files, most_used_files, related_files

    def __on_menuitem_activated(self, arg, name):
        if name in self.zg_files:
            self.launch_item(None, None, self.zg_files[name])
            return
        for id, menu_item in self.dockmanager.get_menu_items().items():
            if name == menu_item['label']:
                self.dockmanager.MenuItemActivated(id)
                self.hide_list()
                return
        menu_funcs = \
            {_("_Close"): self.action_close_all_windows,
             _("_Close") + _(" all windows"): self.action_close_all_windows,
             _("Ma_ximize"): self.action_maximize_all_windows,
             _("Ma_ximize") + _(" all windows"):
                                        self.action_maximize_all_windows,
             _("Unma_ximize"): self.action_maximize_all_windows,
             _("Unma_ximize")+_(" all windows"):
                                        self.action_maximize_all_windows,
             _("_Minimize"): self.action_minimize_all_windows,
             _("_Minimize")+_(" all windows"):
                                        self.action_minimize_all_windows,
             _("Un_minimize"): self.__menu_unminimize_all_windows,
             _("Un_minimize")+_(" all windows"):
                                        self.__menu_unminimize_all_windows,
             _("Edit Launcher"): self.__menu_edit_launcher,
             _("Edit Identifier"): self.__menu_change_identifier,
             _("Unpin application"): self.action_remove_launcher,
             _("Make custom launcher"): self.__menu_edit_launcher,
             _("_Pin application"): self.__menu_pin,
             _("_Launch application"): self.action_launch_application}
        func = menu_funcs.get(name, None)
        if func:
            func()

    def __on_menu_resized(self, *args):
        self.popup.resize(10,10)

    def __menu_position(self, menu):
        # Used only with the gtk menu
        x, y = self.button.window.get_origin()
        a = self.button.get_allocation()
        x += a.x
        y += a.y
        w, h = menu.size_request()
        if self.globals.orient == "v":
            if x < (self.screen.get_width() / 2):
                x += a.width
            else:
                x -= w
            if y + h > self.screen.get_height():
                y -= h - a.height
        if self.globals.orient == "h":
            if y < (self.screen.get_height() / 2):
                y += a.height
            else:
                y -= h
            if x + w >= self.screen.get_width():
                x -= w - a.width
        return (x, y, False)

    def __menu_closed(self, menushell):
        # Used only with the gtk menu
        self.globals.gtkmenu_showing = False
        gobject.source_remove(self.menu_selection_done_sid)
        self.menu_selection_done_sid = None
        self.menu.delete_menu()
        self.menu = None

    def __menu_unminimize_all_windows(self, widget=None, event=None):
        t = gtk.get_current_event_time()
        for window in self.windows.get_list():
            if window.is_minimized():
                window.unminimize(t)
        self.hide_list()

    def __menu_change_identifier(self, widget=None, event=None):
        self.hide_list()
        self.dockbar_r().change_identifier(self.desktop_entry.getFileName(),
                                           self.identifier)

    def __menu_edit_launcher(self, widget=None, event=None):
        if self.desktop_entry:
            path = self.desktop_entry.getFileName()
        else:
            path = ""
        self.dockbar_r().edit_launcher(path, self.identifier)
        self.hide_list()

    def __menu_pin(self, widget=None, event=None):
        self.pinned = True
        self.dockbar_r().update_pinned_apps_list()
        self.hide_list()

    #### Actions
    def action_select(self, widget, event):
        wins = self.windows.get_list()
        if (self.pinned and not wins):
            if self.media_buttons:
                sucess = self.media_buttons.show_player()
            if not self.media_buttons or not sucess:
                self.action_launch_application()
        # One window
        elif len(wins) == 1:
            sow = self.globals.settings["select_one_window"]
            if sow == "select window":
                self.windows[wins[0]].action_select_window(widget, event)
            elif sow == "select or minimize window":
                self.windows[wins[0]].action_select_or_minimize_window(widget,
                                                                       event)
            self.hide_list()
            self.deopacify()
        # Multiple windows
        elif len(wins) > 1:
            smw = self.globals.settings["select_multiple_windows"]
            if smw == "select all":
                self.action_select_or_minimize_group(widget, event,
                                                     minimize=False)
            elif smw == "select or minimize all":
                self.action_select_or_minimize_group(widget, event,
                                                     minimize=True)
            elif smw == "compiz scale":
                umw = self.windows.get_unminimized()
                if len(umw) == 1:
                    sow = self.globals.settings["select_one_window"]
                    if sow == "select window":
                        self.windows[umw[0]].action_select_window(widget,
                                                                  event)
                        self.hide_list()
                        self.deopacify()
                    elif sow == "select or minimize window":
                        self.windows[umw[0]].action_select_or_minimize_window(
                                                                 widget, event)
                        self.hide_list()
                        self.deopacify()
                elif len(umw) == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif smw == "cycle through windows":
                self.action_select_next(widget, event)
            elif smw == "show popup":
                self.action_select_popup(widget, event)

    def action_select_popup(self, widget, event):
        if self.popup_showing is True:
            self.hide_list()
        else:
            self.show_list()

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if self.globals.settings["show_only_current_desktop"]:
            mode = "ignore"
        else:
            mode = self.globals.settings["workspace_behavior"]
        screen = self.screen
        windows_stacked = screen.get_windows_stacked()
        grp_win_stacked = []
        ignorelist = []
        minimized_win_cnt = len([win for win in self.windows \
                                     if win.is_minimized()])
        moved = False
        grtop = False
        wingr = False
        active_workspace = screen.get_active_workspace()
        self.hide_list()
        self.deopacify()

        # Check if there are any uminimized windows, unminimize
        # them (unless they are on another workspace and work-
        # space behavior is somehting other than move) and
        # return.
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized():
                    ignored = False
                    if not win.is_pinned() \
                    and win.get_workspace() is not None \
                    and screen.get_active_workspace() != win.get_workspace():
                        if mode == "move":
                            ws = screen.get_active_workspace()
                            win.move_to_workspace(ws)
                        else: # mode == "ignore" or "switch"
                            ignored = True
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == "move":
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                        else: # mode == "ignore" or "switch"
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
            and (win.get_window_type() in [wnck.WINDOW_NORMAL,
                                           wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() \
                    and win.get_workspace() is not None \
                    and active_workspace != win.get_workspace():
                        if mode == "move":
                            ws = screen.get_active_workspace()
                            win.move_to_workspace(ws)
                            moved = True
                        else: # mode == "ignore" or "switch"
                            ignored = True
                            ignorelist.append(win)
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == "move":
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                            moved = True
                        else: # mode == "ignore" or "switch"
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

        if not grp_win_stacked and mode == "switch":
            # Put the windows in dictionaries according to workspace and
            # viewport so we can compare which workspace and viewport that
            # has most windows.
            workspaces ={}
            for win in self.windows:
                if win.get_workspace() is None:
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
                        vp = workspaces[workspace][xvp][yvp]
                        nr = len (vp)
                        if nr > max:
                            max = nr
                            x = screen.get_width() * xvp
                            y = screen.get_height() * yvp
                            new_workspace = workspace
                            grp_win_stacked = vp
                        elif nr == max:
                            # Check wether this workspace or previous workspace
                            # with the same amount of windows has been
                            # activated later.
                            for win in ignorelist:
                                if win in grp_win_stacked:
                                    break
                                if win in vp:
                                    x = screen.get_width() * xvp
                                    y = screen.get_height() * yvp
                                    new_workspace = workspace
                                    grp_win_stacked = vp
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
            #Bottommost window fist again.
            ignorelist.reverse()
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list

        if grtop and not moved and minimize:
            for win in grp_win_stacked:
                self.windows[win].window.minimize()
        delay = self.globals.settings["delay_on_select_all"]
        win_nr = len(grp_win_stacked)
        if not grtop:
            for i in range(win_nr):
                grp_win_stacked[i].activate(event.time)
                if delay and i < win_nr - 1:
                    sleep(0.05)

    def action_select_only(self, widget, event):
        self.action_select_or_minimize_group(widget, event, False)

    def action_select_or_compiz_scale(self, widget, event):
        wins = self.windows.get_unminimized()
        if  len(wins) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
        self.hide_list()
        self.deopacify()

    def action_minimize_all_windows(self,widget=None, event=None):
        for window in self.windows.get_list():
            window.minimize()
        self.hide_list()
        self.deopacify()

    def action_maximize_all_windows(self,widget=None, event=None):
        maximized = False
        for window in self.windows.get_list():
            if not window.is_maximized() \
            and window.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
                window.maximize()
                maximized = True
        if not maximized:
            for window in self.windows:
                window.unmaximize()
        self.hide_list()
        self.deopacify()


    def action_select_next(self, widget=None, event=None, previous=False):
        if not self.windows.get_list():
            return
        if self.nextlist_time is None or time() - self.nextlist_time > 1.5 or \
           self.nextlist is None:
            # Make the list and pick the window.
            windows_stacked = self.screen.get_windows_stacked()
            wins = self.windows.get_list()
            if self.globals.settings["select_next_use_lastest_active"]:
                self.nextlist = []
                minimized_list = []
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
            else:
                topwin = None
                for i in range(1, len(windows_stacked)+1):
                        if windows_stacked[-i] in wins and \
                           not windows_stacked[-i].is_minimized():
                            topwin = windows_stacked[-i]
                            break
                self.nextlist = wins
                if topwin:
                    while self.nextlist[0] != topwin:
                        win = self.nextlist.pop(0)
                        self.nextlist.append(win)
            if self.nextlist[0].is_active():
                if previous:
                    win = self.nextlist.pop(-1)
                    self.nextlist.insert(0, win)
                else:
                    win = self.nextlist.pop(0)
                    self.nextlist.append(win)
        else:
            # Iterate the list.
            if previous:
                win = self.nextlist.pop(-1)
                self.nextlist.insert(0, win)
            else:
                win = self.nextlist.pop(0)
                self.nextlist.append(win)
        win = self.nextlist[0]
        self.nextlist_time = time()
        # Just a safety check
        if not win in self.windows:
            return

        if not self.popup_showing:
            self.show_list()
        if self.globals.settings["select_next_activate_immediately"]:
            self.windows[win].action_select_window(widget, event)
        else:
            if self.scrollpeak_wb:
                self.scrollpeak_wb.button.set_highlighted(False)
            self.scrollpeak_wb = self.windows[win]
            self.scrollpeak_wb.button.set_highlighted(True)
            if self.scrollpeak_sid is not None:
                gobject.source_remove(self.scrollpeak_sid)
            self.scrollpeak_sid = gobject.timeout_add(1500,
                                                      self.scrollpeak_select)
            while gtk.events_pending():
                    gtk.main_iteration(False)
            self.scrollpeak_wb.opacify()

    def action_select_previous(self, widget=None, event=None):
        self.action_select_next(widget, event, previous=True)

    def action_select_next_with_popup(self, widget=None,
                                      event=None, previous=False):
        self.show_list()
        self.action_select_next(widget, event, previous)
        if self.hide_list_sid is not None:
            gobject.source_remove(self.hide_list_sid)
        self.hide_time = time()
        self.hide_list_sid = gobject.timeout_add(1500,
                                                 self.hide_list_request)

    def scrollpeak_select(self):
        self.scrollpeak_wb.action_select_window()
        self.scrollpeak_abort()

    def scrollpeak_abort(self):
        if self.scrollpeak_wb:
            self.scrollpeak_wb.button.set_highlighted(False)
            self.scrollpeak_wb.deopacify()
            self.scrollpeak_wb = None
        if self.scrollpeak_sid:
            gobject.source_remove(self.scrollpeak_sid)
            self.scrollpeak_sid = None
        if self.launch_sid:
            gobject.source_remove(self.launch_sid)
            self.launch_sid = None
        self.hide_list()

    def action_close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        for window in self.windows.get_list():
            window.close(t)
        self.hide_list()
        self.deopacify()

    def action_launch_application(self, widget=None, event=None):
        if self.lastlaunch is not None \
        and time() - self.lastlaunch < 2:
                return
        if self.desktop_entry:
            self.desktop_entry.launch()
        else:
            return
        self.lastlaunch = time()
        self.launch_effect = True
        self.update_state()
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000,
                                                self.__remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000,
                                                self.__remove_launch_effect)
        self.hide_list()
        self.deopacify()
        if self.launch_sid:
            gobject.source_remove(self.launch_sid)
            self.launch_sid = None

    def action_launch_with_delay(self, widget=None, event=None, delay=1500):
        self.launch_sid = gobject.timeout_add(delay,
                                              self.action_launch_application)


    def action_show_menu(self, widget, event):
        self.menu_show(event)

    def action_remove_launcher(self, widget=None, event=None):
        print "Removing launcher ", self.identifier
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        self.pinned = False
        if not self.windows:
            self.dockbar_r().remove_groupbutton(self)
        else:
            self.dockbar_r().group_unpinned(name)
        self.hide_list()
        self.deopacify()

    def action_minimize_all_other_groups(self, widget, event):
        self.hide_list()
        self.dockbar_r().minimize_other_groups(self)
        self.hide_list()
        self.deopacify()

    def action_compiz_scale_windows(self, widget, event):
        wins = self.windows.get_unminimized()
        if not wins:
            return
        self.hide_list()
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return
        if self.globals.settings["show_only_current_desktop"]:
            path = "scale/allscreens/initiate_key"
        else:
            path = "scale/allscreens/initiate_all_key"
        try:
            compiz_call_async(path, "activate","root", self.root_xid,"match", \
                        "iclass=%s"%wins[0].get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings["popup_delay"] + 200,
                            self.hide_list)
        self.deopacify()

    def action_compiz_shift_windows(self, widget, event):
        wins = self.windows.get_unminimized()
        if not wins:
            return
        self.hide_list()
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return

        if self.globals.settings["show_only_current_desktop"]:
            path = "shift/allscreens/initiate_key"
        else:
            path = "shift/allscreens/initiate_all_key"
        try:
            compiz_call_async(path, "activate","root", self.root_xid,"match", \
                        "iclass=%s"%wins[0].get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings["popup_delay"]+ 200,
                            self.hide_list)
        self.deopacify()

    def action_compiz_scale_all(self, widget, event):
        try:
            compiz_call_async("scale/allscreens/initiate_key", "activate",
                        "root", self.root_xid)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings["popup_delay"]+ 200,
                            self.hide_list)
        self.hide_list()
        self.deopacify()

    def action_dbpref (self,widget=None, event=None):
        # Preferences dialog
        self.dockbar_r().open_preference()
        self.hide_list()
        self.deopacify()

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = \
            ODict((
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


class GroupMenu(gobject.GObject):
    __gsignals__ = {
        "item-activated":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
        "menu-resized":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,())}

    def __init__(self, gtk_menu=False):
        gobject.GObject.__init__(self)
        self.gtk_menu = gtk_menu
        self.submenus = {}
        if gtk_menu:
            self.menu = gtk.Menu()
        else:
            self.menu = gtk.VBox()
            self.menu.set_spacing(2)
        self.menu.show()

    def add_item(self, name, submenu=None):
        if self.gtk_menu:
            item = gtk.MenuItem(name)
            item.show()
            if submenu:
                self.submenus[submenu].append(item)
                item.connect("button-press-event",
                             self.__on_item_activated, name)
            else:
                self.menu.append(item)
                item.connect("activate", self.__on_item_activated, name)
        else:
            item = CairoMenuItem(name)
            item.connect("clicked", self.__on_item_activated, name)
            item.show()
            if submenu:
                self.submenus[submenu].add_item(item)
            else:
                self.menu.pack_start(item)

    def add_submenu(self, name):
        if self.gtk_menu:
            item = gtk.MenuItem(name)
            item.show()
            self.menu.append(item)
            menu = gtk.Menu()
            item.set_submenu(menu)
        else:
            menu = CairoToggleMenu(name)
            self.menu.pack_start(menu)
            menu.show()
            menu.connect("toggled", self.__on_submenu_toggled)
        self.submenus[name] = menu

    def add_separator(self):
        separator = gtk.SeparatorMenuItem()
        separator.show()
        if self.gtk_menu:
            self.menu.append(separator)
        else:
            self.menu.pack_start(separator)

    def get_menu(self):
        return self.menu

    def has_submenu(self, name):
        return name in self.submenus

    def delete_menu(self):
        self.menu.destroy()
        del self.menu
        del self.submenus

    def __on_item_activated(self, *args):
        name = args[-1]
        self.emit("item-activated", name)

    def __on_submenu_toggled(self, *args):
        self.emit("menu-resized")

