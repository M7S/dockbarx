#!/usr/bin/python

#   groupbutton.py
#
#	Copyright 2010 Matias Sars
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

from distutils.core import setup
from distutils.core import setup
from distutils import cmd
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build

import msgfmt
import os
import sys

class build_trans(cmd.Command):
    description = 'Compile .po files into .mo files'
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        po_dict = {
                    'dockbarx': os.path.join(os.path.dirname(os.curdir), 'po'),
                    'dockbarx-themes': os.path.join(os.path.dirname(os.curdir), 'po-themes')
                  }
        for (mo_file, po_dir) in po_dict.items():
            for path, names, filenames in os.walk(po_dir):
                for f in filenames:
                    if f.endswith('.po'):
                        lang = f[:len(f) - 3]
                        src = os.path.join(path, f)
                        dest_path = os.path.join('build', 'locale', lang, 'LC_MESSAGES')
                        dest = os.path.join(dest_path, "%s.mo"%mo_file)
                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)
                        if not os.path.exists(dest):
                            print 'Compiling %s for %s' % (src, mo_file)
                            msgfmt.make(src, dest)
                        else:
                            src_mtime = os.stat(src)[8]
                            dest_mtime = os.stat(dest)[8]
                            if src_mtime > dest_mtime:
                                print 'Compiling %s for %s' % (src, mo_file)
                                msgfmt.make(src, dest)

class build(_build):
    sub_commands = _build.sub_commands + [('build_trans', None)]
    def run(self):
        _build.run(self)

class install_data(_install_data):

    def run(self):
        for lang in os.listdir('build/locale/'):
            lang_dir = os.path.join('/', 'usr', 'share', 'locale', lang, 'LC_MESSAGES')
            lang_files = []
            d_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES', 'dockbarx.mo')
            dt_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES', 'dockbarx-themes.mo')
            if os.path.exists(d_file):
                lang_files.append(d_file)
            if os.path.exists(dt_file):
                lang_files.append(dt_file)
            self.data_files.append( (lang_dir, lang_files) )
        _install_data.run(self)

cmdclass = {
    'build': build,
    'build_trans': build_trans,
    'install_data': install_data,
}

data_files=[('/usr/share/dockbarx/themes', ['themes/dbx.tar.gz',
                                            'themes/Gaia.tar.gz',
                                            'themes/old.tar.gz',
                                            'themes/minimalistic.tar.gz',
                                            'themes/sunny-c.tar.gz',
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
         ]

setup(name='Dockbarx',
      version='0.3.1',
      description='A dock-ish gnome-applet',
      author='Aleksey Shaferov and Matias Sars',
      url='http://launchpad.net/dockbar/',
      packages=['dockbarx'],
      data_files=data_files,
      cmdclass=cmdclass
     )



if len(sys.argv) == 2 and sys.argv[1] == 'install':
    if os.path.exists('/usr/bin/dockbarx.py'):
        # Remove old dockbarx.py so that it isn't imported
        # instead of the package dockbarx when dockbarx is run.
        print
        print 'There is a dockbarx.py in /usr/bin. ' + \
              'This has to be removed to make DockbarX run correctly.'
        remove = raw_input('Remove /usr/bin/dockbarx.py? (Y/n)')
        if remove == "" or remove[0].lower() == 'y':
            os.remove('/usr/bin/dockbarx.py')
        else:
            print '/usr/bin/dockbarx.py is not removed. ' + \
                  'Please remove it or rename it manually.'
