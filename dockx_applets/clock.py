#!/usr/bin/python2

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

import gtk
import gobject
import time
import os
from dockbarx.applets import DockXApplet, DockXAppletDialog


DEFAULT_CUSTOM_FORMAT = \
            "<span foreground=\"#FFFFFF\" font=\"Sans 14\">%H:%M</span>"
DEFAULT_COMMAND = "orage"

class ClockApplet(DockXApplet):
    """A clock applet for DockbarX standalone dock"""
    applet_name = "Clock"
    applet_description  = "Shows the time."

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        alignment = gtk.Alignment(xalign=0.5, yalign=0.5)
        self.add(alignment)
        self.label = gtk.Label()
        self.label.set_use_markup(True)
        alignment.add(self.label)
        alignment.show_all()
        self.show()
        self.label_text = ""
        self.set_text_direction(self.get_setting("text_direction", "default"))
        self.font = self.get_setting("font", "Sans 14")
        self.color = self.get_setting("color", "#FFFFFF")
        self.show_date = self.get_setting("show_date", False)
        self.use_custom_format = self.get_setting("use_custom_format", False)
        self.custom_format = self.get_setting("custom_format",
                                              DEFAULT_CUSTOM_FORMAT)
        self.command = self.get_setting("command", DEFAULT_COMMAND)
        self.update()
        gobject.timeout_add(1000, self.update)
        self.connect("clicked", self.on_clicked)

        self.menu = gtk.Menu()
        preferences_item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences_item.connect('activate', self.open_preferences)
        self.menu.insert(preferences_item, 0)
        self.menu.show_all()
        
    def update(self, *args):
        if self.use_custom_format:
            # Todo: User made markup errors needs to be catched but how?
            text = time.strftime(self.custom_format)
            if text != self.label_text:
                self.label.set_label(text)
                self.label_text = text
            return True
        if self.show_date:
            tstr = time.strftime("%x %H:%M")
        else:
            tstr = time.strftime("%H:%M")
        text ="<span foreground=\"%s\" font=\"%s\">%s</span>" % (self.color,
                                                                 self.font,
                                                                 tstr)
        if text != self.label_text:
            self.label.set_label(text)
            self.label_text = text
        return True

    def on_setting_changed(self, key, value):
        if key == "font":
            self.font = value
        if key == "color":
            self.color = value
        if key == "show_date":
            self.show_date = value
        if key == "custom_format":
            self.custom_format = value
        if key == "use_custom_format":
            self.use_custom_format = value
        if key == "text_direction":
            self.set_text_direction(value)
        if key == "command":
            self.command = value
        self.update()

    def set_text_direction(self, direction):
        if direction == "default":
            if self.get_position() in ("left", "right"):
                direction = "top-down"
            else:
                direction = "left-right"
        angles = {"left-right": 0, "top-down": 270, "bottom-up": 90}
        self.label.set_angle(angles[direction])
        
    def on_clicked(self, widget, event):
        if event.button == 1:
            os.system("/bin/sh -c '%s' &" % self.command)
        elif event.button == 3:
            self.menu.popup(None, None, None, event.button, event.time)

    def open_preferences(self, *args):
        run_applet_dialog(self.APPLET_NAME)


