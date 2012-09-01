#!/usr/bin/python

#   DockbarX applets
#
#	Copyright 2011 Matias Sars
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
#	along with dockbar.  If not, see <http://www.gnu.org/licenses

import gtk
import os
import imp
import gconf
import dbus
import weakref
import gobject
from dbus.mainloop.glib import DBusGMainLoop
from log import logger

GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = "/apps/dockbarx"

DBusGMainLoop(set_as_default=True) # for async calls
BUS = dbus.SessionBus()
           
class DockXApplets():
    def __init__(self):
        self.find_applets()

    def find_applets(self):
        # Reads the themes from /usr/share/dockbarx/themes/dock_themes and
        # ~/.dockbarx/themes/dock_themes and returns a dict
        # of the theme file names and paths so that a theme can be loaded
        self.applets = {}
        home_folder = os.path.expanduser("~")
        theme_folder = home_folder + "/.dockbarx/applets"
        dirs = ["/usr/share/dockbarx/applets", theme_folder]
        for dir in dirs:
            if not(os.path.exists(dir) and os.path.isdir(dir)):
                continue
            for f in os.listdir(dir):
                name, ext = os.path.splitext(os.path.split(f)[-1])
                if not(f.startswith("dbx_applet_") and ext.lower() == ".py"):
                    continue
                path = os.path.join(dir, f)
                try:
                    applet = imp.load_source(name, path)
                except:
                    message = "Could not load applet from %s. " % path
                    message += "Could not import the script."
                    logger.exception(message)
                if not hasattr(applet, "get_dbx_applet"):
                    continue
                try:
                    name = applet.APPLET_NAME
                except AttributeError:
                    message = "Could not load applet from %s. " % path
                    message += "It has no applet name."
                    logger.exception(message)
                    continue
                # Todo: More intelligent selecting of applets with same name.
                # Version control perhaps?
                if  name not in self.applets:
                    self.applets[name] = applet

    def get(self, name):
        return self.applets[name]

    def get_description(self, name):
        try:
            return self.applets[name].APPLET_DESCRIPTION
        except:
            return ""

    def get_list(self):
        try:
            old_list = GCONF_CLIENT.get_list(GCONF_DIR + \
                                             "/applets/applet_list",
                                             gconf.VALUE_STRING)
        except:
            raise
            GCONF_CLIENT.set_list(GCONF_DIR + "/applets/applet_list",
                                  gconf.VALUE_STRING,
                                  ["DockbarX"])
            return ["DockbarX"]
        all_applets = self.applets.keys() + ["DockbarX", "Spacer"]
        applet_list = [a for a in old_list if a in all_applets]
        if not "DockbarX" in applet_list:
            applet_list.append("DockbarX")
        if applet_list != old_list:
            GCONF_CLIENT.set_list(GCONF_DIR + "/applets/applet_list",
                                  gconf.VALUE_STRING,
                                  applet_list)
        return applet_list

    def get_unused_list(self):
        try:
            applet_list = GCONF_CLIENT.get_list(GCONF_DIR + \
                                                "/applets/applet_list",
                                                gconf.VALUE_STRING)
        except:
            GCONF_CLIENT.set_list(GCONF_DIR + "/applets/applet_list",
                                  gconf.VALUE_STRING,
                                  ["DockbarX"])
            applet_list = ["DockbarX"]
        all_applets = self.applets.keys() + ["Spacer"]
        return [a for a in all_applets if a not in applet_list]
        
        
    def set_list(self, applet_list):
        all_applets = self.applets.keys() + ["DockbarX", "Spacer"]
        applet_list = [a for a in applet_list if a in all_applets]
        if not "DockbarX" in applet_list:
            applet_list.append("DockbarX")
        GCONF_CLIENT.set_list(GCONF_DIR+"/applets/applet_list",
                              gconf.VALUE_STRING,
                              applet_list)

