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
gi.require_version('Pango', '1.0')
from gi.repository import Pango
from gi.repository import GLib
import sys
import os
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck
from tarfile import open as taropen
from dockbarx.applets import DockXApplet

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from namebar.namebar_common import create_context_menu, PrefDialog

class WindowTitleApplet(DockXApplet):
    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.menu = create_context_menu(dbx_dict["id"])
        self.menu.show_all()

        self.connect("clicked", self.on_clicked)
        self.shown_window = None
        self.active_window = None
        self.aw_state_handler = None
        self.containerbox = None
        
        #~ Wnck.set_client_type(Wnck.CLIENT_TYPE_PAGER)
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        self.window_state = 'active'

        self.label = Gtk.Label()
        self.label_box = Gtk.EventBox()
        self.label_box.set_visible_window(False)
        self.label_box.add(self.label)
        self.label_box.connect("button-press-event",self.on_label_press_event)
        self.on_alignment_changed(self.get_setting("alignment"))

        self.repack()

        self.screen.connect("active-window-changed", self.on_active_window_changed)
        self.screen.connect("window-closed", self.on_window_closed)

        self.on_active_window_changed(self.screen)
        self.show()

    def repack(self):
        if self.containerbox:
            children = self.containerbox.get_children()
            for child in children:
                self.containerbox.remove(child)
            self.remove(self.containerbox)
            self.containerbox.destroy()
        if self.get_position() in ("left", "right"):
            self.containerbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
            self.label.set_angle(270)
            self.label.set_ellipsize(Pango.EllipsizeMode.NONE)
        else:
            self.containerbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
            self.label.set_angle(0)
            self.label.set_ellipsize(Pango.EllipsizeMode.END)
                
        self.containerbox.set_spacing(0)

        self.set_expand(self.get_setting("expand"))
        self.resize()
        self.add(self.containerbox)
        #~ self.containerbox.pack_start(self.icon_box, False)
        self.containerbox.pack_start(self.label_box, True, True, 2)
        self.containerbox.show_all()
        return

    def on_setting_changed(self, key, value):
        if key == "show_title":
            self.find_window_to_show()
        elif key == "expand":
            self.set_expand(value)
        elif key == "size":
            self.resize()
        elif key == "alignment":
            self.on_alignment_changed(value)
        elif key == "active_color" or key == "active_font" or \
             key == "passive_color" or key == "passive_font" or \
             key == "active_alpha" or key == "passive_alpha" or \
             key == "font_size":
            self.set_text_style()

    def on_alignment_changed(self, alignment):
        align = { "left / top": Gtk.Align.START,
                  "center": Gtk.Align.CENTER,
                  "right / bottom": Gtk.Align.END }
        if self.get_position() in ("left", "right"):
            self.label.set_valign(align[alignment])
        else:
            self.label.set_halign(align[alignment])

    def set_shown_window(self, window):
        if self.shown_window != None:
            if self.sw_name_changed_handler != None:
                self.shown_window.disconnect(self.sw_name_changed_handler)
            if self.sw_state_changed_handler != None:
                self.shown_window.disconnect(self.sw_state_changed_handler)
        self.shown_window = window
        self.sw_name_changed_handler = self.shown_window.connect('name-changed', self.on_window_name_changed)
        self.sw_state_changed_handler = self.shown_window.connect('state-changed', self.on_shown_window_state_changed)

        self.containerbox.show_all()
        name = ""+self.shown_window.get_name()
        self.label.set_tooltip_text(name)
        self.label.set_text(name)
        if self.shown_window == self.active_window \
        and self.window_state == 'passive':
            self.window_state = 'active'
        elif self.shown_window != self.active_window \
        and not self.window_state == 'passive':
            self.window_state = 'passive'

        self.set_text_style()

    def set_text_style(self):
        font = self.get_setting('%s_font'%self.window_state)
        color = self.get_setting('%s_color'%self.window_state)
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        if hasattr(Pango, "attr_font_desc_new") and hasattr(Pango, "attr_foreground_new"):
            attr_list = Pango.AttrList()
            attr_list.insert(Pango.attr_font_desc_new(Pango.FontDescription(font)))
            attr_list.insert(Pango.attr_foreground_new(r * 257, g * 257, b * 257))
            attr_list.insert(Pango.attr_foreground_alpha_new(self.get_setting('%s_alpha'%self.window_state) * 257))
            self.label.set_attributes(attr_list)
        else:
            hex_color = "#%02x%02x%02x" % (r, g, b)
            text = GLib.markup_escape_text(self.label.get_text(), -1)
            markup = '<span foreground="%s" font_desc="%s">%s</span>' % (hex_color, font, text)
            self.label.set_markup(markup)

    def show_none(self):
        if self.shown_window == None:
            return
        if self.sw_name_changed_handler != None:
            self.shown_window.disconnect(self.sw_name_changed_handler)
            self.sw_name_changed_handler = None
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
                return True
        if self.get_setting('show_title') == 'maximized':
            windows_stacked = self.screen.get_windows_stacked()
            for n in range(1,len(windows_stacked)+1):
                if windows_stacked[-n].is_maximized() \
                and not windows_stacked[-n].is_minimized() \
                and not windows_stacked[-n].is_skip_tasklist()\
                and (windows_stacked[-n].get_window_type() in [Wnck.WindowType.NORMAL,Wnck.WindowType.DIALOG]):
                    self.set_shown_window(windows_stacked[-n])
                    return True
        # No window found
        self.show_none()

    def resize(self):
        if self.get_setting("expand"):
            self.containerbox.set_size_request(-1, -1)
        else:
            if self.get_position() in ("left", "right"):
                self.containerbox.set_size_request(-1, self.get_setting('size'))
            else:
                self.containerbox.set_size_request(self.get_setting('size'), -1)

    #### Window Events
    def on_active_window_changed(self, screen, previous_active_window=None):
        # This function sets the state handler for the active window
        # and then calls find_window_to_show.
        if self.aw_state_handler != None:
            self.active_window.disconnect(self.aw_state_handler)
            self.aw_state_handler = None
        self.active_window = screen.get_active_window()
        if self.active_window != None and \
           not self.active_window.is_skip_tasklist() and \
           self.active_window.get_window_type() in [Wnck.WindowType.NORMAL,
                                                    Wnck.WindowType.DIALOG]:
            self.aw_state_handler = self.active_window.connect('state-changed', self.on_active_window_state_changed)
        self.find_window_to_show()


    def on_window_name_changed(self, window):
        name = ""+window.get_name()
        self.label.set_tooltip_text(name)
        self.label.set_text(name)

    def on_active_window_state_changed(self, window, changed_mask, new_state):
        if self.active_window != self.shown_window \
        and self.active_window.is_maximized():
            self.set_shown_window(self.active_window)

    def on_shown_window_state_changed(self, window, changed_mask, new_state):
        if self.shown_window == None:
            return
        if not self.shown_window.is_maximized() \
        and self.get_setting('show_title') == 'maximized':
            self.find_window_to_show()
        elif self.shown_window.is_minimized():
            self.find_window_to_show()

    def on_window_closed(self,screen,window):
        if window == self.shown_window:
            self.find_window_to_show()

    #### Mouse events
    def on_label_press_event(self, widget, event):
        if event.button ==1 \
        and self.shown_window != self.active_window:
            self.shown_window.activate(event.time)

    def on_clicked(self, widget, event):
        button = event.get_button().button
        if button == 3:
            self.menu.popup(None, None, None, None, button, event.time)

def get_dbx_applet(dbx_dict):
    wt_applet = WindowTitleApplet(dbx_dict)
    return wt_applet

def run_applet_dialog(applet_id):
    dialog = PrefDialog(applet_id)
    dialog.run()
    dialog.destroy()
