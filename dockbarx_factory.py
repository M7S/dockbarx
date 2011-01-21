#!/usr/bin/python

#   dockbarx_factory.py
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

from dockbarx.log import *
import sys
if not (len(sys.argv) == 2 and sys.argv[1] == "run-in-window"):
    log_to_file()
    sys.stderr = StdErrWrapper()
    sys.stdout = StdOutWrapper()

import pygtk
pygtk.require("2.0")
import gtk
import gnomeapplet
import dockbarx.dockbar

class DockBarWindow():
    """DockBarWindow sets up the window if run-in-window is used."""
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(200,40)
        self.window.show()
        self.window.set_property("skip-taskbar-hint",True)
        self.window.set_keep_above(True)
        self.window.connect ("destroy",self.__destroy)

        self.dockbar = dockbarx.dockbar.DockBar(None)
        hbox = gtk.HBox()
        button = gtk.Button("Pref")
        button.connect("clicked", self.__on_pref_clicked)
        hbox.pack_start(button, False)
        hbox.pack_start(self.dockbar.container, False)
        eb = gtk.EventBox()
##        eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#2E2E2E"))
        eb.add(hbox)
        self.window.add(eb)
        eb.show_all()
        ##self.window.add(self.dockbar.container)

    def __on_pref_clicked(self, *args):
        self.dockbar.open_preference()

    def __destroy (self,widget,data=None):
        gtk.main_quit()

    def main(self):
        gtk.main()


def dockbar_factory(applet, iid):
    dockbar = dockbarx.dockbar.DockBar(applet)
    applet.set_background_widget(applet)
    applet.show_all()
    return True

if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":
    dockbarwin = DockBarWindow()
    dockbarwin.main()
else:
    gnomeapplet.bonobo_factory("OAFIID:GNOME_DockBarXApplet_Factory",
                                     gnomeapplet.Applet.__gtype__,
                                     "dockbar applet", "0", dockbar_factory)