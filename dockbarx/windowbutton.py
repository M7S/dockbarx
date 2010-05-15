#!/usr/bin/python
import wnck
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango
import gc
gc.enable()

from common import ODict, Globals
from cairowidgets import CairoWindowButton

try:
    from ctypes.util import find_library
    import ctypes
    libgdk = ctypes.cdll.LoadLibrary(find_library("gdk-x11-2.0"))
    libX11 = ctypes.cdll.LoadLibrary(find_library("X11"))
    libXcomposite = ctypes.cdll.LoadLibrary(find_library("Xcomposite"))
except:
    print "Failed loading libraries needed for preview."


class WindowButton(gobject.GObject):
    __gsignals__ = {
                    "minimized": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
                    "unminimized": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
                    "needs-attention-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
                    "popup-hide": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
                    "popup-hide-request": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
                    "popup-expose-request": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,())
                   }
    """WindowButton takes care of a window, shows up an icon and name in popup window."""
    def __init__(self, window):
        gobject.GObject.__init__(self)
        self.globals = Globals()
        self.globals.connect('color-changed', self.update_label_state)
        self.screen = wnck.screen_get_default()
        self.preview = False
        self.name = window.get_name()
        self.window = window
        self.locked = False
        self.is_active_window = False
        self.needs_attention = False
        self.opacified = False
        self.button_pressed = False

        self.window_button = CairoWindowButton()
        self.label = gtk.Label()
        self.label.set_alignment(0, 0.5)
        self.on_window_name_changed(self.window)

        if window.needs_attention():
            self.needs_attention = True

        self.window_button_icon = gtk.Image()
        self.on_window_icon_changed(window)
        hbox = gtk.HBox()
        hbox.pack_start(self.window_button_icon, False, padding = 2)
        hbox.pack_start(self.label, True, True)
        if self.globals.settings["preview"]:
            self.preview = True
            vbox = gtk.VBox()
            vbox.pack_start(hbox, False)
            self.preview_image =  gtk.Image()
            vbox.pack_start(self.preview_image, True, True, padding = 4)
            self.window_button.add(vbox)
            # Fixed with of self.label.
            self.label.set_ellipsize(pango.ELLIPSIZE_END)
        else:
            self.window_button.add(hbox)


        self.update_label_state()


        #--- Events
        self.window_button.connect("enter-notify-event",self.on_button_mouse_enter)
        self.window_button.connect("leave-notify-event",self.on_button_mouse_leave)
        self.window_button.connect("button-press-event",self.on_window_button_press_event)
        self.window_button.connect("button-release-event",self.on_window_button_release_event)
        self.window_button.connect("scroll-event",self.on_window_button_scroll_event)
        self.state_changed_event = self.window.connect("state-changed",self.on_window_state_changed)
        self.icon_changed_event = self.window.connect("icon-changed",self.on_window_icon_changed)
        self.name_changed_event = self.window.connect("name-changed",self.on_window_name_changed)

        #--- D'n'D
        self.window_button.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT, [], 0)
        self.window_button.connect("drag_motion", self.on_button_drag_motion)
        self.window_button.connect("drag_leave", self.on_button_drag_leave)
        self.button_drag_entered = False
        self.dnd_select_window = None


    def set_button_active(self, mode):
        """Use set_button_active to tell WindowButton that it's window is the active one."""
        self.is_active_window = mode
        self.update_label_state()

    def update_label_state(self, arg=None):
        """Updates the style of the label according to window state."""
        attr_list = pango.AttrList()
        if self.needs_attention:
            attr_list.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, 50))
        if self.is_active_window:
            color = self.globals.colors['color3']
        elif self.window.is_minimized():
            color = self.globals.colors['color4']
        else:
            color = self.globals.colors['color2']
        # color is a hex-string (like '#FFFFFF').
        r = int(color[1:3], 16)*256
        g = int(color[3:5], 16)*256
        b = int(color[5:7], 16)*256
        attr_list.insert(pango.AttrForeground(r, g, b, 0, 50))
        self.label.set_attributes(attr_list)



    def is_on_current_desktop(self):
        if (self.window.get_workspace() == None \
        or self.screen.get_active_workspace() == self.window.get_workspace()) \
        and self.window.is_in_viewport(self.screen.get_active_workspace()):
            return True
        else:
            return False

    def del_button(self):
        self.window_button.destroy()
        self.window.disconnect(self.state_changed_event)
        self.window.disconnect(self.icon_changed_event)
        self.window.disconnect(self.name_changed_event)
        del self.icon
        del self.icon_locked
        del self.icon_transp
        del self.screen
        del self.window
        del self.preview
        del self.globals
        gc.collect()

    #### Previews
    def get_screenshot_xcomposite(self, screen, window, size=200):
        ''' Get the window pixmap of window from the X compositor extension, return
            it as a gdk.pixbuf.
        '''
        # Parts of this are ported from Talika (C) 2009-2010 Sinew Software Systems
        if None in [libgdk, libXcomposite, libX11]:
            return None
        display = screen.get_display()
        xdisplay = libgdk.gdk_x11_display_get_xdisplay(hash(display))
        xid = window.get_xid()

        libgdk.gdk_error_trap_push()
        # Call the X function which may cause an error here ...
        p_xid = libXcomposite.XCompositeNameWindowPixmap(xdisplay, xid)
        # Flush the X queue to catch errors now.
        libgdk.gdk_flush()
        errors = libgdk.gdk_error_trap_pop()
        if errors:
            pixmap = None
        else:
            pixmap = gtk.gdk.pixmap_foreign_new_for_display(display, p_xid)
        if not pixmap:
            return None

        depth = pixmap.get_depth()
        if depth <= 24:
            cmap = screen.get_rgb_colormap()
        else:
            cmap = screen.get_rgba_colormap()
        w, h = pixmap.get_size()
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
        pixbuf.get_from_drawable(pixmap, cmap, 0, 0, 0, 0, w, h)

        if w >= h:
            if w > size:
                h = int(h * size/w)
                w = size
        else:
            if h > size:
                w = int(w * size/h)
                h = size
        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)

        del pixmap
        libX11.XFreePixmap(xdisplay, p_xid)
        return pixbuf

    def update_preview(self, size=None):
        if not self.preview:
            return False
        if size == None:
            size = self.globals.settings["preview_size"]
        pixbuf = None
        scn = gtk.gdk.screen_get_default()
        if not self.window.is_minimized() and scn.is_composited():
            pixbuf = self.get_screenshot_xcomposite(scn, self.window, size)
        else:
            pixbuf = self.preview_image.get_pixbuf()
        if pixbuf == None:
            pixbuf = self.window.get_icon()
        self.preview_image.set_from_pixbuf(pixbuf)
        self.preview_image.set_size_request(size,size)
        del pixbuf
        gc.collect()

    def clear_preview_image(self):
        if not self.preview:
            return False
        self.preview_image.clear()
        gc.collect()

    #### Windows's Events
    def on_window_state_changed(self, window,changed_mask, new_state):
        try:
            state_minimized = wnck.WINDOW_STATE_MINIMIZED
        except:
            state_minimized = 1 << 0
        if state_minimized & changed_mask & new_state:
            if self.locked:
                self.window_button_icon.set_from_pixbuf(self.icon_locked)
            else:
                self.window_button_icon.set_from_pixbuf(self.icon_transp)
            self.update_label_state()
            self.emit('minimized')
        elif state_minimized & changed_mask:
            self.window_button_icon.set_from_pixbuf(self.icon)
            self.update_label_state()
            self.emit('unminimized')

        # Check if the window needs attention
        if window.needs_attention() != self.needs_attention:
            self.needs_attention = window.needs_attention()
            self.update_label_state()
            self.emit('needs-attention-changed')

    def on_window_icon_changed(self, window):
        # Creates pixbufs for minimized, locked and normal icons
        # from the window's mini icon and set the one that should
        # be used as window_button_icon according to window state.
        self.icon = window.get_mini_icon()
        pixbuf = self.icon.copy()
        self.icon_transp = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, pixbuf.get_width(), pixbuf.get_height())
        self.icon_transp.fill(0x00000000)
        pixbuf.composite(self.icon_transp, 0, 0, pixbuf.get_width(), pixbuf.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 190)
        self.icon_transp.saturate_and_pixelate(self.icon_transp, 0.12, False)

        i = gtk.Invisible()
        lock = i.render_icon(gtk.STOCK_DIALOG_AUTHENTICATION,gtk.ICON_SIZE_BUTTON)
        if pixbuf.get_height() != lock.get_height() or pixbuf.get_width() != lock.get_width():
            lock = lock.scale_simple(pixbuf.get_width(), pixbuf.get_height(), gtk.gdk.INTERP_BILINEAR)
        self.icon_locked = self.icon_transp.copy()
        lock.composite(self.icon_locked, 0, 0, lock.get_width(), lock.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)

        if self.locked:
            self.window_button_icon.set_from_pixbuf(self.icon_locked)
        elif window.is_minimized():
            self.window_button_icon.set_from_pixbuf(self.icon_transp)
        else:
            self.window_button_icon.set_from_pixbuf(self.icon)
        del pixbuf
        del lock

    def on_window_name_changed(self, window):
        name = u""+window.get_name()
        # TODO: fix a better way to shorten names.
        if len(name) > 40 and not self.preview:
            name = name[0:37]+"..."
        self.name = name
        self.label.set_label(name)

    def on_set_icongeo_win(self, arg=None):
        if self.globals.settings["show_only_current_desktop"] \
        and not self.is_on_current_desktop():
            self.window.set_icon_geometry(0, 0, 0, 0)
            return
        alloc = self.window_button.get_allocation()
        w = alloc.width
        h = alloc.height
        x,y = self.window_button.window.get_origin()
        x += alloc.x
        y += alloc.y
        self.window.set_icon_geometry(x, y, w, h)


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
                    self.globals.opacity_values = compiz_call('core/screen0/opacity_matches','get')
                except:
                    return
        self.globals.opacified = True
        self.opacified = True
        ov = [self.globals.settings['opacify_alpha']]
        om = ["!(title=%s) & !(class=dockbarx_factory.py)  & (type=Normal | type=Dialog)"%self.window.get_name()]
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
        b_m_x,b_m_y = self.window_button.get_pointer()
        b_r = self.window_button.get_allocation()
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
                pass
        self.globals.opacity_values = None
        self.globals.opacity_matches = None
        return False

    def deopacify_request(self):
        if not self.opacified:
            return False
        # Make sure that mouse cursor really has left the window button.
        b_m_x,b_m_y = self.window_button.get_pointer()
        b_r = self.window_button.get_allocation()
        if (b_m_x>=0 and b_m_x<b_r.width) and (b_m_y >= 0 and b_m_y < b_r.height):
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
##        self.window_button.drag_unhighlight()
        self.emit('popup-expose-request')
        self.emit('popup-hide-request')


    #### Events
    def on_button_mouse_enter(self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        # Keep that in mind when coding this def!
        if self.button_pressed :
            return
        self.update_label_state(True)
        if self.globals.settings["opacify"]:
            gobject.timeout_add(100,self.opacify_request)
            # Just for safty in case no leave-signal is sent
            gobject.timeout_add(500, self.deopacify_request)

    def on_button_mouse_leave(self, widget, event):
        # In compiz there is a enter and a leave event before a button_press event.
        # Keep that in mind when coding this def!
        self.button_pressed = False
        self.update_label_state(False)
        if self.globals.settings["opacify"]:
            self.deopacify_request()

    def on_window_button_press_event(self, widget,event):
        # In compiz there is a enter and a leave event before a button_press event.
        # self.button_pressed is used to stop functions started with
        # gobject.timeout_add from self.on_button_mouse_enter or self.on_button_mouse_leave.
        self.button_pressed = True
        gobject.timeout_add(600, self.set_button_pressed_false)

    def set_button_pressed_false(self):
        # Helper function for on_window_button_press_event.
        self.button_pressed = False
        return False

    def on_window_button_scroll_event(self, widget,event):
        if self.globals.settings["opacify"]and self.opacified:
            self.globals.opacified = False
            self.opacified = False
            self.deopacify()
        if event.direction == gtk.gdk.SCROLL_UP:
            action = self.globals.settings['windowbutton_scroll_up']
            self.action_function_dict[action](self, widget, event)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            action = self.globals.settings['windowbutton_scroll_down']
            self.action_function_dict[action](self, widget, event)

    def on_window_button_release_event(self, widget,event):
        if self.globals.settings["opacify"]and self.opacified:
            self.globals.opacified = False
            self.opacified = False
            self.deopacify()
        if event.button == 1 and event.state & gtk.gdk.SHIFT_MASK :
            action = self.globals.settings['windowbutton_shift_and_left_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 1:
            action = self.globals.settings['windowbutton_left_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 2 and event.state & gtk.gdk.SHIFT_MASK:
            action = self.globals.settings['windowbutton_shift_and_middle_click_action']
            self.action_function_dict[action](self, widget,event)
        elif event.button == 2:
            action = self.globals.settings['windowbutton_middle_click_action']
            self.action_function_dict[action](self, widget,event)
        elif event.button == 3 and event.state & gtk.gdk.SHIFT_MASK:
            action = self.globals.settings['windowbutton_shift_and_right_click_action']
            self.action_function_dict[action](self, widget, event)
        elif event.button == 3:
            action = self.globals.settings['windowbutton_right_click_action']
            self.action_function_dict[action](self, widget, event)

    #### Menu functions
    def menu_closed(self, menushell):
        self.globals.right_menu_showing = False
        self.emit('popup-hide')

    def minimize_window(self, widget=None, event=None):
        if self.window.is_minimized():
            self.window.unminimize(gtk.get_current_event_time())
        else:
            self.window.minimize()

    #### Actions
    def action_select_or_minimize_window(self, widget=None, event=None, minimize=True):
        # The window is activated, unless it is already
        # activated, then it's minimized. Minimized
        # windows are unminimized. The workspace
        # is switched if the window is on another
        # workspace.
        if event:
            t = event.time
        else:
            t = gtk.get_current_event_time()
        if self.window.get_workspace() != None \
        and self.screen.get_active_workspace() != self.window.get_workspace():
            self.window.get_workspace().activate(t)
        if not self.window.is_in_viewport(self.screen.get_active_workspace()):
            win_x,win_y,win_w,win_h = self.window.get_geometry()
            self.screen.move_viewport(win_x-(win_x%self.screen.get_width()),win_y-(win_y%self.screen.get_height()))
            # Hide popup since mouse movment won't
            # be tracked during compiz move effect
            # which means popup list can be left open.
            self.emit('popup-hide')
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

    def action_lock_or_unlock_window(self, widget=None, event=None):
        pass

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
        #(Un)Lock
        lock_item = None
        if self.window.get_actions() & action_minimize \
        and not self.locked:
            lock_item = gtk.MenuItem('_Lock')
        elif self.locked:
            lock_item = gtk.MenuItem('Un_lock')
        if lock_item:
            menu.append(lock_item)
            lock_item.connect("activate", self.action_lock_or_unlock_window)
            lock_item.show()
        #(Un)Minimize
        minimize_item = None
        if self.window.get_actions() & action_minimize \
        and not self.window.is_minimized():
            minimize_item = gtk.MenuItem('_Minimize')
        elif self.window.get_actions() & action_unminimize \
        and self.window.is_minimized():
            minimize_item = gtk.MenuItem('Un_minimize')
        if minimize_item:
            menu.append(minimize_item)
            minimize_item.connect("activate", self.minimize_window)
            minimize_item.show()
        # (Un)Maximize
        maximize_item = None
        if not self.window.is_maximized() \
        and self.window.get_actions() & action_maximize:
            maximize_item = gtk.MenuItem('Ma_ximize')
        elif self.window.is_maximized() \
        and self.window.get_actions() & action_unminimize:
            maximize_item = gtk.MenuItem('Unma_ximize')
        if maximize_item:
            menu.append(maximize_item)
            maximize_item.connect("activate", self.action_maximize_window)
            maximize_item.show()
        # Close
        close_item = gtk.MenuItem('_Close')
        menu.append(close_item)
        close_item.connect("activate", self.action_close_window)
        close_item.show()
        menu.popup(None, None, None, event.button, event.time)
        self.globals.right_menu_showing = True

    def action_none(self, widget = None, event = None):
        pass

    action_function_dict = ODict((
                                  ('select or minimize window', action_select_or_minimize_window),
                                  ('select window', action_select_window),
                                  ('maximize window', action_maximize_window),
                                  ('close window', action_close_window),
                                  ('show menu', action_show_menu),
                                  ('lock or unlock window', action_lock_or_unlock_window),
                                  ('shade window', action_shade_window),
                                  ('unshade window', action_unshade_window),
                                  ('no action', action_none)
                                ))


