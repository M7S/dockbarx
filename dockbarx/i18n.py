#!/usr/bin/python3

import os
import sysconfig
import locale
import gettext
from .dirutils import get_data_dirs

APP_DOMAIN = "dockbarx"
THEME_DOMAIN = "dockbarx-themes"

def find_mo_location(domain):
    data_dirs = get_data_dirs()
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
