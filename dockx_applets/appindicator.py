#!/usr/bin/python3

#   dockbar.py
#
#   Copyright 2008, 2009, 2010 Aleksey Shaferov and Matias Sars
#
#   DockbarX is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DockbarX is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import dbus
import os
import os.path
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib
import weakref
from dbus.mainloop.glib import DBusGMainLoop
from dockbarx.applets import DockXApplet
from dockbarx.unity import DBusMenu
from dockbarx.groupbutton import GroupMenu as Menu
from dockbarx.log import logger

DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

INDICATOR_DBUS = {
    "canonical": {
        "name": "com.canonical.indicator.application",
        "path": "/com/canonical/indicator/application/service",
        "interface": "com.canonical.indicator.application.service"
    },
    "ayatana": {
        "name": "org.ayatana.indicator.application",
        "path": "/org/ayatana/indicator/application/service",
        "interface": "org.ayatana.indicator.application.service"
    }
}

class AppIndicator(Gtk.EventBox):
    def __init__(self, applet, icon_name, position, address, obj,
                  icon_path, label, labelguide,
                  accessibledesc, hint=None, title=None):
        self.applet_r = weakref.ref(applet)
        self.menu = None
        GObject.GObject.__init__(self)
        self.set_visible_window(False)
        self.box = None
        self.icon = Gtk.Image()
        self.icon_name = None
        self.icon_pixbufs = {}
        self.label = Gtk.Label()
        self.repack()
        self.icon_themepath = icon_path
        self.on_icon_changed(icon_name, None)
        self.on_label_changed(label, labelguide)
        
        # Older versions of application-indicator-service doesn't give a title.
        self.title = title
        
        self.dbusmenu = DBusMenu(self, address, obj)
        
        self.show_all()
        self.connect("button-press-event", self.on_button_press_event)

    def repack(self):
        if self.box is not None:
            self.box.remove(self.icon)
            self.box.remove(self.label)
            self.remove(self.box)
            self.box.destroy()
        if self.applet_r().get_position() in ("left", "right"):
            self.box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
            self.label.set_angle(270)
        else:
            self.box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
            self.label.set_angle(0)
        self.box.pack_start(self.icon, True, True, 0)
        self.box.pack_start(self.label, True, True, 0)
        self.add(self.box)

    def on_button_press_event(self, widget, event):
        self.show_menu(event)

    def show_menu(self, event):
        self.menu = Menu(gtk_menu=True)
        # Since some application menus doesn't seem to be
        # update, let's try to fetch just in case.
        self.dbusmenu.fetch_layout()
        
        self.menu.add_quicklist(self.dbusmenu.layout)
        self.sids = {}
        self.sids[0] = self.menu.connect("item-activated",
                                         self.on_menuitem_activated)
        #~ self.sids[1] = self.menu.connect("item-hovered",
                                         #~ self.__on_menuitem_hovered)
        #~ self.sids[2] = self.menu.connect("menu-resized",
                                         #~ self.__on_menu_resized)
        gtkmenu = self.menu.get_menu()
        self.sd_sid = gtkmenu.connect("selection-done", self.menu_closed)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            gtkmenu.popup_at_pointer(event)
        else:
            gtkmenu.popup(None, None, self.position_menu, None,
                          event.button, event.time)

    def menu_closed(self, *args):
        if self.menu is not None:
            while len(self.sids) > 0:
                key, sid = self.sids.popitem()
                self.menu.disconnect(sid)
            self.sd_sid = self.menu.get_menu().disconnect(self.sd_sid)
            self.menu.delete_menu()
            self.menu = None

    def on_menuitem_activated(self, menu_item, identifier):
        if identifier.startswith("unity_"):
            identifier = int(identifier.rsplit("_", 1)[-1])
            data = dbus.String("", variant_level=1)
            t = dbus.UInt32(0)
            self.dbusmenu.send_event(identifier, "clicked", data, t)

    def on_icon_changed(self, icon_name=None, icon_desc=None):
        if self.icon_name == icon_name:
            return
        if icon_name is not None:
            self.icon_name = icon_name
        self.update_icon()
        
    def update_icon(self, force=False):
        if not force and self.icon_name in self.icon_pixbufs:
            pixbuf = self.icon_pixbufs[self.icon_name]
        else:
            pixbuf = self.get_icon(self.icon_name)
            self.icon_pixbufs[self.icon_name] = pixbuf
        self.icon.set_from_pixbuf(pixbuf)
        
    def get_icon(self, icon_name):
        icon_size = self.applet_r().get_full_size()
        if icon_name.startswith("/") and os.path.exists(icon_name):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name,
                                                          icon_size, 
                                                          icon_size)
        else:
            icon_theme = Gtk.IconTheme.get_default()
            if self.icon_themepath != "" and \
               os.path.exists(self.icon_themepath):
                icon_theme.prepend_search_path(self.icon_themepath)
            pixbuf = icon_theme.load_icon(self.icon_name, icon_size, 0)
        return pixbuf

    def on_icon_themepath_changed(self, path):
        if self.icon_themepath == path:
            return
        self.icon_themepath = path
        #reset icon_pixbufs so that the icons will be reloaded.
        self.icon_pixbufs = {}
        # Update the icon
        if self.icon_name is not None:
            self.update_icon()

    def on_label_changed(self, label, guide):
        self.label.set_text(label)

    def on_title_changed(self, title):
        self.title = title

    def position_menu(self, menu, x, y, push_in):
        dummy, x, y = self.get_window().get_origin()
        a = self.get_allocation()
        requisition = menu.size_request()
        w, h = requisition.width, requisition.height
        size = self.applet_r().get_full_size()
        if self.applet_r().get_position() == "left":
            x += size
            y += a.y
        if self.applet_r().get_position() == "right":
            x -= w
            y += a.y
        if self.applet_r().get_position() == "top":
            x += a.x
            y += size
        if self.applet_r().get_position() == "bottom":
            x += a.x
            y -= h
        screen = self.get_window().get_screen()
        if y + h > screen.get_height():
                y = screen.get_height() - h
        if x + w >= screen.get_width():
                x = screen.get_width() - w
        return (x, y, False)

