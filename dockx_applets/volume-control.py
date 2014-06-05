#!/usr/bin/python2
# Copyright (C) 2008 - 2010  onox <denkpadje@gmail.com>
#               2012 Matias Sars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

from collections import defaultdict
import os
import subprocess
import threading
from dockbarx.applets import DockXApplet
import weakref

import pygtk
pygtk.require("2.0")
import gtk
from gtk import gdk
import gobject

#~ from awn.extras import _, awnlib, __version__

import pygst
pygst.require("0.10")
import gst

gst_message_types = (gst.interfaces.MIXER_MESSAGE_MUTE_TOGGLED.value_nick,
                     gst.interfaces.MIXER_MESSAGE_VOLUME_CHANGED.value_nick)

# Interval in seconds between two successive reads of the current volume
read_volume_interval = 0.5

# Delay in seconds to freeze the GStreamer messages. This is used by the
# value-changed callback of the volume scale to avoid jittering
gstreamer_freeze_messages_interval = 0.2

applet_name = _("Volume Control")
applet_description = _("Applet to control your computer's volume")

theme_dir = "/usr/share/icons"
ui_file = os.path.join(os.path.dirname(__file__), "volume-control.ui")

system_theme_name = _("System theme")

volume_control_apps = ["gnome-volume-control", "xfce4-mixer"]

# PulseAudio's volume control application
pa_control_app = "pavucontrol"

moonbeam_theme_dir = os.path.join(os.path.dirname(__file__), "vc-themes")
moonbeam_ranges = [100, 93, 86, 79, 71, 64, 57, 50, 43, 36, 29, 21, 14, 1]

# Logo of the applet, shown in the GTK About dialog
applet_logo = os.path.join(os.path.dirname(__file__), "volume-control.svg")

volume_ranges = [("high", 66), ("medium", 36), ("low", 1)]
volume_step = 4

mixer_names = ("pulsemixer", "oss4mixer", "alsamixer")

no_mixer_message = _("Install the appropriate plug-ins for one or more of the following GStreamer elements: %s.")
no_devices_message = _("Could not find any devices.")

def add_cell_renderer_text(combobox):
    """Add a gtk.CellRendererText to the combobox. To be used if the combobox
    has a gtk.ListStore model with a string as the first column.

    """
    text = gtk.CellRendererText()
    combobox.pack_start(text, True)
    combobox.add_attribute(text, "text", 0)

class Timing:

    """Provides utilities to register a function to be called periodically
    or once after a specified delay.

    """

    def __init__(self):
        """Create a new Timing object.

        @param parent: The parent applet of the timing instance.
        @type parent: L{Applet}

        """
        #~ self.__parent = parent
        pass

    def register(self, callback, seconds, start=True):
        """Register a function to be called periodically.

        @param callback: Function to be called.
        @type callback: C{function}
        @param seconds: Number of seconds within each call.
        @type seconds: C{float} or C{int}
        @param start: Whether to start the callback automatically
        @type start: C{bool}
        @return: A L{Callback} object for the C{callback} parameter
        @rtype: L{Callback}

        """
        def callback_wrapper():
            callback()
            return True
        cb = self.Callback(callback_wrapper, seconds)
        if start:
            cb.start()
        return cb

    def delay(self, callback, seconds, start=True):
        """Delay the execution of the given callback.

        @param callback: Function
        @type callback: C{function}
        @param seconds: Number of seconds to delay function call
        @type seconds: C{float} or C{int}
        @return: A L{Callback} object for the C{callback} parameter
        @rtype: L{Callback}

        """
        def callback_wrapper():
            callback()
            return False
        cb = self.Callback(callback_wrapper, seconds)
        if start:
            cb.start()
        return cb

    class Callback:

        """Wrapper around a callback function to provide ways to start and
        stop the function, to change the interval or to test if the callback
        is scheduled to run.

        """

        def __init__(self, callback, seconds):
            """Create a new C{Callback} object.

            @param callback: The function to wrap the Callback around.
            @type callback: C{function}
            @param seconds: Number of seconds within each call.
            @type seconds: C{float} or C{int}

            """
            assert seconds > 0.0

            self.__callback = callback
            self.__seconds = seconds
            self.__timer_id = None

        def is_started(self):
            """Return True if the callback has been scheduled to run after
            each interval, False if the callback is stopped.

            @return: True if the callback has been scheduled, False otherwise
            @rtype: L{bool}

            """
            return self.__timer_id is not None

        def start(self):
            """Start executing the callback periodically.

            @return: True if the callback was started, False otherwise
            @rtype: L{bool}

            """
            if self.__timer_id is not None:
                return False

            if int(self.__seconds) == self.__seconds:
                self.__timer_id = gobject.timeout_add_seconds(int(self.__seconds), self.__callback)
            else:
                self.__timer_id = gobject.timeout_add(int(self.__seconds * 1000), self.__callback)
            return True

        def stop(self):
            """Stop the callback from running again if it was scheduled
            to run.

            @return: True if the callback was stopped, False otherwise
            @rtype: L{bool}

            """
            if self.__timer_id is None:
                return False

            gobject.source_remove(self.__timer_id)
            self.__timer_id = None
            return True

        def change_interval(self, seconds):
            """Change the interval and restart the callback if it was scheduled
            to run.

            @param seconds: Number of seconds within each call.
            @type seconds: C{float} or C{int}

            """
            assert seconds > 0.0

            self.__seconds = seconds

            # Restart if the callback was scheduled to run
            if self.stop():
                self.start()

