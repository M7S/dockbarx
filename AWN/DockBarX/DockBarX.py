#!/usr/bin/python

#	Copyright 2009, Aleksey Shaferov
#   DockBar Applet for Avant Window Navigator  (DB4AWN)
#
#	DB4AWN is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	DB4AWN is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with media-applet.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

import awn
import dockbarx
import sys
import gtk


class DockBarApp (awn.Applet):
    def __init__ (self, uid, orient, height):
        awn.Applet.__init__(self, uid, orient, height)
        print "DockBarApp.__init__()"
        print "dockbarx.__file__ = ",dockbarx.__file__
        print " uid = ",uid,"\n orinet = ", orient,"\n height = ", height
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(height)
        self.hbox = gtk.HBox()
        self.vbox.add(self.hbox)
        self.db = dockbarx.DockBar(None)
        self.vbox.add(self.db.container)
        self.add(self.vbox)
        #self.h_size_allocate = self.connect('size-allocate',self.on_size_allocate)
        self.connect ('height-changed',self.on_height_changed)
        self.show_all()
        
    #def on_size_allocate (self,arg1,arg2):
    #    print "SA signal"
    #    print "self.get_allocation().height = ",self.get_allocation().height
    #    print "self.vbox.get_allocation().height = ",self.vbox.get_allocation().height
        
    def on_height_changed (self,arg1,new_height):
        self.vbox.set_spacing(new_height)


if __name__ == "__main__":
    awn.init(sys.argv[1:])
    print "%s %d %d" % (awn.uid, awn.orient, awn.height)
    applet = DockBarApp(awn.uid, awn.orient, awn.height)
    awn.init_applet(applet)
    applet.show_all()
    gtk.main()
