#!/usr/bin/python

#   groupbutton.py
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
pygtk.require('2.0')
import gtk
import gobject
import gconf
import wnck
from time import time
from time import sleep
import os
import gc
gc.enable()
import pango

from windowbutton import WindowButton
from iconfactory import IconFactory
from common import ODict
from cairowidgets import CairoButton, CairoMenuItem
from cairowidgets import CairoPopup, CairoToggleMenu
from common import Globals, compiz_call, DesktopEntry
import zg

import i18n
_ = i18n.language.gettext

ATOM_PREVIEWS = gtk.gdk.atom_intern('_KDE_WINDOW_PREVIEW')

class WindowDict(dict):
    def __init__(self, monitor=1, **kvargs):
        dict.__init__(self, **kvargs)
        self.globals = Globals()
        self.monitor = monitor

    def get_list(self):
        # Returns a list of windows that are in current use
        wins = []
        for win in self:
            if self.globals.settings["show_only_current_desktop"] and \
               not self[win].is_on_current_desktop():
                continue
            if self.globals.settings["show_only_current_monitor"] and \
               self.monitor != self[win].monitor:
                continue
            wins.append(win)
        return wins

    def get_unminimized(self):
        return [win for win in self.get_list() if not win.is_minimized()]

    def get_minimized(self):
        return [win for win in self.get_list() if win.is_minimized()]

    def get_count(self):
        return len(self.get_list())

    def get_minimized_count(self):
        return len(self.get_minimized())

    def get_unminimized_count(self):
        return len(self.get_unminimized())

