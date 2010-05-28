#!/usr/bin/python

#   groupbutton.py
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


import pygtk
pygtk.require('2.0')
import gtk
import gobject
import gconf
import wnck
from time import time
from xdg.DesktopEntry import DesktopEntry
import os
import gc
gc.enable()
from urllib import unquote

from windowbutton import WindowButton
from iconfactory import IconFactory
from common import ODict
from cairowidgets import CairoButton
from cairowidgets import CairoPopup
from common import Globals, compiz_call
import zg

class LauncherPathError(Exception):
    pass

class NoGioAppExistError(Exception):
    pass



class Launcher():
    def __init__(self, identifier, path):
        globals = Globals()
        self.identifier = identifier
        self.path = path
        self.app = None
        if path[:4] == "gio:":
            if path[4:] in globals.apps_by_id:
                self.app = globals.apps_by_id[path[4:]]
            else:
                raise NoGioAppExistError()
        elif os.path.exists(path):
            self.desktop_entry = DesktopEntry(path)
        else:
            raise LauncherPathError()


    def get_identifier(self):
        return self.identifier

    def set_identifier(self, identifier):
        self.identifier = identifier

    def get_path(self):
        return self.path

    def get_desktop_file_name(self):
        if self.app:
            return self.app.get_id().split('/')[-1]
        else:
            return self.path.split('/')[-1]


    def get_icon_name(self):
        if self.app:
            return self.app.get_icon()
        else:
            return self.desktop_entry.getIcon()

    def get_entry_name(self):
        if self.app:
            return self.app.get_name()
        else:
            return self.desktop_entry.getName()

    def get_executable(self):
        if self.app:
            return self.app.get_executable()

        exe = self.desktop_entry.getExec()
        l= exe.split()
        if l[0] in ('sudo','gksudo', 'gksu',
                    'java','mono',
                    'ruby','python'):
            exe = l[1]
        else:
            exe = l[0]
        exe = exe[exe.rfind('/')+1:]
        if exe.find('.')>-1:
            exe = exe[:exe.rfind('.')]
        return exe

    def launch_with_uri(self, uri):
        os.chdir(os.path.expanduser('~'))
        if self.app:
            uri = unquote(uri)
            self.app.launch_uris([uri], None)
        else:
            uri = uri.replace("%20","\ ")
            uri = unquote(uri)
            self.execute("%s %s"%(self.desktop_entry.getExec(), uri))


    def launch(self):
        os.chdir(os.path.expanduser('~'))
        if self.app:
            print "Executing", self.app.get_name()

            return self.app.launch(None, None)
        else:
            print 'Executing %s'%self.desktop_entry.getExec()
            self.execute(self.desktop_entry.getExec())

    def remove_args(self, stringToExecute):
        specials = ["%f","%F","%u","%U","%d","%D","%n","%N","%i","%c","%k","%v","%m","%M", "-caption","--view", "\"%c\""]
        return [element for element in stringToExecute.split() if element not in specials]

    def execute(self, command):
        command = self.remove_args(command)
        if os.path.isdir(command[0]):
            command = "xdg-open '%s' &"%(" ".join(command))
        else:
            command = "/bin/sh -c '%s' &"%(" ".join(command))
        os.system(command)


