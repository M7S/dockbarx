#!/usr/bin/python2

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

import gtk
import dbus
import os
import os.path
import gobject
import weakref
from dbus.mainloop.glib import DBusGMainLoop
from dockbarx.applets import DockXApplet
from dockbarx.unity import DBusMenu
from dockbarx.groupbutton import GroupMenu as Menu

DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

ICONSIZE = 18

# List of possible commands to launch indicator-application-service
service_cmds = ["/usr/lib/x86_64-linux-gnu/indicator-application/indicator-application-service", 
                "/usr/lib/x86_64-linux-gnu/indicator-application-service",
                "/usr/lib/i386-linux-gnu/indicator-application/indicator-application-service",
                "/usr/lib/i386-linux-gnu/indicator-application-service",
                "/usr/lib/indicator-application/indicator-application-service"]

class AppIndicator(gtk.EventBox):
    def __init__(self, applet, icon_name, position, address, obj,
                  icon_path, label, labelguide,
                  accessibledesc, hint=None, title=None):
        self.applet_r = weakref.ref(applet)
        self.menu = None
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.box = None
        self.icon = gtk.Image()
        self.icon_name = None
        self.icon_pixbufs = {}
        self.label = gtk.Label()
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
            self.box = gtk.VBox()
            self.label.set_angle(270)
        else:
            self.box = gtk.HBox()
            self.label.set_angle(0)
        self.box.pack_start(self.icon)
        self.box.pack_start(self.label)
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
        gtkmenu.popup(None, None, self.position_menu,
                      event.button, event.time)

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
        if self.icon_name == icon_name:
            return
        if icon_name is not None:
            self.icon_name = icon_name
        self.update_icon()
        
    def update_icon(self):
        if self.icon_name in self.icon_pixbufs:
            pixbuf = self.icon_pixbufs[self.icon_name]
        else:
            pixbuf = self.get_icon(self.icon_name)
            self.icon_pixbufs[self.icon_name] = pixbuf
        self.icon.set_from_pixbuf(pixbuf)
        
    def get_icon(self, icon_name):
        if icon_name.startswith("/") and os.path.exists(icon_name):
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(icon_name,
                                                          ICONSIZE, 
                                                          ICONSIZE)
        else:
            icon_theme = gtk.icon_theme_get_default()
            if self.icon_themepath != "" and \
               os.path.exists(self.icon_themepath):
                icon_theme.prepend_search_path(self.icon_themepath)
            pixbuf = icon_theme.load_icon(self.icon_name, ICONSIZE, 0)
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

    def position_menu(self, menu):
        x, y = self.get_window().get_origin()
        a = self.get_allocation()
        w, h = menu.size_request()
        size = self.applet_r().get_size()
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
        self.alignment = gtk.Alignment(0.5, 0.5)
        self.add(self.alignment)
        self.alignment.show()

        self.box = None
        self.repack()
        self.show()
        self.fdo = BUS.get_object("org.freedesktop.DBus",
                                  "/org/freedesktop/DBus")
        addresses = self.fdo.ListNames(dbus_interface="org.freedesktop.DBus")
        for address in addresses:
            if str(address) == "com.canonical.indicator.application":
                self.connect_dbus(address)
                break
        else:
            gobject.idle_add(self.start_service)
        self.fdo.connect_to_signal("NameOwnerChanged",
                                    self.on_name_change_detected,
                                    dbus_interface=\
                                    "org.freedesktop.DBus")
        self.menu = None

    def repack(self):
        children = []
        if self.box is not None:
            children = self.box.get_children()
            for child in children:
                self.box.remove(child)
            self.alignment.remove(self.box)
            self.box.destroy()
        if self.get_position() in ("left", "right"):
            self.box = gtk.VBox(False, 4)
        else:
            self.box = gtk.HBox(False, 4)
            self.container = gtk.HBox()
        self.box.set_border_width(4)
        self.alignment.add(self.box)
        for child in children:
            self.box.pack_start(child)
            child.repack()
        self.box.show_all()
        
    def start_service(self):
        for cmd in service_cmds:
            if os.path.exists(cmd):
                os.system("/bin/sh -c '%s' &" % cmd)
                break
        return False
    
    def on_name_change_detected(self, name, previous_owner, current_owner):
        if str(name) == "com.canonical.indicator.application":
            if previous_owner == "" and current_owner !="":
                self.connect_dbus(name)
            if previous_owner != "" and current_owner == "":
                print "indicator-application-service disappeared"
                self.disconnect_dbus()

    def connect_dbus(self, address):
        try:
            self.ayatana = BUS.get_object(address,
                                      "/org/ayatana/indicator/service")
        except:
            print "Error: Couldn't make dbus connection with %s" % address
            return
        self.ayatana.Watch(dbus_interface="org.ayatana.indicator.service",
                           reply_handler=self.reply_handler,
                           error_handler=self.error_handler)
        self.obj = BUS.get_object(address,
                                "/com/canonical/indicator/application/service")
        self.obj.GetApplications(
                dbus_interface="com.canonical.indicator.application.service", 
                reply_handler=self.indicators_loaded,
                error_handler=self.error_loading)

    def disconnect_dbus(self):
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
        ind = AppIndicator(self, *args)
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
        indicators = self.box.get_children()
        ind = indicators[position]
        ind.on_icon_changed(icon_name, icon_desc)

    def on_icon_themepath_changed(self, position, path):
        indicators = self.box.get_children()
        ind = indicators[position]
        ind.on_themepath_changed(path)

    def on_label_changed(self, position, label, guide):
        indicators = self.box.get_children()
        ind = indicators[position]
        ind.on_label_changed(label, guide)

    def on_title_changed(self, position, title):
        indicators = self.box.get_children()
        ind = indicators[position]
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
        aiapplet.repack()
    except:
        # First run, make a new instance
        aiapplet = AppIndicatorApplet(dbx_dict)
    return aiapplet
