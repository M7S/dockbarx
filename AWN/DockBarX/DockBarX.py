#!/usr/bin/python2

#   DockBarX.py
#
#	Copyright 2009, 2010 Aleksey Shaferov and Matias Sars
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

import awn
import dockbarx.dockbar
from dockbarx.common import Globals
import gobject
import weakref
import time
import sys
import gtk
import wnck
import dbus
import dbus.service

WNCK_WINDOW_STATE_MINIMIZED = 1

class DockBarApp (awn.AppletSimple):
    def __init__ (self, uid, panel_id):
        awn.AppletSimple.__init__(self, "DockbarX", uid, panel_id)
        self.set_icon_name("gtk-apply")
        gobject.idle_add(self.__on_idle)
        self.db_loaded = False
        self.awn_applet_dbus = AWNappletDBus(self)


    def __on_idle(self):
        self.globals = Globals()
        self.autohide_sid = None
        self.should_autohide = True
        self.hide_inhibit_cookie = None
        self.geometry_time = 0
        self.last_geometry_window = lambda: None
        self.windows = weakref.WeakKeyDictionary()
        self.border_distances = weakref.WeakKeyDictionary()
        self.old_child = self.get_child()
        self.wnck_screen = wnck.screen_get_default()
        gdk_screen = gtk.gdk.screen_get_default()
        self.icon = self.get_icon()
        self.remove(self.old_child)
        self.alignment = gtk.Alignment()
        self.add(self.alignment)
        self.alignment.show()
        self.db = dockbarx.dockbar.DockBar(self)
        self.db.set_parent_window_reporting(True)
        self.db.load()

        # Inactive dockbarx's size overflow management
        self.db.set_max_size(3000)

        if self.get_pos_type() == gtk.POS_RIGHT:
            self.db.set_orient("right")
            self.alignment.set(1, 0, 0, 0)
        elif self.get_pos_type() == gtk.POS_TOP:
            self.db.set_orient("up")
            self.alignment.set(0, 0, 0, 0)
        elif self.get_pos_type() == gtk.POS_LEFT:
            self.db.set_orient("left")
            self.alignment.set(0, 0, 0, 0)
        else:
            self.db.set_orient("down")
            self.alignment.set(0, 1, 0, 0)
        container = self.db.get_container()
        if self.db.get_orient() in ("down", "up"):
            container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 5)
        else:
            container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 5, -1)
        self.alignment.add(container)
        self.connect("size-changed", self.__on_size_changed)
        self.connect("offset-changed", self.__on_size_changed)
        self.connect("position-changed", self.__on_position_changed)
        self.globals.connect("awn-behavior-changed",
                             self.__on_behavior_changed)
        container.show_all()
        self.show()
        self.wnck_screen.connect("active-window-changed",
                                 self.__on_active_window_changed)
        gobject.timeout_add(200, self.__update_autohide)
        for window in self.db.get_windows():
            self.add_window(window)
        self.db_loaded = True
        self.__compute_should_autohide()

    def __on_size_changed(self, *args):
        container = self.db.get_container()
        if self.db.get_orient() in ("down", "up"):
            container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 5)
        else:
            container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 5, -1)
        self.__compute_should_autohide()

    def __on_position_changed(self, applet, position):
        self.alignment.remove(self.db.get_container())
        if self.get_pos_type() == gtk.POS_RIGHT:
            self.db.set_orient("right")
            self.alignment.set(1, 0, 0, 0)
        elif self.get_pos_type() == gtk.POS_TOP:
            self.db.set_orient("up")
            self.alignment.set(0, 0, 0, 0)
        elif self.get_pos_type() == gtk.POS_LEFT:
            self.db.set_orient("left")
            self.alignment.set(0, 0, 0, 0)
        else:
            self.db.set_orient("down")
            self.alignment.set(0, 1, 0, 0)
        container = self.db.get_container()
        if self.db.get_orient() in ("up", "down"):
            container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 5)
        else:
            container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 5, -1)
        self.alignment.add(container)
        container.show_all()
        self.show()
        self.__compute_should_autohide()

    #### Autohide stuff
    def add_window(self, window, reset_should_autohide=True):
        geo_sid = window.connect("geometry-changed",
                             self.__on_window_geometry_changed)
        state_sid = window.connect("state-changed",
                             self.__on_window_state_changed)
        self.windows[window] = (geo_sid, state_sid)
        self.__calc_border_distance(window)
        if self.db_loaded and reset_should_autohide:
            self.__compute_should_autohide()

    def remove_window(self, window, reset_should_autohide=True, forced=False):
        if window in self.border_distances:
            del self.border_distances[window]
        if window in self.windows:
            sids = self.windows.pop(window)
            if sids is not None:
                window.disconnect(sids[0])
                window.disconnect(sids[1])
        if reset_should_autohide:
            self.__compute_should_autohide()

    def __update_autohide(self):
        if self.should_autohide and self.globals.shown_popup() is None:
            if self.hide_inhibit_cookie is not None:
                self.uninhibit_autohide(self.hide_inhibit_cookie)
                self.hide_inhibit_cookie = None
        else:
            if self.hide_inhibit_cookie is None:
                self.hide_inhibit_cookie = self.inhibit_autohide(
                                                            "dbx intellihide")
        return True

    def __on_window_state_changed(self, wnck_window,changed_mask, new_state):
        if WNCK_WINDOW_STATE_MINIMIZED & changed_mask:
            self.__compute_should_autohide()

    def __on_window_geometry_changed(self, window):
        if time.time() - self.geometry_time < 0.12 and \
           window == self.last_geometry_window():
               # Same window get multiple calls when the geometry changes
               # In that case, just return.
               return
        self.last_geometry_window = weakref.ref(window)
        self.geometry_time = time.time()
        gobject.timeout_add(120, self.__calc_border_distance, window, True)

    def __on_active_window_changed(self, screen, previous_active_window):
        if self.globals.settings["awn/behavior"] == "dodge active window":
            self.__compute_should_autohide()

    def __on_behavior_changed(self, *args):
        self.__compute_should_autohide()

    def __calc_border_distance(self, window, reset_should_autohide=False):
        bd = {"left": 1000, "right": 1000, "top": 1000, "bottom": 1000}
        x, y, w, h = window.get_geometry()
        gdk_screen = gtk.gdk.screen_get_default()
        monitor = gdk_screen.get_monitor_at_point(x + (w / 2), y  + (h / 2))
        if monitor != self.get_monitor():
            return
        mx, my, mw, mh = self.get_monitor_geometry()
        if y < my + mh and y + h > my:
            if x + w > mx:
                bd["left"] = x - mx
            if x < mx + mw:
                bd["right"] = mx + mw - x - w
        if x < mx + mw and x + w > mx:
            if y + h > my:
                bd["top"] = y - my
            if y < my + mh:
                bd["bottom"] = my + mh - y - h
        self.border_distances[window] = bd
        if reset_should_autohide:
            self.__compute_should_autohide()

    def __compute_should_autohide(self):
        pos = ("left", "right", "top", "bottom")[self.get_pos_type()]
        size = self.get_size() + self.icon.get_offset() + 2
        self.behavior = self.globals.settings["awn/behavior"]
        if not self.behavior in ("dodge windows", "dodge active window"):
            self.should_autohide = True
            return True
        self.should_autohide = False
        active_workspace = self.wnck_screen.get_active_workspace()
        for window in self.db.get_windows():
            if window.is_minimized():
                continue
            if self.behavior == "dodge active window" and \
               not window.is_active():
                continue
            if window.get_workspace() != active_workspace:
                continue
            border_distance = self.border_distances.get(window)
            if border_distance is None:
                continue
            if border_distance[pos] < size:
                self.should_autohide = True
                break
        return self.should_autohide

    def get_monitor(self):
        screen = self.get_screen()
        if screen is None:
            screen = gtk.gdk.screen_get_default()
        return screen.get_monitor_at_window(self.window)

    def get_monitor_geometry(self):
        screen = self.get_screen()
        if screen is None:
            screen = gtk.gdk.screen_get_default()
        monitor = screen.get_monitor_at_window(self.window)
        return screen.get_monitor_geometry(monitor)

    def reload(self=None):
        self.db_loaded = False
        self.db.reload()
        self.db_loaded = True

    def readd_container(self, container):
        # Dockbar calls back to this function when it is reloaded
        if self.db.get_orient() in ("up", "down"):
            container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 5)
        else:
            container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 5, -1)
        self.alignment.add(container)
        container.show_all()
        self.__compute_should_autohide()



class AWNappletDBus(dbus.service.Object):

    def __init__(self, applet):
        self.bus_name = "org.dockbar.AWNapplet"
        if "org.dockbar.AWNapp" in dbus.SessionBus().list_names():
            for n in range(1, 100):
                name = "org.dockbar.AWNapplet%s" % n
                if not name in dbus.SessionBus().list_names():
                    self.bus_name = name
                    break
        self.applet_r = weakref.ref(applet)
        bus_name = dbus.service.BusName(self.bus_name,
                                        bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
                                     "/org/dockbar/AWNapplet")

    @dbus.service.method(dbus_interface="org.dockbar.AWNapplet",
                         in_signature="", out_signature="",)
    def Reload(self):
        self.applet().reload()

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == "org.dockbar.AWNapplet":
            return {}
        else:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The Foo object does not implement the %s interface'
                    % interface_name)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv', out_signature='')
    def Set(self, interface_name, property_name, property_value):
        pass

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass

if __name__ == "__main__":
    awn.init(sys.argv[1:])
    applet = DockBarApp(awn.uid, awn.panel_id)
    awn.embed_applet(applet)
    applet.show_all()
    gtk.main()
