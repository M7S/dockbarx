#!/usr/bin/python3

#   Hello world dockbarx applet
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
from gi.repository import GLib
from dockbarx.applets import DockXApplet, DockXAppletDialog 

class HelloWorldApplet(DockXApplet):
    """An example applet for DockbarX standalone dock"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        text = self.get_setting("text")
        self.label = Gtk.Label()
        self.update_text(text)
        
        # DockXApplet base class is pretty much a Gtk.EventBox.
        # so all you have to do is adding your widget with self.add()
        self.add(self.label)

        self.connect("clicked", self.on_clicked)
        self.label.show()
        self.show()

    def update_text(self, text):
        text = GLib.markup_escape_text(text, -1)
        self.label.set_markup('<span foreground="#FFFFFF" background="#000000">%s</span>' % text)

    def on_setting_changed(self, key, value):
        # self.debug((key, value))
        if key == "text":
            self.update_text(value)

    def on_clicked(self, applet, event):
        run_applet_dialog(self.get_id())

class HelloWorldPreferences(DockXAppletDialog):
    Title = "Hello World Applet Preference"
    
    def __init__(self, applet_id):
        DockXAppletDialog.__init__(self, applet_id, title=self.Title)
        self.setting = False

        hbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)

        self.label = Gtk.Label("Text:")
        hbox.pack_start(self.label, False, False, 0)
        
        self.entry = Gtk.Entry()
        text = self.get_setting("text")
        self.entry.set_text(text)
        self.entry.connect("changed", self.save_text)
        hbox.pack_start(self.entry, False, False, 5)

        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 10:
            self.button = Gtk.Button.new_from_icon_name("edit-clear", Gtk.IconSize.BUTTON);
        else:
            self.button = Gtk.Button.new_from_stock(Gtk.STOCK_CLEAR);
        self.button.connect("clicked", self.reset_to_default_text)
        self.button.show()
        hbox.pack_start(self.button, True, True, 0)
        
        self.vbox.pack_start(hbox, False, False, 0)
        self.vbox.show_all()

    def run(self):
        DockXAppletDialog.run(self)

    def save_text(self, entry):
        text = self.entry.get_text()
        self.setting = True
        self.set_setting("text", text)
        self.setting = False
        pass

    def on_setting_changed(self, key, value):
        # self.debug((key, value))
        if self.setting:
            return
        if key == "text":
            self.entry.set_text(value)

    def reset_to_default_text(self, button):
        self.setting = True
        text = self.set_setting("text", None)
        self.entry.set_text(self.get_setting("text"))
        self.setting = False


# All applets needs to have this function
def get_dbx_applet(dbx_dict):
    # This is the function that dockx will be calling.
    # Returns an instance of the applet.
    applet = HelloWorldApplet(dbx_dict)
    return applet


def run_applet_dialog(applet_id):
    dialog = HelloWorldPreferences(applet_id)
    dialog.run()
    dialog.destroy()
        
