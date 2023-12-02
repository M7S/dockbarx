#!/usr/bin/python3

#   setup.py
#
#	Copyright 2010- Matias Sars
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

from setuptools import setup
from setuptools import Command
from setuptools.command.install import install as _install
from setuptools.command.build import build as _build

import polib
import os
import sys

VERSION = "1.0-beta3"

class build_trans(Command):
    description = "Compile .po files into .mo files"
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        po_dict = {
                    "dockbarx": os.path.join(os.path.dirname(os.curdir), "po"),
                    "dockbarx-themes": os.path.join(os.path.dirname(os.curdir), "po-themes")
                  }
        for (mo_file, po_dir) in list(po_dict.items()):
            for path, names, filenames in os.walk(po_dir):
                for f in filenames:
                    if f.endswith(".po"):
                        lang = f[:len(f) - 3]
                        src = os.path.join(path, f)
                        dest_path = os.path.join("build", "locale", lang, "LC_MESSAGES")
                        dest = os.path.join(dest_path, "%s.mo"%mo_file)
                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)
                        if not os.path.exists(dest):
                            print("Compiling %s for %s" % (src, mo_file))
                            po = polib.pofile(src);
                            po.save_as_mofile(dest)
                        else:
                            src_mtime = os.stat(src)[8]
                            dest_mtime = os.stat(dest)[8]
                            if src_mtime > dest_mtime:
                                print("Compiling %s for %s" % (src, mo_file))
                                po = polib.pofile(src);
                                po.save_as_mofile(dest)

class build(_build):
    sub_commands = _build.sub_commands + [("build_trans", None)]
    def run(self):
        _build.run(self)

class install(_install):

    def run(self):
        for lang in os.listdir("build/locale/"):
            lang_dir = os.path.join("/", "usr", "share",
                                    "locale", lang, "LC_MESSAGES")
            lang_files = []
            d_file = os.path.join("build", "locale", lang,
                                  "LC_MESSAGES", "dockbarx.mo")
            dt_file = os.path.join("build", "locale", lang,
                                   "LC_MESSAGES", "dockbarx-themes.mo")
            if os.path.exists(d_file):
                lang_files.append(d_file)
            if os.path.exists(dt_file):
                lang_files.append(dt_file)
            self.distribution.data_files.append( (lang_dir, lang_files) )
        # Scan folders for the right files
        self.scan_path("share/dockbarx/themes", "themes", ext=".tar.gz")
        self.scan_path("share/icons/", "icons", ext=".png")
        self.scan_path("share/dockbarx/applets/namebar_themes",
                       "dockx_applets/namebar_themes",
                       ext=".tar.gz")
        _install.run(self)

    def scan_path(self, install_path, base_path, path="", ext=""):
        files = []
        for f in os.listdir(os.path.join(base_path, path)):
            fpath = os.path.join(base_path, path, f)
            if os.path.isdir(fpath):
                self.scan_path(install_path, base_path,
                               os.path.join(path, f), ext)
            elif os.path.isfile(fpath) and fpath.endswith(ext):
                files.append(fpath)
        if files:
            self.distribution.data_files.append((os.path.join(install_path, path), files))


cmdclass = {
    "build": build,
    "build_trans": build_trans,
    "install": install,
}

data_files=[
            ("share/dockbarx/applets", ["dockx_applets/clock.py",
                                             "dockx_applets/clock.applet",
                                             "dockx_applets/appindicator.py",
                                             "dockx_applets/appindicator.applet",
                                             "dockx_applets/hello_world.py",
                                             "dockx_applets/hello_world.applet",
                                             "dockx_applets/battery_status.py",
                                             "dockx_applets/battery_status.applet",
                                             "dockx_applets/battery_status_helper.sh",
                                             "dockx_applets/namebar_common.py",
                                             "dockx_applets/namebar_window_buttons.applet",
                                             "dockx_applets/namebar_window_buttons.py",
                                             "dockx_applets/namebar_window_title.applet",
                                             "dockx_applets/namebar_window_title.py"]),
            ("bin", ["dbx_preference", "dbx_migrate_settings", "dockx"]),
            ("lib/mate-panel/", ["mate_panel_applet/dockbarx_mate_applet"]),
            ("share/applications/", ["dbx_preference.desktop"]),
            ("share/applications/", ["DockX.desktop"]),
            ("share/glib-2.0/schemas/", ["org.dockbar.dockbarx.gschema.xml",
                                         "dockx_applets/org.dockbar.applets.clock.gschema.xml",
                                         "dockx_applets/org.dockbar.applets.hello-world.gschema.xml",
                                         "dockx_applets/org.dockbar.applets.batterystatus.gschema.xml",
                                         "dockx_applets/org.dockbar.applets.namebar.gschema.xml"]),
            ("share/dbus-1/services/", ["mate_panel_applet/org.mate.panel.applet.DockbarXAppletFactory.service"]),
            ("share/mate-panel/applets/", ["mate_panel_applet/org.mate.panel.DockbarX.mate-panel-applet"]),
            ("share/mate-panel/ui/", ["mate_panel_applet/dockbarx-applet-menu.xml"]),
         ]

setup(name="Dockbarx",
      version=VERSION,
      description="A dock-ish gnome-applet",
      author="Aleksey Shaferov and Matias Sars",
      url="http://launchpad.net/dockbar/",
      packages=["dockbarx"],
      data_files=data_files,
      cmdclass=cmdclass
     )


