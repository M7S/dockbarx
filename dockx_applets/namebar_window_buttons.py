#!/usr/bin/python2

#	Copyright 2009, 2010 Matias Sars
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

import pygtk
pygtk.require('2.0')
import gtk
import pango
import sys
import os
import wnck
import gconf
from tarfile import open as taropen
from dockbarx.applets import DockXApplet, DockXAppletDialog

VERSION = '0.1'

GCONF_CLIENT = gconf.client_get_default()
GCONF_DIR = '/apps/namebar'

DEFAULT_SETTINGS = { 'theme': 'Dust-ish',
                     'show_title':'maximized',
                     'expand': True,
                     'size': 500,
                     'show_buttons': True,
                     'active_color': "#EEEEEE",
                     'passive_color': "#AAAAAA",
                     'active_bold': False,
                     'passive_bold': False,
                     'alignment': 0,
                     'use_custom_layout': False,
                     'custom_layout': "menu:minimize,maximize,close"}
settings = DEFAULT_SETTINGS.copy()

PREFDIALOG = None # Warning non-constant!

try:
    action_minimize = wnck.WINDOW_ACTION_MINIMIZE
    action_unminimize = wnck.WINDOW_ACTION_UNMINIMIZE
    action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
except:
    action_minimize = 1 << 12
    action_unminimize = 1 << 13
    action_maximize = 1 << 14

class AboutDialog():
    __instance = None

    def __init__ (self):
        if AboutDialog.__instance == None:
            AboutDialog.__instance = self
        else:
            AboutDialog.__instance.about.present()
            return
        self.about = gtk.AboutDialog()
        self.about.set_name("Namebar Applet")
        self.about.set_version(VERSION)
        self.about.set_copyright("Copyright (c) 2009, 2010 Matias S\xc3\xa4rs")
        self.about.connect("response",self.about_close)
        self.about.show()

    def about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None

