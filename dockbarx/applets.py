#!/usr/bin/python3

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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
import os
import importlib.util
import dbus
import weakref
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
from .log import logger
from .common import Globals
from .dirutils import get_app_dirs
from . import i18n
_ = i18n.language.gettext


DBusGMainLoop(set_as_default=True) # for async calls
BUS = dbus.SessionBus()


def get_applet_gsetting(applet_id):
    schema_id = "org.dockbarx.applets.%s" % applet_id
    path = "/org/dockbarx/applets/%s/" % applet_id
    source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup(schema_id, True)
    if not schema:
        logger.error("No schema %s" % schema_id)
        return (None, 1)
    if schema.get_path() != path:
        logger.error("No %s in schema %s" % (path, schema_id))
        return (None, 1)
    return (Gio.Settings.new_with_path(schema_id, path), schema)

def set_applet_setting(gsettings, gschema, key, value, empty_list_type=str):
    if type(key) != str:
        logger.error("The key must be a string")
        return
    key = key.replace("_", "-")
    if gschema is not None:
        if not gschema.has_key(key):
            logger.error("No %s in schema %s" % (key, gschema.get_id()))
            return
    if value is None:
        gsettings.reset(key)
        gsettings.sync()
        return

    basic_types = {
       str: "s",
       bool: "b",
       int: "i",
       float: "d"
    }
    if isinstance(value, list):
        if len(value) == 0:
            if empty_list_type in basic_types:
                vtype = "a%s" % basic_types[empty_list_type]
            else:
                logger.error("Unsupported type: %s" % empty_list_type)
                return
        else:
            if type(value[0]) not in basic_types:
                logger.error("The values in list must be string, bool, int, or float")
                return
            for v in value:
                if type(v) != type(value[0]):
                    logger.error("All values in the list must be of the same sort")
                    return
            vtype = "a%s" % basic_types[type(value[0])]
    else:
        vtype = None
        for t in basic_types:
            if isinstance(value, t):
                vtype = basic_types[t]
                break
        if vtype is None:
            logger.error("The value must be a string, bool, int, float, or list")
            return
    if gsettings.set_value(key, GLib.Variant(vtype, value)):
        gsettings.sync()

def get_applet_setting(gsettings, gschema, key):
    if type(key) != str:
        logger.error("The key must be a string")
        return None
    key = key.replace("_", "-")
    if gschema is not None:
        if not gschema.has_key(key):
            logger.error("No %s in schema %s" % (key, gschema.get_id()))
            return None
    return gsettings.get_value(key).unpack()

def get_applet_default_setting(gsettings, gschema, key):
    if type(key) != str:
        logger.error("The key must be a string")
        return None
    key = key.replace("_", "-")
    if gschema is not None:
        if not gschema.has_key(key):
            logger.error("No %s in schema %s" % (key, gschema.get_id()))
            return None
    return gsettings.get_default_value(key).unpack()