class BackendError(Exception):
    pass

class VolumeControlApplet:

    """Applet to control your computer's volume.

    """

    # Used to check whether the applet's icon must be updated
    __old_volume = None
    __was_muted = None

    __volume_scale_lock = threading.Lock()

    def __init__(self, applet):
        self.applet = applet

        try:
            self.backend = GStreamerBackend(self)
        except BackendError, e:
            print "Error: %s" % e
            return None
        else:
            timing = Timing()
            self.message_delay_handler = timing.delay(self.backend.freeze_messages.clear, gstreamer_freeze_messages_interval, False)

            prefs = gtk.Builder()
            prefs.add_from_file(ui_file)
            self.setup_main_dialog(prefs)
            self.setup_context_menu(prefs)

            applet.connect("scroll-event", self.icon_scroll_event_cb)
            #~ applet.connect("position-changed", lambda a, o: self.refresh_orientation())

    def icon_scroll_event_cb(self, widget, event):
        if event.direction == gdk.SCROLL_UP:
            self.backend.increase_volume()
        elif event.direction == gdk.SCROLL_DOWN:
            self.backend.decrease_volume()

    def setup_main_dialog(self, prefs):
        prefs.get_object("hbox-volume").reparent(self.applet.main_dialog)

        self.volume_scale = prefs.get_object("hscale-volume")
        self.volume_scale.props.can_focus = False

        self.volume_scale.add_mark(100, gtk.POS_BOTTOM, "<small>%s</small>" % "100%")

        self.volume_label = prefs.get_object("label-volume")
        self.mute_item = prefs.get_object("checkbutton-mute")

        self.volume_scale.connect("button-press-event", self.volume_scale_pressed_cb)
        self.volume_scale.connect("button-release-event", self.volume_scale_released_cb)
        self.volume_scale.connect("value-changed", self.volume_scale_changed_cb)
        self.volume_scale.connect("scroll-event", self.volume_scale_scroll_event_cb)
        self.mute_item.connect("toggled", self.mute_toggled_cb)

        self.applet.connect("clicked", self.clicked_cb)

    def clicked_cb(self, widget, event):
        if event.button == 1:
            self.applet.show_main_dialog()
        elif event.button == 2:
            # Toggle 'Mute' checkbutton
            self.mute_item.set_active(not self.mute_item.get_active())
        elif event.button == 3:
            self.menu.popup(None, None, None, event.button, event.time)

    def volume_scale_pressed_cb(self, widget, event):
        # Same hack as used by gnome-volume-control to make left-click behave as middle-click
        if event.button == 1:
            event.button = 2

        return False

    def volume_scale_released_cb(self, widget, event):
        # Same hack as used by gnome-volume-control to make left-click behave as middle-click
        if event.button == 1:
            event.button = 2

        volume = widget.get_value()
        self.mute_item.set_active(volume == 0)

        return False

    def volume_scale_changed_cb(self, widget):
        volume = widget.get_value()

        # Don't update if the callback was invoked via refresh_icon()
        if volume != self.backend.get_volume():
            with self.__volume_scale_lock:
                self.message_delay_handler.stop()

                self.backend.freeze_messages.set()
                self.backend.set_volume(volume)

                self.message_delay_handler.start()

    def volume_scale_scroll_event_cb(self, widget, event):
        if event.direction == gdk.SCROLL_UP:
            self.backend.increase_volume()
        elif event.direction == gdk.SCROLL_DOWN:
            self.backend.decrease_volume()
        return True

    def setup_context_menu(self, prefs):
        """Add "Open Volume Control" to the context menu.

        """
        menu = gtk.Menu() #self.applet.dialog.menu

        volume_control_item = gtk.MenuItem(_("Open Volume Control"))
        volume_control_item.connect("activate", self.show_volume_control_cb)
        volume_control_item.show_all()
        menu.append(volume_control_item)

        separator_item = gtk.SeparatorMenuItem()
        separator_item.show_all()
        menu.append(separator_item)

        preference_item = gtk.MenuItem(_("Preference"))
        preference_item.connect("activate", self.show_preferences_cb)
        preference_item.show_all()
        menu.append(preference_item)
        # Set up preferences
        self.dialog = gtk.Dialog(title=_("volume control"),
                            flags=0,
                            buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.dialog.connect("delete-event", lambda w, e: w.hide() or True)
        self.dialog.connect("response", lambda w, e: w.hide() or True)
        prefs.get_object("dialog-vbox").reparent(self.dialog.vbox)
        self.load_theme_pref(prefs)
        self.load_device_pref(prefs)
        self.load_track_pref(prefs)

        binds = {"combobox-theme": self.combobox_theme_changed_cb,
                 "combobox-device": self.combobox_device_changed_cb,
                 "combobox-mixer-track": self.combobox_track_changed_cb}
        for name, callback in binds.items():
            obj = prefs.get_object(name).connect("changed", callback)
        #~ binder = self.applet.settings.get_binder(prefs)
        #~ binder.bind("theme", "combobox-theme", key_callback=self.combobox_theme_changed_cb)
        #~ binder.bind("device", "combobox-device", key_callback=self.combobox_device_changed_cb)
        #~ binder.bind("track", "combobox-mixer-track", key_callback=self.combobox_track_changed_cb)
        #~ self.applet.settings.load_bindings(binder)

        self.menu = menu

    def show_volume_control_cb(self, widget):
        for command in volume_control_apps:
            try:
                subprocess.Popen(command)
                return
            except OSError:
                pass
        raise RuntimeError("No volume control found (%s)" % ", ".join(volume_control_apps))

    def show_preferences_cb(self, widget):
        self.dialog.show()

    def load_theme_pref(self, prefs):
        # Only use themes that are likely to provide all the files
        def filter_theme(theme):
            return os.path.isfile(os.path.join(theme_dir, theme, "scalable/status/audio-volume-high.svg"))
        themes = filter(filter_theme, os.listdir(theme_dir))
        self.themes = [system_theme_name] + sorted(themes) + sorted(os.listdir(moonbeam_theme_dir))
        
        if self.applet.get_setting("theme") not in self.themes:
            # Todo: check if there is a problem with using str() here.
            self.applet.set_setting("theme", str(system_theme_name))
        combobox_theme = prefs.get_object("combobox-theme")
        add_cell_renderer_text(combobox_theme)
        for i in self.themes:
            combobox_theme.append_text(i)
            if i == self.applet.get_setting("theme"):
                combobox_theme.set_active(self.themes.index(i))

        

        self.setup_icons()

    def load_device_pref(self, prefs):
        device_labels = self.backend.get_device_labels()

        if self.applet.get_setting("device") not in device_labels:
            self.applet.set_setting("device", self.backend.get_default_device_label())

        self.combobox_device = prefs.get_object("combobox-device")
        add_cell_renderer_text(self.combobox_device)
        for i in device_labels:
            self.combobox_device.append_text(i)
            if i == self.applet.get_setting("device"):
                self.combobox_device.set_active(device_labels.index(i))

        self.backend.set_device(self.applet.get_setting("device"))

    def load_track_pref(self, prefs):
        self.combobox_track = prefs.get_object("combobox-mixer-track")
        add_cell_renderer_text(self.combobox_track)

        self.reload_tracks()

    def reload_tracks(self):
        track_labels = self.backend.get_track_labels()

        track = self.applet.get_setting("track")
        if track not in track_labels:
            track = self.backend.get_default_track_label()

        tracks_model = self.combobox_track.get_model()
        number_old_tracks = len(tracks_model)
        self.combobox_track.get_model().clear()
        for i in track_labels:
            self.combobox_track.append_text(i)
            if i == track:
                self.combobox_track.set_active(track_labels.index(i))
        # Hackish way to delete old tracks (clear() triggers exception in configbinder)
        #~ for i in range(number_old_tracks):
            #~ del tracks_model[0]

        self.backend.set_track(track)

        # Initialize mixer track combobox
        self.applet.set_setting("track", track)

    def combobox_device_changed_cb(self, cb):
        value = cb.get_active_text()
        self.applet.set_setting("device", str(value))
        self.backend.set_device(value)
        self.reload_tracks()

    def combobox_track_changed_cb(self, cb):
        value = cb.get_active_text()
        if value == None:
            return
        self.applet.set_setting("track", value)
        self.backend.set_track(value)

    def combobox_theme_changed_cb(self, cb):
        value = cb.get_active_text()
        self.applet.set_setting("theme", value)
        self.setup_icons()
        self.refresh_icon(True)

    def refresh_icon(self, force_update=False):
        volume = self.backend.get_volume()
        muted = self.backend.is_muted() if self.backend.can_be_muted() else False

        mute_changed = self.__was_muted != muted

        # Update if the update is forced or volume/mute has changed
        if force_update or self.__old_volume != volume or mute_changed:
            if mute_changed:
                self.refresh_mute_checkbox()

            if muted or volume == 0:
                icon = title = "muted"
            else:
                title = str(volume) + "%"

                if os.path.isdir(os.path.join(moonbeam_theme_dir, self.theme)):
                    icon = str(filter(lambda i: volume >= i, moonbeam_ranges)[0])
                else:
                    icon = [key for key, value in volume_ranges if volume >= value][0]

            self.applet.set_tooltip_text(self.backend.get_current_track_label() + ": " + title)
            self.applet.set_icon(icon)

            # Update the volume label on the right of the volume scale
            self.volume_label.set_text("%d%%" % volume)

            self.volume_scale.set_value(volume)

            self.__old_volume = volume
            self.__was_muted = muted

    def setup_icons(self):
        self.theme = self.applet.get_setting("theme")

        is_moonbeam_theme = os.path.isdir(os.path.join(moonbeam_theme_dir, self.theme))
        keys = list(moonbeam_ranges) if is_moonbeam_theme else [key for key, value in volume_ranges]

        states = { "muted": "audio-volume-muted" }
        for i in map(str, keys):
            states[i] = "audio-volume-%s" % i
        self.applet.set_icon_states(states)

        theme = self.theme if self.theme != system_theme_name else None
        self.applet.set_theme(theme)

        self.refresh_orientation()

    def refresh_orientation(self):
        rotate = self.theme == "Minimal" and self.applet.get_position() in ("left", "right")
        self.applet.set_rotation(gdk.PIXBUF_ROTATE_CLOCKWISE if rotate else gdk.PIXBUF_ROTATE_NONE)

    def refresh_mute_checkbox(self):
        """Update the state of the 'Mute' checkbox.

        """
        can_be_muted = self.backend.can_be_muted()

        self.mute_item.set_sensitive(can_be_muted)

        if can_be_muted:
            self.mute_item.set_active(self.backend.is_muted())
        else:
            # Clear checkbox (this will fire the "toggled" signal)
            self.mute_item.set_active(False)

    def mute_toggled_cb(self, widget):
        """ Only (un)mute if possible (this callback can be invoked because we
        set the 'Mute' checkbox to False """
        if self.backend.can_be_muted():
            item_active = int(self.mute_item.get_active())
            self.backend.set_mute(item_active)


class GStreamerBackend:

    """GStreamer backend. Controls the current device and track, and the
    current track's volume and mute status.

    """

    __devices = {}
    __current_track = None

    def __init__(self, parent):
        self.__parent = parent

        self.freeze_messages = threading.Event()

        # Collect a set of possible mixers to use
        found_mixers = set()
        for f in gst.registry_get_default().get_feature_list(gst.ElementFactory):
            if f.get_name().endswith("mixer") and f.get_klass() == "Generic/Audio":
                found_mixers.add(f.get_name())

        # Only keep certain names and sort it in order of mixer_names' order
        useable_mixers = [i for i in mixer_names if i in found_mixers]

        if len(useable_mixers) == 0:
            parent.applet.errors.general((_("No GStreamer mixer found"), no_mixer_message % ", ".join(mixer_names)))
            raise BackendError("No GStreamer mixer found")

        mixer_devices = self.find_mixer_and_devices(useable_mixers)

        if mixer_devices is None:
            parent.applet.errors.general((_("No devices found"), no_devices_message))
            raise BackendError("No devices found")

        self.__mixer, self.__devices = mixer_devices

        # Prefer PulseAudio's volume control when using GStreamer mixer element pulsemixer
        if self.__mixer.get_factory().get_name() == "pulsemixer":
            volume_control_apps.insert(0, pa_control_app)

        # Set-up the necessary mechanism to receive volume/mute change updates
        self.__mixer.set_state(gst.STATE_READY)
        if self.__mixer.get_mixer_flags() & gst.interfaces.MIXER_FLAG_AUTO_NOTIFICATIONS:
            bus = gst.Bus()
            bus.add_signal_watch()
            bus.connect("message::element", self.message_element_cb)
            self.__mixer.set_bus(bus)
        else:
            parent.applet.timing.register(parent.refresh_icon, read_volume_interval)
        self.__mixer.set_state(gst.STATE_NULL)

    def find_mixer_and_devices(self, names):
        """Return the first GStreamer mixer element and its list of devices
        for which devices are found.

        """
        for mixer_name in names:
            mixer = gst.element_factory_make(mixer_name)
            devices = self.__find_devices(mixer)

            if len(devices) > 0:
                return (mixer, devices)

    def __find_devices(self, mixer):
        """Return a list of devices found via the given GStreamer mixer element.

        """
        if not isinstance(mixer, gst.interfaces.PropertyProbe):
            raise RuntimeError(mixer.get_factory().get_name() + " cannot probe properties")

        occurrences = defaultdict(int)
        devices = {}

        mixer.probe_property_name("device")
        for device in mixer.probe_get_values_name("device"):
            self.__init_mixer_device(mixer, device)

            if not isinstance(mixer, gst.interfaces.Mixer) or len(self.get_mixer_tracks(mixer)) == 0:
                mixer.set_state(gst.STATE_NULL)
                continue

            name = mixer.get_property("device-name")
            occurrences[name] += 1
            if occurrences[name] > 1:
                name += " (%d)" % occurrences[name]

            devices[name] = device

        return devices

    def __init_mixer_device(self, mixer, device):
        """Set the mixer to use the given device name.

        """
        mixer.set_state(gst.STATE_NULL)
        mixer.set_property("device", device)
        mixer.set_state(gst.STATE_READY)

    def message_element_cb(self, bus, message):
        if not self.freeze_messages.isSet() \
            and message.type is gst.MESSAGE_ELEMENT and message.src is self.__mixer \
            and message.structure["type"] in gst_message_types \
            and message.structure["track"] is self.__current_track:
                self.__parent.refresh_icon()

    def get_mixer_tracks(self, mixer):
        """Return those tracks of the mixer that are output tracks and have
        at least one channel. Assumes the mixer has been initialized.

        """
        assert mixer.get_state()[1] is gst.STATE_READY

        def filter_track(track):
            return bool(track.flags & gst.interfaces.MIXER_TRACK_OUTPUT) and track.num_channels > 0
        return filter(filter_track, mixer.list_tracks())

    def set_device(self, device_label):
        """Set the mixer to the device labeled by the given label.

        """
        self.__init_mixer_device(self.__mixer, self.__devices[device_label])

        self.__tracks = self.get_mixer_tracks(self.__mixer)
        self.__track_labels = [track.label for track in self.__tracks]

    def get_device_labels(self):
        """Return a list of labels of all devices that have previously
        been found.

        """
        return self.__devices.keys()

    def get_default_device_label(self):
        """Return the label of the first known device. Assumes at least
        one device has been found.

        """
        return self.get_device_labels()[0]

    def set_track(self, track_label):
        """Change the current track and enable or disable the 'Mute'
        checkbox.

        """
        for track in self.__tracks:
            if track.label == track_label:
                self.__current_track = track
                break

        self.__volume_multiplier = 100.0 / (self.__current_track.max_volume - self.__current_track.min_volume)

        self.__parent.refresh_mute_checkbox()
        self.__parent.refresh_icon(True)

    def get_current_track_label(self):
        """Return the label of the current mixer track. The current
        track is the track on which operations (getting/setting volume
        and (un)muting) are performed.

        """
        return self.__current_track.label

    def get_track_labels(self):
        """Return a list of labels of all tracks that belong to the
        device to which the GStreamer mixer element is currently set.

        """
        return self.__track_labels

    def get_default_track_label(self):
        """Return the label of the default track of the device to which
        the mixer is set. This is the master track or otherwise the
        first track of the list of known tracks.

        """
        for track in self.__tracks:
            if track.flags & gst.interfaces.MIXER_TRACK_MASTER:
                return track.label
        return self.__track_labels[0]

    def can_be_muted(self):
        return True

    def is_muted(self):
        """Return whether all channels (left and right if there are two)
        are muted.

        """
        return bool(self.__current_track.flags & gst.interfaces.MIXER_TRACK_MUTE)

    def set_mute(self, mute):
        self.__mixer.set_mute(self.__current_track, mute)

        # Update applet's icon
        self.__parent.refresh_icon(True)

    def get_gst_volume(self):
        volume_channels = self.__mixer.get_volume(self.__current_track)
        return sum(volume_channels) / len(volume_channels) - self.__current_track.min_volume

    def get_volume(self):
        return int(round(self.get_gst_volume() * self.__volume_multiplier))

    def set_gst_volume(self, volume):
        self.__mixer.set_volume(self.__current_track, (self.__current_track.min_volume + volume, ) * self.__current_track.num_channels)

    def set_volume(self, value):
        self.set_gst_volume(int(round(value / self.__volume_multiplier)))

        # Update applet's icon
        self.__parent.refresh_icon(True)

    def increase_volume(self):
        self.set_volume(min(100, self.get_volume() + volume_step))

    def decrease_volume(self):
        self.set_volume(max(0, self.get_volume() - volume_step))


class MainDialog(gtk.Window):
    def __init__(self, applet):
        self.applet_r = weakref.ref(applet)
        gtk.Window.__init__(self)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.is_shown = False
        self.hide_sid = None

    def show(self):
        self.is_shown = True
        self.hide_sid = gobject.timeout_add(10, self.hide_on_outside_click)
        return gtk.Window.show(self)

    def hide(self):
        if self.hide_sid is not None:
            gobject.source_remove(self.hide_sid)
            self.hide_sid = None
        self.is_shown = False
        return gtk.Window.hide(self)
        
    def hide_on_outside_click(self, *args):
        if self.is_shown == False:
            return False
        #~ display = gtk.gdk.display_get_default()
        #~ pos = display.get_pointer()
        pos = self.window.get_pointer()
        button_list = gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON2_MASK | \
                      gtk.gdk.BUTTON3_MASK | gtk.gdk.BUTTON4_MASK | \
                      gtk.gdk.BUTTON5_MASK
        if not pos[2] & button_list:
            # No mouse button is pressed and less than 600 ms has passed.
            # Check again in 10 ms.
            #~ gobject.timeout_add(10, self.__hide_if_not_hovered)
            return True
        a = self.get_allocation()
        if pos[0] >= 0 and pos[0] < a.width and \
           pos[1] >= 0 and pos[1] < a.height:
            return True
        if self.applet_r().pointer_is_inside():
            return True
        self.hide()
        return False
        
class DbxVolumeApplet(DockXApplet):
    """An example applet for DockbarX standalone dock"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        self.icon = gtk.Image()
        #~ self.icon.set_from_icon_name("cardapio-dark256", gtk.ICON_SIZE_DIALOG)
        #~ self.icon.set_pixel_size(self.get_size())
        self.add(self.icon)
        self.icon.show()
        self.show()
        self.icon_states = {}
        self.icon_state = None
        self.rotation = gdk.PIXBUF_ROTATE_NONE

        self.main_dialog = MainDialog(self) 
        self.vca = VolumeControlApplet(self)

    def update(self):
        self.vca.refresh_orientation()
        self.refresh_icon()

    def set_icon_states(self, states):
        self.icon_states = states

    def set_icon(self, state):
        self.icon_state = state
        self.refresh_icon()

    def refresh_icon(self):
        name = self.icon_states[self.icon_state]
        pb = self.theme.load_icon(name, self.get_size(), 0)
        if self.rotation != gdk.PIXBUF_ROTATE_NONE:
            pb = pb.rotate_simple(self.rotation)
        self.icon.set_from_pixbuf(pb)

    def set_theme(self, name):
        if name is None:
            self.theme = gtk.icon_theme_get_default()
        else:
            self.theme = gtk.IconTheme()
            self.theme.prepend_search_path(moonbeam_theme_dir)
            self.theme.set_custom_theme(name)
        #~ if self.icon_state:
            #~ self.refresh_icon()

    def set_rotation(self, rot):
        if rot != self.rotation:
            self.rotation = rot

    def show_main_dialog(self):
        if self.main_dialog.is_shown:
            # It is shown. Let's hide it.
            self.main_dialog.hide()
            return
        mgeo = gtk.gdk.screen_get_default().get_monitor_geometry(
                                                            self.get_monitor())
        
        width, height = self.main_dialog.get_size()
        wx, wy = self.window.get_origin()
        b_alloc = self.get_allocation()
        # Check that the popup is within the monitor
        if self.get_position() in ("left", "right"):
            x = b_alloc.x + wx
            y = b_alloc.y + wy + (b_alloc.height / 2) - (height / 2)
            if y + height > mgeo.y + mgeo.height:
                y = mgeo.y + mgeo.height - height
            if y < mgeo.y:
                y = mgeo.y
            if x >= mgeo.x + (mgeo.width / 2):
                x -= width
            else:
                x += b_alloc.width
        else:
            x = b_alloc.x + wx + (b_alloc.width / 2) - (width / 2)
            y = b_alloc.y + wy
            if x + width > mgeo.x + mgeo.width:
                x = mgeo.x + mgeo.width - width
            if x < mgeo.x:
                x = mgeo.x
            if y >= mgeo.y + (mgeo.height / 2):
                y = y - height
            else:
                y = y + b_alloc.height
        self.main_dialog.move(x, y)
        self.main_dialog.show()

    def pointer_is_inside(self):
        pos = self.window.get_pointer()
        a = self.get_allocation()
        if pos[0] >= a.x and pos[0] < a.x + a.width and \
           pos[1] >= a.y and pos[1] < a.y + a.height:
               return True
        return False
        

def get_dbx_applet(dbx_dict):
    global vcapplet
    try:
        vcapplet.update()
    except NameError:
        # First run, make a new instance
        vcapplet = DbxVolumeApplet(dbx_dict)
    return vcapplet
    
#~ if __name__ == "__main__":
    #~ awnlib.init_start(VolumeControlApplet, {"name": applet_name, "short": "volume-control",
        #~ "version": __version__,
        #~ "description": applet_description,
        #~ "logo": applet_logo,
        #~ "author": "onox",
        #~ "copyright-year": "2008 - 2010",
        #~ "authors": ["onox <denkpadje@gmail.com>"],
        #~ "artists": ["Jakub Steiner"]})
