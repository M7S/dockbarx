#!/usr/bin/python2

#   dockbar.py
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

import dbus
import dbus.service
import weakref

class DockbarDBus(dbus.service.Object):
    def __init__(self, dockbar):
        self.bus_name = "org.dockbar.DockbarX"
        if "org.dockbar.DockbarX" in dbus.SessionBus().list_names():
            for n in range(1, 100):
                name = "org.dockbar.DockbarX%s" % n
                if not name in dbus.SessionBus().list_names():
                    self.bus_name = name
                    break
        self.dockbar_r = weakref.ref(dockbar)
        bus_name = dbus.service.BusName(self.bus_name,
                                        bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
                                     "/org/dockbar/DockbarX")

    @dbus.service.method(dbus_interface="org.dockbar.DockbarX",
                         in_signature="", out_signature="",)
    def Reload(self):
        dockbar = self.dockbar_r()
        if not dockbar.no_dbus_reload:
            dockbar.reload()

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == "org.dockbar.DockbarX":
            return {}
        else:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The Foo object does not implement the %s interface'
                    % interface_name)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv', out_signature='')
    def Set(self, interface_name, property_name, property_value):
        pass

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass
