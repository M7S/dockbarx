import os, sys
import locale
import gettext



APP_NAME = "dockbarx"


APP_DIR = os.path.join (sys.prefix,
                        "share")
LOCALE_DIR = os.path.join(APP_DIR, "locale")

mo_location = LOCALE_DIR


gettext.install (True)

gettext.bindtextdomain (APP_NAME,
                        mo_location)
gettext.textdomain (APP_NAME)
language = gettext.translation (APP_NAME,
                                mo_location,
                                fallback = True)



theme = None

def load_theme_translation():
    global theme
    gettext.bindtextdomain("dockbarx-themes", mo_location)
    theme = gettext.translation("dockbarx-themes",
                                mo_location,
                                fallback = True)
