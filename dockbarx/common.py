#!/usr/bin/python3

#   common.py
#
#	Copyright 2008, 2009, 2010 Aleksey Shaferov and Matias Sars
#
#	DockBar is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	DockBar is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

import os
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
import xdg.DesktopEntry
from urllib.parse import unquote
from time import time
from gi.repository import Gtk
import weakref
import locale
from .log import logger
import sys
import struct


DBusGMainLoop(set_as_default=True) # for async calls
BUS = dbus.SessionBus()

def compiz_call_sync(obj_path, func_name, *args):
    # Returns a compiz function call.
    # No errors are dealt with here,
    # error handling are left to the calling function.
    path = "/org/freedesktop/compiz"
    if obj_path:
        path += "/" + obj_path
    obj = BUS.get_object("org.freedesktop.compiz", path)
    iface = dbus.Interface(obj, "org.freedesktop.compiz")
    func = getattr(iface, func_name)
    if func:
        return func(*args)
    return None

def compiz_reply_handler(*args):
    pass

def compiz_error_handler(error, *args):
    logger.warning("Compiz/dbus error: %s" % error)

def compiz_call_async(obj_path, func_name, *args):
    path = "/org/freedesktop/compiz"
    if obj_path:
        path += "/" + obj_path
    obj = BUS.get_object("org.freedesktop.compiz", path)
    iface = dbus.Interface(obj, "org.freedesktop.compiz")
    func = getattr(iface, func_name)
    if func:
        func(reply_handler=compiz_reply_handler,
             error_handler=compiz_error_handler, *args)

def check_program(name):
    # Checks if a program exists in PATH
    for dir in os.environ['PATH'].split(':'):
        prog = os.path.join(dir, name)
        if os.path.exists(prog): return prog
        
appdir = None
def get_app_homedir():
    global appdir
    if appdir is not None:
        return appdir
    homedir = os.environ['HOME']
    default = os.path.join(homedir, '.local', 'share')
    appdir = os.path.join(
    os.getenv('XDG_DATA_HOME', default),
    'dockbarx'
    )
    """
    Migration Path
    From "$HOME/.dockbarx" to "${XDG_DATA_HOME:-$HOME/.local/share}/dockbarx"
    """
    old_appdir = os.path.join(homedir, '.dockbarx')
    if os.path.exists(old_appdir) and os.path.isdir(old_appdir):
        try:
            os.rename(old_appdir, appdir)
        except OSError:
            sys.stderr.write(
            "Could not move dir '%s' to '%s'. Move the contents of '%s' to '%s' manually and then remove the first location.\n"
            % (old_appdir, appdir, old_appdir, appdir)
            )
    """
    End Migration Path
    """
    return appdir


class Connector():
    """A class to simplify disconnecting of signals"""
    def __init__(self):
        self.connections = weakref.WeakKeyDictionary()

    def connect(self, obj, signal, handler, *args):
            sids = self.connections.get(obj, [])
            sids.append(obj.connect(signal, handler, *args))
            self.connections[obj] = sids

    def connect_after(self, obj, signal, handler, *args):
            sids = self.connections.get(obj, [])
            sids.append(obj.connect_after(signal, handler, *args))
            self.connections[obj] = sids

    def disconnect(self, obj):
        sids = self.connections.pop(obj, None)
        while sids:
            try:
                obj.disconnect(sids.pop())
            except:
                raise


class ODict():
    """An ordered dictionary.

    Has only the most needed functions of a dict, not all."""
    def __init__(self, d=[]):
        if not type(d) in (list, tuple):
            raise TypeError(
                        "The argument has to be a list or a tuple or nothing.")
        self.list = []
        for t in d:
            if not type(d) in (list, tuple):
                raise ValueError(
                        "Every item of the list has to be a list or a tuple.")
            if not len(t) == 2:
                raise ValueError(
                        "Every tuple in the list needs to be two items long.")
            self.list.append(t)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        t = (key, value)
        self.list.append(t)

    def __delitem__(self, key):
        self.remove(key)

    def __len__(self):
        self.list.__len__()

    def __contains__(self, key):
        for t in self.list:
            if t[0] == key:
                return True
        else:
            return False

    def __iter__(self):
        return list(self.keys()).__iter__()

    def __eq__(self, x):
        if type(x) == dict:
            d = {}
            for t in self.list:
                d[t[0]] = t[1]
            return (d == x)
        elif x.__class__ == self.__class__:
            return (self.list == x.list)
        else:
            return (self.list == x)

    def __len__(self):
        return len(self.list)

    def values(self):
        values = []
        for t in self.list:
            values.append(t[1])
        return values

    def keys(self):
        keys = []
        for t in self.list:
            keys.append(t[0])
        return keys

    def items(self):
        return self.list

    def add_at_index(self, index, key, value):
        t = (key, value)
        self.list.insert(index, t)

    def get(self, key, default=None):
        for t in self.list:
            if t[0] == key:
                return t[1]
        return default

    def get_index(self, key):
        for t in self.list:
            if t[0] == key:
                return self.list.index(t)

    def move(self, key, index):
        for t in self.list:
            if key == t[0]:
                self.list.remove(t)
                self.list.insert(index, t)

    def remove(self, key):
        for t in self.list:
            if key == t[0]:
                self.list.remove(t)

    def has_key(self, key):
        for t in self.list:
            if key == t[0]:
                return True
        else:
            return False