class PrefDialog():
    __instance = None

    def __init__ (self, namebar=None):
        global PREFDIALOG
        if PrefDialog.__instance == None:
            PrefDialog.__instance = self
        else:
            PrefDialog.__instance.dialog.present()
            return

        PREFDIALOG = self
        self.dialog = gtk.Dialog("WindowButtonApplet preferences")
        self.dialog.connect("response",self.dialog_close)

        self.namebar= namebar

        try:
            ca = self.dialog.get_content_area()
        except:
            ca = self.dialog.vbox
        l1 = gtk.Label("<big>Behavior</big>")
        l1.set_alignment(0,0.5)
        l1.set_use_markup(True)
        ca.pack_start(l1,False)

        self.rb1_1 = gtk.RadioButton(None,"Show buttons for the active window")
        self.rb1_1.connect("toggled",self.rb_toggled,"rb1_always")
        self.rb1_2 = gtk.RadioButton(self.rb1_1,"Show buttons for the topmost maximized window")
        self.rb1_2.connect("toggled",self.rb_toggled,"rb1_maximized")
        ca.pack_start(self.rb1_1,False)
        ca.pack_start(self.rb1_2,False)

        l1 = gtk.Label("<big>Layout</big>")
        l1.set_alignment(0,0.5)
        l1.set_use_markup(True)
        ca.pack_start(l1,False)

        hbox = gtk.HBox()
        ca.pack_start(hbox)
        self.use_custom_layout_cb = gtk.CheckButton("Use custom button layout")
        self.use_custom_layout_cb.connect("toggled", self.checkbutton_toggled, "use_custom_layout")
        hbox.pack_start(self.use_custom_layout_cb)
        self.custom_layout_entry = gtk.Entry()
        hbox.pack_start(self.custom_layout_entry)
        self.custom_layout_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_APPLY,
                                         gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.custom_layout_button.add(image)
        self.custom_layout_button.connect("clicked", self.set_custom_layout)
        hbox.pack_start(self.custom_layout_button)

        #Themes
        hbox = gtk.HBox()
        label = gtk.Label('Theme:')
        label.set_alignment(1,0.5)
        themes = self.find_themes()
        self.theme_combo = gtk.combo_box_new_text()
        for theme in themes.keys():
                self.theme_combo.append_text(theme)
        self.theme_combo.connect('changed', self.cb_changed)
        button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_SMALL_TOOLBAR)
        button.add(image)
        button.connect("clicked", self.change_theme)
        hbox.pack_start(label, False)
        hbox.pack_start(self.theme_combo, False)
        hbox.pack_start(button, False)
        ca.pack_start(hbox)


        self.update()

        self.dialog.add_button(gtk.STOCK_CLOSE,gtk.RESPONSE_CLOSE)
        self.dialog.show_all()

    def update(self):
        self.settings_show_title = settings['show_title']
        if self.settings_show_title == 'always':
            self.rb1_1.set_active(True)
        elif self.settings_show_title == 'maximized':
            self.rb1_2.set_active(True)

        self.use_custom_layout_cb.set_active(settings["use_custom_layout"])
        self.custom_layout_entry.set_text(settings["custom_layout"])
        sensitive = settings["use_custom_layout"]
        self.custom_layout_entry.set_sensitive(sensitive)

        # Themes
        model = self.theme_combo.get_model()
        for i in range(len(self.theme_combo.get_model())):
            if model[i][0] == settings['theme']:
                self.theme_combo.set_active(i)
                break

    def dialog_close (self,par1,par2):
        global PREFDIALOG
        PREFDIALOG = None
        self.dialog.destroy()
        PrefDialog.__instance = None

    def rb_toggled (self, button, par1):
        if par1 == 'rb1_always' and button.get_active():
            self.settings_show_title  = 'always'
        if par1 == 'rb1_maximized' and button.get_active():
            self.settings_show_title  = 'maximized'

        if self.settings_show_title != settings['show_title']:
            GCONF_CLIENT.set_string("%s/show_title" % GCONF_DIR, self.settings_show_title)

    def checkbutton_toggled (self,button,name):
        if button.get_active() != settings[name]:
            GCONF_CLIENT.set_bool(GCONF_DIR+'/'+name, button.get_active())

    def cb_changed(self, combobox):
        if combobox == self.theme_combo:
            value = combobox.get_active_text()
            if value == None:
                return
            if value != settings['theme']:
                GCONF_CLIENT.set_string("%s/theme" % GCONF_DIR, value)

    def set_custom_layout(self, *args):
        text = self.custom_layout_entry.get_text()
        if text != settings["custom_layout"]:
            GCONF_CLIENT.set_string("%s/custom_layout" % GCONF_DIR, text)

    def find_themes(self):
        # Reads the themes from /usr/share/dockbarx/themes and ~/.dockbarx/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        dirs = ["/usr/share/namebar/themes", "%s/.namebar/themes" % os.path.expanduser("~")]
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
            md = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                'No working themes found in "/usr/share/namebar/themes" or "~/.namebar/themes"')
            md.run()
            md.destroy()
            print 'Preference dialog error: No working themes found in "/usr/share/namebar/themes" or "~/.namebar/themes"'
        return themes

    def change_theme(self, button=None):
        self.namebar.change_theme()

class Theme():
    @staticmethod
    def check(path_to_tar):
        tar = taropen(path_to_tar)
        try:
            for button in ('close', 'minimize', 'maximize'):
                # Try loading the pixbuf to if everything is OK
                f = tar.extractfile('active/%s_normal.png'%button)
                buffer=f.read()
                pixbuf_loader=gtk.gdk.PixbufLoader()
                pixbuf_loader.write(buffer)
                pixbuf_loader.close()
                f.close()
                pixbuf_loader.get_pixbuf()
        except KeyError:
            tar.close()
            print "Nambar couldn't read the image %s from theme file %s"%('active/%s_normal.png'%button, path_to_tar)
            print "This theme will be ignored."
            return False
        tar.close()
        return True

    def __init__(self, path_to_tar):
        tar = taropen(path_to_tar)
        self.pixbufs = {}
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
        buffer=f.read()
        pixbuf_loader=gtk.gdk.PixbufLoader()
        pixbuf_loader.write(buffer)
        pixbuf_loader.close()
        f.close()
        pixbuf=pixbuf_loader.get_pixbuf()
        return pixbuf

    def get_pixbufs(self):
        return self.pixbufs