class ClockAppletPreferences(DockXAppletDialog):
    Title = "Clock Applet Preferences"
    
    def __init__(self, applet_name):
        DockXAppletDialog.__init__(self, applet_name)
        table = gtk.Table(2, 3)
        self.vbox.pack_start(table)
        
        self.font_button = gtk.FontButton()
        self.font_button.set_use_font(True)
        self.font_button.set_use_size(True)
        self.font_button.set_show_style(True)
        label = gtk.Label(_("Font:"))
        table.attach(label, 0, 1, 0, 1)
        self.font_button.set_title(_("Clock font"))
        self.font_button.connect("font_set", self.__set_font)
        table.attach(self.font_button, 1, 2, 0, 1)
        
        label = gtk.Label(_("Color:"))
        table.attach(label, 0, 1, 1, 2)
        self.color_button = gtk.ColorButton()
        self.color_button.set_title(_("Font color"))
        self.color_button.connect("color-set",  self.__color_set)
        table.attach(self.color_button, 1, 2, 1, 2)

        self.date_cb = gtk.CheckButton(_("Show Date"))
        self.date_cb.connect("toggled", self.__cb_toggled, "show_date")
        table.attach(self.date_cb, 1, 2, 2, 3)

        frame = gtk.Frame()
        self.vbox.pack_start(frame)
        vbox = gtk.VBox()
        frame.add(vbox)
        self.custom_clock_cb = gtk.CheckButton(_("Use custom clock"))
        self.custom_clock_cb.connect("toggled",
                                     self.__cb_toggled, "use_custom_format")
        vbox.pack_start(self.custom_clock_cb)
        hbox = gtk.HBox()
        vbox.pack_start(hbox)
        self.cf_entry = gtk.Entry()
        self.cf_entry.set_tooltip_text("The format is identical to gnome-panel clock's custom format. Google 'gnome-panel custom clock' for exampels.")
        hbox.pack_start(self.cf_entry)
        self.cf_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_APPLY,
                                         gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.cf_button.add(image)
        self.cf_button.connect("clicked", self.__set_custom_format)
        hbox.pack_start(self.cf_button)

        hbox = gtk.HBox()
        self.vbox.pack_start(hbox)
        label = gtk.Label(_("Text direction: "))
        hbox.pack_start(label)
        self.td_cbt = gtk.combo_box_new_text()
        self.td_cbt.append_text(_("default"))
        self.td_cbt.append_text(_("left-right"))
        self.td_cbt.append_text(_("top-down"))
        self.td_cbt.append_text(_("bottom-up"))
        self.td_cbt.connect("changed",  self.__text_direction_changed)
        hbox.pack_start(self.td_cbt)
        
        self.show_all()

    def run(self):
        font = self.get_setting("font", "Sans 14")
        self.font_button.set_font_name(font)
        color = gtk.gdk.color_parse(self.get_setting("color", "#FFFFFF"))
        self.color_button.set_color(color)
        self.cf_entry.set_text(self.get_setting("custom_format",
                                                DEFAULT_CUSTOM_FORMAT))
        td = self.get_setting("text_direction", "default")
        tds = ["default", "left-right", "top-down", "bottom-up"]
        self.td_cbt.set_active(tds.index(td))
        cf = self.get_setting("use_custom_format", False)
        self.custom_clock_cb.set_active(cf)
        self.font_button.set_sensitive(not cf)
        self.color_button.set_sensitive(not cf)
        self.date_cb.set_sensitive(not cf)
        self.cf_entry.set_sensitive(cf)
        self.cf_button.set_sensitive(cf)          
        return DockXAppletDialog.run(self)
        
    def __set_font(self, button):
        self.set_setting("font", button.get_font_name())

    def __color_set(self, button):
        # Read the value from color (and alpha) and write
        # it as 8-bit/channel hex string for gconf.
        # (Alpha is written like int (0-255).)
        color = button.get_color().to_string()
        # cs has 16-bit per color, we want 8.
        color = color[0:3] + color[5:7] + color[9:11]
        self.set_setting("color", color)

    def __cb_toggled(self, button, key):
        self.set_setting(key, button.get_active())
        if key == "use_custom_format":
            cf = button.get_active()
            self.font_button.set_sensitive(not cf)
            self.color_button.set_sensitive(not cf)
            self.date_cb.set_sensitive(not cf)
            self.cf_entry.set_sensitive(cf)
            self.cf_button.set_sensitive(cf)

    def __set_custom_format(self, *args):
        self.set_setting("custom_format", self.cf_entry.get_text())

    def __text_direction_changed(self, cbt):
        text = cbt.get_active_text()
        direction = {_("default"): "default",
                     _("left-right"):"left-right",
                     _("top-down"):"top-down",
                     _("bottom-up"):"bottom-up"}.get(text, "default")
        self.set_setting("text_direction", direction)

# All applets needs to have this functions
def get_dbx_applet(dbx_dict):
    # This is the function that dockx will be calling.
    # Returns an instance of the applet.
    applet = ClockApplet(dbx_dict)
    return applet

def run_applet_dialog(name):
    dialog = ClockAppletPreferences(name)
    dialog.run()
    dialog.destroy()
        
