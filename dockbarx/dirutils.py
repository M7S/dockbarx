#!/usr/bin/python3

#   dirutils.py
#
#	Copyright 2023 Xu Zhen
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

import os
import sys
from collections import OrderedDict

appdir = None
def get_app_homedir():
    global appdir
    if appdir is not None:
        return appdir
    homedir = os.environ.get("XDG_DATA_HOME", os.environ.get("HOME", os.path.expanduser('~')))
    appdir = os.path.join(homedir, '.local', 'share', "dockbarx")
    """
    Migration Path
    From "$HOME/.dockbarx" to "${XDG_DATA_HOME:-$HOME/.local/share}/dockbarx"
    """
    old_appdir = os.path.join(homedir, '.dockbarx')
    if os.path.exists(old_appdir) and os.path.isdir(old_appdir):
        try:
            os.rename(old_appdir, appdir)
        except OSError:
            sys.stderr.write(
            "Could not move dir '%s' to '%s'. Move the contents of '%s' to '%s' manually and then remove the first location.\n"
            % (old_appdir, appdir, old_appdir, appdir)
            )
    """
    End Migration Path
    """
    return appdir

def get_app_dirs():
    data_dirs = get_data_dirs()
    app_dirs = [ os.path.join(d, "dockbarx") for d in data_dirs ]
    return app_dirs

def get_data_dirs(user_first=True):
    data_dirs = []
    home_dir = os.environ.get("XDG_DATA_HOME", os.environ.get("HOME", os.path.expanduser('~')))
    user_dir = os.path.join(home_dir, ".local", "share")
    if user_first:
        data_dirs.append(user_dir)
    env = os.environ.get("XDG_DATA_DIRS")
    if env:
        data_dirs.extend(env.split(":"))
    if not user_first:
        data_dirs.append(user_dir)
    data_dirs.extend( ( "/usr/local/share", "/usr/share" ) )
    # dict.fromkeys can be used instead for python 3.7+
    return list(OrderedDict.fromkeys(data_dirs))

