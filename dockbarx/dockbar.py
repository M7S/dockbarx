#!/usr/bin/python


#	Copyright 2008, 2009, 2010 Aleksey Shaferov and Matias Sars
#
#	DockBar is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	DockBar is distributed in the hope that it will be useful,
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
import sys
import wnck
import gnomeapplet
import os
import dbus
import gio
import gc
gc.enable()

from groupbutton import *
from cairowidgets import *
from theme import Theme, NoThemesError
from common import *

VERSION = 'x.0.30'

class AboutDialog():
    __instance = None

    def __init__ (self):
        if AboutDialog.__instance == None:
            AboutDialog.__instance = self
        else:
            AboutDialog.__instance.about.present()
            return
        self.about = gtk.AboutDialog()
        self.about.set_name("DockBarX Applet")
        self.about.set_version(VERSION)
        self.about.set_copyright("Copyright (c) 2008-2009 Aleksey Shaferov and Matias S\xc3\xa4rs")
        self.about.connect("response",self.about_close)
        self.about.show()

    def about_close (self,par1,par2):
        self.about.destroy()
        AboutDialog.__instance = None


class GroupList():
    """GroupList contains a list with touples containing identifier, group button and launcherpath."""
    def __init__(self):
        self.list = []

    def __getitem__(self, name):
        return self.get_group(name)

    def __setitem__(self, identifier, group_button):
        self.add_group(identifier, group_button)

    def __contains__(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return True
        for t in self.list:
            if t[2] == name:
                return True
        return False

    def __iter__(self):
        return self.get_identifiers().__iter__()

    def add_group(self, identifier, group_button, path_to_launcher=None, index=None):
        t = (identifier, group_button, path_to_launcher)
        if index:
            self.list.insert(index, t)
        else:
            self.list.append(t)

    def get_group(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return t[1]
        for t in self.list:
            if t[2] == name:
                return t[1]

    def get_launcher_path(self, name):
        if not name:
            return
        for t in self.list:
            if t[0] == name:
                return t[2]
            if t[2] == name:
                return t[2]

    def set_launcher_path(self, identifier, path):
        if not identifier:
            return
        for t in self.list:
            if t[0] == identifier:
                n = [t[0], t[1], path]
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                return True

    def set_identifier(self, path, identifier):
        for t in self.list:
            if t[2] == path:
                n = (identifier, t[1], t[2])
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                n[1].identifier_changed(identifier)
                return True

    def get_groups(self):
        grouplist = []
        for t in self.list:
            grouplist.append(t[1])
        return grouplist

    def get_identifiers(self):
        namelist = []
        for t in self.list:
            if t[0]:
                namelist.append(t[0])
        return namelist

    def get_undefined_launchers(self):
        namelist = []
        for t in self.list:
            if t[0] == None:
                namelist.append(t[2])
        return namelist

    def get_identifiers_or_paths(self):
        namelist = []
        for t in self.list:
            if t[0] == None:
                namelist.append(t[2])
            else:
                namelist.append(t[0])
        return namelist

    def get_non_launcher_names(self):
        #Get a list of names of all buttons without launchers
        namelist = []
        for t in self.list:
            if not t[2]:
                namelist.append(t[0])
        return namelist

    def get_index(self, name):
        if not name:
            return
        for t in self.list:
            if t[0]==name:
                return self.list.index(t)
        for t in self.list:
            if t[2]==name:
                return self.list.index(t)

    def move(self, name, index):
        if not name:
            return
        for t in self.list:
            if name == t[0]:
                self.list.remove(t)
                self.list.insert(index, t)
                return True
        for t in self.list:
            if name == t[2]:
                self.list.remove(t)
                self.list.insert(index, t)
                return True

    def remove_launcher(self, identifier):
        if not identifier:
            return
        for t in self.list:
            if identifier == t[0]:
                n = (t[0], t[1], None)
                index = self.list.index(t)
                self.list.remove(t)
                self.list.insert(index, n)
                return True

    def remove(self, name):
        if not name:
            return
        for t in self.list:
            if name == t[0]:
                self.list.remove(t)
                return True
        for t in self.list:
            if name == t[2] and not t[0]:
                self.list.remove(t)
                return True

    def get_launchers_list(self):
        #Returns a list of name and launcher paths tuples
        launcherslist = []
        for t in self.list:
            #if launcher exist
            if t[2]:
                launchertuple = (t[0],t[2])
                launcherslist.append(launchertuple)
        return launcherslist


class DockBar():
    def __init__(self,applet):
        print "Dockbarx init"
        self.applet = applet
        self.groups = None
        self.windows = None
        self.container = None
        self.theme = None

        wnck.set_client_type(wnck.CLIENT_TYPE_PAGER)
        self.screen = wnck.screen_get_default()
        self.root_xid = int(gtk.gdk.screen_get_default().get_root_window().xid)
        self.screen.force_update()

        self.globals = Globals()
        self.globals.connect('theme-changed', self.reload)


        #--- Applet / Window container
        if self.applet != None:
            self.applet.set_applet_flags(gnomeapplet.HAS_HANDLE|gnomeapplet.EXPAND_MINOR)
            if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN or applet.get_orient() == gnomeapplet.ORIENT_UP:
                self.globals.orient = "h"
                self.container = gtk.HBox()
            else:
                self.globals.orient = "v"
                self.container = gtk.VBox()
            self.applet.add(self.container)
            self.pp_menu_xml = """
            <popup name="button3">
                <menuitem name="About Item" verb="About" stockid="gtk-about" />
                <menuitem name="Preferences" verb="Pref" stockid="gtk-properties" />
                <menuitem name="Reload" verb="Reload" stockid="gtk-refresh" />
            </popup>
            """

            self.pp_menu_verbs = [("About", self.on_ppm_about),
                                  ("Pref", self.on_ppm_pref),
                                  ("Reload", self.reload)]
            self.applet.setup_menu(self.pp_menu_xml, self.pp_menu_verbs,None)
            self.applet_origin_x = -1000 # off screen. there is no 'window' prop
            self.applet_origin_y = -1000 # at this step
            self.applet.set_background_widget(applet) # background bug workaround
            self.applet.show_all()
        else:
            self.container = gtk.HBox()
            self.globals.orient = "h"

        # Wait until everything is loaded
        # before adding groupbuttons
        while gtk.events_pending():
            gtk.main_iteration(False)

        self.reload()
        if self.applet != None:
            self.applet.connect("size-allocate",self.on_applet_size_alloc)
            self.applet.connect("change_background", self.on_change_background)
            self.applet.connect("change-orient",self.on_change_orient)
            self.applet.connect("delete-event",self.cleanup)


    def reload(self, event=None, data=None):
        # Remove all old groupbuttons from container.
        for child in self.container.get_children():
            self.container.remove(child)
        if self.windows:
            # Removes windows and non-launcher group buttons
            for win in self.screen.get_windows():
                self.on_window_closed(None, win)
        if self.groups != None:
            # Removes launcher group buttons
            for name in self.groups.get_identifiers_or_paths():
                self.groups[name].hide_list()
                self.groups[name].icon_factory.remove()
                self.groups.remove(name)

        del self.groups
        del self.windows
        if self.theme:
            self.theme.remove()
        gc.collect()
        print "Dockbarx reload"
        self.groups = GroupList()
        self.windows = {}
        self.globals.apps_by_id = {}
        #--- Generate Gio apps
        self.globals.apps_by_id = {}
        self.globals.apps_by_exec={}
        self.globals.apps_by_name = {}
        self.globals.apps_by_longname={}
        for app in gio.app_info_get_all():
            id = app.get_id()
            id = id[:id.rfind('.')].lower()
            name = u""+app.get_name().lower()
            exe = app.get_executable()
            if id[:5] != 'wine-' and exe:
                # wine not supported.
                # skip empty exec
                self.globals.apps_by_id[id] = app
                if name.find(' ')>-1:
                    self.globals.apps_by_longname[name] = id
                else:
                    self.globals.apps_by_name[name] = id
                if exe not in ('sudo','gksudo',
                                'java','mono',
                                'ruby','python'):
                    if exe[0] == '/':
                        exe = exe[exe.rfind('/')+1:]
                        self.globals.apps_by_exec[exe] = id
                    else:
                        self.globals.apps_by_exec[exe] = id


        try:
            if self.theme == None:
                self.theme = Theme()
            else:
                self.theme.on_theme_changed()
        except NoThemesError, details:
            print details
            sys.exit(1)

        self.container.set_spacing(self.theme.get_gap())
        self.container.show()

        #--- Initiate launchers
        self.launchers_by_id = {}
        self.launchers_by_exec={}
        self.launchers_by_name = {}
        self.launchers_by_longname={}

        gconf_launchers = self.globals.get_launchers_from_gconf()


        # Initiate launcher group buttons
        for launcher in gconf_launchers:
            identifier, path = launcher.split(';')
            if identifier == '':
                identifier = None
            try:
                self.add_launcher(identifier, path)
            except LauncherPathError:
                message = "The launcher at path %s cant be found. Did you perhaps delete the file?"%path
                print message
                md = gtk.MessageDialog(None,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                    message)
                md.run()
                md.destroy()
            except NoGioAppExistError:
                print "The Gio app for pinned app %s doesn't exist. The launcher will be removed."%identifier
        # Update launchers list to remove any launchers that are faulty.
        self.update_launchers_list()

        #--- Initiate windows
        # Initiate group buttons with windows
        for window in self.screen.get_windows():
            self.on_window_opened(self.screen, window)

        self.screen.connect("window-opened", self.on_window_opened)
        self.screen.connect("window-closed", self.on_window_closed)
        self.screen.connect("active-window-changed", self.on_active_window_changed)
        self.screen.connect("viewports-changed", self.on_desktop_changed)
        self.screen.connect("active-workspace-changed", self.on_desktop_changed)

        self.on_active_window_changed(self.screen, None)

    def reset_all_surfaces(self):
        # Removes all saved pixbufs with active glow in groupbuttons iconfactories.
        # Use this def when the looks of active glow has been changed.
        for group in self.groups.get_groups():
            group.icon_factory.reset_surfaces()

    def all_windowbuttons_update_label_state(self):
        # Updates all window button labels. To be used when
        # settings has been changed for the labels.
        for group in self.groups.get_groups():
            for winb in group.windows.values():
                winb.update_label_state()

    def update_all_popup_labels(self):
        # Updates all popup windows' titles. To be used when
        # settings has been changed for the labels.
        for group in self.groups.get_groups():
            group.update_popup_label()


    #### Applet events
    def on_ppm_pref(self,event=None,data=None):
        # Starts the preference dialog
        os.spawnlp(os.P_NOWAIT,'/usr/bin/dbx_preference.py',
                    '/usr/bin/dbx_preference.py')

    def on_ppm_about(self,event,data=None):
        AboutDialog()

    def on_applet_size_alloc(self, widget, allocation):
        if widget.window:
            x,y = widget.window.get_origin()
            if x!=self.applet_origin_x or y!=self.applet_origin_y:
                # Applet and/or panel moved
                self.applet_origin_x = x
                self.applet_origin_y = y
                for group in self.groups.get_groups():
                    group.on_db_move()

    def on_change_orient(self,arg1,data):
        if self.applet.get_orient() == gnomeapplet.ORIENT_DOWN \
        or self.applet.get_orient() == gnomeapplet.ORIENT_UP:
            self.set_orient('h')
        else:
            self.set_orient('v')

    def set_orient(self, orient):
        for group in self.groups.get_groups():
            self.container.remove(group.button)
        if self.applet:
            self.applet.remove(self.container)
        self.container.destroy()
        self.container = None
        self.globals.orient = orient
        if orient == 'h':
            self.container = gtk.HBox()
        else:
            self.container = gtk.VBox()
        if self.applet:
            self.applet.add(self.container)
        for group in self.groups.get_groups():
            self.container.pack_start(group.button,False)
        self.container.set_spacing(self.theme.get_gap())
        if self.globals.settings["show_only_current_desktop"]:
            self.container.show()
            self.on_desktop_changed()
        else:
            self.container.show_all()

    def on_change_background(self, applet, type, color, pixmap):
        applet.set_style(None)
        rc_style = gtk.RcStyle()
        applet.modify_style(rc_style)
        if type == gnomeapplet.COLOR_BACKGROUND:
            applet.modify_bg(gtk.STATE_NORMAL, color)
        elif type == gnomeapplet.PIXMAP_BACKGROUND:
            style = applet.style
            style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
            applet.set_style(style)
        return


    #### Wnck events
    def on_active_window_changed(self, screen, previous_active_window):
        # Sets the right window button and group button active.
        for group in self.groups.get_groups():
            group.set_has_active_window(False)
        # Activate new windowbutton
        active_window = screen.get_active_window()
        if active_window in self.windows:
            active_group_name = self.windows[active_window]
            active_group = self.groups.get_group(active_group_name)
            if active_group:
                active_group.set_has_active_window(True)
                window_button = active_group.windows[active_window]
                window_button.set_button_active(True)

    def on_window_closed(self,screen,window):
        if window in self.windows:
            class_group_name = self.windows[window]
            group = self.groups[class_group_name]
            if group:
                group.del_window(window)
                if not group.windows and not group.launcher:
                    self.groups.remove(class_group_name)
            del self.windows[window]

    def on_window_opened(self,screen,window):
        if window.is_skip_tasklist() \
        or not (window.get_window_type() in [wnck.WINDOW_NORMAL, wnck.WINDOW_DIALOG]):
            return

        class_group = window.get_class_group()
        class_group_name = class_group.get_res_class()
        if class_group_name == "":
            class_group_name = class_group.get_name()
        # Special cases
        if class_group_name == "Wine" \
        and self.globals.settings['separate_wine_apps']:
            class_group_name = self.get_wine_app_name(window)
        if class_group_name.startswith("OpenOffice.org"):
            class_group_name = self.get_ooo_app_name(window)
            if self.globals.settings['separate_ooo_apps']:
                window.connect("name-changed", self.on_ooo_window_name_changed)
        self.windows[window] = class_group_name
        if class_group_name in self.groups.get_identifiers():
            # This isn't the first open window of this group.
            self.groups[class_group_name].add_window(window)
            return

        id = self.find_matching_launcher(class_group_name)
        if id:
            # The window is matching a launcher without open windows.
            path = self.launchers_by_id[id].get_path()
            self.groups.set_identifier(path, class_group_name)
            self.groups[class_group_name].add_window(window)
            self.update_launchers_list()
            self.remove_launcher_id_from_undefined_list(id)
        else:
            # First window of a new group.
            app = self.find_gio_app(class_group_name)
            self.make_groupbutton(class_group, identifier=class_group_name, app=app)
            self.groups[class_group_name].add_window(window)

    def find_matching_launcher(self, identifier):
        id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.launchers_by_id:
                id = rc
                print "Opened window matched with launcher on id:", rc
            elif rc in self.launchers_by_name:
                id = self.launchers_by_name[rc]
                print "Opened window matched with launcher on name:", rc
            elif rc in self.launchers_by_exec:
                id = self.launchers_by_exec[rc]
                print "Opened window matched with launcher on executable:", rc
            else:
                for lname in self.launchers_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == ' ') \
                        or (pos+len(rc) == len(lname) and lname[pos-1] == ' ') \
                        or (lname[pos-1] == ' ' and lname[pos+len(rc)] == ' '):
                            id = self.launchers_by_longname[lname]
                            print "Opened window matched with launcher on long name:", rc
                            break

            if id == None and rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    if rc in self.launchers_by_id:
                        id = rc
                        print "Partial name for open window matched with id:", rc
                    elif rc in self.launchers_by_name:
                        id = self.launchers_by_name[rc]
                        print "Partial name for open window matched with name:", rc
                    elif rc in self.launchers_by_exec:
                        id = self.launchers_by_exec[rc]
                        print "Partial name for open window matched with executable:", rc
        return id

    def find_gio_app(self, identifier):
        app = None
        app_id = None
        rc = u""+identifier.lower()
        if rc != "":
            if rc in self.globals.apps_by_id:
                app_id = rc
                print "Opened window matched with gio app on id:", rc
            elif rc in self.globals.apps_by_name:
                app_id = self.globals.apps_by_name[rc]
                print "Opened window matched with gio app on name:", rc
            elif rc in self.globals.apps_by_exec:
                app_id = self.globals.apps_by_exec[rc]
                print "Opened window matched with gio app on executable:", rc
            else:
                for lname in self.globals.apps_by_longname:
                    pos = lname.find(rc)
                    if pos>-1: # Check that it is not part of word
                        if rc == lname \
                        or (pos==0 and lname[len(rc)] == ' ') \
                        or (pos+len(rc) == len(lname) and lname[pos-1] == ' ') \
                        or (lname[pos-1] == ' ' and lname[pos+len(rc)] == ' '):
                            app_id = self.globals.apps_by_longname[lname]
                            print "Opened window matched with gio app on longname:", rc
                            break
            if not app_id:
                if rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    print " trying to find as",rc
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    ### keys()
                    if rc in self.globals.apps_by_id.keys():
                        app_id = rc
                        print " found in apps id list as",rc
                    elif rc in self.globals.apps_by_name.keys():
                        app_id = self.globals.apps_by_name[rc]
                        print " found in apps name list as",rc
                    elif rc in self.globals.apps_by_exec.keys():
                        app_id = self.globals.apps_by_exec[rc]
                        print " found in apps exec list as",rc
            if app_id:
                app = self.globals.apps_by_id[app_id]
        return app

    def get_wine_app_name(self, window):
        # This function guesses an application name base on the window name
        # since all wine applications are has the identifier "Wine".
        name = window.get_name()
        # if the name has " - " in it the application is usually the part after it.
        name = name.split(" - ")[-1]
        return "Wine__" + name

    def get_ooo_app_name(self, window):
        # Separates the differnt openoffice applications from each other
        # The names are chosen to match the gio app ids.
        if not self.globals.settings['separate_ooo_apps']:
            return "openoffice.org-writer"
        name = window.get_name()
        for app in ['Calc', 'Impress', 'Draw', 'Math']:
            if name.endswith(app):
                return "openoffice.org-" + app.lower()
        else:
            return "openoffice.org-writer"

    def on_ooo_window_name_changed(self, window):
        identifier = None
        for group in self.groups.get_groups():
            if window in group.windows:
                identifier = group.identifier
                break
        else:
            print "OOo app error: Name changed but no group found."
        if identifier != self.get_ooo_app_name(window):
            self.on_window_closed(self.screen, window)
            self.on_window_opened(self.screen, window)
            if window == self.screen.get_active_window():
                self.on_active_window_changed(self.screen, None)


    #### Desktop events
    def on_desktop_changed(self, screen=None, workspace=None):
        if not self.globals.settings['show_only_current_desktop']:
            return
        for group in self.groups.get_groups():
            group.update_state()
            group.emit('set-icongeo-grp')
            group.nextlist = None


    #### Groupbuttons
    def make_groupbutton(self, class_group=None, identifier=None, launcher=None, app=None, path=None, index=None):
        gb = GroupButton(class_group, identifier, launcher, app)
        self.groups.add_group(identifier, gb, path)
        if index == None:
            self.container.pack_start(gb.button, False)
        else:
            # Insterts the button on it's index by removing
            # and repacking the buttons that should come after it
            repack_list = self.groups.get_groups()[index:]
            for group in repack_list:
                self.container.remove(group.button)
            self.container.pack_start(gb.button, False)
            for group in repack_list:
                self.container.pack_start(group.button, False)

        gb.connect('delete', self.remove_groupbutton)
        gb.connect('identifier-change', self.change_identifier)
        gb.connect('groupbutton-moved', self.on_groupbutton_moved)
        gb.connect('launcher-dropped', self.on_launcher_dropped)
        gb.connect('pinned', self.on_pinned)
        gb.connect('unpinned', self.on_unpinned)
        gb.connect('minimize-others', self.on_minimize_others)
        gb.connect('launch-preference', self.on_ppm_pref)

    def remove_groupbutton(self, arg, name):
        self.groups.remove(name)
        self.update_launchers_list()

    def on_pinned(self, arg, identifier, path):
        self.groups.set_launcher_path(identifier, path)
        self.update_launchers_list()

    def on_unpinned(self, arg, identifier):
        self.groups.remove_launcher(identifier)
        gb = self.groups[identifier]
        if gb.app == None:
                # The launcher is not of gio-app type.
                # The group button will be reset with its
                # non-launcher name and icon.
                gb.app = self.find_gio_app(identifier)
                gb.icon_factory.remove_launcher(class_group=gb.class_group, app = gb.app)
                gb.update_name()
        self.update_launchers_list()

    def on_minimize_others(self, arg, gb):
        for g in self.dockbar.groups.get_groups():
            if gb != g:
                for win in g.get_windows():
                    win.minimize()




    #### Launchers
    def add_launcher(self, identifier, path):
        """Adds a new launcher from a desktop file located at path and from the name"""
        launcher = Launcher(identifier, path)
        self.make_groupbutton(identifier=identifier, launcher=launcher, path = path)
        if identifier == None:
            id = path[path.rfind('/')+1:path.rfind('.')].lower()
            name = u""+launcher.get_entry_name().lower()
            exe = launcher.get_executable()
            self.launchers_by_id[id] = launcher
            if name.find(' ')>-1:
                self.launchers_by_longname[name] = id
            else:
                self.launchers_by_name[name] = id
            self.launchers_by_exec[exe] = id

    def on_launcher_dropped(self, arg, path, calling_button):
        # Creates a new launcher with a desktop file located at path
        # and lets the user enter the proper res class name in a
        # dialog. The new laucnher is inserted at the right (or under)
        # the group button that the launcher was dropped on.
        try:
            launcher = Launcher(None, path)
        except Exception, detail:
            print "ERROR: Couldn't read dropped file. Was it a desktop entry?"
            print "Error message:", detail
            return False

        id = path[path.rfind('/')+1:path.rfind('.')].lower()
        name = u""+launcher.get_entry_name().lower()
        exe = launcher.get_executable()

        if name.find(' ')>-1:
            lname = name
        else:
            lname = None

        if exe[0] == '/':
            exe = exe[exe.rfind('/')+1:]

        print "New launcher dropped"
        print "id: ", id
        if lname:
            print "long name: ", name
        else:
            print "name: ", name
        print "executable: ", exe
        print
        for identifier in self.groups.get_non_launcher_names():
            rc = u""+identifier.lower()
            if not rc:
                continue
            if rc == id:
                break
            if rc == name:
                break
            if rc == exe:
                break
            if lname:
                pos = lname.find(rc)
                if pos>-1: # Check that it is not part of word
                    if (pos==0) and (lname[len(rc)] == ' '):
                        break
                    elif (pos+len(rc) == len(lname)) and (lname[pos-1] == ' '):
                        break
                    elif (lname[pos-1] == ' ') and (lname[pos+len(rc)] == ' '):
                        break
            if rc.find(' ')>-1:
                    rc = rc.partition(' ')[0] # Cut all before space
                    # Workaround for apps
                    # with identifier like this 'App 1.2.3' (name with ver)
                    if rc == id:
                        break
                    elif rc == name:
                        break
                    elif rc == exe:
                        break
        else:
            # No open windows where found that could be connected
            # with the new launcher. Id, name and exe will be stored
            # so that it can be checked against new windows later.
            identifier = None
            self.launchers_by_id[id] = launcher
            if lname:
                self.launchers_by_longname[name] = id
            else:
                self.launchers_by_name[name] = id
            self.launchers_by_exec[exe] = id

        class_group = None
        if identifier:
            launcher.set_identifier(identifier)
        # Remove existing groupbutton for the same program
        winlist = []
        if calling_button in (identifier, path):
            index = self.groups.get_index(calling_button)
            group = self.groups[calling_button]
            class_group = group.get_class_group()
            # Get the windows for repopulation of the new button
            winlist = group.windows.keys()
            # Destroy the group button
            group.popup.destroy()
            group.button.destroy()
            group.winlist.destroy()
            self.groups.remove(calling_button)
        else:
            if identifier in self.groups.get_identifiers():
                group = self.groups[identifier]
                class_group = group.get_class_group()
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(identifier)
            elif path in self.groups.get_undefined_launchers():
                group = self.groups[path]
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(path)

            # Insert the new button after (to the
            # right of or under) the calling button
            index = self.groups.get_index(calling_button) + 1
        self.make_groupbutton(class_group=class_group, identifier=identifier, launcher=launcher, index=index, path=path)
        self.update_launchers_list()
        for window in winlist:
            self.on_window_opened(self.screen, window)
        return True

    def identifier_dialog(self, identifier=None):
        # Input dialog for inputting the identifier.
        dialog = gtk.MessageDialog(
            None,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL,
            None)
        dialog.set_title('Identifier')
        dialog.set_markup('<b>Enter the identifier here</b>')
        dialog.format_secondary_markup(
            'You should have to do this only if the program fails to recognice its windows. '+ \
            'If the program is already running you should be able to find the identifier of the program from the dropdown list.')
        #create the text input field
        #entry = gtk.Entry()
        combobox = gtk.combo_box_entry_new_text()
        entry = combobox.get_child()
        if identifier:
            entry.set_text(identifier)
        # Fill the popdown list with the names of all class names of buttons that hasn't got a launcher already
        for name in self.groups.get_non_launcher_names():
            combobox.append_text(name)
        entry = combobox.get_child()
        #entry.set_text('')
        #allow the user to press enter to do ok
        entry.connect("activate", lambda widget: dialog.response(gtk.RESPONSE_OK))
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label('Identifier:'), False, 5, 5)
        hbox.pack_end(combobox)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            text = entry.get_text()
        else:
            text = ''
        dialog.destroy()
        return text

    def on_groupbutton_moved(self, arg, name, calling_button=None):
        # Moves the button to the right of the calling button.

        #Remove the groupbutton that should be moved
        move_group = self.groups.get_group(name)
        move_path = self.groups.get_launcher_path(name)
        self.container.remove(move_group.button)
        self.groups.remove(name)

        if calling_button:
            index = self.groups.get_index(calling_button) + 1
        else:
            print "Error: cant move button without either a index or the calling button's name"
            return
        # Insterts the button on it's index by removing
        # and repacking the buttons that should come after it
        repack_list = self.groups.get_groups()[index:]
        for group in repack_list:
            self.container.remove(group.button)
        self.container.pack_start(move_group.button, False)
        for group in repack_list:
            self.container.pack_start(group.button, False)
        self.groups.add_group(name, move_group, move_path, index)
        self.update_launchers_list()

    def change_identifier(self, arg=None, path=None, identifier=None):
        identifier = self.identifier_dialog(identifier)
        if not identifier:
            return False
        winlist = []
        if identifier in self.groups.get_identifiers():
                group = self.groups[identifier]
                # Get the windows for repopulation of the new button
                winlist = group.windows.keys()
                # Destroy the group button
                group.popup.destroy()
                group.button.destroy()
                group.winlist.destroy()
                self.groups.remove(identifier)
        self.groups.set_identifier(path, identifier)
        for window in winlist:
            self.on_window_opened(self.screen, window)
        self.update_launchers_list()

    def update_launchers_list(self):
        # Saves launchers_list to gconf.
        launchers_list = self.groups.get_launchers_list()
        gconf_launchers = []
        for identifier, path in launchers_list:
            if identifier == None:
                identifier = ''
            gconf_launchers.append(identifier + ';' + path)
        self.globals.set_launchers_list(gconf_launchers)

    def remove_launcher_id_from_undefined_list(self, id):
        self.launchers_by_id.pop(id)
        for l in (self.launchers_by_name, self.launchers_by_exec,
                     self.launchers_by_longname):
            for key, value in l.items():
                if value == id:
                    l.pop(key)
                    break

    def cleanup(self,event):
        del self.applet