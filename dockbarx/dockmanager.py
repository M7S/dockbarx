#!/usr/bin/python

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

import weakref
import dbus
import dbus.service

from common import ODict
from log import logger

class DockManager(dbus.service.Object):
    def __init__(self, dockbar):
        self.dockbar_r = weakref.ref(dockbar)
        bus_name = dbus.service.BusName("net.launchpad.DockManager",
                                        bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
                                     "/net/launchpad/DockManager")


    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="", out_signature="as",)
    def GetCapabilities(self):
        capabilities = ["menu-item-container-title",
                        "menu-item-icon-file",
                        "menu-item-icon-name",
                        "menu-item-with-label"]
        return capabilities

    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="", out_signature="ao",)
    def GetItems(self):
        path_list = []
        for path in self.dockbar_r().get_dm_paths():
            path_list.append(dbus.ObjectPath(path))
        return path_list

    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="s", out_signature="ao",)
    def GetItemsByDesktopFile(self, name):
        path_list = []
        for path in self.dockbar_r().get_dm_paths_by_desktop_file(name):
            path_list.append(dbus.ObjectPath(path))
        logger.debug("Items gotten by dekstop file:", path_list)
        return path_list

    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="s", out_signature="ao",)
    def GetItemsByName(self, name):
        path_list = []
        for path in self.dockbar_r().get_dm_paths_by_name(name):
            path_list.append(dbus.ObjectPath(path))
        logger.debug("Items gotten by name:", path_list)
        return path_list

    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="i", out_signature="ao",)
    def GetItemsByPid(self, pid):
        path_list = []
        for path in self.dockbar_r().get_dm_paths_by_pid(pid):
            path_list.append(dbus.ObjectPath(path))
        logger.debug("Items gotten by pid:", path_list)
        return path_list

    @dbus.service.method(dbus_interface="net.launchpad.DockManager",
                         in_signature="x", out_signature="ao",)
    def GetItemsByXid(self, xid):
        path_list = []
        for path in self.dockbar_r().get_dm_paths_by_xid(xid):
            path_list.append(dbus.ObjectPath(path))
        logger.debug("Items gotten by xid:", path_list)
        return path_list

    @dbus.service.signal(dbus_interface='net.launchpad.DockManager',
                         signature='o')
    def ItemAdded(self, obj_path):
        pass

    @dbus.service.signal(dbus_interface='net.launchpad.DockManager',
                         signature='o')
    def ItemRemoved(self, obj_path):
        pass

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == "net.launchpad.DockManager":
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

    def reset(self):
        bus = dbus.SessionBus()
        proxy = bus.get_object("net.launchpad.DockManager.Daemon",
                               "/net/launchpad/DockManager/Daemon")
        proxy.RestartAll(dbus_interface="net.launchpad.DockManager.Daemon")

class DockManagerItem(dbus.service.Object):
    counter = 0
    def __init__(self, groupbutton):
        self.groupbutton_r = weakref.ref(groupbutton)
        self.menu_counter = 0
        self.menu_items = ODict()

        DockManagerItem.counter += 1
        self.obj_path = "/net/launchpad/DockManager/Item" + \
                        str(DockManagerItem.counter)
        bus_name = dbus.service.BusName("net.launchpad.DockManager",
                                        bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, self.obj_path)
        desktop_entry = self.groupbutton_r().desktop_entry
        if desktop_entry:
            path = desktop_entry.getFileName()
        else:
            path = ""

    @dbus.service.method(dbus_interface="net.launchpad.DockItem",
                         in_signature="a{sv}", out_signature="i")
    def AddMenuItem(self, properties):
        self.menu_counter += 1
        id = self.menu_counter
        self.menu_items[id] = dict(properties)
        return id

    @dbus.service.method(dbus_interface="net.launchpad.DockItem",
                         in_signature="i", out_signature="")
    def RemoveMenuItem(self, id):
        try:
            del self.menu_items[id]
        except KeyError:
            pass

    @dbus.service.method(dbus_interface="net.launchpad.DockItem",
                         in_signature="a{sv}", out_signature="")
    def UpdateDockItem(self, properties):
        pass

    @dbus.service.signal(dbus_interface='net.launchpad.DockItem',
                         signature='i')
    def MenuItemActivated(self, id):
        pass

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface, propname):
        return self.GetAll(interface)[propname]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface == "net.launchpad.DockItem":
            path = self.groupbutton_r().get_desktop_entry_file_name()
            return { 'DesktopFile': path,
                     'Uri': ''
                   }
        else:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The Foo object does not implement the %s interface'
                    % interface)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv', out_signature='')
    def Set(self, interface, propname, value):
        pass

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass

    def get_path(self):
        return self.obj_path

    def get_menu_items(self):
        return self.menu_items
