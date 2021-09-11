#!/usr/bin/python3

#   groupbutton.py
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
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GObject
from gi.repository import GLib
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck
from time import time
from time import sleep
import os
from gi.repository import Pango
from xml.sax.saxutils import escape
import weakref
import Xlib
import urllib.parse

from .windowbutton import Window
from .iconfactory import IconFactory
from .cairowidgets import CairoMenuItem, CairoCheckMenuItem
from .cairowidgets import CairoPopup, CairoToggleMenu, CairoAppButton
from .unity import DBusMenu
from .common import *
from . import zg
from .log import logger

from . import i18n
_ = i18n.language.gettext

X = None

try:
    WNCK_WINDOW_ACTION_MAXIMIZE = Wnck.WindowActions.MAXIMIZE
except:
    WNCK_WINDOW_ACTION_MAXIMIZE = 1 << 14


class GroupIdentifierError(Exception):
    pass

class ListOfWindows(list):
    def __init__(self, _list=[]):
        list.__init__(self)
        self.extend(_list)

    def __contains__(self, item):
        if isinstance(item, Wnck.Window):
            return item in [window.wnck for window in self]
        else:
            return list.__contains__(self, item)

    def __getitem__(self, item):
        if isinstance(item, Wnck.Window):
            for window in self:
                if window == item:
                    return window
            else:
                raise KeyError
        else:
            return list.__getitem__(self, item)

    def get (self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default


    #### Get windows
    def get_windows(self):
        # Returns a list of windows that are in current use
        windows = []
        for window in self:
            if self.globals.settings["show_only_current_desktop"] and \
               not window.is_on_current_desktop():
                continue
            if self.globals.settings["show_only_current_monitor"] and \
               not window.is_on_monitor(self.get_monitor()):
                continue
            windows.append(window)
        return ListOfWindows(windows)

    def get_unminimized_windows(self):
        windows = [w for w in self.get_windows() if not w.wnck.is_minimized()]
        return ListOfWindows(windows)

    def get_minimized_windows(self):
        windows = [w for w in self.get_windows() if w.wnck.is_minimized()]
        return ListOfWindows(windows)

    def get_count(self):
        return len(self.get_windows())

    def get_minimized_count(self):
        return len(self.get_minimized_windows())

    def get_unminimized_count(self):
        return len(self.get_unminimized_windows())



class Group(ListOfWindows):
    """A group contains all windows of the group, the button and popup window.

    The group controls all aspects of an application and and it's window.
    It contains to the windows of the group, the panel button,
    the popup window, the window list and other stuff."""

    def __init__(self, dockbar, identifier=None, desktop_entry=None,
                 pinned=False, size=None):
        ListOfWindows.__init__(self)
        self.dockbar_r = weakref.ref(dockbar)
        self.globals = Globals()
        self.globals_event = self.globals.connect("show-only-current-desktop-changed",
                                                  self.__on_show_only_current_desktop_changed)
        self.opacify_obj = Opacify()
        self.pinned = pinned
        self.desktop_entry = desktop_entry
        self.identifier = identifier
        if not identifier and desktop_entry is None:
            raise GroupIdentifierError(
                "Can't initiate Group button without identifier or launcher.")


        # Variables
        self.has_active_window = False
        self.needs_attention = False
        self.nextlist = None
        self.nextlist_time = 0
        self.lastlaunch_time = 0
        self.opacified = False
        self.opacify_sid = None
        self.deopacify_sid = None
        self.menu_is_shown = False
        self.menu = None
        self.media_controls = None
        self.launch_menu = None
        self.launch_timer_sid = None
        self.scrollpeak_sid = None
        self.scrollpeak_window = None
        self.quicklist = None
        self.unity_launcher_bus_name = None
        self.unity_urgent = False
        self.dm_attention = False
        self.zg_files = {}

        self.screen = Wnck.Screen.get_default()
        self.root_xid = int(Gdk.Screen.get_default().get_root_window().get_xid())
        self.update_name()

        self.monitor = self.get_monitor()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = self.monitor.get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(self.monitor)
        self.monitor_aspect_ratio = float(mgeo.width) / mgeo.height


        self.button = GroupButton(self, size)
        self.popup = GroupPopup(self)
        self.window_list = WindowList(self)
        self.popup.set_child_(self.window_list)
        self.locked_popup = None


    def __eq__(self, item):
        # __eq__ needs to be defined since a group doesn't equal another
        # group just because both groups has no windows ([]==[]).
        return self is item

    def __ne__(self, item):
        return self is not item

    def destroy(self):
        # Remove group button.
        self.remove_media_controls()
        self.remove_launch_timer()
        if self.quicklist:
            self.quicklist.destroy()
            self.quicklist = None
        if self.scrollpeak_sid is not None:
            GLib.source_remove(self.scrollpeak_sid)
        if self.deopacify_sid is not None:
            self.deopacify()
            GLib.source_remove(self.deopacify_sid)
            self.opacify_sid = None
        if self.opacify_sid is not None:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None
        if self.launch_menu:
            self.launch_menu.destroy()
        if self.locked_popup:
            self.locked_popup.destroy()
        if self.popup:
            disconnect(self.popup)
            self.popup.destroy()
        if self.button:
            disconnect(self.button)
            self.button.destroy()
        if self.menu:
            disconnect(self.menu)
        if self.window_list:
            self.window_list.destroy()
        self.globals.disconnect(self.globals_event)

    def get_monitor(self):
        window = self.dockbar_r().groups.box.get_window()
        gdk_screen = Gdk.Screen.get_default()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            display = gdk_screen.get_display();
            if window is not None:
                return display.get_monitor_at_window(window)
            else:
                return display.get_primary_monitor()
        else:
            if window is not None:
                return gdk_screen.get_monitor_at_window(window)
            else:
                return 0

    def get_app_uri(self):
        if self.desktop_entry is not None:
            name = self.desktop_entry.getFileName().rsplit('/')[-1]
            return "application://%s" % name

    def desktop_changed(self):
        self.button.update_state()
        self.button.set_icongeo()
        self.nextlist = None
        for window in self:
            window.desktop_changed()

        # hide after the possible enter-notify-event
        GLib.timeout_add(10, self.popup.hide)
        if self.button.is_visible():
            GLib.timeout_add(self.globals.settings["popup_delay"] + 20,
                    lambda: self.button.pointer_is_inside() and self.popup.show())

        if self.locked_popup:
            self.locked_popup.get_child_().show_all()
            self.locked_popup.resize(10, 10)
            if self.get_windows():
                self.locked_popup.show()
            else:
                self.locked_popup.hide()

    def update_name(self):
        self.name = None
        if self.desktop_entry:
            try:
                self.name = self.desktop_entry.getName()
            except:
                pass
        if (self.name is None or self.name == "") and len(self) > 0:
            # Uses first half of the name,
            # like "Amarok" from "Amarok - [SONGNAME]"
            # A program that uses a name like "[DOCUMENT] - [APPNAME]" would be
            # totally screwed up. So far no such program has been reported.
            self.name = self[0].wnck.get_class_group().get_name()
            self.name = self.name.split(" - ", 1)[0]
        if not self.name and self.identifier:
            self.name = self.identifier
        if self.name is None:
            return
        try:
            self.button.update_tooltip()
            self.popup.update_title()
        except AttributeError:
            pass

    def set_identifier(self, identifier):
        if not identifier:
            raise GroupIdentifierError(
                "Can't change identifier %s to \"%s\"." % (self.identifier,
                                                           identifier))
        if self.identifier == get_opacifier():
            set_opacifier(identifier)
        self.identifier = identifier
        self.window_list.update_title_tooltip()

    def set_desktop_entry(self, desktop_entry):
        self.desktop_entry = desktop_entry
        self.update_name()
        self.button.icon_factory.set_desktop_entry(desktop_entry)
        self.button.icon_factory.reset_surfaces()
        self.button.update_state()

    def launch(self, button=None, event=None, uri=None, delay=0):
        if delay:
            self.launch_timer_sid = GLib.timeout_add(delay, self.launch,
                                                        button, event, uri)
            return False
        self.desktop_entry.launch(uri)
        self.button.apply_launch_effect()

    def remove_launch_timer(self):
        if self.launch_timer_sid:
            GLib.source_remove(self.launch_timer_sid)
            self.launch_timer_sid = None

    def __on_show_only_current_desktop_changed(self, arg):
        self.button.update_state()
        self.nextlist = None
        self.button.set_icongeo()
        if self.locked_popup:
            self.locked_popup.get_child_().show_all()
            self.locked_popup.resize(10, 10)
            self.locked_popup.show()


    def show_launch_popup(self):
        self.menu_is_shown = False
        #Launch program item
        if not self.launch_menu:
            self.launch_menu = Gtk.Box.new(Gtk.Orientation.VERTICAL, 2)
            launch_program_item = CairoMenuItem(_("_Launch application"))
            launch_program_item.connect("clicked",
                                self.action_launch_application)
            self.launch_menu.pack_start(launch_program_item, True, True, 0)
            self.launch_menu.can_be_shown = lambda : True
        self.popup.set_child_(self.launch_menu)
        self.popup.show()

    def add_locked_popup(self):
        if self.locked_popup:
            return
        self.popup.hide()
        locked_popup = self.globals.get_locked_popup()
        if locked_popup:
            locked_popup.destroy()
        self.locked_popup = LockedPopup(self)
        self.globals.set_locked_popup(self.locked_popup)
        self.locked_popup.show()

    def remove_locked_popup(self):
        if self.locked_popup:
            self.locked_popup.destroy()
            self.popup.hide()
            self.locked_popup = None

    #### Window handling
    def add_window(self, wnck_window):
        if wnck_window in self:
            return
        window = Window(wnck_window, self)
        self.append(window)
        self.window_list.add_item(window.item)
        if len(self)==1:
            if self.name is None:
                self.update_name()
            class_group = window.wnck.get_class_group()
            self.button.icon_factory.set_class_group(class_group)
            class_group.connect("icon-changed", self.group_icon_changed)
        if self.button.launch_effect:
            self.button.remove_launch_effect()
        if window.needs_attention:
            self.needs_attention_changed(state_update=False)

        # Update state unless the button hasn't been shown yet.
        self.button.update_state_if_shown()

        if (self.globals.settings["show_only_current_desktop"] and \
           not window.is_on_current_desktop()) and \
           (self.globals.settings["show_only_current_monitor"] and \
           not window.is_on_monitor(self.get_monitor())):
            window.item.hide()
        else:
            window.item.show()

        self.button.update_tooltip()

        if self.globals.settings["preview"] and self.globals.settings["preview_keep"]:
            window.update_preview_later()

        # Set minimize animation
        # (if the eventbox is created already,
        # otherwise the icon animation is set in sizealloc())
        self.button.set_icongeo(window)
        self.remove_launch_timer()

    def del_window(self, wnck_window):
        window = self[wnck_window]
        if window == self.scrollpeak_window:
            self.scrollpeak_abort()
        self.remove(window)
        if self.nextlist and window in self.nextlist:
            self.nextlist.remove(window)
        window.destroy()
        if self.needs_attention:
            self.needs_attention_changed(state_update=False)
        if self.pinned or len(self):
            self.window_list.set_show_previews(
                                            self.globals.settings["preview"])
            self.button.update_state_if_shown()
            self.button.update_tooltip()
        if self.get_unminimized_count() == 0:
            if self.opacified:
                self.deopacify()
        if self.popup.popup_showing:
            if self.get_count() > 0 or self.media_controls:
                self.popup.resize(10, 10)
            else:
                self.popup.hide()
        if self.locked_popup:
            if self.get_count() >= 1:
                self.locked_popup.resize(10, 10)
            else:
                self.locked_popup.destroy()

    def set_active_window(self, wnck_window=None):
        has_active = False
        for window in self:
            if window == wnck_window:
                window.set_active(True)
                has_active = True
                if self.globals.settings["reorder_window_list"]:
                    self.remove(window)
                    self.insert(0, window)
                    self.window_list.reorder_item(0, window.item)
            else:
                window.set_active(False)
        if has_active != self.has_active_window:
            self.has_active_window = has_active
            self.button.update_state_if_shown()

    def update_window_previews(self):
        for window in self.get_windows():
            if window.item.get_visible():
                window.update_preview_later()

    def needs_attention_changed(self, arg=None, state_update=True):
        # Checks if there are any urgent windows and changes
        # the group button looks if there are at least one
        if self.unity_urgent or self.dm_attention:
            self.needs_attention = True
        else:
            for window in self:
                if window.wnck.needs_attention():
                    self.needs_attention = True
                    break
            else:
                self.needs_attention = False
        if state_update:
            self.button.update_state_if_shown()

    def window_monitor_changed(self):
        self.button.update_state()
        self.button.set_icongeo()

    def window_desktop_changed(self):
        self.button.update_state()
        self.nextlist = None
        self.button.set_icongeo()
        if self.locked_popup:
            self.locked_popup.get_child_().show_all()
            self.locked_popup.resize(10, 10)
            self.locked_popup.show()

    def group_icon_changed(self, class_group):
        if self.button.icon_factory is None:
            return
        self.button.icon_factory.reset_icon()
        self.button.icon_factory.reset_surfaces()
        self.button.update_state(force_update=True)
        self.button.drag_source_set_icon_pixbuf(self.button.icon_factory.get_icon(32))


    #### Opacify
    def opacify(self, delay=0):
        if delay:
            if not self.opacify_sid:
                # Todo: Would it be better to remove previous delays if
                # a delay already is set?
                self.opacify_sid = GLib.timeout_add(delay, self.opacify)
            return
        xids = [window.wnck.get_xid() for window in self]
        opacify(xids, self.identifier)
        self.opacified = True
        self.opacify_sid = None

    def deopacify(self, delay=0):
        if delay:
            if not self.deopacify_sid:
                # Todo: Would it be better to remove previous delays if
                # a delay already is set?
                self.deopacify_sid = GLib.timeout_add(delay, self.deopacify)
            return
        if self.button.opacify_sid is not None:
            GLib.source_remove(self.button.opacify_sid)
            self.button.opacify_sid = None
        self.cancel_opacify_request()
        deopacify(self.identifier)

    def cancel_opacify_request(self):
        if self.opacify_sid:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None

    def cancel_deopacify_request(self):
        if self.deopacify_sid:
            GLib.source_remove(self.deopacify_sid)
            self.deopacify_sid = None


    #### Media Controls
    def add_media_controls(self, media_controls):
        if self.media_controls:
            self.remove_media_controls()
        self.media_controls = media_controls
        self.window_list.add_plugin(self.media_controls)
        self.button.update_tooltip()

    def remove_media_controls(self):
        if self.media_controls:
            self.window_list.remove_plugin(self.media_controls)
            self.media_controls = None
            self.button.update_tooltip()
            if self.popup.popup_showing:
                if self.get_count() == 0:
                    self.popup.hide()

    def get_desktop_entry_file_name(self):
        if self.desktop_entry:
            file_name = self.desktop_entry.getFileName()
        else:
            file_name = ''
        return file_name

    def set_unity_properties(self, properties, sender):
        self.unity_launcher_bus_name = sender
        if properties.get("count-visible", False):
            count = properties.get("count")
            if count is not None:
                self.button.set_badge(str(count), backend="unity")
        else:
            self.button.set_badge(None, backend="unity")
        if properties.get("progress-visible", False):
            progress = properties.get("progress")
            if progress is not None:
                self.button.set_progress_bar(progress, backend="unity")
        else:
            self.button.set_progress_bar(None, backend="unity")
        self.unity_urgent = properties.get("urgent", False)
        if self.needs_attention != self.unity_urgent:
            self.needs_attention_changed()
        path = properties.get("quicklist")
        if path and self.quicklist and sender == self.quicklist.bus_name and \
           path == self.quicklist.path:
                return
        elif not path and self.quicklist:
            self.quicklist.destroy()
            self.quicklist = None
            if self.menu:
                self.menu.remove_quicklist()
        elif path:
            if self.quicklist:
                self.quicklist.destroy()
            self.quicklist = DBusMenu(self, sender, path)

    #### Menu
    def menu_show(self, event=None):
        if self.globals.gtkmenu:
            return
        if self.menu is not None:
            self.menu.delete_menu()
            self.menu = None
        if self.menu_is_shown and not self.globals.settings["old_menu"]:
            # The menu is already shown, show the window list instead.
            self.menu_is_shown = False
            if self.locked_popup:
                self.popup.hide()
            else:
                self.popup.set_child_(self.window_list)
            return
        if self.globals.settings["old_menu"]:
            self.popup.hide()
        else:
            self.menu_is_shown = True
        self.menu = self.__menu_build()

        connect(self.menu, "item-activated", self.__on_menuitem_activated)
        connect(self.menu, "item-hovered", self.__on_menuitem_hovered)
        connect(self.menu, "menu-resized", self.__on_menu_resized)
        if self.globals.settings["old_menu"]:
            menu = self.menu.get_menu()
            menu.popup(None, None, None,
                       self.__menu_position, event.button, event.time)
            self.globals.gtkmenu = menu
            # TODO: check is this connection destroyed when done?
            menu.connect("selection-done", self.__menu_closed)
        else:
            self.popup.set_child_(self.menu.get_menu())
            self.popup.show(force=True)

    def __menu_build(self):
        win_nr = self.get_count()
        if self.locked_popup or \
           (win_nr > 1 and self.globals.settings["locked_list_in_menu"]):
            use_locked_popup = True
        else:
            use_locked_popup = False
        for window in self:
            if not window.wnck.is_maximized() \
            and window.wnck.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
                maximize = True
                break
        else:
            maximize = False
        minimize = self.get_unminimized_count() > 0

        menu = GroupMenu(self.globals.settings["old_menu"])
        menu.build_group_menu(self.desktop_entry, \
                              self.quicklist, self.pinned, self.locked_popup, \
                              use_locked_popup, win_nr, minimize, maximize)

        if zg.is_available():
            self.__menu_get_zg_files()
        return menu

    def __menu_get_zg_files(self):
        # Get information from zeitgeist
        self.zg_most_used_files = None
        self.zg_recent_files = None
        self.zg_related_files = None
        self.zg_recent_today_files = None
        if self.desktop_entry is None:
            return
        appname = self.desktop_entry.getFileName().split("/")[-1]
        try:
            zg.get_recent_for_app(appname, days=30,
                                  number_of_results=8,
                                  handler=self.__menu_recent_handler)
        except:
            logger.exception("Couldn't get zeitgeist recent files for %s" % \
                             self.name)
        try:
            zg.get_most_used_for_app(appname,
                                     days=30,
                                     number_of_results=8,
                                     handler=self.__menu_most_used_handler)
        except:
            logger.exception("Couldn't get zeitgeist most used files" +
                             " for %s" % self.name)
        # Related files contains files that can be used by the program and
        # has been used by other programs (but not this program) today.
        try:
            mimetypes = self.desktop_entry.getMimeTypes()
        except AttributeError:
            mimetypes = None
        if mimetypes:
            try:
                zg.get_recent_for_mimetypes(mimetypes,
                                        days=1,
                                        number_of_results=20,
                                        handler=self.__menu_related_handler)
                zg.get_recent_for_app(appname,
                                    days=1,
                                    number_of_results=20,
                                    handler=self.__menu_recent_today_handler)
            except:
                logger.exception("Couldn't get zeitgeist related" + \
                                 " files for %s" % self.name)

    def __menu_recent_handler(self, source, result):
        self.zg_recent_files = zg.pythonify_zg_events(source, result)
        self.__menu_update_zg()

    def __menu_most_used_handler(self, source, result):
        self.zg_most_used_files = zg.pythonify_zg_events(source, result)
        self.__menu_update_zg()

    def __menu_related_handler(self, source, result):
        self.zg_related_files = zg.pythonify_zg_events(source, result)
        self.__menu_update_zg()

    def __menu_recent_today_handler(self, source, result):
        self.zg_recent_today_files = zg.pythonify_zg_events(source, result)
        self.__menu_update_zg()

    def __menu_update_zg(self):
        # Updates zeitgeist recent, most used and related menus when
        # all of them has been received.
        if self.zg_most_used_files is None or \
           self.zg_recent_files is None or \
           self.zg_related_files is None or \
           self.zg_recent_today_files is None:
               return
        related_files = [rf for rf in self.zg_related_files \
                         if not (rf in self.zg_recent_files or \
                         rf in self.zg_recent_today_files)]
        related_files = related_files[:3]
        self.zg_files = self.menu.populate_zg_menus(self.zg_recent_files,
                                                self.zg_most_used_files,
                                                related_files)
        self.zg_most_used_files = None
        self.zg_recent_files = None
        self.zg_related_files = None
        self.zg_recent_today_files = None

    def __on_menuitem_hovered(self, arg, t, identifier):
        if identifier.startswith("unity_") and self.quicklist:
            identifier = int(identifier.rsplit("_", 1)[-1])
            data = dbus.String("", variant_level=1)
            t = dbus.UInt32(t)
            self.quicklist.send_event(identifier, "hovered", data, t)
            return

    def __on_menuitem_activated(self, menu_item, identifier):
        if identifier.startswith("unity_") and self.quicklist:
            identifier = int(identifier.rsplit("_", 1)[-1])
            data = dbus.String("", variant_level=1)
            t = dbus.UInt32(0)
            self.quicklist.send_event(identifier, "clicked",
                                      data, t)
            return
        if identifier in self.zg_files:
            self.launch(None, None, self.zg_files[identifier])
            return
        if self.desktop_entry:
            quicklist = self.desktop_entry.get_quicklist()
        if identifier.startswith("quicklist_") and \
           quicklist.get(identifier[10:]) is not None:
            self.desktop_entry.launch_quicklist_entry(identifier[10:])
            return
        menu_funcs = \
            {_("_Close"): self.action_close_all_windows,
             _("_Close") + _(" all windows"): self.action_close_all_windows,
             _("Ma_ximize"): self.action_maximize_all_windows,
             _("Ma_ximize") + _(" all windows"):
                                        self.action_maximize_all_windows,
             _("Unma_ximize"): self.action_maximize_all_windows,
             _("Unma_ximize")+_(" all windows"):
                                        self.action_maximize_all_windows,
             _("_Minimize"): self.action_minimize_all_windows,
             _("_Minimize")+_(" all windows"):
                                        self.action_minimize_all_windows,
             _("Un_minimize"): self.__menu_unminimize_all_windows,
             _("Un_minimize")+_(" all windows"):
                                        self.__menu_unminimize_all_windows,
             _("Edit Launcher"): self.__menu_edit_launcher,
             _("Edit Identifier"): self.__menu_change_identifier,
             _("Unpin application"): self.action_remove_pinned_app,
             _("Make custom launcher"): self.__menu_edit_launcher,
             _("_Pin application"): self.__menu_pin,
             _("_Launch application"): self.action_launch_application,
             _("Floating Window Panel"): self.action_toggle_locked_list}
        func = menu_funcs.get(identifier, None)
        if func:
            func()

    def __on_menu_resized(self, *args):
        self.popup.resize(10,10)

    def __menu_position(self, menu):
        # Used only with the gtk menu
        dummy, x, y = self.button.get_window().get_origin()
        a = self.button.get_allocation()
        x += a.x
        y += a.y
        w, h = menu.size_request()
        if self.dockbar_r().orient in ("left", "right"):
            if x < (self.screen.get_width() // 2):
                x += a.width
            else:
                x -= w
            if y + h > self.screen.get_height():
                y -= h - a.height
        if self.dockbar_r().orient in ("down", "up"):
            if y < (self.screen.get_height() // 2):
                y += a.height
            else:
                y -= h
            if x + w >= self.screen.get_width():
                x -= w - a.width
        return (x, y, False)

    def __menu_closed(self, menushell=None):
        # Used only with the gtk menu
        if self.globals.gtkmenu:
            self.globals.gtkmenu = None
            self.menu.delete_menu()
            self.menu = None

    def __menu_unminimize_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = GdkX11.x11_get_server_time(Gdk.get_default_root_window())
        for window in self.get_minimized_windows():
            window.wnck.unminimize(t)
        self.popup.hide()

    def __menu_change_identifier(self, widget=None, event=None):
        self.popup.hide()
        self.dockbar_r().change_identifier(self.desktop_entry.getFileName(),
                                           self.identifier)
        if self.globals.gtkmenu:
            # the modal __identifier_dialog prevented us from receiving selection-done signal
            self.__menu_closed()

    def __menu_edit_launcher(self, widget=None, event=None):
        if self.desktop_entry:
            path = self.desktop_entry.getFileName()
        else:
            path = ""
        self.popup.hide()
        self.dockbar_r().edit_launcher(path, self.identifier)
        if self.globals.gtkmenu:
            # the modal DesktopFileEditor dialog prevented us from receiving selection-done signal
            self.__menu_closed()

    def __menu_pin(self, widget=None, event=None):
        self.pinned = True
        self.dockbar_r().update_pinned_apps_list()
        self.popup.hide()

    #### Actions
    def action_select(self, widget, event):
        wins = self.get_windows()
        if (self.pinned and not wins):
            #~ success = False
            #~ if self.media_controls:
                #~ success = self.media_controls.show_player()
            #~ if not self.media_controls or not success:
                #~ self.action_launch_application()
            self.action_launch_application()
        # One window
        elif len(wins) == 1:
            sow = self.globals.settings["select_one_window"]
            if sow == "select window":
                wins[0].action_select_window(widget, event)
            elif sow == "select or minimize window":
                wins[0].action_select_or_minimize_window(widget, event)
            self.popup.hide()
            self.deopacify()
        # Multiple windows
        elif len(wins) > 1:
            smw = self.globals.settings["select_multiple_windows"]
            if smw == "select all":
                self.action_select_or_minimize_group(widget, event,
                                                     minimize=False)
            elif smw == "select or minimize all":
                self.action_select_or_minimize_group(widget, event,
                                                     minimize=True)
            elif smw == "compiz scale":
                umw = self.get_unminimized_windows()
                if len(umw) == 1:
                    sow = self.globals.settings["select_one_window"]
                    if sow == "select window":
                        umw[0].action_select_window(widget, event)
                        self.popup.hide()
                        self.deopacify()
                    elif sow == "select or minimize window":
                        umw[0].action_select_or_minimize_window(widget, event)
                        self.popup.hide()
                        self.deopacify()
                elif len(umw) == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif smw == "cycle through windows":
                self.action_select_next(widget, event)
            elif smw == "show popup":
                self.action_select_popup(widget, event)

    def action_select_popup(self, widget, event):
        if self.popup.popup_showing is True:
            self.popup.hide()
        else:
            self.popup.show()

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if self.globals.settings["show_only_current_desktop"]:
            mode = "ignore"
        else:
            mode = self.globals.settings["workspace_behavior"]
        screen = self.screen
        windows_stacked = screen.get_windows_stacked()
        grp_win_stacked = []
        ignorelist = []
        minimized_windows = self.get_minimized_windows()
        moved = False
        grtop = False
        wingr = False
        active_workspace = screen.get_active_workspace()
        self.popup.hide()
        self.deopacify()

        # Check if there are any uminimized windows, unminimize
        # them (unless they are on another workspace and work-
        # space behavior is something other than move) and
        # return.
        if self.get_unminimized_count() == 0:
            # Only unminimize if all windows are minimize
            unminimized = False
            for window in minimized_windows:
                ignored = False
                # Check if the window is on another workspace
                if not window.wnck.is_pinned() \
                and window.wnck.get_workspace() is not None \
                and window.wnck.get_workspace() != active_workspace:
                    if mode == "move":
                        ws = screen.get_active_workspace()
                        window.wnck.move_to_workspace(ws)
                    else: # mode == "ignore" or "switch"
                        ignored = True
                # Check if the window is on another viewport
                if not window.wnck.is_in_viewport(active_workspace):
                    if mode == "move":
                        wx, wy, ww, wh = window.wnck.get_geometry()
                        window.wnck.set_geometry(0,3,
                                         wx%screen.get_width(),
                                         wy%screen.get_height(),
                                         ww, wh)
                    else: # mode == "ignore" or "switch"
                        ignored = True
                if not ignored:
                    window.wnck.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return

        # Make a list of the windows in group with the bottom most
        # first and top most last.
        # If mode is other than "move"
        # windows on other workspaces is put in a separate list instead.
        # grtop is set to true if not all windows in the group is the
        # topmost windows.
        for wnck_window in windows_stacked:
            if wnck_window.is_skip_tasklist() or \
               wnck_window.is_minimized() or \
               not (wnck_window.get_window_type() in [Wnck.WindowType.NORMAL, Wnck.WindowType.DIALOG]):
                continue
            if not wnck_window in self:
                if wingr:
                    grtop = False
                continue
            ignored = False
            if not wnck_window.is_pinned() \
            and wnck_window.get_workspace() is not None \
            and active_workspace != wnck_window.get_workspace():
                if mode == "move":
                    ws = screen.get_active_workspace()
                    wnck_window.move_to_workspace(ws)
                    moved = True
                else: # mode == "ignore" or "switch"
                    ignored = True
                    ignorelist.append(self[wnck_window])
            if not wnck_window.is_in_viewport(screen.get_active_workspace()):
                if mode == "move":
                    wx, wy, ww, wh = wnck_window.get_geometry()
                    wnck_window.set_geometry(0,3,wx%screen.get_width(),
                                     wy%screen.get_height(),
                                     ww,wh)
                    moved = True
                else: # mode == "ignore" or "switch"
                    ignored = True
                    ignorelist.append(self[wnck_window])

            if not ignored:
                grp_win_stacked.append(self[wnck_window])
                if wingr == False:
                    wingr = True
                    grtop = True

        if not grp_win_stacked and mode == "switch":
            # Put the windows in dictionaries according to workspace and
            # viewport so we can compare which workspace and viewport that
            # has most windows.
            workspaces ={}
            for window in self:
                if window.wnck.get_workspace() is None:
                    continue
                workspace = window.wnck.get_workspace()
                wx,wy,ww,wh = window.wnck.get_geometry()
                vpx = wx//screen.get_width()
                vpy = wy//screen.get_height()
                if not workspace in workspaces:
                    workspaces[workspace] = {}
                if not vpx in workspaces[workspace]:
                    workspaces[workspace][vpx] = {}
                if not vpy in workspaces[workspace][vpx]:
                    workspaces[workspace][vpx][vpy] = []
                workspaces[workspace][vpx][vpy].append(window)
            max = 0
            x = 0
            y = 0
            new_workspace = None
            # Compare which workspace and viewport that has most windows.
            ignorelist.reverse() # Topmost window first.
            for workspace in workspaces:
                for xvp in workspaces[workspace]:
                    for yvp in workspaces[workspace][xvp]:
                        vp = workspaces[workspace][xvp][yvp]
                        nr = len(vp)
                        if nr > max:
                            max = nr
                            x = screen.get_width() * xvp
                            y = screen.get_height() * yvp
                            new_workspace = workspace
                            grp_win_stacked = vp
                        elif nr == max:
                            # Check whether this workspace or previous workspace
                            # with the same amount of windows has been
                            # activated later.
                            for win in ignorelist:
                                if win in grp_win_stacked:
                                    break
                                if win in vp:
                                    x = screen.get_width() * xvp
                                    y = screen.get_height() * yvp
                                    new_workspace = workspace
                                    grp_win_stacked = vp
                                    break
            if new_workspace != screen.get_active_workspace():
                new_workspace.activate(event.time)
            screen.move_viewport(x, y)
            # Hide popup since mouse movement won't
            # be tracked during compiz move effect
            if not (x == 0 and y == 0):
                self.popup.hide()
            unminimized = False
            for window in grp_win_stacked:
                if window.wnck.is_minimized():
                    window.wnck.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            #Bottommost window fist again.
            ignorelist.reverse()
            grp_win_stacked = [w for w in ignorelist if w in grp_win_stacked]

        # Minimize all windows if the top most window belongs to the
        # application and no windows has been moved to a different
        # workspace and minimizing is allowed.
        if grtop and not moved and minimize:
            for window in grp_win_stacked:
                window.wnck.minimize()
        # If the topmost window doesn't belong to the application,
        # raise all windows.
        elif not grtop:
            delay = self.globals.settings["delay_on_select_all"]
            while grp_win_stacked:
                grp_win_stacked.pop(0).wnck.activate(event.time)
                if grp_win_stacked and delay:
                    sleep(0.05)


    def action_select_only(self, widget, event):
        self.action_select_or_minimize_group(widget, event, False)

    def action_select_or_compiz_scale(self, widget, event):
        windows = self.get_unminimized_windows()
        if  len(windows) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif len(windows) == 1:
            windows[0].action_select_window(widget, event)
        self.popup.hide()
        self.deopacify()

    def action_minimize_all_windows(self, widget=None, event=None):
        for window in self.get_windows():
            window.wnck.minimize()
        self.popup.hide()
        self.deopacify()

    def action_maximize_all_windows(self, widget=None, event=None):
        maximized = False
        for window in self.get_windows():
            if not window.wnck.is_maximized() \
            and window.wnck.get_actions() & WNCK_WINDOW_ACTION_MAXIMIZE:
                window.wnck.maximize()
                maximized = True
        if not maximized:
            for window in self:
                window.wnck.unmaximize()
        self.popup.hide()
        self.deopacify()

    def action_select_next(self, widget=None, event=None, previous=False,
                           keyboard_select=False):
        if not self.get_windows():
            return
        if time() - self.nextlist_time > 1.5 or \
           self.nextlist is None:
            # Make the list and pick the window.
            windows_stacked = self.screen.get_windows_stacked()
            windows = self.get_windows()
            snula = self.globals.settings["select_next_use_lastest_active"]
            rwl = self.globals.settings["reorder_window_list"]
            if snula and not rwl:
                self.nextlist = []
                minimized_list = []
                for window in windows_stacked:
                        if window in windows:
                            if window.is_minimized():
                                minimized_list.append(self[window])
                            else:
                                self.nextlist.append(self[window])
                # Reverse -> topmost window first
                self.nextlist.reverse()
                # Add minimized windows last.
                self.nextlist.extend(minimized_list)
            else:
                topwindow = None
                for i in range(1, len(windows_stacked)+1):
                        if windows_stacked[-i] in windows and \
                           not windows_stacked[-i].is_minimized():
                            topwindow = self[windows_stacked[-i]]
                            break
                self.nextlist = windows
                if topwindow:
                    while self.nextlist[0] != topwindow:
                        window = self.nextlist.pop(0)
                        self.nextlist.append(window)
            if self.nextlist[0].wnck.is_active():
                if previous:
                    window = self.nextlist.pop(-1)
                    self.nextlist.insert(0, window)
                else:
                    window = self.nextlist.pop(0)
                    self.nextlist.append(window)
        else:
            # Iterate the list.
            if previous:
                window = self.nextlist.pop(-1)
                self.nextlist.insert(0, window)
            else:
                window = self.nextlist.pop(0)
                self.nextlist.append(window)
        window = self.nextlist[0]
        self.nextlist_time = time()
        # Just a safety check
        if not window in self:
            return

        self.popup.show()
        if self.globals.settings["select_next_activate_immediately"] and \
           not self.globals.settings["reorder_window_list"]:
            window.action_select_window(widget, event)
        else:
            if self.scrollpeak_window:
                self.scrollpeak_window.item.set_highlighted(False)
            self.scrollpeak_window = window
            self.scrollpeak_window.item.set_highlighted(True)
            if self.scrollpeak_sid is not None:
                GLib.source_remove(self.scrollpeak_sid)
            if not keyboard_select:
                self.scrollpeak_sid = GLib.timeout_add(1500, self.scrollpeak_select)
            ctx = GLib.MainContext.default()
            while ctx.pending():
                ctx.iteration(False)
            if self.scrollpeak_window: #TODO: find out why scollpeak_window is None sometimes.
                self.scrollpeak_window.opacify()

    def action_select_previous(self, widget=None, event=None):
        self.action_select_next(widget, event, previous=True)

    def action_select_next_with_popup(self, widget=None,
                                      event=None, previous=False):
        self.popup.show()
        self.action_select_next(widget, event, previous)
        self.popup.hide_if_not_hovered(1500)

    def scrollpeak_select(self):
        if self.scrollpeak_window:
            self.scrollpeak_window.action_select_window()
        self.scrollpeak_abort()

    def scrollpeak_abort(self):
        if self.scrollpeak_window:
            self.scrollpeak_window.item.set_highlighted(False)
            self.scrollpeak_window.deopacify()
            self.scrollpeak_window = None
        if self.scrollpeak_sid:
            GLib.source_remove(self.scrollpeak_sid)
            self.scrollpeak_sid = None
        self.remove_launch_timer()
        self.popup.hide()

    def action_close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = 1
        for window in self.get_windows():
            window.wnck.close(t)
        self.popup.hide()
        self.deopacify()

    def action_launch_application(self, widget=None, event=None):
        if time() - self.lastlaunch_time < 2:
                return
        if self.desktop_entry:
            self.desktop_entry.launch()
        else:
            return
        self.lastlaunch_time = time()
        self.button.apply_launch_effect()
        self.button.update_state()
        self.popup.hide()
        self.deopacify()
        self.remove_launch_timer()

    def action_show_menu(self, widget, event):
        self.menu_show(event)

    def action_remove_pinned_app(self, widget=None, event=None):
        logger.debug("Removing launcher: %s" % self.identifier)
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        self.pinned = False
        if not len(self):
            self.dockbar_r().remove_groupbutton(self)
        else:
            self.dockbar_r().group_unpinned(name)
        self.popup.hide()
        self.deopacify()

    def action_minimize_all_other_groups(self, widget, event):
        self.popup.hide()
        self.dockbar_r().minimize_other_groups(self)
        self.popup.hide()
        self.deopacify()

    def action_compiz_scale_windows(self, widget, event):
        windows = self.get_unminimized_windows()

        if not windows:
            return
        self.popup.hide()
        if len(windows) == 1:
            self[0].action_select_window(widget, event)
            return

        if self.globals.get_compiz_version() >= '0.9.4':
            screen_path = 'screen0'
        else:
            screen_path = 'allscreens'

        if self.globals.settings["show_only_current_desktop"]:
            path = "scale/%s/initiate_key"%screen_path
        else:
            path = "scale/%s/initiate_all_key"%screen_path
        try:
            compiz_call_async(path, "activate","root", self.root_xid,"match", \
                "iclass=%s"%windows[0].wnck.get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefore needed.
        GLib.timeout_add(self.globals.settings["popup_delay"] + 200,
                            self.popup.hide)
        #~ self.deopacify()

    def action_compiz_shift_windows(self, widget, event):
        windows = self.get_unminimized_windows()
        if not windows:
            return
        self.popup.hide()
        if len(windows) == 1:
            self[0].action_select_window(widget, event)
            return

        if self.globals.get_compiz_version() >= '0.9.4':
            screen_path = 'screen0'
        else:
            screen_path = 'allscreens'

        if self.globals.settings["show_only_current_desktop"]:
            path = "shift/%s/initiate_key"%screen_path
        else:
            path = "shift/%s/initiate_all_key"%screen_path
        try:
            compiz_call_async(path, "activate","root", self.root_xid,"match", \
                "iclass=%s"%windows[0].wnck.get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefore needed.
        GLib.timeout_add(self.globals.settings["popup_delay"]+ 200,
                            self.popup.hide)
        #~ self.deopacify()

    def action_compiz_scale_all(self, widget, event):
        if self.globals.get_compiz_version() >= '0.9.4':
            screen_path = 'screen0'
        else:
            screen_path = 'allscreens'

        try:
            compiz_call_async("scale/%s/initiate_key"%screen_path, "activate",
                        "root", self.root_xid)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefore needed.
        GLib.timeout_add(self.globals.settings["popup_delay"]+ 200,
                            self.popup.hide)
        self.popup.hide()
        self.deopacify()

    def action_toggle_locked_list(self, widget=None, event=None):
        if self.locked_popup:
            self.remove_locked_popup()
        else:
            self.add_locked_popup()

    def action_dbpref(self,widget=None, event=None):
        # Preferences dialog
        self.dockbar_r().open_preference()
        self.popup.hide()
        self.deopacify()

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = \
            ODict((
            ("select", action_select),
            ("close all windows", action_close_all_windows),
            ("minimize all windows", action_minimize_all_windows),
            ("maximize all windows", action_maximize_all_windows),
            ("launch application", action_launch_application),
            ("show menu", action_show_menu),
            ("remove launcher", action_remove_pinned_app),
            ("select next window", action_select_next),
            ("select previous window", action_select_previous),
            ("minimize all other groups", action_minimize_all_other_groups),
            ("compiz scale windows", action_compiz_scale_windows),
            ("compiz shift windows", action_compiz_shift_windows),
            ("compiz scale all", action_compiz_scale_all),
            ("show preference dialog", action_dbpref),
            ("no action", action_none)
            ))

class GroupButton(CairoAppButton):
    """
    Group button takes care of a program's "button" in dockbar.

    It also takes care of the popup window and all the window buttons that
    populates it.
    """

    def __init__(self, group, size):
        CairoAppButton.__init__(self, None)
        self.dockbar_r = weakref.ref(group.dockbar_r())
        self.group_r = weakref.ref(group)
        self.mouse_over = False
        self.pressed = False
        self.attention_effect_running = False
        self.launch_effect = False
        self.state_type = None
        self.badge_backend = None
        self.progress_backend = None
        self.icon_factory = IconFactory(group,
                                        identifier=group.identifier,
                                        desktop_entry=group.desktop_entry,
                                        size=size)
        self.old_alloc = self.get_allocation()

        # The icon size is decided from allocation or manually.
        self.manual_size = size is not None

        self.opacify_sid = None
        self.deopacify_sid = None
        self.launch_effect_sid = None
        self.leave_notify_sid = None


        self.globals_event = self.globals.connect("show-tooltip-changed",
                self.update_tooltip)

        #--- D'n'D
        # Drag and drop should handle buttons that are moved,
        # launchers that is dropped, and open popup window
        # to enable drag and drops to windows that has to be
        # raised.
        self.drag_dest_set(0, [], 0)
        self.drag_entered = False
        self.dnd_has_launcher = False
        self.dnd_on_drop = False
        self.dnd_position = "end"
        self.dnd_show_popup = None

        #Make buttons drag-able
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,[], Gdk.DragAction.MOVE)
        targets = Gtk.TargetList.new([])
        target_atom = Gdk.Atom.intern("text/groupbutton_name", False)
        targets.add(target_atom, Gtk.TargetFlags.SAME_APP, 47593)
        self.drag_source_set_target_list(targets)
        self.drag_source_set_icon_pixbuf(self.icon_factory.get_icon(32))
        #~ self.drag_source_add_text_targets()
        self.is_current_drag_source = False

        # Make scroll events work.
        self.add_events(Gdk.EventMask.SCROLL_MASK)
        
        self.connect("enter-notify-event", self.on_enter_notify_event)
        self.connect("leave-notify-event", self.on_leave_notify_event)
        self.connect("button-release-event", self.on_button_release_event)
        self.connect("button-press-event", self.on_button_press_event)
        self.connect("scroll-event", self.on_scroll_event)
        self.connect("size-allocate", self.on_size_allocate)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-leave", self.on_drag_leave)
        self.connect("drag-drop", self.on_drag_drop)
        self.connect("drag-data-received", self.on_drag_data_received)
        self.connect("drag-begin", self.on_drag_begin)
        self.connect("drag-data-get", self.on_drag_data_get)
        self.connect("drag-end", self.on_drag_end)

    def dockbar_moved(self, arg=None):
        self.set_icongeo()
        self.__reset_locked_popup_position()

    def destroy(self, *args, **kwargs):
        # Remove group button.
        if self.deopacify_sid is not None:
            self.deopacify()
            GLib.source_remove(self.deopacify_sid)
            self.deopacify_sid = None
        if self.opacify_sid is not None:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None
        if self.leave_notify_sid is not None:
            GLib.source_remove(self.leave_notify_sid)
            self.leave_notify_sid = None
        if self.icon_factory:
            self.icon_factory.remove()
            self.icon_factory = None
        self.globals.disconnect(self.globals_event)
        self.remove_launch_effect()
        CairoAppButton.destroy(self, *args, **kwargs)

    #### State
    def update_state(self, force_update=False):
        # Checks button state and set the icon accordingly.
        group = self.group_r()
        window_count = min(group.get_count(), 15)
        if window_count == 0 and not group.pinned:
            # Hide the button if no windows are on the current screen.
            self.hide()
            return
        else:
            # This is necessary if desktop changed.
            self.show()


        state_type = 0
        mwc = group.get_minimized_count()
        if group.pinned and window_count == 0:
            state_type = state_type | IconFactory.LAUNCHER
        elif (window_count - mwc) <= 0:
            state_type = state_type | IconFactory.ALL_MINIMIZED
        elif mwc > 0:
            state_type = state_type | IconFactory.SOME_MINIMIZED

        if group.has_active_window and window_count > 0:
            state_type = state_type | IconFactory.ACTIVE

        if group.needs_attention and window_count > 0:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if  gant == "red":
                state_type = state_type | IconFactory.NEEDS_ATTENTION
            elif gant != "nothing":
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    GLib.timeout_add(700, self.__attention_effect)

        if self.pressed:
            state_type = state_type | IconFactory.MOUSE_BUTTON_DOWN

        if self.mouse_over or \
           (self.drag_entered and not self.dnd_has_launcher):
            state_type = state_type | IconFactory.MOUSE_OVER

        if self.launch_effect:
            state_type = state_type | IconFactory.LAUNCH_EFFECT

        if self.dnd_has_launcher:
            if self.dnd_position == "start":
                state_type = state_type | IconFactory.DRAG_DROPP_START
            else:
                state_type = state_type | IconFactory.DRAG_DROPP_END

        # Add the number of windows
        state_type = state_type | window_count
        if state_type != self.state_type or force_update:
            surface = self.icon_factory.surface_update(state_type)
            self.state_type = state_type
            # Set the button size to the size of the surface
            width = surface.get_width()
            height = surface.get_height()
            if self.get_allocation().width !=  width or \
               self.get_allocation().height != height:
                self.set_size_request(width, height)
                # The size of dockbarx isn't changed when the
                # button size is changed. This is a (ugly?) fix for it.
                GLib.idle_add(self.dockbar_r().groups.box.queue_resize)
            self.update(surface)
        return

    def update_state_if_shown(self, *args):
        #Update state if the button is shown.
        a = self.get_allocation()
        if a.width>10 and a.height>10:
            self.update_state()

    def __attention_effect(self):
        group = self.group_r()
        self.attention_effect_running = True
        if group.needs_attention:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if gant == "compwater":
                dummy, x,y = self.get_window().get_origin()
                alloc = self.get_allocation()
                x = x + alloc.x + alloc.width//2
                y = y + alloc.y + alloc.height//2
                try:
                    if self.globals.get_compiz_version() >= '0.9.4':
                        screen_path = 'screen0'
                    else:
                        screen_path = 'allscreens'

                    compiz_call_async("water/%s/point"%screen_path, "activate",
                                "root", group.root_xid, "x", x, "y", y)
                except:
                    pass
            elif gant == "blink":
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    surface = self.icon_factory.surface_update(
                                        IconFactory.BLINK | self.state_type)
                    self.update(surface)
                else:
                    self.needs_attention_anim_trigger = False
                    surface = self.icon_factory.surface_update(self.state_type)
                    self.update(surface)
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False

    def set_badge(self, badge, backend=None):
        if not badge:
            if backend is not None and backend != self.badge_backend:
               # Don't remove a badge set by another backend.
               return
            self.badge_backend = None
        else:
            self.badge_backend = backend
        if badge == self.badge_text:
            return
        self.make_badge(badge)
        if self.surface is not None:
            self.update()

    def set_progress_bar(self, progress, backend=None):
        if progress is None:
            if backend is not None and backend != self.progress_backend:
               # Don't remove a progress bar set by another backend.
               return
            self.progress_backend = None
        else:
            self.progress_backend = backend
        if progress == self.progress:
            return
        self.make_progress_bar(progress)
        if self.surface is not None:
            self.update()

    def set_icongeo(self, window=None):
        group = self.group_r()
        if window:
            list_ = [window]
        else:
            list_ = group
        for window in list_:
            #~ if self.globals.settings["show_only_current_desktop"] and \
               #~ not window.is_on_current_desktop():
                #~ # Todo: Fix this for multiple dockbarx:s
                #~ window.wnck.set_icon_geometry(0, 0, 0, 0)
                #~ continue
            if (self.globals.settings["show_only_current_desktop"] and \
               not window.is_on_current_desktop()) or \
               (self.globals.settings["show_only_current_monitor"] and \
               not window.is_on_monitor(group.get_monitor())):
                continue
            alloc = self.get_allocation()
            if self.get_window():
                dummy, x,y = self.get_window().get_origin() # Why three values?
                x += alloc.x
                y += alloc.y
                window.wnck.set_icon_geometry(x, y, alloc.width, alloc.height)

    def set_manual_size(self, ms):
        self.manual_size = ms

    def apply_launch_effect(self, length=None):
        group = self.group_r()
        self.launch_effect = True
        if not length:
            if len(group)>0:
                length = 2000
            else:
                length = 10000
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        if group.popup.get_window() is not None:
            group.popup.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self.launch_effect_sid = GLib.timeout_add(length,
                                            self.remove_launch_effect)

    def remove_launch_effect(self):
        if self.launch_effect_sid:
            GLib.source_remove(self.launch_effect_sid)
            self.launch_effect_sid = None
        if not self.launch_effect:
            return False
        self.get_window().set_cursor(None)
        group = self.group_r()
        if group.popup.get_window() is not None:
            group.popup.get_window().set_cursor(None)
        self.launch_effect = False
        self.update_state()
        return False

    def update_tooltip(self, arg=None):
        group = self.group_r()
        if self.globals.settings["groupbutton_show_tooltip"] and \
           group.get_count() == 0 and \
           (self.globals.settings["no_popup_for_one_window"] \
            or not group.media_controls):
            try:
                comment = group.desktop_entry.getComment()
            except:
                comment = None
            if comment:
                text = "\n".join((group.name, comment))
            else:
                text = group.name
            self.set_tooltip_text(text)
        else:
            self.set_has_tooltip(False)


    #### Opacify
    def opacify(self, delay=None):
        group = self.group_r()
        if delay:
            if not self.opacify_sid:
                # Todo: Would it be better to remove previous delays if
                # a delay already is set?
                self.opacify_sid = GLib.timeout_add(delay, self.opacify)
            return
        if group.get_unminimized_count() > 0 and \
           self.pointer_is_inside():
            group.opacify()
            # This is a safety check to make sure that opacify won't stay on
            # forever when it shouldn't be.
            self.deopacify(500)
        if self.opacify_sid:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None

    def deopacify(self, delay=None):
        if delay:
            self.cancel_deopacify_request()
            self.deopacify_sid = GLib.timeout_add(delay, self.deopacify)
            return
        group = self.group_r()
        # Make sure that mouse cursor really has left the window button.
        if self.pointer_is_inside():
            return True
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        group.deopacify(110)

    def cancel_deopacify_request(self):
        if self.deopacify_sid:
            GLib.source_remove(self.deopacify_sid)
            self.deopacify_sid = None

    def cancel_opacify_request(self):
        if self.opacify_sid:
            GLib.source_remove(self.opacify_sid)
            self.opacify_sid = None


    #### DnD (source)
    def on_drag_begin(self, widget, drag_context):
        group = self.group_r()
        self.is_current_drag_source = True
        self.globals.dragging = True
        group.popup.hide()

    def on_drag_data_get(self, widget, context, selection, targetType, eventTime):
        group = self.group_r()
        name = group.identifier or group.desktop_entry.getFileName()
        target = selection.get_target()
        # Set requires bytes not string so we need to encode name.
        selection.set(target, 8, name.encode())


    def on_drag_end(self, widget, drag_context, result=None):
        self.is_current_drag_source = False
        self.globals.dragging = False
        #~ # A delay is needed to make sure the button is
        #~ # shown after on_drag_end has hidden it and
        #~ # not the other way around.
        #~ GLib.timeout_add(30, self.show)

    #### DnD (target)
    def on_drag_drop(self, widget, drag_context, x, y, t):
        targets = [target.name() for target in drag_context.list_targets()]
        if "text/groupbutton_name" in targets:
            target_atom = Gdk.Atom.intern("text/groupbutton_name", False)
            self.drag_get_data(drag_context, target_atom, t)
        elif "text/uri-list" in targets:
            self.dnd_on_drop = True
            target_atom = Gdk.Atom.intern("text/uri-list", False)
            self.drag_get_data(drag_context, target_atom, t)
        else:
            return False
        return True

    def on_drag_data_received(self, widget, context, x, y, selection, targetType, t):
        group = self.group_r()
        selection_target = selection.get_target().name()
        if selection_target == "text/groupbutton_name":
            name = group.identifier or group.desktop_entry.getFileName()
            # Selection data is in bytes we need to decode it to a string.
            data = selection.get_data().decode()
            if data != name:
                self.dockbar_r().groupbutton_moved(data, group, self.dnd_position)
            context.finish(True, False, t)
        elif selection_target == "text/uri-list":
            for uri in selection.get_uris():
                uri = uri.replace('\000', '')     # for spacefm
                if uri.startswith("file://") and uri.endswith(".desktop"):
                    # .desktop file! This is a potential launcher.
                    if self.dnd_on_drop:
                        #remove "file://" from the URI
                        path = uri[7:]
                        path = urllib.parse.unquote(path)
                        self.dockbar_r().launcher_dropped(path, group,
                                                          self.dnd_position)
                    else:
                        self.dnd_has_launcher = True
                        break
                elif self.dnd_on_drop:
                    group.launch(None, None, uri)
            if self.dnd_on_drop:
                context.finish(True, False, t)
            else:
                self.__update_dragging_status(x, y)

    def on_drag_motion(self, widget, drag_context, x, y, t):
        targets = [target.name() for target in drag_context.list_targets()]
        if "text/groupbutton_name" in targets and \
           not self.is_current_drag_source:
            Gdk.drag_status(drag_context, Gdk.DragAction.MOVE, t)
        elif "text/uri-list" in targets:
            Gdk.drag_status(drag_context, Gdk.DragAction.COPY, t)
        else:
            Gdk.drag_status(drag_context, Gdk.DragAction.PRIVATE, t)

        if not self.drag_entered:
            self.on_drag_enter(widget, drag_context, x, y, t)
            return True

        self.__update_dragging_status(x, y)
        return True

    def on_drag_enter(self, widget, drag_context, x, y, t):
        group = self.group_r()
        self.drag_entered = True
        targets = [target.name() for target in drag_context.list_targets()]
        if "text/groupbutton_name" in targets:
            if not self.is_current_drag_source:
                self.dnd_has_launcher = True
                self.update_state()
        elif "text/uri-list" in targets:
            # We have to get the data to find out if this
            # is a launcher or something else.
            self.dnd_on_drop = False
            target_atom = Gdk.Atom.intern("text/uri-list", False)
            self.drag_get_data(drag_context, target_atom, t)
            # No update_state() here!
        else:
            self.update_state()

    def on_drag_leave(self, widget, drag_context, t):
        group = self.group_r()
        self.dnd_has_launcher = False
        self.drag_entered = False
        self.update_state()
        group.popup.hide_if_not_hovered(100)
        if self.dnd_show_popup is not None:
            GLib.source_remove(self.dnd_show_popup)
            self.dnd_show_popup = None
        for window in group:
            window.remove_delayed_select()
        #~ if self.is_current_drag_source:
            #~ # If drag leave signal is given because of a drop,
            #~ # a small delay is needed since
            #~ # drag-end isn't called if
            #~ # the destination is hidden just before
            #~ # the drop is completed.
            #~ GLib.timeout_add(20, self.hide)

    def __update_dragging_status(self, x, y):
        if self.dnd_has_launcher:
            dnd_position = "end"
            if self.dockbar_r().orient in ("left", "right"):
                if y <= self.get_allocation().height // 2:
                    dnd_position = "start"
            else:
                if x <= self.get_allocation().width // 2:
                    dnd_position = "start"
            if dnd_position != self.dnd_position:
                self.dnd_position = dnd_position
                self.update_state()
        else:
            group = self.group_r()
            win_nr = group.get_count()
            if win_nr == 1:
                group[0].select_after_delay(600)
            elif win_nr > 1:
                delay = self.globals.settings["popup_delay"]
                self.dnd_show_popup = GLib.timeout_add(delay, group.popup.show)
            self.update_state()


    #### Events
    def on_size_allocate(self, widget, allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        CairoAppButton.on_size_allocate(self, widget, allocation)
        if self.old_alloc == self.get_allocation():
            return
        if not self.manual_size:
            # Let's update the size of the icons
            self.__set_size_from_allocation(allocation)
        self.__reset_locked_popup_position()
        self.old_alloc = allocation
        # Update icon geometry
        self.set_icongeo()

    def __reset_locked_popup_position(self):
        group = self.group_r()
        # If there is a locked popup on a dockbar at bottom, it needs to be
        # re-created for being at the right position.
        if group.locked_popup and self.dockbar_r().orient == "down":
            group.remove_locked_popup()
            group.add_locked_popup()

    def __set_size_from_allocation(self, allocation):
        if self.dockbar_r().orient in ("left", "right") and \
         allocation.width > 10 and allocation.width < 220 and \
         allocation.width != self.old_alloc.width:
            # A minimium size on 11 is set to stop unnecessary calls
            # work when the button is created
            self.icon_factory.set_size(allocation.width)
        elif self.dockbar_r().orient in ("down", "up") and \
         allocation.height > 10 and allocation.height < 220 and \
         allocation.height != self.old_alloc.height:
            self.icon_factory.set_size(allocation.height)
        else:
            return
        # Update state to resize the icon.
        self.update_state(force_update=True)


    def on_enter_notify_event(self, widget, event):
        group = self.group_r()
        if self.mouse_over:
            # False mouse enter event. Probably because a mouse button has been
            # pressed (compiz bug).
            return
        self.mouse_over = True
        window_cnt = group.get_count()
        if window_cnt <= 1 and \
           self.globals.settings["no_popup_for_one_window"]:
            self.update_state()
            return
        if  window_cnt == 0 and not group.media_controls:
            self.update_state()
            return

        if self.globals.get_shown_popup() is None:
            delay = self.globals.settings["popup_delay"]
        else:
            delay = self.globals.settings["second_popup_delay"]
        if not self.globals.gtkmenu and not self.globals.dragging:
            group.popup.show_after_delay(delay)
        self.update_state()
        # Opacify
        if self.globals.settings["opacify"] and \
           self.globals.settings["opacify_group"]:
            self.opacify(delay)

    def on_leave_notify_event(self, widget, event):
        if self.leave_notify_sid is not None:
            GLib.source_remove(self.leave_notify_sid)
            self.leave_notify_sid = None
        group = self.group_r()
        if group is None:
            return
        if self.pointer_is_inside():
            # False mouse_leave event, the cursor might be on a screen edge
            # or the mouse has been clicked (compiz bug).
            # A timeout is set so that the real mouse leave won't be missed.
            self.leave_notify_sid = GLib.timeout_add(50, self.on_leave_notify_event, self, event)
            return
        self.mouse_over = False
        self.pressed = False
        group.popup.cancel_show_request()
        group.popup.hide_if_not_hovered()
        if self.globals.settings["opacify"] \
        and self.globals.settings["opacify_group"]:
            self.deopacify(100)
        if not self.globals.settings["select_next_activate_immediately"] and \
           group.scrollpeak_sid is not None:
            group.scrollpeak_select()
        self.update_state()



    def on_scroll_event(self, widget, event):
        group = self.group_r()
        if event.direction == Gdk.ScrollDirection.UP:
            action = self.globals.settings["groupbutton_scroll_up"]
            group.action_function_dict[action](group, self, event)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            action = self.globals.settings["groupbutton_scroll_down"]
            group.action_function_dict[action](group, self, event)

    def on_button_release_event(self, widget, event):
        group = self.group_r()
        self.pressed = False
        self.update_state()
        # If a drag and drop just finished set self.draggin to false
        # so that left clicking works normally again
        if event.button == 1 and self.globals.dragging:
            self.globals.dragging = False
            return

        if not self.pointer_is_inside():
            return

        if not event.button in (1, 2, 3):
            return
        button = {1:"left", 2: "middle", 3: "right"}[event.button]
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        if not self.globals.settings[
                                "groupbutton_%s%s_click_double"%(mod, button)]:
            # No double click required, go ahead and do the action.
            action = self.globals.settings[
                                "groupbutton_%s%s_click_action"%(mod, button)]
            group.action_function_dict[action](group, self, event)


    def on_button_press_event(self, widget, event):
        group = self.group_r()
        if not event.button in (1, 2, 3):
            return True
        button = {1:"left", 2: "middle", 3: "right"}[event.button]
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            mod = "shift_and_"
        else:
            mod = ""
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            if self.globals.settings["groupbutton_%s%s_click_double"%(mod,
                                                                      button)]:
                # This is a double click and the
                # action requires a double click.
                # Go ahead and do the action.
                action = self.globals.settings[
                                "groupbutton_%s%s_click_action"%(mod, button)]
                group.action_function_dict[action](group, self, event)

        elif event.button == 1:
            self.pressed = True
            self.update_state()
            # Return False so that a drag-and-drop can be initiated if needed.
            return False
        return True


class GroupPopup(CairoPopup):

    def __init__(self, group, no_arrow=False, type_="popup"):
        self.group_r = weakref.ref(group)
        self.dockbar_r = weakref.ref(group.dockbar_r())
        self.popup_type = type_
        self.globals = Globals()
        CairoPopup.__init__(self, self.dockbar_r().orient, no_arrow, type_)
        self.set_type_hint(Gdk.WindowTypeHint.MENU)

        self.show_sid = None
        self.hide_if_not_hovered_sid = None
        self.popup_showing = False
        self.locked = False
        self.last_allocation = None

        # The popup needs to have a drag_dest just to check
        # if the mouse is hovering it during a drag-drop.
        self.drag_dest_set(0, [], 0)
        self.connect("leave-notify-event", self.on_leave_notify_event)
        self.connect("size-allocate", self.on_size_allocate)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-leave", self.on_drag_leave)

    def destroy(self, *args, **kvargs):
        self.cancel_show_request()
        self.cancel_hide_request()
        self.hide()
        CairoPopup.destroy(self, *args, **kvargs)

    def set_child_(self, child):
        old_child = self.get_child_()
        if old_child == child:
            return
        if old_child:
            self.childbox.remove(old_child)
        self.childbox.add(child)
        if self.popup_showing:
            child.show_all()
            self.resize(10, 10)

    def get_child_(self):
        children = self.childbox.get_children()
        if len(children) == 0:
            return None
        else:
            return children[0]

    def on_size_allocate(self, widget, allocation, no_move=False):
        if allocation == self.last_allocation:
            return
        group = self.group_r()
        # Move popup to it's right spot
        window = group.button.get_window()
        if not window:
            return
        offset = int(self.popup_style.get("%s_distance" % self.popup_type, -7))
        dummy, wx, wy = window.get_origin()
        b_alloc = group.button.get_allocation()
        width, height = allocation.width, allocation.height

        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = group.get_monitor().get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())

        if width > mgeo.width or height > mgeo.height:
            # The popup is too big to fit. Tell the child it needs to shrink.
            try:
                child_func = self.get_child_().shrink_size
            except AttributeError:
                pass
            else:
                child_func(isinstance(widget, LockedPopup))
            GLib.idle_add(self.resize, 10, 10)
            return
        if self.dockbar_r().orient in ("down", "up"):
            if self.globals.settings["popup_align"] == "left":
                x = b_alloc.x + wx
            if self.globals.settings["popup_align"] == "center":
                x = b_alloc.x + wx + (b_alloc.width // 2) - (width // 2)
            if self.globals.settings["popup_align"] == "right":
                x = b_alloc.x + wx + b_alloc.width - width
            y = b_alloc.y + wy - offset
            # Check that the popup is within the monitor
            if x + width > mgeo.x + mgeo.width:
                x = mgeo.x + mgeo.width - width
            if x < mgeo.x:
                x = mgeo.x
            if y >= mgeo.y + (mgeo.height // 2):
                direction = "down"
                y = y - height
            else:
                direction = "up"
                y = y + b_alloc.height + (offset * 2)
            p = wx + b_alloc.x + (b_alloc.width // 2) - x
        else:
            # Set position in such a way that the arrow is splits the
            # height at golden ratio...
            y = b_alloc.y + wy + (b_alloc.height // 2) - int(height * 0.382)
            # ..but don't allow the popup to be lower than the upper edge of
            # the button.
            if y > b_alloc.y + wy:
                y = b_alloc.y + wy
            # Check that the popup is within the monitor
            if y + height > mgeo.y + mgeo.height:
                y = mgeo.y + mgeo.height - height
            if y < mgeo.y:
                y = mgeo.y
            x = b_alloc.x + wx
            if x >= mgeo.x + (mgeo.width // 2):
                direction = "right"
                x = x - width - offset
            else:
                direction = "left"
                x = x + b_alloc.width + offset
            p = wy + b_alloc.y + (b_alloc.height // 2) - y
        self.point(direction, p)
        if not no_move:
            self.move(x, y)
        try:
            child_func = self.get_child_().on_popup_reallocate
        except AttributeError:
            pass
        else:
            child_func(self)


    def on_leave_notify_event(self, widget, event):
        CairoPopup.on_leave_notify_event(self, widget, event)
        self.hide_if_not_hovered()

    def show_after_delay(self, delay=0, force=False):
        group = self.group_r()
        # Prepare window preview so they are ready when the popup is shown.
        if self.get_child_() == group.window_list and group.window_list.show_previews:
            for window in group:
                GLib.idle_add(window.item.set_preview_image)
        if not delay:
            # No delay, show it now.
            self.__show(force)
            return
        self.cancel_show_request()
        self.show_sid = GLib.timeout_add(delay, self.__show, force)
        return


    def show(self, force=False):
        group = self.group_r()
        if self.get_child_() == group.window_list and group.window_list.show_previews:
            for window in group:
                GLib.idle_add(window.item.set_preview_image)
        self.__show(force)

    def __show(self, force=False):
        group = self.group_r()
        self.show_sid = None
        self.cancel_hide_request();
        if group.locked_popup:
            if force:
                group.locked_popup.hide()
            else:
                return
        if self.globals.gtkmenu:
            return
        try:
            if not self.get_child_().can_be_shown():
                return
        except:
            logger.exception("If an empty popup was shown this " + \
                             "might have something to do with it:")

        self.popup_showing = True
        CairoPopup.show_all(self)

        # Hide locked popup.
        if self.globals.get_locked_popup():
            self.globals.get_locked_popup().hide()
        # Hide other popup if open.
        shown_popup = self.globals.get_shown_popup()
        self.globals.set_shown_popup(self)
        if shown_popup is not None and shown_popup is not self:
            shown_popup.hide()
        self.resize(10,10)
        return False

    def hide(self):
        if self.globals.gtkmenu:
            return
        group = self.group_r()
        CairoPopup.hide(self)
        self.popup_showing = False
        self.cancel_show_request()
        self.cancel_hide_request()
        shown_popup = self.globals.get_shown_popup()
        locked_popup = self.globals.get_locked_popup()
        if locked_popup and locked_popup.group_r().get_windows() and \
           (shown_popup is None or shown_popup is self):
            locked_popup.show()
        if shown_popup is self:
            self.globals.set_shown_popup(None)
        if group.menu is not None:
            group.menu.delete_menu()
            group.menu = None
        # Set window list as the child so that it's ready next time
        # the popup is shown.
        if not group.locked_popup:
            self.set_child_(group.window_list)
        group.menu_is_shown = False

    def __hide_if_not_hovered(self):
        self.hide_if_not_hovered_sid = None
        group = self.group_r()
        if self.get_window() is None:
            # Popup isn't shown.
            return
        display = Gdk.Display.get_default()
        pos = display.get_pointer()
        button_list = Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.BUTTON2_MASK | \
                      Gdk.ModifierType.BUTTON3_MASK | Gdk.ModifierType.BUTTON4_MASK | \
                      Gdk.ModifierType.BUTTON5_MASK
        if not pos[3] & button_list and time() - self.hide_time < 0.6:
            # No mouse button is pressed and less than 600 ms has passed.
            # Check again in 10 ms.
            self.hide_if_not_hovered_sid = GLib.timeout_add(10, self.__hide_if_not_hovered)
            return
        if self.pointer_is_inside() or group.button.pointer_is_inside():
            return
        self.hide()
        return

    def hide_if_not_hovered(self, timer=0):
        self.hide_time = time()
        self.cancel_hide_request()
        if timer:
            self.hide_if_not_hovered_sid = GLib.timeout_add(timer,
                                                    self.hide_if_not_hovered)
        else:
            self.__hide_if_not_hovered()

    def cancel_hide_request(self):
        if self.hide_if_not_hovered_sid is not None:
            GLib.source_remove(self.hide_if_not_hovered_sid)
            self.hide_if_not_hovered_sid = None

    def cancel_show_request(self):
        if self.show_sid is not None:
            GLib.source_remove(self.show_sid)
            self.show_sid = None

    def expose(self):
        self.queue_draw()

    #### D'N'D
    def on_drag_motion(self, widget, drag_context, x, y, t):
        Gdk.drag_status(drag_context, Gdk.DragAction.PRIVATE, t)
        return True

    def on_drag_leave(self, widget, drag_context, t):
        self.hide_if_not_hovered(100)

class LockedPopup(GroupPopup):
    def __init__(self, group):
        self.globals = Globals()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = group.get_monitor().get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())
        button_window = group.button.get_window()
        if button_window:
            dummy, wx, wy = button_window.get_origin()
        else:
            wx, wy = (0, 0)
        if group.dockbar_r().orient in ("left", "right") or wy < mgeo.height // 2:
            # The popup should be placed at bottom of the screen and have no arrow.
            GroupPopup.__init__(self, group, no_arrow=True, type_="locked_list")
            self.point("down", 20)
        else:
            GroupPopup.__init__(self, group, type_="locked_list")
        child = group.popup.get_child_()
        if child:
            group.popup.childbox.remove(child)
        self.set_child_(group.window_list)
        group.window_list.apply_mini_mode()
        if not group.get_windows():
            self.hide()
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_accept_focus(False)
        self.set_resizable(False)
        self.overlap_sid = self.globals.connect("locked-list-overlap-changed", self.__set_own_strut)
        self.size_allocate_sid = self.connect("size-allocate", self.on_size_allocate)
        self.connect("realize", self.__on_realized)

    def show(self):
        CairoPopup.show_all(self)
        self.on_size_allocate(self, self.get_allocation())

    def hide(self):
        CairoPopup.hide(self)

    def hide_if_not_hovered(self):
        pass

    def on_size_allocate(self, widget, allocation):
        if allocation == self.last_allocation:
            return
        group = self.group_r()
        if group.locked_popup is None:
            # The group doesn't seem to be remove properly when a new
            # locked popup is opened.
            return
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = group.get_monitor().get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())

        width, height = allocation.width, allocation.height
        if self.dockbar_r().orient in ("down", "up"):
            button_window = group.button.get_window()
            if button_window:
                dummy, wx, wy = button_window.get_origin()
            else:
                wx, wy = (0, 0)
            if wy > mgeo.height // 2:
                GroupPopup.on_size_allocate(self, widget, allocation)
                self.__set_own_strut()
                return
        GroupPopup.on_size_allocate(self, widget, allocation, no_move=True)
        strut = self.__get_other_strut(mgeo.width // 2 - width // 2,
                                       mgeo.width // 2 + width // 2)
        self.move(mgeo.width // 2 - width // 2, mgeo.height - height - strut - 1)
        self.__set_own_strut()

        try:
            child_func = self.get_child_().on_popup_reallocate
        except AttributeError:
            pass
        else:
            child_func(self)

    def __set_own_strut(self, *args):
        win = self.get_window()
        if not win:
            return
        topw = XDisplay.create_resource_object('window',
                                               win.get_toplevel().get_xid())
        if self.globals.settings["locked_list_no_overlap"] is False:
            topw = XDisplay.create_resource_object('window',
                                                   win.get_toplevel().get_xid())
            topw.delete_property(XDisplay.get_atom("_NET_WM_STRUT"))
            topw.delete_property(XDisplay.get_atom("_NET_WM_STRUT_PARTIAL"))
            return
        global X
        if X is None:
            from Xlib import X
        group = self.group_r()
        a = self.get_allocation()
        x, y = self.get_position()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = group.get_monitor().get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())
        height = mgeo.y + mgeo.height - y
        x1 = max(mgeo.x + x, 0)
        x2 = max(mgeo.x + x + a.width, 0)
        strut = [0, 0, 0, height, 0, 0, 0, 0, 0, 0, x1, x2]
        topw.change_property(XDisplay.get_atom('_NET_WM_STRUT'),
                             XDisplay.get_atom('CARDINAL'), 32,
                             strut[:4],
                             X.PropModeReplace)
        topw.change_property(XDisplay.get_atom('_NET_WM_STRUT_PARTIAL'),
                             XDisplay.get_atom('CARDINAL'), 32,
                             strut,
                             X.PropModeReplace)
        XDisplay.flush()

    def __get_other_strut(self, x1, x2):
        # if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
        #     monitor = self.get_screen().get_display().get_monitor(0).get_geometry();
        # else:
        #     monitor = self.get_screen().get_monitor_geometry(0)
        # mx, my, mw, mh = monitor
        root = XDisplay.screen().root
        windows = root.query_tree()._data['children']
        strut_atom = XDisplay.get_atom('_NET_WM_STRUT')
        strut_partial_atom = XDisplay.get_atom('_NET_WM_STRUT_PARTIAL')
        strut = 0
        for w in windows:
            try:
                prop1 = w.get_full_property(strut_partial_atom, 0)
                prop2 = w.get_full_property(strut_atom, 0)
            except Xlib.error.BadWindow:
                continue
            if prop1 is not None:
                cl = w.get_wm_class()
                if cl and cl[0] == "dockx":
                    continue
                if prop1.value[10] <= x2 or prop1.value[11] >= x1:
                    strut = max(strut, prop1.value[3])
                continue
            if prop2 is not None:
                cl = w.get_wm_class()
                if cl and cl[0] == "dockx":
                    continue
                strut = max(strut, prop2.value[3])
        return strut

    def __on_realized(self, widget):
        self.get_window().set_override_redirect(False)
        self.__set_own_strut()

    def destroy(self):
        group = self.group_r()
        group.locked_popup = None
        self.globals.disconnect(self.overlap_sid)
        self.disconnect(self.size_allocate_sid)
        self.childbox.remove(group.window_list)
        group.popup.set_child_(group.window_list)
        group.window_list.apply_normal_mode()
        GroupPopup.destroy(self)


class WindowList(Gtk.Box):
    def __init__(self, group):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.globals = Globals()
        self.group_r = weakref.ref(group)
        self.dockbar_r = weakref.ref(group.dockbar_r())
        self.window_box = None
        self.scrolled_window = None
        self.show_previews = False
        self.size_overflow = False
        self.mini_mode = False

        GObject.GObject.__init__(self)
        self.set_border_width(0)
        self.set_spacing(2)
        self.title = Gtk.Label()
        # Title needs to be shown so that we can calculate the height of the window list.
        self.title.show()
        self.title.set_use_markup(True)
        self.update_title()
        self.update_title_tooltip()
        self.pack_start(self.title, False, False, 0)
        self.set_show_previews(self.globals.settings["preview"])

        self.globals_events = []
        self.globals_events.append(self.globals.connect("color2-changed", self.update_title))
        self.globals_events.append(self.globals.connect("show-previews-changed",
                self.__on_show_previews_changed))

    def destroy(self, *args, **kvargs):
        while self.globals_events:
            self.globals.disconnect(self.globals_events.pop())
        Gtk.Box.destroy(self, *args, **kvargs)

    def show_all(self):
        group = self.group_r()
        for window in group:
            if (self.globals.settings["show_only_current_desktop"] and \
               not window.is_on_current_desktop()) or \
               (self.globals.settings["show_only_current_monitor"] and \
               not window.is_on_monitor(group.get_monitor())):
                window.item.hide()
            else:
                window.item.show()
        Gtk.Box.show_all(self)

    def update_title(self, *args):
        group = self.group_r()
        if group.name is None:
            return
        self.title.set_label(
              "<span foreground='%s'>"%self.globals.colors["color2"] + \
              "<big><b>%s</b></big></span>"%escape(group.name))
        self.title.set_use_markup(True)

    def update_title_tooltip(self):
        group = self.group_r()
        if group.identifier:
            self.title.set_tooltip_text(
                        "%s: %s"%(_("Identifier"), group.identifier))

    def can_be_shown(self):
        group = self.group_r()
        if group.get_count() > 0 or group.media_controls:
            return True
        else:
            return False

    def add_item(self, item):
        if self.show_previews:
            item.update_preview_size()
            item.set_show_preview(self.show_previews)
        self.window_box.pack_start(item, True, True, 0)

    def reorder_item(self, index, item):
        self.window_box.reorder_child(item, index)

    def shrink_size(self, locked_popup=False):
        """This function is called if the window list is too big."""
        if self.show_previews:
            # Turn of the previews as a first meassure
            self.set_show_previews(False)
        else:
            # make the list scrollable
            self.size_overflow = True
            self.__rebuild_list(locked_popup)

    def set_show_previews(self, show_previews):
        group = self.group_r()
        if self.mini_mode:
            return
        if show_previews:
            # Only show the previews if there is enough room on the screen.
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
                mgeo = group.get_monitor().get_geometry();
            else:
                mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())
            if self.dockbar_r().orient in ("down", "up"):
                width = 10
                for window in group.get_windows():
                    width += max(190, window.item.update_preview_size()[0])
                    width += 16
                if width > mgeo.width:
                    show_previews = False
            else:
                height = 12 + self.title.get_preferred_height()[0]
                for window in group.get_windows():
                    height += window.item.update_preview_size()[1]
                    height += 24 + window.item.label.get_preferred_height()[0]
                if height > mgeo.height:
                    show_previews = False
        self.show_previews = show_previews
        self.__rebuild_list()
        for window in group:
            window.item.set_show_preview(show_previews)

    def __on_show_previews_changed(self, arg=None):
        self.set_show_previews(self.globals.settings["preview"])

    def __rebuild_list(self, locked_popup_list=False):
        oldbox = self.window_box
        if self.mini_mode:
            self.window_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 2)
        elif self.show_previews and self.dockbar_r().orient in ("down", "up"):
            self.window_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
        else:
            self.window_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 2)
        if oldbox:
            for c in oldbox.get_children():
                oldbox.remove(c)
                self.window_box.pack_start(c, True, True, 0)
            oldbox.destroy()
        if self.scrolled_window:
            self.adjustment.disconnect(self.scroll_changed_sid)
            self.adjustment = None
            self.scrolled_window.destroy()
            self.scrolled_window = None
        if self.size_overflow:
            self.scrolled_window = self.__create_scrolled_window(locked_popup_list)
            self.scrolled_window.add_with_viewport(self.window_box)
            self.pack_start(self.scrolled_window, True, True, 0)
            self.scrolled_window.show_all()
        else:
            self.pack_start(self.window_box, True, True, 0)
            self.window_box.show_all()

    def __create_scrolled_window(self, horizontal):
        group = self.group_r()
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        if horizontal:
            scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            self.adjustment = scrolled_window.get_hadjustment()
        else:
            scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.adjustment = scrolled_window.get_vadjustment()
        self.scroll_changed_sid = self.adjustment.connect("changed",
                                            self.__on_scroll_changed, horizontal)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 22:
            mgeo = group.get_monitor().get_geometry();
        else:
            mgeo = Gdk.Screen.get_default().get_monitor_geometry(group.get_monitor())
        # Todo: Size is hardcoded to monitor height/width - 100.
        #       Does this need to be more gracefully calculated?
        if horizontal:
            scrolled_window.set_size_request(mgeo.width - 100, -1)
        else:
            scrolled_window.set_size_request(-1, mgeo.height - 100)
        return scrolled_window

    def __on_scroll_changed(self, adjustment, horizontal):
        if adjustment.get_upper() < 1:
            # Not yet realised.
            return
        if adjustment.get_upper() <= adjustment.get_page_size():
            # The scrolled window is no longer needed.
            self.size_overflow = False
            GLib.idle_add(self.__rebuild_list, horizontal)


    def on_popup_reallocate(self, popup):
        if not self.window_box:
            return
        for windowitem in self.window_box.get_children():
            windowitem.redraw()

    #### Plugins
    def add_plugin(self, plugin):
        self.pack_end(plugin, True, True, 0)
        plugin.show()

    def remove_plugin(self, plugin):
        self.remove(plugin)

    #### Mini list
    def apply_mini_mode(self):
        group = self.group_r()
        self.set_spacing(0)
        self.title.set_no_show_all(True)
        self.title.hide()
        self.show_previews = False
        for window in group:
            window.item.set_show_preview(False)
        self.mini_mode = True
        self.__rebuild_list(True)

    def apply_normal_mode(self):
        self.set_spacing(2)
        self.title.set_no_show_all(False)
        self.title.show()
        self.mini_mode = False
        self.set_show_previews(self.globals.settings["preview"])
        self.__rebuild_list(False)


class GroupMenu(GObject.GObject):
    __gsignals__ = {
        "item-activated": (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        "item-hovered": (GObject.SignalFlags.RUN_FIRST, None, (int, str, )),
        "menu-resized": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, gtk_menu=False):
        GObject.GObject.__init__(self)
        self.gtk_menu = gtk_menu
        self.submenus = {}
        self.items = {}
        self.quicklist_position = 0
        self.globals = Globals()
        if gtk_menu:
            self.menu = Gtk.Menu()
        else:
            self.menu = Gtk.Box.new(Gtk.Orientation.VERTICAL, 2)
            self.menu.can_be_shown = lambda: True
        self.menu.show()

    def build_group_menu(self, desktop_entry, quicklist, \
                         pinned, locked_popup, use_locked_popup, \
                         win_nr, minimize, maximize):
        # Launcher stuff
        if desktop_entry:
            self.add_item(_("_Launch application"))
        if desktop_entry and not pinned:
            self.add_item(_("_Pin application"))
        if not pinned:
            self.add_item(_("Make custom launcher"))
        if pinned:
            self.add_item(_("Unpin application"))
            self.add_submenu(_("Properties"))
            self.add_item(_("Edit Identifier"), _("Properties"))
            self.add_item(_("Edit Launcher"), _("Properties"))
        # Quicklist
        self.__build_quicklist_menu(desktop_entry, quicklist)
        # Recent and most used files
        if zg.is_available():
            zg_identifier = self.add_separator(identifier="zg_separator")
            zg_identifier.set_no_show_all(True)
            for name in (_("Recent"), _("Most used"), _("Related")):
                sm = self.add_submenu(name)
                sm.set_no_show_all(True)
        # Floating Window Panel
        if locked_popup or use_locked_popup:
            self.add_separator()
            item = self.add_item(_("Floating Window Panel"), None, None,
                                 "checkmark")
        if locked_popup:
            item.set_active(True)
        # Windows stuff
        if win_nr:
            self.add_separator()
            if win_nr == 1:
                t = ""
            else:
                t = _(" all windows")
            if minimize:
                self.add_item(_("_Minimize") + t)
            else:
                self.add_item(_("Un_minimize") + t)
            if maximize:
                self.add_item(_("Ma_ximize") + t)
            else:
                self.add_item(_("Unma_ximize") + t)
            self.add_item(_("_Close") + t)

    def __build_quicklist_menu(self, desktop_entry, quicklist):
        # Unity static quicklist
        static_quicklist = None
        if desktop_entry and self.globals.settings["quicklist"]:
            static_quicklist = desktop_entry.get_quicklist()
            if static_quicklist:
                self.add_separator()
            for label in static_quicklist:
                identifier = "quicklist_%s" % label
                self.add_item(label, identifier=identifier)
        # Unity dynamic quicklists
        if quicklist:
            layout = quicklist.layout
        else:
            layout = None
        if not bool(static_quicklist) and layout is not None:
            for item in layout[2]:
                if item[1].get("visible", True):
                    self.add_separator()
                    break
        self.add_quicklist(layout)

    def populate_zg_menus(self, recent, most_used, related):
        # Makes Recent, Most used and Related submenus and return a dict of all zeitgeist identifiers and uris.
        zg_files = {}
        # Add a separator.
        if recent or most_used or related:
            self.items["zg_separator"].show()
        else:
            self.items["zg_separator"].hide()
        # Make the menus.
        self.__populate_zg_menu(_("Recent"), recent, zg_files)
        self.__populate_zg_menu(_("Most used"), most_used, zg_files)
        self.__populate_zg_menu(_("Related"), related, zg_files)
        return zg_files

    def __populate_zg_menu(self, name, files, zg_files):
        # Menu items for the files will be made and the indentifiers and uris will be saved in zg_files.
        menu = self.submenus[name]
        # Remove old menu items
        if self.gtk_menu:
            for child in menu.get_children():
                child.destroy()
        else:
            for item in menu.get_items():
                menu.remove_item(item)
                item.destroy()
        if not files:
            menu.hide()
        # Add new items
        for text, uri in files:
            label = text or uri
            # Shorten labels that are more than 40 chars long.
            if len(label)>40:
                label = label[:19]+"..."+label[-18:]
            identifier = "zg_%s" % label
            n = 0
            # If there are multiple identifiers with the same name, add a number to it.
            while identifier in zg_files:
                n += 1
                identifier = "zg_%s%s" % (label, n)
            zg_files[identifier] = uri
            self.add_item(label, name, identifier=identifier)
        # zg_files is a dict so there is no need to return it.

    def add_item(self, name, submenu=None, identifier=None, toggle_type=""):
        # Todo: add toggle types
        if not identifier:
            identifier = name
        if self.gtk_menu:
            if toggle_type in ("checkmark","radio"):
                item = Gtk.CheckMenuItem(name)
                item.set_draw_as_radio(toggle_type == "radio")
            else:
                item = Gtk.MenuItem(name)
            item.set_use_underline(True)
            item.show()
            if submenu:
                self.submenus[submenu].append(item)
                item.connect("button-press-event",
                             self.__on_item_activated, identifier)
            else:
                self.menu.append(item)
                item.connect("activate", self.__on_item_activated, identifier)
        else:
            if toggle_type in ("checkmark","radio"):
                item = CairoCheckMenuItem(name, toggle_type)
            else:
                item = CairoMenuItem(name)
            item.connect("clicked", self.__on_item_activated, identifier)
            item.show()
            if submenu:
                self.submenus[submenu].add_item(item)
            else:
                self.menu.pack_start(item, True, True, 0)
        item.connect("enter-notify-event", self.__on_item_hovered, identifier)
        self.items[identifier] = item
        return item

    def add_submenu(self, name, submenu=None, identifier=None):
        if self.gtk_menu:
            item = Gtk.MenuItem.new_with_mnemonic(name)
            item.show()
            if submenu:
                self.submenus[submenu].append(item)
            else:
                self.menu.append(item)
            menu = Gtk.Menu()
            item.set_submenu(menu)
        else:
            item = None
            menu = CairoToggleMenu(name)
            if submenu:
                self.submenus[submenu].add_item(menu)
            else:
                self.menu.pack_start(menu, True, True, 0)
            menu.show()
            menu.connect("toggled", self.__on_submenu_toggled)
        if identifier is not None:
            self.items[identifier] = item or menu
        self.submenus[identifier or name] = menu
        return item or menu

    def add_separator(self, submenu=None, identifier=None):
        separator = Gtk.SeparatorMenuItem()
        separator.show()
        if self.gtk_menu:
            if submenu:
                self.submenus[submenu].append(separator)
            else:
                self.menu.append(separator)
        else:
            if submenu:
                self.submenus[submenu].add_item(separator)
            else:
                self.menu.pack_start(separator, True, True, 0)
        if identifier is not None:
            self.items[identifier] = separator
        return separator

    def get_menu(self):
        return self.menu

    def get_item(self, identifier):
        return self.items.get(identifier)

    def has_submenu(self, name):
        return name in self.submenus

    def add_quicklist(self, layout):
        self.quicklist_position = len(self.menu.get_children())
        if not layout:
            return False
        return self.add_quicklist_menu(layout, None)

    def add_quicklist_menu(self, layout, parent):
        for layout_item in layout[2]:
            identifier = "unity_%s" % layout_item[0]
            props = layout_item[1]
            label = props.get("label", "")
            visible = props.get("visible", True)
            enabled = props.get("enabled", True)
            type_ = props.get("type", "standard")
            toggle_type = props.get("toggle-type", "")
            toggled = props.get("toggle-state", -1)
            submenu = props.get("children-display", "")
            if type_ == "separator":
                item = self.add_separator(parent, identifier)
            elif submenu:
                item = self.add_submenu(label, parent, identifier)
                self.add_quicklist_menu(layout_item, identifier)
            elif not label:
                continue
            else:
                item = self.add_item(label,
                                     parent,
                                     identifier,
                                     toggle_type)
            if visible:
                item.show()
            else:
                item.hide()
            if not submenu:
                item.set_sensitive(enabled)
            if toggle_type:
                if toggled in (0,1):
                    item.set_active(toggled)
                    item.set_inconsistent(False)
                else:
                    item.set_inconsistent(True)

    def update_quicklist_menu(self, layout):
        open_menus = []
        if not self.gtk_menu:
            # Get all open submenus
            for identifier, menu in list(self.submenus.items()):
                if menu.get_toggled():
                    open_menus.append(identifier)
        # Remove the old parts of the quicklist and add the new.
        if layout[0] == 0:
            for identifier, item in list(self.items.items()):
                if not identifier.startswith("unity_"):
                    continue
                for child in self.menu.get_children():
                    if child == item:
                        break
                else:
                    continue
                del self.items[identifier]
                item.destroy()
            children = self.menu.get_children()
            pack_list = []
            while len(children) > self.quicklist_position:
                child = children.pop(self.quicklist_position)
                self.menu.remove(child)
                pack_list.append(child)
            self.add_quicklist_menu(layout, None)
            for child in pack_list:
                if self.gtk_menu:
                    self.menu.append(child)
                else:
                    self.menu.pack_start(child, True, True, 0)
        else:
            identifier = "unity_%s" % layout[0]
            menu = self.submenus[identifier]
            if self.gtk_menu:
                for child in menu.get_children():
                    child.destroy()
            else:
                for item in menu.get_items():
                    menu.remove_item(item)
                    item.destroy()
            self.add_quicklist_menu(layout, identifier)
        for identifier in open_menus:
            # Reopen the closed submenus.
            menu = self.submenus[identifier]
            if not menu.get_toggled():
                menu.toggle()
            else:
                menu.queue_draw()
        if not self.gtk_menu:
            self.emit("menu-resized")

    def remove_quicklist(self):
        self.update_quicklist_menu([0,{},[]])

    def set_properties(self, identifier, props):
        item = self.get_item(identifier)
        if item is None:
            logger.warning("Tried to change a quicklist menu item that doesn't exist.")
            return
        label = props.get("label", "")
        visible = props.get("visible", True)
        enabled = props.get("enabled", True)
        type_ = props.get("type", "standard")
        toggle_type = props.get("toggle-type", "")
        toggled = props.get("toggle-state", -1)
        submenu = props.get("children-display", "")
        if visible:
            item.show()
        else:
            item.hide()
        if not submenu:
            item.set_sensitive(enabled)
        if toggle_type:
            if toggled in (0,1):
                item.set_active(toggled)
                item.set_inconsistent(False)
            else:
                item.set_inconsistent(True)
        if type_ == "standard" and label:
            if self.gtk_menu:
                item.get_child().set_text(label)
            else:
                item.set_label(label)

    def delete_menu(self):
        del self.submenus
        del self.items
        disconnect(self)
        self.menu.destroy()
        del self.menu

    def __on_item_hovered(self, button, event, identifier):
        self.emit("item-hovered", event.time, identifier)

    def __on_item_activated(self, *args):
        identifier = args[-1]
        self.emit("item-activated", identifier)

    def __on_submenu_toggled(self, *args):
        self.emit("menu-resized")

