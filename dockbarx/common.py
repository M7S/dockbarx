#!/usr/bin/python

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
import gconf
import dbus
import gobject


GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = '/apps/dockbarx'

BUS = dbus.SessionBus()

def compiz_call(obj_path, func_name, *args):
    # Returns a compiz function call.
    # No errors are dealt with here,
    # error handling are left to the calling function.
    path = '/org/freedesktop/compiz'
    if obj_path:
        path += '/' + obj_path
    obj = BUS.get_object('org.freedesktop.compiz', path)
    iface = dbus.Interface(obj, 'org.freedesktop.compiz')
    func = getattr(iface, func_name)
    if func:
        return func(*args)
    return None

class ODict():
    """An ordered dictionary.

    Has only the most needed functions of a dict, not all."""
    def __init__(self, d=[]):
        if not type(d) in (list, tuple):
            raise TypeError('The argument has to be a list or a tuple or nothing.')
        self.list = []
        for t in d:
            if not type(d) in (list, tuple):
                raise ValueError('Every item of the list has to be a list or a tuple.')
            if not len(t) == 2:
                raise ValueError('Every tuple in the list needs to be two items long.')
            self.list.append(t)

    def __getitem__(self, key):
        for t in self.list:
            if t[0] == key:
                return t[1]

    def __setitem__(self, key, value):
        t = (key, value)
        self.list.append(t)

    def __contains__(self, key):
        for t in self.list:
            if t[0] == key:
                return True
        else:
            return False

    def __iter__(self):
        return self.keys().__iter__()

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