# Functions used by both DockXApplet and DockXAppletDialog
def set_setting(key, value, list_type=None, applet_name=None):
    if applet_name is None:
        return
    gdir = "%s/applets/%s" % (GCONF_DIR, applet_name)
    gconf_set = { str: GCONF_CLIENT.set_string,
                  bool: GCONF_CLIENT.set_bool,
                  float: GCONF_CLIENT.set_float,
                  int: GCONF_CLIENT.set_int }
    if type(value) == list:
        list_types = { str: gconf.VALUE_STRING,
                       bool: gconf.VALUE_BOOL,
                       float: gconf.VALUE_FLOAT,
                       int: gconf.VALUE_INT }
        if len(value) == 0:
            if type(list_type) in list_types:
                lt = list_types[type(list_type)]
            else:
                lt = GCONF_CLIENT.set_string
        else:
            for v in values:
                if v != value[0]:
                    raise ValueError(
                        "All values in the list must be of the same sort")
            lt = list_types[type(value[0])]
        GCONF_CLIENT.set_list(GCONF_DIR + "/applets/applet_list",
                              list_types, VALUE)
        
    else:
        if type(value) not in gconf_set:
            raise ValueError(
                    "The value must be a string, bool, int or list")
        gconf_set[type(value)]("%s/%s" % (gdir, key), value)
        

def get_setting(key, default=None, applet_name=None):
    if applet_name is None:
        return
    gdir = "%s/applets/%s" % (GCONF_DIR, applet_name)
    try:
        value = GCONF_CLIENT.get_value("%s/%s" % (gdir, key))
    except:
        if default is not None:
            set_setting(key, default, applet_name=applet_name)
        return default
    return value


def get_value(value):
    if value.type == gconf.VALUE_LIST:
        return [get_value(item) for item in value.get_list()]
    else:
        return {
                "string": value.get_string,
                "int": value.get_int,
                "float": value.get_float,
                "bool": value.get_bool,
                "list": value.get_list
               }[value.type.value_nick]()

class DockXApplet(gtk.EventBox):
    """This is the base class for DockX applets"""
    
    __gsignals__ = {"clicked": (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,(gtk.gdk.Event, )),
                    "enter-notify-event": "override",
                    "leave-notify-event": "override",
                    "button-release-event": "override",
                    "button-press-event": "override"}

    def __init__(self, applet_name, dockx):
        self.dockx_r = weakref.ref(dockx)
        self.applet_name = applet_name.lower().replace(" ", "")
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.set_no_show_all(True)
        self.mouse_pressed = False
        # Set gconf notifiers
        gdir = "%s/applets/%s" % (GCONF_DIR, self.applet_name)
        GCONF_CLIENT.add_dir(gdir, gconf.CLIENT_PRELOAD_NONE)
        GCONF_CLIENT.notify_add(gdir, self.__on_gconf_changed, None)

    def get_setting(self, *args, **kwargs):
        kwargs["applet_name"]=self.applet_name
        return get_setting(*args, **kwargs)

    def set_setting(self, *args, **kwargs):
        kwargs["applet_name"]=self.applet_name
        return set_setting(*args, **kwargs)

    def on_setting_changed(self, key, value):
        # Method to be overridden by applet.
        pass

    def __on_gconf_changed(self, client, par2, entry, par4):
        if entry.get_value() is None:
            return
        key = entry.get_key().split("/")[-1]
        value = get_value(entry.get_value())
        self.on_setting_changed(key, value)

    def get_full_size(self):
        if self.dockx_r:
            dockx = self.dockx_r()
            rel_size = float(dockx.theme.get("rel_size", 100))
            size = dockx.globals.settings["dock/size"]
            return max(size, int(size * rel_size / 100))

    
    def get_size(self):
        if self.dockx_r:
            return self.dockx_r().globals.settings["dock/size"]

    def get_position(self):
        if self.dockx_r:
            return self.dockx_r().globals.settings["dock/position"]

    def do_button_release_event(self, event):
        if self.mousepressed:
            self.emit("clicked", event)
        self.mousepressed=False

    def do_button_press_event(self, event):
        self.mousepressed = True
    
    def do_leave_notify_event(self, *args):
        self.mousepressed = False

    def do_enter_notify_event(self, *args):
        pass
        

class DockXAppletDialog(gtk.Dialog):
    Title = "Applet Preferences"
    def __init__(self, applet_name, t=None, flags=0,
                 buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)):
        self.applet_name = applet_name.lower().replace(" ", "")
        if t is None:
            t = self.Title
        gtk.Dialog.__init__(self, _(t), None, flags, buttons)

    def get_setting(self, *args, **kwargs):
        kwargs["applet_name"]=self.applet_name
        return get_setting(*args, **kwargs)

    def set_setting(self, *args, **kwargs):
        kwargs["applet_name"]=self.applet_name
        return set_setting(*args, **kwargs)
