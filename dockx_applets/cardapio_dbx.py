#  
#  Copyright (C) 2010 Cardapio Team (tvst@hotmail.com)
# 
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import gtk
from dockbarx.applets import DockXApplet
sys.path.insert(0, "/usr/lib/cardapio")
from misc import *
from CardapioAppletInterface import *
from Cardapio import Cardapio

class CardapioDockXApplet(CardapioAppletInterface):

    panel_type = PANEL_TYPE_AWN

    IS_CONFIGURABLE = True
    IS_CONTROLLABLE = True

    ICON = 'cardapio-dark256'

    def __init__(self, applet):

        self.applet = applet

        self.applet_press_handler = None
        self.applet_enter_handler = None
        self.applet_leave_handler = None
        self.autohide_cookie      = None

        self.applet.set_tooltip_text('Cardapio')


    def setup(self, cardapio):

        self.cardapio = cardapio

        self.preferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        self.edit = gtk.ImageMenuItem(gtk.STOCK_EDIT)
        self.about = gtk.ImageMenuItem(gtk.STOCK_ABOUT)

        self.preferences.connect('activate', self._open_options_dialog)
        self.edit.connect('activate', self._launch_edit_app)
        self.about.connect('activate', self._open_about_dialog)
        self.applet.connect('unmap-event', self._on_applet_destroy)

        self.menu = gtk.Menu()
        self.menu.insert(self.preferences, 0)
        self.menu.insert(self.edit, 1)
        self.menu.insert(self.about, 2)
        self.menu.insert(gtk.SeparatorMenuItem(), 3)
        self.menu.show_all()


    def update_from_user_settings(self, settings):

        if self.applet_press_handler is not None:
            try:
                self.applet.disconnect(self.applet_press_handler)
                self.applet.disconnect(self.applet_enter_handler)
                self.applet.disconnect(self.applet_leave_handler)
            except: pass

        if settings['open on hover']:
            self.applet_press_handler = self.applet.connect('clicked', self._on_applet_clicked, True)
            self.applet_enter_handler = self.applet.connect('enter-notify-event', self._on_applet_cursor_enter)
            self.applet_leave_handler = self.applet.connect('leave-notify-event', self._on_applet_cursor_leave)

        else:
            self.applet_press_handler = self.applet.connect('clicked', self._on_applet_clicked, False)
            self.applet_enter_handler = self.applet.connect('enter-notify-event', return_true)
            self.applet_leave_handler = self.applet.connect('leave-notify-event', return_true)

        try:
            self.applet.set_icon_name(settings['applet icon'])
            return
        except: pass

        try: self.applet.set_icon_name(self.ICON)
        except: pass


    def get_size(self):
        icon_size = self.applet.get_size()
        return icon_size, icon_size


    def get_position(self):

        x, y = self.applet.get_window().get_origin()
        ax, ay, w, h = self.applet.get_allocation()
        x += ax
        y += ay
        icon_size = self.applet.get_full_size()

        pos_type = self.applet.get_position().lower()

        if   pos_type == "bottom" : y = y + h - icon_size
        elif pos_type == "right"  : x = x + w - icon_size
        return x, y 


    def get_orientation(self):
        pos_type = self.applet.get_position().lower()
        if pos_type == "top"    : return POS_TOP
        if pos_type == "bottom": return POS_BOTTOM
        if pos_type == "left"   : return POS_LEFT
        else: return POS_RIGHT


    def has_mouse_cursor(self, mouse_x, mouse_y):
        return False


    def draw_toggled_state(self, state):
        pass


    def disable_autohide(self, state):

        if state:
            self.autohide_cookie = self.applet.inhibit_autohide('Showing Cardapio')

        elif self.autohide_cookie != None:
            self.applet.uninhibit_autohide(self.autohide_cookie)
            self.autohide_cookie = None


    def _on_applet_clicked(self, widget, event, ignore_main_button):
        if event.button == 1 and not ignore_main_button:
            self.cardapio.show_hide()
        elif event.button == 3:
            self.menu.popup(None, None, None, event.button, event.time)


    def _on_applet_cursor_enter(self, widget, event):
        self.cardapio.show_hide()
        return True


    def _on_applet_cursor_leave(self, widget, event):
        self.cardapio.handle_mainwindow_cursor_leave()


    def _open_options_dialog(self, widget):
        self.cardapio.open_options_dialog()


    def _launch_edit_app(self, widget):
        self.cardapio.launch_edit_app()


    def _open_about_dialog(self, widget):
        self.cardapio.handle_about_menu_item_clicked(widget)


    def _on_applet_destroy(self, *args):
        self.cardapio.save_and_quit()


    def get_screen_number(self):
        """
        Returns the number of the screen where the applet is placed
        """
        screen = self.applet.get_screen()
        if screen is None: return 0
        return screen.get_number()

class MenuButtonApplet(DockXApplet):
    """An example applet for DockbarX standalone dock"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        self.icon = gtk.Image()
        self.icon.set_from_icon_name("cardapio-dark256", gtk.ICON_SIZE_DIALOG)
        self.icon.set_pixel_size(self.get_size())
        self.add(self.icon)
        self.icon.show()
        self.show()

    def set_icon_name(self, name):
        if os.path.isfile(name):
            self.icon.set_from_file(name)
        else:
            self.icon.set_from_icon_name(name, gtk.ICON_SIZE_DIALOG)
        self.icon.set_pixel_size(self.get_size())

def get_dbx_applet(dbx_dict):
    global mbapplet
    try:
        return mbapplet
    except:
        # First run, make a new instance
        mbapplet = MenuButtonApplet(dbx_dict)
        cardapio_applet = CardapioDockXApplet(mbapplet)
        cardapio = Cardapio(panel_applet=cardapio_applet)
        return mbapplet
