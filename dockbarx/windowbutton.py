#!/usr/bin/python

#   windowbutton.py
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

import wnck
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango
import gc
gc.enable()

from common import ODict, Globals, compiz_call
from cairowidgets import CairoWindowItem

import i18n
_ = i18n.language.gettext




class WindowButton(gobject.GObject):
    __gsignals__ = {"minimized": (gobject.SIGNAL_RUN_FIRST,
                                  gobject.TYPE_NONE,()),
                    "unminimized": (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,()),
                    "needs-attention-changed": (gobject.SIGNAL_RUN_FIRST,
                                                gobject.TYPE_NONE,()),
                    "popup-hide": (gobject.SIGNAL_RUN_FIRST,
                                   gobject.TYPE_NONE,(str, )),
                    "popup-hide-request": (gobject.SIGNAL_RUN_FIRST,
                                           gobject.TYPE_NONE,()),
                    "popup-expose-request": (gobject.SIGNAL_RUN_FIRST,
                                             gobject.TYPE_NONE,()),
                    "monitor-changed": (gobject.SIGNAL_RUN_FIRST,
                                        gobject.TYPE_NONE,())}

    def __init__(self, window):
        gobject.GObject.__init__(self)
        self.globals = Globals()
        self.globals.connect('show-only-current-monitor-changed',
                             self.on_show_only_current_monitor_changed)
        self.screen = wnck.screen_get_default()
        self.name = window.get_name()
        self.window = window
        self.needs_attention = False
        self.opacified = False
        self.button_pressed = False

        self.button = CairoWindowItem(u"" + window.get_name(),
                                      window.get_mini_icon(),
                                      window.get_icon())
        self.button.set_needs_attention(window.needs_attention())
        self.button.show()
        self.button.set_preview_aspect(self.window.get_geometry()[2],
                                       self.window.get_geometry()[3])
        self.geometry_changed_event = None
        self.on_show_only_current_monitor_changed()


        #--- Events
        self.button.connect("enter-notify-event",
                                   self.on_button_mouse_enter)
        self.button.connect("leave-notify-event",
                                   self.on_button_mouse_leave)
        self.button.connect("button-press-event",
                                   self.on_window_button_press_event)
        self.button.connect("clicked",
                                   self.on_clicked)
        self.button.connect("scroll-event",
                                   self.on_window_button_scroll_event)
        self.button.connect("close-clicked", self.action_close_window)
        self.state_changed_event = self.window.connect("state-changed",
                                                self.on_window_state_changed)
        self.icon_changed_event = self.window.connect("icon-changed",
                                                self.on_window_icon_changed)
        self.name_changed_event = self.window.connect("name-changed",
                                                self.on_window_name_changed)

        #--- D'n'D
        self.button.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT, [], 0)
        self.button.connect("drag_motion", self.on_button_drag_motion)
        self.button.connect("drag_leave", self.on_button_drag_leave)
        self.button_drag_entered = False
        self.dnd_select_window = None

    def set_button_active(self, mode):
        self.button.set_is_active_window(mode)


    def is_on_current_desktop(self):
        if (self.window.get_workspace() is None \
        or self.screen.get_active_workspace() == self.window.get_workspace()) \
        and self.window.is_in_viewport(self.screen.get_active_workspace()):
            return True
        else:
            return False

    def get_monitor(self):
        if not self.globals.settings['show_only_current_monitor']:
            return 0
        gdk_screen = gtk.gdk.screen_get_default()
        win = gtk.gdk.window_lookup(self.window.get_xid())
        x, y, w, h, bit_depth = win.get_geometry()
        return gdk_screen.get_monitor_at_point(x + (w / 2), y  + (h / 2))

    def on_show_only_current_monitor_changed(self, arg=None):
        if self.globals.settings['show_only_current_monitor']:
            if self.geometry_changed_event is None:
                self.geometry_changed_event = self.window.connect(
                                'geometry-changed', self.on_geometry_changed)
        else:
            if self.geometry_changed_event is not None:
                self.window.disconnect(self.geometry_changed_event)
        self.monitor = self.get_monitor()

    def del_button(self):
        self.button.destroy()
        self.window.disconnect(self.state_changed_event)
        self.window.disconnect(self.icon_changed_event)
        self.window.disconnect(self.name_changed_event)
        if self.geometry_changed_event is not None:
            self.window.disconnect(self.geometry_changed_event)
        del self.screen
        del self.window
        del self.globals
        gc.collect()

    #### Previews

    def get_preview_alloc(self):
        return self.button.get_preview_allocation()


    #### Windows's Events
    def on_window_state_changed(self, window,changed_mask, new_state):
        try:
            state_minimized = wnck.WINDOW_STATE_MINIMIZED
        except:
            state_minimized = 1 << 0
        if state_minimized & changed_mask & new_state:
            self.button.set_minimized(True)
            self.emit('minimized')
        elif state_minimized & changed_mask:
            self.button.set_minimized(False)
            self.emit('unminimized')

        # Check if the window needs attention
        if window.needs_attention() != self.needs_attention:
            self.needs_attention = window.needs_attention()
            self.button.set_needs_attention(self.needs_attention)
            self.emit('needs-attention-changed')

    def on_window_icon_changed(self, window):
        # Creates pixbufs for minimized and normal icons
        # from the window's mini icon and set the one that should
        # be used as window_button_icon according to window state.
        self.button.set_icon(window.get_mini_icon(), window.get_icon())

    def on_window_name_changed(self, window):
        name = u""+window.get_name()
        self.button.set_name(name)


    def on_geometry_changed(self, *args):
        monitor = self.get_monitor()
        if monitor != self.monitor:
            self.monitor = monitor
            self.emit('monitor-changed')

    #### Opacify
    def opacify(self):
        # Makes all windows but the one connected
        # to this windowbutton transparent.
        if self.globals.opacity_values is None:
            try:
                self.globals.opacity_values = compiz_call(
                                        'obs/screen0/opacity_values','get')
            except:
                try:
                    self.globals.opacity_values = compiz_call(
                                        'core/screen0/opacity_values','get')
                except:
                    return
        if self.globals.opacity_matches is None:
            try:
                self.globals.opacity_matches = compiz_call(
                                        'obs/screen0/opacity_matches','get')
            except:
                try:
                    self.globals.opacity_matches = compiz_call(
                                        'core/screen0/opacity_matches','get')
                except:
                    return
        self.globals.opacified = True
        self.opacified = True
        ov = [self.globals.settings['opacify_alpha']]
        om = ["!(xid=%s)"%self.window.get_xid() + \
              " & !(class=Dockbarx_factory.py) & (type=Normal | type=Dialog)"]
        try:
            compiz_call('obs/screen0/opacity_values','set', ov)
            compiz_call('obs/screen0/opacity_matches','set', om)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', ov)
                compiz_call('core/screen0/opacity_matches','set', om)
            except:
                return

    def opacify_request(self):
        if self.window.is_minimized():
            return False
        # if self.button_pressed is true, opacity_request is called by an
        # wrongly sent out enter_notification_event sent after a
        # button_press (because of a bug in compiz).
        if self.button_pressed:
            self.button_pressed = False
            return False
        # Check if mouse cursor still is over the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            self.opacify()
        return False


    def deopacify(self):
        # always called from deopacify_request (with timeout)
        # If another window button has called opacify, don't deopacify.
        if self.globals.opacified and not self.opacified:
            return False
        if self.globals.opacity_values is None:
            return False
        try:
            compiz_call('obs/screen0/opacity_values','set',
                        self.globals.opacity_values)
            compiz_call('obs/screen0/opacity_matches','set',
                        self.globals.opacity_matches)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set',
                            self.globals.opacity_values)
                compiz_call('core/screen0/opacity_matches','set',
                            self.globals.opacity_matches)
            except:
                print "Error: Couldn't set opacity back to normal."
        self.globals.opacity_values = None
        self.globals.opacity_matches = None
        return False

    def deopacify_request(self):
        if not self.opacified:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if b_m_x >= 0 and b_m_x < b_r.width \
        and b_m_y >= 0 and b_m_y < b_r.height:
            return True
        self.globals.opacified = False
        self.opacified = False
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        gobject.timeout_add(110, self.deopacify)
        return False

    #### D'n'D
    def on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.emit('popup-expose-request')
            self.button_drag_entered = True
            self.dnd_select_window = \
                gobject.timeout_add(600,self.action_select_window)
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.button_drag_entered = False
        gobject.source_remove(self.dnd_select_window)
        self.emit('popup-expose-request')
        self.emit('popup-hide-request')


    #### Events
    def on_button_mouse_enter(self, widget, event):
        # In compiz there is a enter and
        # a leave event before a button_press event.
        # Keep that in mind when coding this def!
        if self.button_pressed :
            return
        if self.globals.settings["opacify"]:
            gobject.timeout_add(100,self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(500, self.deopacify_request)

    def on_button_mouse_leave(self, widget, event):
        # In compiz there is a enter and a leave
        # event before a button_press event.
        # Keep that in mind when coding this def!
        self.button_pressed = False
        if self.globals.settings["opacify"]:
            self.deopacify_request()

    def on_window_button_press_event(self, widget,event):
        # In compiz there is a enter and a leave event before
        # a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.on_button_mouse_enter
        # or self.on_button_mouse_leave.
        self.button_pressed = True
        gobject.timeout_add(600, self.set_button_pressed_false)

    def set_button_pressed_false(self):
        # Helper function for on_window_button_press_event.
        self.button_pressed = False
        return False

    def on_window_button_scroll_event(self, widget, event):
        if self.globals.settings["opacify"] and self.opacified:
            self.globals.opacified = False
            self.opacified = False
            self.deopacify()
        if not event.direction in (gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_DOWN):
            return
        direction = {gtk.gdk.SCROLL_UP: 'scroll_up',
                     gtk.gdk.SCROLL_DOWN: 'scroll_down'}[event.direction]
        action = self.globals.settings['windowbutton_%s'%direction]
        self.action_function_dict[action](self, widget, event)
        if self.globals.settings['windowbutton_close_popup_on_%s'%direction]:
            self.emit('popup-hide', None)

    def on_clicked(self, widget, event):
        if self.globals.settings["opacify"] and self.opacified:
            self.globals.opacified = False
            self.opacified = False
            self.deopacify()

        if not event.button in (1, 2, 3):
            return
        button = {1:'left', 2: 'middle', 3: 'right'}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = 'shift_and_'
        else:
            mod = ''
        action_str = 'windowbutton_%s%s_click_action'%(mod, button)
        action = self.globals.settings[action_str]
        self.action_function_dict[action](self, widget, event)

        popup_close = 'windowbutton_close_popup_on_%s%s_click'%(mod, button)
        if self.globals.settings[popup_close]:
            self.emit('popup-hide', None)

    #### Menu functions
    def menu_closed(self, menushell):
        self.globals.right_menu_showing = False
        self.emit('popup-hide', 'menu-closed')

    def minimize_window(self, widget=None, event=None):
        if self.window.is_minimized():
            self.window.unminimize(gtk.get_current_event_time())
        else:
            self.window.minimize()

    #### Actions
    def action_select_or_minimize_window(self, widget=None,
                                         event=None, minimize=True):
        # The window is activated, unless it is already
        # activated, then it's minimized. Minimized
        # windows are unminimized. The workspace
        # is switched if the window is on another
        # workspace.
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        if self.window.get_workspace() is not None \
        and self.screen.get_active_workspace() != self.window.get_workspace():
            self.window.get_workspace().activate(t)
        if not self.window.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.window.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),
                                      win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            # which means popup list can be left open.
            self.emit('popup-hide', 'viewport-change')
        if self.window.is_minimized():
            self.window.unminimize(t)
        elif self.window.is_active() and minimize:
            self.window.minimize()
        else:
            self.window.activate(t)

    def action_select_window(self, widget = None, event = None):
        self.action_select_or_minimize_window(widget, event, False)

    def action_close_window(self, widget=None, event=None):
        self.window.close(gtk.get_current_event_time())

    def action_maximize_window(self, widget=None, event=None):
        if self.window.is_maximized():
            self.window.unmaximize()
        else:
            self.window.maximize()

    def action_shade_window(self, widget, event):
        self.window.shade()

    def action_unshade_window(self, widget, event):
        self.window.unshade()

    def action_show_menu(self, widget, event):
        try:
            action_minimize = wnck.WINDOW_ACTION_MINIMIZE
            action_unminimize = wnck.WINDOW_ACTION_UNMINIMIZE
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_minimize = 1 << 12
            action_unminimize = 1 << 13
            action_maximize = 1 << 14
        #Creates a popup menu
        menu = gtk.Menu()
        menu.connect('selection-done', self.menu_closed)
        #(Un)Minimize
        minimize_item = None
        if self.window.get_actions() & action_minimize \
        and not self.window.is_minimized():
            minimize_item = gtk.MenuItem(_('_Minimize'))
        elif self.window.get_actions() & action_unminimize \
        and self.window.is_minimized():
            minimize_item = gtk.MenuItem(_('Un_minimize'))
        if minimize_item:
            menu.append(minimize_item)
            minimize_item.connect("activate", self.minimize_window)
            minimize_item.show()
        # (Un)Maximize
        maximize_item = None
        if not self.window.is_maximized() \
        and self.window.get_actions() & action_maximize:
            maximize_item = gtk.MenuItem(_('Ma_ximize'))
        elif self.window.is_maximized() \
        and self.window.get_actions() & action_unminimize:
            maximize_item = gtk.MenuItem(_('Unma_ximize'))
        if maximize_item:
            menu.append(maximize_item)
            maximize_item.connect("activate", self.action_maximize_window)
            maximize_item.show()
        # Close
        close_item = gtk.MenuItem(_('_Close'))
        menu.append(close_item)
        close_item.connect("activate", self.action_close_window)
        close_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.globals.right_menu_showing = True

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = ODict((
                                  ('select or minimize window',
                                            action_select_or_minimize_window),
                                  ('select window', action_select_window),
                                  ('maximize window', action_maximize_window),
                                  ('close window', action_close_window),
                                  ('show menu', action_show_menu),
                                  ('shade window', action_shade_window),
                                  ('unshade window', action_unshade_window),
                                  ('no action', action_none)
                                ))


