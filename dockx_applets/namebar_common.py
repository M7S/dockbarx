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

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
gi.require_version('Pango', '1.0')
from gi.repository import Pango
from tarfile import open as taropen
from dockbarx.applets import DockXAppletDialog
import dockbarx.i18n
_ = dockbarx.i18n.language.gettext

VERSION = '0.2'

namebar_appdir = None
def get_namebar_homedir():
    global namebar_appdir
    if namebar_appdir is not None:
        return namebar_appdir
    homedir = os.environ['HOME']
    default = os.path.join(homedir, '.local', 'share')
    namebar_appdir = os.path.join(
        os.getenv('XDG_DATA_HOME', default),
        'namebar'
    )
    """
    Migration Path
    From "$HOME/.namebar" to "${XDG_DATA_HOME:-$HOME/.local/share}/namebar"
    """
    old_appdir = os.path.join(homedir, '.namebar')
    if os.path.exists(old_appdir) and os.path.isdir(old_appdir):
        try:
            os.rename(old_appdir, namebar_appdir)
        except OSError:
            sys.stderr.write('Could not move dir "%s" to "%s". \
                     Move the contents of "%s" to "%s" manually \
                     and then remove the first location.'
                     % (old_appdir, namebar_appdir, old_appdir, namebar_appdir))
    """
    End Migration Path
    """
    return namebar_appdir


class Theme():
    @staticmethod
    def check(path_to_tar):
        tar = taropen(path_to_tar)
        try:
            for button in ('close', 'minimize', 'maximize'):
                # Try loading the pixbuf to if everything is OK
                f = tar.extractfile('active/%s_normal.png'%button)
                buffer=f.read()
                pixbuf_loader=GdkPixbuf.PixbufLoader()
                pixbuf_loader.write(buffer)
                pixbuf_loader.close()
                f.close()
                pixbuf_loader.get_pixbuf()
        except KeyError:
            tar.close()
            print("Nambar couldn't read the image %s from theme file %s"%('active/%s_normal.png'%button, path_to_tar))
            print("This theme will be ignored.")
            return False
        tar.close()
        return True

    def __init__(self, path_to_tar, angle=0):
        tar = taropen(path_to_tar)
        self.pixbufs = {}
        if angle == 0:
            self.angle = GdkPixbuf.PixbufRotation.NONE
        elif angle == 90:
            self.angle = GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE
        elif angle == 270:
            self.angle = GdkPixbuf.PixbufRotation.CLOCKWISE
        else:
            self.angle = GdkPixbuf.PixbufRotation.NONE

        no_passive_maximize = None
        for button in ('close', 'minimize', 'maximize', 'restore'):
            try:
                self.pixbufs['%s_normal_active'%button] = self.load_pixbuf(tar, 'active/%s_normal.png'%button)
            except:
                if button == 'restore':
                    self.pixbufs['%s_normal_active'%button] = self.pixbufs['maximize_normal_active']
                    self.pixbufs['%s_prelight_active'%button] = self.pixbufs['maximize_prelight_active']
                    self.pixbufs['%s_pressed_active'%button] = self.pixbufs['maximize_pressed_active']
                    self.pixbufs['%s_normal_passive'%button] = self.pixbufs['maximize_normal_passive']
                    self.pixbufs['%s_prelight_passive'%button] = self.pixbufs['maximize_prelight_passive']
                    self.pixbufs['%s_pressed_passive'%button] = self.pixbufs['maximize_pressed_passive']
                    continue
                else:
                    raise
            try:
                self.pixbufs['%s_prelight_active'%button] = self.load_pixbuf(tar, 'active/%s_prelight.png'%button)
            except:
                self.pixbufs['%s_prelight_active'%button] = self.pixbufs['%s_normal_active'%button]
            try:
                self.pixbufs['%s_pressed_active'%button] = self.load_pixbuf(tar, 'active/%s_pressed.png'%button)
            except:
                self.pixbufs['%s_pressed_active'%button] = self.pixbufs['%s_prelight_active'%button]

            try:
                self.pixbufs['%s_normal_passive'%button] = self.load_pixbuf(tar, 'passive/%s_normal.png'%button)
            except:
                if button == 'maximize':
                    no_passive_maximize = True
                if button == 'restore' and not no_passive_maximize:
                    self.pixbufs['%s_normal_passive'%button] = self.pixbufs['maximize_normal_passive']
                    self.pixbufs['%s_prelight_passive'%button] = self.pixbufs['maximize_prelight_passive']
                    self.pixbufs['%s_pressed_passive'%button] = self.pixbufs['maximize_pressed_passive']
                    continue
                self.pixbufs['%s_normal_passive'%button] = self.pixbufs['%s_normal_active'%button]
                self.pixbufs['%s_prelight_passive'%button] = self.pixbufs['%s_prelight_active'%button]
                self.pixbufs['%s_pressed_passive'%button] = self.pixbufs['%s_pressed_active'%button]
                continue
            try:
                self.pixbufs['%s_prelight_passive'%button] = self.load_pixbuf(tar, 'passive/%s_prelight.png'%button)
            except:
                self.pixbufs['%s_prelight_passive'%button] = self.pixbufs['%s_normal_passive'%button]
            try:
                self.pixbufs['%s_pressed_passive'%button] = self.load_pixbuf(tar, 'passive/%s_prelight.png'%button)
            except:
                self.pixbufs['%s_pressed_passive'%button] = self.pixbufs['%s_prelight_passive'%button]

        tar.close()

    def load_pixbuf(self, tar, name):
        f = tar.extractfile(name)
        buffer = f.read()
        pixbuf_loader = GdkPixbuf.PixbufLoader()
        pixbuf_loader.write(buffer)
        pixbuf_loader.close()
        f.close()
        pixbuf = pixbuf_loader.get_pixbuf()
        pixbuf = pixbuf.rotate_simple(self.angle)
        return pixbuf

    def get_pixbufs(self):
        return self.pixbufs