class WindowButtonApplet(DockXApplet):
    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.menu = gtk.Menu()
        preferences_item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences_item.connect('activate', self.open_preferences)
        self.menu.insert(preferences_item, 0)
        self.menu.show_all()
        
        self.connect("clicked", self.on_clicked)
        self.shown_window = None
        self.active_window = None
        self.aw_state_handler = None
        
        #~ wnck.set_client_type(wnck.CLIENT_TYPE_PAGER)
        self.screen = wnck.screen_get_default()
        self.screen.force_update()

        #--- Gconf settings
        gconf_set = { str: GCONF_CLIENT.set_string,
                     bool: GCONF_CLIENT.set_bool,
                     int: GCONF_CLIENT.set_int }
        for name, value in settings.items():
            gc_value = None
            try:
                gc_value = GCONF_CLIENT.get_value(GCONF_DIR + '/' + name)
            except:
                gconf_set[type(value)](GCONF_DIR + '/' + name , value)
            else:
                if type(gc_value) != type(value):
                    gconf_set[type(value)](GCONF_DIR + '/' + name , value)
                else:
                    settings[name] = gc_value
        GCONF_CLIENT.add_dir(GCONF_DIR, gconf.CLIENT_PRELOAD_NONE)
        GCONF_CLIENT.notify_add(GCONF_DIR, self.on_gconf_changed, None)

        try:
            self.button_layout = \
                GCONF_CLIENT.get_value("/apps/metacity/general/button_layout")
        except:
            self.button_layout = "menu:minimize,maximize,close"
        else:
            GCONF_CLIENT.add_dir("/apps/metacity/general",
                                 gconf.CLIENT_PRELOAD_NONE)
            GCONF_CLIENT.notify_add("/apps/metacity/general/button_layout",
                                    self.on_button_layout_changed)
                                    
        self.window_state = 'active'
        self.max_icon_state = 'restore'
        
        self.container = gtk.HBox()
        self.container.set_spacing(0)
        self.container.show()
        self.add(self.container)
        
        #--- Load theme
        self.themes = self.find_themes()
        default_theme_path = None
        for theme, path in self.themes.items():
            if theme == settings['theme']:
                self.theme = Theme(path)
                break
            if theme == DEFAULT_SETTINGS['theme']:
                default_theme_path = path
        else:
            if default_theme_path:
                # If the current theme according to gconf couldn't be found,
                # the default theme is used.
                self.theme = Theme(default_theme_path)
            else:
                # Just use one of the themes that where found if default
                # theme couldn't be found either.
                path = self.themes.values()[0]
                self.theme = Theme(path)

        self.pixbufs = self.theme.get_pixbufs()

        self.minimize_button = gtk.EventBox()
        self.minimize_button.set_visible_window(False)
        self.minimize_image = gtk.image_new_from_pixbuf(self.pixbufs['minimize_normal_active'])
        self.minimize_button.add(self.minimize_image)
        self.minimize_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.minimize_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.minimize_button.connect("button-release-event",self.on_button_release_event)
        self.minimize_button.connect("button-press-event",self.on_button_press_event)

        self.maximize_button = gtk.EventBox()
        self.maximize_button.set_visible_window(False)
        self.maximize_image = gtk.image_new_from_pixbuf(self.pixbufs['maximize_normal_active'])
        self.maximize_button.add(self.maximize_image)
        self.maximize_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.maximize_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.maximize_button.connect("button-release-event",self.on_button_release_event)
        self.maximize_button.connect("button-press-event",self.on_button_press_event)

        self.close_button = gtk.EventBox()
        self.close_button.set_visible_window(False)
        self.close_image = gtk.image_new_from_pixbuf(self.pixbufs['close_normal_active'])
        self.close_button.add(self.close_image)
        self.close_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.close_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.close_button.connect("button-release-event",self.on_button_release_event)
        self.close_button.connect("button-press-event",self.on_button_press_event)

        self.repack()

        self.screen.connect("active-window-changed", self.on_active_window_changed)
        self.screen.connect("window-closed", self.on_window_closed)

        self.on_active_window_changed(self.screen)
        self.show()

    def repack(self):
        children = self.container.get_children()
        for child in children:
            self.container.remove(child)

        pack_dict = { 'minimize': self.minimize_button,
                      'maximize': self.maximize_button,
                      'close': self.close_button }
        if settings["use_custom_layout"]:
            layout = settings["custom_layout"]
        else:
            layout = self.button_layout
        pack_strs = layout.split(':')
        start_list = pack_strs[0].split(',')
        for item in start_list:
            if item in pack_dict:
                self.container.pack_start(pack_dict[item], False)
        try:
            end_list = pack_strs[1].split(',')
        except IndexError:
            pass
        else:
            end_list.reverse()
            for item in end_list:
                if item in pack_dict:
                    self.container.pack_end(pack_dict[item], False)

    def find_themes(self):
        # Reads the themes from /usr/share/dockbarx/themes and ~/.dockbarx/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        dirs = ["/usr/share/namebar/themes", "%s/.namebar/themes"%os.path.expanduser("~")]
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
            md = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                'No working themes found in "/usr/share/namebar/themes" or "~/.namebar/themes"')
            md.run()
            md.destroy()
            print 'No working themes found in "/usr/share/namebar/themes" or "~/.namebar/themes"'
            sys.exit(1)
        return themes

    def change_theme(self):
        self.themes = self.find_themes()
        default_theme_path = None
        for theme, path in self.themes.items():
            if theme == settings['theme']:
                self.theme = Theme(path)
                break
        else:
            return

        self.pixbufs = self.theme.get_pixbufs()
        self.minimize_image.set_from_pixbuf(self.pixbufs['minimize_normal_%s'%self.window_state])
        self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
        self.close_image.set_from_pixbuf(self.pixbufs['close_normal_%s'%self.window_state])


    def on_gconf_changed(self, client, par2, entry, par4):
        global settings
        pref_update = False
        old_settings = settings.copy()
        entry_get = { str: entry.get_value().get_string,
                      bool: entry.get_value().get_bool,
                      int: entry.get_value().get_int }
        key = entry.get_key().split('/')[-1]
        if key in settings:
            value = settings[key]
            if entry_get[type(value)]() != value:
                settings[key] = entry_get[type(value)]()
                pref_update = True
        if pref_update and PREFDIALOG:
            PREFDIALOG.update()
        if old_settings['use_custom_layout'] != settings['use_custom_layout']:
            self.repack()
        if old_settings['custom_layout'] != settings['custom_layout'] and \
           settings['use_custom_layout']:
            self.repack()

    def on_button_layout_changed(self, client, connection_id, entry, args):
        if (entry.get_value().type == gconf.VALUE_STRING):
            new_setting = entry.get_value().get_string()
        if (new_setting != self.button_layout):
            self.button_layout = new_setting
            if not settings["use_custom_layout"]:
                self.repack()

    def open_preferences(self, *args):
        PrefDialog(self)

    def on_ppm_about(self, *args):
        AboutDialog()

    def set_shown_window(self, window):
        if self.shown_window != None:
            if self.sw_state_changed_handler != None:
                self.shown_window.disconnect(self.sw_state_changed_handler)
        self.shown_window = window
        self.sw_state_changed_handler = self.shown_window.connect('state-changed', self.on_shown_window_state_changed)

        self.container.show_all()
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
        self.container.hide_all()

    def find_window_to_show(self):
        # Tries to find a window to show on Namebar.
        if self.active_window != None \
        and settings['show_title'] == 'always' \
        and not self.active_window.is_skip_tasklist() \
        and (self.active_window.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                self.set_shown_window(self.active_window)
                return True
        if settings['show_title'] == 'maximized':
            windows_stacked = self.screen.get_windows_stacked()
            for n in range(1,len(windows_stacked)+1):
                if windows_stacked[-n].is_maximized() \
                and not windows_stacked[-n].is_minimized() \
                and not windows_stacked[-n].is_skip_tasklist()\
                and (windows_stacked[-n].get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                    self.set_shown_window(windows_stacked[-n])
                    return True
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
        and (self.active_window.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
            self.aw_state_handler = self.active_window.connect('state-changed', self.on_active_window_state_changed)
        self.find_window_to_show()

    def on_active_window_state_changed(self, window, changed_mask, new_state):
        if self.active_window != self.shown_window \
        and self.active_window.is_maximized():
            self.set_shown_window(self.active_window)

    def on_shown_window_state_changed(self, window, changed_mask, new_state):
        if self.shown_window == None:
            return
        if settings['show_title'] == 'always':
            if self.shown_window.is_maximized() \
            and self.max_icon_state == "maximize":
                self.max_icon_state = "restore"
                self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
            if not self.shown_window.is_maximized() \
            and self.max_icon_state == "restore":
                self.max_icon_state = "maximize"
                self.maximize_image.set_from_pixbuf(self.pixbufs['%s_normal_%s'%(self.max_icon_state, self.window_state)])
        if not self.shown_window.is_maximized() \
        and settings['show_title'] == 'maximized':
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
        if (x >= 0 and x < a.width) and (y >= 0 and y < a.height) and event.button == 1:
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

    def on_clicked(self, widget, event):
        if event.button == 3:
            self.menu.popup(None, None, None, event.button, event.time)

def get_dbx_applet(dbx_dict):
    wb_applet = WindowButtonApplet(dbx_dict)
    return wb_applet
