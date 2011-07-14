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


import pygtk
pygtk.require("2.0")
import gtk
import gobject
import sys
import os
import dbus
import gc
from time import time
gc.enable()


from common import *
from log import logger

import i18n
_ = i18n.language.gettext

VERSION = "0.45"


ATOM_WM_CLASS = gtk.gdk.atom_intern("WM_CLASS")

SPECIAL_RES_CLASSES = {
                        "thunderbird-bin": "thunderbird",
                        "amarokapp": "amarok",
                        "lives-exe": "lives",
                        "exaile.py": "exaile",
                        "eric4.py": "eric",
                        "geogebra-geogebra": "geogebra",
                        "tuxpaint.tuxpaint": "tuxpaint",
                        "quodlibet":"quod libet"
                      }

# Media player name substitutes (for non-identical resclass/dbus-address pairs)
MPS = {"banshee-1": "banshee"}

class AboutDialog():
    __instance = None

    def __init__ (self):
        if AboutDialog.__instance is None:
            AboutDialog.__instance = self
        else:
            AboutDialog.__instance.about.present()
            return
        self.about = gtk.AboutDialog()
        self.about.set_name("DockbarX Applet")
        self.about.set_logo_icon_name("dockbarx")
        self.about.set_version(VERSION)
        self.about.set_copyright(
            "Copyright (c) 2008-2009 Aleksey Shaferov and Matias S\xc3\xa4rs")
        self.about.connect("response",self.__about_close)
        self.about.show()

    def __about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None


class GroupList(list):
    def __init__(self):
        list.__init__(self)

    def __getitem__(self, item):
        # Item can be a identifier, path or index
        if item is None:
            raise KeyError, item
        if isinstance(item, (str, unicode)):
            for group in self:
                if group.identifier == item or \
                   (group.desktop_entry is not None and
                    group.desktop_entry.getFileName() == item):
                    return group
            raise KeyError, item
        return list.__getitem__(self, item)

    def get(self, item, default=None):
        try:
            return self.__getitem__(item)
        except KeyError:
            return default

    def get_identifiers(self):
        identifiers = []
        for group in self:
            if group.identifier:
                identifiers.append(group.identifier)
            else:
                identifiers.append(group.desktop_entry.getFileName())
        return identifiers

    def move(self, group, index):
        self.remove(group)
        self.insert(index, group)


