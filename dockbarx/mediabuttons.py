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

import gtk
import dbus
from dbus.mainloop.glib import DBusGMainLoop

from cairowidgets import *
DBusGMainLoop(set_as_default=True)
BUS = dbus.SessionBus()

class MediaButtons(gtk.Alignment):
    def __init__(self, name):
        self.sids = []
        self.player = BUS.get_object("org.mpris.MediaPlayer2.%s" % name,
                                     "/org/mpris/MediaPlayer2")
        self.player_iface = dbus.Interface(self.player,
                                           dbus_interface=\
                                           "org.mpris.MediaPlayer2.Player")
        self.signal = self.player.connect_to_signal("PropertiesChanged",
                                      self.on_properties_changed,
                                      dbus_interface=\
                                      "org.freedesktop.DBus.Properties")
        gtk.Alignment.__init__(self, 0.5, 0.5, 0, 0)
        hbox = gtk.HBox()
        self.previous_button = CairoNextButton(previous=True)
        self.playpause_button = CairoPlayPauseButton()
        self.next_button = CairoNextButton()
        self.sids.append((self.previous_button,
                          self.previous_button.connect("clicked",
                                                       self.previous)))
        self.sids.append((self.playpause_button,
                          self.playpause_button.connect("clicked",
                                                        self.playpause)))
        self.sids.append((self.next_button,
                         self.next_button.connect("clicked", self.next)))
        hbox.pack_start(self.previous_button)
        hbox.pack_start(self.playpause_button, padding=4)
        hbox.pack_start(self.next_button)
        self.add(hbox)
        hbox.show_all()
        if self.get_property('PlaybackStatus')== "Playing":
            self.playpause_button.set_pause(True)

    def get_property(self, property):
        try:
            ret_str = str(self.player.Get('org.mpris.MediaPlayer2.Player',
                                          property,
                                          dbus_interface=\
                                          'org.freedesktop.DBus.Properties'))
        except:
            return
        return ret_str

    def previous(self, *args):
        self.player_iface.Previous(reply_handler=self.__reply_handler,
                                   error_handler=self.__error_handler)


    def playpause(self, *args):
        if "Playing" in self.get_property('PlaybackStatus'):
            self.player_iface.Pause(reply_handler=self.__reply_handler,
                                    error_handler=self.__error_handler)
        else:
            self.player_iface.Play(reply_handler=self.__reply_handler,
                                   error_handler=self.__error_handler)

    def next(self, *args):
        self.player_iface.Next(reply_handler=self.__reply_handler,
                               error_handler=self.__error_handler)

    def __reply_handler(self, *args):
        pass

    def __error_handler(self, *args):
        pass

    def remove(self):
        while self.sids:
            widget, sid = self.sids.pop()
            widget.disconnect(sid)
        self.previous_button.destroy()
        self.next_button.destroy()
        self.playpause_button.destroy()
        del self.player_iface
        del self.player

    def on_properties_changed(self, *args):
        pause = self.get_property('PlaybackStatus') == "Playing"
        self.playpause_button.set_pause(pause)

class Mpris2Watch(gobject.GObject):
    __gsignals__ = {'player-added':
                        (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
                    'player-removed':
                        (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, ))}
    def __init__(self):
        gobject.GObject.__init__(self)
        self.players = []
        self.fdo = BUS.get_object("org.freedesktop.DBus",
                                  "/org/freedesktop/DBus")
        addresses = self.fdo.ListNames(dbus_interface="org.freedesktop.DBus")
        for address in addresses:
            if str(address).startswith("org.mpris.MediaPlayer2."):
                try:
                    BUS.get_object(address, "/org/mpris/MediaPlayer2")
                except:
                    print "Error: Couldn't make dbus connection with %s" % \
                                                                    address
                    continue
                self.players.append(
                        str(address).replace("org.mpris.MediaPlayer2.", ""))

        self.fdo.connect_to_signal("NameOwnerChanged",
                                    self.on_name_change_detected,
                                    dbus_interface=\
                                    "org.freedesktop.DBus")

    def on_name_change_detected(self, name, previous_owner, current_owner):
        if str(name).startswith("org.mpris.MediaPlayer2."):
            player_name = str(name).replace("org.mpris.MediaPlayer2.", "")
            if previous_owner == "" and current_owner !="":
                try:
                    BUS.get_object(name, "/org/mpris/MediaPlayer2")
                except:
                    print "Error: Couldn't make dbus connection with %s" % name
                    raise
                self.players.append(player_name)
                self.emit('player-added', player_name)
            if previous_owner != "" and current_owner == "":
                try:
                    self.players.remove(player_name)
                except ValueError:
                    pass
                else:
                    self.emit('player-removed', player_name)

    def has_player(self, name):
        return name in self.players