class AppIndicatorApplet(DockXApplet):
    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.topbox = None
        self.boxes = {}
        self.sids = {}
        self.dbus = {}
        for backend in INDICATOR_DBUS.keys():
            self.sids[backend] = []
            self.dbus[backend] = None
        self.repack()
        self.show()
        self.fdo = BUS.get_object("org.freedesktop.DBus",
                                  "/org/freedesktop/DBus")
        addresses = self.fdo.ListNames(dbus_interface="org.freedesktop.DBus")
        for backend in INDICATOR_DBUS.keys():
            for address in addresses:
                if str(address) == INDICATOR_DBUS[backend]["name"]:
                    self.connect_dbus(backend)

        self.fdo.connect_to_signal("NameOwnerChanged",
                                    self.on_name_change_detected,
                                    dbus_interface=\
                                    "org.freedesktop.DBus")
        self.menu = None

    def update(self):
        if self.topbox is None:
            return
        self.repack(update_icon=True)

    def repack(self, update_icon=False):
        children = {}
        if self.topbox is not None:
            for backend in INDICATOR_DBUS.keys():
                box = self.boxes[backend]
                children[backend] = box.get_children()
                for child in children[backend]:
                    box.remove(child)
                self.topbox.remove(box)
                box.destroy()
            self.remove(self.topbox)
            self.topbox.destroy()

        if self.get_position() in ("left", "right"):
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL

        self.topbox = Gtk.Box.new(orientation, 4)
        for backend in INDICATOR_DBUS.keys():
            self.boxes[backend] = Gtk.Box.new(orientation, 0)
            self.topbox.pack_start(self.boxes[backend], False, False, 0)
            if backend in children.keys():
                for child in children[backend]:
                    self.boxes[backend].pack_start(child, True, True, 0)
                    child.repack()
                    if update_icon:
                        child.update_icon(force=True)
        self.add(self.topbox)
        self.topbox.show_all()
        
    def on_name_change_detected(self, name, previous_owner, current_owner):
        for backend in INDICATOR_DBUS.keys():
            if str(name) == INDICATOR_DBUS[backend]["name"]:
                if previous_owner == "" and current_owner !="":
                    self.connect_dbus(backend)
                if previous_owner != "" and current_owner == "":
                    # logger.info("%s indicator application service disappeared" % backend)
                    self.disconnect_dbus(backend)

    def connect_dbus(self, backend):
        try:
            bus = BUS.get_object(INDICATOR_DBUS[backend]["name"],
                                 INDICATOR_DBUS[backend]["path"])
        except:
            logger.error("Warning: Couldn't make dbus connection with %s" % INDICATOR_DBUS[backend]["name"])
            return
        self.dbus[backend] = bus
        bus.GetApplications(
                dbus_interface=INDICATOR_DBUS[backend]["interface"],
                reply_handler=lambda indicators: self.indicators_loaded(backend, indicators),
                error_handler=self.error_loading)

    def disconnect_dbus(self, backend):
        sids = self.sids[backend]
        for sid in sids[:]:
            sid.remove()
            sids.remove(sid)
        indicators = self.boxes[backend].get_children()
        for ind in indicators:
            ind.dbusmenu.destroy()
            if ind.menu is not None:
                ind.menu.delete_menu()
            ind.destroy()

    def indicators_loaded(self, backend, indicators):
        for ind in indicators:
            self.ind_added(backend, *ind)
        self.sids[backend] = []
        
        connections = {"ApplicationAdded": 
                                    lambda *args: self.ind_added(backend, *args),
                       "ApplicationIconChanged":
                                    lambda *args: self.on_icon_changed(backend, *args),
                       "ApplicationIconThemePathChanged":
                                    lambda *args: self.on_icon_themepath_changed(backend, *args),
                       "ApplicationLabelChanged":
                                    lambda *args: self.on_label_changed(backend, *args),
                       "ApplicationRemoved":
                                    lambda *args: self.ind_removed(backend, *args),
                       "ApplicationTitleChanged":
                                    lambda *args: self.on_title_changed(backend, *args)}
        iface = dbus.Interface(self.dbus[backend],
                               dbus_interface=INDICATOR_DBUS[backend]["interface"])
        for sig, call_func in list(connections.items()):
            self.sids[backend].append(iface.connect_to_signal(sig, call_func))

    def get_ind(self, backend, position):
        indicators = self.boxes[backend].get_children()
        if position < len(indicators):
            return indicators[position]
        return None

    def ind_added(self, backend, *args):
        position = args[1]
        ind = AppIndicator(self, *args)
        self.boxes[backend].pack_start(ind, True, True, 0)
        self.boxes[backend].reorder_child(ind, position)

    def ind_removed(self, backend, position):
        ind = self.get_ind(backend, position)
        if ind is not None:
            ind.dbusmenu.destroy()
            if ind.menu is not None:
                ind.menu.delete_menu()
            ind.destroy()

    def on_icon_changed(self, backend, position, icon_name, icon_desc):
        ind = self.get_ind(backend, position)
        if ind is not None:
            ind.on_icon_changed(icon_name, icon_desc)

    def on_icon_themepath_changed(self, backend, position, path):
        ind = self.get_ind(backend, position)
        if ind is not None:
            ind.on_themepath_changed(path)

    def on_label_changed(self, backend, position, label, guide):
        ind = self.get_ind(backend, position)
        if ind is not None:
            ind.on_label_changed(label, guide)

    def on_title_changed(self, backend, position, title):
        ind = self.get_ind(backend, position)
        if ind is not None:
            ind.on_title_changed(title)
    
    def error_loading(self, err):
        logger.error(err)

def get_dbx_applet(dbx_dict):
    global aiapplet
    try:
        aiapplet.repack()
    except:
        # First run, make a new instance
        aiapplet = AppIndicatorApplet(dbx_dict)
    return aiapplet
