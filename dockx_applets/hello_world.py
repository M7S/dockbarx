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
from dockbarx.applets import DockXApplet #, DockXAppletDialog 


class HelloWorldApplet(DockXApplet):
    """An example applet for DockbarX standalone dock"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        label = gtk.Label("<span foreground=\"#FFFFFF\">Hello World!</span>")
        label.set_use_markup(True)
        # DockXApplet base class is pretty much a gtk.EventBox.
        # so all you have to do is adding your widget with self.add()
        self.add(label)
        label.show()
        self.show()

#~ class HelloWorldPreferences(DockXAppletDialog):
    #~ Title = "Clock Applet Preference"
    #~ 
    #~ def __init__(self):
        #~ DockXAppletDialog.__init__(self, APPLET_NAME)

    #~ def run(self):
        #~ DockXApplet.run(self)

# All applets needs to have this function
def get_dbx_applet(dbx_dict):
    # This is the function that dockx will be calling.
    # Returns an instance of the applet.
    applet = HelloWorldApplet(dbx_dict)
    return applet


#~ def run_applet_dialog():
    #~ dialog = HelloWorldPreferences()
    #~ dialog.run()
    #~ dialog.destroy()
        
