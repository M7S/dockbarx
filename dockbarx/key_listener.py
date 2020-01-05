#!/usr/bin/env python3

# Captures all keyboard and mouse events, including modifiers
# Adapted from http://stackoverflow.com/questions/22367358/
# Requires python-xlib

from Xlib.display import Display
from Xlib import X, XK
from Xlib.ext import record
from Xlib.protocol import rq

from time import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib
from gi.repository import GObject

from .log import logger

class KeyListener(GObject.GObject):

    __gsignals__ = {"key-released": (GObject.SignalFlags.RUN_FIRST, None,())}

    def __init__(self):
        GObject.GObject.__init__(self)
        self.disp = None
        self.abort_listen = False
        self.last_query_time = 0
        self.fail_safe_sid = None

    def fail_safe(self):
        # Fail-safe. Checks if the key release check has stopped working
        # (for exmple if query_keymap has freezed) by checking
        # how long time that has passed since the last control.
        if time() - self.last_query_time > 1:
            # It's been more than a second since the last query.
            # Something has gone wrong.
            # Remove the fail-safe
            self.fail_safe_sid = None
            # Stop listening.
            self.stop_listen_for_super_released()
            # Log the error.
            logger.exception("Error: Failed to check for key-release.")
            # And signal the key release anyway so that the user isn't
            # stuck with a big popup forever (for example).
            self.emit("key-released")
        else:
            # Everything seems fine. Let check again in a second.
            self.fail_safe_sid = GLib.timeout_add(2000, self.fail_safe)


    def listen_for_key_released(self, key, delay=20):
        if self.abort_listen:
            # Stop checking.
            return
        #Check if the key still is pressed
        kmap = self.disp.query_keymap()
        self.last_query_time = time()
        if kmap[key // 8] & (1 << (key % 8)):
            # Try again in 10 ms
            GLib.timeout_add(delay, self.listen_for_key_released, key, delay)
        else:
            # Remove the fail-safe
            if self.fail_safe_sid:
                GLib.source_remove(self.fail_safe_sid)
                self.fail_safe_sid = None
            # Signal the key release.
            self.emit("key-released")

    def stop_listen_for_super_released(self):
        self.abort_listen = True
        if self.fail_safe_sid:
            GLib.source_remove(self.fail_safe_sid)
            self.fail_safe_sid = None

    def listen_for_super_released(self):
        self.abort_listen = False
        self.disp = Display()
        XK.load_keysym_group('xf86')
        super_key = self.disp.keysym_to_keycode(XK.string_to_keysym("Super_L"))
        self.listen_for_key_released(super_key, delay=20)
        # Activate the fail-safe in case somethings
        if self.fail_safe_sid is not None:
            GLib.source_remove(self.fail_safe_sid)
        self.fail_safe_sid = GLib.timeout_add(2000, self.fail_safe)



if __name__ == "__main__":
  Listener().run()

