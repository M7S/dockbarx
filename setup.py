#!/usr/bin/python

from distutils.core import setup
import os
import sys

setup(name='Dockbarx',
      version='0.3.1',
      description='A dock-ish gnome-applet',
      author='Aleksey Shaferov and Matias Sars',
      url='http://launchpad.net/dockbar/',
      packages=['dockbarx'],
      data_files=[('/usr/share/dockbarx/themes', ['themes/default.tar.gz',
                                                'themes/Gaia.tar.gz',
                                                'themes/human_bar.tar.gz',
                                                'themes/minimalistic.tar.gz',
                                                'themes/new_theme.tar.gz', ]),
                  ('/usr/bin', ['dockbarx_factory.py', 'dbx_preference.py']),
                  ('/usr/lib/bonobo/servers', ['GNOME_DockBarXApplet.server']),
                  ('/usr/share/applications/', ['dbx_preference.desktop']),
                  ('share/icons/hicolor/128x128/apps', ['icons/hicolor/128x128/apps/dockbarx.png']),
                  ('share/icons/hicolor/96x96/apps', ['icons/hicolor/96x96/apps/dockbarx.png']),
                  ('share/icons/hicolor/72x72/apps', ['icons/hicolor/72x72/apps/dockbarx.png']),
                  ('share/icons/hicolor/64x64/apps', ['icons/hicolor/64x64/apps/dockbarx.png']),
                  ('share/icons/hicolor/48x48/apps', ['icons/hicolor/48x48/apps/dockbarx.png']),
                  ('share/icons/hicolor/36x36/apps', ['icons/hicolor/36x36/apps/dockbarx.png']),
                  ('share/icons/hicolor/24x24/apps', ['icons/hicolor/24x24/apps/dockbarx.png']),
                  ('share/icons/hicolor/22x22/apps', ['icons/hicolor/22x22/apps/dockbarx.png']),
                  ('share/icons/hicolor/16x16/apps', ['icons/hicolor/16x16/apps/dockbarx.png']),
                 ],
     )


# Remove old dockbarx.py so that it isn't imported instead of the package dockbarx when dockbarx is run.
if os.path.exists('/usr/bin/dockbarx.py') and len(sys.argv) == 2 and sys.argv[1] == 'install':
    print
    print 'There is a dockbarx.py in /usr/bin. This has to be removed to make DockbarX run correctly.'
    remove = raw_input('Remove /usr/bin/dockbarx.py? (Y/n)')
    if remove == ""or remove[0].lower() == 'y':
        os.remove('/usr/bin/dockbarx.py')
    else:
        print '/usr/bin/dockbarx.py is not removed. Please remove it or rename it manually.'