class DockXApplets():
    def __init__(self):
        self.find_applets()
        self.globals = Globals()

    def find_applets(self):
        # Reads the applets from DATA_DIRS/dockbarx/applets
        # and returns a dict of the applets file names and paths so that a
        # applet can be loaded.
        self.applets = {}
        app_dirs = get_app_dirs()
        applets_dirs = [ os.path.join(d, "applets") for d in app_dirs ]
        for d in applets_dirs:
            num_sep = d.count(os.path.sep)
            for root, dirs, files in os.walk(d):
                for f in files:
                    name, ext = os.path.splitext(os.path.basename(f))
                    if ext.lower() != ".applet":
                        continue
                    path = os.path.join(root, f)
                    applet, err = self.read_applet_file(path)
                    if err is not None:
                        logger.debug("Error: Did not load applet from %s: %s" % (path, err))
                        continue
                    name = applet["name"]
                    if name not in self.applets:
                        applet["dir"] = root
                        self.applets[name] = applet
                if num_sep + 1 <= root.count(os.path.sep):
                    del dirs[:]

    def read_applet_file(self, path):
        try:
            f = open(path)
        except:
            text = "Cannot open applet"
            return None, text
        try:
            lines = f.readlines()
        except:
            lines = None
        finally:
            f.close()
        if not lines or not lines[0].lower().strip() == "@dbx applet":
            text = "Doesn't seem to be a dbx applet"
            return None, text
        description_nr = None
        settings = {}
        for i in range(len(lines)):
            line = lines[i]
            if line.strip().lower() == "@description":
                description_nr = i + 1
                break
            # Split at "=" and clean up the key and value
            if not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip().lower()
            value = value.strip().lstrip()
            # Remove comments
            if "#" in key:
                continue
            # If there is a trailing comment, remove it
            # But avoid removing # if it's in a quote
            sharp = value.find("#")
            if sharp != -1 and value.count("\"", 0, sharp) % 2 == 0 and \
               value.count("'", 0, sharp) % 2 == 0:
                   value = value.split("#", 1)[0].strip()
            # Remove quote signs
            if value[0] in ("\"", "'") and value[-1] in ("\"", "'"):
                value = value[1:-1]
            
            if key == "name":
                name = value
            settings[key] = value
        if "name" not in settings:
            text = "The applet has no name"
            return None, text
        if "exec" not in settings:
            text = "Applet %s has no exec" % name
            return None, text
        if description_nr is None or description_nr >= len(lines):
            text = "Applet %s has no description" % name
            return None, text
        settings["description"] =  "\n".join(lines[description_nr:])
        return settings, None

    def get(self, name):
        e = self.applets[name]["exec"]
        iname, ext = os.path.splitext(os.path.split(e)[-1])
        path = os.path.join(self.applets[name]["dir"], e)
        try:
            spec = importlib.util.spec_from_file_location(iname, path)
            applet = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(applet)
        except:
            message = "Error: Could not load applet from %s. " % path
            message += "Could not import the script."
            logger.exception(message)
            return
        return applet

    def get_id(self, name):
        try:
            return self.applets[name]["id"]
        except:
            return ""

    def get_description(self, name):
        try:
            return self.applets[name]["description"]
        except:
            return ""

    def get_list(self):
        old_list = self.globals.settings["applets/enabled_list"]
        all_applets = list(self.applets.keys()) + ["DockbarX", "Spacer"]
        applet_list = [a for a in old_list if a in all_applets]
        if not "DockbarX" in applet_list:
            applet_list.append("DockbarX")
        if applet_list != old_list:
            self.globals.set_applets_enabled_list(applet_list)
        return applet_list

    def get_unused_list(self):
        applet_list = self.globals.settings["applets/enabled_list"]
        all_applets = list(self.applets.keys())
        unused_applets = [a for a in all_applets if a not in applet_list]
        # There should be totally two spacers.
        while (unused_applets + applet_list).count("Spacer") < 2:
            unused_applets.append("Spacer")
        return unused_applets
        
        
    def set_list(self, applet_list):
        all_applets = list(self.applets.keys()) + ["DockbarX", "Spacer"]
        applet_list = [a for a in applet_list if a in all_applets]
        if not "DockbarX" in applet_list:
            applet_list.append("DockbarX")
        self.globals.set_applets_enabled_list(applet_list)
        

