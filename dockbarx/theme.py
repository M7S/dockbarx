#!/usr/bin/python

from tarfile import open as taropen
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import gobject
import cairo
import os
from common import ODict
from common import Globals

class NoThemesError(Exception):
    pass

class ThemeHandler(ContentHandler):
    """Reads the xml-file into a ODict"""
    def __init__(self):
        self.dict = ODict()
        self.name = None
        self.nested_contents = []
        self.nested_contents.append(self.dict)
        self.nested_attributes = []

    def startElement(self, name, attrs):
        name = name.lower().encode()
        if name == 'theme':
            for attr in attrs.keys():
                if attr.lower() == 'name':
                    self.name = attrs[attr]
            return
        # Add all attributes to a dictionary
        d = {}
        for attr in attrs.keys():
            # make sure that all text is in lower
            d[attr.encode().lower()] = attrs[attr].encode().lower()
        # Add a ODict to the dictionary in which all
        # content will be put.
        d['content'] = ODict()
        self.nested_contents[-1][name] = d
        # Append content ODict to the list so that it
        # next element will be put there.
        self.nested_contents.append(d['content'])

        self.nested_attributes.append(d)

    def endElement(self, name):
        if name == 'theme':
            return
        # Pop the last element of nested_contents
        # so that the new elements won't show up
        # as a content to the ended element.
        if len(self.nested_contents)>1:
            self.nested_contents.pop()
        # Remove Content Odict if the element
        # had no content.
        d = self.nested_attributes.pop()
        if d['content'].keys() == []:
                d.pop('content')

    def get_dict(self):
        return self.dict

    def get_name(self):
        return self.name