class GroupButton (gobject.GObject):
    """Group button takes care of a program's "button" in dockbar.

    It also takes care of the popup window and all the window buttons that
    populates it."""

    __gsignals__ = {
        "set-icongeo-win": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "set-icongeo-grp": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "set-icongeo-delay": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "delete": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
        "launch-preference": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
        "identifier-change": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "groupbutton-moved": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "launcher-dropped": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "pinned": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, str)),
        "unpinned": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, )),
        "minimize-others": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,(str, ))
    }

    def __init__(self, class_group=None, identifier=None, launcher=None, app=None):
        gobject.GObject.__init__(self)

        self.globals = Globals()
        self.globals.connect('show-only-current-desktop-changed', self.on_show_only_current_desktop_changed)
        self.globals.connect('color2-changed', self.update_popup_label)
        self.launcher = launcher
        self.class_group = class_group
        self.app = app
        if identifier:
            self.identifier = identifier
        elif launcher:
            self.identifier = launcher.get_identifier()
            # launcher.get_identifier() returns None
            # if the identifier is still unknown
        else:
            raise Exception, "Can't initiate Group button without class_group or launcher."



        # Variables
        self.windows = {}
        self.minimized_windows_count = 0
        self.minimized_state = 0
        self.has_active_window = False
        self.needs_attention = False
        self.attention_effect_running = False
        self.nextlist = None
        self.nextlist_time = None
        self.mouse_over = False
        self.opacified = False
        self.lastlaunch = None
        self.launch_effect = False
        # Compiz sends out false mouse enter messages after button is pressed.
        # This works around that bug.
        self.button_pressed = False

        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)


        #--- Button
        self.icon_factory = IconFactory(class_group, launcher, app, self.identifier)
        self.button = CairoButton()
        self.button.show_all()



        # Button events
        self.button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.button.connect("button-release-event",self.on_group_button_release_event)
        self.button.connect("button-press-event",self.on_group_button_press_event)
        self.button.connect("scroll-event",self.on_group_button_scroll_event)
        self.button.connect("size-allocate", self.on_sizealloc)
        self.button_old_alloc = self.button.get_allocation()


        #--- Popup window
        cairo_popup = CairoPopup()

        if self.globals.settings["preview"]:
            self.winlist = gtk.HBox()
            self.winlist.set_spacing(4)
        else:
            self.winlist = gtk.VBox()
            self.winlist.set_spacing(2)
        self.popup_box = gtk.VBox()
        self.popup_box.set_border_width(5)
        self.popup_box.set_spacing(2)
        self.popup_label = gtk.Label()
        self.update_name()
        self.popup_label.set_use_markup(True)
        if self.identifier:
            # Todo: add tooltip when identifier is added.
            self.popup_label.set_tooltip_text("Identifier: %s"%self.identifier)
        self.popup_box.pack_start(self.popup_label, False)
        self.popup_box.pack_start(self.winlist, False)


        self.popup = cairo_popup.window
        self.popup_showing = False
        self.popup.connect("leave-notify-event",self.on_popup_mouse_leave)
        self.popup.add(self.popup_box)


        #--- D'n'D
        # Drag and drop should handel buttons that are moved,
        # launchers that is dropped, and open popup window
        # to enable drag and drops to windows that has to be
        # raised.
        self.button.drag_dest_set(0, [], 0)
        self.button.connect("drag_motion", self.on_button_drag_motion)
        self.button.connect("drag_leave", self.on_button_drag_leave)
        self.button.connect("drag_drop", self.on_drag_drop)
        self.button.connect("drag_data_received", self.on_drag_data_received)
        self.button_drag_entered = False
        self.launcher_drag = False
        self.dnd_show_popup = None
        self.dnd_select_window = None
        self.dd_uri = None

        # The popup needs to have a drag_dest just to check
        # if the mouse is howering it during a drag-drop.
        self.popup.drag_dest_set(0, [], 0)
        self.popup.connect("drag_motion", self.on_popup_drag_motion)
        self.popup.connect("drag_leave", self.on_popup_drag_leave)

        #Make buttons drag-able
        self.button.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                    [('text/groupbutton_name', 0, 47593)],
                                    gtk.gdk.ACTION_MOVE)
        self.button.drag_source_set_icon_pixbuf(self.icon_factory.find_icon_pixbuf(32))
        self.button.connect("drag_begin", self.on_drag_begin)
        self.button.connect("drag_data_get", self.on_drag_data_get)
        self.button.connect("drag_end", self.on_drag_end)
        self.is_current_drag_source = False


    def identifier_changed(self, identifier):
        self.identifier = identifier
        self.launcher.set_identifier(identifier)
        self.popup_label.set_tooltip_text("Identifier: %s"%self.identifier)

    def update_class_group(self, class_group):
        self.class_group = class_group

    def get_class_group(self):
        return self.class_group

    def update_name(self):
        if self.launcher:
            self.name = self.launcher.get_entry_name()
        elif self.app:
            self.name = u"" + self.app.get_name()
        else:
            # Uses first half of the name, like "Amarok" from "Amarok - [SONGNAME]"
            # A program that uses a name like "[DOCUMENT] - [APPNAME]" would be
            # totally screwed up. So far no such program has been reported.
            self.name = self.class_group.get_name().split(" - ", 1)[0]
        self.popup_label.set_label("<span foreground='%s'><big><b>%s</b></big></span>"%(self.globals.colors['color2'], self.name))

    def remove_launch_effect(self):
        self.launch_effect = False
        self.update_state()
        return False

    #### State
    def update_popup_label(self, arg=None):
        self.popup_label.set_text("<span foreground='%s'><big><b>%s</b></big></span>"%(self.globals.colors['color2'], self.name))
        self.popup_label.set_use_markup(True)

    def update_state(self):
        # Checks button state and set the icon accordingly.
        win_nr = min(self.get_windows_count(), 15)
        if win_nr == 0 and not self.launcher:
            self.button.hide()
            return
        else:
            self.button.show()

        mwc = self.get_minimized_windows_count()
        if self.launcher and win_nr == 0:
            icon_mode = IconFactory.LAUNCHER
        elif (win_nr - mwc) == 0:
            icon_mode = IconFactory.ALL_MINIMIZED
        elif mwc > 0:
            icon_mode = IconFactory.SOME_MINIMIZED
        else:
            icon_mode = 0

        if self.has_active_window and win_nr>0:
            icon_active = IconFactory.ACTIVE
        else:
            icon_active = 0

        if self.needs_attention and win_nr>0:
            if self.globals.settings["groupbutton_attention_notification_type"] == 'red':
                icon_effect = IconFactory.NEEDS_ATTENTION
            elif self.globals.settings["groupbutton_attention_notification_type"] == 'nothing':
                # Do nothing
                icon_effect = 0
            else:
                self.needs_attention_anim_trigger = False
                if not self.attention_effect_running:
                    gobject.timeout_add(700, self.attention_effect)
                icon_effect = 0
        else:
            icon_effect = 0

        if self.mouse_over:
            mouse_over = IconFactory.MOUSE_OVER
        elif self.button_drag_entered and not self.launcher_drag:
            # Mouse over effect on other drag and drop
            # than launcher dnd.
            mouse_over = IconFactory.MOUSE_OVER
        else:
            mouse_over = 0

        if self.launch_effect:
            launch_effect = IconFactory.LAUNCH_EFFECT
        else:
            launch_effect = 0

        if self.launcher_drag:
            dd_effect = IconFactory.DRAG_DROPP
        else:
            dd_effect = 0


        self.state_type = icon_mode | icon_effect | icon_active | mouse_over | launch_effect | dd_effect | win_nr
        surface = self.icon_factory.surface_update(self.state_type)
        # Set the button size to the size of the surface
        if self.button.allocation.width != surface.get_width() \
        or self.button.allocation.height != surface.get_height():
            self.button.set_size_request(surface.get_width(), surface.get_height())
        self.button.update(surface)
        return

    def update_state_request(self):
        #Update state if the button is shown.
        a = self.button.get_allocation()
        if a.width>10 and a.height>10:
            self.update_state()

    def attention_effect (self):
        self.attention_effect_running = True
        if self.needs_attention:
            if self.globals.settings["groupbutton_attention_notification_type"] == 'compwater':
                x,y = self.button.window.get_origin()
                alloc = self.button.get_allocation()
                x = x + alloc.x + alloc.width/2
                y = y + alloc.y + alloc.height/2
                try:
                    compiz_call('water/allscreens/point','activate','root',self.root_xid,'x',x,'y',y)
                except:
                    pass
            elif self.globals.settings["groupbutton_attention_notification_type"] == 'blink':
                if not self.needs_attention_anim_trigger:
                    self.needs_attention_anim_trigger = True
                    surface = self.icon_factory.surface_update(IconFactory.BLINK | self.state_type)
                    self.button.update(surface)
                else:
                    self.needs_attention_anim_trigger = False
                    surface = self.icon_factory.surface_update(self.state_type)
                    self.button.update(surface)
            return True
        else:
            self.needs_attention_anim_trigger = False
            self.attention_effect_running = False
            return False

    def on_show_only_current_desktop_changed(self, arg):
        self.update_state()
        self.nextlist = None
        self.on_set_icongeo_grp()

    #### Window counts
    def get_windows_count(self):
        if not self.globals.settings["show_only_current_desktop"]:
            return len(self.windows)
        nr = 0
        for win in self.windows:
            if not self.windows[win].is_on_current_desktop():
                continue
            nr += 1
        return nr

    def get_minimized_windows_count(self):
        nr = 0
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if win.is_minimized():
                nr += 1
        return nr

    def get_unminimized_windows_count(self):
        nr = 0
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if not win.is_minimized():
                nr += 1
        return nr

    #### Window handling
    def add_window(self,window):
        if window in self.windows:
            return
        wb = WindowButton(window)
        self.windows[window] = wb
        self.winlist.pack_start(wb.window_button, True)
        if window.is_minimized():
            self.minimized_windows_count += 1
        if (self.launcher and len(self.windows)==1):
            self.class_group = window.get_class_group()
        if self.launch_effect:
            self.launch_effect = False
            gobject.source_remove(self.launch_effect_timeout)
        if window.needs_attention():
            self.on_needs_attention_changed()

        wb.connect('minimized', self.on_window_minimized, wb)
        wb.connect('unminimized', self.on_window_unminimized, wb)
        wb.connect('needs-attention-changed', self.on_needs_attention_changed)
        wb.connect('popup-hide', self.on_popup_hide)
        wb.connect('popup-expose-request', self.on_popup_expose_request)
        # Update state unless the button hasn't been shown yet.
        self.update_state_request()

        #Update popup-list if it is being shown.
        if self.popup_showing:
            if self.globals.settings["show_only_current_desktop"]:
                self.winlist.show()
                self.popup_label.show()
                for win in self.windows.values():
                    if win.is_on_current_desktop():
                        win.window_button.show_all()
                    else:
                        win.window_button.hide_all()
            else:
                self.winlist.show_all()
            gobject.idle_add(self.show_list_request)

        # Set minimize animation
        # (if the eventbox is created already, otherwice the icon animation is set in sizealloc())
        if self.button.window:
            x, y = self.button.window.get_origin()
            a = self.button.get_allocation()
            x += a.x
            y += a.y
            window.set_icon_geometry(x, y, a.width, a.height)

        if not self.class_group:
            self.update_classgroup(window.get_class_group())

    def del_window(self,window):
        if window.is_minimized():
            self.minimized_windows_count -= 1
        if self.nextlist and window in self.nextlist:
            self.nextlist.remove(window)
        self.windows[window].del_button()
        del self.windows[window]
        if self.needs_attention:
            self.on_needs_attention_changed()
        self.update_state_request()
        if self.get_unminimized_windows_count() == 0:
            if self.opacified:
                self.globals.opacified = False
                self.opacified = False
                self.deopacify()
            if self.popup_showing and self.launcher:
                # Move the popup.
                self.popup.resize(10,10)
                gobject.idle_add(self.show_list_request)
        if not self.windows and not self.launcher:
            # Remove group button.
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()

    def set_has_active_window(self, mode):
        if mode != self.has_active_window:
            self.has_active_window = mode
            if mode == False:
                for window_button in self.windows.values():
                    window_button.set_button_active(False)
            self.update_state_request()

    def on_window_minimized(self, arg, wb):
        self.minimized_windows_count+=1
        self.update_state()
        if self.popup_showing:
            wb.update_preview()

    def on_window_unminimized(self, arg, wb):
        self.minimized_windows_count-=1
        if self.popup_showing:
            gobject.timeout_add(200, wb.update_preview)
        self.update_state()

    def get_windows(self):
        if self.globals.settings["show_only_current_desktop"]:
            wins = []
            for win in self.windows:
                if self.windows[win].is_on_current_desktop():
                    wins.append(win)
            return wins
        else:
            return self.windows.keys()

    def get_unminimized_windows(self):
        wins = []
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                continue
            if not win.is_minimized():
                wins.append(win)
        return wins

    def on_needs_attention_changed(self, arg=None):
        # Checks if there are any urgent windows and changes
        # the group button looks if there are at least one
        for window in self.windows.keys():
            if window.needs_attention():
                self.needs_attention = True
                self.update_state_request()
                return True
        else:
            if self.windows.keys() == []:
                # The window needs attention already when it's added,
                # before it's been added to the list.
                self.needs_attention = True
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return True
            else:
                self.needs_attention = False
                # Update state unless the button hasn't been shown yet.
                self.update_state_request()
                return False


    def on_set_icongeo_win(self, arg=None):
        for wb in self.windows.values():
            wb.on_set_icongeo_win()

    def on_set_icongeo_grp(self, arg=None):
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                win.set_icon_geometry(0, 0, 0, 0)
                return
            alloc = self.button.get_allocation()
            if self.button.window:
                x,y = self.button.window.get_origin()
                x += alloc.x
                y += alloc.y
                win.set_icon_geometry(x, y, alloc.width, alloc.height)

    def on_set_icongeo_delay(self, arg=None):
        # This one is used during popup delay to aviod
        # thumbnails on group buttons.
        for win in self.windows:
            if self.globals.settings["show_only_current_desktop"] \
            and not self.windows[win].is_on_current_desktop():
                win.set_icon_geometry(0, 0, 0, 0)
                return
            alloc = self.button.get_allocation()
            if self.button.window:
                x, y = self.button.window.get_origin()
                x += alloc.x
                y += alloc.y
                if self.globals.orient == "h":
                    w = alloc.width
                    h = 2
                    if y<5:
                            # dockbar applet is at top of screen
                            # the area should be below the button
                            y += alloc.height + 1
                    else:
                        # the area should be above the button
                        y -= 2
                else:
                    w = 2
                    h = alloc.height
                    if x<5:
                            # dockbar applet is at the left egde of screen
                            # the area should be to the right ofthe button
                            x += alloc.width + 1
                    else:
                        # the area should be to the right of the button
                        x -= 2
                win.set_icon_geometry(x, y, w, h)

    def on_db_move(self, arg=None):
        self.on_set_icongeo_grp()

    def on_popup_expose_request(self, arg=None):
        event = gtk.gdk.Event(gtk.gdk.EXPOSE)
        event.window = self.popup.window
        event.area = self.popup.get_allocation()
        self.popup.send_expose(event)

    def on_popup_hide(self, arg=None):
        self.hide_list()

    def on_popup_hide_request(self, arg=None):
        self.hide_list_request()

    #### Show/hide list
    def show_list_request(self):
        # If mouse cursor is over the button, show popup window.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if self.popup_showing or ((b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height) \
           and not self.globals.right_menu_showing and not self.globals.dragging):
            self.show_list()
        return False

    def show_list(self):
        # Move popup to it's right spot and show it.
        offset = 3

        if self.globals.settings["preview"]:
            # Iterate gtk before loading previews so that
            # the system doesn't feel slow.
            while gtk.events_pending():
                gtk.main_iteration(False)
            for win in self.get_windows():
                self.windows[win].update_preview()
        if self.globals.settings["show_only_current_desktop"]:
            self.popup_box.show()
            self.winlist.show()
            self.popup_label.show()
            for win in self.windows.values():
                if win.is_on_current_desktop():
                    win.window_button.show_all()
                else:
                    win.window_button.hide_all()
        else:
            self.popup_box.show_all()
        self.popup.resize(10,10)
        x,y = self.button.window.get_origin()
        b_alloc = self.button.get_allocation()
        w,h = self.popup.get_size()
        if self.globals.orient == "h":
            if self.globals.settings['popup_align'] == 'left':
                x = b_alloc.x + x
            if self.globals.settings['popup_align'] == 'center':
                x = b_alloc.x + x + (b_alloc.width/2)-(w/2)
            if self.globals.settings['popup_align'] == 'right':
                x = b_alloc.x + x + b_alloc.width - w
            y = b_alloc.y + y-offset
            if x+(w)>self.screen.get_width():
                x=self.screen.get_width()-w
            if x<0:
                x = 0
            if y-h >= 0:
                self.popup.move(x,y-h)
            else:
                self.popup.move(x,y+b_alloc.height+(offset*2))
        else:
            x = b_alloc.x + x
            y = b_alloc.y + y
            if y+h>self.screen.get_height():
                y=self.screen.get_height()-h
            if x+w >= self.screen.get_width():
                self.popup.move(x - w - offset,y)
            else:
                self.popup.move(x + b_alloc.width + offset,y)

        self.popup.show()
        self.popup_showing = True
        self.on_set_icongeo_win()
        return False

    def hide_list_request(self):
        if self.popup.window == None:
            return
        # Checks if mouse cursor really isn't hovering the button
        # or the popup window anymore and hide the popup window
        # if so.
        p_m_x,p_m_y = self.popup.get_pointer()
        p_w,p_h = self.popup.get_size()
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        r = 5 #radius for the rounded corner of popup window

        # Make sure that the popup list isn't closed when
        # howering the gap between button and list.
        w,h = self.popup.get_size()
        p_x,p_y = self.popup.window.get_origin()
        offset = 3
        b_x,b_y = self.button.window.get_origin()
        if self.globals.orient == 'h' and b_m_x>=0 and b_m_x<=(b_r.width-1):
            if (p_y < b_y and b_m_y>=-offset and b_m_y<=0) \
            or (p_y > b_y and b_m_y>=(b_r.height-1) and b_m_y<=(b_r.height-1+offset)):
                gobject.timeout_add(50, self.hide_list_request)
                return
        elif self.globals.orient == 'v' and b_m_y>=0 and b_m_y<=(b_r.height-1):
            if (p_x < b_x and b_m_x>=-offset and b_m_x<=0) \
            or (p_x > b_x and b_m_x>=(b_r.width-1) and b_m_x<=(b_r.width-1+offset)):
                gobject.timeout_add(50, self.hide_list_request)
                return

        if not ((p_m_x<0 or p_m_x>(p_w-1))or(p_m_y<0 or p_m_y>(p_h-1))):
            # Mouse pointer is inside the "rectangle"
            # but check if it's still outside the rounded corners
            x = None
            y = None
            if p_m_x < r:
                x = r - p_m_x
            if (p_w - p_m_x) < r:
                x = p_m_x - (p_w - r)
            if p_m_y < r:
                y = r - p_m_y
            if (p_h - p_m_y) < r:
                y = p_m_y - (p_h - r)
            if x == None or y == None \
            or (x**2 + y**2) < (r-1)**2:
                # It's inside the rounded corners!
                return
        if not ((b_m_x<0 or b_m_x>(b_r.width-1)) or (b_m_y<0 or b_m_y>(b_r.height-1))):
            # Mouse pointer is over the group button.
            gobject.timeout_add(50, self.hide_list_request)
            # This timeout add is needed if mouse cursor leaves the
            # screen following the screen edge.
            return
        self.hide_list()
        return

    def hide_list(self):
        self.popup.hide()
        self.popup_showing = False
        self.on_set_icongeo_grp()
        if self.globals.settings["preview"] and not self.globals.settings["remember_previews"]:
            # Remove previews to save memory.
            for win in self.get_windows():
                self.windows[win].clear_preview_image()
            gc.collect()
        return False

    #### Opacify
    def opacify(self):
        # Makes all windows but the one connected to this windowbutton transparent
        if self.globals.opacity_values == None:
            try:
                self.globals.opacity_values = compiz_call('obs/screen0/opacity_values','get')
            except:
                try:
                    self.globals.opacity_values = compiz_call('core/screen0/opacity_values','get')
                except:
                    return
        if self.globals.opacity_matches == None:
            try:
                self.globals.opacity_matches = compiz_call('obs/screen0/opacity_matches','get')
            except:
                try:
                    self.globals.opacity_matches = compiz_call('core/screen0/opacity_matches','get')
                except:
                    return
        self.globals.opacified = True
        self.opacified = True
        ov = [self.globals.settings['opacify_alpha']]
        om = ["!(class=%s | class=dockbarx_factory.py)  & (type=Normal | type=Dialog)"%self.class_group.get_res_class()]
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
        if self.get_unminimized_windows_count() == 0:
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
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            self.opacify()
        return False


    def deopacify(self):
        # always called from deopacify_request (with timeout)
        # If another window button has called opacify, don't deopacify.
        if self.globals.opacified and not self.opacified:
            return False
        if self.globals.opacity_values == None:
            return False
        try:
            compiz_call('obs/screen0/opacity_values','set', self.globals.opacity_values)
            compiz_call('obs/screen0/opacity_matches','set', self.globals.opacity_matches)
        except:
            try:
                compiz_call('core/screen0/opacity_values','set', self.globals.opacity_values)
                compiz_call('core/screen0/opacity_matches','set', self.globals.opacity_matches)
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
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
            return True
        self.globals.opacified = False
        self.opacified = False
        # Wait before deopacifying in case a new windowbutton
        # should call opacify, to avoid flickering
        gobject.timeout_add(110, self.deopacify)
        return False

    #### DnD
    def on_drag_begin(self, widget, drag_context):
        self.is_current_drag_source = True
        self.globals.dragging = True
        self.hide_list()

    def on_drag_data_get(self, widget, context, selection, targetType, eventTime):
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        selection.set(selection.target, 8, name)


    def on_drag_end(self, widget, drag_context, result = None):
        self.is_current_drag_source = False
        # A delay is needed to make sure the button is
        # shown after button_drag_end has hidden it and
        # not the other way around.
        gobject.timeout_add(30, self.button.show)

    def on_drag_drop(self, wid, drag_context, x, y, t):
        if 'text/groupbutton_name' in drag_context.targets:
            self.button.drag_get_data(drag_context, 'text/groupbutton_name', t)
            drag_context.finish(True, False, t)
        elif 'text/uri-list' in drag_context.targets:
            #Drag data should already be stored in self.dd_uri
            if ".desktop" in self.dd_uri:
                # .desktop file! This is a potential launcher.
                if self.identifier:
                    name = self.identifier
                else:
                    name = self.launcher.get_path()
                #remove 'file://' and '/n' from the URI
                path = self.dd_uri[7:-2]
                path = path.replace("%20"," ")
                self.emit('launcher-dropped', path, name)
            else:
                uri = self.dd_uri
                # Remove the new line at the end
                uri = uri.rstrip()
                self.launch_item(None, None, uri)
            drag_context.finish(True, False, t)
        else:
            drag_context.finish(False, False, t)
        self.dd_uri = None
        return True

    def on_drag_data_received(self, wid, context, x, y, selection, targetType, t):
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        if selection.target == 'text/groupbutton_name':
            if selection.data != name:
                self.emit('groupbutton-moved', selection.data, name)
        elif selection.target == 'text/uri-list':
            # Uri lists are tested on first motion instead on drop
            # to check if it's a launcher.
            # The data is saved in self.dd_uri to be used again
            # if the file is dropped.
            self.dd_uri = selection.data
            if ".desktop" in selection.data:
                # .desktop file! This is a potential launcher.
                self.launcher_drag = True
            self.update_state()

    def on_button_drag_motion(self, widget, drag_context, x, y, t):
        if not self.button_drag_entered:
            self.button_drag_entered = True
            if not 'text/groupbutton_name' in drag_context.targets:
                win_nr = self.get_windows_count()
                if win_nr == 1:
                    self.dnd_select_window = gobject.timeout_add(600, self.windows.values()[0].action_select_window)
                elif win_nr > 1:
                    self.dnd_show_popup = gobject.timeout_add(self.globals.settings['popup_delay'], self.show_list)
            if 'text/groupbutton_name' in drag_context.targets \
            and not self.is_current_drag_source:
                self.launcher_drag = True
                self.update_state()
            elif 'text/uri-list' in drag_context.targets:
                # We have to get the data find out if this
                # is a launcher or something else.
                self.button.drag_get_data(drag_context, 'text/uri-list', t)
                # No update_state() here!
            else:
                self.update_state()
        if 'text/groupbutton_name' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_MOVE, t)
        elif 'text/uri-list' in drag_context.targets:
            drag_context.drag_status(gtk.gdk.ACTION_COPY, t)
        else:
            drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_button_drag_leave(self, widget, drag_context, t):
        self.launcher_drag = False
        self.button_drag_entered = False
        self.update_state()
        self.hide_list_request()
        if self.dnd_show_popup != None:
            gobject.source_remove(self.dnd_show_popup)
            self.dnd_show_popup = None
        if self.dnd_select_window != None:
            gobject.source_remove(self.dnd_select_window)
            self.dnd_select_window = None
        if self.is_current_drag_source:
            # If drag leave signal is given because of a drop,
            # a small delay is needed since
            # drag-end isn't called if
            # the destination is hidden just before
            # the drop is completed.
            gobject.timeout_add(20, self.button.hide)

    def on_popup_drag_motion(self, widget, drag_context, x, y, t):
        drag_context.drag_status(gtk.gdk.ACTION_PRIVATE, t)
        return True

    def on_popup_drag_leave(self, widget, drag_context, t):
        self.hide_list_request()


    #### Events
    def on_sizealloc(self,applet,allocation):
        # Sends the new size to icon_factory so that a new icon in the right
        # size can be found. The icon is then updated.
        if self.button_old_alloc != self.button.get_allocation():
            if self.globals.orient == "v" \
            and allocation.width>10 and allocation.width < 220 \
            and allocation.width != self.button_old_alloc.width:
                # A minimium size on 11 is set to stop unnecessary calls
                # work when the button is created
                self.icon_factory.set_size(allocation.width)
                self.update_state()
            elif self.globals.orient == "h" \
            and allocation.height>10 and allocation.height<220\
            and allocation.height != self.button_old_alloc.height:
                self.icon_factory.set_size(allocation.height)
                self.update_state()
            self.button_old_alloc = allocation

            # Update icon geometry
            self.on_set_icongeo_grp()

    def on_button_mouse_enter (self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        if self.button_pressed :
            return
        self.mouse_over = True
        self.update_state()
        if self.globals.settings["opacify"] and self.globals.settings["opacify_group"]:
            gobject.timeout_add(self.globals.settings['popup_delay'],self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(self.globals.settings['popup_delay']+500, self.deopacify_request)

        if self.get_windows_count() <= 1 and self.globals.settings['no_popup_for_one_window']:
            return
        # Prepare for popup window
        if self.globals.settings["popup_delay"]>0:
            self.on_set_icongeo_delay()
        if not self.globals.right_menu_showing and not self.globals.dragging:
            gobject.timeout_add(self.globals.settings['popup_delay'], self.show_list_request)

    def on_button_mouse_leave (self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        self.button_pressed = False
        self.mouse_over = False
        self.update_state()
        self.hide_list_request()
        if self.popup.window == None:
            # self.hide_list takes care of emitting 'set-icongeo-grp' normally
            # but if no popup window exist its taken care of here.
            self.on_set_icongeo_grp()
        if self.globals.settings["opacify"] and self.globals.settings["opacify_group"]:
            self.deopacify_request()

    def on_popup_mouse_leave (self,widget,event):
        self.hide_list_request()

    def on_group_button_scroll_event (self,widget,event):
        if event.direction == gtk.gdk.SCROLL_UP:
            action = self.globals.settings['groupbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = self.globals.settings['groupbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)

    def on_group_button_release_event(self, widget, event):
        # Check that the mouse still is over the group button.
        b_m_x,b_m_y = self.button.get_pointer()
        b_r = self.button.get_allocation()
        if not ((b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height)):
            return

        # If a drag and drop just finnished set self.draggin to false
        # so that left clicking works normally again
        if event.button == 1 and self.globals.dragging:
            self.globals.dragging = False
            return

        if not event.button in (1, 2, 3):
            return
        button = {1:'left', 2: 'middle', 3: 'right'}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = 'shift_and_'
        else:
            mod = ''
        if not self.globals.settings['groupbutton_%s%s_click_double'%(mod, button)]:
            # No double click required, go ahead and do the action.
            action = self.globals.settings['groupbutton_%s%s_click_action'%(mod, button)]
            self.action_function_dict[action](self, widget, event)


    def on_group_button_press_event(self,widget,event):
        # In compiz there is a enter and a leave event before a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.button_mouse_enter or self.on_button_mouse_leave.
        self.button_pressed = True
        gobject.timeout_add(600, self.set_button_pressed_false)

        if not event.button in (1, 2, 3):
            return True
        button = {1:'left', 2: 'middle', 3: 'right'}[event.button]
        if event.state & gtk.gdk.SHIFT_MASK:
            mod = 'shift_and_'
        else:
            mod = ''
        if event.type == gtk.gdk._2BUTTON_PRESS:
            if self.globals.settings['groupbutton_%s%s_click_double'%(mod, button)]:
                # This is a double click and the action requires a double click.
                # Go ahead and do the action.
                action = self.globals.settings['groupbutton_%s%s_click_action'%(mod, button)]
                self.action_function_dict[action](self, widget, event)
        elif event.button == 1:
            # Return False so that a drag-and-drop can be initiated if needed.
            return False
        return True

    def set_button_pressed_false(self):
        # Helper function to group_button_press_event.
        self.button_pressed = False
        return False

    #### Menu functions
    def menu_closed(self, menushell):
        self.globals.right_menu_showing = False

    def unminimize_all_windows(self, widget=None, event=None):
        t = gtk.get_current_event_time()
        for window in self.get_windows():
            if window.is_minimized():
                window.unminimize(t)

    def change_identifier(self, widget=None, event=None):
        self.emit('identifier-change', self.launcher.get_path(), self.identifier)

    def add_launcher(self, widget=None, event=None):
        path = "gio:" + self.app.get_id()[:self.app.get_id().rfind('.')].lower()
        self.launcher = Launcher(self.identifier, path)
        self.emit('pinned', self.identifier, path)

    def launch_item(self, button, event, uri):
        uri = str(uri)
        if uri.startswith('file://'):
            uri = uri[7:]

        if self.app:
            uri = uri.replace("%20"," ")
            self.app.launch_uris([uri], None)
        else:
            self.launcher.launch_with_uri(uri)
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000, self.remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000, self.remove_launch_effect)

    #### Actions
    def action_select(self, widget, event):
        wins = self.get_windows()
        if (self.launcher and not wins):
            self.action_launch_application()
        # One window
        elif len(wins) == 1:
            if self.globals.settings["select_one_window"] == "select window":
                self.windows[wins[0]].action_select_window(widget, event)
            elif self.globals.settings["select_one_window"] == "select or minimize window":
                self.windows[wins[0]].action_select_or_minimize_window(widget, event)
        # Multiple windows
        elif len(wins) > 1:
            if self.globals.settings["select_multiple_windows"] == "select all":
                self.action_select_or_minimize_group(widget, event, minimize=False)
            elif self.globals.settings["select_multiple_windows"] == "select or minimize all":
                self.action_select_or_minimize_group(widget, event, minimize=True)
            elif self.globals.settings["select_multiple_windows"] == "compiz scale":
                umw = self.get_unminimized_windows()
                if len(umw) == 1:
                    if self.globals.settings["select_one_window"] == "select window":
                        self.windows[umw[0]].action_select_window(widget, event)
                    elif self.globals.settings["select_one_window"] == "select or minimize window":
                        self.windows[umw[0]].action_select_or_minimize_window(widget, event)
                elif len(umw) == 0:
                    self.action_select_or_minimize_group(widget, event)
                else:
                    self.action_compiz_scale_windows(widget, event)
            elif self.globals.settings["select_multiple_windows"] == "cycle through windows":
                self.action_select_next(widget, event)
            elif self.globals.settings["select_multiple_windows"] == "show popup":
                self.action_select_popup(widget, event)

    def action_select_popup(self, widget, event):
        if self.popup_showing is True:
            self.hide_list()
        else:
            self.show_list()

    def action_select_or_minimize_group(self, widget, event, minimize=True):
        # Brings up all windows or minizes them is they are already on top.
        # (Launches the application if no windows are open)
        if self.globals.settings['show_only_current_desktop']:
            mode = 'ignore'
        else:
            mode = self.globals.settings['workspace_behavior']
        screen = self.screen
        windows_stacked = screen.get_windows_stacked()
        grp_win_stacked = []
        ignorelist = []
        minimized_win_cnt = self.minimized_windows_count
        moved = False
        grtop = False
        wingr = False
        active_workspace = screen.get_active_workspace()

        # Check if there are any uminimized windows, unminimize
        # them (unless they are on another workspace and work-
        # space behavior is somehting other than move) and
        # return.
        unminimized = False
        if minimized_win_cnt > 0:
            for win in self.windows:
                if win.is_minimized():
                    ignored = False
                    if not win.is_pinned() and win.get_workspace() != None \
                       and screen.get_active_workspace() != win.get_workspace():
                        if mode == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                    if not ignored:
                        win.unminimize(event.time)
                        unminimized = True
        if unminimized:
            return

        # Make a list of the windows in group with the bottom most
        # first and top most last.
        # If mode is other than move
        # windows on other workspaces is put in a separate list instead.
        # grtop is set to true if not all windows in the group is the
        # topmost windows.
        for win in windows_stacked:
            if (not win.is_skip_tasklist()) and (not win.is_minimized()) \
            and (win.get_window_type() in [wnck.WINDOW_NORMAL,wnck.WINDOW_DIALOG]):
                if win in self.windows:
                    ignored = False
                    if not win.is_pinned() and win.get_workspace() != None \
                       and active_workspace != win.get_workspace():
                        if mode == 'move':
                            win.move_to_workspace(screen.get_active_workspace())
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)
                    if not win.is_in_viewport(screen.get_active_workspace()):
                        if mode == 'move':
                            win_x,win_y,win_w,win_h = win.get_geometry()
                            win.set_geometry(0,3,win_x%screen.get_width(),
                                             win_y%screen.get_height(),
                                             win_w,win_h)
                            moved = True
                        else: # mode == 'ignore' or 'switch'
                            ignored = True
                            ignorelist.append(win)

                    if not ignored:
                        grp_win_stacked.append(win)
                        if wingr == False:
                            wingr = True
                            grtop = True
                else:
                    if wingr:
                        grtop = False

        if not grp_win_stacked and mode == 'switch':
            # Put the windows in dictionaries according to workspace and viewport
            # so we can compare which workspace and viewport that has most windows.
            workspaces ={}
            for win in self.windows:
                if win.get_workspace() == None:
                    continue
                workspace = win.get_workspace()
                win_x,win_y,win_w,win_h = win.get_geometry()
                vpx = win_x/screen.get_width()
                vpy = win_y/screen.get_height()
                if not workspace in workspaces:
                    workspaces[workspace] = {}
                if not vpx in workspaces[workspace]:
                    workspaces[workspace][vpx] = {}
                if not vpy in workspaces[workspace][vpx]:
                    workspaces[workspace][vpx][vpy] = []
                workspaces[workspace][vpx][vpy].append(win)
            max = 0
            x = 0
            y = 0
            new_workspace = None
            # Compare which workspace and viewport that has most windows.
            ignorelist.reverse() # Topmost window first.
            for workspace in workspaces:
                for xvp in workspaces[workspace]:
                    for yvp in workspaces[workspace][xvp]:
                        nr = len (workspaces[workspace][xvp][yvp])
                        if nr > max:
                            max = nr
                            x = screen.get_width() * xvp
                            y = screen.get_height() * yvp
                            new_workspace = workspace
                            grp_win_stacked = workspaces[workspace][xvp][yvp]
                        elif nr == max:
                            # Check wether this workspace or previous workspace
                            # with the same amount of windows has been activated
                            # later.
                            for win in ignorelist:
                                if win in grp_win_stacked:
                                    break
                                if win in workspaces[workspace][xvp][yvp]:
                                    x = screen.get_width() * xvp
                                    y = screen.get_height() * yvp
                                    new_workspace = workspace
                                    grp_win_stacked = workspaces[workspace][xvp][yvp]
                                    break
            if new_workspace != screen.get_active_workspace():
                new_workspace.activate(event.time)
            screen.move_viewport(x, y)
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            if not (x == 0 and y == 0):
                self.hide_list()
            for win in grp_win_stacked:
                if win.is_minimized():
                    win.unminimize(event.time)
                    unminimized = True
            if unminimized:
                return
            ordered_list = []
            ignorelist.reverse() #Bottommost window fist again.
            for win in ignorelist:
                if win in grp_win_stacked:
                    ordered_list.append(win)
            grp_win_stacked = ordered_list

        if grtop and not moved and minimize:
            for win in grp_win_stacked:
                self.windows[win].window.minimize()
        if not grtop:
            for win in grp_win_stacked:
                self.windows[win].window.activate(event.time)

    def action_select_only(self, widget, event):
        self.action_select_or_minimize_group(widget, event, False)

    def action_select_or_compiz_scale(self, widget, event):
        wins = self.get_unminimized_windows()
        if  len(wins) > 1:
            self.action_compiz_scale_windows(widget, event)
        elif len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)

    def action_minimize_all_windows(self,widget=None, event=None):
        for window in self.get_windows():
            window.minimize()

    def action_maximize_all_windows(self,widget=None, event=None):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        maximized = False
        for window in self.get_windows():
            if not window.is_maximized() \
            and window.get_actions() & action_maximize:
                window.maximize()
                maximized = True
        if not maximized:
            for window in self.windows:
                window.unmaximize()

    def action_select_next(self, widget=None, event=None, previous=False):
        if not self.get_windows():
            return
        if self.nextlist_time == None or time() - self.nextlist_time > 2 \
        or self.nextlist == None:
            self.nextlist = []
            minimized_list = []
            screen = self.screen
            windows_stacked = screen.get_windows_stacked()
            wins = self.get_windows()
            for win in windows_stacked:
                    if win in wins:
                        if win.is_minimized():
                            minimized_list.append(win)
                        else:
                            self.nextlist.append(win)
            # Reverse -> topmost window first
            self.nextlist.reverse()
            # Add minimized windows last.
            self.nextlist.extend(minimized_list)
        self.nextlist_time = time()

        if previous:
            win = self.nextlist.pop(-1)
            if win.is_active():
                self.nextlist.insert(0, win)
                win = self.nextlist.pop(-1)
        else:
            win = self.nextlist.pop(0)
            if win.is_active():
                self.nextlist.append(win)
                win = self.nextlist.pop(0)
        # Just a safety check
        if not win in self.windows:
            return
        self.windows[win].action_select_window(widget, event)
        if previous:
            self.nextlist.insert(0, win)
        else:
            self.nextlist.append(win)

    def action_select_previous(self, widget=None, event=None):
        self.action_select_next(widget, event, previous=True)

    def action_close_all_windows(self, widget=None, event=None):
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        for window in self.get_windows():
            window.close(t)

    def action_launch_application(self, widget=None, event=None):
        if self.lastlaunch != None \
        and time() - self.lastlaunch < 2:
                return
        if self.launcher:
            self.launcher.launch()
        elif self.app:
            self.app.launch(None, None)
        else:
            return
        self.lastlaunch = time()
        self.launch_effect = True
        self.update_state()
        if self.windows:
            self.launch_effect_timeout = gobject.timeout_add(2000, self.remove_launch_effect)
        else:
            self.launch_effect_timeout = gobject.timeout_add(10000, self.remove_launch_effect)


    def action_show_menu(self, widget, event):
        try:
            action_maximize = wnck.WINDOW_ACTION_MAXIMIZE
        except:
            action_maximize = 1 << 14
        self.hide_list()
        #Creates a popup menu
        menu = gtk.Menu()
        menu.connect('selection-done', self.menu_closed)
        if self.app and not self.launcher:
            #Add launcher item
            add_launcher_item = gtk.MenuItem('_Pin application')
            menu.append(add_launcher_item)
            add_launcher_item.connect("activate", self.add_launcher)
            add_launcher_item.show()
        if self.launcher or self.app:
            #Launch program item
            launch_program_item = gtk.MenuItem('_Launch application')
            menu.append(launch_program_item)
            launch_program_item.connect("activate", self.action_launch_application)
            launch_program_item.show()
        if self.launcher:
            #Remove launcher item
            remove_launcher_item = gtk.MenuItem('Unpin application')
            menu.append(remove_launcher_item)
            remove_launcher_item.connect("activate", self.action_remove_launcher)
            remove_launcher_item.show()
            #Edit identifier item
            edit_identifier_item = gtk.MenuItem('Edit Identifier')
            menu.append(edit_identifier_item)
            edit_identifier_item.connect("activate", self.change_identifier)
            edit_identifier_item.show()

        # Recent and most used files
        if self.app or self.launcher:
            if self.app:
                appname = self.app.get_id().split('/')[-1]
            else:
                appname = self.launcher.get_desktop_file_name()
            recent_files = zg.get_recent_for_app(appname)
            most_used_files = zg.get_most_used_for_app(appname)
            #Separator
            if recent_files or most_used_files:
                sep = gtk.SeparatorMenuItem()
                menu.append(sep)
                sep.show()
            for files, menu_name in ((recent_files, 'Recent'), (most_used_files, 'Most used')):
                if files:
                    submenu = gtk.Menu()
                    menu_item = gtk.MenuItem(menu_name)
                    menu_item.set_submenu(submenu)
                    menu.append(menu_item)
                    menu_item.show()

                    for ev in files:
                        for subject in ev.get_subjects():
                            label = subject.text or subject.uri
                            if len(label)>40:
                                label = label[:20]+"..."+label[-17:]
                            submenu_item = gtk.MenuItem(label, use_underline=False)
                            submenu.append(submenu_item)
                            # "activate" doesn't seem to work on sub menus
                            # so "button-press-event" is used instead.
                            submenu_item.connect("button-press-event", self.launch_item, subject.uri)
                            submenu_item.show()

        if (self.launcher or self.app) and self.windows:
            #Separator
            sep = gtk.SeparatorMenuItem()
            menu.append(sep)
            sep.show()
        # Windows stuff
        win_nr = self.get_windows_count()
        if win_nr:
            if win_nr == 1:
                t = "window"
            else:
                t = "all windows"
            if self.get_unminimized_windows_count() == 0:
                # Unminimize all
                unminimize_all_windows_item = gtk.MenuItem('Un_minimize %s'%t)
                menu.append(unminimize_all_windows_item)
                unminimize_all_windows_item.connect("activate", self.unminimize_all_windows)
                unminimize_all_windows_item.show()
            else:
                # Minimize all
                minimize_all_windows_item = gtk.MenuItem('_Minimize %s'%t)
                menu.append(minimize_all_windows_item)
                minimize_all_windows_item.connect("activate", self.action_minimize_all_windows)
                minimize_all_windows_item.show()
            # (Un)Maximize all
            for window in self.windows:
                if not window.is_maximized() \
                and window.get_actions() & action_maximize:
                    maximize_all_windows_item = gtk.MenuItem('Ma_ximize %s'%t)
                    break
            else:
                maximize_all_windows_item = gtk.MenuItem('Unma_ximize %s'%t)
            menu.append(maximize_all_windows_item)
            maximize_all_windows_item.connect("activate", self.action_maximize_all_windows)
            maximize_all_windows_item.show()
            # Close all
            close_all_windows_item = gtk.MenuItem('_Close %s'%t)
            menu.append(close_all_windows_item)
            close_all_windows_item.connect("activate", self.action_close_all_windows)
            close_all_windows_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.globals.right_menu_showing = True

    def action_remove_launcher(self, widget=None, event=None):
        print 'Removing launcher ', self.identifier
        if self.identifier:
            name = self.identifier
        else:
            name = self.launcher.get_path()
        self.launcher = None
        if not self.windows:
            self.hide_list()
            self.icon_factory.remove()
            del self.icon_factory
            self.popup.destroy()
            self.button.destroy()
            self.winlist.destroy()
            self.emit('delete', name)
        else:
            self.emit('unpinned', name)

    def action_minimize_all_other_groups(self, widget, event):
        self.hide_list()
        self.emit('minimize-others', self)

    def action_compiz_scale_windows(self, widget, event):
        wins = self.get_unminimized_windows()
        if not self.class_group or not wins:
            return
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return
        if self.globals.settings['show_only_current_desktop']:
            path = 'scale/allscreens/initiate_key'
        else:
            path = 'scale/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                        'iclass=%s'%self.class_group.get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay'] + 200, self.hide_list)

    def action_compiz_shift_windows(self, widget, event):
        wins = self.get_unminimized_windows()
        if not self.class_group or not wins:
            return
        if len(wins) == 1:
            self.windows[wins[0]].action_select_window(widget, event)
            return

        if self.globals.settings['show_only_current_desktop']:
            path = 'shift/allscreens/initiate_key'
        else:
            path = 'shift/allscreens/initiate_all_key'
        try:
            compiz_call(path, 'activate','root', self.root_xid,'match', \
                        'iclass=%s'%self.class_group.get_res_class())
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay']+ 200, self.hide_list)

    def action_compiz_scale_all(self, widget, event):
        try:
            compiz_call('scale/allscreens/initiate_key','activate','root', self.root_xid)
        except:
            return
        # A new button enter signal is sent when compiz is called,
        # a delay is therefor needed.
        gobject.timeout_add(self.globals.settings['popup_delay']+ 200, self.hide_list)

    def action_dbpref (self,widget=None, event=None):
        # Preferences dialog
        self.emit('launch-preference')

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = ODict((
                                  ("select", action_select),
                                  ("close all windows", action_close_all_windows),
                                  ("minimize all windows", action_minimize_all_windows),
                                  ("maximize all windows", action_maximize_all_windows),
                                  ("launch application", action_launch_application),
                                  ("show menu", action_show_menu),
                                  ("remove launcher", action_remove_launcher),
                                  ("select next window", action_select_next),
                                  ("select previous window", action_select_previous),
                                  ("minimize all other groups", action_minimize_all_other_groups),
                                  ("compiz scale windows", action_compiz_scale_windows),
                                  ("compiz shift windows", action_compiz_shift_windows),
                                  ("compiz scale all", action_compiz_scale_all),
                                  ("show preference dialog", action_dbpref),
                                  ("no action", action_none)
                                ))