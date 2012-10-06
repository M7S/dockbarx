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
from log import logger
import time

DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

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
        BUS = dbus.SessionBus()
        self.dockbar_r = weakref.ref(dockbar)
        self.fake_unity = None
        self.sid = None
        self.name_owner_sid = None
        self.props_by_app = {}

    def start(self):
        if self.fake_unity is None:
            self.fake_unity = UnityFakeDBus()
        if self.sid is None:
            interface = "com.canonical.Unity.LauncherEntry"
            self.sid = BUS.add_signal_receiver(self.__on_signal_recieved,
                                               dbus_interface=interface,
                                               sender_keyword="sender")
        if self.name_owner_sid is None:
            self.name_owner_sid = BUS.add_signal_receiver(
                                        self.__on_name_owner_changed,
                                        signal_name="NameOwnerChanged",
                                        bus_name="org.freedesktop.DBus",
                                        path="/org/freedesktop/DBus",
                                        dbus_interface="org.freedesktop.DBus")

    def stop(self):
        for group in self.dockbar_r().groups:
            if group.unity_launcher_bus_name is not None:
                # Remove counts, quicklists etc.
                group.set_unity_properties({}, None)
        self.props_by_app = {}
        if self.sid is not None:
            BUS.remove_signal_receiver(self.sid)
            self.sid = None
        if self.name_owner_sid is not None:
            BUS.remove_signal_receiver(self.name_owner_sid)
            self.name_owner_sid = None
        if self.fake_unity is not None:
            self.fake_unity.stop()
            self.fake_unity = None

    def apply_for_group(self, group):
        app_uri = group.get_app_uri()
        if app_uri in self.props_by_app:
            group.set_unity_properties(self.props_by_app[app_uri],
                                       self.props_by_app[app_uri]["sender"])

    def __on_signal_recieved(self, app_uri, properties, sender):
        if not app_uri or not sender:
            return
        # Apparently python dbus doensn't handle all kinds of int/long 
        # variables correctly. Try the UnityFox firefox addon for example.
        # This is a hack to fix that. There's perhaps a more correct way
        # to do this?
        count = properties.get("count", 0)
        if count < -(1<<35):
            # We assume that the actual int value contains 36(?) bits but
            # python-dbus has made a number of 64 bits instead. The first bits
            # then contains garbage.
            count = int(bin(count)[-36:], 2)
            # The nuber will now start from 1<<35 and go downwards as the
            # actual number increases (because count was negative before we
            # cut the first half). Let's fix that.
            count = (1<<35) - count
            properties["count"] = count
        dockbar = self.dockbar_r()
        if app_uri in self.props_by_app and \
           sender == self.props_by_app[app_uri]["sender"]:
               for key, value in properties.items():
                   self.props_by_app[app_uri][key] = value
        else:
            self.props_by_app[app_uri] = properties
            properties["sender"] = sender
        for group in dockbar.groups:
            if group.get_app_uri() == app_uri:
                break
        else:
            return
        group.set_unity_properties(self.props_by_app[app_uri], sender)

    def __on_name_owner_changed(self, name, before, after):
        dockbar = self.dockbar_r()
        if not after:
            # Name disappeared. Check if it's one of the unity launchers.
            for group in dockbar.groups:
                if name == group.unity_launcher_bus_name:
                    # Remove counts, quicklists etc.
                    group.set_unity_properties({}, None)
            for key, value in self.props_by_app.items():
                if name == value["sender"]:
                    del self.props_by_app[key]

    
class DBusMenu(object):
    def __new__(cls, group, bus_name, path):
        if not bus_name in BUS.list_names():
            return None
        return object.__new__(cls)
        
    def __init__(self, group, bus_name, path):
        self.group_r = weakref.ref(group)
        self.sids = []
        self.bus_name = bus_name
        self.path = path
        self.obj = BUS.get_object(bus_name, path)
        self.iface = dbus.Interface(self.obj, dbus_interface=\
                                    "com.canonical.dbusmenu")
        self.layout = [0,{},[]]
        empty_list = dbus.Array([], "s")
        self.iface.GetLayout(0, -1, empty_list, 
                             reply_handler=self.__layout_loaded,
                             error_handler=self.__error_loading)

    def __layout_loaded(self, revision, layout):
        group = self.group_r()
        self.layout = layout
        self.revision = revision
        self.sids.append(self.iface.connect_to_signal("ItemsPropertiesUpdated",
                                                self.__on_properties_updated))
        self.sids.append(self.iface.connect_to_signal("LayoutUpdated",
                                                self.__on_layout_updated))
        self.sids.append(self.iface.connect_to_signal("ItemActivationRequested",
                                                self.__on_item_activition_requested))
        if group.menu:
            group.menu.update_quicklist_menu(layout)
                                                
    def __error_loading(self, *args):
        # The interface is probably not up and running yet
        time.sleep(0.2)
        empty_list = dbus.Array([], "s")
        self.iface.GetLayout(0, -1, empty_list, 
                             reply_handler=self.__layout_loaded,
                             error_handler=self.__error_handler)
    
    def __error_handler(self, *args):
        pass

    def get_layout(self, parent=0):
        empty_list = dbus.Array([], "s")
        if parent != 0:
            layout = self.__recursive_match(self.layout, parent)
            self.revision, new_layout = self.iface.GetLayout(parent, -1,
                                                             empty_list)
            layout[1] = new_layout[1]
            layout[2] = new_layout[2]
        else:
            self.revision, self.layout = self.iface.GetLayout(0, -1,
                                                              empty_list)

    def __recursive_match(self, a, k):
        if a[0] == k:
            return a
        for child in a[2]:
            result = self.__recursive_match(child, k)
            if result is not None:
                return result
        return None

    def __on_layout_updated(self, revision, parent):
        group = self.group_r()
        if revision != self.revision:
            self.get_layout(parent)
        layout = self.__recursive_match(self.layout, parent)
        if group.menu:
            group.menu.update_quicklist_menu(layout)
            
    def send_event(self, id, event, data, event_time):
        self.iface.Event(id, event, data, event_time)
        
    def __on_properties_updated(self, changed_props, removed_props):
        group = self.group_r()
        changed_items = [] 
        for props in changed_props:
            item = self.__recursive_match(self.layout, props[0])
            if item is None:
                continue
            for key, value in props[1].items():
                item[1][key] = value
            changed_items.append(item)
            if group.menu is not None:
                identifier = "unity_%s" % props[0]
                group.menu.set_properties(identifier, props[1])
        for props in removed_props:
            item = self.__recursive_match(self.layout, props[0])
            if item is None:
                continue
            for prop in props[1]:
                if prop in item[1]:
                    del item[1][prop]
            changed_items.append(item)
        if group.menu is not None:
            for item in changed_items:
                identifier = "unity_%s" % item[0]
                group.menu.set_properties(identifier, item[1])

    def __on_item_activition_requested(self, item_id, timestamp):
        #~ group = self.group_r()
        #~ group.menu_item_activision_requested(item_id, time_stamp)
        pass
        
    def destroy(self):
        for sid in self.sids[:]:
            sid.remove()
            self.sids.remove(sid)
        
