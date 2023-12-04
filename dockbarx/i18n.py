#!/usr/bin/python3

import os
import sysconfig
import locale
import gettext

APP_DOMAIN = "dockbarx"
THEME_DOMAIN = "dockbarx-themes"

def find_mo_location(domain):
    def_data_dirs = ( "/usr/local/share", "/usr/share" )
    data_dirs = os.environ.get("XDG_DATA_DIRS", "")
    if not data_dirs:
        home = os.environ.get("XDG_DATA_HOME", os.path.expanduser('~'))
        data_dirs = os.path.join(home, ".local", "share")
    data_dirs = data_dirs.split(":")
    for d in def_data_dirs:
        if d not in data_dirs:
            data_dirs.append(d)
    for d in data_dirs:
        locale_dir = os.path.join(d, "locale")
        if gettext.find(domain, locale_dir):
            return locale_dir
    return os.path.join(sysconfig.get_path("data"), "share")


gettext.install(True)

app_mo_location = find_mo_location(APP_DOMAIN)
gettext.bindtextdomain(APP_DOMAIN, app_mo_location)
gettext.textdomain(APP_DOMAIN)
language = gettext.translation(APP_DOMAIN, app_mo_location, fallback = True)

theme = None

def load_theme_translation():
    global theme
    theme_mo_location = find_mo_location(THEME_DOMAIN)
    gettext.bindtextdomain(THEME_DOMAIN, theme_mo_location)
    theme = gettext.translation(THEME_DOMAIN, theme_mo_location, fallback = True)
