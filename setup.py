#!/usr/bin/python

from distutils.core import setup

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
                  ('/usr/lib/bonobo/servers', ['GNOME_DockBarXApplet.server'])],
     )
