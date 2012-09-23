#!/usr/bin/python

#   dockbar.py
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

import gtk
import dbus
import os
import gobject
from dbus.mainloop.glib import DBusGMainLoop
from dockbarx.applets import DockXApplet
from dockbarx.unity import DBusMenu
from dockbarx.groupbutton import GroupMenu as Menu

DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

class AppIndicator(gtk.EventBox):
    def __init__(self, icon_name, position, address, obj,
                  icon_path, label, labelguide, accessibledesc, hint, title):
        self.menu = None
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.box = gtk.HBox()
        self.icon = gtk.Image()
        self.box.pack_start(self.icon)
        self.label = gtk.Label()
        self.box.pack_start(self.label)
        self.add(self.box)
        self.icon_themepath = icon_path
        self.on_icon_changed(icon_name, None)
        self.title = title
        
        self.dbusmenu = DBusMenu(self, address, obj)
        
        self.show_all()
        self.connect("button-press-event", self.on_button_press_event)

    def on_button_press_event(self, widget, event):
        self.show_menu(event)

    def show_menu(self, event):
        self.menu = Menu(gtk_menu=True)
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
        gtkmenu.popup(None, None, None, event.button, event.time)

    def menu_closed(self, *args):
        if self.menu is not None:
            for key in self.sids.keys():
                sid = self.sids.pop(key)
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
        if icon_name is not None:
            self.icon_name = icon_name
        icon_theme = gtk.IconTheme()
        icon_theme.set_screen(gtk.gdk.screen_get_default())
        if self.icon_themepath != "" and os.path.exists(self.icon_themepath):
            icon_theme.prepend_search_path(self.icon_themepath)
        pixbuf = icon_theme.load_icon(self.icon_name, 16, 0)
        self.icon.set_from_pixbuf(pixbuf)

    def on_icon_themepath_changed(self, path):
        self.icon_themepath = path

    def on_label_changed(self, label, guide):
        self.label.set_text(label)

    def on_title_changed(self, title):
        self.title = title

    def position_menu(self, menu):
        # Used only with the gtk menu
        x, y = self.window.get_origin()
        a = self.get_allocation()
        x += a.x
        y += a.y
        w, h = menu.size_request()
        if self.dockbar_r().orient == "v":
            if x < (self.screen.get_width() / 2):
                x += a.width
            else:
                x -= w
            if y + h > self.screen.get_height():
                y -= h - a.height
        if self.dockbar_r().orient == "h":
            if y < (self.screen.get_height() / 2):
                y += a.height
            else:
                y -= h
            if x + w >= self.screen.get_width():
                x -= w - a.width
        return (x, y, False)

class AppIndicatorApplet(DockXApplet):
    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        alignment = gtk.Alignment(0.5, 0.5)
        self.add(alignment)
        alignment.show()
        self.box = gtk.HBox(False, 2)
        self.box.set_border_width(4)
        self.box.show()
        alignment.add(self.box)
        self.show()
        self.fdo = BUS.get_object("org.freedesktop.DBus",
                                  "/org/freedesktop/DBus")
        addresses = self.fdo.ListNames(dbus_interface="org.freedesktop.DBus")
        for address in addresses:
            if str(address) == "com.canonical.indicator.application":
                self.connect(address)
                break
        else:
            gobject.idle_add(self.start_server)
        self.fdo.connect_to_signal("NameOwnerChanged",
                                    self.on_name_change_detected,
                                    dbus_interface=\
                                    "org.freedesktop.DBus")
        self.menu = None

    def start_server(self):
        cmd = "/usr/lib/indicator-application/indicator-application-service"
        os.system("/bin/sh -c '%s' &" % cmd)
        return False
    
    def on_name_change_detected(self, name, previous_owner, current_owner):
        if str(name) == "com.canonical.indicator.application":
            if previous_owner == "" and current_owner !="":
                self.connect(name)
            if previous_owner != "" and current_owner == "":
                print "indicator-application-service disappeared"
                self.disconnect()

    def connect(self, address):
        try:
            self.ayatana = BUS.get_object(address,
                                      "/org/ayatana/indicator/service")
        except:
            print "Error: Couldn't make dbus connection with %s" % address
            return
        # Todo: Should version and service version arguments be something
        #       other than 0 and 0?
        self.ayatana.Watch(0, 0,
                           dbus_interface="org.ayatana.indicator.service",
                           reply_handler=self.reply_handler,
                           error_handler=self.error_handler)
        self.obj = BUS.get_object(address,
                                "/com/canonical/indicator/application/service")
        self.obj.GetApplications(
                dbus_interface="com.canonical.indicator.application.service", 
                reply_handler=self.indicators_loaded,
                error_handler=self.error_loading)

    def disconnect(self):
        for sid in self.sids[:]:
            sid.remove()
            self.sids.remove(sid)
        indicators = self.box.get_children()
        for ind in indicators:
            ind.dbusmenu.destroy()
            if ind.menu is not None:
                ind.menu.delete_menu()
            ind.destroy()

    def indicators_loaded(self, indicators):
        for ind in indicators:
            self.ind_added(*ind)
        self.sids = []
        
        iface = dbus.Interface(self.obj,
                  dbus_interface="com.canonical.indicator.application.service")
        connections = {"ApplicationAdded": self.ind_added,
                       "ApplicationIconChanged": self.on_icon_changed,
                       "ApplicationIconThemePathChanged":
                                            self.on_icon_themepath_changed,
                       "ApplicationLabelChanged": self.on_label_changed,
                       "ApplicationRemoved": self.ind_removed,
                       "ApplicationTitleChanged": self.on_title_changed}
        for sig, call_func in connections.items():
            self.sids.append(iface.connect_to_signal(sig, call_func))

    def ind_added(self, *args):
        position = args[1]
        ind = AppIndicator(*args)
        self.box.pack_start(ind)
        self.box.reorder_child(ind, position)

    def ind_removed(self, position):
        indicators = self.box.get_children()
        ind = indicators[position]
        ind.dbusmenu.destroy()
        if ind.menu is not None:
            ind.menu.delete_menu()
        ind.destroy()

    def on_icon_changed(self, position, icon_name, icon_desc):
        ind = self.box.get_children(position)
        ind.on_icon_changed(icon_name, icon_desc)

    def on_icon_themepath_changed(self, position, path):
        ind = self.box.get_children(position)
        ind.on_themepath_changed(path)

    def on_label_changed(self, position, label, guide):
        ind = self.box.get_children(position)
        ind.on_label_changed(label, guide)

    def on_title_changed(self, position, title):
        ind = self.box.get_children(position)
        ind.on_title_changed(title)
    
    def error_loading(self, err):
        print err

    def reply_handler(self, *args):
        pass

    def error_handler(self, err):
        print err
        
def get_dbx_applet(dbx_dict):
    global aiapplet
    try:
        return aiapplet
    except:
        # First run, make a new instance
        aiapplet = AppIndicatorApplet(dbx_dict)
        return aiapplet