class DockXApplet(Gtk.EventBox):
    """This is the base class for DockX applets"""
    
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST,
                                None,(Gdk.Event, ))}

    def __init__(self, dbx_dict):
        self.__dockx_r = weakref.ref(dbx_dict["dock"])
        self.__applet_id = dbx_dict["id"]
        self.__inited = False
        GObject.GObject.__init__(self)
        self.set_visible_window(False)
        self.set_no_show_all(True)
        self.mouse_pressed = False
        self.expand = False
        self.connect("enter-notify-event", self.on_enter_notify_event)
        self.connect("leave-notify-event", self.on_leave_notify_event)
        self.connect("button-release-event", self.on_button_release_event)
        self.connect("button-press-event", self.on_button_press_event)
        if self.__applet_id:
            self.__settings, self.__schema = get_applet_gsetting(self.__applet_id)
            if self.__settings is not None:
                self.__sid = self.__settings.connect("changed", self.__on_settings_changed)
                self.__setting_key = None
        else:
            self.__settings = None
            self.__schema = None

    def get_id(self):
        return self.__applet_id

    def __check_settings(self):
        if self.__settings is not None:
            return True
        if self.__schema is not None:
            logger.error("Error: Cannot use applet settings " \
                         "with an invalid id in the .applet file")
        else:
            logger.error("Error: Cannot use applet settings " \
                         "without an id in the .applet file")
        return False

    def get_setting(self, key):
        if not self.__check_settings():
            return
        return get_applet_setting(self.__settings, self.__schema, key)

    def get_default_setting(self, key):
        if not self.__check_settings():
            return
        return get_applet_default_setting(self.__settings, self.__schema, key)

    def set_setting(self, key, value, empty_list_type=None, ignore_changed_event=True):
        if not self.__check_settings():
            return
        if ignore_changed_event:
            self.__setting_key = key
        set_applet_setting(self.__settings, self.__schema, key, value, empty_list_type)
        self.__setting_key = None

    def on_setting_changed(self, key, value):
        # Method to be overridden by applet.
        pass

    def __on_settings_changed(self, gsettings, key):
        _key = key.replace("-", "_")
        if _key == self.__setting_key:
            return
        value = get_applet_setting(gsettings, self.__schema, key)
        self.on_setting_changed(_key, value)

    def update(self):
        # Method to be overridden by applet.
        pass

    def get_full_size(self):
        if self.__dockx_r:
            dockx = self.__dockx_r()
            rel_size = float(dockx.theme.get("rel_size", 100))
            size = dockx.globals.settings["dock/size"]
            return max(size, int(size * rel_size / 100))
    
    def get_size(self):
        if self.__dockx_r:
            return self.__dockx_r().globals.settings["dock/size"]

    def get_position(self):
        if self.__dockx_r:
            return self.__dockx_r().globals.settings["dock/position"]

    def get_monitor(self):
        if self.__dockx_r:
            return self.__dockx_r().monitor

    def get_expand(self):
        return self.expand
        
    def get_applet_size(self):
        if not self.__dockx_r:
            return 0
        if not self.get_visible():
            return 0
        if self.get_position() in ("top", "bottom"):
            return self.get_allocation().width
        else:
            return self.get_allocation().height

    def finish_init(self):
        self.__inited = True

    def set_expand(self, expand):
        if self.__inited:
            if self.__dockx_r:
                GLib.idle_add(self.__dockx_r().reload_applets)
            else:
                self.expand = expand
        else:
            self.expand = expand

    def on_button_release_event(self, widget, button_event):
        if self.mouse_pressed:
            event = Gdk.Event();
            for p in [ "type", "window", "send_event", "time", "x", "y", "state", "button", "device", "x_root", "y_root" ]:
                setattr(event.button, p, getattr(button_event, p))
            self.emit("clicked", event)
        self.mouse_pressed=False

    def on_button_press_event(self, widget, event):
        self.mouse_pressed = True
    
    def on_leave_notify_event(self, *args):
        self.mouse_pressed = False

    def on_enter_notify_event(self, *args):
        pass

    def debug(self, text):
        logger.debug(text)
        
    def destroy(self):
        if self.__settings is not None:
            self.__settings.disconnect(self.__sid)
        super().destroy()


class DockXAppletDialog(Gtk.Dialog):
    Title = "Applet Preferences"
    def __init__(self, applet_id, title=Title, flags=0,
                 buttons=(_("_Close"), Gtk.ResponseType.CLOSE)):
        Gtk.Dialog.__init__(self, title=title, flags=flags, buttons=buttons)
        GObject.GObject.__init__(self)
        if applet_id:
            self.__applet_id = applet_id
            self.__settings, self.__schema = get_applet_gsetting(self.__applet_id)
            if self.__settings is not None:
                # Set gsettings notifiers
                self.__sid = self.__settings.connect("changed", self.__on_settings_changed)
                self.__setting_key = None
        else:
            self.__settings = None
            self.__schema = None

    def __check_settings(self):
        if self.__settings is not None:
            return True
        if self.__schema is not None:
            logger.error("Error: Cannot use applet settings " \
                         "with an invalid id in the .applet file")
        else:
            logger.error("Error: Cannot use applet settings " \
                         "without an id in the .applet file")
        return False

    def get_setting(self, key):
        if not self.__check_settings():
            return
        return get_applet_setting(self.__settings, self.__schema, key)

    def get_default_setting(self, key):
        if not self.__check_settings():
            return
        return get_applet_default_setting(self.__settings, self.__schema, key)

    def set_setting(self, key, value, empty_list_type=None, ignore_changed_event=True):
        if not self.__check_settings():
            return
        if ignore_changed_event:
            self.__setting_key = key
        set_applet_setting(self.__settings, self.__schema, key, value, empty_list_type)
        self.__setting_key = None

    def on_setting_changed(self, key, value):
        # Method to be overridden by applet.
        pass

    def __on_settings_changed(self, gsettings, key):
        _key = key.replace("-", "_")
        if _key == self.__setting_key:
            return
        value = get_applet_setting(gsettings, self.__schema, key)
        self.on_setting_changed(_key, value)

    def debug(self, text):
        logger.debug(text)

    def destroy(self):
        if self.__settings is not None:
            self.__settings.disconnect(self.__sid)
        super().destroy()

