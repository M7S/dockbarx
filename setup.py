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
from setuptools.command.install import install as _install
from setuptools.command.build_py import build_py as _build_py

import polib
import os
import sys

VERSION = "1.0-beta3"

dbx_files = []

def scan_path(file_list, dest, base_path, ext="", exclude_ext=None, fixed_dest=False):
    files = []
    for f in os.listdir(base_path):
        fpath = os.path.join(base_path, f)
        if fpath == ".git":
            continue
        elif os.path.isdir(fpath):
            instdir = dest if fixed_dest else os.path.join(dest, f)
            scan_path(file_list, instdir, os.path.join(base_path, f), ext, exclude_ext, fixed_dest)
        elif os.path.isfile(fpath) and fpath.endswith(ext) and (exclude_ext is None or not fpath.endswith(exclude_ext)):
            files.append(fpath)
    if files:
        file_list.append( ( dest, files ) )

scan_path(dbx_files, "bin", "utils")
scan_path(dbx_files, "share/applications", "data", ext=".desktop")
scan_path(dbx_files, "share/dockbarx/applets", "applets", exclude_ext=".gschema.xml")
scan_path(dbx_files, "share/dockbarx/themes", "data/themes", ext=".tar.gz")
scan_path(dbx_files, "share/glib-2.0/schemas", os.curdir, ext=".gschema.xml", fixed_dest=True)
scan_path(dbx_files, "share/icons", "data/icons", ext=".png")

class build_py(_build_py):

    def build_package_data(self):
        _build_py.build_package_data(self)
        self.build_trans()

    def build_trans(self):
        po_dict = {
            os.path.join(os.path.dirname(os.curdir), "data/po") : "dockbarx",
            os.path.join(os.path.dirname(os.curdir), "data/po-themes") : "dockbarx-themes"
        }
        for path in po_dict.keys():
            for f in os.listdir(path):
                if f.endswith(".po"):
                    lang = f[:len(f) - 3]
                    src = os.path.join(path, f)
                    domain = po_dict[path]
                    dest_path = os.path.join("build", "locale", lang, "LC_MESSAGES")
                    dest = os.path.join(dest_path, "%s.mo" % domain)
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    print("Compiling %s for %s" % (src, domain))
                    po = polib.pofile(src);
                    po.save_as_mofile(dest)
        scan_path(dbx_files, "share/locale", "build/locale", ext=".mo")

class install(_install):

    def run(self):
        if self.distribution.data_files is None:
            self.distribution.data_files = dbx_files
        else:
            for d in dbx_files:
                self.distribution.data_files.append(d)
        _install.run(self)


cmdclass = {
    "build_py": build_py,
    "install": install,
}

setup(name="Dockbarx",
      version=VERSION,
      description="A dock-ish gnome-applet",
      author="Aleksey Shaferov and Matias Sars",
      url="http://launchpad.net/dockbar/",
      packages=["dockbarx"],
      cmdclass=cmdclass
     )


