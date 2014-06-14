#!/usr/bin/env python2
# -*- coding: UTF-8 -*-


license = """Licensed under the GNU General Public License Version 3

Battery Status is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

Battery Status is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301, USA.
"""


name = "battery-status"
comment = "Battery Status applet for the GNOME desktop ported to DockX"
homepage = "http://live.gnome.org/BatteryStatus"
copyright = "Copyright © 2010 Ivan Zorin, 2014 Matias Sars"
authors = ["Ivan Zorin <ivan.a.zorin@gmail.com>", ]
version = "0.1.1"


import os
import sys
import platform
import time
import gobject
import gtk
import pygtk
import gconf
import dbus
from dockbarx.applets import DockXApplet
from dbus.mainloop.glib import DBusGMainLoop



class BatteryApplet():
    """GNOME Battery Status applet - shows battery status and battery life/charge time in GNOME panel"""
    
    
    # bool var. for default status of apport package
    package_apport = False
    # bool var. for default status of gnome-screensaver package
    package_screensaver = True
    # bool var. for default status of gnome-session-bin package
    package_session = True
    # bool var. for default status of gnome-power-manager package
    package_power = True
    # bool var. for default status of gnome-applets (with cpufreq-selector as backend for switching CPU frequency) package
    package_cpufreq = True
    # bool var. for detect D-Bus UPower/DeviceKit-Power error
    power_error = False
    # bool var. for detect CPU frequency scaling error
    cpufreq_error = False
    # bool var. for battery available status
    no_battery = False
    # bool var. for set up correct background when adding applet on panel
    option_panel_bgstate = 0
    # bool var. for low battery state trigger
    on_low_battery = False
    # bool var. for lock main menu item when battery information dialog opens
    lock_battery_status = False
    # power source device
    power_dev = ""
    # current power mode (in indicator)
    powermode = ""
    # default set of CPU items for scaling
    cpu_items = ""
    
    
    def __init__(self, event_box):
        """Create applet"""
        self.init_widgets(event_box)
        self.init_gconf_settings()
        self.init_packages()
        self.init_pp_menu()
        self.init_first_run()
        self.init_cpufreq()
        self.init_power_dbus()
    
    
    def init_widgets(self, event_box):
        """Create widgets for applet"""
        ### core widgets of applet
        # get current icon theme for icons
        self.icon_theme = gtk.icon_theme_get_default()
        self.icon_theme.append_search_path('/usr/share/gnome-power-manager/icons')
        self.icon_theme.connect("changed", self.update_status)
        # icon of gnome-power-manager
        self.pixbuf_gpm_32 = self.icon_theme.load_icon("gnome-power-manager", 32, gtk.ICON_LOOKUP_FORCE_SVG)
        # icon of battery status
        self.icon_name = "gpm-ac-adapter"
        pixbuf_battery_24 = self.icon_theme.load_icon(self.icon_name, 24, gtk.ICON_LOOKUP_FORCE_SVG)
        self.icon = gtk.Image()
        self.icon.set_from_pixbuf(pixbuf_battery_24)
        # label with text of battery status
        self.label = gtk.Label("")
        self.label.set_use_markup(True)
        if event_box.get_position() in ("left", "right"):
            # HBox widget - container for icon and label
            self.box = gtk.VBox()
        else:
            self.box = gtk.HBox()
        # add icon and label in hbox/vbox
        self.box.add(self.icon)
        self.box.add(self.label)
        # EventBox for events and main container
        self.event_box = event_box
        # add box in event_box
        self.event_box.add(self.box)
        # set up callback for button press
        self.event_box.connect("button-press-event", self.event_on_press)
        # call related method on mouse button press:
        self.button_actions = {
            1: self.main_menu_show,
            2: lambda: None,
            3: self.pp_menu_show,
        }
        ### widgets for main menu
        # menu item and icon with battery status
        pixbuf_battery_16 = self.icon_theme.load_icon("gpm-ac-adapter", 16, gtk.ICON_LOOKUP_FORCE_SVG)
        self.icon_status = gtk.Image()
        self.icon_status.set_from_pixbuf(pixbuf_battery_16)
        self.item_status = gtk.ImageMenuItem()
        self.item_status.set_image(self.icon_status)
        # menu item and icon with battery status when item locked
        self.icon_status_lock = gtk.Image()
        self.icon_status_lock.set_from_pixbuf(pixbuf_battery_16)
        self.item_status_lock = gtk.ImageMenuItem()
        self.item_status_lock.set_image(self.icon_status_lock)
        # menu item with power source information
        self.item_power = gtk.ImageMenuItem("Po_wer Source:")
        # menu item with power source information when item locked
        self.item_power_lock = gtk.ImageMenuItem("Po_wer Source:")
        ### widgets for battery status dialog
        # label for battery capacity information
        self.label_capacity_data = gtk.Label()
        self.label_capacity_data.set_justify(gtk.JUSTIFY_CENTER)
        # label for battery charge information
        self.label_charge_data = gtk.Label()
        self.label_charge_data.set_justify(gtk.JUSTIFY_RIGHT)
        # label for battery technical information
        self.label_info_data = gtk.Label()
        self.label_info_data.set_justify(gtk.JUSTIFY_CENTER)
        # label for battery information text
        self.label_info = gtk.Label()
        self.label_info.set_justify(gtk.JUSTIFY_LEFT)
        # progress bar of battery capacity
        self.progress_capacity = gtk.ProgressBar()
        self.progress_capacity.set_size_request(200, 24)
        # progress bar of battery charge
        self.progress_charge = gtk.ProgressBar()
        self.progress_charge.set_size_request(200, 24)
        
        # Don't know where to put this.
        self.box.show_all()
    
    
    def event_on_press(self, widget, event):
        """Action on pressing button in applet"""
        if event.type == gtk.gdk.BUTTON_PRESS:
            # detect pressing mouse button and calls related method
            self.button_actions[event.button](event)
    
    
    def pp_menu_show(self, event):
        """Show popup menu"""
        return
        self.applet.setup_menu(self.pp_menu_xml, self.pp_menu_verbs, None)
    
    
    def main_menu_show(self, event):
        """Create main menu"""
        # update power state, if available
        if not self.power_error:
            self.update_status()
        # update cpu frequency information
        self.init_cpufreq()
        ### init main menu with items
        menu = gtk.Menu()
        ### menu item: ----
        # separator
        settings_separator = gtk.SeparatorMenuItem()
        settings_separator.show()
        power_separator = gtk.SeparatorMenuItem()
        power_separator.show()
        actions_separator = gtk.SeparatorMenuItem()
        actions_separator.show()
        ### menu item: Power Mode >
        # icon for Power Mode menu item
        pixbuf_power = self.icon_theme.load_icon("gnome-power-statistics", 16, gtk.ICON_LOOKUP_FORCE_SVG)
        icon_power = gtk.Image()
        icon_power.set_from_pixbuf(pixbuf_power)
        # Power Mode submenu
        submenu_power = gtk.Menu()
        # Powersave item for Power Mode submenu
        submenu_power_ritem_powersave = gtk.RadioMenuItem(None, "Powe_rsave")
        submenu_power_ritem_powersave.connect("activate", self.power_management, "menu", self.powermode, self.cpu_items)
        submenu_power_ritem_powersave.show()
        # Ondemand item for Power Mode submenu
        submenu_power_ritem_ondemand = gtk.RadioMenuItem(None, "On_demand")
        submenu_power_ritem_ondemand.connect("activate", self.power_management, "menu", self.powermode, self.cpu_items)
        submenu_power_ritem_ondemand.show()
        # Conservative item for Power Mode submenu
        submenu_power_ritem_conservative = gtk.RadioMenuItem(None, "N_ormal")
        submenu_power_ritem_conservative.connect("activate", self.power_management, "menu", self.powermode, self.cpu_items)
        submenu_power_ritem_conservative.show()
        # Performance item for Power Mode submenu
        submenu_power_ritem_performance = gtk.RadioMenuItem(None, "P_erformance")
        submenu_power_ritem_performance.connect("activate", self.power_management, "menu", self.powermode, self.cpu_items)
        submenu_power_ritem_performance.show()
        # detect current option for Power Mode submenu
        power_modes = {0: "P_ower Mode: Powersave", 1: "P_ower Mode: Ondemand", 2: "P_ower Mode: Normal", 3: "P_ower Mode: Performance"}
        powermode_text = ""
        if self.powermode == "powersave":
            submenu_power_ritem_powersave.set_property("active", True)
            submenu_power_ritem_ondemand.set_property("active", False)
            submenu_power_ritem_conservative.set_property("active", False)
            submenu_power_ritem_performance.set_property("active", False)
            powermode_text = power_modes[0]
        elif self.powermode == "ondemand":
            submenu_power_ritem_powersave.set_property("active", False)
            submenu_power_ritem_ondemand.set_property("active", True)
            submenu_power_ritem_conservative.set_property("active", False)
            submenu_power_ritem_performance.set_property("active", False)
            powermode_text = power_modes[1]
        elif self.powermode == "conservative":
            submenu_power_ritem_powersave.set_property("active", False)
            submenu_power_ritem_ondemand.set_property("active", False)
            submenu_power_ritem_conservative.set_property("active", True)
            submenu_power_ritem_performance.set_property("active", False)
            powermode_text = power_modes[2]
        elif self.powermode == "performance":
            submenu_power_ritem_powersave.set_property("active", False)
            submenu_power_ritem_ondemand.set_property("active", False)
            submenu_power_ritem_conservative.set_property("active", False)
            submenu_power_ritem_performance.set_property("active", True)
            powermode_text = power_modes[3]
        # set up Power Mode submenu
        if self.option_powermenu:
            # add created items in Power Mode submenu
            submenu_power.add(submenu_power_ritem_powersave)
            submenu_power.add(submenu_power_ritem_ondemand)
            submenu_power.add(submenu_power_ritem_conservative)
            submenu_power.add(submenu_power_ritem_performance)
            # create Power Mode menu item and set up submenu for it
            menu_power = gtk.ImageMenuItem(powermode_text)
            menu_power.set_submenu(submenu_power)
            menu_power.set_image(icon_power)
            menu_power.show()
        ### menu item: Show >
        # icon for Show menu item
        pixbuf_show = self.icon_theme.load_icon("gtk-properties", 16, gtk.ICON_LOOKUP_FORCE_SVG)
        icon_show = gtk.Image()
        icon_show.set_from_pixbuf(pixbuf_show)
        # Show submenu
        submenu_show = gtk.Menu()
        # Icon Only item for Show submenu
        submenu_show_ritem_icon = gtk.RadioMenuItem(None, "_Icon Only")
        submenu_show_ritem_icon.connect("activate", self.main_menu_action)
        submenu_show_ritem_icon.show()
        # Time item for Show submenu
        submenu_show_ritem_time = gtk.RadioMenuItem(None, "_Time")
        submenu_show_ritem_time.connect("activate", self.main_menu_action)
        submenu_show_ritem_time.show()
        # Percentage item for Show submenu
        submenu_show_ritem_percent = gtk.RadioMenuItem(None, "_Percentage")
        submenu_show_ritem_percent.connect("activate", self.main_menu_action)
        submenu_show_ritem_percent.show()
        # detect current option for Show submenu
        if self.option_show == "time":
            submenu_show_ritem_icon.set_property("active", False)
            submenu_show_ritem_time.set_property("active", True)
            submenu_show_ritem_percent.set_property("active", False)
        elif self.option_show == "percent":
            submenu_show_ritem_icon.set_property("active", False)
            submenu_show_ritem_time.set_property("active", False)
            submenu_show_ritem_percent.set_property("active", True)
        else:
            submenu_show_ritem_icon.set_property("active", True)
            submenu_show_ritem_time.set_property("active", False)
            submenu_show_ritem_percent.set_property("active", False)
        if self.option_icon != "always":
            submenu_show_ritem_icon.set_sensitive(False)
        else:
            submenu_show_ritem_icon.set_sensitive(True)
        # separator for Show submenu
        submenu_show_separator = gtk.SeparatorMenuItem()
        submenu_show_separator.show()
        # Sleep Actions item for Show submenu
        submenu_show_citem_sleep = gtk.CheckMenuItem("S_leep Actions", True)
        submenu_show_citem_sleep.set_active(self.option_sleep)
        submenu_show_citem_sleep.connect("toggled", self.main_menu_action)
        submenu_show_citem_sleep.show()
        # Session Actions item for Show submenu
        submenu_show_citem_session = gtk.CheckMenuItem("S_ession Actions", True)
        submenu_show_citem_session.set_active(self.option_session)
        submenu_show_citem_session.set_sensitive(self.package_session)
        submenu_show_citem_session.connect("toggled", self.main_menu_action)
        submenu_show_citem_session.show()
        # another separator for Show submenu
        submenu_show_settings_separator = gtk.SeparatorMenuItem()
        submenu_show_settings_separator.show()
        # Text Size item for Show submenu
        submenu_show_citem_textsize = gtk.CheckMenuItem("Te_xt Size", True)
        submenu_show_citem_textsize.set_active(self.option_showtext)
        submenu_show_citem_textsize.connect("toggled", self.main_menu_action)
        submenu_show_citem_textsize.show()
        # Power Mode item for Show submenu
        submenu_show_citem_powermode = gtk.CheckMenuItem("Po_wer Modes", True)
        submenu_show_citem_powermode.set_active(self.option_cpufreq)
        submenu_show_citem_powermode.set_sensitive(self.package_cpufreq and not self.cpufreq_error)
        submenu_show_citem_powermode.connect("toggled", self.main_menu_action)
        submenu_show_citem_powermode.show()
        # add created items in Show submenu
        submenu_show.add(submenu_show_ritem_icon)
        submenu_show.add(submenu_show_ritem_time)
        submenu_show.add(submenu_show_ritem_percent)
        submenu_show.add(submenu_show_separator)
        submenu_show.add(submenu_show_citem_sleep)
        submenu_show.add(submenu_show_citem_session)
        submenu_show.add(submenu_show_settings_separator)
        submenu_show.add(submenu_show_citem_textsize)
        submenu_show.add(submenu_show_citem_powermode)
        # create Show menu item and set up submenu for it
        menu_show = gtk.ImageMenuItem("S_how", True)
        menu_show.set_submenu(submenu_show)
        menu_show.set_image(icon_show)
        menu_show.show()
        ### menu item: Text Size >
        # icon for Text Size menu item
        pixbuf_text = self.icon_theme.load_icon("text-editor", 16, gtk.ICON_LOOKUP_FORCE_SVG)
        icon_text = gtk.Image()
        icon_text.set_from_pixbuf(pixbuf_text)
        # Text Size submenu
        submenu_text = gtk.Menu()
        # Small item for Text Size submenu
        submenu_text_ritem_small = gtk.RadioMenuItem(None, "_Small")
        submenu_text_ritem_small.connect("activate", self.main_menu_action)
        submenu_text_ritem_small.show()
        # Normal item for Text Size submenu
        submenu_text_ritem_normal = gtk.RadioMenuItem(None, "_Normal")
        submenu_text_ritem_normal.connect("activate", self.main_menu_action)
        submenu_text_ritem_normal.show()
        # detect current option for Text Size submenu
        if self.option_text == "medium":
            submenu_text_ritem_small.set_property("active", False)
            submenu_text_ritem_normal.set_property("active", True)
        else:
            submenu_text_ritem_small.set_property("active", True)
            submenu_text_ritem_normal.set_property("active", False)
        # add created items in Text Size submenu
        submenu_text.add(submenu_text_ritem_small)
        submenu_text.add(submenu_text_ritem_normal)
        # create Text Size menu item and set up submenu for it
        menu_text = gtk.ImageMenuItem("_Text Size", True)
        menu_text.set_submenu(submenu_text)
        menu_text.set_image(icon_text)
        # make Text Size inactive, if Show > Icon Only
        if self.option_show == "icon":
            menu_text.set_sensitive(False)
        else:
            menu_text.set_sensitive(True)
        menu_text.show()
        ### menu item: Power Management...
        # icon for gnome-power-management item
        pixbuf_gpm = self.icon_theme.load_icon("gnome-power-manager", 16, gtk.ICON_LOOKUP_FORCE_SVG)
        icon_gpm = gtk.Image()
        icon_gpm.set_from_pixbuf(pixbuf_gpm)
        # create item itself
        item_pmsettings = gtk.ImageMenuItem("_Power Management...", True)
        item_pmsettings.set_image(icon_gpm)
        item_pmsettings.connect("activate", self.main_menu_action)
        item_pmsettings.show()
        # icon for power statistics
        icon_power_history = gtk.Image()
        if self.option_power and self.package_power:
            pixbuf_power_history = self.icon_theme.load_icon("gnome-power-statistics", 16, gtk.ICON_LOOKUP_FORCE_SVG)
            icon_power_history.set_from_pixbuf(pixbuf_power_history)
        else:
            icon_power_history.set_from_pixbuf(None)
        # battery status and power source menu items
        if self.lock_battery_status:
            # if battery status dialog already open, use inactive locked item status
            self.item_status_lock.set_label(self.status_text)
            self.item_status_lock.set_sensitive(False)
            self.item_status_lock.show()
            # and locked item power
            self.item_power_lock.set_image(icon_power_history)
            self.item_power_lock.set_label(self.power_source_text)
            self.item_power_lock.connect("activate", self.main_menu_action)
            if self.option_power and self.package_power:
                self.item_power_lock.set_sensitive(True)
            else:
                self.item_power_lock.set_sensitive(False)
            self.item_power_lock.show()
            # add items in menu
            menu.append(self.item_status_lock)
            if self.option_settings:
                menu.append(settings_separator)
                menu.append(menu_show)
                if self.option_showtext:
                    menu.append(menu_text)
            menu.append(power_separator)
            menu.append(self.item_power_lock)
        else:
            # else use existing global items for status item
            self.item_status.set_label(self.status_text)
            if self.power_error or self.no_battery:
                self.item_status.set_sensitive(False)
            else:
                self.item_status.set_sensitive(True)
                self.item_status.connect("activate", self.main_menu_battery_dialog)
            self.item_status.show()
            # and for power item
            self.item_power.set_image(icon_power_history)
            self.item_power.set_label(self.power_source_text)
            self.item_power.connect("activate", self.main_menu_action)
            if self.option_power and self.package_power:
                self.item_power.set_sensitive(True)
            else:
                self.item_power.set_sensitive(False)
            self.item_power.show()
            # add items in menu
            menu.append(self.item_status)
            if self.option_settings:
                menu.append(settings_separator)
                menu.append(menu_show)
                if self.option_showtext:
                    menu.append(menu_text)
            menu.append(power_separator)
            menu.append(self.item_power)
        # add Power Mode menu item(s) in menu
        if self.option_cpufreq and self.package_cpufreq and not self.cpufreq_error:
            if self.option_powermenu:
                menu.append(menu_power)
            else:
                menu.append(submenu_power_ritem_powersave)
                menu.append(submenu_power_ritem_ondemand)
                menu.append(submenu_power_ritem_conservative)
                menu.append(submenu_power_ritem_performance)
        if self.option_power and self.package_power:
            if not self.option_sleep and not self.option_session and self.option_cpufreq and self.package_cpufreq:
                menu.append(actions_separator)
            # if g-p-m package installed and integration available, add g-p-m settings in menu
            menu.append(item_pmsettings)
        if self.option_sleep and not self.power_error:
            ### show sleep actions in menu, if available
            if self.power_properties_interface.Get(self.power_address, "can-suspend") or self.power_properties_interface.Get(self.power_address, "can-hibernate"):
                ### menu item: ----
                # separator
                item_sleep_separator = gtk.SeparatorMenuItem()
                item_sleep_separator.show()
                menu.append(item_sleep_separator)
            if self.power_properties_interface.Get(self.power_address, "can-suspend"):
                ### menu item: Suspend
                # icon for suspend
                try:
                    pixbuf_suspend = self.icon_theme.load_icon("gnome-session-hibernate", 16, gtk.ICON_LOOKUP_FORCE_SVG)
                except:
                    pixbuf_suspend = self.icon_theme.load_icon("gpm-hibernate", 16, gtk.ICON_LOOKUP_FORCE_SVG)
                icon_suspend = gtk.Image()
                icon_suspend.set_from_pixbuf(pixbuf_suspend)
                # suspend item
                item_suspend = gtk.ImageMenuItem("S_uspend", True)
                item_suspend.set_image(icon_suspend)
                item_suspend.connect("activate", self.suspend)
                item_suspend.show()
                # add suspend item in menu
                menu.append(item_suspend)
            if self.power_properties_interface.Get(self.power_address, "can-hibernate"):
                ### menu item: Hibernate
                # icon for hibernate
                try:
                    pixbuf_hibernate = self.icon_theme.load_icon("drive-harddisk-root", 16, gtk.ICON_LOOKUP_FORCE_SVG)
                except:
                    pixbuf_hibernate = self.icon_theme.load_icon("drive-harddisk", 16, gtk.ICON_LOOKUP_FORCE_SVG)
                icon_hibernate = gtk.Image()
                icon_hibernate.set_from_pixbuf(pixbuf_hibernate)
                # hibernate item
                item_hibernate = gtk.ImageMenuItem("Hiber_nate", True)
                item_hibernate.set_image(icon_hibernate)
                item_hibernate.connect("activate", self.hibernate)
                item_hibernate.show()
                # add hibernate item in menu
                menu.append(item_hibernate)
        if self.option_session and self.package_session:
            ### show session actions in menu
            ### menu item: ----
            # separator
            item_session_separator = gtk.SeparatorMenuItem()
            item_session_separator.show()
            ### menu item: Log Out...
            # icon for logout
            try:
                pixbuf_logout = self.icon_theme.load_icon("gnome-session", 16, gtk.ICON_LOOKUP_FORCE_SVG)
            except:
                pixbuf_logout = self.icon_theme.load_icon("session-properties", 16, gtk.ICON_LOOKUP_FORCE_SVG)
            icon_logout = gtk.Image()
            icon_logout.set_from_pixbuf(pixbuf_logout)
            # logout item
            item_logout = gtk.ImageMenuItem("_Log Out...", True)
            item_logout.set_image(icon_logout)
            item_logout.connect("activate", self.main_menu_action)
            item_logout.show()
            ### menu item: Shut Down...
            # icon for shutdown
            try:
                pixbuf_shutdown = self.icon_theme.load_icon("system-shutdown-panel", 16, gtk.ICON_LOOKUP_FORCE_SVG)
            except:
                pixbuf_shutdown = self.icon_theme.load_icon("system-shutdown", 16, gtk.ICON_LOOKUP_FORCE_SVG)
            icon_shutdown = gtk.Image()
            icon_shutdown.set_from_pixbuf(pixbuf_shutdown)
            # shutdown item
            item_shutdown = gtk.ImageMenuItem("_Shut Down...", True)
            item_shutdown.set_image(icon_shutdown)
            item_shutdown.connect("activate", self.main_menu_action)
            item_shutdown.show()
            # add items in menu
            menu.append(item_session_separator)
            menu.append(item_logout)
            menu.append(item_shutdown)
        # shows main menu
        menu.popup(None, None, self.menu_position, event.button, event.time)
    
    
    def menu_position(self, menu):
        """Detect main menu popup position"""
        x, y = self.event_box.get_window().get_origin()
        a = self.event_box.get_allocation()
        w, h = menu.size_request()
        size = self.event_box.get_size()
        if self.event_box.get_position() == "left":
            x += size
            y += a.y
        if self.event_box.get_position() == "right":
            x -= w
            y += a.y
        if self.event_box.get_position() == "top":
            x += a.x
            y += size
        if self.event_box.get_position() == "bottom":
            x += a.x
            y -= h
        screen = self.event_box.get_window().get_screen()
        if y + h > screen.get_height():
                y = screen.get_height() - h
        if x + w >= screen.get_width():
                x = screen.get_width() - w
        return x, y, True
        
        #~ # detect screen with applet
        #~ screen = self.event_box.get_screen()
        #~ # detect monitor with screen
        #~ monitor = screen.get_monitor_geometry(screen.get_monitor_at_window(self.event_box.window))
        #~ # detect applet size
        #~ x_size, y_size = self.event_box.size_request()
        #~ # detect coordinates of window with applet
        #~ x_origin, y_origin = self.event_box.window.get_origin()
        #~ # detect menu size
        #~ x_menu, y_menu = menu.size_request()
        #~ # detect y position (popup direction) for main menu according to its size and applet location
        #~ if y_origin + y_menu < monitor.height :
            #~ y = y_origin + y_size - 1
        #~ else:
            #~ y = y_origin - y_menu + 1
        #~ # detect x position for main menu
        #~ x = x_origin - 1
        #~ # return coordinates with menu position
        #~ return x, y, True
    
    
    def init_gconf_settings(self):
        """Getting applet settings from GConf"""
        # set up connection to GConf
        self.g_conf = gconf.client_get_default()
        # check settings
        settings = self.g_conf.dir_exists("/apps/battery_status")
        # if GConf settings not available from schema file, set up defaults
        if not settings:
            # Show > submenu option
            self.g_conf.set_string("/apps/battery_status/show", "icon")
            # Text Size > submenu option
            self.g_conf.set_string("/apps/battery_status/text", "small")
            # option for icon behavior
            self.g_conf.set_string("/apps/battery_status/icon_policy", "always")
            # option for lock screen on suspend/hibernate
            self.g_conf.set_bool("/apps/battery_status/lock_screen", True)
            # option for show additional info in battery status dialog window
            self.g_conf.set_bool("/apps/battery_status/show_info", False)
            # option for show tooltip
            self.g_conf.set_bool("/apps/battery_status/show_tooltip", True)
            # option for show status of battery when charge time/lifetime not available
            self.g_conf.set_bool("/apps/battery_status/show_status", True)
            # option for show sleep actions (Suspend/Hibernate) in main menu
            self.g_conf.set_bool("/apps/battery_status/show_sleep", False)
            # option for show session actions (Logout/Shutdown) in main menu
            self.g_conf.set_bool("/apps/battery_status/show_session", False)
            # option for show gnome-power-manager related items in main menu
            self.g_conf.set_bool("/apps/battery_status/show_power", True)
            # option for low charge, when shows critical battery message window
            self.g_conf.set_int("/apps/battery_status/percentage_low", 8)
            # option for time of showing critical battery message window
            self.g_conf.set_int("/apps/battery_status/timer", 60)
            # first run - for show advice to remove gnome-power-managment tray icon, if in use.
            self.g_conf.set_bool("/apps/battery_status/first_run", True)
            # option for show power modes
            self.g_conf.set_bool("/apps/battery_status/show_powermode", True)
            # option for show Text Size settings
            self.g_conf.set_bool("/apps/battery_status/show_textsize", False)
            # option for show Show > and Text Size > settings
            self.g_conf.set_bool("/apps/battery_status/show_settings", True)
            # option for show power device in "Power Statistics" dialog according to current power source
            self.g_conf.set_bool("/apps/battery_status/power_source_sensitive", False)
            # option for reduce label with "hour" digit
            self.g_conf.set_bool("/apps/battery_status/reduce_hours", False)
            # option for Power Mode menu
            self.g_conf.set_bool("/apps/battery_status/powermode_as_submenu", False)
            # option for allow power management
            self.g_conf.set_bool("/apps/battery_status/power_manager", False)
        # get settings for applet
        self.option_show = self.g_conf.get_string("/apps/battery_status/show")
        self.option_text = self.g_conf.get_string("/apps/battery_status/text")
        self.option_icon = self.g_conf.get_string("/apps/battery_status/icon_policy")
        self.option_lock = self.g_conf.get_bool("/apps/battery_status/lock_screen")
        self.option_info = self.g_conf.get_bool("/apps/battery_status/show_info")
        self.option_tooltip = self.g_conf.get_bool("/apps/battery_status/show_tooltip")
        self.option_status = self.g_conf.get_bool("/apps/battery_status/show_status")
        self.option_sleep = self.g_conf.get_bool("/apps/battery_status/show_sleep")
        self.option_session = self.g_conf.get_bool("/apps/battery_status/show_session")
        self.option_power = self.g_conf.get_bool("/apps/battery_status/show_power")
        self.option_percentage_low = self.g_conf.get_int("/apps/battery_status/percentage_low")
        self.option_timer = self.g_conf.get_int("/apps/battery_status/timer")
        self.option_firstrun = self.g_conf.get_bool("/apps/battery_status/first_run")
        self.option_cpufreq = self.g_conf.get_bool("/apps/battery_status/show_powermode")
        self.option_showtext = self.g_conf.get_bool("/apps/battery_status/show_textsize")
        self.option_settings = self.g_conf.get_bool("/apps/battery_status/show_settings")
        self.option_sensitive = self.g_conf.get_bool("/apps/battery_status/power_source_sensitive")
        self.option_reduce = self.g_conf.get_bool("/apps/battery_status/reduce_hours")
        self.option_powermenu = self.g_conf.get_bool("/apps/battery_status/powermode_as_submenu")
        self.option_gpm = self.g_conf.get_bool("/apps/battery_status/power_manager")
        # validate settings
        if not self.option_show:
            self.g_conf.set_string("/apps/battery_status/show", "icon")
            self.option_show = self.g_conf.get_string("/apps/battery_status/show")
        if not self.option_text:
            self.g_conf.set_string("/apps/battery_status/text", "small")
            self.option_text = self.g_conf.get_string("/apps/battery_status/text")
        if not self.option_icon:
            self.g_conf.set_string("/apps/battery_status/icon_policy", "always")
            self.option_icon = self.g_conf.get_string("/apps/battery_status/icon_policy")
        if self.option_percentage_low is None:
            self.g_conf.set_int("/apps/battery_status/percentage_low", 8)
            self.option_percentage_low = self.g_conf.get_int("/apps/battery_status/percentage_low")
        if self.option_timer is None:
            self.g_conf.set_int("/apps/battery_status/timer", 60)
            self.option_timer = self.g_conf.get_int("/apps/battery_status/timer")
        # get g-p-m icon policy setting for advice to remove tray icon, if in use.
        self.option_gpm_icon_policy = self.g_conf.get_string("/apps/gnome-power-manager/ui/icon_policy")
        # add GConf settings of applet for detecting changes
        self.g_conf.add_dir("/apps/battery_status", gconf.CLIENT_PRELOAD_NONE)
        # set up related callbacks for changes of GConf settings
        self.g_conf.notify_add("/apps/battery_status/show", self.init_gconf_changes, "show")
        self.g_conf.notify_add("/apps/battery_status/text", self.init_gconf_changes, "text")
        self.g_conf.notify_add("/apps/battery_status/icon_policy", self.init_gconf_changes, "icon")
        self.g_conf.notify_add("/apps/battery_status/lock_screen", self.init_gconf_changes, "lock")
        self.g_conf.notify_add("/apps/battery_status/show_info", self.init_gconf_changes, "info")
        self.g_conf.notify_add("/apps/battery_status/show_tooltip", self.init_gconf_changes, "tooltip")
        self.g_conf.notify_add("/apps/battery_status/show_status", self.init_gconf_changes, "status")
        self.g_conf.notify_add("/apps/battery_status/show_sleep", self.init_gconf_changes, "sleep")
        self.g_conf.notify_add("/apps/battery_status/show_session", self.init_gconf_changes, "session")
        self.g_conf.notify_add("/apps/battery_status/show_power", self.init_gconf_changes, "power")
        self.g_conf.notify_add("/apps/battery_status/percentage_low", self.init_gconf_changes, "low")
        self.g_conf.notify_add("/apps/battery_status/timer", self.init_gconf_changes, "timer")
        self.g_conf.notify_add("/apps/battery_status/first_run", self.init_gconf_changes, "run")
        self.g_conf.notify_add("/apps/battery_status/show_powermode", self.init_gconf_changes, "cpufreq")
        self.g_conf.notify_add("/apps/battery_status/show_textsize", self.init_gconf_changes, "showtext")
        self.g_conf.notify_add("/apps/battery_status/show_settings", self.init_gconf_changes, "settings")
        self.g_conf.notify_add("/apps/battery_status/power_source_sensitive", self.init_gconf_changes, "sensitive")
        self.g_conf.notify_add("/apps/battery_status/reduce_hours", self.init_gconf_changes, "reduce")
        self.g_conf.notify_add("/apps/battery_status/powermode_as_submenu", self.init_gconf_changes, "powermenu")
        self.g_conf.notify_add("/apps/battery_status/power_manager", self.init_gconf_changes, "powermanager")
        self.g_conf.notify_add("/apps/gnome-power-manager/ui/icon_policy", self.init_gconf_changes, "gpm_icon")
            
        # Fix to make battery app icon centered when only the icon is shown.
        if self.option_show == "icon":
            self.label.hide()
        else:
            self.label.show()
    
    
    def init_gconf_changes(self, client, connection_id, entry, option):
        """Callback function for GConf changes"""
        ### update GConf settings on the fly, if it's changing within applet works
        # update Show submenu setting
        if option == "show" and entry.get_value().type == gconf.VALUE_STRING:
            if entry.get_value().get_string() == "time" or entry.get_value().get_string() == "percent":
                self.option_show = entry.get_value().get_string()
            else:
                self.option_show = "icon"
                # make icon visible, if shows icon only
                self.g_conf.set_string("/apps/battery_status/icon_policy", "always")
        # update Text size submenu setting
        elif option == "text" and entry.get_value().type == gconf.VALUE_STRING:
            if entry.get_value().get_string() == "medium":
                self.option_text = entry.get_value().get_string()
            else:
                self.option_text = "small"
        # update icon policy option
        elif option == "icon" and entry.get_value().type == gconf.VALUE_STRING:
            if entry.get_value().get_string() == "low" or entry.get_value().get_string() == "never" or entry.get_value().get_string() == "charge":
                self.option_icon = entry.get_value().get_string()
            else:
                self.option_icon = "always"
            if self.option_icon == "never" and self.option_show == "icon":
                # prevent to hide icon
                self.g_conf.set_string("/apps/battery_status/icon_policy", "always")
        # update lock screen option
        elif option == "lock" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_lock = entry.get_value().get_bool()
        # update info option
        elif option == "info" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_info = entry.get_value().get_bool()
        # update tooltip option
        elif option == "tooltip" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_tooltip = entry.get_value().get_bool()
        # update status option
        elif option == "status" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_status = entry.get_value().get_bool()
        # update option for show sleep actions in main menu
        elif option == "sleep" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_sleep = entry.get_value().get_bool()
        # update option for show session actions in main menu
        elif option == "session" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_session = entry.get_value().get_bool()
        # update option for show session actions in main menu
        elif option == "power" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_power = entry.get_value().get_bool()
        # update low percentage option
        elif option == "low" and entry.get_value().type == gconf.VALUE_INT:
            self.option_percentage_low = entry.get_value().get_int()
        # update timer option
        elif option == "timer" and entry.get_value().type == gconf.VALUE_INT:
            self.option_timer = entry.get_value().get_int()
        # update first run option
        elif option == "run" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_firstrun = entry.get_value().get_bool()
        # update show powermode option
        elif option == "cpufreq" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_cpufreq = entry.get_value().get_bool()
        # update show text size option
        elif option == "showtext" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_showtext = entry.get_value().get_bool()
        # update show settings option
        elif option == "settings" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_settings = entry.get_value().get_bool()
        # update power source sensitive option
        elif option == "sensitive" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_sensitive = entry.get_value().get_bool()
        # update reduce option
        elif option == "reduce" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_reduce = entry.get_value().get_bool()
        # update Power Mode option
        elif option == "powermenu" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_powermenu = entry.get_value().get_bool()
        # update gpm option
        elif option == "powermanager" and entry.get_value().type == gconf.VALUE_BOOL:
            self.option_gpm = entry.get_value().get_bool()
        # update gnome-power-manager's icon policy option
        elif option == "icon_policy" and entry.get_value().type == gconf.VALUE_STRING:
            self.option_gpm_icon_policy = entry.get_value().get_string()
        # update battery info for applying changes
        if not self.power_error:
            try:
                # to handle error, if it's occurs before detecting self.power_error state
                self.update_status()
            except:
                pass
        else:
            self.power_dbus_signal_error("dbus")
            
        # Fix to make battery app icon centered when only the icon is shown.
        if self.option_show == "icon":
            self.label.hide()
        else:
            self.label.show()
    
    
    def init_packages(self):
        """Detect packages"""
        dist = ""
        # detect current distribution
        try:
            # to get distroname in a python 2.6 way
            dist = platform.linux_distribution()[0]
        except:
            # get distroname in a deprecated way
            dist = platform.dist()[0]
        if dist == "Ubuntu" or dist == "debian":
            try:
                import apt
                cache = apt.Cache()
                package = cache["gnome-screensaver"]
                self.package_screensaver = package.isInstalled
                package = cache["gnome-session-bin"]
                self.package_session = package.isInstalled
                package = cache["gnome-power-manager"]
                self.package_power = package.isInstalled
                package = cache["gnome-applets"]
                self.package_cpufreq = package.isInstalled
                package = cache["apport-gtk"]
                self.package_apport = package.isInstalled
            except:
                pass
        elif dist == "Fedora":
            try:
                import rpm
                transaction = rpm.TransactionSet()
                matches = transaction.dbMatch()
                matches.pattern('name', rpm.RPMMIRE_GLOB, "gnome-screensaver")
                self.package_screensaver = False
                for match in matches:
                    self.package_screensaver = True
                matches = transaction.dbMatch()
                matches.pattern('name', rpm.RPMMIRE_GLOB, "gnome-session")
                self.package_session = False
                for match in matches:
                    self.package_session = True
                matches = transaction.dbMatch()
                matches.pattern('name', rpm.RPMMIRE_GLOB, "gnome-power-manager-extra")
                self.package_power = False
                for match in matches:
                    self.package_power = True
                matches = transaction.dbMatch()
                matches.pattern('name', rpm.RPMMIRE_GLOB, "gnome-applets")
                self.package_cpufreq = False
                for match in matches:
                    self.package_cpufreq = True
            except:
                pass
        else:
            pass
    
    
    def init_pp_menu(self):
        """Create popup menu"""
        # xml menu for right-mouse button
        self.pp_menu_xml = """<popup name="button3">"""
        # list with verbs "item - action" for popup menu
        self.pp_menu_verbs = []
        if self.package_apport:
            self.pp_menu_xml += """<menuitem name="Report"
                verb="Report"
                label="Report a Problem"
                pixtype="filename"
                pixname="/usr/share/icons/hicolor/scalable/apps/apport.svg"/>"""
            self.pp_menu_verbs.append(("Report", self.pp_menu_item_report))
        if self.package_power:
            self.pp_menu_xml += """<menuitem name="Help"
                verb="Help"
                label="_Help"
                pixtype="stock"
                pixname="gtk-help"/>"""
            self.pp_menu_verbs.append(("Help", self.pp_menu_item_help))
        self.pp_menu_xml += """<menuitem name="About"
            verb="About"
            label="_About"
            pixtype="stock"
            pixname="gtk-about"/>
        </popup>
        """
        self.pp_menu_verbs.append(("About", self.pp_menu_item_about))
    
    
    def pp_menu_item_report(self, event, data = None):
        """Generate bug report on choosing 'Report a Problem' in popup menu"""
        os.system("/usr/share/apport/apport-gtk -f -p battery-status &")
    
    
    def pp_menu_item_help(self, event, data = None):
        """Show gnome-power-manager help on choosing 'Help' in popup menu"""
        os.system("yelp ghelp:gnome-power-manager &")
    
    
    def pp_menu_item_about(self, event, data = None):
        """Show information about applet on choosing 'About' in popup menu"""
        About = gtk.AboutDialog()
        About.set_version(version)
        About.set_name(name)
        About.set_license(license)
        About.set_authors(authors)
        About.set_comments(comment)
        About.set_website(homepage)
        About.set_copyright(copyright)
        About.set_icon(self.pixbuf_gpm_32)
        About.set_logo_icon_name("gnome-power-manager")
        About.set_website_label("GNOME Battery Status applet Website")
        About.run()
        About.destroy()
    
    
    def main_menu_battery_dialog(self, item = False):
        """Battery device information dialog"""
        # local callback for expander of battery technical info frame
        def expander_info_cb(expander, gparam_bool, widget):
            if expander.get_expanded():
                widget.show()
            else:
                widget.hide()
            # update GConf setting
            self.g_conf.set_bool("/apps/battery_status/show_info", expander.get_expanded())
        # lock main menu for prevent duplicating battery information dialog
        self.lock_battery_status = True
        # update power information
        self.update_status()
        # text column for capacity data
        text_capacity = "State:\nPercentage:\nCapacity:\nLifetime:\nCharge time:\n"
        # text column for charge data
        text_charge = "Voltage:\nRate:\nCurrent:\nLast full:\nMaximum:\n"
        # label for capacity text
        label_capacity = gtk.Label()
        label_capacity.set_markup(text_capacity)
        label_capacity.set_justify(gtk.JUSTIFY_LEFT)
        label_capacity.show()
        # show label with capacity data
        self.label_capacity_data.show()
        # hbox for capacity labels
        hbox_capacity = gtk.HBox()
        hbox_capacity.add(label_capacity)
        hbox_capacity.add(self.label_capacity_data)
        hbox_capacity.show()
        # show progress bar of current battery capacity
        self.progress_capacity.show()
        # vbox for hbox with capacity labels and capacity progress bar
        vbox_capacity = gtk.VBox()
        vbox_capacity.add(hbox_capacity)
        vbox_capacity.add(self.progress_capacity)
        vbox_capacity.show()
        # alignment for vbox with capacity data
        align_capacity = gtk.Alignment()
        align_capacity.set_property("left-padding", 12)
        align_capacity.set_property("right-padding", 12)
        align_capacity.set_property("top-padding", 12)
        align_capacity.set_property("bottom-padding", 12)
        align_capacity.add(vbox_capacity)
        align_capacity.show()
        # frame for alignment
        frame_capacity = gtk.Frame("  Battery Capacity  ")
        frame_capacity.set_border_width(8)
        frame_capacity.add(align_capacity)
        frame_capacity.show()
        # label for charge text
        label_charge = gtk.Label()
        label_charge.set_markup(text_charge)
        label_charge.set_justify(gtk.JUSTIFY_LEFT)
        label_charge.show()
        # show label with charge data
        self.label_charge_data.show()
        # hbox for charge labels
        hbox_charge = gtk.HBox()
        hbox_charge.add(label_charge)
        hbox_charge.add(self.label_charge_data)
        hbox_charge.show()
        # show progress bar of current battery charge
        self.progress_charge.show()
        # vbox for hbox with charge labels and charge progress bar
        vbox_charge = gtk.VBox()
        vbox_charge.add(hbox_charge)
        vbox_charge.add(self.progress_charge)
        vbox_charge.show()
        # alignment for vbox with charge data
        align_charge = gtk.Alignment()
        align_charge.set_property("left-padding", 12)
        align_charge.set_property("right-padding", 12)
        align_charge.set_property("top-padding", 12)
        align_charge.set_property("bottom-padding", 12)
        align_charge.add(vbox_charge)
        align_charge.show()
        # frame for alignment
        frame_charge = gtk.Frame("  Battery Charge  ")
        frame_charge.set_border_width(8)
        frame_charge.add(align_charge)
        frame_charge.show()
        # show label with battery info text
        self.label_info.show()
        # show label with battery info data
        self.label_info_data.show()
        # hbox for battery info labels
        hbox_info = gtk.HBox()
        hbox_info.add(self.label_info)
        hbox_info.add(self.label_info_data)
        hbox_info.show()
        # alignment for hbox with battery info
        align_info = gtk.Alignment()
        align_info.set_property("left-padding", 24)
        align_info.set_property("right-padding", 0)
        align_info.set_property("top-padding", 12)
        align_info.set_property("bottom-padding", 12)
        align_info.add(hbox_info)
        align_info.show()
        # frame for alignment
        frame_info = gtk.Frame()
        frame_info.set_border_width(8)
        frame_info.add(align_info)
        # expander for frame with battery info
        expander_info = gtk.Expander()
        if self.option_info:
            frame_info.show()
        else:
            frame_info.hide()
        expander_info.set_expanded(self.option_info)
        expander_info.set_label("Battery Information")
        expander_info.connect("notify::expanded", expander_info_cb, frame_info)
        expander_info.show()
        # generate dialog window with provided battery information
        message_battery_status = gtk.Dialog(title = "", parent = None, buttons = None)
        message_battery_status.set_title("Battery Status")
        message_battery_status.set_property("gravity", gtk.gdk.GRAVITY_NORTH)
        message_battery_status.set_property("skip-taskbar-hint", False)
        message_battery_status.set_property("skip-pager-hint", True)
        message_battery_status.set_property("resizable", False)
        message_battery_status.set_property("deletable", False)
        message_battery_status.set_has_separator(False)
        message_battery_status.set_icon(self.pixbuf_battery_info)
        message_battery_status.vbox.add(frame_capacity)
        message_battery_status.vbox.add(frame_charge)
        message_battery_status.vbox.add(expander_info)
        message_battery_status.vbox.add(frame_info)
        # copy dialog for destroy it, if user remove applet when dialog open
        self.lock_battery_status = message_battery_status
        message_battery_status.run()
        message_battery_status.destroy()
        # unlock menu
        self.lock_battery_status = False
        # make battery item active, only if battery available
        if self.no_battery or self.power_error:
            self.item_status.set_sensitive(False)
            self.item_status_lock.set_sensitive(False)
        else:
            self.item_status.set_sensitive(True)
            self.item_status_lock.set_sensitive(True)
    
    
    def main_menu_action(self, item, data = None, args = None):
        """Main menu items/actions handler"""
        action = item.get_label()
        ### Power Source item
        if action.find("Po_wer Source:") != -1:
            if self.option_sensitive:
                # if power_source_sensitive, then set statistics for current power source device
                if action.find("Battery") != -1:
                    self.g_conf.set_string("/apps/gnome-power-manager/info/last_device", self.power_address + "/devices/" + self.power_battery_name)
                else:
                    self.g_conf.set_string("/apps/gnome-power-manager/info/last_device", self.power_address + "/devices/" + self.power_ac_name)
            # show power statistics
            os.system("gnome-power-statistics &")
        ### Power Management item
        elif action == "_Power Management...":
            # show power preferences
            os.system("gnome-control-center power &")
        ### Session items
        elif action == "_Log Out...":
            # show logout dialog
            os.system("gnome-session-save --logout-dialog &")
        elif action == "_Shut Down...":
            # show shutdown dialog
            os.system("gnome-session-save --shutdown-dialog &")
        ### Show submenu item action and update GConf setting on changing it
        elif action == "_Percentage":
            self.g_conf.set_string("/apps/battery_status/show", "percent")
        elif action == "_Time":
            self.g_conf.set_string("/apps/battery_status/show", "time")
        elif action == "_Icon Only":
            self.g_conf.set_string("/apps/battery_status/show", "icon")
        ### Text Size submenu item action and update GConf setting on changing it
        elif action == "_Normal":
            self.g_conf.set_string("/apps/battery_status/text", "medium")
        elif action == "_Small":
            self.g_conf.set_string("/apps/battery_status/text", "small")
        ### Show submenu check items and update GConf setting on changing it
        elif action == "S_leep Actions":
            self.g_conf.set_bool("/apps/battery_status/show_sleep", not self.option_sleep)
        elif action == "S_ession Actions":
            self.g_conf.set_bool("/apps/battery_status/show_session", not self.option_session)
        elif action == "Te_xt Size":
            self.g_conf.set_bool("/apps/battery_status/show_textsize", not self.option_showtext)
        elif action == "Po_wer Modes":
            self.g_conf.set_bool("/apps/battery_status/show_powermode", not self.option_cpufreq)
        else:
            pass
    
    
    
    def init_first_run(self):
        """After-init hook"""
        # if user add applet at first time and use gnome-power-manager icon in indicator/notification area
        if self.option_firstrun and self.option_gpm_icon_policy != "never":
            # then show advice to remove icon from notification area
            message_icon_tray = gtk.MessageDialog(parent = None, type = gtk.MESSAGE_QUESTION, buttons = gtk.BUTTONS_NONE, message_format = None)
            title_text = "Battery Status applet has been added on the GNOME panel."
            message_text = 'Battery Status applet shows state/percentage/lifetime of battery in your laptop, but you also use Power Manager\'s battery icon for the same purpose - would you like to remove it?\n\nYou can always change Power Manager\'s battery icon settings and its behavior in "Power Management" Preferences'
            message_icon_tray.set_markup('<span weight="bold" size="medium">' + title_text + '</span>' + '\n\n' + message_text)
            message_icon_tray.set_icon(self.pixbuf_gpm_32)
            message_icon_tray.set_property("window-position", "center")
            message_icon_tray.set_keep_above(True)
            message_icon_tray.add_button("_Remove", 1)
            message_icon_tray.add_button("Ign_ore", 0)
            message_icon_tray.set_default_response(0)
            if message_icon_tray.run() == 1:
                self.g_conf.set_string("/apps/gnome-power-manager/ui/icon_policy", "never")
            message_icon_tray.destroy()
        self.g_conf.set_bool("/apps/battery_status/first_run", False)
    
    
    def init_cpufreq(self):
        """Init detecting CPU frequency mode"""
        if self.package_cpufreq and self.option_cpufreq:
            try:
                ### to get CPU frequency scaling information
                # get current governor
                powermode_file = open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r')
                self.powermode = powermode_file.read().rstrip('\n')
                powermode_file.close()
                # get list of CPUs
                cpu_data = os.popen("ls /sys/devices/system/cpu | grep '^cpu[0-9]*$' | sed 's,^cpu,,'")
                self.cpu_items = cpu_data.readlines()
                cpu_data.close()
                self.cpufreq_error = False
            except:
                self.cpufreq_error = True
        else:
            pass
    
    
    def init_power_dbus(self):
        """Init D-Bus UPower/DeviceKit-Power environment"""
        # set up default values for global D-Bus UPower/DeviceKit-Power related variables
        self.power_ac_address = None
        self.power_battery_address = None
        self.power_ac_name = "line_power"
        self.power_battery_name = "battery"
        self.properties_bus = "org.freedesktop.DBus.Properties"
        # set up power info dictionaries
        self.power_device_types = {0: "Unknown", 1: "Line Power", 2: "Battery", 3: "UPS", 4: "Monitor", 5: "Mouse", 6: "Keyboard", 7: "PDA", 8: "Phone"}
        self.power_battery_techs = {0: "Unknown", 1: "Lithium Ion", 2: "Lithium Polymer", 3: "Lithium Iron Phosphate", 4: "Lead Acid", 5: "Nickel Cadmium", 6: "Nickel Metal Hydride"}
        self.power_battery_state = {0: "unknown", 1: "charging", 2: "discharging", 3: "discharged", 4: "charged"}
        self.power_battery_tooltip = {0: "", 1: "until charged", 2: "remaining", 3: "", 4: "is fully charged"}
        self.power_source = {0: "Po_wer Source: AC Line", 1: "Po_wer Source: Battery"}
        self.battery_full = 4
        try:
            # to create connection for system bus
            self.bus = dbus.SystemBus()
            try:
                # to get power object using new UPower D-Bus address
                self.power_address = "/org/freedesktop/UPower"
                self.power_bus = "org.freedesktop.UPower"
                power_object = self.bus.get_object(self.power_bus, self.power_address)
            except:
                # try to get power object using old DeviceKit-Power D-Bus address
                self.power_address = "/org/freedesktop/DeviceKit/Power"
                self.power_bus = "org.freedesktop.DeviceKit.Power"
                power_object = self.bus.get_object(self.power_bus, self.power_address)
            # setting up power interfaces
            self.power_interface = dbus.Interface(power_object, self.power_bus)
            self.power_properties_interface = dbus.Interface(power_object, self.properties_bus)
            # update power information
            self.power_dbus_signal()
            # connect to signals
            # "DeviceChanged" is not used in UPower >=0.99, PropertiesChanged will be used instead
            #~ self.power_interface.connect_to_signal("DeviceChanged", self.power_dbus_signal) 
            self.power_interface.connect_to_signal("DeviceAdded", self.power_dbus_signal)
            self.power_interface.connect_to_signal("DeviceRemoved", self.power_dbus_signal)
            # if everything good
            self.power_error = False
        except dbus.exceptions.DBusException, exception:
            # else show error message
            self.dbus_error(exception.__str__())
        if self.power_error:
            self.power_dbus_signal_error("dbus")
    
    
    def dbus_error(self, exception_text):
        """Critical message with technical details, when something goes wrong"""
        # text buffer with details
        text_buffer = gtk.TextBuffer()
        text_buffer.set_text("DBus exception:\n" + exception_text)
        # container for text buffer
        text_field = gtk.TextView()
        text_field.set_editable(False)
        text_field.set_wrap_mode(gtk.WRAP_WORD)
        text_field.set_buffer(text_buffer)
        text_field.show()
        # container for details
        message_details = gtk.Expander()
        message_details.set_expanded(False)
        message_details.set_label("View technical details")
        message_details.add(text_field)
        message_details.show()
        # generate error message dialog
        message_error = gtk.MessageDialog(parent = None, type = gtk.MESSAGE_WARNING, buttons = gtk.BUTTONS_NONE, message_format = None)
        title_text = "Battery Status applet error."
        message_text = "Applet can't get power state of computer.\nD-Bus system or UPower/DeviceKit-Power information unavailable now.\n"
        question_text = "Would you like still to keep applet?"
        message_error.set_markup('<span weight="bold" size="medium">' + title_text + '</span>' + '\n\n' + message_text + '\n' + question_text)
        message_error.set_icon(self.pixbuf_gpm_32)
        message_error.set_property("window-position", "center")
        message_error.add_button("_Remove", 1)
        message_error.add_button("_Keep", 0)
        message_error.set_default_response(0)
        message_error.set_keep_above(True)
        message_error.vbox.add(message_details)
        # show error dialog
        if message_error.run():
            # destroy applet
            self.destroy(self.event)
            # and quit with error status
            sys.exit(1)
        message_error.destroy()
        self.power_error = True
    
    
    def power_dbus_signal_error(self, error_type):
        """Handle power errors"""
        ### Keep applet working, even if some power information not available
        if type(self.lock_battery_status).__name__ == "Dialog":
            # destroy battery status dialog, if active
            self.lock_battery_status.destroy()
        # set up text for label on error
        label_text = ""
        if self.option_show != "icon":
            label_text = '<span size="' + self.option_text + '">' + '('
            if self.option_show == "time":
                if self.option_status:
                    label_text += "missing"
                else:
                    label_text += "-:--"
            elif self.option_show == "percent":
                if self.option_status:
                    label_text += "missing"
                else:
                    label_text += "--" + '%'
            label_text += ')' + '</span>'
        self.label.set_markup(label_text)
        # set up icons
        self.icon.set_from_pixbuf(self.icon_theme.load_icon("gpm-ac-adapter", 24, gtk.ICON_LOOKUP_FORCE_SVG))
        self.icon_status.set_from_pixbuf(None)
        self.icon_status_lock.set_from_pixbuf(None)
        # generate text in main menu items and in tooltip according to current error
        if error_type == "dbus":
            self.status_text = "No Information"
            self.power_source_text = "Po_wer Source: No Information"
            tooltip_text = "Power information not available"
        elif error_type == "no_battery":
            self.status_text = "No Battery"
            self.power_source_text = "Po_wer Source: AC Line"
            tooltip_text = "Laptop battery not available"
        # set up locked status and power items
        self.item_status_lock.set_label(self.status_text)
        self.item_power_lock.set_label(self.power_source_text)
        self.item_status_lock.set_sensitive(False)
        self.item_status_lock.set_image(self.icon_status_lock)
        # set up unlocked status and power items
        self.item_status.set_label(self.status_text)
        self.item_power.set_label(self.power_source_text)
        self.item_status.set_sensitive(False)
        self.item_status.set_image(self.icon_status)
        # set up tooltip
        if self.option_tooltip:
            self.event_box.set_tooltip_text(tooltip_text)
        else:
            self.event_box.set_tooltip_text(None)
        
    def power_dbus_signal(self, device = None, signal = None):
        """Get battery power information on update"""
        # get list of available power devices
        power_devices = self.power_interface.EnumerateDevices()
        # list for AC devices
        power_ac_devices = []
        # list for battery devices
        power_battery_devices = []
        # detect ACs and batteries
        for power_device in power_devices:
            if power_device.find(self.power_battery_name) != -1:
                power_battery_devices.append(power_device)
            if power_device.find(self.power_ac_name) != -1:
                power_ac_devices.append(power_device)
        # detect primary AC address from available AC devices
        if len(power_ac_devices) == 0:
            self.power_ac_address = ""
        elif len(power_ac_devices) == 1:
            # get info for available AC
            power_ac_object = self.bus.get_object(self.power_bus, power_ac_devices[0])
            power_ac_interface = dbus.Interface(power_ac_object, self.properties_bus)
            power_ac = power_ac_interface.GetAll("")
            # check type of available AC
            if self.power_device_types[power_ac['Type']] == self.power_device_types[1] and power_ac['PowerSupply']:
                self.power_ac_address = power_ac_devices[0]
            else:
                self.power_ac_address = ""
        else:
            # multiple AC power lines - is it possible?
            pass
        # detect battery address from available battery devices
        if len(power_battery_devices) == 0:
            self.power_battery_address = ""
        elif len(power_battery_devices) == 1:
            # get info for available battery
            power_battery_object = self.bus.get_object(self.power_bus, power_battery_devices[0])
            self.power_battery_interface = dbus.Interface(power_battery_object, self.properties_bus)
            power_battery = self.power_battery_interface.GetAll("")
            # check type of available battery
            if self.power_device_types[power_battery['Type']] == self.power_device_types[2] and power_battery['PowerSupply']:
                self.power_battery_address = power_battery_devices[0]
            else:
                self.power_battery_address = ""
        else:
            # FIXME: code for processing multiple batteries goes here
            # it hasn't been tested on real multiple batteries, so any bug reports and logs are welcome
            for battery_address in power_battery_devices:
                power_battery_object = self.bus.get_object(self.power_bus, battery_address)
                self.power_battery_interface = dbus.Interface(power_battery_object, self.properties_bus)
                power_battery = self.power_battery_interface.GetAll("")
                # finding laptop battery address
                if self.power_device_types[power_battery['Type']] == self.power_device_types[2] and power_battery['PowerSupply']:
                    self.power_battery_address = battery_address
                    break
        # check availability of battery
        if self.power_battery_address:
            # get battery information, if available
            power_battery_object = self.bus.get_object(self.power_bus, self.power_battery_address)
            self.power_battery_interface = dbus.Interface(power_battery_object, self.properties_bus)
            self.power_battery_interface.connect_to_signal("PropertiesChanged", self.update_status)
            self.no_battery = False
        else:
            # keep working without battery information
            self.no_battery = True
            self.power_dbus_signal_error("no_battery")
            return False
        self.update_status()
        
    
    def update_status(self, *args):
        ### keep working with battery information
        if self.lock_battery_status or self.power_error or self.no_battery:
            self.item_status.set_sensitive(False)
            self.item_status_lock.set_sensitive(False)
        else:
            self.item_status.set_sensitive(True)
            self.item_status_lock.set_sensitive(True)
        # update battery information
        power_battery = self.power_battery_interface.GetAll("")
        # update power properties
        power_properties = self.power_properties_interface.GetAll("")
        # get battery state
        self.battery_state = self.power_battery_state[power_battery['State']]
        # get battery percentage
        self.battery_percent = int(round(power_battery['Percentage'], 1))
        # detect power source
        self.power_on_battery = power_properties['OnBattery']
        # detect critical charge
        if not self.on_low_battery and self.power_on_battery and self.battery_percent < self.option_percentage_low and self.option_timer > 0:
            self.on_low_battery = True
            self.critical_low()
        elif self.battery_percent >= self.option_percentage_low:
            self.on_low_battery = False
        # generate icon name according to current percentage
        if self.battery_percent >= 0 and self.battery_percent < 10:
            self.icon_name = "gpm-battery-000"
        elif self.battery_percent >= 10 and self.battery_percent < 20:
            self.icon_name = "gpm-battery-020"
        elif self.battery_percent >= 20 and self.battery_percent < 48:
            self.icon_name = "gpm-battery-040"
        elif self.battery_percent >= 48 and self.battery_percent < 75:
            self.icon_name = "gpm-battery-060"
        elif self.battery_percent >= 75 and self.battery_percent < 89:
            self.icon_name = "gpm-battery-080"
        elif self.battery_percent >= 89 and self.battery_percent <= 100:
            self.icon_name = "gpm-battery-100"
        if self.battery_state == self.power_battery_state[self.battery_full]:
            self.icon_name = "gpm-battery-charged"
        elif self.battery_state == "charging":
            self.icon_name += "-charging"
        ### set up battery icons
        # set up battery icon for main icon widget
        if self.option_icon == "always" or (self.option_icon == "low" and self.on_low_battery) or (self.option_icon == "charge" and self.battery_state != self.power_battery_state[self.battery_full]):
            self.icon.set_from_pixbuf(self.icon_theme.load_icon(self.icon_name, 24, gtk.ICON_LOOKUP_FORCE_SVG))
        else:
            self.icon.set_from_pixbuf(None)
        # set up global battery icon status for item status in main menu
        self.icon_status.set_from_pixbuf(self.icon_theme.load_icon(self.icon_name, 16, gtk.ICON_LOOKUP_FORCE_SVG))
        # set up local battery icon status for item status in main menu
        icon_status = gtk.Image()
        icon_status.set_from_pixbuf(self.icon_theme.load_icon(self.icon_name, 16, gtk.ICON_LOOKUP_FORCE_SVG))
        self.item_status.set_image(icon_status)
        # set up local battery icon status for locked item status in main menu
        icon_status_lock = gtk.Image()
        icon_status_lock.set_from_pixbuf(self.icon_theme.load_icon(self.icon_name, 16, gtk.ICON_LOOKUP_FORCE_SVG))
        self.item_status_lock.set_image(icon_status_lock)
        # set up battery icon for battery status dialog
        self.pixbuf_battery_info = self.icon_theme.load_icon(self.icon_name, 128, gtk.ICON_LOOKUP_FORCE_SVG)
        # init local variable for tooltip
        battery_time = "-:--"
        # get battery lifetime
        self.battery_lifetime = power_battery['TimeToEmpty']
        # convert battery lifetime from seconds to human-readable format (if available)
        if self.battery_lifetime:
            self.battery_lifetime = time.strftime('%H:%M', time.gmtime(self.battery_lifetime))[1:5]
            battery_time = self.battery_lifetime
        else:
            self.battery_lifetime = "-:--"
            h_time = 0
            m_time = 0
        # get battery charge time
        self.battery_chargetime = power_battery['TimeToFull']
        # convert battery charge time from seconds to human-readable format (if available)
        if self.battery_chargetime:
            self.battery_chargetime = time.strftime('%H:%M', time.gmtime(self.battery_chargetime))[1:5]
            battery_time = self.battery_chargetime
        else:
            self.battery_chargetime = "-:--"
        # detect color text
        if self.battery_percent < 15 and self.power_on_battery:
            color_begin = '<span color="#F00000">'
            color_end = '</span>'
        else:
            color_begin = ''
            color_end = ''
        # convert battery percentage from integer to string
        self.battery_percent = str(self.battery_percent)
        # generate text for main label widget based on applet settings and current power status
        label_text = ""
        if self.option_show != "icon":
            label_text = '<span size="' + self.option_text + '">' + '(' + color_begin
            if self.option_show == "time":
                if self.power_on_battery:
                    if self.battery_lifetime == "-:--" and self.option_status:
                        label_text += "discharging"
                    elif self.battery_lifetime != "-:--" and not int(self.battery_lifetime[0]) and self.option_reduce:
                        label_text += self.battery_lifetime[1:4]
                    else:
                        label_text += self.battery_lifetime
                elif self.battery_state == self.power_battery_state[self.battery_full]:
                    label_text += "charged"
                else:
                    if self.battery_chargetime == "-:--" and self.option_status:
                        label_text += "charging"
                    elif self.battery_chargetime != "-:--" and not int(self.battery_chargetime[0]) and self.option_reduce:
                        label_text += self.battery_chargetime[1:4]
                    else:
                        label_text += self.battery_chargetime
            elif self.option_show == "percent":
                label_text += self.battery_percent + '%'
            label_text += color_end + ')' + '</span>'
        # update label text
        self.label.set_markup(label_text)
        # generate text for battery status item in main menu
        self.status_text = ""
        if battery_time != "-:--" and self.battery_state != self.power_battery_state[self.battery_full] and self.option_show != "time":
            # show battery lifetime/chargetime only if it available and this actual
            self.status_text += battery_time
            if self.power_on_battery:
                self.status_text += " remaining"
            else:
                self.status_text += " until full"
        else:
            # in other case, show battery status
            self.status_text += "Battery is " + self.power_battery_state[power_battery['State']]
        if self.option_show != "percent":
            # show percentage, if its not showing in applet
            self.status_text += ": " + self.battery_percent + '%'
        # update battery status text in main menu
        self.item_status.set_label(self.status_text)
        # update battery status text in main menu for reserve locked menu item
        self.item_status_lock.set_label(self.status_text)
        # generate text for power source item in main menu
        self.power_source_text = self.power_source[self.power_on_battery]
        # update power source text in main menu
        self.item_power.set_label(self.power_source_text)
        # update power source text in main menu for reserve locked menu item
        self.item_power_lock.set_label(self.power_source_text)
        ### generate tooltip for applet
        # generic tooltip text
        tooltip_text = "Laptop battery"
        # init default values
        h_tooltip = ''
        m_tooltip = ''
        percent_tooltip = ''
        # get information for tooltip
        battery_tooltip = self.power_battery_tooltip[power_battery['State']]
        if self.battery_state != self.power_battery_state[self.battery_full]:
            percent_tooltip = ' (' + str(round(power_battery['Percentage'], 1)) + '%)'
        if battery_time != "-:--":
            h_time = int(battery_time[0:1])
            m_time = int(battery_time[2:4])
            if h_time > 1:
                h_tooltip = ' ' + str(h_time) + " hours"
            elif h_time == 1:
                h_tooltip = ' ' + str(h_time) + " hour"
            if m_time > 1:
                m_tooltip = ' ' + str(m_time) + " minutes"
            elif m_time == 1:
                m_tooltip = ' ' + str(m_time) + " minute"
        else:
            battery_tooltip = self.battery_state
        # set up tooltip
        tooltip_text += h_tooltip + m_tooltip + ' ' + battery_tooltip + percent_tooltip
        self.event_box.set_tooltip_text(None)
        if self.option_tooltip:
            self.event_box.set_tooltip_text(tooltip_text)
        ### get information for battery status dialog, if it's open
        if self.lock_battery_status:
            # generate text about battery capacity
            text_capacity_data = self.power_battery_state[power_battery['State']] + '\n'
            text_capacity_data += str(round(power_battery['Percentage'], 1)) + '%\n'
            text_capacity_data += str(round(power_battery['Capacity'], 1)) + '%\n'
            text_capacity_data += self.battery_lifetime + '\n'
            text_capacity_data += self.battery_chargetime + '\n'
            # generate text about battery charge
            text_charge_data = str(round(power_battery['Voltage'], 1)) + ' V   \n'
            text_charge_data += str(round(power_battery['EnergyRate'], 1)) + ' W  \n'
            text_charge_data += str(round(power_battery['Energy'], 1)) + ' Wh\n'
            text_charge_data += str(round(power_battery['EnergyFull'], 1)) + ' Wh\n'
            text_charge_data += str(round(power_battery['EnergyFullDesign'], 1)) + ' Wh\n'
            # update battery status in information dialog window
            self.label_capacity_data.set_markup(text_capacity_data)
            self.label_charge_data.set_markup(text_charge_data)
            # update progress bar with battery capacity information
            self.progress_capacity.set_fraction(power_battery['Percentage']/100)
            self.progress_capacity.set_text(str(int(round(power_battery['Percentage'], 1))) + '%')
            # update progress bar with battery charge information
            progress_charge_data = 100 * power_battery['Energy'] / power_battery['EnergyFullDesign']
            self.progress_charge.set_fraction(progress_charge_data/100)
            self.progress_charge.set_text(str(int(round(progress_charge_data, 1))) + '%')
            if self.option_info:
                # text column for battery info
                text_info = "Technology:\nVendor:\nModel:"
                # generate text about battery information
                text_info_data = '\t' + self.power_battery_techs[power_battery['Technology']] + '\n'
                text_info_data += '\t' + power_battery['Vendor'] + '\n'
                text_info_data += '\t' + power_battery['Model']
                # display serial number only if available
                if power_battery['Serial'] != "":
                    text_info += "\nSerial:"
                    text_info_data += '\n' + '\t' + power_battery['Serial']
                self.label_info.set_markup(text_info)
                self.label_info_data.set_markup(text_info_data)
        # update power management state and its current settings
        self.power_management(None, "signal", self.powermode, None)
    
    
    def critical_low(self):
        """Message dialog about low battery percentage"""
        # local function for timer management
        def count(widget, timeout):
            # update power information
            self.update_status()
            # if timer enabled, then handle it
            if timeout:
                self.timer -= 1
                self.opacity -= self.opacity_step
                if self.timer > 1:
                    second = " seconds."
                else:
                    second = " second."
                if self.timer > 0 and self.power_on_battery:
                    # show critical low message only if timer ticking and AC not available
                    message_warning_label.set_markup("This message will automatically disappear in " + str(self.timer) + second)
                    widget.set_property("opacity", self.opacity)
                    return True
                else:
                    # in other case close message and stop timer
                    message_battery_low.destroy()
                    return False
            # if timer not enabled
            else:
                # but AC become available
                if not self.power_on_battery:
                    # close message
                    message_battery_low.destroy()
                    return False
                # in other case keep message showing and updating power information
                else:
                    return True
        # setting up default timer
        self.timer = self.option_timer
        # setting up opacity variables for fade out effect
        self.opacity = 1
        self.opacity_step = float(self.opacity)/self.timer
        # create icon for message
        battery_low_pixbuf = self.icon_theme.load_icon("gpm-battery-000", 64, gtk.ICON_LOOKUP_FORCE_SVG)
        battery_low_icon = gtk.Image()
        battery_low_icon.set_from_pixbuf(battery_low_pixbuf)
        battery_low_icon.show()
        # generate message about low battery percentage
        message_battery_low = gtk.MessageDialog(parent = None, buttons = gtk.BUTTONS_NONE, message_format = None)
        title_text = "You are now running on reserve battery power."
        message_text = "Please connect your computer to AC power. If you do not,\nyour computer will go to sleep in a few minutes to preserve\nthe contents of memory."
        message_battery_low.set_markup('<span weight="bold" size="medium">' + title_text + '</span>' + '\n\n' + message_text)
        message_battery_low.set_icon(self.pixbuf_gpm_32)
        message_battery_low.set_property("gravity", gtk.gdk.GRAVITY_NORTH)
        message_battery_low.set_keep_above(True)
        message_battery_low.set_image(battery_low_icon)
        # add Hibernate Now button, if such feature available
        if self.power_properties_interface.Get(self.power_address, "can-hibernate"):
            message_battery_low.add_button("Hiber_nate Now", 2)
        # add Ignore button and set up it by default
        message_battery_low.add_button("Ign_ore", 1)
        message_battery_low.set_default_response(1)
        # add timer and label for destroy dialog
        if self.timer > 1:
            message_battery_low.set_property("opacity", self.opacity)
            message_warning_label = gtk.Label()
            message_warning_label.set_markup("This message will automatically disappear in " + str(self.timer) + " seconds.")
            message_warning_label.show()
            message_battery_low.vbox.add(message_warning_label)
            gobject.timeout_add_seconds(self.timer, message_battery_low.destroy)
            timeout = True
        elif self.timer == 1:
            message_battery_low.set_property("opacity", 0.8)
            timeout = False
        gobject.timeout_add_seconds(1, count, message_battery_low, timeout)
        if message_battery_low.run() == 2:
            self.hibernate()
        message_battery_low.destroy()
    
    
    def hibernate(self, data = None):
        """Hibernate call for UPower/DeviceKit-Power D-Bus"""
        try:
            if self.package_screensaver and self.option_lock:
                # to lock screen and
                os.system("gnome-screensaver-command --lock &")
            # to hibernate
            self.power_interface.Hibernate()
        except dbus.exceptions.DBusException, exception:
            # if hibernate fail, then do nothing
            pass
    
    
    def suspend(self, data = None):
        """Suspend call for UPower/DeviceKit-Power D-Bus"""
        try:
            if self.package_screensaver and self.option_lock:
                # to lock screen and
                os.system("gnome-screensaver-command --lock &")
            # to suspend
            self.power_interface.Suspend()
        except dbus.exceptions.DBusException, exception:
            # if suspend fail, then do nothing
            pass
    
    
    def power_management(self, item, sender, mode, cpus):
        """Power settings management"""
        cpu_mode = ""
        if sender == "menu":
            # change CPU frequency scaling mode
            action = item.get_label()
            power_switch = False
            cpu_switch = True
            if action == "Powe_rsave":
                if mode != "powersave":
                    for cpu in cpus:
                        os.system("cpufreq-selector -g powersave -c " + cpu.rstrip('\n'))
                    cpu_mode = "powersave"
            elif action == "On_demand":
                if mode != "ondemand":
                    for cpu in cpus:
                        os.system("cpufreq-selector -g ondemand -c " + cpu.rstrip('\n'))
                    cpu_mode = "ondemand"
            elif action == "N_ormal":
                if mode != "conservative":
                    for cpu in cpus:
                        os.system("cpufreq-selector -g conservative -c " + cpu.rstrip('\n'))
                    cpu_mode = "conservative"
            elif action == "P_erformance":
                if mode != "performance":
                    for cpu in cpus:
                        os.system("cpufreq-selector -g performance -c " + cpu.rstrip('\n'))
                    cpu_mode = "performance"
            else:
                cpu_mode = ""
                cpu_switch = False
        elif sender == "signal":
            # change power source mode
            cpu_mode = mode
            power_switch = True
            cpu_switch = False
            if self.power_on_battery and self.power_dev != "battery":
                self.power_dev = "battery"
            elif not self.power_on_battery and self.power_dev != "ac":
                self.power_dev = "ac"
            else:
                power_switch = False
        else:
            power_switch = False
            cpu_switch = False
        # update cpu frequency information
        self.init_cpufreq()
        # if power state has changed, then switch settings, if available
        if (power_switch or cpu_switch) and cpu_mode == self.powermode and self.package_power and self.option_gpm:
            self.power_settings(self.power_dev, cpu_mode)
    
    
    def power_settings(self, power_source, cpu_mode):
        """Switch power settings according to current power source/cpu frequency"""
        if power_source == "ac":
            if cpu_mode == "powersave":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_ac", 70)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_ac", 1800)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_ac", 300)
            elif cpu_mode == "ondemand":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_ac", 80)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_ac", 3600)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_ac", 600)
            elif cpu_mode == "conservative":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_ac", 90)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_ac", 7200)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_ac", 1800)
            elif cpu_mode == "performance":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_ac", 100)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_ac", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_ac", 0)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_ac", 3600)
            else:
                pass
        elif power_source == "battery":
            if cpu_mode == "powersave":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/battery_reduce", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_dim_battery", 60)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_brightness", 20)
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_dim_time", 10)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_battery", 600)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_battery", 60)
            elif cpu_mode == "ondemand":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/battery_reduce", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_dim_battery", 40)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_brightness", 40)
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_dim_time", 30)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_battery", 1800)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_battery", 300)
            elif cpu_mode == "conservative":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/battery_reduce", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_dim_battery", 20)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_brightness", 60)
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_dim_time", 60)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_battery", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_battery", 3600)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_battery", 600)
            elif cpu_mode == "performance":
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/battery_reduce", False)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/brightness_dim_battery", 0)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_brightness", 80)
                self.g_conf.set_bool("/apps/gnome-power-manager/backlight/idle_dim_battery", True)
                self.g_conf.set_int("/apps/gnome-power-manager/backlight/idle_dim_time", 90)
                self.g_conf.set_bool("/apps/gnome-power-manager/disk/spindown_enable_battery", False)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_computer_battery", 7200)
                self.g_conf.set_int("/apps/gnome-power-manager/timeout/sleep_display_battery", 1800)
            else:
                pass
        else:
            pass


class DockXBatteryApplet(DockXApplet):
    """An example applet for DockbarX standalone dock"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        # DockXApplet base class is pretty much a gtk.EventBox.
        # so all you have to do is adding your widget with self.add()
        self.battery_applet = BatteryApplet(self)
        self.show()
        
    def update(self):
        self.battery_applet.update_status()


dockx_battery_applet = None

def get_dbx_applet(dbx_dict):
    global dockx_battery_applet
    if dockx_battery_applet is None:
        dockx_battery_applet = DockXBatteryApplet(dbx_dict)
    else: 
        dockx_battery_applet.update()
    return dockx_battery_applet
