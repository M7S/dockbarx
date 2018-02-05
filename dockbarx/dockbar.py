#!/usr/bin/python2

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


import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GObject
import sys
import os
import dbus
import cairowidgets
import weakref
from time import time
from xdg.DesktopEntry import ParsingError


from common import *
from log import logger

import i18n
_ = i18n.language.gettext

VERSION = "0.93-gtk3"


ATOM_WM_CLASS = Gdk.atom_intern("WM_CLASS", False)

SPECIAL_RES_CLASSES = {
                        "thunderbird-bin": "thunderbird",
                        "amarokapp": "amarok",
                        "lives-exe": "lives",
                        "exaile.py": "exaile",
                        "eric4.py": "eric",
                        "geogebra-geogebra": "geogebra",
                        "tuxpaint.tuxpaint": "tuxpaint",
                        "quodlibet":"quod libet",
                        "xfce4-terminal":"exo-terminal-emulator",
                        "xbmc.bin":"xbmc"
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
        self.about = Gtk.AboutDialog()
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

class Spacer(Gtk.EventBox):
    def __init__(self, dockbar):
        GObject.GObject.__init__(self)
        self.globals = Globals()
        self.dockbar_r = weakref.ref(dockbar)
        self.set_visible_window(False)

        self.drag_dest_set(0, [], 0)
        self.drag_entered = False
        self.connect("button-release-event", self.on_button_release_event)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-leave", self.on_drag_leave)
        self.connect("drag-drop", self.on_drag_drop)
        self.connect("drag-data-received", self.on_drag_data_received)

    def on_button_release_event(self, widget, event):
        if event.button != 3:
            return
        self.dockbar_r().create_popup_menu(event)

    def on_drag_drop(self, widget, drag_context, x, y, t):
        targets = [target.name() for target in drag_context.list_targets()]
        if "text/groupbutton_name" in targets:
            self.drag_get_data(drag_context, "text/groupbutton_name", t)
            drag_context.finish(True, False, t)
        elif "text/uri-list" in targets:
            self.drag_get_data(drag_context, "text/uri-list", t)
            drag_context.finish(True, False, t)
        else:
            drag_context.finish(False, False, t)
        return True

    def on_drag_data_received(self, widget, context, x, y, selection, targetType, t):
        selection_target = selection.get_target().name()
        if selection_target == "text/groupbutton_name":
            self.dockbar_r().groupbutton_moved(selection.get_data(),
                                                    "after")
        elif selection_target == "text/uri-list":
            if ".desktop" in selection.get_data():
                # .desktop file! This is a potential launcher.
                #remove "file://" and "/n" from the URI
                path = selection.get_data()
                if path.startswith("file://"):
                    path = path[7:]
                else:
                    # No support for other kind of uris.
                    return
                path = path.rstrip()
                path = path.replace("%20"," ")
                self.dockbar_r().launcher_dropped(path, "after")

    def on_drag_motion(self, widget, drag_context, x, y, t):
        if not self.drag_entered:
            self.on_drag_enter(drag_context, x, y, t)
        targets = [target.name() for target in drag_context.list_targets()]
        if "text/groupbutton_name" in targets:
            Gdk.drag_status(drag_context, Gdk.DragAction.MOVE, t)
        elif "text/uri-list" in targets():
            Gdk.drag_status(drag_context, Gdk.DragAction.COPY, t)
        else:
            Gdk.drag_status(drag_context, Gdk.DragAction.PRIVATE, t)
        return True

    def on_drag_enter(self, widget, drag_context, x, y, t):
        self.drag_entered = True

    def on_drag_leave(self, widget, drag_context, t):
        self.drag_entered = False

class GroupList(list):
    def __init__(self, dockbar, orient):
        list.__init__(self)
        self.dockbar_r = weakref.ref(dockbar)
        self.orient = orient
        self.overflow_set = 0
        self.spacing = 0
        self.button_size = 0
        self.arrows_visible = False
        self.arrow_box = None
        self.aspect_ratio = None
        self.max_size = None
        if self.orient in ("down", "up"):
            self.container = Gtk.HBox()
            self.box = Gtk.HBox()
        else:
            self.container = Gtk.VBox()
            self.box = Gtk.VBox()
        self.allocation_sid = self.box.connect("size-allocate",
                                               self.on_size_allocate)
        self.box.pack_start(self.container, False, False, 0)
        self.empty = Spacer(dockbar)
        self.box.pack_start(self.empty, True, True, 0)
        self.box.show_all()
        self.__make_arrow_buttons()

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
        list.remove(self, group)
        list.insert(self, index, group)
        self.container.reorder_child(group.button, index)
        self.manage_size_overflow()

    def append(self, group):
        list.append(self, group)
        self.container.pack_start(group.button, False, False, 0)
        self.manage_size_overflow()

    def insert(self, index, group):
        list.insert(self, index, group)
        self.container.pack_start(group.button, False, False, 0)
        self.container.reorder_child(button, index)
        self.manage_size_overflow()

    def remove(self, group):
        list.remove(self, group)
        group.destroy()
        self.manage_size_overflow()

    def show(self):
        self.box.show()
        self.container.show()

    def set_spacing(self, gap):
        self.container.set_spacing(gap)

    def set_aspect_ratio(self, aspect_ratio):
        if aspect_ratio == self.aspect_ratio:
            return
        self.aspect_ratio = aspect_ratio
        self.calculate_button_size()

    def set_orient(self, orient):
        for pair in (("up", "down"), ("left", "right")):
            if orient in pair and self.orient in pair:
                # The orient hasn't changed in regards to horizontal
                # or vertical orient. No need to rebuild the [H/V]Box.
                self.orient = orient
                return
        self.orient = orient
        # Make new box and container
        if self.orient in ("down", "up"):
            container = Gtk.HBox()
            box = Gtk.HBox()
        else:
            container = Gtk.VBox()
            box = Gtk.VBox()
        # Remove the children from the container.
        for child in self.container.get_children():
            self.container.remove(child)
            container.pack_start(child, True, True, 0)
        # Destroy the old box and container.
        self.box.remove(self.container)
        self.box.remove(self.empty)
        self.box.remove(self.arrow_box)
        self.box.disconnect(self.allocation_sid)
        self.container.destroy()
        self.empty.destroy()
        self.box.destroy()
        self.box = box
        self.container = container
        self.box.pack_start(self.container, False, False, 0)
        self.empty = Spacer(self.dockbar_r())
        self.box.pack_start(self.empty, True, True, 0)
        self.__make_arrow_buttons()
        self.allocation_sid = self.box.connect("size-allocate",
                                               self.on_size_allocate)

    def __make_arrow_buttons(self):
        if self.arrow_box is not None:
            self.next_button.destroy()
            self.previous_button.destroy()
            self.arrow_box.destroy()
        if self.orient in ("down", "up"):
            box = Gtk.VBox()
            self.next_button = cairowidgets.CairoArrowButton("right")
            self.previous_button = cairowidgets.CairoArrowButton("left")
        else:
            box = Gtk.HBox()
            self.next_button = cairowidgets.CairoArrowButton("down")
            self.previous_button = cairowidgets.CairoArrowButton("up")
        self.arrow_box = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.arrow_box.add(box)
        box.pack_start(self.next_button, True, True, 0)
        box.pack_start(self.previous_button, True, True, 0)
        self.box.pack_start(self.arrow_box, False, False, 0)

        #Connections
        next_sid = self.next_button.connect("clicked", self.on_next_button_clicked)
        previous_sid = self.previous_button.connect("clicked", self.on_previous_button_clicked)

    def show_arrow_buttons(self):
        self.arrows_visible = True
        self.arrow_box.show_all()

    def hide_arrow_buttons(self):
        self.arrows_visible = False
        self.arrow_box.hide()

    def get_shown_groups(self):
        # returns groups that are visible
        groups = []
        for group in self:
            if group.get_count() == 0 and not group.pinned:
                continue
            groups.append(group)
        return groups

    def manage_size_overflow(self):
        if self.button_size <= 1:
            return
        groups = self.get_shown_groups()
        if self.overflow_set < 0:
            self.overflow_set = 0
        if not groups:
            # No buttons are shown on the screen, no size overflow.
            self.hide_arrow_buttons()
            return
        max_size = self.calculate_max_size()
        if max_size < self.button_size:
            return
        max_buttons = max_size / self.button_size
        if len(groups) <= self.overflow_set * max_buttons:
            # The current overflow_set is too high and would
            # show a empty screen, let's decrease it to something
            # that will actually show something.
            self.overflow_set = (len(groups) - 1) / max_buttons
        if len(groups) <= max_buttons:
            self.hide_arrow_buttons()
        else:
            self.show_arrow_buttons()
        # Button sensitivity
        if self.overflow_set == 0:
            self.previous_button.set_sensitive(False)
        else:
            self.previous_button.set_sensitive(True)
        if self.overflow_set == (len(groups) - 1) / max_buttons:
            self.next_button.set_sensitive(False)
        else:
            self.next_button.set_sensitive(True)
        # Hide all buttons and then show the ones that is
        # in the currently shown set.

        for group in groups:
            group.button.hide()
        begin = self.overflow_set * max_buttons
        end = (self.overflow_set + 1) * max_buttons
        if end > len(groups):
            end = len(groups)
            begin = max(0, end - max_buttons)
        for group in groups[begin:end]:
            group.button.show()
        #TODO: Fix locked popup behavior when group disapears or move

    def calculate_button_size(self):
        # Calculate the button size.
        if self.orient in ("down", "up"):
            size = self.container.get_allocation().height
        else:
            size = self.container.get_allocation().width
        if size <= 1:
            # Not yet realized. No reason to continue.
            return
        spacing = self.container.get_spacing()
        button_size = int(size * self.aspect_ratio + spacing)
        if button_size != self.button_size:
            # The button size has changed lets check if all buttons
            # still can be shown at once.
            self.button_size = button_size
            self.manage_size_overflow()

    def set_max_size(self, max_size):
        # When runned in dock (and possibly other cases) the max
        # size is set from outside this class using this funtction.
        self.max_size = max_size
        self.manage_size_overflow()

    def calculate_max_size(self):
        if self.max_size is None:
            # Maxsize is not set externally use the allocation size.
            if self.orient in ("down", "up"):
                size = self.box.get_allocation().width
            else:
                size = self.box.get_allocation().height
        else:
            size = self.max_size
        # Remove the size of the arrows (if visible) from max size.
        if self.orient in ("down", "up"):
            if self.arrows_visible:
                size = size - self.arrow_box.get_allocation().width
        else:
            if self.arrows_visible:
                size = size - self.arrow_box.get_allocation().height
        # Add gap size to max size since button size includes gap size
        # and the number of gaps is one less than the number of
        # buttons.
        size = size + self.container.get_spacing()
        return size

    def on_size_allocate(self, widget, allocation):
        if allocation.width <= 1:
            # Not yet realized.
            return
        self.calculate_button_size()

    def on_next_button_clicked(self, *args):
        self.overflow_set = self.overflow_set + 1
        self.manage_size_overflow()

    def on_previous_button_clicked(self, *args):
        self.overflow_set = self.overflow_set - 1
        self.manage_size_overflow()

    def destroy(self):
        self.box.disconnect(self.allocation_sid)
        self.container.destroy()
        self.empty.destroy()
        self.box.destroy()


class DockBar():
    def __init__(self, parent):
        logger.info("DockbarX %s"%VERSION)
        logger.info("DockbarX init")
        self.parent = parent
        self.windows = None
        self.theme = None
        self.popup_style = None
        self.skip_tasklist_windows = None
        self.next_group = None
        self.dockmanager = None
        self.groups = None
        self.size = None
        self.kbd_sid = None

        self.parent_window_reporting = False
        self.parent_handles_menu = False
        self.keyboard_show_dock = False
        self.no_theme_change_reload = False
        self.no_dbus_reload = False
        self.orient = "down"

        self.globals = Globals()
        self.globals.connect("theme-changed", self.__on_theme_changed)
        self.globals.connect("media-buttons-changed",
                             self.__on_media_controls_changed)
        self.globals.connect("dockmanager-changed",
                             self.__on_dockmanager_changed)

    #### Parent functions
    # The dock/applet/widget interacts with dockbar through these functions.

    def load(self):
        """Loads DockbarX. Should be run once DockbarX is initiated."""

        # Most things are imported here instead of immediately at startup
        # since python gnomeapplet must be realized quickly to avoid crashes.
        global subprocess
        import subprocess
        global Gio
        from gi.repository import Gio
        gi.require_version('Keybinder', '3.0')
        global Keybinder
        from gi.repository import Keybinder
        gi.require_version('Wnck', '3.0')
        global Wnck
        from gi.repository import Wnck
        global Group
        global GroupIdentifierError
        from groupbutton import Group, GroupIdentifierError
        global Theme
        global NoThemesError
        global PopupStyle
        from theme import Theme, NoThemesError, PopupStyle
        global Mpris2Watch
        global MediaButtons
        from mediabuttons import Mpris2Watch, MediaButtons
        global DockManager
        from dockmanager import DockManager
        global DockbarDBus
        from dbx_dbus import DockbarDBus
        global UnityWatcher
        from unity import UnityWatcher

        # Media Controls
        self.media_controls = {}
        self.mpris = Mpris2Watch(self)

        # Dbus
        self.dbus = DockbarDBus(self)

        # Wnck for controlling windows
        Wnck.set_client_type(2) # 2=CLIENT_TYPE_PAGER
        self.screen = Wnck.Screen.get_default()
        self.root_xid = int(Gdk.Screen.get_default().get_root_window().get_xid())
        self.screen.force_update()

        # Keybord shortcut stuff
        self.gkeys = {"gkeys_select_next_group": None,
                      "gkeys_select_previous_group": None,
                      "gkeys_select_next_window": None,
                      "gkeys_select_previous_window": None}
        self.__gkeys_changed(dialog=False)
        self.__init_number_shortcuts()
        self.globals.connect("gkey-changed", self.__gkeys_changed)
        self.globals.connect("use-number-shortcuts-changed",
                             self.__init_number_shortcuts)
        Keybinder.init()
        Keybinder.set_use_cooked_accelerators(False)

        # Unity stuff
        self.unity_watcher = UnityWatcher(self)
        if self.globals.settings["unity"]:
            self.unity_watcher.start()
        self.globals.connect("unity-changed", self.__on_unity_changed)

        # Generate Gio apps so that windows and .desktop files
        # can be matched correctly with eachother.
        self.apps_by_id = {}
        self.app_ids_by_exec = {}
        self.app_ids_by_name = {}
        self.app_ids_by_longname = {}
        self.app_ids_by_cmd = {}
        self.wine_app_ids_by_program = {}
        for app in Gio.app_info_get_all():
            id = app.get_id()
            id = id[:id.rfind(".")].lower()
            name = app.get_name().lower()
            exe = app.get_executable()
            if exe:
                self.apps_by_id[id] = app
                try:
                    cmd = app.get_commandline().lower()
                except AttributeError:
                    # Older versions of gio doesn't have get_comandline.
                    cmd = ""
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

        self.reload(tell_parent=False)

    def reload(self, event=None, data=None, tell_parent=True):
        """Reloads DockbarX."""
        logger.info("DockbarX reload")
        # Clear away the old stuff, if any.
        if self.windows:
            # Remove windows and unpinned group buttons
            for win in self.screen.get_windows():
                self.__on_window_closed(None, win)
        # Remove pinned group buttons
        if self.groups is not None:
            for group in self.groups:
                self.groups.remove(group)
                group.destroy()
            self.groups.destroy()
            del self.groups
        del self.skip_tasklist_windows
        del self.windows
        disconnect(self.globals)
        if self.theme:
            self.theme.remove()

        # Start building up stuff again.
        self.skip_tasklist_windows = []
        self.windows = {}
        self.globals.set_shown_popup(None)
        self.next_group = None

        # Reload theme.
        try:
            if self.theme is None:
                self.theme = Theme()
            else:
                self.theme.on_theme_changed()
        except NoThemesError, details:
            logger.exception("Error: Couldn't find any themes")
            sys.exit(1)

        # Reload popup style.
        if self.popup_style is None:
            self.popup_style = PopupStyle()
        else:
            self.popup_style.reload()

        # Set up groups.
        self.groups = GroupList(self, self.orient)
        self.groups.set_spacing(self.theme.get_gap())
        self.groups.set_aspect_ratio(self.theme.get_aspect_ratio())
        self.groups.show()
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
        # Since the old container is destroyed we need to tell
        # parent to readd it.
        if tell_parent:
            try:
                self.parent.readd_container(self.get_container())
            except AttributeError:
                pass


    def set_orient(self, orient):
        """ Set the orient (up, down, left or right) and prepares the container.

            Don't forget to add the new container
            to the dock/applet/widget afterwards."""
        if orient == self.orient:
            return
        self.orient = orient
        if self.groups is None:
            return
        self.groups.set_orient(orient)

        # Set aspect ratio and spacing.
        if self.orient in ("up", "down"):
            aspect_ratio = self.theme.get_aspect_ratio(False)
        else:
            aspect_ratio = self.theme.get_aspect_ratio(True)
        self.groups.set_aspect_ratio(aspect_ratio)
        self.groups.set_spacing(self.theme.get_gap())

        # Add the group buttons to the new container.
        for group in self.groups:
            preview = self.globals.settings["preview"]
            group.window_list.set_show_previews(preview)
            if orient in ("down", "up"):
                # The direction of the pointer isn't important here, we only
                # need the right amount of padding so that the popup has right
                # width and height for placement calculations.
                group.popup.point("down")
            if orient in ("left", "right"):
                group.popup.point("left")

        if self.globals.settings["show_only_current_desktop"]:
            self.__on_desktop_changed()
        #~ self.groups.manage_size_overflow() # Don't think line does anything useful here. Remove if everything looks OK.

        # If a floating window panel is shown, close it.
        lp = self.globals.get_locked_popup()
        if lp:
            group = lp.group_r()
            group.remove_locked_popup()
            group.add_locked_popup()

    def get_orient(self):
        """Returns orient of DockbarX"""
        return self.orient

    def get_container(self):
        """Returns the HBox/VBox that contains all group buttons"""
        return self.groups.box

    def get_windows(self):
        """Returns the dict of wnck windows and identifiers"""
        return self.windows

    def dockbar_moved(self):
        """This method should be called when dockbar has been moved"""
        # Inform all groups about the change.
        if self.groups:
            for group in self.groups:
                group.button.dockbar_moved()

    def set_size(self, size):
        """Manualy set and update the size of group buttons"""
        if size == self.size:
            return
        self.size = size
        for group in self.groups:
            group.button.icon_factory.set_size(size)
            group.button.update_state(force_update=True)

    def set_max_size(self, max_size):
        """Set the max size DockbarX is allowed to occupy."""
        self.groups.set_max_size(max_size)

    def set_parent_window_reporting(self, report):
        """If True, dockbarx reports to the parent when windows are added or removed"""
        self.parent_window_reporting = report

    def set_parent_handles_menu(self, handles_menu):
        """If True, the create_popup_menu function of the parent will be used instead of dockbar's own."""
        self.parent_handles_menu = handles_menu

    def set_keyboard_show_dock(self, keyboard_show_dock):
        """For DockX. If true the dock is shown when dockbarx keyboard shortcuts are used."""
        self.keyboard_show_dock = keyboard_show_dock

    def set_no_theme_change_reload(self, no_theme_change_reload):
        """If True, the dockbar won't reload automatically on theme change."""
        self.no_theme_change_reload = no_theme_change_reload

    def set_no_dbus_reload(self, no_dbus_reload):
        """If True, the dockbar won't reload on dbus reload signal."""
        self.no_dbus_reloadd = no_dbus_reload

    def set_expose_on_clear(self, expose_on_clear):
        """Dummy function. Does nothing now.

        Left here just in case some backend should try to call it."""
        pass

    def open_preference(self):
        # Starts the preference dialog
        os.spawnlp(os.P_NOWAIT,"/usr/bin/dbx_preference",
                   "/usr/bin/dbx_preference")

    #### Menu
    def create_popup_menu(self, event):
        if self.parent_handles_menu:
            self.parent.create_popup_menu(event)
            return
        menu = Gtk.Menu()
        menu.connect("selection-done", self.__menu_closed)
        preference_item = Gtk.MenuItem(_("Preferences"))
        menu.append(preference_item)
        preference_item.connect("activate", self.on_ppm_pref)
        preference_item.show()
        reload_item = Gtk.MenuItem(_("Reload"))
        menu.append(reload_item)
        reload_item.connect("activate", self.reload)
        reload_item.show()
        about_item = Gtk.MenuItem(_("About"))
        menu.append(about_item)
        about_item.connect("activate", self.on_ppm_about)
        about_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.globals.gtkmenu = menu

    def __menu_closed(self, menushell):
        self.globals.gtkmenu = None
        menushell.destroy()

    def on_ppm_pref(self,event=None,data=None):
        self.open_preference()

    def on_ppm_about(self,event,data=None):
        AboutDialog()

    def __on_theme_changed(self, *args):
        if not self.no_theme_change_reload:
            self.reload()

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
            if self.parent_window_reporting:
                self.parent.remove_window(window)
            disconnect(window)
            self.__remove_window(window)
        if window in self.skip_tasklist_windows:
            self.skip_tasklist_windows.remove(window)

    def __on_window_opened(self, screen, window):
        if not (window.get_window_type() in [Wnck.WindowType.NORMAL,
                                             Wnck.WindowType.DIALOG]):
            return
        connect(window, "state-changed", self.__on_window_state_changed)
        if window.is_skip_tasklist():
            self.skip_tasklist_windows.append(window)
            return
        self.__add_window(window)
        if self.parent_window_reporting:
            self.parent.add_window(window)

    def __on_window_state_changed(self, window, changed_mask, new_state):
        if window in self.skip_tasklist_windows and \
           not window.is_skip_tasklist():
            self.__add_window(window)
            self.skip_tasklist_windows.remove(window)
            if self.parent_window_reporting:
                self.parent.add_window(window)
        if window.is_skip_tasklist() and \
           not window in self.skip_tasklist_windows:
            if self.parent_window_reporting:
                self.parent.remove_window(window)
            self.__remove_window(window)
            self.skip_tasklist_windows.append(window)

    def __on_desktop_changed(self, screen=None, workspace=None):
        if not self.globals.settings["show_only_current_desktop"]:
            return
        for group in self.groups:
            group.desktop_changed()
        self.groups.manage_size_overflow()


    #### Groupbuttons
    def remove_groupbutton(self, group):
        self.groups.remove(group)
        self.update_pinned_apps_list()
        if self.next_group and \
           self.next_group in self.groups:
            self.next_group.scrollpeak_abort()
            self.next_group = None

    def groupbutton_moved(self, name, drop_point, drop_position="end"):
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
            if drop_position == "start":
                index -= 1
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
                         pinned=False, index=None, window=None):
        group = Group(self, identifier, desktop_entry, pinned, self.size)
        if window is not None:
            # Windows are added here instead of later so that
            # overflow manager knows if the button should be
            # shown or not.
            group.add_window(window)
        if index is None or index == -1:
            self.groups.append(group)
        else:
            self.groups.insert(index, group)
        self.__media_player_check(identifier, group)
        self.unity_watcher.apply_for_group(group)
        self.update_pinned_apps_list()
        group.button.update_state
        # If the size is set (and is bigger than 10px everything else is assumed to be
        # accidentally given sizes during startup) we need to update the state to make
        # make a button surface with the right size.
        if self.size is not None and self.size > 10:
            # Update the surface
            group.button.update_state(force_update=True)
        return group

    def __add_window(self, window):
        try:
            #Support of wine applications - get name of .exe as identifier
            gdkw = gtk.gdk.window_foreign_new(window.get_xid())
            wm_class_property = gdkw.property_get(ATOM_WM_CLASS)[2].split("\0")
            res_class = wm_class_property[1].lower()
            res_name  = wm_class_property[0].lower()
        except:
            res_class = window.get_class_group().get_res_class().lower()
            res_name = window.get_class_group().get_name().lower()
        if window.has_name():
            fallback = window.get_name().lower()
        else:
            #in case window has no name - issue with Spotify
            pid = window.get_pid()
            try:
                f = open("/proc/"+str(pid)+"/cmdline", "r")
            except:
                raise
            cmd = f.readline().split("\0")[0]
            if "/" in cmd:
                fallback = cmd.split("/")[-1]
            else:
                fallback = cmd
        identifier = res_class or res_name or fallback
        # Special cases
        if identifier in SPECIAL_RES_CLASSES:
            identifier = SPECIAL_RES_CLASSES[identifier]
        wine = False
        chromium = False
        if ".exe" in identifier:
            if self.globals.settings["separate_wine_apps"]:
                wine = True
            else:
                identifier = "wine"
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
                                                desktop_entry=desktop_entry,
                                                window=window)
            except GroupIdentifierError:
                logger.exception("Couldn't make a new groupbutton.")
                del self.windows[window]
                return

    def __remove_window(self, window):
        identifier = self.windows[window]
        group = self.groups[identifier]
        group.del_window(window)
        if not len(group) and not group.pinned:
            self.remove_groupbutton(group)
        del self.windows[window]

    def __find_desktop_entry_id(self, identifier):
        id = None
        rc = identifier.lower()
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
        rc = identifier.lower()
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
    def launcher_dropped(self, path, drop_point, drop_position="end"):
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
        name = desktop_entry.getName()
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
            rc = identifier.lower()
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
                if drop_position == "start":
                    index -= 1
        group = self.groups.get(identifier) or self.groups.get(path)
        if group is not None:
            # Get the windows for repopulation of the new button
            window_list = [window.wnck for window in group]
            self.groups.remove(group)
        if index is None:
            index = self.groups.index(drop_point)
            if drop_position == "end":
                index += 1
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
        programs = ("gnome-desktop-item-edit",
                    "mate-desktop-item-edit", "exo-desktop-item-edit")
        for program in programs:
            if check_program(program):
                break
        else:
            logger.warning("Error: Found no program for editing .desktop files.")
            return
        process = subprocess.Popen([program, new_path], env=os.environ)
        GObject.timeout_add(100, self.__wait_for_launcher_editor,
                            process, path, new_path, identifier)

    def update_pinned_apps_list(self, arg=None):
        # Saves pinned_apps_list to GConf.
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

            name = desktop_entry.getName().lower()
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
        flags = Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        dialog = Gtk.MessageDialog(None,
                                   flags,
                                   Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.OK_CANCEL,
                                   None)
        dialog.set_title(_("Identifier"))
        dialog.set_markup("<b>%s</b>"%_("Enter the identifier here"))
        dialog.format_secondary_markup(
            _("You should have to do this only if the program fails to recognice its windows. ")+ \
            _("If the program is already running you should be able to find the identifier of the program from the dropdown list."))
        #create the text input field
        #entry = Gtk.Entry()
        combobox = Gtk.ComboBoxText.new_with_entry()
        entry = combobox.get_child()
        if identifier:
            entry.set_text(identifier)
        # Fill the popdown list with the names of all class
        # names of buttons that hasn't got a launcher already
        for group in self.groups:
            if not group.pinned:
                combobox.append_text(group.identifier)
        #allow the user to press enter to do ok
        entry.connect("activate",
                      lambda widget: dialog.response(Gtk.ResponseType.OK))
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Identifier:")), False, False, 5)
        hbox.pack_end(combobox, True, True, 0)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
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

    def __on_unity_changed(self, *args):
        if self.globals.settings["unity"]:
            self.unity_watcher.start()
        else:
            self.unity_watcher.stop()

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
                Keybinder.unbind(self.gkeys[s])
                self.gkeys[s] = None
            if not self.globals.settings[s]:
                # The global key is not in use
                continue
            keystr = self.globals.settings["%s_keystr" % s]
            # Fix for keyboard shortcut name since you cant have <> in gsettings schemas.
            keystr = keystr.replace("[", "<")
            keystr = keystr.replace("]", ">")

            try:
                if Keybinder.bind(keystr, f):
                    # Key succesfully bound.
                    self.gkeys[s]= keystr
                    error = False
                else:
                    error = True
                    reason = ""
                    # Keybinder sometimes doesn't unbind faulty binds.
                    # We have to do it manually.
                    try:
                        Keybinder.unbind(keystr)
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
                    md = Gtk.MessageDialog(
                            None,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                            text
                                          )
                    md.run()
                    md.destroy()

    def __gkey_select_next_group(self, key):
        #~ self.__grab_keyboard("gkeys_select_next_group_keystr")
        self.__set_select_or_launch_timout()
        self.__select_next_group()

    def __gkey_select_previous_group(self, key):
        #~ self.__grab_keyboard("gkeys_select_previous_group_keystr")
        self.__set_select_or_launch_timout()
        self.__select_previous_group()

    def __gkey_select_next_window_in_group(self, key):
        #~ self.__grab_keyboard("gkeys_select_next_window_keystr")
        self.__set_select_or_launch_timout()
        self.__select_next_window_in_group()

    def __gkey_select_previous_window_in_group(self, key):
        #~ self.__grab_keyboard("gkeys_select_previous_window_keystr")
        self.__set_select_or_launch_timout()
        self.__select_previous_window_in_group()

    def __set_select_or_launch_timout(self, t=600):
        if self.kbd_sid is not None:
            GObject.source_remove(self.kbd_sid)
            self.kbd_sid = None
        self.kbd_sid = GObject.timeout_add(t, self.__select_or_launch)

    #~ def __grab_keyboard(self, keystr):
        #~ if self.parent:
            #~ print "kbdgrb", Gdk.keyboard_grab(self.parent.get_window(), False, Gdk.CURRENT_TIME)
            #~ self.parent.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
            #~ self.parent.add_events(Gdk.EventMask.KEY_PRESS_MASK)
            #~ connect(self.parent, "key-release-event", self.__key_released)
            #~ connect(self.parent, "key-press-event", self.__key_pressed)

            #~ # Find the mod key(s) which realse should finnish the selection.
            #~ mod_keys = ["Control", "Super", "Alt"]
            #~ mod_keys = [key for key in mod_keys \
                    #~ if key.lower() in self.globals.settings[keystr].lower()]
            #~ if "next" in keystr:
                #~ keystr = keystr.replace("next", "previous")
            #~ else:
                #~ keystr = keystr.replace("previous","next")
            #~ self.mod_keys = [key for key in mod_keys \
                    #~ if key.lower() in self.globals.settings[keystr].lower()]
            #~ if not self.mod_keys:
                #~ self.mod_keys = mod_keys

            #~ if self.keyboard_show_dock:
                #~ self.parent.show_dock()

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

    #~ def __key_pressed(self, widget, event):
        #~ print "Keypressed"
        #~ functions = {"gkeys_select_next_group": self.__select_next_group,
                     #~ "gkeys_select_previous_group": \
                                #~ self.__select_previous_group,
                     #~ "gkeys_select_next_window": \
                                #~ self.__select_next_window_in_group,
                     #~ "gkeys_select_previous_window": \
                                #~ self.__select_previous_window_in_group}
        #~ keyname = Gdk.keyval_name(event.keyval)
        #~ # Check if it's a number shortcut.
        #~ if Gdk.EventMask.SUPER_MASK & event.get_state():
            #~ keys = [str(n) for n in range(10)]
            #~ if keyname in keys:
                #~ self.__on_number_shortcut_pressed(int(keyname),
                                                  #~ keyboard_grabbed=True)
                #~ return
        #~ # Check if it's any other global shortcut.
        #~ for name, func in functions.items():
            #~ if not self.globals.settings[name]:
                #~ continue
            #~ keystring = self.globals.settings["%s_keystr" % name]
            #~ keystr = keystr.replace("[", "<")
            #~ keystr = keystr.replace("]", ">")
            #~ mod_keys = {"super": Gdk.EventMask.SUPER_MASK,
                        #~ "alt": Gdk.ModifierType.MOD1_MASK,
                        #~ "control": Gdk.ModifierType.CONTROL_MASK,
                        #~ "shift": Gdk.ModifierType.SHIFT_MASK}
            #~ if "ISO_Left_Tab" in keystring:
                #~ # ISO_Left_Tab implies that shift has been used in combination
                #~ # with tab so we don't need to check if shift is pressed
                #~ # or not.
                #~ del mod_keys["shift"]
            #~ elif "shift" in keystring.lower() and "Tab" in keystring:
                #~ keystring = keystring.replace("Tab", "ISO_Left_Tab")
            #~ for key, mask in mod_keys.items():
                #~ if (key in keystring.lower()) !=  bool(mask & event.get_state()):
                    #~ break
            #~ else:
                #~ keystring = keystring.rsplit(">")[-1]
                #~ if keyname.lower() == keystring.lower():
                    #~ func()

    #~ def __key_released(self, widget, event):
        #~ print "key releasead: ", Gdk.keyval_name(event.keyval)
        #~ keyname = Gdk.keyval_name(event.keyval)
        #~ for key in self.mod_keys:
            #~ if key in keyname:
                #~ self.__select_or_launch()
                #~ Gdk.keyboard_ungrab(event.time)
                #~ if self.parent:
                    #~ disconnect(self.parent)
                #~ break

    def __select_or_launch(self, *args):
        group = self.next_group
        if group is not None:
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
        self.kbd_sid = None

    def __init_number_shortcuts(self, *args):
        for i in range(10):
            key = "<super>%s" % i
            if self.globals.settings["use_number_shortcuts"]:
                try:
                    success = Keybinder.bind(key,
                                         self.__on_number_shortcut_pressed, i)
                except:
                    success = False
                if not success:
                    # Keybinder sometimes doesn't unbind faulty binds.
                    # We have to do it manually.
                    try:
                        Keybinder.unbind(key)
                    except:
                        pass
            else:
                try:
                    Keybinder.unbind(key)
                except:
                    pass

    def __on_number_shortcut_pressed(self, key, n, keyboard_grabbed=False):
        if n == 0:
            n = 10
        n -= 1
        try:
            group = self.groups[n]
        except IndexError:
            return
        windows = group.get_windows()
        if len(windows) > 1:
            group.action_select_next(keyboard_select=True)
            if self.next_group is not None and self.next_group != group:
                self.next_group.scrollpeak_abort()
            self.next_group = group
            #~ if self.parent and not keyboard_grabbed:
                #~ print "kbdgrb", Gdk.keyboard_grab(self.parent.get_window(), False, Gdk.CURRENT_TIME)
                #~ connect(self.parent, "key-release-event", self.__key_released)
                #~ connect(self.parent, "key-press-event", self.__key_pressed)
                #~ self.mod_keys = ["Super"]
        else:
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
            if self.next_group:
                self.next_group.scrollpeak_abort()
            if self.parent:
                disconnect(self.parent)
            self.next_group = None
            if self.keyboard_show_dock:
                self.parent.show()
                GObject.timeout_add(600, self.parent.show_dock)
        if not windows:
            success = False
            if group.media_controls:
                success = group.media_controls.show_player()
            if not group.media_controls or not success:
                group.action_launch_application()
        if len(windows) == 1:
            windows[0].action_select_window()
