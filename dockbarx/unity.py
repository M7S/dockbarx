#!/usr/bin/python

#   unity.py
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
#	along with dockbar.  If not, see <http://www.gnu.org/licenses/>.


import dbus
import dbus.service
import gobject
import weakref
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)

class UnityFakeDBus(dbus.service.Object):
    def __new__(cls):
        if "com.canonical.Unity" in dbus.SessionBus().list_names():
            return None
        else:
            return dbus.service.Object.__new__(cls)
            
    def __init__(self):
        bus_name = dbus.service.BusName("com.canonical.Unity",
                                        bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
                                     "/org/dockbar/fakeunity")

    def stop(self):
        self.remove_from_connection()
                                     
    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == "com.canonical.Unity":
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


class UnityWatcher():
    def __init__(self, dockbar):
        self.bus = dbus.SessionBus()
        self.dockbar_r = weakref.ref(dockbar)
        self.fake_unity = None
        self.sid = None

    def start(self):
        if self.fake_unity is None:
            self.fake_unity = UnityFakeDBus()
        if self.sid is not None:
            return
        interface = "com.canonical.Unity.LauncherEntry"
        self.sid = self.bus.add_signal_receiver(self.__on_signal_recieved,
                                                dbus_interface=interface)

    def stop(self):
        if self.sid is not None:
            self.bus.remove_signal_receiver(self.sid)
            self.sid = None
        if self.fake_unity is not None:
            self.fake_unity.stop()
            self.fake_unity = None

    def __on_signal_recieved(self, app_uri, properties):
        dockbar = self.dockbar_r()
        for group in dockbar.groups:
            if group.get_app_uri() == app_uri:
                break
        else:
            return
        group.set_unity_properties(properties)
        
