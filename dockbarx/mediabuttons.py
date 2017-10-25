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

from gi.repository import Gtk
import dbus
from dbus.mainloop.glib import DBusGMainLoop

from cairowidgets import *
from log import logger
import weakref

DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

class MediaButtons(Gtk.Alignment):
    def __init__(self, name):
        self.sids = []
        self.player = BUS.get_object("org.mpris.MediaPlayer2.%s" % name,
                                     "/org/mpris/MediaPlayer2")
        self.player_iface = dbus.Interface(self.player,
                                           dbus_interface=\
                                           "org.mpris.MediaPlayer2.Player")
        self.signal = self.player.connect_to_signal("PropertiesChanged",
                                      self.__on_properties_changed,
                                      dbus_interface=\
                                      "org.freedesktop.DBus.Properties")
        GObject.GObject.__init__(self)
        self.set(0.5, 0.5, 0, 0)
        hbox = Gtk.HBox()
        self.previous_button = CairoNextButton(previous=True)
        self.playpause_button = CairoPlayPauseButton()
        self.next_button = CairoNextButton()
        connect(self.previous_button, "clicked", self.previous)
        connect(self.playpause_button,"clicked", self.playpause)
        connect(self.next_button, "clicked", self.next)
        hbox.pack_start(self.previous_button, True, True, 0)
        hbox.pack_start(self.playpause_button, True, True, 4)
        hbox.pack_start(self.next_button, True, True, 0)
        self.add(hbox)
        hbox.show_all()
        self.update_plaback_status()

    def get_property(self, property):
        # This function gets the property using a sync call
        # (in other words: avoid using it).
        try:
            ret_str = str(self.player.Get("org.mpris.MediaPlayer2.Player",
                                          property,
                                          dbus_interface=\
                                          "org.freedesktop.DBus.Properties"))
        except:
            return
        return ret_str

    def previous(self, *args):
        self.player_iface.Previous(reply_handler=self.__reply_handler,
                                   error_handler=self.__error_handler)

    def playpause(self, *args):
        self.player_iface.PlayPause(reply_handler=self.__reply_handler,
                                error_handler=self.__playpause_error_handler)

    def __playpause_error_handler(self, err):
        # Todo: There must be a less ugly way to catch this error.
        if str(err).startswith("org.freedesktop.DBus.Error.UnknownMethod"):
            # Todo: Would it be worth it to make this function async?
            if "Playing" in self.get_property("PlaybackStatus"):
                self.player_iface.Pause(reply_handler=self.__reply_handler,
                                        error_handler=self.__error_handler)
            else:
                self.player_iface.Play(reply_handler=self.__reply_handler,
                                       error_handler=self.__error_handler)

    def next(self, *args):
        self.player_iface.Next(reply_handler=self.__reply_handler,
                               error_handler=self.__error_handler)

    def show_player(self, *args):
        try:
            self.player.Raise(dbus_interface="org.mpris.MediaPlayer2")
        except:
            return False
        return True

    def remove(self):
        self.signal.remove()
        disconnect(self.previous_button)
        disconnect(self.next_button)
        disconnect(self.playpause_button)
        self.previous_button.destroy()
        self.next_button.destroy()
        self.playpause_button.destroy()
        del self.player_iface
        del self.player

    def __reply_handler(self, *args):
        pass

    def __error_handler(self, err):
        print "DBus error in media buttons:", err

    def __on_properties_changed(self, iface, changed_props, inv_props):
        if "PlaybackStatus" in changed_props:
            pause = changed_props["PlaybackStatus"]== "Playing"
            self.playpause_button.set_pause(pause)

    def update_plaback_status(self):
        self.player.Get("org.mpris.MediaPlayer2.Player",
                        "PlaybackStatus",
                        dbus_interface="org.freedesktop.DBus.Properties",
                        reply_handler=self.__playback_status_reply_handler,
                        error_handler=self.__error_handler)

    def __playback_status_reply_handler(self, status):
        self.playpause_button.set_pause(status == "Playing")

class Mpris2Watch():
    def __init__(self, dockbar):
        self.dockbar_r = weakref.ref(dockbar)
        self.players = []
        self.fdo = BUS.get_object("org.freedesktop.DBus",
                                  "/org/freedesktop/DBus")
        addresses = self.fdo.ListNames(dbus_interface="org.freedesktop.DBus")
        for address in addresses:
            if str(address).startswith("org.mpris.MediaPlayer2."):
                try:
                    BUS.get_object(address, "/org/mpris/MediaPlayer2")
                except:
                    logger.warning("Error: Couldn't make dbus connection " + \
                                   "with %s" % address)
                    continue
                self.players.append(
                        str(address).replace("org.mpris.MediaPlayer2.", ""))

        self.fdo.connect_to_signal("NameOwnerChanged",
                                    self.__on_name_change_detected,
                                    dbus_interface=\
                                    "org.freedesktop.DBus")

    def __on_name_change_detected(self, name, previous_owner, current_owner):
        if str(name).startswith("org.mpris.MediaPlayer2."):
            player_name = str(name).replace("org.mpris.MediaPlayer2.", "")
            if previous_owner == "" and current_owner !="":
                try:
                    BUS.get_object(name, "/org/mpris/MediaPlayer2")
                except:
                    logger.exception("Error: Couldn't make dbus " + \
                                     "connection with %s" % name)
                    return
                self.players.append(player_name)
                self.dockbar_r().media_player_added(player_name)
            if previous_owner != "" and current_owner == "":
                try:
                    self.players.remove(player_name)
                except ValueError:
                    pass
                else:
                    self.dockbar_r().media_player_removed(player_name)

    def has_player(self, name):
        return name in self.players

    def get_players(self):
        return self.players

