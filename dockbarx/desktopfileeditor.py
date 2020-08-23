#!/usr/bin/python3

#   Desktop File Editor for Dockbarx
#
#	Copyright 2020 Xu Zhen
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
#	along with dockbar.  If not, see <http://www.gnu.org/licenses/>

import configparser
import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from .log import logger
from . import i18n
_ = i18n.language.gettext


class DesktopFileEditor(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self, _("Edit Launcher"))
        self.config = configparser.ConfigParser(delimiters=('='))
        self.config.optionxform = str
        self.langs = os.environ.get("LANGUAGE")
        self.keymap = {}
        self.icon = None
        self.file = None
        if self.langs is not None:
            self.langs = self.langs.split(":")
        else:
            self.langs = []

        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        row = 0
        label = Gtk.Label.new(_("Name:"))
        label.set_halign(Gtk.Align.END)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_hexpand(True)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(self.name_entry, 1, row, 1, 1)
        row += 1
        label = Gtk.Label.new(_("Comment:"))
        label.set_halign(Gtk.Align.END)
        self.comment_entry = Gtk.Entry()
        self.comment_entry.set_hexpand(True)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(self.comment_entry, 1, row, 1, 1)
        row += 1
        label = Gtk.Label.new(_("Command:"))
        label.set_halign(Gtk.Align.END)
        self.command_entry = Gtk.Entry()
        self.command_entry.set_hexpand(True)
        self.command_entry.set_margin_end(5)
        self.command_button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("document-open", Gtk.IconSize.SMALL_TOOLBAR)
        self.command_button.set_image(image)
        self.command_button.set_hexpand(True)
        box = Gtk.HBox()
        box.pack_start(self.command_entry, True, True, 0)
        box.pack_start(self.command_button, False, True, 0)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(box, 1, row, 1, 1)
        row += 1
        label = Gtk.Label.new(_("Working Directory:"))
        label.set_halign(Gtk.Align.END)
        self.workdir_entry = Gtk.Entry()
        self.workdir_entry.set_hexpand(True)
        self.workdir_entry.set_margin_end(5)
        self.workdir_button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.SMALL_TOOLBAR)
        self.workdir_button.set_image(image)
        box = Gtk.HBox()
        box.pack_start(self.workdir_entry, True, True, 0)
        box.pack_start(self.workdir_button, False, True, 0)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(box, 1, row, 1, 1)
        row += 1
        label = Gtk.Label.new(_("Icon:"))
        label.set_halign(Gtk.Align.END)
        self.icon_button = Gtk.Button()
        self.icon_button.set_size_request(64, 64)
        box = Gtk.HBox()
        box.pack_start(self.icon_button, False, True, 0)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(box, 1, row, 1, 1)
        row += 1
        label = Gtk.Label.new(_("Options:"))
        label.set_halign(Gtk.Align.END)
        self.notification_check = Gtk.CheckButton.new_with_label(_("Use startup notification"))
        grid.attach(label, 0, row, 1, 1)
        grid.attach(self.notification_check, 1, row, 1, 1)
        row += 1
        self.terminal_check = Gtk.CheckButton.new_with_label(_("Run in terminal"))
        grid.attach(self.terminal_check, 1, row, 1, 1)

        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("Save"), Gtk.ResponseType.OK)

        self.command_dialog = Gtk.FileChooserDialog()
        self.command_dialog.set_title(_("Select an application"))
        self.command_dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_OK"), Gtk.ResponseType.OK)
        self.workdir_dialog = Gtk.FileChooserDialog()
        self.workdir_dialog.set_title(_("Select a working directory"))
        self.workdir_dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_OK"), Gtk.ResponseType.OK)
        self.workdir_dialog.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.icon_dialog = Gtk.FileChooserDialog()
        self.icon_dialog.set_title(_("Select an icon"))
        self.icon_dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_OK"), Gtk.ResponseType.OK)
        icon_filter = Gtk.FileFilter()
        icon_filter.add_pixbuf_formats()
        self.icon_dialog.set_filter(icon_filter)
        self.previewer = Gtk.Image()
        self.icon_dialog.set_preview_widget(self.previewer)
        self.icon_dialog.connect("update-preview", self.update_preview)

        self.command_button.connect("clicked", self.select_file, "command")
        self.workdir_button.connect("clicked", self.select_file, "workdir")
        self.icon_button.connect("clicked", self.select_image)

        self.set_resizable(False)
        box = self.get_content_area()
        box.pack_start(grid, True, True, 10)

    def select_file(self, button, name):
        dialog = getattr(self, name + "_dialog")
        entry = getattr(self, name + "_entry")
        action = dialog.run()
        if action == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.hide()

    def select_image(self, button):
        action = self.icon_dialog.run()
        if action == Gtk.ResponseType.OK:
            filename = self.icon_dialog.get_filename()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 64, 64)
            if pixbuf is None:
                return
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.icon_button.set_image(image)
            self.icon = filename
        self.icon_dialog.hide()

    def update_preview(self, chooser):
        filename = chooser.get_preview_filename()
        if filename is None or not os.path.isfile(filename):
            chooser.set_preview_widget_active(False)
            return
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 256, 256)
        if pixbuf is not None:
            image = chooser.get_preview_widget()
            image.set_from_pixbuf(pixbuf)
        chooser.set_preview_widget_active(pixbuf is not None)

    def load(self, filename):
        self.file = None
        if not os.path.exists(filename):
            return False
        try:
            self.config.read(filename)
        except:
            return False
        if self.get_item("Type") != "Application":
            return False
        self.file = filename
        self.name_entry.set_text(self.get_item("Name"))
        self.comment_entry.set_text(self.get_item("Comment"))
        self.command_entry.set_text(self.get_item("Exec"))
        self.workdir_entry.set_text(self.get_item("Path"))
        self.notification_check.set_active(self.get_item("StartupNotify") == "true")
        self.terminal_check.set_active(self.get_item("Terminal") == "true")
        icon = self.get_item("Icon")
        if icon.startswith("/"):
            pixbuf = GdkPixbuf.new_from_file_at_size(icon, 64, 64)
        else:
            icon_theme = Gtk.IconTheme.get_default()
            pixbuf = icon_theme.load_icon(icon, 64, 0)
        if pixbuf is not None:
            self.icon = icon
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.icon_button.set_image(image)
        return True

    def save(self, filename=None):
        if filename is None:
            filename = self.file
        if "Desktop Entry" not in self.config.sections():
            self.config["Desktop Entry"] = {}
        self.set_item("Name", self.name_entry.get_text())
        self.set_item("Comment", self.comment_entry.get_text())
        self.set_item("Exec", self.command_entry.get_text())
        self.set_item("Path", self.workdir_entry.get_text())
        self.set_item("StartupNotify", self.notification_check.get_active())
        self.set_item("Terminal", self.terminal_check.get_active())
        self.set_item("Icon", self.icon)
        try:
            f = open(filename, "w", encoding="utf-8")
            self.config.write(f, space_around_delimiters=False)
            f.close()
            return True
        except:
            logger.error("failed to save launcher: %s" % filename)
            return False

    def get_item(self, name):
        if name in ("Name", "Comment", "GenericName"):
            keys = [ name + "[%s]" % l for l in self.langs ]
            keys.append(name)
        else:
            keys = [ name ]
        for key in keys:
            try:
                text = self.config.get("Desktop Entry", key, raw=True)
            except:
                pass
            else:
                self.keymap[name] = key
                return text
        return ""

    def set_item(self, name, value):
        if name in self.keymap:
            name = self.keymap[name]
        try:
            if type(value) == bool:
                if value:
                    value = "true"
                else:
                    value = "false"
            if value is None or value == "":
                self.config.remove_option("Desktop Entry", name)
            else:
                text = self.config.set("Desktop Entry", name, value)
        except:
            pass