class Globals(gobject.GObject):
    """ Globals is a signletron containing all the "global" variables of dockbarx.

    It also keeps track of gconf settings and signals changes in gconf to other programs"""

    __gsignals__ = {
        'color2-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        'show-only-current-desktop-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        'theme-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        'color-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        'preference-update': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
    }

    DEFAULT_SETTINGS = {  "theme": "default",
                          "groupbutton_attention_notification_type": "red",
                          "workspace_behavior": "switch",
                          "popup_delay": 250,
                          "popup_align": "center",
                          "no_popup_for_one_window": False,
                          "show_only_current_desktop": False,
                          "preview": False,
                          "preview_size": 230,

                          "select_one_window": "select or minimize window",
                          "select_multiple_windows": "select all",

                          "opacify": False,
                          "opacify_group": False,
                          "opacify_alpha": 11,

                          "separate_wine_apps": True,
                          "separate_ooo_apps": True,

                          "groupbutton_left_click_action":"select or minimize group",
                          "groupbutton_shift_and_left_click_action":"launch application",
                          "groupbutton_middle_click_action":"close all windows",
                          "groupbutton_shift_and_middle_click_action": "no action",
                          "groupbutton_right_click_action": "show menu",
                          "groupbutton_shift_and_right_click_action": "no action",
                          "groupbutton_scroll_up": "select next window",
                          "groupbutton_scroll_down": "select previous window",
                          "groupbutton_left_click_double": False,
                          "groupbutton_shift_and_left_click_double": False,
                          "groupbutton_middle_click_double": True,
                          "groupbutton_shift_and_middle_click_double": False,
                          "groupbutton_right_click_double": False,
                          "groupbutton_shift_and_right_click_double": False,
                          "windowbutton_left_click_action":"select or minimize window",
                          "windowbutton_shift_and_left_click_action":"no action",
                          "windowbutton_middle_click_action":"close window",
                          "windowbutton_shift_and_middle_click_action": "no action",
                          "windowbutton_right_click_action": "show menu",
                          "windowbutton_shift_and_right_click_action": "no action",
                          "windowbutton_scroll_up": "shade window",
                          "windowbutton_scroll_down": "unshade window" }

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
                      "color8": "#000000",

               }

    def __new__(cls, *p, **k):
        if not '_the_instance' in cls.__dict__:
            cls._the_instance = gobject.GObject.__new__(cls)
        return cls._the_instance

    def __init__(self):
        if not 'settings' in self.__dict__:
            # First run.
            gobject.GObject.__init__(self)

            # "Global" variables
            self.right_menu_showing = False
            self.opacified = False
            self.opacity_values = None
            self.opacity_matches = None
            self.dragging = False
            self.orient = 'h'
            self.apps_by_id = {}
            self.theme_name = None

            # Get gconf settings
            self.settings = self.DEFAULT_SETTINGS.copy()
            gconf_set = { str: GCONF_CLIENT.set_string,
                          bool: GCONF_CLIENT.set_bool,
                          int: GCONF_CLIENT.set_int }
            for name, value in self.settings.items():
                gc_value = None
                try:
                    gc_value = GCONF_CLIENT.get_value(GCONF_DIR + '/' + name)
                except:
                    gconf_set[type(value)](GCONF_DIR + '/' + name , value)
                else:
                    if type(gc_value) != type(value):
                        gconf_set[type(value)](GCONF_DIR + '/' + name , value)
                    else:
                        self.settings[name] = gc_value

            # Set gconf notifiers
            GCONF_CLIENT.add_dir(GCONF_DIR, gconf.CLIENT_PRELOAD_NONE)
            GCONF_CLIENT.notify_add(GCONF_DIR, self.on_gconf_changed, None)

            # Change old gconf settings
            group_button_actions_d = {"select or minimize group": "select",
                                      "select group": "select",
                                      "select or compiz scale group": "select"}
            for name, value in self.settings.items():
                if ("groupbutton" in name) and ("click" in name or "scroll" in name) \
                and value in group_button_actions_d:
                    self.settings[name] = group_button_actions_d[value]
                    GCONF_CLIENT.set_string(GCONF_DIR + '/' + name , self.settings[name])

            self.colors = {}

    def on_gconf_changed(self, client, par2, entry, par4):
        if entry.get_value() == None:
            return
        pref_update = False
        changed_settings = []
        entry_get = { str: entry.get_value().get_string,
                      bool: entry.get_value().get_bool,
                      int: entry.get_value().get_int }
        key = entry.get_key().split('/')[-1]
        if key in self.settings:
            value = self.settings[key]
            if entry_get[type(value)]() != value:
                changed_settings.append(key)
                self.settings[key] = entry_get[type(value)]()
                pref_update = True

        if self.theme_name:
            theme_name = self.theme_name.replace(' ', '_').encode()
            try:
                theme_name = theme_name.translate(None, '!?*()/#"@')
            except:
                pass
            for i in range(1, 9):
                c = 'color%s'%i
                a = 'color%s_alpha'%i
                for k in (c, a):
                    if entry.get_key() == "%s/themes/%s/%s"%(GCONF_DIR, theme_name, k):
                        value = self.colors[k]
                        if entry_get[type(value)]() != value:
                            changed_settings.append(key)
                            self.colors[k] = entry_get[type(value)]()
                            pref_update = True

        #TODO: Add check for sane values for critical settings.

        if 'color2' in changed_settings:
            self.emit('color2-changed')

        if 'show_only_current_desktop' in changed_settings:
            self.emit('show-only-current-desktop-changed')
        for key in changed_settings:
            if key == 'theme':
                self.emit('theme-changed')
            if 'color' in key:
                self.emit('color-changed')

        if pref_update == True:
            self.emit('preference-update')

    def update_colors(self, theme_name, theme_colors=None, theme_alphas=None):
        # Updates the colors when the theme calls for an update.
        if theme_name == None:
            self.colors.clear()
            # If there are no theme name, preference window wants empty colors.
            for i in range(1, 9):
                self.colors['color%s'%i] = "#000000"
            return

        theme_name = theme_name.replace(' ', '_').encode()
        try:
            theme_name = theme_name.translate(None, '!?*()/#"@')
        except:
            # Todo: better error handling here.
            pass
        color_dir = GCONF_DIR + '/themes/' + theme_name
        self.colors.clear()
        for i in range(1, 9):
            c = 'color%s'%i
            a = 'color%s_alpha'%i
            try:
                self.colors[c] = GCONF_CLIENT.get_value(color_dir + '/' + c)
            except:
                if c in theme_colors:
                    self.colors[c] = theme_colors[c]
                else:
                    self.colors[c] = self.DEFAULT_COLORS[c]
                GCONF_CLIENT.set_string(color_dir + '/' + c , self.colors[c])
            try:
                self.colors[a] = GCONF_CLIENT.get_value(color_dir + '/' + a)
            except:
                if c in theme_alphas:
                    if'no' in theme_alphas[c]:
                        continue
                    else:
                        self.colors[a] = int(int(theme_alphas[c]) * 2.55 + 0.4)
                elif a in self.DEFAULT_COLORS:
                    self.colors[a] = self.DEFAULT_COLORS[a]
                else:
                    continue
                GCONF_CLIENT.set_int(color_dir + '/' + a , self.colors[a])

    def get_launchers_from_gconf(self):
        # Get list of launchers
        gconf_launchers = []
        try:
            gconf_launchers = GCONF_CLIENT.get_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING)
        except:
            GCONF_CLIENT.set_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING, gconf_launchers)
        return gconf_launchers

    def set_launchers_list(self, launchers):
        GCONF_CLIENT.set_list(GCONF_DIR + '/launchers', gconf.VALUE_STRING, launchers)