class Theme(gobject.GObject):
    __gsignals__ = {
        "theme_reloaded": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,()),
    }

    def __new__(cls, *p, **k):
        if not '_the_instance' in cls.__dict__:
            cls._the_instance = gobject.GObject.__new__(cls)
        return cls._the_instance

    def __init__(self):
        if 'theme' in self.__dict__:
            # This is not the first instance of Theme, no need to initiate anything
            return
        gobject.GObject.__init__(self)
        self.globals = Globals()
        self.globals.connect('theme_changed', self.on_theme_changed)
        self.on_theme_changed()

    def on_theme_changed(self, arg=None):
        themes = self.find_themes()
        default_theme_path = None
        for theme, path in themes.items():
            if theme.lower() == self.globals.settings['theme'].lower():
                self.theme_path = path
                break
            if theme.lower == self.globals.DEFAULT_SETTINGS['theme'].lower():
                default_theme_path = path
        else:
            if default_theme_path:
                # If the current theme according to gconf couldn't be found,
                # the default theme is used.
                self.theme_path = default_theme_path
            else:
                # Just use one of the themes that where found if default
                # theme couldn't be found either.
                self.theme_path = themes.values()[0]

        self.reload()

    def find_themes(self):
        # Reads the themes from /usr/share/dockbarx/themes and ~/.dockbarx/themes
        # and returns a dict of the theme names and paths so that
        # a theme can be loaded
        themes = {}
        theme_paths = []
        homeFolder = os.path.expanduser("~")
        theme_folder = homeFolder + "/.dockbarx/themes"
        dirs = ["/usr/share/dockbarx/themes", theme_folder]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == '.tar.gz':
                        theme_paths.append(dir+"/"+f)
        for theme_path in theme_paths:
            try:
                name = self.check(theme_path)
            except Exception, detail:
                print "Error loading theme from %s"%theme_path
                print detail
                name = None
            if name != None:
                name = str(name)
                themes[name] = theme_path
        if not themes:
            md = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                'No working themes found in "/usr/share/dockbarx/themes" or "~/.dockbarx/themes"')
            md.run()
            md.destroy()
            raise NoThemesError('No working themes found in "/usr/share/dockbarx/themes" or "~/.dockbarx/themes"')
        return themes

    def reload(self):
        tar = taropen(self.theme_path)
        config = tar.extractfile('config')

        # Parse
        parser = make_parser()
        theme_handler = ThemeHandler()
        parser.setContentHandler(theme_handler)
        parser.parse(config)
        self.theme = theme_handler.get_dict()

        # Name
        self.name = theme_handler.get_name()

        # Pixmaps
        self.surfaces = {}
        pixmaps = {}
        if self.theme.has_key('pixmaps'):
            pixmaps = self.theme['pixmaps']['content']
        for (type, d) in pixmaps.items():
            if type == 'pixmap_from_file':
                self.surfaces[d['name']] = self.load_surface(tar, d['file'])

        # Colors
        self.color_names = {}
        self.default_colors = {}
        self.default_alphas = {}
        colors = {}
        if self.theme.has_key('colors'):
            colors = self.theme['colors']['content']
        for i in range(1, 9):
            c = 'color%s'%i
            if colors.has_key(c):
                d = colors[c]
                if d.has_key('name'):
                    self.color_names[c] = d['name']
                if d.has_key('default'):
                    if self.test_color(d['default']):
                        self.default_colors[c] = d['default']
                    else:
                        print 'Theme error: %s\'s default for theme %s cannot be read.'%(c, self.name)
                        print 'A default color should start with an "#" and be followed by six hex-digits, ' + \
                              'for example "#FF13A2".'
                if d.has_key('opacity'):
                    alpha = d['opacity']
                    if self.test_alpha(alpha):
                        self.default_alphas[c] = alpha
                    else:
                        print 'Theme error: %s\'s opacity for theme %s cannot be read.'%(c, self.name)
                        print 'The opacity should be a number ("0"-"100") or the words "not used".'

        config.close()
        tar.close()

        # Inform rest of dockbar about the reload.
        self.globals.theme_name = self.name
        self.globals.update_colors(self.name, self.default_colors, self.default_alphas)
        self.emit('theme_reloaded')

    def check(self, path_to_tar):
        #TODO: Optimize this
        tar = taropen(path_to_tar)
        config = tar.extractfile('config')
        parser = make_parser()
        theme_handler = ThemeHandler()
        try:
            parser.setContentHandler(theme_handler)
            parser.parse(config)
        except:
            config.close()
            tar.close()
            raise
        config.close()
        tar.close()
        return theme_handler.get_name()

    def print_dict(self, d, indent=""):
        for key in d.keys():
            if key == 'content' or type(d[key]) == dict:
                print "%s%s={"%(indent,key)
                self.print_dict(d[key], indent+"   ")
                print "%s}"%indent
            else:
                print '%s%s = %s'%(indent,key,d[key])

    def load_pixbuf(self, tar, name):
        f = tar.extractfile('pixmaps/'+name)
        buffer=f.read()
        pixbuf_loader=gtk.gdk.PixbufLoader()
        pixbuf_loader.write(buffer)
        pixbuf_loader.close()
        f.close()
        pixbuf=pixbuf_loader.get_pixbuf()
        return pixbuf

    def load_surface(self, tar, name):
        f = tar.extractfile('pixmaps/'+name)
        surface = cairo.ImageSurface.create_from_png(f)
        f.close()
        return surface

    def has_surface(self, name):
        if name in self.surfaces:
            return True
        else:
            return False

    def get_surface(self, name):
        return self.surfaces[name]

    def get_icon_dict(self):
        return self.theme['button_pixmap']['content']

    def get_name(self):
        return self.name

    def get_gap(self):
        return int(self.theme['button_pixmap'].get('gap', 0))

    def get_windows_cnt(self):
        return int(self.theme['button_pixmap'].get('windows_cnt', 1))

    def get_aspect_ratio(self):
        ar = self.theme['button_pixmap'].get('aspect_ratio', "1")
        l = ar.split('/',1)
        if len(l) == 2:
            ar = float(l[0])/float(l[1])
        else:
            ar = float(ar)
        return ar

    def get_default_colors(self):
        return self.default_colors

    def get_default_alphas(self):
        return self.default_alphas

    def get_color_names(self):
        return self.color_names

    def test_color(self, color):
        if len(color) != 7:
            return False
        try:
            t = int(color[1:], 16)
        except:
            return False
        return True

    def test_alpha(self, alpha):
        if 'no' in alpha:
            return True
        try:
            t = int(alpha)
        except:
            return False
        if t<0 or t>100:
            return False
        return True

    def remove(self):
        del self.color_names
        del self.default_colors
        del self.default_alphas
        del self.surfaces