class DockBar():
    def __init__(self, applet=None, awn_applet=None,
                 parent_window=None, run_as_dock=False):
        logger.info("DockbarX %s"%VERSION)
        logger.info("DockbarX init")
        self.applet = applet
        self.awn_applet = awn_applet
        self.parent_window = parent_window
        self.is_dock = run_as_dock
        self.groups = None
        self.windows = None
        self.container = None
        self.theme = None
        self.skip_tasklist_windows = None
        self.next_group = None
        self.dockmanager = None

        self.globals = Globals()
        self.globals.connect("theme-changed", self.reload)
        self.globals.connect("media-buttons-changed",
                             self.__on_media_controls_changed)
        self.globals.connect("dockmanager-changed",
                             self.__on_dockmanager_changed)

        #--- Applet / Window container
        if self.applet is not None:
            global gnomeapplet
            import gnomeapplet
            self.applet.set_applet_flags(
                            gnomeapplet.HAS_HANDLE|gnomeapplet.EXPAND_MINOR)
            if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN \
            or applet.get_orient() == gnomeapplet.ORIENT_UP:
                self.orient = "h"
                self.container = gtk.HBox()
            else:
                self.orient = "v"
                self.container = gtk.VBox()
            self.applet.add(self.container)
            self.pp_menu_xml = """
           <popup name="button3">
           <menuitem name="About Item" verb="About" stockid="gtk-about" />
           <menuitem name="Preferences" verb="Pref" stockid="gtk-properties" />
           <menuitem name="Reload" verb="Reload" stockid="gtk-refresh" />
           </popup>
            """

            self.pp_menu_verbs = [("About", self.__on_ppm_about),
                                  ("Pref", self.__on_ppm_pref),
                                  ("Reload", self.reload)]
            self.applet.setup_menu(self.pp_menu_xml, self.pp_menu_verbs,None)
            self.applet_origin_x = -1000
            self.applet_origin_y = -1000
            # background bug workaround
            self.applet.set_background_widget(applet)
            self.applet.show_all()
            self.applet.connect("delete-event", self.__cleanup)
        else:
            self.container = gtk.HBox()
            self.orient = "h"

                        
        # Most of initializion must happen after dockbarx is
        # realized since python gnomeapplets crash if they
        # take too much time to realize.
        if not awn_applet and not run_as_dock:
            gobject.idle_add(self.__load_on_realized)

    def __load_on_realized(self):
        while gtk.events_pending():
                    gtk.main_iteration(False)
        self.load()

    def load(self):
        global subprocess
        import subprocess
        global gio
        import gio
        global keybinder
        import keybinder
        global wnck
        import wnck
        global Group
        global GroupIdentifierError
        from groupbutton import Group, GroupIdentifierError
        global Theme
        global NoThemesError
        from theme import Theme, NoThemesError
        global Mpris2Watch
        global MediaButtons
        from mediabuttons import Mpris2Watch, MediaButtons
        global DockManager
        from dockmanager import DockManager
        global DockbarDBus
        from dbx_dbus import DockbarDBus
        global UnityWatcher
        from unity import UnityWatcher
        
        self.media_controls = {}
        self.mpris = Mpris2Watch(self)
        self.dbus = DockbarDBus(self)

        self.gkeys = {
                        "gkeys_select_next_group": None,
                        "gkeys_select_previous_group": None,
                        "gkeys_select_next_window": None,
                        "gkeys_select_previous_window": None
                     }

        wnck.set_client_type(wnck.CLIENT_TYPE_PAGER)
        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.screen.force_update()
        if self.applet is not None:
            self.applet.connect("size-allocate", self.__on_applet_size_alloc)
            self.applet.connect("change_background",
                                self.__on_change_background)
            self.applet.connect("change-orient", self.__on_change_orient)
        self.__gkeys_changed(dialog=False)
        self.__init_number_shortcuts()
        self.globals.connect("gkey-changed", self.__gkeys_changed)
        self.globals.connect("use-number-shortcuts-changed",
                             self.__init_number_shortcuts)
        self.unity_watcher = UnityWatcher(self)
        self.unity_watcher.start()
        
        #--- Generate Gio apps
        self.apps_by_id = {}
        self.app_ids_by_exec = {}
        self.app_ids_by_name = {}
        self.app_ids_by_longname = {}
        self.app_ids_by_cmd = {}
        self.wine_app_ids_by_program = {}
        for app in gio.app_info_get_all():
            id = app.get_id()
            id = id[:id.rfind(".")].lower()
            name = u""+app.get_name().lower()
            exe = app.get_executable()
            if exe:
                self.apps_by_id[id] = app
                try:
                    cmd = u""+app.get_commandline().lower()
                except AttributeError:
                    # Older versions of gio doesn't have get_comandline.
                    cmd = u""
                if id[:5] == "wine-":
                    if cmd.find(".exe") > 0:
                        program = cmd[:cmd.rfind(".exe")+4]
                        program = program[program.rfind("\\")+1:]
                        self.wine_app_ids_by_program[program] = id
                if cmd:
                    self.app_ids_by_cmd[cmd] = id
                if name.find(" ")>-1:
                    self.app_ids_by_longname[name] = id
                else:
                    self.app_ids_by_name[name] = id
                if exe not in ("sudo","gksudo",
                                "java","mono",
                                "ruby","python"):
                    if exe[0] == "/":
                        exe = exe[exe.rfind("/")+1:]
                        self.app_ids_by_exec[exe] = id
                    else:
                        self.app_ids_by_exec[exe] = id
        self.reload()
        return False


    def reload(self, event=None, data=None):
        if self.windows:
            # Removes windows and unpinned group buttons
            for win in self.screen.get_windows():
                self.__on_window_closed(None, win)
        if self.groups is not None:
            # Removes pinned group buttons
            for group in self.groups:
                group.destroy()
        disconnect(self.globals)
        del self.skip_tasklist_windows
        del self.groups
        del self.windows
        if self.theme:
            self.theme.remove()
        gc.collect()

        self.skip_tasklist_windows = []

        logger.info("DockbarX reload")
        self.groups = GroupList()
        self.windows = {}
        self.globals.set_shown_popup(None)
        self.next_group = None
        try:
            if self.theme is None:
                self.theme = Theme()
            else:
                self.theme.on_theme_changed()
        except NoThemesError, details:
            logger.exception("Error: Couldn't find any themes")
            sys.exit(1)

        self.container.set_spacing(self.theme.get_gap())
        self.container.show()
        self.__start_dockmanager()

        #--- Initiate launchers
        self.desktop_entry_by_id = {}
        self.d_e_ids_by_exec = {}
        self.d_e_ids_by_name = {}
        self.d_e_ids_by_longname = {}
        self.d_e_ids_by_wine_program = {}
        self.d_e_ids_by_chromium_cmd = {}

        gconf_pinned_apps = self.globals.get_pinned_apps_from_gconf()


        # Initiate launcher group buttons
        for launcher in gconf_pinned_apps:
            identifier, path = launcher.split(";")
            # Fix for launchers made in previous version of dockbarx
            identifier = identifier.lower()
            if identifier == "":
                identifier = None
            self.__add_launcher(identifier, path)
        # Update pinned_apps list to remove any pinned_app that are faulty.
        self.update_pinned_apps_list()

        #--- Initiate windows
        # Initiate group buttons with windows
        for window in self.screen.get_windows():
            self.__on_window_opened(self.screen, window)

        self.screen.connect("window-opened", self.__on_window_opened)
        self.screen.connect("window-closed", self.__on_window_closed)
        self.screen.connect("active-window-changed",
                            self.__on_active_window_changed)
        self.screen.connect("viewports-changed",
                            self.__on_desktop_changed)
        self.screen.connect("active-workspace-changed",
                            self.__on_desktop_changed)

        self.__on_active_window_changed(self.screen, None)

    def set_orient(self, orient):
        if orient == self.orient:
            return
        for group in self.groups:
            self.container.remove(group.button)
        if self.applet:
            self.applet.remove(self.container)
        self.container.destroy()
        self.orient = orient
        if orient == "h":
            self.container = gtk.HBox()
        else:
            self.container = gtk.VBox()
        if self.applet:
            self.applet.add(self.container)
        for group in self.groups:
            self.container.pack_start(group.button, False)
            group.window_list.set_show_previews(
                                              self.globals.settings["preview"])
            if orient == "h":
                # The direction of the pointer isn't important here, we only
                # need the right amount of padding so that the popup has right
                # width and height for placement calculations.
                group.popup.point("down")
            if orient == "v":
                group.popup.point("left")
        self.container.set_spacing(self.theme.get_gap())
        if self.globals.settings["show_only_current_desktop"]:
            self.container.show()
            self.__on_desktop_changed()
        else:
            self.container.show_all()
        if self.globals.get_locked_popup():
            group = self.globals.get_locked_popup().group_r()
            group.remove_locked_popup()
            group.add_locked_popup()

    def open_preference(self):
        # Starts the preference dialog
        os.spawnlp(os.P_NOWAIT,"/usr/bin/dbx_preference",
                   "/usr/bin/dbx_preference")

    #### Applet events
    def __on_ppm_pref(self,event=None,data=None):
        self.open_preference()

    def __on_ppm_about(self,event,data=None):
        AboutDialog()

    def __on_applet_size_alloc(self, widget, allocation):
        if widget.window:
            x,y = widget.window.get_origin()
            if x!=self.applet_origin_x or y!=self.applet_origin_y:
                # Applet and/or panel moved
                self.applet_origin_x = x
                self.applet_origin_y = y
                if self.groups:
                    for group in self.groups:
                        group.button.dockbar_moved()

    def __on_change_orient(self, arg1, data):
        if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN \
        or self.applet.get_orient() == gnomeapplet.ORIENT_UP:
            self.set_orient("h")
        else:
            self.set_orient("v")

    def __on_change_background(self, applet, type, color, pixmap):
        applet.set_style(None)
        rc_style = gtk.RcStyle()
        applet.modify_style(rc_style)
        if type == gnomeapplet.COLOR_BACKGROUND:
            applet.modify_bg(gtk.STATE_NORMAL, color)
        elif type == gnomeapplet.PIXMAP_BACKGROUND:
            style = applet.style
            style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
            applet.set_style(style)
        return

    def __cleanup(self,event):
        del self.applet


    #### Wnck events
    def __on_active_window_changed(self, screen, previous_active_window):
        # Sets the right window button and group button active.
        for group in self.groups:
            group.set_active_window(None)
        # Activate new windowbutton
        active_window = screen.get_active_window()
        if active_window in self.windows:
            active_group_name = self.windows[active_window]
            active_group = self.groups[active_group_name]
            active_group.set_active_window(active_window)

    def __on_window_closed(self, screen, window):
        if window in self.windows:
            if self.is_dock:
                self.parent_window.remove_window(window)
            disconnect(window)
            self.__remove_window(window)
        if window in self.skip_tasklist_windows:
            self.skip_tasklist_windows.remove(window)

    def __on_window_opened(self, screen, window):
        if not (window.get_window_type() in [wnck.WINDOW_NORMAL,
                                             wnck.WINDOW_DIALOG]):
            return
        connect(window, "state-changed", self.__on_window_state_changed)
        if window.is_skip_tasklist():
            self.skip_tasklist_windows.append(window)
            return
        self.__add_window(window)
        if self.is_dock:
            self.parent_window.add_window(window)

    def __on_window_state_changed(self, window, changed_mask, new_state):
        if window in self.skip_tasklist_windows and \
           not window.is_skip_tasklist():
            self.__add_window(window)
            self.skip_tasklist_windows.remove(window)
            if self.is_dock:
                self.parent_window.add_window(window)
        if window.is_skip_tasklist() and \
           not window in self.skip_tasklist_windows:
            if self.is_dock:
                self.parent_window.remove_window(window)
            self.__remove_window(window)
            self.skip_tasklist_windows.append(window)

    def __on_desktop_changed(self, screen=None, workspace=None):
        if not self.globals.settings["show_only_current_desktop"]:
            return
        for group in self.groups:
            group.desktop_changed()


    #### Groupbuttons
    def remove_groupbutton(self, group):
        self.groups.remove(group)
        group.destroy()
        self.update_pinned_apps_list()
        if self.next_group and \
           self.next_group in self.groups:
            self.next_group.scrollpeak_abort()
            self.next_group = None

    def groupbutton_moved(self, name, drop_point):
        # Moves the button to the right of the drop point.
        group = self.groups[name]

        if drop_point == "after":
            index = len(self.groups) - 1
        elif drop_point == "before":
            index = 0
        else:
            # Dropped on a group button
            index = self.groups.index(drop_point)
            index += (index < self.groups.index(group))
        self.container.reorder_child(group.button, index)
        self.groups.move(group, index)
        self.update_pinned_apps_list()

    def group_unpinned(self, identifier):
        group = self.groups[identifier]
        # Reset the desktop_entry in case this was
        # an custom launcher.
        if identifier in self.wine_app_ids_by_program:
            app_id = self.wine_app_ids_by_program[identifier]
            app = self.apps_by_id[app_id]
        else:
            app = self.__find_gio_app(identifier)
        if app:
            desktop_entry = self.__get_desktop_entry_for_id(app.get_id())
            group.set_desktop_entry(desktop_entry)
        group.update_name()

    def __make_groupbutton(self, identifier=None, desktop_entry=None,
                         pinned=False, index=None):
        group = Group(self, identifier, desktop_entry, pinned)
        self.container.pack_start(group.button, False)
        if index is not None and index != -1:
            self.container.reorder_child(group.button, index)
            self.groups.insert(index, group)
        else:
            self.groups.append(group)
        self.__media_player_check(identifier, group)
        self.update_pinned_apps_list()
        return group

    def __add_window(self, window):
        res_class = window.get_class_group().get_res_class().lower()
        res_name = window.get_class_group().get_name().lower()
        identifier = res_class or res_name or window.get_name().lower()
        # Special cases
        if identifier in SPECIAL_RES_CLASSES:
            identifier = SPECIAL_RES_CLASSES[identifier]
        wine = False
        chromium = False
        if identifier == "wine" and \
           self.globals.settings["separate_wine_apps"]:
            identifier = res_name
            wine = True
        if identifier in ("chromium-browser", "chrome-browser"):
            identifier = self.__get_chromium_id(window)
            if not identifier in ("chromium-browser", "chrome-browser"):
                chromium = True
        if identifier == "prism" and \
           self.globals.settings["separate_prism_apps"]:
            identifier = self.__get_prism_app_name(window)
        elif identifier.startswith("openoffice.org") or \
           identifier.startswith("libreoffice"):
            identifier = self.__get_ooo_app_name(window)
            if self.globals.settings["separate_ooo_apps"]:
                connect(window, "name-changed",
                        self.__on_ooo_window_name_changed)
        self.windows[window] = identifier
        if identifier in self.groups.get_identifiers():
            self.groups[identifier].add_window(window)
            return

        if wine:
            if identifier in self.d_e_ids_by_wine_program:
                desktop_entry_id = self.d_e_ids_by_wine_program[identifier]
            else:
                desktop_entry_id = None
        elif chromium:
            desktop_entry_id = self.__find_chromium_d_e_id(identifier)
        else:
            desktop_entry_id = self.__find_desktop_entry_id(identifier)
        if desktop_entry_id:
            desktop_entry = self.desktop_entry_by_id[desktop_entry_id]
            path = desktop_entry.getFileName()
            group = self.groups[path]
            self.__set_group_identifier(group, identifier)
            group.add_window(window)
            self.__remove_desktop_entry_id_from_list(desktop_entry_id)
        else:
            # First window of a new group.
            app = None
            if wine:
                if res_name in self.wine_app_ids_by_program:
                    app_id = self.wine_app_ids_by_program[res_name]
                    app = self.apps_by_id[app_id]
            elif chromium:
                app = self.__find_chromium_gio_app(identifier)
            else:
                app = self.__find_gio_app(identifier)
            if app:
                desktop_entry = self.__get_desktop_entry_for_id(app.get_id())
            else:
                desktop_entry = None
            try:
                group = self.__make_groupbutton(identifier=identifier,
                                                desktop_entry=desktop_entry)
            except GroupIdentifierError:
                logger.exception("Couldn't make a new groupbutton.")
                del self.windows[window]
                return
            group.add_window(window)

    def __remove_window(self, window):
        identifier = self.windows[window]
        group = self.groups[identifier]
        group.del_window(window)
        if not len(group) and not group.pinned:
            self.remove_groupbutton(group)
        del self.windows[window]

    def __find_desktop_entry_id(self, identifier):
        id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.desktop_entry_by_id:
                id = rc
            elif rc in self.d_e_ids_by_name:
                id = self.d_e_ids_by_name[rc]
            elif rc in self.d_e_ids_by_exec:
                id = self.d_e_ids_by_exec[rc]
            else:
                for lname in self.d_e_ids_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == " ") \
                        or (pos+len(rc) == len(lname) \
                        and lname[pos-1] == " ") \
                        or (lname[pos-1] == " " and lname[pos+len(rc)] == " "):
                            id = self.d_e_ids_by_longname[lname]
                            break

            if id is None and rc.find(" ")>-1:
                    rc = rc.partition(" ")[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this "App 1.2.3" (name with ver)
                    if rc in self.desktop_entry_by_id:
                        id = rc
                    elif rc in self.d_e_ids_by_name:
                        id = self.d_e_ids_by_name[rc]
                    elif rc in self.d_e_ids_by_exec:
                        id = self.d_e_ids_by_exec[rc]
        return id

    def __find_gio_app(self, identifier):
        app = None
        app_id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.apps_by_id:
                app_id = rc
            elif rc in self.app_ids_by_name:
                app_id = self.app_ids_by_name[rc]
            elif rc in self.app_ids_by_exec:
                app_id = self.app_ids_by_exec[rc]
            else:
                for lname in self.app_ids_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == " ") \
                        or (pos+len(rc) == len(lname) \
                        and lname[pos-1] == " ") \
                        or (lname[pos-1] == " " and lname[pos+len(rc)] == " "):
                            app_id = self.app_ids_by_longname[lname]
                            break
            if not app_id:
                if rc.find(" ")>-1:
                    rc = rc.partition(" ")[0] 
                    # Workaround for apps
                    # with identifier like this "App 1.2.3" (name with ver)
                    if rc in self.apps_by_id.keys():
                        app_id = rc
                    elif rc in self.app_ids_by_name.keys():
                        app_id = self.app_ids_by_name[rc]
                    elif rc in self.app_ids_by_exec.keys():
                        app_id = self.app_ids_by_exec[rc]
            if app_id:
                app = self.apps_by_id[app_id]
        return app

    def __get_ooo_app_name(self, window):
        # Separates the differnt openoffice applications from each other
        # The names are chosen to match the gio app ids.
        name = window.get_name().lower()
        resclass = window.get_class_group().get_res_class().lower()
        if "libreoffice" in resclass:
            office = "libreoffice"
        elif "openoffice.org" in resclass:
            office = "openoffice.org"
        if not self.globals.settings["separate_ooo_apps"]:
            return "%s-writer" % office
        for app in ["calc", "impress", "draw", "math"]:
            if name.endswith(app):
                return "%s-%s" % (office, app)
        else:
            return "%s-writer" % office

    def __get_prism_app_name(self, window):
        return window.get_name()

    def __get_chromium_id(self, window):
        resclass = window.get_class_group().get_res_class().lower()
        pid = window.get_pid()
        try:
            f = open("/proc/"+str(pid)+"/cmdline", "r")
        except:
            raise
        cmd = f.readline()
        if "--app=" in cmd:
            # Get the app address, remove trailing null char and remove '"'
            app = cmd.split("--app=")[-1][:-1].translate(None, "\"")
            return "%s-%s" % (resclass, app)
        else:
            return resclass

    def __find_chromium_gio_app(self, identifier):
        app = identifier.split("-browser-", 1)[-1]
        name = identifier.split("-browser-", 1)[0] + "-browser"
        for cmd in self.app_ids_by_cmd:
            if name in cmd and "--app=" in cmd:
                a = str(cmd.split("--app=")[-1][:-1]).translate(None, "\"")
                if app == a:
                    id = self.app_ids_by_cmd[cmd]
                    return self.apps_by_id[id]

    def __find_chromium_d_e_id(self, identifier):
        app = identifier.split("-browser-", 1)[-1]
        for cmd in self.d_e_ids_by_chromium_cmd:
            if "--app=" in cmd:
                a = str(cmd.split("--app=")[-1][:-1]).translate(None, "\"")
                if app == a:
                    return self.d_e_ids_by_chromium_cmd[cmd]
        return None
        
    def __on_ooo_window_name_changed(self, window):
        identifier = None
        for group in self.groups:
            if window in group:
                identifier = group.identifier
                break
        else:
            logger.warning("OOo app error: Name changed but no group found.")
        if identifier != self.__get_ooo_app_name(window):
            self.__remove_window(window)
            self.__add_window(window)
            if window == self.screen.get_active_window():
                self.__on_active_window_changed(self.screen, None)

    def __set_group_identifier(self, group, identifier):
        group.set_identifier(identifier)
        for window in group:
            self.windows[window.wnck] = indentifier
        self.update_pinned_apps_list()
        self.__media_player_check(identifier, group)

    def minimize_other_groups(self, group):
        for g in self.groups:
            if group != g:
                for window in g.get_list():
                    window.wnck.minimize()


    #### Launchers
    def launcher_dropped(self, path, drop_point):
        # Creates a new launcher with a desktop file located at path.
        # The new launcher is inserted at the right (or under)
        # the group button that the launcher was dropped on.
        try:
            desktop_entry = DesktopEntry(path)
        except Exception, detail:
            logger.exception("ERROR: Couldn't read dropped file. " + \
                             "Was it a desktop entry?")
            return False

        # Try to match the launcher against the groups that aren't pinned.
        id = path[path.rfind("/")+1:path.rfind(".")].lower()
        name = u"" + desktop_entry.getName()
        exe = desktop_entry.getExec()
        wine = False
        chromium = False
        if ("chromium-browser" in exe or "chrome-browser" in exe) and \
           "--app=" in exe:
            cmd = exe
            app = cmd.split("--app=")[-1][:-1].translate(None, "\"")
            chromium = True
        elif self.globals.settings["separate_wine_apps"] \
        and "wine" in exe and ".exe" in exe.lower():
                exe = exe.lower()
                exe = exe[:exe.rfind(".exe")+4]
                exe = exe[exe.rfind("\\")+1:]
                wine = True
        else:
            l= exe.split()
            if l and l[0] in ("sudo","gksudo", "gksu",
                              "java","mono",
                              "ruby","python"):
                exe = l[1]
            else:
                exe = l[0]
            exe = exe[exe.rfind("/")+1:]
            if exe.find(".")>-1:
                exe = exe[:exe.rfind(".")]

        if name.find(" ")>-1:
            lname = name
        else:
            lname = None

        if exe and exe[0] == "/":
            exe = exe[exe.rfind("/")+1:]

        for group in self.groups:
            if group.pinned:
                continue
            identifier = group.identifier
            rc = u"" + identifier.lower()
            if not rc:
                continue
            if wine:
                if rc == exe:
                    break
                else:
                    continue
            if chromium and ("chromium-browser" in identifier or \
               "chrome-browser" in identifier):
                a = identifier.split("-browser-", 1)[-1]
                if a == app:
                    break
                else:
                    continue
            if rc == id:
                break
            if rc == name:
                break
            if rc == exe:
                break
            if lname:
                pos = lname.find(rc)
                if pos>-1: # Check that it is not part of word
                    if (pos==0) and (lname[len(rc)] == " "):
                        break
                    elif (pos+len(rc) == len(lname)) and (lname[pos-1] == " "):
                        break
                    elif (lname[pos-1] == " ") and (lname[pos+len(rc)] == " "):
                        break
            if rc.find(" ")>-1:
                    rc = rc.partition(" ")[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this "App 1.2.3" (name with ver)
                    if rc == id:
                        break
                    elif rc == name:
                        break
                    elif rc == exe:
                        break
        else:
            # No unpinned group could be connected
            # with the new launcher. Id, name and exe will be stored
            # so that it can be checked against new windows later.
            identifier = None

            self.desktop_entry_by_id[id] = desktop_entry
            if wine:
                self.d_e_ids_by_wine_program[exe] = id
            elif chromium:
                self.d_e_ids_by_chromium_cmd[cmd] = id
            else:
                if lname:
                    self.d_e_ids_by_longname[name] = id
                else:
                    self.d_e_ids_by_name[name] = id
                if exe:
                    self.d_e_ids_by_exec[exe] = id

        # Remove existing groupbutton for the same program
        window_list = []
        index = None
            
        if drop_point == "after":
            index = -1
        elif drop_point == "before":
            index = 0
        else:
            drop_identifier = drop_point.identifier or \
                              drop_point.desktop_entry.getFileName()
            if drop_identifier in (identifier, path):
                index = self.groups.index(drop_point)
        group = self.groups.get(identifier) or self.groups.get(path)
        if group is not None:
            # Get the windows for repopulation of the new button
            window_list = [window.wnck for window in group]
            self.groups.remove(group)
            group.destroy()
        if index is None:
            index = self.groups.index(drop_point) + 1
        try:
            self.__make_groupbutton(identifier=identifier,
                                  desktop_entry=desktop_entry,
                                  pinned=True,
                                  index=index)
        except GroupIdentifierError:
            logger.exception("Couldn't add the dropped launcher.")
        for window in window_list:
            self.__on_window_opened(self.screen, window)
        return True


    def change_identifier(self, path=None, old_identifier=None):
        identifier = self.__identifier_dialog(old_identifier)
        if not identifier:
            return False
        window_list = []
        if identifier in self.groups.get_identifiers():
                group = self.groups[identifier]
                # Get the windows for repopulation of the new button
                window_list = [window.wnck for window in group]
                self.groups.remove(group)
                group.destroy()
        group = self.groups.get(old_identifier) or self.groups[path]
        self.__set_group_identifier(group, identifier)
        for window in window_list:
            self.__add_window(window)

    def edit_launcher(self, path, identifier):
        launcher_dir = os.path.join(os.path.expanduser("~"),
                                    ".dockbarx", "launchers")
        if not os.path.exists(launcher_dir):
            os.makedirs(launcher_dir)
        if path:
            if not os.path.exists(path):
                logger.warning("Error: file %s doesn't exist."%path)
            new_path = os.path.join(launcher_dir, os.path.basename(path))
            if new_path != path:
                os.system("cp %s %s"%(path, new_path))
        else:
            new_path = os.path.join(launcher_dir, "%s.desktop"%identifier)
        process = subprocess.Popen(["gnome-desktop-item-edit", new_path],
                                   env=os.environ)
        gobject.timeout_add(100, self.__wait_for_launcher_editor,
                            process, path, new_path, identifier)

    def update_pinned_apps_list(self, arg=None):
        # Saves pinned_apps_list to gconf.
        gconf_pinned_apps = []
        for group in self.groups:
            if not group.pinned:
                continue
            identifier = group.identifier
            if identifier is None:
                identifier = ""
            path = group.desktop_entry.getFileName()
            # Todo: Is there any drawbacks from using encode("utf-8") here?
            gconf_pinned_apps.append(identifier.encode("utf-8") + ";" +
                                     path.encode("utf-8"))
        self.globals.set_pinned_apps_list(gconf_pinned_apps)

    def __add_launcher(self, identifier, path):
        if path[:4] == "gio:":
            # This launcher is from an older version of dockbarx.
            # It will be updated to new form automatically.
            if path[4:] in self.apps_by_id:
                app = self.apps_by_id[path[4:]]
                desktop_entry = self.__get_desktop_entry_for_id(app.get_id())
                if desktop_entry is None:
                    return
            else:
                logger.debug("Couldn't find gio app for launcher %s" % path)
                return
        else:
            try:
                desktop_entry = DesktopEntry(path)
            except ParsingError:
                logger.debug("Couldn't add launcher: " + \
                             "%s is not an desktop file!" % path)
                return
            except UnboundLocalError:
                logger.debug("Couldn't add launcher: " + \
                             "path %s doesn't exist" % path)
                return
                
        # Safety in case something has gone wrong and there's duplicates
        # in the list.
        if (identifier or path) in self.groups.get_identifiers():
            return
        try:
            self.__make_groupbutton(identifier=identifier, \
                                  desktop_entry=desktop_entry, \
                                  pinned=True)
        except GroupIdentifierError:
            logger.exception("Couldn't add a pinned application.")
            return
        if identifier is None:
            id = path[path.rfind("/")+1:path.rfind(".")].lower()
            self.desktop_entry_by_id[id] = desktop_entry
            exe = desktop_entry.getExec()
            if self.globals.settings["separate_wine_apps"] \
            and "wine" in exe and ".exe" in exe:
                # We are interested in the nameoftheprogram.exe part of the
                # executable.
                exe = exe[:exe.rfind(".exe")+4][exe.rfind("\\")+1:].lower()
                self.d_e_ids_by_wine_program[exe] = id
                return
            elif ("chromium-browser" in exe or "chrome-browser" in exe) and \
                 "--app=" in exe:
                self.d_e_ids_by_chromium_cmd[exe] = id
                return
            l = exe.split()
            if l and l[0] in ("sudo","gksudo", "gksu",
                              "java","mono",
                              "ruby","python"):
                exe = l[1]
            elif l:
                exe = l[0]
            else:
                exe = ""
            exe = exe.rpartition("/")[-1]
            exe = exe.partition(".")[0]
            if exe != "":
                self.d_e_ids_by_exec[exe] = id

            name = u"" + desktop_entry.getName().lower()
            if name.find(" ")>-1:
                self.d_e_ids_by_longname[name] = id
            else:
                self.d_e_ids_by_name[name] = id

    def __remove_desktop_entry_id_from_list(self, id):
        self.desktop_entry_by_id.pop(id)
        for l in (self.d_e_ids_by_name,
                  self.d_e_ids_by_exec,
                  self.d_e_ids_by_longname,
                  self.d_e_ids_by_wine_program):
            for key, value in l.items():
                if value == id:
                    l.pop(key)
                    break

    def __get_desktop_entry_for_id(self, id):
        # Search for the desktop id first in ~/.local/share/applications
        # and then in XDG_DATA_DIRS/applications
        user_folder = os.environ.get("XDG_DATA_HOME",
                                     os.path.join(os.path.expanduser("~"),
                                                  ".local", "share"))
        data_folders = os.environ.get("XDG_DATA_DIRS",
                                      "/usr/local/share/:/usr/share/")
        folders = "%s:%s"%(user_folder, data_folders)
        for folder in folders.split(":"):
            dirname = os.path.join(folder, "applications")
            basename = id
            run = True
            while run:
                run = False
                path = os.path.join(dirname, basename)
                if os.path.isfile(path):
                    try:
                        return DesktopEntry(path)
                    except:
                        pass
                # If the desktop file is in a subfolders, the id is formated
                # "[subfoldername]-[basename]", but there can of cource be
                # "-" in basenames or subfoldernames as well.
                if "-" in basename:
                    parts = basename.split("-")
                    for n in range(1, len(parts)):
                        subfolder = "-".join(parts[:n])
                        if os.path.isdir(os.path.join(dirname, subfolder)):
                            dirname = os.path.join(dirname, subfolder)
                            basename = "-".join(parts[n:])
                            run = True
                            break
        return None

    def __identifier_dialog(self, identifier=None):
        # Input dialog for inputting the identifier.
        flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
        dialog = gtk.MessageDialog(None,
                                   flags,
                                   gtk.MESSAGE_QUESTION,
                                   gtk.BUTTONS_OK_CANCEL,
                                   None)
        dialog.set_title(_("Identifier"))
        dialog.set_markup("<b>%s</b>"%_("Enter the identifier here"))
        dialog.format_secondary_markup(
            _("You should have to do this only if the program fails to recognice its windows. ")+ \
            _("If the program is already running you should be able to find the identifier of the program from the dropdown list."))
        #create the text input field
        #entry = gtk.Entry()
        combobox = gtk.combo_box_entry_new_text()
        entry = combobox.get_child()
        if identifier:
            entry.set_text(identifier)
        # Fill the popdown list with the names of all class
        # names of buttons that hasn't got a launcher already
        for group in self.groups:
            if not group.pinned:
                combobox.append_text(group.identifier)
        entry = combobox.get_child()
        #allow the user to press enter to do ok
        entry.connect("activate",
                      lambda widget: dialog.response(gtk.RESPONSE_OK))
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_("Identifier:")), False, 5, 5)
        hbox.pack_end(combobox)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            text = entry.get_text()
        else:
            text = ""
        dialog.destroy()
        return text

    def __wait_for_launcher_editor(self, process,
                                   old_path, new_path, identifier):
        if process.poll() != None:
            # Launcher editor closed.
            if os.path.isfile(new_path):
                # Update desktop_entry.
                desktop_entry = DesktopEntry(new_path)
                if identifier:
                    group = self.groups[identifier]
                else:
                    group = self.groups[old_path]
                group.pinned = True
                group.set_desktop_entry(desktop_entry)
                self.update_pinned_apps_list()
            return False
        return True

    #### Media players
    def get_media_controls(self, identifier):
        if not identifier in self.media_controls:
            self.media_controls[identifier] = MediaButtons(identifier)
        return self.media_controls[identifier]

    def media_player_added(self, name):
        if not self.globals.settings["media_buttons"]:
            return
        identifiers = [MPS.get(id, id) for id in self.groups.get_identifiers()]
        if self.groups is not None and name in identifiers:
            media_controls = self.get_media_controls(name)
            group = self.groups[identifiers.index(name)]
            group.add_media_controls(media_controls)

    def media_player_removed(self, name):
        identifiers = [MPS.get(id, id) for id in self.groups.get_identifiers()]
        if self.groups is not None and name in identifiers:
            group = self.groups[identifiers.index(name)]
            group.remove_media_controls()
        if name in self.media_controls:
            media_controls = self.media_controls.pop(name)
            media_controls.remove()
            media_controls.destroy()

    def __media_player_check(self, identifier, group):
        identifier = MPS.get(identifier, identifier)
        if self.globals.settings["media_buttons"] and \
           self.mpris.has_player(identifier):
            media_controls = self.get_media_controls(identifier)
            group.add_media_controls(media_controls)
        else:
            group.remove_media_controls()

    def __on_media_controls_changed(self, *args):
        if self.globals.settings["media_buttons"]:
            for player in self.mpris.get_players():
                self.media_player_added(player)
        else:
            for group in self.groups:
                group.remove_media_controls()

    #### DockManager
    def get_dm_paths(self):
        paths = []
        for group in self.groups:
            path = group.get_dm_path()
            if path is not None:
                paths.append(path)
        return paths

    def get_dm_paths_by_name(self, name):
        paths = []
        for group in self.groups:
            path = group.get_dm_path_by_name(name)
            if path is not None:
                paths.append(path)
        return paths

    def get_dm_paths_by_desktop_file(self, name):
        paths = []
        for group in self.groups:
            path = group.get_dm_path_by_desktop_file(name)
            if path is not None:
                paths.append(path)
        return paths

    def get_dm_paths_by_pid(self, pid):
        paths = []
        for group in self.groups:
            path = group.get_dm_path_by_pid(pid)
            if path is not None:
                paths.append(path)
        return paths

    def get_dm_paths_by_xid(self):
        paths = []
        for group in self.groups:
            path = group.get_dm_path_by_xid(xid)
            if path is not None:
                paths.append(path)
        return paths

    def add_dm_item(self, path):
        self.dockmanager.ItemAdded(dbus.ObjectPath(path))

    def remove_dm_item(self, path):
        self.dockmanager.ItemRemoved(dbus.ObjectPath(path))

    def __start_dockmanager(self):
        if not self.globals.settings['dockmanager']:
            return
        if not self.dockmanager:
            try:
                self.dockmanager = DockManager(self)
            except:
                logger.exception("Couldn't start Dockmanager, is it " + \
                                 "prehaps already in use by some other dock?")
                return
        if not self.dockmanager:
            return
        for group in self.groups:
            group.add_dockmanager()
        self.dockmanager.reset()

    def __stop_dockmanager(self):
        for group in self.groups:
            group.remove_dockmanager()
        if self.dockmanager:
            self.dockmanager.remove()
            self.dockmanager = None

    def __on_dockmanager_changed(self, *args):
        if self.globals.settings["dockmanager"]:
            self.__start_dockmanager()
        else:
            self.__stop_dockmanager()

    #### Keyboard actions
    def __gkeys_changed(self, arg=None, dialog=True):
        functions = {"gkeys_select_next_group": self.__gkey_select_next_group,
                     "gkeys_select_previous_group": \
                                self.__gkey_select_previous_group,
                     "gkeys_select_next_window": \
                                self.__gkey_select_next_window_in_group,
                     "gkeys_select_previous_window": \
                                self.__gkey_select_previous_window_in_group}
        translations = {
           "gkeys_select_next_group": _("Select next group"),
           "gkeys_select_previous_group": _("Select previous group"),
           "gkeys_select_next_window": _("Select next window in group"),
           "gkeys_select_previous_window": _("Select previous window in group")
                       }
        for (s, f) in functions.items():
            if self.gkeys[s] is not None:
                keybinder.unbind(self.gkeys[s])
                self.gkeys[s] = None
            if not self.globals.settings[s]:
                # The global key is not in use
                continue
            keystr = self.globals.settings["%s_keystr" % s]
            # Fix for <Shift>Tab keybindings
            if "<shift>" in keystr.lower() and "Tab" in keystr:
                n = keystr.lower().find("<shift>")
                keystr = keystr[:n] + keystr[(n + 7):]
                if not "ISO_Left_Tab" in keystr:
                    keystr = keystr.replace("Tab", "ISO_Left_Tab")

            try:
                if keybinder.bind(keystr, f):
                    # Key succesfully bound.
                    self.gkeys[s]= keystr
                    error = False
                else:
                    error = True
                    reason = ""
                    # Keybinder sometimes doesn't unbind faulty binds.
                    # We have to do it manually.
                    try:
                        keybinder.unbind(keystr)
                    except:
                        pass
            except KeyError:
                error = True
                reason = "The key is already bound elsewhere."
            if error:
                message = "Error: DockbarX couldn't set " + \
                          "global keybinding '%s' for %s." % (keystr, s)
                text = "%s %s"%(message, reason)
                logger.warning(text)
                if dialog:
                    md = gtk.MessageDialog(
                            None,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                            text
                                          )
                    md.run()
                    md.destroy()

    def __gkey_select_next_group(self):
        self.__grab_keyboard("gkeys_select_next_group_keystr")
        self.__select_next_group()

    def __gkey_select_previous_group(self):
        self.__grab_keyboard("gkeys_select_previous_group_keystr")
        self.__select_previous_group()

    def __gkey_select_next_window_in_group(self):
        self.__grab_keyboard("gkeys_select_next_window_keystr")
        self.__select_next_window_in_group()

    def __gkey_select_previous_window_in_group(self):
        self.__grab_keyboard("gkeys_select_previous_window_keystr")
        self.__select_previous_window_in_group()

    def __grab_keyboard(self, keystr):
        applet = self.parent_window or self.applet or self.awn_applet
        if applet:
            gtk.gdk.keyboard_grab(applet.window)
            connect(applet, "key-release-event", self.__key_released)
            connect(applet, "key-press-event", self.__key_pressed)

            # Find the mod key(s) which realse should finnish the selection.
            mod_keys = ["Control", "Super", "Alt"]
            mod_keys = [key for key in mod_keys \
                    if key.lower() in self.globals.settings[keystr].lower()]
            if "next" in keystr:
                keystr = keystr.replace("next", "previous")
            else:
                keystr = keystr.replace("previous","next")
            self.mod_keys = [key for key in mod_keys \
                    if key.lower() in self.globals.settings[keystr].lower()]
            if not self.mod_keys:
                self.mod_keys = mod_keys
            
            if self.is_dock:
                applet.show_dock()

    def __select_next_group(self, previous=False):
        if len(self.groups) == 0:
            return
        if self.next_group is None or not (self.next_group in self.groups):
            for group in self.groups:
                if group.has_active_window:
                    self.next_group = group
                    break
            else:
                self.next_group = self.groups[0]
            old_next_group = None
        else:
            old_next_group = self.next_group
            i = self.groups.index(self.next_group)
            groups = self.groups[i+1:] + self.groups[:i]
            if previous:
                groups.reverse()
            if self.globals.settings["gkeys_select_next_group_skip_launchers"]:
                for group in groups:
                    if group.get_count() != 0:
                        self.next_group = group
                        break
                else:
                    return
            else:
                self.next_group = groups[0]
        group = self.next_group
        if group.get_count() > 0:
            group.action_select_next(keyboard_select=True)
        else:
            group.show_launch_popup()
        if not self.globals.settings["select_next_activate_immediately"] and \
           old_next_group and old_next_group != group:
                old_next_group.scrollpeak_abort()


    def __select_previous_group(self):
        self.__select_next_group(previous=True)

    def __select_next_window_in_group(self, previous=False):
        if not self.next_group:
            for group in self.groups:
                if group.has_active_window:
                    self.next_group = group
                    break
        self.next_group.action_select_next(previous=previous,
                                           keyboard_select=True)

    def __select_previous_window_in_group(self):
        self.__select_next_window_in_group(previous=True)

    def __key_pressed(self, widget, event):
        functions = {"gkeys_select_next_group": self.__select_next_group,
                     "gkeys_select_previous_group": \
                                self.__select_previous_group,
                     "gkeys_select_next_window": \
                                self.__select_next_window_in_group,
                     "gkeys_select_previous_window": \
                                self.__select_previous_window_in_group}
        keyname = gtk.gdk.keyval_name(event.keyval)
        # Check if it's a number shortcut.
        if gtk.gdk.SUPER_MASK & event.state:
            keys = [str(n) for n in range(10)]
            if keyname in keys:
                self.__on_number_shortcut_pressed(int(keyname),
                                                  keyboard_grabbed=True)
                return
        # Check if it's any other global shortcut.
        for name, func in functions.items():
            if not self.globals.settings[name]:
                continue
            keystring = self.globals.settings["%s_keystr" % name]
            mod_keys = {"super": gtk.gdk.SUPER_MASK,
                        "alt": gtk.gdk.MOD1_MASK,
                        "control": gtk.gdk.CONTROL_MASK,
                        "shift": gtk.gdk.SHIFT_MASK}
            if "ISO_Left_Tab" in keystring:
                # ISO_Left_Tab implies that shift has been used in combination
                # with tab so we don't need to check if shift is pressed
                # or not.
                del mod_keys["shift"]
            elif "shift" in keystring.lower() and "Tab" in keystring:
                keystring = keystring.replace("Tab", "ISO_Left_Tab")
            for key, mask in mod_keys.items():
                if (key in keystring.lower()) !=  bool(mask & event.state):
                    break
            else:
                keystring = keystring.rsplit(">")[-1]
                if keyname.lower() == keystring.lower():
                    func()

    def __key_released(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        for key in self.mod_keys:
            if key in keyname:
                group = self.next_group
                if group:
                    if group.get_count() > 0:
                        group.scrollpeak_select()
                    else:
                        if group.media_controls:
                            success = group.media_controls.show_player()
                            if success:
                                group.scrollpeak_abort()
                        if not group.media_controls or not success:
                            group.action_launch_application()
                self.next_group = None
                gtk.gdk.keyboard_ungrab()
                applet = self.parent_window or self.applet or self.awn_applet
                if applet:
                    disconnect(applet)
                break

    def __init_number_shortcuts(self, *args):
        for i in range(10):
            key = "<super>%s" % i
            if self.globals.settings["use_number_shortcuts"]:
                try:
                    success = keybinder.bind(key,
                                         self.__on_number_shortcut_pressed, i)
                except:
                    success = False
                if not success:
                    # Keybinder sometimes doesn't unbind faulty binds.
                    # We have to do it manually.
                    try:
                        keybinder.unbind(key)
                    except:
                        pass
            else:
                try:
                    keybinder.unbind(key)
                except:
                    pass

    def __on_number_shortcut_pressed(self, n, keyboard_grabbed=False):
        if n == 0:
            n = 10
        n -= 1
        try:
            group = self.groups[n]
        except IndexError:
            return
        windows = group.get_windows()
        applet = self.parent_window or self.applet or self.awn_applet
        if len(windows) > 1:
            group.action_select_next(keyboard_select=True)
            if self.next_group is not None and self.next_group != group:
                self.next_group.scrollpeak_abort()
            self.next_group = group
            if applet and not keyboard_grabbed:
                gtk.gdk.keyboard_grab(applet.window)
                connect(applet, "key-release-event", self.__key_released)
                connect(applet, "key-press-event", self.__key_pressed)
                self.mod_keys = ["Super"]
        else:
            gtk.gdk.keyboard_ungrab()
            if self.next_group:
                self.next_group.scrollpeak_abort()
            if applet:
                disconnect(applet)
            self.next_group = None
            if self.is_dock:
                self.parent_window.show()
                gobject.timeout_add(600, self.parent_window.show_dock)
        if not windows:
            success = False
            if group.media_controls:
                success = group.media_controls.show_player()
            if not group.media_controls or not success:
                group.action_launch_application()
        if len(windows) == 1:
            windows[0].action_select_window()