class AboutDialog(Gtk.AboutDialog):
    def __init__ (self):
        Gtk.AboutDialog.__init__(self)
        self.set_program_name("Namebar Applet")
        self.set_version(VERSION)
        self.set_logo_icon_name("dockbarx")
        self.set_copyright("Copyright (c) 2009, 2010 Matias S\xc3\xa4rs\nCopyright (c) 2020 Xu Zhen")

class PrefDialog(DockXAppletDialog):
    Title = "NameBar preferences"

    def __init__ (self, applet_id):
        DockXAppletDialog.__init__(self, applet_id, title=self.Title)

        frame = Gtk.Frame.new(_('Window Buttons'))
        frame.set_border_width(5)

        vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        frame.add(vbox)

        hbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        hbox.set_margin_bottom(5)
        label = Gtk.Label(label='Theme:')
        themes = self.find_themes()
        self.theme_combo = Gtk.ComboBoxText()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            label.set_margin_start(5)
            label.set_margin_end(5)
            self.theme_combo.set_margin_end(5)
        else:
            label.set_margin_left(5)
            label.set_margin_right(5)
            self.theme_combo.set_margin_right(5)
        for theme in list(themes.keys()):
                self.theme_combo.append_text(theme)
        self.theme_combo.connect('changed', self.cb_changed)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(self.theme_combo, True, True, 0)
        vbox.pack_start(hbox, True, True, 0)

        hbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        hbox.set_margin_bottom(5)
        self.use_custom_layout_cb = Gtk.CheckButton("Custom layout")
        self.use_custom_layout_cb.connect("toggled", self.checkbutton_toggled, ("use_custom_layout", False))
        hbox.pack_start(self.use_custom_layout_cb, False, False, 5)
        self.custom_layout_entry = Gtk.Entry()
        hbox.pack_start(self.custom_layout_entry, True, True, 0)
        self.custom_layout_button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("gtk-apply", Gtk.IconSize.SMALL_TOOLBAR)
        self.custom_layout_button.add(image)
        self.custom_layout_button.connect("clicked", self.set_custom_layout)
        hbox.pack_start(self.custom_layout_button, False, False, 1)
        self.reset_custom_layout_button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("edit-clear", Gtk.IconSize.SMALL_TOOLBAR)
        self.reset_custom_layout_button.add(image)
        self.reset_custom_layout_button.connect("clicked", self.reset_custom_layout)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            self.reset_custom_layout_button.set_margin_end(5)
        else:
            self.reset_custom_layout_button.set_margin_right(5)
        hbox.pack_start(self.reset_custom_layout_button, False, False, 1)

        vbox.pack_start(hbox, True, True, 0)

        self.vbox.pack_start(frame, False, False, 5)


        frame = Gtk.Frame.new(_('Window Title'))
        frame.set_border_width(5)

        table = Gtk.Grid()
        table.set_row_spacing(5)
        table.set_column_spacing(5)
        table.set_margin_bottom(5)
        row = 0
        label = Gtk.Label.new("Display")
        label.set_halign(Gtk.Align.END)
        self.show_title_cbt = Gtk.ComboBoxText()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            label.set_margin_start(5)
            self.show_title_cbt.set_margin_end(5)
        else:
            label.set_margin_left(5)
            self.show_title_cbt.set_margin_right(5)
        
        self.show_title_options = {_("Title of the active window"): "always",
                                   _("Title of the topmost maximized window"): "maximized"}
        show_title_options_ordered = [_("Title of the active window"), _("Title of the topmost maximized window")]
        for op in show_title_options_ordered:
            self.show_title_cbt.append_text(op)
        self.show_title_cbt.connect("changed", self.show_title_changed)
        table.attach(label, 0, row, 1, 1)
        table.attach(self.show_title_cbt, 1, row, 2, 1)

        # A directory of combobox names and the name of corresponding setting
        color_settings_and_labels = { "active": _('Active Color'),
                                      "passive": _('Passive Color')}
        font_settings_and_labels = { "active": _('Active Font'),
                                      "passive": _('Passive Font')}
        # A list to ensure that the order is kept correct
        color_font_labels = ['active', 'passive']
        self.color_buttons = {}
        self.color_clear_buttons = {}
        self.font_buttons = {}
        self.font_clear_buttons = {}
        for name in color_font_labels:
            row += 1
            text = font_settings_and_labels[name]
            label = Gtk.Label.new(text)
            self.font_button = Gtk.FontButton()
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
                label.set_margin_start(5)
            else:
                label.set_margin_left(5)
            label.set_halign(Gtk.Align.END)
            self.font_buttons[name] = Gtk.FontButton()
            self.font_buttons[name].set_use_font(True)
            self.font_buttons[name].set_use_size(False)
            self.font_buttons[name].set_show_size(True)
            self.font_buttons[name].set_show_style(True)
            self.font_buttons[name].set_hexpand(True)
            self.font_buttons[name].connect("font-set", self.font_set, name)
            self.font_clear_buttons[name] = Gtk.Button()
            image = Gtk.Image.new_from_icon_name("edit-clear", Gtk.IconSize.SMALL_TOOLBAR)
            self.font_clear_buttons[name].add(image)
            self.font_clear_buttons[name].connect("clicked", self.font_reset, name)
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
                self.font_clear_buttons[name].set_margin_end(5)
            else:
                self.font_clear_buttons[name].set_margin_right(5)
            table.attach(label, 0, row, 1, 1)
            table.attach(self.font_buttons[name], 1, row, 1, 1)
            table.attach(self.font_clear_buttons[name], 2, row, 1, 1)

            row += 1
            text = color_settings_and_labels[name]
            label = Gtk.Label.new(text)
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
                label.set_margin_start(5)
            else:
                label.set_margin_left(5)
            label.set_halign(Gtk.Align.END)
            self.color_buttons[name] = Gtk.ColorButton()
            self.color_buttons[name].set_title(text)
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 4:
                Gtk.ColorChooser.set_use_alpha(self.color_buttons[name], hasattr(Pango, "attr_foreground_alpha_new"))
            else:
                self.color_buttons[name].set_use_alpha(hasattr(Pango, "attr_foreground_alpha_new"))
            self.color_buttons[name].set_hexpand(True)
            self.color_buttons[name].connect("color-set", self.color_set, name)
            self.color_clear_buttons[name] = Gtk.Button()
            image = Gtk.Image.new_from_icon_name("edit-clear", Gtk.IconSize.SMALL_TOOLBAR)
            self.color_clear_buttons[name].add(image)
            self.color_clear_buttons[name].connect("clicked", self.color_reset, name)
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
                self.color_clear_buttons[name].set_margin_end(5)
            else:
                self.color_clear_buttons[name].set_margin_right(5)
            table.attach(label, 0, row, 1, 1)
            table.attach(self.color_buttons[name], 1, row, 1, 1)
            table.attach(self.color_clear_buttons[name], 2, row, 1, 1)

        row += 1
        label = Gtk.Label.new(_("Alignment"))
        label.set_halign(Gtk.Align.END)
        self.al_cbt = Gtk.ComboBoxText()
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            label.set_margin_start(5)
            self.al_cbt.set_margin_end(5)
        else:
            label.set_margin_left(5)
            self.al_cbt.set_margin_right(5)
        self.alignment_options = {_("Left / Top"): "left / top",
                                  _("Center"): "center",
                                  _("Right / Bottom"): "right / bottom" }
        alignment_options_order = [ _("Left / Top"), _("Center"), _("Right / Bottom") ]
        for op in alignment_options_order:
            self.al_cbt.append_text(op)
        self.al_cbt.connect("changed",  self.al_cbt_changed)
        table.attach(label, 0, row, 1, 1)
        table.attach(self.al_cbt, 1, row, 2, 1)

        row += 1
        self.expand_cb = Gtk.CheckButton(_('Expand in panel mode'))
        self.expand_cb.connect('toggled', self.checkbutton_toggled, ('expand', False))
        table.attach(self.expand_cb, 0, row, 3, 1)

        row += 1
        label = Gtk.Label.new(_("Size"))
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            label.set_margin_end(5)
        else:
            label.set_margin_right(5)
        label.set_halign(Gtk.Align.END)
        table.attach(label, 0, row, 1, 1)
        adj = Gtk.Adjustment(0, 100, 10000, 1, 50)
        self.size_spin = Gtk.SpinButton.new(adj, 0.5, 0)
        self.size_spin.set_hexpand(True)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 12:
            self.size_spin.set_margin_end(5)
        else:
            self.size_spin.set_margin_right(5)
        adj.connect("value_changed", self.spin_changed, self.size_spin)
        table.attach(self.size_spin, 1, row, 2, 1)

        frame.add(table)

        self.vbox.pack_start(frame, False, False, 5)

        self.update()
        self.show_all()

    def on_setting_changed(self, key, value):
        if key == "show_title":
            if value == 'always':
                self.show_title_cbt.set_active(0)
            elif value == 'maximized':
                self.show_title_cbt.set_active(1)
        elif key == "use_custom_layout":
            self.use_custom_layout_cb.set_active(value)
            self.custom_layout_entry.set_sensitive(value)
            self.custom_layout_button.set_sensitive(value)
            self.reset_custom_layout_button.set_sensitive(value)
        elif key == "custom_layout":
            self.custom_layout_entry.set_text(value)
        elif key == "expand":
            self.expand_cb.set_active(value)
            self.size_spin.set_sensitive(not value)
        elif key == "size":
            self.size_spin.set_value(value)
        elif key == "theme":
            model = self.theme_combo.get_model()
            for i in range(len(self.theme_combo.get_model())):
                if model[i][0] == value:
                    self.theme_combo.set_active(i)
                    break
        elif key == 'active_color' or key == "passive_color":
            state = key.split("_")[0]
            self.set_button_color(self.color_buttons[state], state, color=value)
        elif key == 'active_font' or key == "passive_font":
            state = key.split("_")[0]
            if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 2:
                Gtk.FontChooser.set_font(self.font_buttons[state], value)
            else:
                self.font_buttons[state].set_font_name(value)
        elif key == 'active_alpha' or key == "passive_alpha":
            state = key.split("_")[0]
            self.set_button_color(self.color_buttons[state], state, alpha=value)
        elif key == "alignment":
            alignments = [ "left / top", "center", "right / bottom" ]
            self.al_cbt.set_active(alignments.index(value))

    def set_button_color(self, button, state, color=None, alpha=None):
        if color is None:
            color = self.get_setting(state + "_color")
        if alpha is None:
            alpha = self.get_setting(state + "_alpha")
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 4:
            rgba = Gdk.RGBA()
            Gdk.RGBA.parse(rgba, color)
            rgba.alpha = alpha / 255
            Gtk.ColorChooser.set_rgba(button, rgba)
        else:
            button.set_color(Gdk.color_parse(color))
            button.set_alpha(alpha * 257)

    def update(self):
        prefs = ("show_title", "use_custom_layout", "custom_layout",
                 "expand", "size", "theme", "active_color",
                 "passive_color", "active_font", "passive_font",
                 "alignment")
        for pref in prefs:
            self.on_setting_changed(pref, self.get_setting(pref))

    def show_title_changed (self, cbt):
        text = cbt.get_active_text()
        value = self.show_title_options[text]
        self.set_setting('show_title', value)

    def checkbutton_toggled (self, button, userdata):
        self.set_setting(userdata[0], button.get_active(),
                         ignore_changed_event=userdata[1])

    def spin_changed(self, widget, spin):
        if spin == self.size_spin:
            value = spin.get_value_as_int()
            self.set_setting('size', value)

    def cb_changed(self, combobox):
        if combobox == self.theme_combo:
            value = combobox.get_active_text()
            if value == None:
                return
            self.set_setting('theme', value)

    def al_cbt_changed(self, cbt):
        text = cbt.get_active_text()
        alignment = self.alignment_options[text]
        self.set_setting("alignment", alignment)

    def set_custom_layout(self, *args):
        text = self.custom_layout_entry.get_text()
        self.set_setting("custom_layout", text)

    def reset_custom_layout(self, *args):
        self.set_setting("custom_layout", None, ignore_changed_event=False)

    def font_set(self, button, setting_base):
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 2:
            font = Gtk.FontChooser.get_font(button)
        else:
            font = button.get_font_name()
        self.set_setting(setting_base+"_font", font)

    def font_reset(self, button, setting_base):
        # Reset font setting to default.
        self.set_setting("%s_font" % setting_base, None, ignore_changed_event=False)

    def color_set(self, button, setting_base):
        # Read the value from color (and alpha) and write
        # it as 8-bit/channel hex string.
        # (Alpha is written like int (0-255).)
        if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 4:
            rgba = Gtk.ColorChooser.get_rgba(button)
            new_color = "#%02x%02x%02x" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))
            new_alpha = round(rgba.alpha * 255)
        else:
            color = button.get_color()
            alpha = button.get_alpha()
            cs = color.to_string()
            # cs has 16-bit per color, we want 8.
            new_color = cs[0:3] + cs[5:7] + cs[9:11]
            new_alpha = min(int(button.get_alpha() / 257), 255)
        self.set_setting(setting_base+"_color", new_color)
        self.set_setting(setting_base+"_alpha", new_alpha)

    def color_reset(self, button, setting_base):
        # Reset color setting to default.
        self.set_setting("%s_color" % setting_base, None, ignore_changed_event=False)
        self.set_setting("%s_alpha" % setting_base, None, ignore_changed_event=False)

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
        if not themes:
            md = Gtk.MessageDialog(None,
                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                'No working themes found in ' + ' or '.join(dirs))
            md.run()
            md.destroy()
            print('Preference dialog error: No working themes found in ' + ' or '.join(dirs))
        return themes


def create_context_menu(applet_id):
    menu = Gtk.Menu()
    if Gtk.MAJOR_VERSION > 3 or Gtk.MINOR_VERSION >= 10:
        pref_item = Gtk.MenuItem.new_with_mnemonic(_("_Preferences"))
        about_item = Gtk.MenuItem.new_with_mnemonic(_("_About"))
    else:
        pref_item = Gtk.ImageMenuItem(Gtk.STOCK_PREFERENCES)
        about_item = Gtk.ImageMenuItem(Gtk.STOCK_ABOUT)
    menu.append(pref_item)
    menu.append(about_item)
    pref_item.connect('activate', open_pref_dialog, applet_id)
    about_item.connect('activate', open_about_dialog)
    return menu

def open_pref_dialog(menuitem, applet_id):
    dialog = PrefDialog(applet_id)
    dialog.run()
    dialog.destroy()

def open_about_dialog(menuitem):
    dialog = AboutDialog()
    dialog.run()
    dialog.destroy()