class DesktopEntry(xdg.DesktopEntry.DesktopEntry):
    def __init__(self, file_name):
        xdg.DesktopEntry.DesktopEntry.__init__(self, file_name)
        # Quicklist
        self.quicklist = ODict()
        if not "Actions" in self.content["Desktop Entry"]:
            return
        entries = self.content["Desktop Entry"]["Actions"]
        entries = entries.split(";")
        for entry in entries:
            sg = self.content.get("Desktop Action %s" % entry)
            if not sg:
                continue
            lo = locale.getlocale()[0]
            n = "Name[%s]"
            name = sg.get(n % lo) or sg.get(n % lo[:2])
            if name is None:
                for s in sg:
                    if s.startswith("Name[" + lo[:2]):
                        name = sg[s]
                        break
                else:
                    name = sg.get("Name")
            exe = sg.get("Exec")
            if name and exe:
                self.quicklist[name] = exe

    def launch(self, uri=None, command=None):
        if command is None:
            command = self.getExec()

        os.chdir(os.path.expanduser("~"))
        if command == "":
            return

        # Replace arguments
        if "%i" in command:
            icon = self.getIcon()
            if icon:
                command = command.replace("%i","--icon %s"%icon)
            else:
                command = command.replace("%i", "")
        command = command.replace("%c", self.getName())
        command = command.replace("%k", self.getFileName())
        command = command.replace("%%", "%")
        for arg in ("%d", "%D", "%n", "%N", "%v", "%m", "%M","--view"):
            command = command.replace(arg, "")
        # TODO: check if more unescaping is needed.

        # Parse the uri
        uris = []
        files = []
        if uri:
            uri = str(uri)
            # Multiple uris are separated with newlines
            uri_list = uri.split("\n")
            for uri in uri_list:
                uri = uri.rstrip()
                file = uri

                # Nautilus and zeitgeist don't encode ' and " in uris and
                # that's needed if we should launch with /bin/sh -c
                uri = uri.replace("'", "%27")
                uri = uri.replace('"', "%22")
                uris.append(uri)

                if file.startswith("file://"):
                    file = file[7:]
                file = file.replace("%20","\ ")
                file = unquote(file)
                files.append(file)

        # Replace file/uri arguments
        if "%f" in command or "%u" in command:
            # Launch once for every file (or uri).
            iterlist = list(range(max(1, len(files))))
        else:
            # Launch only one time.
            iterlist = [0]
        for i in iterlist:
            cmd = command
            # It's an assumption that no desktop entry has more than one
            # of "%f", "%F", "%u" or "%U" in it's command. Othervice some
            # files might be launched multiple times with this code.
            if "%f" in cmd:
                try:
                    f = files[i]
                except IndexError:
                    f = ""
                cmd = cmd.replace("%f", f)
            elif "%u" in cmd:
                try:
                    u = uris[i]
                except IndexError:
                    u = ""
                cmd = cmd.replace("%u", u)
            elif "%F" in cmd:
                cmd = cmd.replace("%F", " ".join(files))
            elif "%U" in cmd:
                cmd = cmd.replace("%U", " ".join(uris))
            # Append the files last if there is no rule for how to append them.
            elif files:
                cmd = "%s %s"%(cmd, " ".join(files))

            logger.info("Executing: %s"%cmd)
            os.system("/bin/sh -c '%s' &"%cmd)

    def get_quicklist(self):
        return self.quicklist

    def launch_quicklist_entry(self, entry, uri=None):
        if not entry in self.quicklist:
            return
        self.launch(uri, self.quicklist[entry])

    def getIcon(self, *args):
        try:
            return xdg.DesktopEntry.DesktopEntry.getIcon(self, *args)
        except:
            logger.warning("Couldn't get icon name from a DesktopEntry")
            return None