class GroupButton(gobject.GObject):
    """Group button takes care of a program's "button" in dockbar.

    It also takes care of the popup window and all the window buttons that
    populates it."""

    __gsignals__ = {
        "delete":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
        "launch-preference":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "identifier-change":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "groupbutton-moved":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "edit-launcher-properties":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "launcher-dropped":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "pinned":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "unpinned":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
        "minimize-others":
            (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, ))
                   }

    def __init__(self, identifier=None, desktop_entry=None,
                 pinned=False, monitor=0):
        gobject.GObject.__init__(self)

        self.globals = Globals()
        self.globals.connect('show-only-current-desktop-changed',
                             self.on_show_only_current_desktop_changed)
        self.globals.connect('color2-changed', self.update_popup_label)
        self.globals.connect('show-previews-changed',
                             self.on_show_previews_changed)
        self.globals.connect('show-tooltip-changed',
                             self.update_tooltip)
        self.pinned = pinned
        self.desktop_entry = desktop_entry
        self.monitor = monitor
        self.identifier = identifier
        if identifier is None and desktop_entry is None:
            raise Exception, \
                "Can't initiate Group button without identifier or launcher."



        # Variables

        self.minimized_windows_count = 0
        self.minimized_state = 0
        self.has_active_window = False
        self.needs_attention = False
        self.attention_effect_running = False
        self.nextlist = None
        self.nextlist_time = None
        self.mouse_over = False
        self.pressed = False
        self.opacified = False
        self.lastlaunch = None
        self.launch_effect = False
        self.hide_list_sid = None
        self.show_list_sid = None

        self.menu_is_shown = False

        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.windows = WindowDict(self.monitor)


        #--- Button
        self.icon_factory = IconFactory(identifier=self.identifier,
                                        desktop_entry=self.desktop_entry)
        self.button = CairoButton()
        self.button.show_all()



        # Button events
        self.button.connect("enter-notify-event", self.on_button_mouse_enter)
        self.button.connect("leave-notify-event", self.on_button_mouse_leave)
        self.button.connect("button-release-event",
                            self.on_group_button_release_event)
        self.button.connect("button-press-event",
                            self.on_group_button_press_event)
        self.button.connect("scroll-event", self.on_group_button_scroll_event)
        self.button.connect("size-allocate", self.on_sizealloc)
        self.button_old_alloc = self.button.get_allocation()


        #--- Popup window
        self.popup = CairoPopup()
        self.popup_showing = False
        self.popup.connect("leave-notify-event",self.on_popup_mouse_leave)
        self.popup.connect_after("size-allocate", self.on_popup_size_allocate)

        self.popup_box = gtk.VBox()
        self.popup_box.set_border_width(0)
        self.popup_box.set_spacing(2)
        self.popup_label = gtk.Label()
        self.popup_label.set_use_markup(True)
        self.update_name()
        if self.identifier:
            self.popup_label.set_tooltip_text(
                                    "%s: %s"%(_("Identifier"),self.identifier))
        self.popup_box.pack_start(self.popup_label, False)
        # Initiate the windowlist
        self.winlist = None
        self.on_show_previews_changed()
        self.popup.add(self.popup_box)


        #--- D'n'D
        # Drag and drop should handel buttons that are moved,
        # launchers that is dropped, and open popup window
        # to enable drag and drops to windows that has to be
        # raised.
        self.button.drag_dest_set(0, [], 0)
        self.button.connect("drag_motion", self.on_button_drag_motion)
        self.button.connect("drag_leave", self.on_button_drag_leave)
        self.button.connect("drag_drop", self.on_drag_drop)
        self.button.connect("drag_data_received", self.on_drag_data_received)
        self.button_drag_entered = False
        self.launcher_drag = False
        self.dnd_show_popup = None
        self.dnd_select_window = None
        self.dd_uri = None

        # The popup needs to have a drag_dest just to check
        # if the mouse is howering it during a drag-drop.
        self.popup.drag_dest_set(0, [], 0)
        self.popup.connect("drag_motion", self.on_popup_drag_motion)
        self.popup.connect("drag_leave", self.on_popup_drag_leave)

        #Make buttons drag-able
        self.button.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                    [('text/groupbutton_name', 0, 47593)],
                                    gtk.gdk.ACTION_MOVE)
        self.button.drag_source_set_icon_pixbuf(
                                        self.icon_factory.find_icon_pixbuf(32))
        self.button.connect("drag_begin", self.on_drag_begin)
        self.button.connect("drag_data_get", self.on_drag_data_get)
        self.button.connect("drag_end", self.on_drag_end)
        self.is_current_drag_source = False


    def set_identifier(self, identifier):
        self.identifier = identifier
        self.popup_label.set_tooltip_text(
                                    "%s: %s"%(_("Identifier"),self.identifier))

    def update_name(self):
        self.name = None
        if self.desktop_entry:
            try:
                self.name = self.desktop_entry.getName()
            except:
                pass
        if self.name is None and self.windows:
            # Uses first half of the name,
            # like "Amarok" from "Amarok - [SONGNAME]"
            # A program that uses a name like "[DOCUMENT] - [APPNAME]" would be
            # totally screwed up. So far no such program has been reported.
            self.name = self.windows.keys()[0].get_class_group().get_name()
            self.name = self.name.split(" - ", 1)[0]
        if self.name is None and self.identifier:
            self.name = self.identifier
        if self.name is None:
            return
        self.popup_label.set_label(
                    "<span foreground='%s'>"%self.globals.colors['color2'] + \
                    "<big><b>%s</b></big></span>"%self.name
                                  )
        self.update_tooltip()

    def remove_launch_effect(self):
        self.launch_effect = False
        self.update_state()
        return False

    def update_tooltip(self, arg=None):
        if self.globals.settings['groupbutton_show_tooltip'] and \
           self.windows.get_count() == 0:
            try:
                comment = self.desktop_entry.getComment()
            except:
                comment = None
            if comment:
                text = "\n".join((self.name, comment))
            else:
                text = self.name
            self.button.set_tooltip_text(text)
        else:
            self.button.set_has_tooltip(False)

    #### State
    def update_popup_label(self, arg=None):
        if self.name is None:
            return
        self.popup_label.set_text(
                    "<span foreground='%s'>"%self.globals.colors['color2'] + \
                    "<big><b>%s</b></big></span>"%self.name
                                 )
        self.popup_label.set_use_markup(True)

    def update_state(self):
        # Checks button state and set the icon accordingly.
        win_nr = min(self.windows.get_count(), 15)
        if win_nr == 0 and not self.pinned:
            self.button.hide()
            return
        else:
            self.button.show()


        self.state_type = 0
        mwc = self.windows.get_minimized_count()
        if self.pinned and win_nr == 0:
            self.state_type = self.state_type | IconFactory.LAUNCHER
        elif (win_nr - mwc) <= 0:
            self.state_type = self.state_type | IconFactory.ALL_MINIMIZED
        elif mwc > 0:
            self.state_type = self.state_type | IconFactory.SOME_MINIMIZED

        if self.has_active_window and win_nr > 0:
            self.state_type = self.state_type | IconFactory.ACTIVE

        if self.needs_attention and win_nr > 0:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if  gant == 'red':
                self.state_type = self.state_type | IconFactory.NEEDS_ATTENTION
            elif gant != 'nothing':
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    gobject.timeout_add(700, self.attention_effect)

        if self.pressed:
            self.state_type = self.state_type | IconFactory.MOUSE_BUTTON_DOWN

        if self.mouse_over:
            self.state_type = self.state_type | IconFactory.MOUSE_OVER
        elif self.button_drag_entered and not self.launcher_drag:
            # Mouse over effect on other drag and drop
            # than launcher dnd.
            self.state_type = self.state_type | IconFactory.MOUSE_OVER

        if self.launch_effect:
            self.state_type = self.state_type | IconFactory.LAUNCH_EFFECT

        if self.launcher_drag:
            self.state_type = self.state_type | IconFactory.DRAG_DROPP

        # Add the number of windows
        self.state_type = self.state_type | win_nr
        surface = self.icon_factory.surface_update(self.state_type)

        # Set the button size to the size of the surface
        if self.button.allocation.width != surface.get_width() or \
           self.button.allocation.height != surface.get_height():
            self.button.set_size_request(
                                    surface.get_width(), surface.get_height())
        self.button.update(surface)
        return

    def update_state_request(self):
        #Update state if the button is shown.
        a = self.button.get_allocation()
        if a.width>10 and a.height>10:
            self.update_state()

    def attention_effect (self):
        self.attention_effect_running = True
        if self.needs_attention:
            gant = self.globals.settings[
                                    "groupbutton_attention_notification_type"]
            if gant == 'compwater':
                x,y = self.button.window.get_origin()
                alloc = self.button.get_allocation()
                x = x + alloc.x + alloc.width/2
                y = y + alloc.y + alloc.height/2
                try:
                    compiz_call('water/allscreens/point', 'activate',
                                'root', self.root_xid, 'x', x, 'y', y)
                except:
                    pass
            elif gant == 'blink':
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    surface = self.icon_factory.surface_update(
                                        IconFactory.BLINK | self.state_type)
                    self.button.update(surface)
                else:
                    self.needs_attention_anim_trigger = False
                    surface = self.icon_factory.surface_update(self.state_type)
                    self.button.update(surface)
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False

    def on_show_only_current_desktop_changed(self, arg):
        self.update_state()
        self.nextlist = None
        self.set_icongeo()

    def on_show_previews_changed(self, arg=None):
        oldbox = self.winlist
        if self.globals.settings['preview']:
            self.winlist = gtk.HBox()
            self.winlist.set_spacing(4)
        else:
            self.winlist = gtk.VBox()
            self.winlist.set_spacing(2)
        if oldbox:
            for c in oldbox.get_children():
                oldbox.remove(c)
                self.winlist.pack_start(c, False)
            self.popup_box.remove(oldbox)
        self.popup_box.pack_start(self.winlist, False)

    #### Window handling
    def add_window(self,window):
        if window in self.windows:
            return
        wb = WindowButton(window)
        self.windows[window] = wb
        self.winlist.pack_start(wb.button, True, True)
        if window.is_minimized():
            self.minimized_windows_count += 1
        if len(self.windows)==1:
            if self.name is None:
                self.update_name()
            self.icon_factory.set_class_group(window.get_class_group())
        if self.launch_effect:
            self.launch_effect = False
            gobject.source_remove(self.launch_effect_timeout)
        if window.needs_attention():
            self.on_needs_attention_changed()

        wb.connect('minimized', self.on_window_minimized, wb)
        wb.connect('unminimized', self.on_window_unminimized, wb)
        wb.connect('needs-attention-changed', self.on_needs_attention_changed)
        wb.connect('popup-hide', self.on_popup_hide)
        wb.connect('popup-expose-request', self.on_popup_expose_request)
        wb.connect('monitor-changed', self.on_window_monitor_changed)
        # Update state unless the button hasn't been shown yet.
        self.update_state_request()

        #Update popup-list if it is being shown.
        if self.popup_showing:
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if (self.globals.settings["show_only_current_desktop"] and \
                   not win.is_on_current_desktop()) or \
                   (self.globals.settings["show_only_current_monitor"] and \
                   self.monitor != win.monitor):
                    win.button.hide_all()
                else:
                    win.button.show_all()
            gobject.idle_add(self.show_list)

        self.update_tooltip()

        # Set minimize animation
        # (if the eventbox is created already,
        # otherwice the icon animation is set in sizealloc())
        if self.button.window:
            x, y = self.button.window.get_origin()
            a = self.button.get_allocation()
            x += a.x
            y += a.y
            window.set_icon_geometry(x, y, a.width, a.height)

    def del_window(self,window):
        if window.is_minimized():
            self.minimized_windows_count -= 1
        if self.nextlist and window in self.nextlist:
            self.nextlist.remove(window)
        self.windows[window].del_button()
        del self.windows[window]
        if self.needs_attention:
            self.on_needs_attention_changed()
        self.update_state_request()
        self.update_tooltip()
        if self.windows.get_unminimized_count() == 0:
            if self.opacified:
                self.globals.opacified = False
                self.opacified = False
                self.deopacify()
        if self.popup_showing:
            if self.windows.get_count() > 0:
                # Move and resize the popup.
                self.show_list()
            else:
                self.hide_list()
        if not self.windows and not self.pinned:
            # Remove group button.
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()

    def set_has_active_window(self, mode):
        if mode != self.has_active_window:
            self.has_active_window = mode
            if mode == False:
                for window_button in self.windows.values():
                    window_button.set_button_active(False)
            self.update_state_request()

    def on_window_minimized(self, arg, wb):
        self.minimized_windows_count+=1
        self.update_state()

    def on_window_unminimized(self, arg, wb):
        self.minimized_windows_count-=1
        self.update_state()

    def on_needs_attention_changed(self, arg=None):
        # Checks if there are any urgent windows and changes
        # the group button looks if there are at least one
        for window in self.windows.keys():
            if window.needs_attention():
                self.needs_attention = True
                self.update_state_request()
                return True
        else:
            if self.windows.keys() == []:
                # The window needs attention already when it's added,
                # before it's been added to the list.
                self.needs_attention = True
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return True
            else:
                self.needs_attention = False
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return False


    def set_icongeo(self, arg=None):
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] and \
               not self.windows[win].is_on_current_desktop():
                win.set_icon_geometry(0, 0, 0, 0)
                continue
            if self.globals.settings["show_only_current_desktop"] and \
               self.windows[win].monitor != self.monitor:
                continue
            alloc = self.button.get_allocation()
            if self.button.window:
                x,y = self.button.window.get_origin()
                x += alloc.x
                y += alloc.y
                win.set_icon_geometry(x, y, alloc.width, alloc.height)


    def on_db_move(self, arg=None):
        self.set_icongeo()

    def on_window_monitor_changed(self, arg=None):
        self.update_state()
        self.on_set_geo_grp()
        #Update popup-list if it is being shown.
        if self.popup_showing:
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if (self.globals.settings["show_only_current_desktop"] and \
                   not win.is_on_current_desktop()) or \
                   (self.globals.settings["show_only_current_monitor"] and \
                   self.monitor != win.monitor):
                    win.button.hide_all()
                else:
                    win.button.show_all()
            gobject.idle_add(self.show_list_request)


    def on_popup_expose_request(self, arg=None):
        event = gtk.gdk.Event(gtk.gdk.EXPOSE)
        event.window = self.popup.window
        event.area = self.popup.get_allocation()
        self.popup.send_expose(event)

    def on_popup_hide(self, arg=None, reason=None):
        if reason == 'viewport-change' \
        and self.hide_list_sid is not None:
            # The list brought up by keyboard
            # and will close by itself later
            # no need to close it now.
            return
        self.hide_list()

    def on_popup_hide_request(self, arg=None):
        self.hide_time = time()
        self.hide_list_request()


    #### Show/hide list
    def show_list_request(self):
        # If mouse cursor is over the button, show popup window.
        if self.popup_showing or \
           (self.button.pointer_is_inside() and \
            not self.globals.right_menu_showing and \
            not self.globals.dragging):
            self.show_list()
        return False

    def show_list(self):
        win_cnt = self.windows.get_count()
        if win_cnt == 0 and not self.menu_is_shown:
            self.hide_list()
            return
        if self.globals.settings["preview"]:
            # Set hint type so that previews can be used.
            if not self.popup.get_property('visible'):
                self.popup.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_MENU)
        else:
            if not self.popup.get_property('visible'):
                self.popup.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)

        self.popup_box.show()
        self.winlist.show()
        self.popup_label.show()
        for window, wb in self.windows.items():
            if (self.globals.settings["show_only_current_desktop"] and \
               not wb.is_on_current_desktop()) or \
               (self.globals.settings["show_only_current_monitor"] and \
               self.monitor != wb.monitor):
                wb.button.hide()
            else:
                wb.button.show()
                wb.button.set_preview_aspect(window.get_geometry()[2],
                                              window.get_geometry()[3])
        self.popup.resize(10,10)
        self.popup.show()
        self.popup_showing = True

        # Hide other popup if open.
        if self.globals.gb_showing_popup is not None and \
           self.globals.gb_showing_popup != self:
            self.globals.gb_showing_popup.hide_list()
        self.globals.gb_showing_popup = self

        # The popup must be shown before the
        # preview can be set. Iterate gtk events.
        while gtk.events_pending():
                gtk.main_iteration(False)
        # Tell the compiz/kwin where to put the previews.
        if self.globals.settings["preview"] and not self.menu_is_shown and \
           self.windows.get_count() > 0:
            previews = []
            previews.append(win_cnt)
            for win in self.windows.get_list():
                wb = self.windows[win]
                previews.append(5)
                previews.append(win.get_xid())
                (x, y, w, h) = wb.get_preview_alloc()
                previews.append(x)
                previews.append(y)
                previews.append(w)
                previews.append(h)
                # The button needs to be drawn again to ensure that
                # the preview is shown correctly.
                # Todo: Make sure if this is the best solution!
                #       What is the connection between redrawing and previews?
                wb.button.redraw()
        else:
            previews = [0,5,0,0,0,0,0]
        self.popup.window.property_change(ATOM_PREVIEWS,
                                          ATOM_PREVIEWS,
                                          32,
                                          gtk.gdk.PROP_MODE_REPLACE,
                                          previews)

        return False

    def hide_list_request(self):
        if self.popup.window is None:
            # Popup isn't shown.
            return
        display = gtk.gdk.display_get_default()
        pos = display.get_pointer()
        button_list = gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON2_MASK | \
                      gtk.gdk.BUTTON3_MASK | gtk.gdk.BUTTON4_MASK | \
                      gtk.gdk.BUTTON5_MASK
        if not pos[3] & button_list and time() - self.hide_time < 0.6:
            # No mouse button is pressed and less than 600 ms has passed.
            # Check again in 10 ms.
            gobject.timeout_add(10, self.hide_list_request)
            return
        if self.popup.pointer_is_inside() or self.button.pointer_is_inside():
            return
        self.hide_list()
        return

    def hide_list(self):
        if self.popup.window:
            self.popup.window.property_change(ATOM_PREVIEWS,
                                              ATOM_PREVIEWS,
                                              32,
                                              gtk.gdk.PROP_MODE_REPLACE,
                                              [0,5,0,0,0,0,0])
        self.popup.hide()
        self.popup_showing = False
        if self.show_list_sid is not None:
            gobject.source_remove(self.show_list_sid)
            self.show_list_sid = None
        if self.hide_list_sid is not None:
            gobject.source_remove(self.hide_list_sid)
            self.hide_list_sid = None
        if self.globals.gb_showing_popup == self:
            self.globals.gb_showing_popup = None
        self.popup.remove(self.popup.alignment.get_child())
        self.popup.add(self.popup_box)
        self.menu_is_shown = False
        return False

    def on_popup_size_allocate(self, widget, allocation):
        # Move popup to it's right spot
        offset = -7
        wx, wy = self.button.window.get_origin()
        b_alloc = self.button.get_allocation()
        width, height = self.popup.get_size()
        mgeo = gtk.gdk.screen_get_default().get_monitor_geometry(self.monitor)
        if self.globals.orient == "h":
            if self.globals.settings['popup_align'] == 'left':
                x = b_alloc.x + wx
            if self.globals.settings['popup_align'] == 'center':
                x = b_alloc.x + wx + (b_alloc.width / 2) - (width / 2)
            if self.globals.settings['popup_align'] == 'right':
                x = b_alloc.x + wx + b_alloc.width - width
            y = b_alloc.y + wy - offset
            # Check that the popup is within the monitor
            if x + width > mgeo.x + mgeo.width:
                x = mgeo.x + mgeo.width - width
            if x < mgeo.x:
                x = mgeo.x
            if y - height >= mgeo.y:
                direction = 'down'
                y = y - height
            else:
                direction = 'up'
                y = y + b_alloc.height + (offset * 2)
            p = wx + b_alloc.x + (b_alloc.width / 2) - x
        else:
            x = b_alloc.x + wx
            y = b_alloc.y + wy
            # Check that the popup is within the monitor
            if y + height > mgeo.y + mgeo.height:
                y = mgeo.y + mgeo.height - h
            if x + width >= mgeo.x + mgeo.width:
                direction = 'right'
                x = x - width - offset
            else:
                direction = 'left'
                x = x + b_alloc.width + offset
            p= wy + b_alloc.y + (b_alloc.height / 2) - y
        self.popup.point(direction, p)
        self.popup.move(x, y)

    #### Opacify
    def opacify(self):
        # Makes all windows but the one connected to this windowbutton
        # transparent
        if self.globals.opacity_values is None:
            try:
                self.globals.opacity_values = \
                            compiz_call('obs/screen0/opacity_values','get')
            except:
                try:
                    self.globals.opacity_values = \
                            compiz_call('core/screen0/opacity_values','get')
                except:
                    return
        if self.globals.opacity_matches is None:
            try:
                self.globals.opacity_matches = \
                            compiz_call('obs/screen0/opacity_matches','get')
            except:
                try:
                    self.globals.opacity_matches = \
                            compiz_call('core/screen0/opacity_matches','get')
                except:
                    return
        self.globals.opacified = True
        self.opacified = True
        ov = [self.globals.settings['opacify_alpha']]
        om = ["!(class=%s" % \
              self.windows.keys()[0].get_class_group().get_res_class() + \
              " | class=Dockbarx_factory.py) & (type=Normal | type=Dialog)"]
        try:
            compiz_call('obs/screen0/opacity_values','set', ov)
            compiz_call('obs/screen0/opacity_matches','set', om)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', ov)
                compiz_call('core/screen0/opacity_matches','set', om)
            except:
                return

    def opacify_request(self):
        if self.windows.get_unminimized_count() == 0:
            return False
        # Check if mouse cursor still is over the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            self.opacify()
        return False


    def deopacify(self):
        # always called from deopacify_request (with timeout)
        # If another window button has called opacify, don't deopacify.
        if self.globals.opacified and not self.opacified:
            return False
        if self.globals.opacity_values is None:
            return False
        try:
            compiz_call('obs/screen0/opacity_values','set',
                        self.globals.opacity_values)
            compiz_call('obs/screen0/opacity_matches','set',
                        self.globals.opacity_matches)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set',
                            self.globals.opacity_values)
                compiz_call('core/screen0/opacity_matches','set',
                            self.globals.opacity_matches)
            except:
                print "Error: Couldn't set opacity back to normal."
        self.globals.opacity_values = None
        self.globals.opacity_matches = None
        return False

    def deopacify_request(self):
        if not self.opacified:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            return True
        self.globals.opacified = False
        self.opacified = False
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        gobject.timeout_add(110, self.deopacify)
        return False

    #### DnD (source)
    def on_drag_begin(self, widget, drag_context):
        self.is_current_drag_source = True
        self.globals.dragging = True
        self.hide_list()

    def on_drag_data_get(self, widget, context,
                         selection, targetType, eventTime):
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        selection.set(selection.target, 8, name)


    def on_drag_end(self, widget, drag_context, result = None):
        self.is_current_drag_source = False
        # A delay is needed to make sure the button is
        # shown after button_drag_end has hidden it and
        # not the other way around.
        gobject.timeout_add(30, self.button.show)

    #### DnD (target)
    def on_drag_drop(self, wid, drag_context, x, y, t):
        if 'text/groupbutton_name' in drag_context.targets:
            self.button.drag_get_data(drag_context, 'text/groupbutton_name', t)
            drag_context.finish(True, False, t)
        elif 'text/uri-list' in drag_context.targets:
            #Drag data should already be stored in self.dd_uri
            if ".desktop" in self.dd_uri:
                # .desktop file! This is a potential launcher.
                if self.identifier:
                    name = self.identifier
                else:
                    name = self.desktop_entry.getFileName()
                #remove 'file://' and '/n' from the URI
                path = self.dd_uri[7:-2]
                path = path.replace("%20"," ")
                self.emit('launcher-dropped', path, name)
            else:
                uri = self.dd_uri
                # Remove the new line at the end
                uri = uri.rstrip()
                self.launch_item(None, None, uri)
            drag_context.finish(True, False, t)
        else:
            drag_context.finish(False, False, t)
        self.dd_uri = None
        return True

    def on_drag_data_received(self, wid, context,
                              x, y, selection, targetType, t):
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        if selection.target == 'text/groupbutton_name':
            if selection.data != name:
                self.emit('groupbutton-moved', selection.data, name)
        elif selection.target == 'text/uri-list':
            # Uri lists are tested on first motion instead on drop
            # to check if it's a launcher.
            # The data is saved in self.dd_uri to be used again
            # if the file is dropped.
            self.dd_uri = selection.data
            if ".desktop" in selection.data:
                # .desktop file! This is a potential launcher.
                self.launcher_drag = True
            self.update_state()

    def on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.button_drag_entered = True
            if not 'text/groupbutton_name' in drag_context.targets:
                win_nr = self.windows.get_count()
                if win_nr == 1:
                    self.dnd_select_window = gobject.timeout_add(600,
                                self.windows.values()[0].action_select_window)
                elif win_nr > 1:
                    self.dnd_show_popup = gobject.timeout_add(
                        self.globals.settings['popup_delay'], self.show_list)
            if 'text/groupbutton_name' in drag_context.targets \
            and not self.is_current_drag_source:
                self.launcher_drag = True
                self.update_state()
            elif 'text/uri-list' in drag_context.targets:
                # We have to get the data to find out if this
                # is a launcher or something else.
                self.button.drag_get_data(drag_context, 'text/uri-list', t)
                # No update_state() here!
            else:
                self.update_state()
        if 'text/groupbutton_name' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_MOVE, t)
        elif 'text/uri-list' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_COPY, t)
        else:
            drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.launcher_drag = False
        self.button_drag_entered = False
        self.update_state()
        self.hide_time = time()
        gobject.timeout_add(100, self.hide_list_request)
        if self.dnd_show_popup is not None:
            gobject.source_remove(self.dnd_show_popup)
            self.dnd_show_popup = None
        if self.dnd_select_window is not None:
            gobject.source_remove(self.dnd_select_window)
            self.dnd_select_window = None
        if self.is_current_drag_source:
            # If drag leave signal is given because of a drop,
            # a small delay is needed since
            # drag-end isn't called if
            # the destination is hidden just before
            # the drop is completed.
            gobject.timeout_add(20, self.button.hide)

    def on_popup_drag_motion(self, widget, drag_context, x, y, t):
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_popup_drag_leave(self, widget, drag_context, t):
        self.hide_time = time()
        gobject.timeout_add(100, self.hide_list_request)


    #### Events
    def on_sizealloc(self,applet,allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        if self.button_old_alloc != self.button.get_allocation():
            if self.globals.orient == "v" \
            and allocation.width>10 and allocation.width < 220 \
            and allocation.width != self.button_old_alloc.width:
                # A minimium size on 11 is set to stop unnecessary calls
                # work when the button is created
                self.icon_factory.set_size(allocation.width)
                self.update_state()
            elif self.globals.orient == "h" \
            and allocation.height>10 and allocation.height<220\
            and allocation.height != self.button_old_alloc.height:
                self.icon_factory.set_size(allocation.height)
                self.update_state()
            self.button_old_alloc = allocation

            # Update icon geometry
            self.set_icongeo()

    def on_button_mouse_enter (self, widget, event):
        if self.mouse_over:
            # False mouse enter event. Probably because a mouse button has been
            # pressed (compiz bug).
            return
        self.mouse_over = True
        self.update_state()
        if self.globals.settings["opacify"] and \
           self.globals.settings["opacify_group"]:
            gobject.timeout_add(self.globals.settings['popup_delay'],
                                self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(self.globals.settings['popup_delay'] + 500,
                                self.deopacify_request)

        win_cnt = self.windows.get_count()
        if  win_cnt == 0:
            return
        if win_cnt == 1 and \
           self.globals.settings['no_popup_for_one_window']:
            return
        # Prepare for popup window
        if not self.globals.right_menu_showing and not self.globals.dragging:
            if self.globals.gb_showing_popup is None:
                self.show_list_sid = \
                    gobject.timeout_add(self.globals.settings['popup_delay'],
                                        self.show_list_request)
            else:
                self.show_list_sid = \
                    gobject.timeout_add(
                                self.globals.settings['second_popup_delay'],
                                self.show_list_request)

    def on_button_mouse_leave (self, widget, event):
        if self.button.pointer_is_inside():
            # False mouse_leave event, the cursor might be on a screen edge
            # or the mouse has been clicked (compiz bug).
            # A timeout is set so that the real mouse leave won't be missed.
            gobject.timeout_add(50, self.on_button_mouse_leave, widget, event)
            return
        self.mouse_over = False
        self.pressed = False
        self.update_state()
        self.hide_time = time()
        self.hide_list_request()
        if self.globals.settings["opacify"] \
        and self.globals.settings["opacify_group"]:
            self.deopacify_request()

    def on_popup_mouse_leave (self,widget,event):
        self.hide_time = time()
        self.hide_list_request()

    def on_group_button_scroll_event (self,widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = self.globals.settings['groupbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = self.globals.settings['groupbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)

    def on_group_button_release_event(self, widget, event):
        self.pressed = False
        self.update_state()
        # If a drag and drop just finnished set self.draggin to false
        # so that left clicking works normally again
        if event.button == 1 and self.globals.dragging:
            self.globals.dragging = False
            return

        if not self.button.pointer_is_inside():
            return

        if not event.button in (1, 2, 3):
            return
        button = {1:'left', 2: 'middle', 3: 'right'}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = 'shift_and_'
        else:
            mod = ''
        if not self.globals.settings[
                                'groupbutton_%s%s_click_double'%(mod, button)]:
            # No double click required, go ahead and do the action.
            action = self.globals.settings[
                                'groupbutton_%s%s_click_action'%(mod, button)]
            self.action_function_dict[action](self, widget, event)


    def on_group_button_press_event(self,widget,event):
        if not event.button in (1, 2, 3):
            return True
        button = {1:'left', 2: 'middle', 3: 'right'}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = 'shift_and_'
        else:
            mod = ''
        if event.type == gtk.gdk._2BUTTON_PRESS:
            if self.globals.settings['groupbutton_%s%s_click_double'%(mod,
                                                                      button)]:
                # This is a double click and the
                # action requires a double click.
                # Go ahead and do the action.
                action = self.globals.settings[
                                'groupbutton_%s%s_click_action'%(mod, button)]
                self.action_function_dict[action](self, widget, event)

        elif event.button == 1:
            self.pressed = True
            self.update_state()
            # Return False so that a drag-and-drop can be initiated if needed.
            return False
        return True


    #### Menu
    def menu_show(self, event=None):
        if self.menu_is_shown:
            self.menu_is_shown = False
            self.popup.remove(self.popup.alignment.get_child())
            self.popup.add(self.popup_box)
            self.show_list()
            return

        self.menu_is_shown = True
        if self.popup.window:
            self.popup.window.property_change(ATOM_PREVIEWS,
                                              ATOM_PREVIEWS,
                                              32,
                                              gtk.gdk.PROP_MODE_REPLACE,
                                              [0,5,0,0,0,0,0])
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        menu = gtk.VBox()
        menu.set_spacing(2)
        if self.desktop_entry:
            #Launch program item
            launch_program_item = CairoMenuItem(_('_Launch application'))
            menu.pack_start(launch_program_item)
            launch_program_item.connect("clicked",
                                self.action_launch_application)
            launch_program_item.show()
        if self.desktop_entry and not self.pinned:
            #Add launcher item
            pin_item = CairoMenuItem(_('_Pin application'))
            menu.pack_start(pin_item)
            pin_item.connect("clicked", self.menu_pin)
            pin_item.show()
        if not self.pinned:
            #Make Custom Launcher item
            make_launcher_item = CairoMenuItem(_('Make custom launcher'))
            menu.pack_start(make_launcher_item)
            make_launcher_item.connect("clicked",
                                         self.menu_edit_launcher)
            make_launcher_item.show()
        if self.pinned:
            #Remove launcher item
            remove_launcher_item = CairoMenuItem(_('Unpin application'))
            menu.pack_start(remove_launcher_item)
            remove_launcher_item.connect("clicked",
                                         self.action_remove_launcher)
            remove_launcher_item.show()
            #Properties submenu
            properties_toggle = CairoToggleMenu(_('Properties'))
            menu.pack_start(properties_toggle)
            properties_toggle.show()
            properties_toggle.connect('toggled', self.on_toggle_menu_toggled)
            #Edit identifier item
            edit_identifier_item = CairoMenuItem(_('Edit Identifier'))
            properties_toggle.add_item(edit_identifier_item)
            edit_identifier_item.connect("clicked",
                                         self.menu_change_identifier)
            edit_identifier_item.show()
            #Edit launcher item
            edit_launcher_item = CairoMenuItem(_('Edit Launcher'))
            properties_toggle.add_item(edit_launcher_item)
            edit_launcher_item.connect("clicked",
                                       self.menu_edit_launcher)
            edit_launcher_item.show()

        #--- Recent and most used files
        if self.desktop_entry:
            recent_files, most_used_files, related_files = \
                                                    self.menu_get_zg_files()
            #Separator
            if recent_files or most_used_files or related_files:
                sep = gtk.SeparatorMenuItem()
                menu.pack_start(sep)
                sep.show()
            # Create and add the submenus.
            for files, menu_name in ((recent_files, _('Recent')),
                                      (most_used_files, _('Most used')),
                                      (related_files, _('Related'))):
                if files:
                    toggle_menu = CairoToggleMenu(menu_name)
                    menu.pack_start(toggle_menu)
                    toggle_menu.show()
                    toggle_menu.connect('toggled', self.on_toggle_menu_toggled)

                    for text, uri in files:
                        label = text or uri
                        if len(label)>40:
                            label = label[:20]+"..."+label[-17:]
                        toggle_menu_item = CairoMenuItem(label)
                        toggle_menu.add_item(toggle_menu_item)
                        toggle_menu_item.connect("clicked",
                                             self.launch_item, uri)
                        toggle_menu_item.show()

        # Windows stuff
        win_nr = self.windows.get_count()
        if win_nr:
            #Separator
            sep = gtk.SeparatorMenuItem()
            menu.pack_start(sep)
            sep.show()
            if win_nr == 1:
                t = ""
            else:
                t = _(" all windows")
            if self.windows.get_unminimized_count() == 0:
                # Unminimize all
                unminimize_all_windows_item = CairoMenuItem(
                                                '%s%s'%(_("Un_minimize"), t))
                menu.pack_start(unminimize_all_windows_item)
                unminimize_all_windows_item.connect("clicked",
                                              self.menu_unminimize_all_windows)
                unminimize_all_windows_item.show()
            else:
                # Minimize all
                minimize_all_windows_item = CairoMenuItem(
                                                    '%s%s'%(_("_Minimize"), t))
                menu.pack_start(minimize_all_windows_item)
                minimize_all_windows_item.connect("clicked",
                                            self.action_minimize_all_windows)
                minimize_all_windows_item.show()
            # (Un)Maximize all
            for window in self.windows:
                if not window.is_maximized() \
                and window.get_actions() & action_maximize:
                    maximize_all_windows_item = CairoMenuItem(
                                                    '%s%s'%(_("Ma_ximize"), t))
                    break
            else:
                maximize_all_windows_item = CairoMenuItem(
                                                '%s%s'%(_("Unma_ximize"), t))
            menu.pack_start(maximize_all_windows_item)
            maximize_all_windows_item.connect("clicked",
                                            self.action_maximize_all_windows)
            maximize_all_windows_item.show()
            # Close all
            close_all_windows_item = CairoMenuItem('%s%s'%(_("_Close"), t))
            menu.pack_start(close_all_windows_item)
            close_all_windows_item.connect("clicked",
                                           self.action_close_all_windows)
            close_all_windows_item.show()

        self.popup.remove(self.popup_box)
        self.popup.add(menu)
        menu.show()
        self.popup.show()
        self.popup.resize(10,10)
        # Hide other popup if open.
        if self.globals.gb_showing_popup is not None and \
           self.globals.gb_showing_popup != self:
            self.globals.gb_showing_popup.hide_list()
        self.globals.gb_showing_popup = self


    def menu_get_zg_files(self):
        # Get information from zeitgeist
        appname = self.desktop_entry.getFileName().split('/')[-1]
        recent_files = zg.get_recent_for_app(appname,
                                             days=30,
                                             number_of_results=8)
        most_used_files = zg.get_most_used_for_app(appname,
                                                   days=30,
                                                   number_of_results=8)
        # For programs that work badly with zeitgeist (openoffice for now),
        # mimetypes should be used to identify recent and most used as well.
        if self.identifier in zg.workrounds:
            if self.identifier == 'openoffice-writer' and \
               not self.globals.settings['separate_ooo_apps']:
                mimetypes = zg.workrounds['openoffice-writer'] + \
                            zg.workrounds['openoffice-calc'] + \
                            zg.workrounds['openoffice-presentation'] + \
                            zg.workrounds['openoffice-draw']
            else:
                mimetypes = zg.workrounds[self.identifier]
            recent_files += zg.get_recent_for_mimetypes(mimetypes,
                                                        days=30,
                                                        number_of_results=8)
            most_used_files += zg.get_most_used_for_mimetypes(mimetypes,
                                                              days=30,
                                                           number_of_results=8)
        # Related files contains files that can be used by the program and
        # has been used by other programs (but not this program) today.
        related_files = []
        try:
            mimetypes = self.desktop_entry.getMimeTypes()
        except AttributeError:
            mimetypes = None
        if mimetypes:
            related_candidates = zg.get_recent_for_mimetypes(mimetypes,
                                                             days=1,
                                                        number_of_results=20)
            other_recent = zg.get_recent_for_app(appname,
                                                 days=1,
                                                 number_of_results=20)
            related_files = [rf for rf in related_candidates \
                             if not (rf in recent_files or \
                                     rf in other_recent)]
            related_files = related_files[:3]
        return recent_files, most_used_files, related_files

    def on_toggle_menu_toggled(self, *args):
        self.popup.resize(10,10)


    def menu_unminimize_all_windows(self, widget=None, event=None):
        t = gtk.get_current_event_time()
        for window in self.windows.get_list():
            if window.is_minimized():
                window.unminimize(t)
        self.hide_list()

    def menu_change_identifier(self, widget=None, event=None):
        self.hide_list()
        self.emit('identifier-change',
                  self.desktop_entry.getFileName(), self.identifier)

    def menu_edit_launcher(self, widget=None, event=None):
        if self.desktop_entry:
            path = self.desktop_entry.getFileName()
        else:
            path = ""
        self.emit('edit-launcher-properties',
                  path, self.identifier)
        self.hide_list()

    def menu_pin(self, widget=None, event=None):
        self.pinned = True
        self.emit('pinned')
        self.hide_list()

    def launch_item(self, button, event, uri):
        self.desktop_entry.launch(uri)
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000,
                                                    self.remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000,
                                                    self.remove_launch_effect)

    #### Actions
    def action_select(self, widget, event):
        wins = self.windows.get_list()
        if (self.pinned and not wins):
            self.action_launch_application()
        # One window
        elif len(wins) == 1:
            sow = self.globals.settings["select_one_window"]
            if sow == "select window":
                self.windows[wins[0]].action_select_window(widget, event)
            elif sow == "select or minimize window":
                self.windows[wins[0]].action_select_or_minimize_window(widget,
                                                                       event)
            self.hide_list()
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
                umw = self.windows.get_unminimized()
                if len(umw) == 1:
                    sow = self.globals.settings["select_one_window"]
                    if sow == "select window":
                        self.windows[umw[0]].action_select_window(widget,
                                                                  event)
                        self.hide_list()
                    elif sow == "select or minimize window":
                        self.windows[umw[0]].action_select_or_minimize_window(
                                                                 widget, event)
                        self.hide_list()
                elif len(umw) == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif smw == "cycle through windows":
                self.action_select_next(widget, event)
            elif smw == "show popup":
                self.action_select_popup(widget, event)

    def action_select_popup(self, widget, event):
        if self.popup_showing is True:
            self.hide_list()
        else:
            self.show_list()

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if self.globals.settings['show_only_current_desktop']:
            mode = 'ignore'
        else:
            mode = self.globals.settings['workspace_behavior']
        screen = self.screen
        windows_stacked = screen.get_windows_stacked()
        grp_win_stacked = []
        ignorelist = []
        minimized_win_cnt = self.minimized_windows_count
        moved = False
        grtop = False
        wingr = False
        active_workspace = screen.get_active_workspace()
        self.hide_list()

        # Check if there are any uminimized windows, unminimize
        # them (unless they are on another workspace and work-
        # space behavior is somehting other than move) and
        # return.
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized():
                    ignored = False
                    if not win.is_pinned() \
                    and win.get_workspace() is not None \
                    and screen.get_active_workspace() != win.get_workspace():
                        if mode == 'move':
                            ws = screen.get_active_workspace()
                            win.move_to_workspace(ws)
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not ignored:
                        win.unminimize(event.time)
                        unminimized = True
        if unminimized:
            return

        # Make a list of the windows in group with the bottom most
        # first and top most last.
        # If mode is other than move
        # windows on other workspaces is put in a separate list instead.
        # grtop is set to true if not all windows in the group is the
        # topmost windows.
        for win in windows_stacked:
            if (not win.is_skip_tasklist()) and (not win.is_minimized()) \
            and (win.get_window_type() in [wnck.WINDOW_NORMAL,
                                           wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() \
                    and win.get_workspace() is not None \
                    and active_workspace != win.get_workspace():
                        if mode == 'move':
                            ws = screen.get_active_workspace()
                            win.move_to_workspace(ws)
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)

                    if not ignored:
                        grp_win_stacked.append(win)
                        if wingr == False:
                            wingr = True
                            grtop = True
                else:
                    if wingr:
                        grtop = False

        if not grp_win_stacked and mode == 'switch':
            # Put the windows in dictionaries according to workspace and
            # viewport so we can compare which workspace and viewport that
            # has most windows.
            workspaces ={}
            for win in self.windows:
                if win.get_workspace() is None:
                    continue
                workspace = win.get_workspace()
                win_x,win_y,win_w,win_h = win.get_geometry()
                vpx = win_x/screen.get_width()
                vpy = win_y/screen.get_height()
                if not workspace in workspaces:
                    workspaces[workspace] = {}
                if not vpx in workspaces[workspace]:
                    workspaces[workspace][vpx] = {}
                if not vpy in workspaces[workspace][vpx]:
                    workspaces[workspace][vpx][vpy] = []
                workspaces[workspace][vpx][vpy].append(win)
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
                        nr = len (vp)
                        if nr > max:
                            max = nr
                            x = screen.get_width() * xvp
                            y = screen.get_height() * yvp
                            new_workspace = workspace
                            grp_win_stacked = vp
                        elif nr == max:
                            # Check wether this workspace or previous workspace
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
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            if not (x == 0 and y == 0):
                self.hide_list()
            for win in grp_win_stacked:
                if win.is_minimized():
                    win.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            ordered_list = []
            #Bottommost window fist again.
            ignorelist.reverse()
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list

        if grtop and not moved and minimize:
            for win in grp_win_stacked:
                self.windows[win].window.minimize()
        delay = self.globals.settings['delay_on_select_all']
        win_nr = len(grp_win_stacked)
        if not grtop:
            for i in range(win_nr):
                grp_win_stacked[i].activate(event.time)
                if delay and i < win_nr - 1:
                    sleep(0.05)

    def action_select_only(self, widget, event):
        self.action_select_or_minimize_group(widget, event, False)

    def action_select_or_compiz_scale(self, widget, event):
        wins = self.windows.get_unminimized()
        if  len(wins) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
        self.hide_list()

    def action_minimize_all_windows(self,widget=None, event=None):
        for window in self.windows.get_list():
            window.minimize()
        self.hide_list()

    def action_maximize_all_windows(self,widget=None, event=None):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        maximized = False
        for window in self.windows.get_list():
            if not window.is_maximized() \
            and window.get_actions() & action_maximize:
                window.maximize()
                maximized = True
        if not maximized:
            for window in self.windows:
                window.unmaximize()
        self.hide_list()


    def action_select_next(self, widget=None, event=None, previous=False):
        if not self.windows.get_list():
            return
        if self.nextlist_time is None or time() - self.nextlist_time > 2 \
        or self.nextlist is None:
            self.nextlist = []
            minimized_list = []
            screen = self.screen
            windows_stacked = screen.get_windows_stacked()
            wins = self.windows.get_list()
            for win in windows_stacked:
                    if win in wins:
                        if win.is_minimized():
                            minimized_list.append(win)
                        else:
                            self.nextlist.append(win)
            # Reverse -> topmost window first
            self.nextlist.reverse()
            # Add minimized windows last.
            self.nextlist.extend(minimized_list)
        self.nextlist_time = time()

        if previous:
            win = self.nextlist.pop(-1)
            if win.is_active():
                self.nextlist.insert(0, win)
                win = self.nextlist.pop(-1)
        else:
            win = self.nextlist.pop(0)
            if win.is_active():
                self.nextlist.append(win)
                win = self.nextlist.pop(0)
        # Just a safety check
        if not win in self.windows:
            return
        self.windows[win].action_select_window(widget, event)
        if previous:
            self.nextlist.insert(0, win)
        else:
            self.nextlist.append(win)

    def action_select_previous(self, widget=None, event=None):
        self.action_select_next(widget, event, previous=True)

    def action_select_next_with_popup(self, widget=None,
                                      event=None, previous=False):
        self.show_list()
        self.action_select_next(widget, event, previous)
        if self.hide_list_sid is not None:
            gobject.source_remove(self.hide_list_sid)
        self.hide_time = time()
        self.hide_list_sid = gobject.timeout_add(2000,
                                                 self.hide_list_request)

    def action_close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        for window in self.windows.get_list():
            window.close(t)
        self.hide_list()

    def action_launch_application(self, widget=None, event=None):
        if self.lastlaunch is not None \
        and time() - self.lastlaunch < 2:
                return
        if self.desktop_entry:
            self.desktop_entry.launch()
        else:
            return
        self.lastlaunch = time()
        self.launch_effect = True
        self.update_state()
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000,
                                                    self.remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000,
                                                    self.remove_launch_effect)
        self.hide_list()


    def action_show_menu(self, widget, event):
        self.menu_show(event)

    def action_remove_launcher(self, widget=None, event=None):
        print 'Removing launcher ', self.identifier
        if self.identifier:
            name = self.identifier
        else:
            name = self.desktop_entry.getFileName()
        self.pinned = False
        if not self.windows:
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            self.emit('delete', name)
        else:
            self.emit('unpinned', name)
        self.hide_list()

    def action_minimize_all_other_groups(self, widget, event):
        self.hide_list()
        self.emit('minimize-others', self)
        self.hide_list()

    def action_compiz_scale_windows(self, widget, event):
        wins = self.windows.get_unminimized()
        if not wins:
            return
        self.hide_list()
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return
        if self.globals.settings['show_only_current_desktop']:
            path = 'scale/allscreens/initiate_key'
        else:
            path = 'scale/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                        'iclass=%s'%wins[0].get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay'] + 200,
                            self.hide_list)

    def action_compiz_shift_windows(self, widget, event):
        wins = self.windows.get_unminimized()
        if not wins:
            return
        self.hide_list()
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return

        if self.globals.settings['show_only_current_desktop']:
            path = 'shift/allscreens/initiate_key'
        else:
            path = 'shift/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                   'iclass=%s'%wins[0].get_class_group().get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay']+ 200,
                            self.hide_list)

    def action_compiz_scale_all(self, widget, event):
        try:
            compiz_call('scale/allscreens/initiate_key', 'activate',
                        'root', self.root_xid)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay']+ 200,
                            self.hide_list)
        self.hide_list()

    def action_dbpref (self,widget=None, event=None):
        # Preferences dialog
        self.emit('launch-preference')
        self.hide_list()

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
            ("remove launcher", action_remove_launcher),
            ("select next window", action_select_next),
            ("select previous window", action_select_previous),
            ("minimize all other groups", action_minimize_all_other_groups),
            ("compiz scale windows", action_compiz_scale_windows),
            ("compiz shift windows", action_compiz_shift_windows),
            ("compiz scale all", action_compiz_scale_all),
            ("show preference dialog", action_dbpref),
            ("no action", action_none)
            ))