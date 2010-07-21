#!/usr/bin/python

#   DockBarX.py
#
#	Copyright 2009, 2010 Aleksey Shaferov and Matias Sars
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

import awn
import dockbarx.dockbar
import gobject
import sys
import gtk


class DockBarApp (awn.AppletSimple):
    def __init__ (self, uid, panel_id):
        awn.AppletSimple.__init__(self, "DockbarX", uid, panel_id)
        print "DockBarApp.__init__()"
        print "dockbarx.__file__ = ",dockbarx.__file__
        print " uid = ",uid,"\n panel_id= ", panel_id
        self.set_icon_name("gtk-apply")
        gobject.idle_add(self.on_idle)


    def on_idle(self):
        self.old_child = self.get_child()
        gdk_screen = gtk.gdk.screen_get_default()
        window = self.old_child.window
        monitor = gdk_screen.get_monitor_at_window(window)
        self.icon = self.get_icon()
        self.remove(self.old_child)
        self.db = dockbarx.dockbar.DockBar(as_awn_applet=True)
        self.db.monitor = monitor
        self.db.reload()
        if self.get_pos_type() in (gtk.POS_BOTTOM, gtk.POS_TOP):
            self.box = gtk.VBox()
            self.db.set_orient('h')
        else:
            self.box = gtk.HBox()
            self.db.set_orient('v')
        if self.get_pos_type() in (gtk.POS_BOTTOM, gtk.POS_RIGHT):
            self.box.pack_end(self.db.container, False, False)
        else:
            self.box.pack_start(self.db.container, False, False)
        if self.db.globals.orient == 'h':
            self.db.container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 2)
        else:
            self.db.container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 2, -1)
        self.add(self.box)
        self.connect('size-changed',self.on_size_changed)
        self.connect('position-changed', self.on_position_changed)
        self.box.show()
        self.db.container.show()
        self.show()

    def on_size_changed(self, arg1, new_size):
        if self.db.globals.orient == 'h':
            self.db.container.set_size_request(-1, new_size + \
                                               self.icon.get_offset() + 2)
        else:
            self.db.container.set_size_request(new_size + \
                                               self.icon.get_offset() + 2, -1)

    def on_position_changed(self, applet, position):
        self.box.remove(self.db.container)
        self.remove(self.box)
        if self.get_pos_type() in (gtk.POS_BOTTOM, gtk.POS_TOP):
            self.box = gtk.VBox()
            self.db.set_orient('h')
        else:
            self.box = gtk.HBox()
            self.db.set_orient('v')
        if self.get_pos_type() in (gtk.POS_BOTTOM, gtk.POS_RIGHT):
            self.box.pack_end(self.db.container, False, False)
        else:
            self.box.pack_start(self.db.container, False, False)
        if self.db.globals.orient == 'h':
            self.db.container.set_size_request(-1, self.get_size() + \
                                               self.icon.get_offset() + 2)
        else:
            self.db.container.set_size_request(self.get_size() + \
                                               self.icon.get_offset() + 2, -1)
        self.add(self.box)
        self.box.show()
        self.db.container.show()
        self.show()

if __name__ == "__main__":
    awn.init(sys.argv[1:])
    print "%s %d" % (awn.uid, awn.panel_id)
    applet = DockBarApp(awn.uid, awn.panel_id)
    awn.embed_applet(applet)
    applet.show_all()
    gtk.main()