class Opacify():
    def __init__(self):
        self.opacifier = None
        self.old_windows = None
        self.sids = {}
        self.globals = Globals()

    def opacify(self, windows, opacifier=None):
        """Add semi-transparency to windows"""
        if type(windows) in [int, int]:
            windows = [windows]
        if windows:
            windows = [str(xid) for xid in windows]
        if windows and windows == self.old_windows:
            self.opacifier = opacifier
            return
        try:
            values = compiz_call_sync("obs/screen0/opacity_values","get")[:]
            matches = compiz_call_sync("obs/screen0/opacity_matches","get")[:]
            self.use_old_call = False
        except:
            # For older versions of compiz
            try:
                values = compiz_call_sync("core/screen0/opacity_values", "get")
                matches = compiz_call_sync("core/screen0/opacity_matches",
                                              "get")
                self.use_old_call = True
            except:
                return
        # If last fade in/out isn't completed abort the rest of it.
        while self.sids:
            GLib.source_remove(self.sids.popitem()[1])

        steps = self.globals.settings["opacify_smoothness"]
        interval = self.globals.settings["opacify_duration"] / steps
        alpha = self.globals.settings["opacify_alpha"]
        use_fade = self.globals.settings["opacify_fade"]
        placeholder = "(title=Placeholder_line_for_DBX)"
        placeholders = [placeholder, placeholder, placeholder]
        rule_base = "(type=Normal|type=Dialog)&%s&!title=Line_added_by_DBX"
        # Remove old opacify rule if one exist
        old_values = []
        for match in matches[:]:
            if "Line_added_by_DBX" in str(match) or \
               "Placeholder_line_for_DBX" in str(match):
                i = matches.index(match)
                matches.pop(i)
                try:
                    old_values.append(max(values.pop(i), alpha))
                except IndexError:
                    pass
        if not self.globals.settings["opacify_fade"]:
            if windows:
                matches.insert(0,
                               rule_base % "!(xid=%s)" % "|xid=".join(windows))
                self.__compiz_call([alpha]+values, matches)
            else:
                self.__compiz_call(values, matches)
            self.opacifier = opacifier
            self.old_windows = windows
            return

        matches = placeholders + matches
        if len(old_values)>3:
            old_values = old_values[0:2]
        while len(old_values)<3:
            old_values.append(alpha)
        min_index = old_values.index(min(old_values))
        max_index = old_values.index(max(old_values))
        if min_index == max_index:
            min_index = 2
        for x in (0,1,2):
            if x != max_index and x != min_index:
                mid_index = x
                break
        if self.old_windows and windows:
            # Both fade in and fade out needed.
            fadeins = [xid for xid in windows if not xid in self.old_windows]
            fadeouts = [xid for xid in self.old_windows if not xid in windows]

            matches[min_index] = rule_base % "!(xid=%s)" % \
                                 "|xid=".join(windows + fadeouts)
            if fadeouts:
                matches[max_index] = \
                               rule_base % "(xid=%s)" % "|xid=".join(fadeouts)
            if fadeins:
                matches[mid_index] = \
                               rule_base % "(xid=%s)" % "|xid=".join(fadeins)
            v = [alpha, alpha, alpha]
            for i in range(1, steps+1):
                if fadeins:
                    v[mid_index] = 100 - ((steps - i) * (100 - alpha) // steps)
                if fadeouts:
                    v[max_index] = 100 - (i*(100-alpha) // steps)
                sid = time()
                if i == 1:
                    self.__compiz_call(v + values, matches)
                else:
                    self.sids[sid] = GLib.timeout_add((i - 1) * interval,
                                                         self.__compiz_call,
                                                         v+values,
                                                         None,
                                                         sid)
        elif windows:
            # Fade in
            matches[max_index] = rule_base % "!(xid=%s)" % \
                                 "|xid=".join(windows) + "_"
            # The "_" is added since matches that change only on a "!" isn't
            # registered. (At least that's what I think.)
            v = [alpha, alpha, alpha]
            v[max_index] = 100
            self.__compiz_call(v + values, matches)
            for i in range(1, steps+1):
                v[max_index] = 100 - ( i * (100 - alpha) // steps)
                sid = time()
                self.sids[sid] = GLib.timeout_add(i * interval,
                                                     self.__compiz_call,
                                                     v + values,
                                                     None,
                                                     sid)
        else:
            # Deopacify
            v = [0, 0, 0]
            for i in range(1, steps):
                value = 100 - ((steps - i) * (100 - alpha) // steps)
                v = [max(value, old_value) for old_value in old_values]
                sid = time()
                self.sids[sid] = GLib.timeout_add(i * interval,
                                                     self.__compiz_call,
                                                     v + values,
                                                     None,
                                                     sid)
            delay = steps * interval + 1
            sid = time()
            v = [100, alpha, alpha]
            self.sids[sid] = GLib.timeout_add(delay,
                                                 self.__compiz_call,
                                                 v + values,
                                                 matches,
                                                 sid)
        self.opacifier = opacifier
        self.old_windows = windows

    def deopacify(self, opacifier=None):
        if opacifier is None or opacifier == self.opacifier:
            self.opacify(None)

    def set_opacifier(self, opacifier):
        if self.opacifier != None:
            self.opacifier = opacifier

    def get_opacifier(self):
        return self.opacifier

    def __compiz_call(self, values=None, matches=None, sid=None):
        if self.use_old_call:
            plugin = "core"
        else:
            plugin = "obs"
        if values is not None:
            compiz_call_async(plugin + "/screen0/opacity_values",
                              "set", values)
        if matches is not None:
            compiz_call_async(plugin + "/screen0/opacity_matches",
                              "set", matches)
        self.sids.pop(sid, None)



class Globals(GObject.GObject):
    """ Globals is a signletron containing all the "global" variables of dockbarx.

    It also keeps track of gconf settings and signals changes in gconf to other programs"""

    __gsignals__ = {
        "color2-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "show-only-current-desktop-changed": (GObject.SignalFlags.RUN_FIRST,
                                              None,()),
        "show-only-current-monitor-changed": (GObject.SignalFlags.RUN_FIRST,
                                              None,()),
        "theme-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "popup-style-changed": (GObject.SignalFlags.RUN_FIRST,
                                None,()),
        "color-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "dockmanager-changed": (GObject.SignalFlags.RUN_FIRST,
                                None,()),
        "dockmanager-badge-changed": (GObject.SignalFlags.RUN_FIRST,
                                      None,()),
        "badge-look-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "progress-bar-look-changed": (GObject.SignalFlags.RUN_FIRST,
                                      None,()),
        "media-buttons-changed": (GObject.SignalFlags.RUN_FIRST,
                                None,()),
        "quicklist-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "unity-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "show-tooltip-changed": (GObject.SignalFlags.RUN_FIRST,
                                 None,()),
        "show-previews-changed": (GObject.SignalFlags.RUN_FIRST,
                                  None,()),
        "preview-size-changed": (GObject.SignalFlags.RUN_FIRST,
                                 None,()),
        "window-title-width-changed": (GObject.SignalFlags.RUN_FIRST,
                                       None,()),
        "locked-list-in-menu-changed": (GObject.SignalFlags.RUN_FIRST,
                                         None,()),
        "locked-list-overlap-changed": (GObject.SignalFlags.RUN_FIRST,
                                         None,()),
        "preference-update": (GObject.SignalFlags.RUN_FIRST, None,()),
        "gkey-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "use-number-shortcuts-changed": (GObject.SignalFlags.RUN_FIRST,
                                         None,()),
        "show-close-button-changed": (GObject.SignalFlags.RUN_FIRST,
                                      None,()),
        "dock-size-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "dock-position-changed": (GObject.SignalFlags.RUN_FIRST,
                                      None,()),
        "dock-mode-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "dock-offset-changed": (GObject.SignalFlags.RUN_FIRST,
                                None,()),
        "dock-overlap-changed": (GObject.SignalFlags.RUN_FIRST,
                                 None,()),
        "dock-behavior-changed": (GObject.SignalFlags.RUN_FIRST,
                                  None,()),
        "dock-theme-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "dock-color-changed": (GObject.SignalFlags.RUN_FIRST, None,()),
        "dock-end-decorations-changed": (GObject.SignalFlags.RUN_FIRST,
                                  None,()),
        "awn-behavior-changed": (GObject.SignalFlags.RUN_FIRST,
                                  None,())
    }

    DEFAULT_SETTINGS = {
          "theme": "Glassified",
          "popup_style_file": "dbx.tar.gz",
          "groupbutton_attention_notification_type": "red",
          "workspace_behavior": "switch",
          "popup_delay": 250,
          "second_popup_delay": 30,
          "popup_align": "center",
          "no_popup_for_one_window": False,
          "show_only_current_desktop": False,
          "show_only_current_monitor": False,
          "preview": False,
          "preview_size": 150,
          "preview_minimized": True,
          "old_menu": False,
          "show_close_button": True,
          "locked_list_in_menu": True,
          "locked_list_no_overlap": False,
          "window_title_width": 140,
          "reorder_window_list": True,

          "select_one_window": "select or minimize window",
          "select_multiple_windows": "select or minimize all",
          "delay_on_select_all": True,
          "select_next_use_lastest_active": False,
          "select_next_activate_immediately": False,

          "dockmanager": False,
          "media_buttons": True,
          "quicklist": True,
          "unity": True,

          "badge_use_custom_font": False,
          "badge_font": "sans 10",
          "badge_custom_bg_color": False,
          "badge_bg_color": "#CDCDCD",
          "badge_bg_alpha": 255,
          "badge_custom_fg_color": False,
          "badge_fg_color": "#020202",
          "badge_fg_alpha": 255,

          "progress_custom_bg_color": False,
          "progress_bg_color": "#CDCDCD",
          "progress_bg_alpha": 64,
          "progress_custom_fg_color": False,
          "progress_fg_color": "#772953",
          "progress_fg_alpha": 255,

          "opacify": False,
          "opacify_group": False,
          "opacify_fade": True,
          "opacify_alpha": 5,
          "opacify_smoothness": 5,
          "opacify_duration": 100,

          "separate_wine_apps": True,
          "separate_prism_apps": True,
          "separate_ooo_apps": True,

          "groupbutton_show_tooltip": False,

          "groupbutton_left_click_action": "select",
          "groupbutton_shift_and_left_click_action": "launch application",
          "groupbutton_middle_click_action": "close all windows",
          "groupbutton_shift_and_middle_click_action": "no action",
          "groupbutton_right_click_action": "show menu",
          "groupbutton_shift_and_right_click_action": "no action",
          "groupbutton_scroll_up": "select previous window",
          "groupbutton_scroll_down": "select next window",
          "groupbutton_left_click_double": False,
          "groupbutton_shift_and_left_click_double": False,
          "groupbutton_middle_click_double": False,
          "groupbutton_shift_and_middle_click_double": False,
          "groupbutton_right_click_double": False,
          "groupbutton_shift_and_right_click_double": False,

          "windowbutton_left_click_action": "select or minimize window",
          "windowbutton_shift_and_left_click_action": \
                                            "select or minimize window",
          "windowbutton_middle_click_action": "close window",
          "windowbutton_shift_and_middle_click_action": "no action",
          "windowbutton_right_click_action": "show menu",
          "windowbutton_shift_and_right_click_action": "no action",
          "windowbutton_scroll_up": "shade window",
          "windowbutton_scroll_down": "unshade window",

          "windowbutton_close_popup_on_left_click": True,
          "windowbutton_close_popup_on_shift_and_left_click": False,
          "windowbutton_close_popup_on_middle_click": False,
          "windowbutton_close_popup_on_shift_and_middle_click": False,
          "windowbutton_close_popup_on_right_click": False,
          "windowbutton_close_popup_on_shift_and_right_click": False,
          "windowbutton_close_popup_on_scroll_up": False,
          "windowbutton_close_popup_on_scroll_down": False,

          "gkeys_select_next_group": False,
          "gkeys_select_next_group_keystr": "<super>Tab",
          "gkeys_select_previous_group": False,
          "gkeys_select_previous_group_keystr": "<super><shift>Tab",
          "gkeys_select_next_window": False,
          "gkeys_select_next_window_keystr": "<super><control>Tab",
          "gkeys_select_previous_window": False,
          "gkeys_select_previous_window_keystr": "<super><control><shift>Tab",
          "gkeys_select_next_group_skip_launchers": False,
          "use_number_shortcuts": True,
          "launchers": [],

          "dock/theme_file": "dbx.tar.gz",
          "dock/position": "left",
          "dock/size": 42,
          "dock/offset":0,
          "dock/mode": "centered",
          "dock/behavior": "panel",
          "dock/end_decorations": False,

          "awn/behavior": "disabled"}

    DEFAULT_COLORS={
                      "color1": "#333333",
                      "color1_alpha": 170,
                      "color2": "#FFFFFF",
                      "color3": "#FFFF75",
                      "color4": "#9C9C9C",

                      "color5": "#FFFF75",
                      "color5_alpha": 160,
                      "color6": "#000000",
                      "color7": "#000000",
                      "color8": "#000000",}

    def __new__(cls, *p, **k):
        if not "_the_instance" in cls.__dict__:
            cls._the_instance = GObject.GObject.__new__(cls)
        return cls._the_instance

    def __init__(self):
        if not "settings" in self.__dict__:
            # First run.
            GObject.GObject.__init__(self)

            # "Global" variables
            self.gtkmenu = None
            self.opacified = False
            self.opacity_values = None
            self.opacity_matches = None
            self.dragging = False
            self.theme_name = None
            self.theme_gsettings = None
            self.dock_theme_gsettings = None
            self.popup_style_file = None
            self.default_popup_style = None
            self.default_theme_colors = {}
            self.default_theme_alphas = {}
            self.dock_colors = {}
            self.old_dock_gs_colors = {}
            self.default_dock_colors={}
            self.__compiz_version = None

            self.set_shown_popup(None)
            self.set_locked_popup(None)

            self.gsettings = Gio.Settings.new_with_path("org.dockbarx.dockbarx", "/org/dockbarx/dockbarx/")
            self.dock_gsettings = Gio.Settings.new_with_path("org.dockbarx.dockx", "/org/dockbarx/dockx/")
            self.settings = self.__get_settings(self.DEFAULT_SETTINGS)

            self.gsettings.connect("changed", self.__on_gsettings_changed)
            self.dock_gsettings.connect("changed", self.__on_dock_gsettings_changed)


            self.colors = {}

    def __on_gsettings_changed(self, settings, gkey, data=None):
        key = gkey.replace("-", "_")
        if not key in self.settings:
            print("The changed setting is not in settings dictionary:", key)
            return
        self.settings[key] = self.gsettings.get_value(gkey).unpack()
        #~ entry_get = { str: entry.get_value().get_string,
                      #~ bool: entry.get_value().get_bool,
                      #~ int: entry.get_value().get_int }
        #~ key = entry.get_key().split("/")[-1]
        #~ if entry.get_key().split("/")[-2] == "dock":
            #~ key = "dock/" + key
        #~ elif entry.get_key().split("/")[-2] == "awn":
            #~ key = "awn/" + key
        #~ elif entry.get_key().split("/")[-2] == "applets":
            #~ key = "applets/" + key
        #~ elif len(entry.get_key().split("/"))>=3 and \
              #~ entry.get_key().split("/")[-3] == "applets":
                  #~ # Ignore applet settings
                  #~ return
        #~ if key in self.settings:
            #~ value = self.settings[key]
            #~ if entry_get[type(value)]() != value:
                #~ changed_settings.append(key)
                #~ self.settings[key] = entry_get[type(value)]()
                #~ pref_update = True

        #~ # Theme colors and popup style
        #~ if self.theme_name:
            #~ theme_name = self.theme_name.replace(" ", "_")
            #~ try:
                #~ theme_name = theme_name.translate(None, '!?*()/#"@')
            #~ except:
                #~ pass
            #~ psf = "%s/themes/%s/popup_style_file"%(GCONF_DIR, theme_name)
            #~ if entry.get_key() == psf:
                #~ value = entry.get_value().get_string()
                #~ if self.popup_style_file != value:
                    #~ self.popup_style_file = value
                    #~ pref_update == True
                    #~ self.emit("popup-style-changed")



        #~ # Dock theme colors
        #~ for key, value in self.dock_colors.items():
            #~ tf = self.settings["dock/theme_file"]
            #~ if entry.get_key() == "%s/dock/themes/%s/%s"%(GCONF_DIR, tf, key):
                #~ if entry_get[type(value)] != value:
                    #~ self.dock_colors[key] = entry_get[type(value)]()
                    #~ self.emit("dock-color-changed")
                    #~ pref_update = True

        #TODO: Add check for sane values for critical settings.
        #~ if "awn/behavior" == key:
            #~ self.emit("awn-behavior-changed")
        if "locked_list_no_overlap" == key:
            self.emit("locked-list-overlap-changed")
        elif "locked_list_in_menu" == key:
            self.emit("locked-list-in-menu-changed")
        elif "color2" == key:
            self.emit("color2-changed")
        elif "show_only_current_desktop" == key:
            self.emit("show-only-current-desktop-changed")
        elif "show_only_current_monitor" == key:
            self.emit("show-only-current-monitor-changed")
        elif "preview" == key:
            self.emit("show-previews-changed")
        elif "preview_size" == key:
            self.emit("preview-size-changed")
        elif "window_title_width" == key:
            self.emit("window-title-width-changed")
        elif "groupbutton_show_tooltip" == key:
            self.emit("show-tooltip-changed")
        elif "show_close_button" == key:
            self.emit("show-close-button-changed")
        elif "media_buttons" == key:
            self.emit("media-buttons-changed")
        elif "quicklist" == key:
            self.emit("quicklist-changed")
        elif "unity" == key:
            self.emit("unity-changed")
        elif "dockmanager" == key:
            self.emit("dockmanager-changed")
        elif "use_number_shortcuts" == key:
            self.emit("use-number-shortcuts-changed")
        elif key == "theme":
            self.emit("theme-changed")
        elif key.startswith("color"):
            self.emit("color-changed")
        elif "gkey" in key:
            self.emit("gkey-changed")
        elif key.startswith("badge"):
            self.emit("badge-look-changed")
        elif key.startswith("progress"):
            self.emit("progress-bar-look-changed")

        self.emit("preference-update")

    def __on_dock_gsettings_changed(self, settings, gkey, data=None):
        key = gkey.replace("-", "_")
        key = "dock/%s" % key
        if not key in self.settings:
            print("The changed setting is not in settings dictionary:", key)
            return
        self.settings[key] = self.dock_gsettings.get_value(gkey).unpack()

        if "size" == gkey:
            self.emit("dock-size-changed")
        elif "offset" == gkey:
            self.emit("dock-offset-changed")
        elif "position" == gkey:
            self.emit("dock-position-changed")
        elif "behavior" == gkey:
            self.emit("dock-behavior-changed")
        elif "mode" == gkey:
            self.emit("dock-mode-changed")
        elif "end-decorations" == gkey:
            self.emit("dock-end-decorations-changed")
        elif "theme-file" == gkey:
            self.emit("dock-theme-changed")
        self.emit("preference-update")

    def __on_theme_gsettings_changed(self, settings, gkey, data=None):
        value = self.theme_gsettings.get_value(gkey).unpack()
        key = gkey.replace("-", "_")
        if key in self.colors:
            if value == "default":
                value = self.default_theme_colors.get(key, "#000000")
            elif value == -1:
                value = self.default_theme_alphas.get(key[:6], 255)
            self.colors[key] = value
        elif gkey == "popup-style-file":
            if value.lower() == "theme default":
                value = self.default_popup_style
            self.popup_style_file = value
            self.emit("popup-style-changed")
        self.emit("preference-update")

    def __on_dock_theme_gsettings_changed(self, settings, gkey, data=None):
        colors = self.dock_theme_gsettings.get_value("colors").unpack()
        self.__update_dock_colors(colors)

    def __get_settings(self, default):
        settings = default.copy()
        #~ gconf_set = { str: GCONF_CLIENT.set_string,
                      #~ bool: GCONF_CLIENT.set_bool,
                      #~ int: GCONF_CLIENT.set_int }
        for name, value in list(settings.items()):
            gs_name = name.replace("_", "-")
            if name.startswith("awn/"):
                continue
            elif name.startswith("dock/"):
                gs_name = gs_name.split("/")[-1]
                gsettings = self.dock_gsettings
            else:
                gsettings = self.gsettings
            gs_value = gsettings.get_value(gs_name).unpack()
            if type(gs_value) != type(value):
                # Todo: Remove this if unneccessary.
                print("Gsettings import. Wrong types for", name, "- New type:", gs_value, "Old type:", value)
            settings[name] = gs_value
        return settings

    def set_theme_gsettings(self, theme_name):
        self.theme_name = theme_name
        if self.theme_gsettings is not None:
            self.theme_gsettings.disconnect(self.theme_gsettings_sid)
        theme_name = theme_name.lower().replace(" ", "_")
        for sign in ("'", '"', "!", "?", "*", "(", ")", "/", "#", "@"):
            theme_name = theme_name.replace(sign, "")
        path = "/org/dockbarx/dockbarx/themes/%s/" % theme_name
        self.theme_gsettings = Gio.Settings.new_with_path("org.dockbarx.dockbarx.theme", path)
        self.theme_gsettings_sid = self.theme_gsettings.connect("changed", self.__on_theme_gsettings_changed)

    def update_colors(self, theme_name, theme_colors={}, theme_alphas={}):
        # Updates the colors when the theme calls for an update.
        if theme_name is None:
            self.colors.clear()
            # If there are no theme name, preference window wants empty colors.
            for i in range(1, 9):
                self.colors["color%s"%i] = "#000000"
            return

        self.default_theme_colors = theme_colors
        self.default_theme_alphas = theme_alphas
        self.colors.clear()
        for i in range(1, 9):
            c = "color%s"%i
            a = "color%s-alpha"%i
            color = self.theme_gsettings.get_value(c).unpack()
            alpha = self.theme_gsettings.get_value(a).unpack()
            if color == "default":
                if c in theme_colors:
                    color = theme_colors[c]
                else:
                    color = self.DEFAULT_COLORS[c]
            self.colors[c] = color

            if alpha == -1:
                if c in theme_alphas:
                    if theme_alphas[c] == "no":
                        alpha = 255
                    else:
                        alpha = int(theme_alphas[c])
                        alpha = int(round(alpha * 2.55))
                else:
                    alpha = self.DEFAULT_COLORS.get("%s_alpha"%c, 255)
            self.colors["color%s_alpha" % i] = alpha
            
        for i in range(1, 9):
            # DConf-editor can't see relocatable schemas
            # so we will set the settings manually so that they will show up.
            c = "color%s"%i
            a = "color%s-alpha"%i

            color = self.theme_gsettings.get_value(c)
            alpha = self.theme_gsettings.get_value(a)
            if self.theme_gsettings.get_user_value(c) is None:
                self.theme_gsettings.set_value(c, color)
            if self.theme_gsettings.get_user_value(a) is None:
                self.theme_gsettings.set_value(a, alpha)

    def update_popup_style(self, default_style):
        # Runs when the theme has changed.
        self.default_popup_style = default_style
        style = self.theme_gsettings.get_string("popup-style-file")
        if self.theme_gsettings.get_user_value("popup-style-file") is None:
            # DConf-editor can't see relocatable schemas
            # so we will set the setting manually so that it will show up.
            self.theme_gsettings.set_string("popup-style-file", style)
        if style.lower() == "theme default":
            style = default_style
        if style != self.popup_style_file:
            self.popup_style_file = style
            self.emit("popup-style-changed")
            self.emit("preference-update")

    def set_popup_style(self, style):
        # Used when the popup style is reloaded.
        if self.popup_style_file == style:
            return
        self.theme_gsettings.set_string("popup-style-file", style)
        if style.lower() == "theme default":
            style = self.default_popup_style
        self.popup_style_file = style
        self.emit("preference-update")

    def set_dock_theme(self, theme, default_colors):
        if self.settings["dock/theme_file"] != theme:
            self.settings["dock/theme_file"] = theme
            self.dock_gsettings.set_string("theme-file", theme)
        if self.dock_theme_gsettings is not None:
            self.dock_theme_gsettings.disconnect(self.dock_theme_gsettings_sid)
        path = "/org/dockbarx/dockx/themes/%s/" % theme.lower()
        self.dock_theme_gsettings = Gio.Settings.new_with_path("org.dockbarx.dockx.theme", path)
        self.dock_theme_gsettings_sid = self.dock_theme_gsettings.connect("changed", self.__on_dock_theme_gsettings_changed)
        colors = self.dock_theme_gsettings.get_value("colors").unpack()
        self.default_dock_colors = default_colors
        self.__update_dock_colors(colors)

    def __update_dock_colors(self, colors):
        for key in self.default_dock_colors:
            if not key in colors:
                colors[key] = "default"
            if colors[key] == "default":
                self.dock_colors[key] = self.default_dock_colors[key]
            elif "alpha" in key:
                self.dock_colors[key] = int(colors[key])
            else:
                self.dock_colors[key] = colors[key]
        # Update the gsettings
        update_needed = False
        for key in colors.copy():
            colors[key] = str(colors[key])
            if not key in self.old_dock_gs_colors or self.old_dock_gs_colors[key] != colors[key]:
                update_needed = True
        if len(self.old_dock_gs_colors) != len(colors):
            update_needed = True
        if update_needed:
            self.old_dock_gs_colors = colors
            self.dock_theme_gsettings.set_value("colors", GLib.Variant("a{ss}", colors))
            self.emit("preference-update")


    def get_pinned_apps_from_gconf(self):
        # Get list of pinned_apps
        pinned_apps = self.gsettings.get_value("launchers").unpack()
        return pinned_apps

    def set_pinned_apps_list(self, pinned_apps):
        self.gsettings.set_value("launchers", GLib.Variant("as", pinned_apps))

    def set_shown_popup(self, popup):
        if popup is None:
            self.shown_popup = lambda: None
        else:
            self.shown_popup = weakref.ref(popup)

    def get_shown_popup(self):
        return self.shown_popup()

    def set_locked_popup(self, popup):
        if popup is None:
            self.locked_popup = lambda: None
        else:
            self.locked_popup = weakref.ref(popup)

    def get_locked_popup(self):
        return self.locked_popup()

    def get_compiz_version(self):
        if self.__compiz_version is None:
            try:
                import ccm
                self.__compiz_version = ccm.Version
            except:
                self.__compiz_version = "0.8"
        return self.__compiz_version



__connector = Connector()
connect = __connector.connect
connect_after = __connector.connect_after
disconnect = __connector.disconnect

__opacify_obj = Opacify()
opacify = __opacify_obj.opacify
deopacify = __opacify_obj.deopacify
set_opacifier = __opacify_obj.set_opacifier
get_opacifier = __opacify_obj.get_opacifier
