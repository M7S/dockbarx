#!/usr/bin/python3

#	Copyright 2009, 2010 Matias Sars
#	Copyright 2020 Xu Zhen
#
#	Namebar applet is free software: you can redistribute it and/or modify
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
#	along with Namebar.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import Pango
import sys
import os
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck
from dockbarx.applets import DockXApplet
import dockbarx.i18n
_ = dockbarx.i18n.language.gettext

from pathlib import Path
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))
from applets.namebar_common import get_namebar_homedir, create_context_menu, PrefDialog, Theme

try:
    action_minimize = Wnck.WindowType.ACTION_MINIMIZE
    action_unminimize = Wnck.WindowType.ACTION_UNMINIMIZE
    action_maximize = Wnck.WindowType.ACTION_MAXIMIZE
except:
    action_minimize = 1 << 12
    action_unminimize = 1 << 13
    action_maximize = 1 << 14

class WindowButtonApplet(DockXApplet):
    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.menu = create_context_menu(dbx_dict["id"])
        self.menu.show_all()

        self.shown_window = None
        self.active_window = None
        self.aw_state_handler = None
        
        #~ Wnck.set_client_type(Wnck.CLIENT_TYPE_PAGER)
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        self.button_layout = self.get_setting("custom_layout")

        self.window_state = 'active'
        self.max_icon_state = 'restore'
        
        self.containerbox = None
        
        self.minimize_button = Gtk.EventBox()
        self.minimize_button.set_visible_window(False)
        self.minimize_image = Gtk.Image()
        self.minimize_button.add(self.minimize_image)
        self.minimize_button.connect("enter-notify-event", self.on_button_mouse_enter)
        self.minimize_button.connect("leave-notify-event", self.on_button_mouse_leave)
        self.minimize_button.connect("button-release-event", self.on_button_release_event)
        self.minimize_button.connect("button-press-event", self.on_button_press_event)

        self.maximize_button = Gtk.EventBox()
        self.maximize_button.set_visible_window(False)
        self.maximize_image = Gtk.Image()
        self.maximize_button.add(self.maximize_image)
        self.maximize_button.connect("enter-notify-event", self.on_button_mouse_enter)
        self.maximize_button.connect("leave-notify-event", self.on_button_mouse_leave)
        self.maximize_button.connect("button-release-event", self.on_button_release_event)
        self.maximize_button.connect("button-press-event", self.on_button_press_event)

        self.close_button = Gtk.EventBox()
        self.close_button.set_visible_window(False)
        self.close_image = Gtk.Image()
        self.close_button.add(self.close_image)
        self.close_button.connect("enter-notify-event", self.on_button_mouse_enter)
        self.close_button.connect("leave-notify-event", self.on_button_mouse_leave)
        self.close_button.connect("button-release-event", self.on_button_release_event)
        self.close_button.connect("button-press-event", self.on_button_press_event)

        #--- Load theme
        self.change_theme(self.get_setting('theme'))

        self.repack()

        self.screen.connect("active-window-changed", self.on_active_window_changed)
        self.screen.connect("window-closed", self.on_window_closed)

        self.on_active_window_changed(self.screen)
        self.show()

    def repack(self):
        if self.containerbox is not None:
            children = self.containerbox.get_children()
            for child in children:
                self.containerbox.remove(child)
            self.remove(self.containerbox)
            self.containerbox.destroy()

        if self.get_position() in ("left", "right"):
            self.containerbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        else:
            self.containerbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        self.containerbox.set_spacing(0)
        self.containerbox.show()
        self.add(self.containerbox)

        pack_dict = { 'minimize': self.minimize_button,
                      'maximize': self.maximize_button,
                      'close': self.close_button }
        if self.get_setting("use_custom_layout"):
            layout = self.get_setting("custom_layout")
        else:
            layout = self.button_layout
        pack_strs = layout.split(':')
        start_list = pack_strs[0].split(',')
        for item in start_list:
            if item in pack_dict:
                self.containerbox.pack_start(pack_dict[item], False, False, 0)
        try:
            end_list = pack_strs[1].split(',')
        except IndexError:
            pass
        else:
            end_list.reverse()
            for item in end_list:
                if item in pack_dict:
                    self.containerbox.pack_end(pack_dict[item], False, False, 0)

    def find_themes(self):
        # Reads the themes from /usr/share/namebar/themes and
        # ${XDG_DATA_HOME:-$HOME/.local/share}/namebar/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        dirs = [os.path.join(os.path.dirname(__file__), "namebar_themes"),
                os.path.join(get_namebar_homedir(), "themes")]
        for dir in dirs:
            if os.path.exists(dir):
                for f in os.listdir(dir):
                    if f[-7:] == '.tar.gz':
                        theme_paths.append(dir+"/"+f)
        for theme_path in theme_paths:
            if Theme.check(theme_path):
                name = theme_path.split('/')[-1][:-7]
                themes[name] = theme_path
        return themes

    def change_theme(self, pref_theme):
        self.themes = self.find_themes()
        if len(self.themes) == 0:
            logger.error("No themes found for namebar!")
            return
        path = self.themes.get(pref_theme)
        if path is None:
            # try the default theme
            path = self.themes.get(self.get_default_setting("theme"))
            if path is None:
                # Just use one of the themes
                path = list(self.themes.values())[0]

        if self.get_position() in ("left", "right"):
            angle = 270
        else:
            angle = 0
        self.theme = Theme(path, angle)
        self.pixbufs = self.theme.get_pixbufs()
        self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_normal_%s'%self.window_state])
        self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
        self.close_image.set_from_pixbuf(self.pixbufs['close_normal_%s'%self.window_state])

    def on_setting_changed(self, key, value):
        if key == 'custom_layout':
            if self.get_setting('use_custom_layout'):
                self.repack()
        elif key == 'use_custom_layout':
            self.repack()
        elif key == 'theme':
            self.change_theme(value)
        elif key == "show_title":
            self.on_active_window_changed(self.screen)

    def set_shown_window(self, window):
        if self.shown_window != None:
            if self.sw_state_changed_handler != None:
                self.shown_window.disconnect(self.sw_state_changed_handler)
        self.shown_window = window
        self.sw_state_changed_handler = self.shown_window.connect('state-changed', self.on_shown_window_state_changed)

        self.containerbox.show_all()
        if self.shown_window.get_actions() & action_minimize:
            self.minimize_button.show()
        else:
            self.minimize_button.hide()
        if self.shown_window.is_maximized():
            self.max_icon_state = 'restore'
            if self.shown_window.get_actions() & action_unminimize:
                self.maximize_button.show()
            else:
                self.maximize_button.hide()
        else:
            self.max_icon_state = 'maximize'
            if self.shown_window.get_actions() & action_maximize:
                self.maximize_button.show()
            else:
                self.maximize_button.hide()
        if self.shown_window == self.active_window \
        and self.window_state == 'passive':
            self.window_state = 'active'
            self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_normal_%s'%self.window_state])
            self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
            self.close_image.set_from_pixbuf(self.pixbufs['close_normal_%s'%self.window_state])
        elif self.shown_window != self.active_window \
        and not self.window_state == 'passive':
            self.window_state = 'passive'
            self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_normal_%s'%self.window_state])
            self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
            self.close_image.set_from_pixbuf(self.pixbufs['close_normal_%s'%self.window_state])

    def show_none(self):
        if self.shown_window == None:
            return
        if self.sw_state_changed_handler != None:
            self.shown_window.disconnect(self.sw_state_changed_handler)
            self.sw_state_changed_handler = None
        self.shown_window = None
        self.containerbox.hide()

    def find_window_to_show(self):
        # Tries to find a window to show on Namebar.
        if self.active_window != None \
        and self.get_setting('show_title') == 'always' \
        and not self.active_window.is_skip_tasklist() \
        and (self.active_window.get_window_type() in [Wnck.WindowType.NORMAL,Wnck.WindowType.DIALOG]):
                self.set_shown_window(self.active_window)
                return
        if self.get_setting('show_title') == 'maximized':
            windows_stacked = self.screen.get_windows_stacked()
            for n in range(1,len(windows_stacked)+1):
                if windows_stacked[-n].is_maximized() \
                and not windows_stacked[-n].is_minimized() \
                and not windows_stacked[-n].is_skip_tasklist()\
                and (windows_stacked[-n].get_window_type() in [Wnck.WindowType.NORMAL,Wnck.WindowType.DIALOG]):
                    self.set_shown_window(windows_stacked[-n])
                    return
        # No window found
        self.show_none()

    #### Window Events
    def on_active_window_changed(self, screen, previous_active_window=None):
        # This function sets the state handler for the active window
        # and then calls find_window_to_show.
        if self.aw_state_handler != None:
            self.active_window.disconnect(self.aw_state_handler)
            self.aw_state_handler = None
        self.active_window = screen.get_active_window()
        if self.active_window != None and not self.active_window.is_skip_tasklist() \
        and (self.active_window.get_window_type() in [Wnck.WindowType.NORMAL,Wnck.WindowType.DIALOG]):
            self.aw_state_handler = self.active_window.connect('state-changed', self.on_active_window_state_changed)
        self.find_window_to_show()

    def on_active_window_state_changed(self, window, changed_mask, new_state):
        if self.active_window != self.shown_window \
        and self.active_window.is_maximized():
            self.set_shown_window(self.active_window)

    def on_shown_window_state_changed(self, window, changed_mask, new_state):
        if self.shown_window == None:
            return
        if self.get_setting('show_title') == 'always':
            if self.shown_window.is_maximized() \
            and self.max_icon_state == "maximize":
                self.max_icon_state = "restore"
                self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
            if not self.shown_window.is_maximized() \
            and self.max_icon_state == "restore":
                self.max_icon_state = "maximize"
                self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
        if not self.shown_window.is_maximized() \
        and self.get_setting('show_title') == 'maximized':
            self.find_window_to_show()
        elif self.shown_window.is_minimized():
            self.find_window_to_show()

    def on_window_closed(self,screen,window):
        if window == self.shown_window:
            self.find_window_to_show()

    #### Mouse events
    def on_button_release_event(self, widget, event):
        # Checks if the mouse pointer still is over the button and does the
        # minimze/maximize/unmaximize/close action and changes the icon back
        # to prelight if it does.
        x,y = widget.get_pointer()
        a = widget.get_allocation()
        if (x >= 0 and x < a.width) and (y >= 0 and y < a.height):
            if event.button == 1:
                if widget == self.minimize_button:
                    self.shown_window.minimize()
                    self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_prelight_%s'%self.window_state])
                if widget == self.maximize_button:
                    if self.shown_window.is_maximized():
                        self.max_icon_state = 'maximize'
                        self.shown_window.unmaximize()
                    else:
                        self.max_icon_state = 'restore'
                        self.shown_window.maximize()
                    self.maximize_image.set_from_pixbuf(self.pixbufs['%s_prelight_%s'%(self.max_icon_state, self.window_state)])
                if widget == self.close_button:
                    self.shown_window.close(event.time)
                    self.close_image.set_from_pixbuf(self.pixbufs['close_prelight_%s'%self.window_state])
            elif event.button == 3:
                self.menu.popup(None, None, None, None, event.button, event.time)

    def on_button_press_event(self, widget, event):
        # Change the image to "pressed".
        if event.button ==1:
            if widget == self.minimize_button:
                self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_pressed_%s'%self.window_state])
            if widget == self.maximize_button:
                self.maximize_image.set_from_pixbuf(self.pixbufs['%s_pressed_%s'%(self.max_icon_state, self.window_state)])
            if widget == self.close_button:
                self.close_image.set_from_pixbuf(self.pixbufs['close_pressed_%s'%self.window_state])

    def on_button_mouse_enter(self, widget, event):
        # Change the button's image to "prelight".
        if widget == self.minimize_button:
            self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_prelight_%s'%self.window_state])
        if widget == self.maximize_button:
            self.maximize_image.set_from_pixbuf(self.pixbufs['%s_prelight_%s'%(self.max_icon_state, self.window_state)])
        if widget == self.close_button:
            self.close_image.set_from_pixbuf(self.pixbufs['close_prelight_%s'%self.window_state])

    def on_button_mouse_leave(self, widget, event):
        # Chagenge the button's image to "normal".
        if widget == self.minimize_button:
            self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_normal_%s'%self.window_state])
        if widget == self.maximize_button:
            self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
        if widget == self.close_button:
            self.close_image.set_from_pixbuf(self.pixbufs['close_normal_%s'%self.window_state])

def get_dbx_applet(dbx_dict):
    wb_applet = WindowButtonApplet(dbx_dict)
    return wb_applet

def run_applet_dialog(applet_id):
    dialog = PrefDialog(applet_id)
    dialog.run()
    dialog.destroy()
