#!/usr/bin/python3

#   theme.py
#
#   Copyright 2009, 2010 Matias Sars
#
#   DockbarX is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DockbarX is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

from tarfile import open as taropen
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GObject
import cairo
import os
import array
from .common import ODict
from .common import Globals
from .dirutils import get_app_dirs
from .log import logger
from PIL import Image

from . import i18n
_ = i18n.language.gettext

class NoThemesError(Exception):
    pass

class ThemeHandler(ContentHandler):
    """Reads the xml-file into a ODict"""
    def __init__(self):
        self.dict = ODict()
        self.name = None
        self.types = []
        self.nested_contents = []
        self.nested_contents.append(self.dict)
        self.nested_attributes = []

    def startElement(self, name, attrs):
        name = name.lower()
        if name == "theme":
            for attr in list(attrs.keys()):
                if attr.lower() == "name":
                    self.name = attrs[attr]
            return
        # Add all attributes to a dictionary
        d = {}
        for key, value in list(attrs.items()):
            # make sure that all text is in lower
            # except for file_names
            if key.lower() == "file_name":
                d[key.lower()] = value
            else:
                d[key.lower()] = value.lower()
        # Add a ODict to the dictionary in which all
        # content will be put.
        d["content"] = ODict()
        self.nested_contents[-1][name] = d
        # Append content ODict to the list so that it
        # next element will be put there.
        self.nested_contents.append(d["content"])

        self.nested_attributes.append(d)

        if name == "if" and "type" in d:
            self.__add_to_types(d["type"])

    def endElement(self, name):
        if name == "theme":
            return
        # Pop the last element of nested_contents
        # so that the new elements won't show up
        # as a content to the ended element.
        if len(self.nested_contents)>1:
            self.nested_contents.pop()
        # Remove Content Odict if the element
        # had no content.
        d = self.nested_attributes.pop()
        if list(d["content"].keys()) == []:
                d.pop("content")

    def __add_to_types(self, type):
        if type[0] == "!":
            type == type[1:]
        if not type in self.types:
            self.types.append(type)

    def get_dict(self):
        return self.dict

    def get_name(self):
        return self.name

    def get_types(self):
        return self.types

class Theme(GObject.GObject):
    __gsignals__ = {
        "theme_reloaded": (GObject.SignalFlags.RUN_FIRST, None,()),
    }

    def __new__(cls, *p, **k):
        if not "_the_instance" in cls.__dict__:
            cls._the_instance = GObject.GObject.__new__(cls)
        return cls._the_instance

    def __init__(self):
        if "theme" in self.__dict__:
            # This is not the first instance of Theme,
            # no need to initiate anything
            return
        GObject.GObject.__init__(self)
        self.globals = Globals()
        self.globals.connect("theme_changed", self.on_theme_changed)
        self.on_theme_changed()

    def on_theme_changed(self, arg=None):
        self.themes = self.find_themes()
        default_theme_path = None
        for theme, path in list(self.themes.items()):
            if theme.lower() == self.globals.settings["theme"].lower():
                self.theme_path = path
                break
            if theme.lower() == self.globals.DEFAULT_SETTINGS["theme"].lower():
                default_theme_path = path
        else:
            if default_theme_path:
                # If the current theme according to settings couldn't be found,
                # the default theme is used.
                self.theme_path = default_theme_path
            else:
                # Just use one of the themes that where found if default
                # theme couldn't be found either.
                self.theme_path = list(self.themes.values())[0]
        self.globals.set_theme_gsettings(self.theme_path)
        self.reload()

    def find_themes(self):
        # Reads the themes from APP_DIRS/themes
        # and returns a dict of the theme names and paths so
        # that a theme can be loaded.
        themes = {}
        theme_paths = []
        app_dirs = get_app_dirs()
        dirs = [os.path.join(d, "themes") for d in app_dirs]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == ".tar.gz":
                        theme_paths.append(dir+"/"+f)
        for theme_path in theme_paths:
            try:
                name = self.check(theme_path)
            except Exception as detail:
                logger.exception("Error loading theme from %s"%theme_path)
                name = None
            if name is not None:
                name = str(name)
                themes[name] = theme_path
        if not themes:
            md = Gtk.MessageDialog(None,
                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                _("No working themes found in any of these locations:\n\n%s") % "\n".join(dirs))
            md.run()
            md.destroy()
            raise NoThemesError("No working themes found")
        return themes

    def reload(self):
        tar = taropen(self.theme_path)
        config = tar.extractfile("config")

        # Parse
        parser = make_parser()
        theme_handler = ThemeHandler()
        parser.setContentHandler(theme_handler)
        parser.parse(config)
        self.theme = theme_handler.get_dict()

        # Name
        self.name = theme_handler.get_name()

        self.types = theme_handler.get_types()

        # Pixmaps
        self.surfaces = {}
        pixmaps = {}
        if "pixmaps" in self.theme:
            pixmaps = self.theme["pixmaps"]["content"]
        for (type_, d) in list(pixmaps.items()):
            if type_ == "pixmap_from_file":
                self.surfaces[d["name"]] = self.load_surface(tar, d["file"])

        # Popup style
        ps = self.theme.get("popup_style", {})
        self.default_popup_style = ps.get("file_name", "dbx.tar.gz")

        # Colors
        self.color_names = {}
        self.default_colors = {}
        self.default_alphas = {}
        colors = {}
        if "colors" in self.theme:
            colors = self.theme["colors"]["content"]
        for i in range(1, 9):
            c = "color%s"%i
            if c in colors:
                d = colors[c]
                if "name" in d:
                    self.color_names[c] = d["name"]
                if "default" in d:
                    if self.test_color(d["default"]):
                        self.default_colors[c] = d["default"]
                    else:
                        logger.warning("Theme error: %s\'s default for" % c + \
                                       " theme %s cannot be read." % self.name)
                        logger.info("A default color should start with an " + \
                                    "\"#\" and be followed by six " + \
                                    "hex-digits, for example \"#FF13A2\".")
                if "opacity" in d:
                    alpha = d["opacity"]
                    if self.test_alpha(alpha):
                        self.default_alphas[c] = alpha
                    else:
                        logger.warning("Theme error: %s\'s opacity" % c + \
                                       " for theme %s" % self.name + \
                                       " cannot be read.")
                        logger.info("The opacity should be a number " + \
                                    "(\"0\"-\"100\") or the words " + \
                                    "\"not used\".")


        # Sets
        self.sets = {}
        sets = {}
        if "sets" in self.theme:
            sets = self.theme["sets"]["content"]
        for (type_, d) in list(sets.items()):
            if type_ == "set":
                self.sets[d["name"]] = d
        config.close()
        tar.close()

        # Inform rest of dockbar about the reload.
        self.globals.set_theme_gsettings(self.name)
        self.globals.update_colors(self.name, self.default_colors, self.default_alphas)
        self.globals.update_popup_style(self.default_popup_style)
        self.emit("theme_reloaded")

    def check(self, path_to_tar):
        #TODO: Optimize this
        tar = taropen(path_to_tar)
        config = tar.extractfile("config")
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
        for key in list(d.keys()):
            if key == "content" or type(d[key]) == dict:
                print("%s%s={"%(indent,key))
                self.print_dict(d[key], indent+"   ")
                print("%s}"%indent)
            else:
                print("%s%s = %s"%(indent,key,d[key]))

    def load_pixbuf(self, tar, name):
        f = tar.extractfile("pixmaps/"+name)
        buffer=f.read()
        pixbuf_loader=GdkPixbuf.PixbufLoader()
        pixbuf_loader.write(buffer)
        pixbuf_loader.close()
        f.close()
        pixbuf=pixbuf_loader.get_pixbuf()
        return pixbuf

    def load_surface(self, tar, name):
        f = tar.extractfile("pixmaps/"+name)
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
        return self.theme["button_pixmap"]["content"]

    def get_name(self):
        return self.name

    def get_types(self):
        return self.types

    def get_gap(self):
        return int(self.theme["button_pixmap"].get("gap", 0))

    def get_windows_cnt(self):
        return int(self.theme["button_pixmap"].get("windows_cnt", 1))

    def get_aspect_ratio(self, vertical=False):
        ar = self.theme["button_pixmap"].get("aspect_ratio", "1")
        if vertical:
            ar = self.theme["button_pixmap"].get("aspect_ratio_v", ar)
        l = ar.split("/",1)
        if len(l) == 2:
            ar = float(l[0])/float(l[1])
        else:
            ar = float(ar)
        if vertical and "aspect_ratio_v" in self.theme["button_pixmap"]:
            ar = 1 / ar
        return ar

    def get_from_set(self, sname, orient):
        if not sname in self.sets:
            return None
        s = self.sets[sname]
        return s.get(orient, "0")

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
        if "no" in alpha:
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

class PopupStyle(GObject.GObject):
    __gsignals__ = {"popup-style-reloaded": (GObject.SignalFlags.RUN_FIRST,
                                             None,()),}

    def __new__(cls, *p, **k):
        if not "_the_instance" in cls.__dict__:
            cls._the_instance = GObject.GObject.__new__(cls)
        return cls._the_instance

    def __init__(self):
        if "is_initiated" in self.__dict__:
            # This is not the first instance of PopupStyle,
            # no need to initiate anything
            return
        self.is_initiated = True
        GObject.GObject.__init__(self)
        self.globals = Globals()
        self.name = "DBX"
        self.settings = {}
        self.globals.connect("popup-style-changed", self.on_style_changed)
        self.on_style_changed()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def find_styles(self):
        # Reads the styles from APP_DIRS/themes/popup_styles
        # and returns a dict of the style file names and paths so that a
        # style can be loaded
        styles = {}
        app_dirs = get_app_dirs()
        dirs = [os.path.join(d, "themes", "popup_styles") for d in app_dirs]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == ".tar.gz":
                        styles[f] = dir+"/"+f
        return styles

    def on_style_changed(self, arg=None):
        styles = self.find_styles()
        if self.globals.popup_style_file in styles:
            self.style_path = styles[self.globals.popup_style_file]
        elif self.globals.default_popup_style in styles:
            self.style_path = styles[self.globals.default_popup_style]
        else:
            self.style_path = styles.get("dbx.tar.gz", "dbx.tar.gz")
        self.reload()

    def reload(self):
        if self.style_path is None:
            return
        # Default settings
        self.bg = None
        self.cb_pressed_pic = None
        self.cb_hover_pic = None
        self.cb_normal_pic = None
        self.settings = {"border_color2": "#000000",
                         "menu_item_lr_padding": 3}
        self.name = "DBX"
        try:
            tar = taropen(self.style_path)
        except:
            logger.debug("Error opening style %s" % self.style_path)
            self.globals.set_popup_style("dbx.tar.gz")
            self.emit("popup-style-reloaded")
            return
        # Load settings
        try:
            config = tar.extractfile("style")
        except:
            logger.exception("Error extracting style from %s" % \
                             self.style_path)
            tar.close()
            self.globals.set_popup_style("dbx.tar.gz")
            self.emit("popup-style-reloaded")
            return
        self.settings = {}
        for line in config.readlines():
            line = line.decode('utf-8')
            # Split at "=" and clean up the key and value
            if not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip().lower()
            value = value.strip().lstrip()
            # Remove comments
            if "#" in key:
                continue
            # If there is a trailing comment, remove it
            # But avoid removing # if it's in a quote
            sharp = value.find("#")
            if sharp != -1 and value.count("\"", 0, sharp) % 2 == 0 and \
               value.count("'", 0, sharp) % 2 == 0:
                   value = value.split("#", 1)[0].strip()
            # Remove quote signs
            if value[0] in ("\"", "'") and value[-1] in ("\"", "'"):
                value = value[1:-1]
            
            if key == "name":
                name = value
                continue
            value = value.lower()
            self.settings[key] = value
        config.close()
        if name:
            self.name = name
        else:
            self.settings = {"border_color2": "#000000",
                             "menu_item_lr_padding": 3}
            self.globals.set_popup_style("dbx.tar.gz")
            self.emit("popup-style-reloaded")
            tar.close()
            return
        # Load background
        if "background.png" in tar.getnames():
            bgf = tar.extractfile("background.png")
            self.bg = cairo.ImageSurface.create_from_png(bgf)
            bgf.close()
        if "closebutton/normal.png" in tar.getnames():
            cbf = tar.extractfile("closebutton/normal.png")
            self.cb_normal_pic = cairo.ImageSurface.create_from_png(cbf)
            cbf.close()
        if "closebutton/pressed.png" in tar.getnames():
            cbf = tar.extractfile("closebutton/pressed.png")
            self.cb_pressed_pic = cairo.ImageSurface.create_from_png(cbf)
            cbf.close()
        if "closebutton/hover.png" in tar.getnames():
            cbf = tar.extractfile("closebutton/hover.png")
            self.cb_hover_pic = cairo.ImageSurface.create_from_png(cbf)
            cbf.close()
        tar.close()

        # Inform rest of dockbar about the reload.
        self.globals.set_popup_style(self.style_path.rsplit("/", 1)[-1])
        self.emit("popup-style-reloaded")

    def get_styles(self, theme_name=None):
        # For DockbarX preference. This function makes a dict of the names and
        # file names of the styles for all styles that can be opened correctly.
        styles = {}
        app_dirs = get_app_dirs()
        dirs = [os.path.join(d, "themes", "popup_styles") for d in app_dirs]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == ".tar.gz":
                        name, oft = self.check(dir+"/"+f)
                        if oft:
                            # The style is meant only for themes
                            # mentioned in oft.
                            if theme_name is None:
                                continue
                            oft = [t.strip().lstrip().lower() \
                                   for t in oft.split(",")]
                            if not theme_name.lower() in oft:
                                continue
                        if name:
                            styles[name] = f
        # The default style (if the theme doesn't set another one) is DBX,
        # whether or not the file actually exists.
        if not "DBX" in styles:
            styles["DBX"] = "dbx.tar.gz"
        return styles

    def check(self, style_path):
        try:
            tar = taropen(style_path)
        except:
            return None
        try:
            config = tar.extractfile("style")
        except:
            tar.close()
            return None
        name = None
        oft = None
        for line in config.readlines():
            line = line.decode('utf-8')
            # Split at "=" and clean up the key and value
            if not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip().lower()
            value = value.strip().lstrip()
            # Remove comments
            if "#" in key:
                continue
            # If there is a trailing comment, remove it
            # But avoid removing # if it's in a quote
            sharp = value.find("#")
            if sharp != -1 and value.count("\"", 0, sharp) % 2 == 0 and \
               value.count("'", 0, sharp) % 2 == 0:
                   value = value.split("#", 1)[0].strip()
            # Remove quote signs
            if value[0] in ("\"", "'") and value[-1] in ("\"", "'"):
                value = value[1:-1]
            if key == "only_for_themes":
                oft = value
            if key == "name":
                name = value
        tar.close()
        return name, oft

class DockTheme(GObject.GObject):
    __gsignals__ = {"dock-theme-reloaded": (GObject.SignalFlags.RUN_FIRST,
                                             None,()),}

    def __init__(self):
        GObject.GObject.__init__(self)
        self.globals = Globals()
        self.name = "DBX"
        self.settings = {}
        self.globals.connect("dock-theme-changed", self.on_theme_changed)
        self.on_theme_changed()

    def get(self, key, default=None):
        return self.settings.get(key, default)


    def get_bg(self, bar, size=None):
        if size is None:
            return self.bg[bar]
        if size != self.bg_sizes[bar]:
            bg = self.bg[bar]
            w = bg.get_width()
            self.resized_bg[bar] = self.__resize_surface(bg, w, size)
            self.bg_sizes[bar] = size
        return self.resized_bg[bar]

    def find_themes(self):
        # Reads the themes from APP_DIRS/themes/dock
        # and returns a dict of the theme names and paths so
        # that a theme can be loaded.
        themes = {}
        app_dirs = get_app_dirs()
        dirs = [os.path.join(d, "themes", "dock") for d in app_dirs]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == ".tar.gz":
                        themes[f] = dir+"/"+f
        return themes

    def on_theme_changed(self, arg=None):
        themes = self.find_themes()
        if self.globals.settings["dock/theme_file"] in themes:
            self.theme_path = themes[self.globals.settings["dock/theme_file"]]
        else:
            self.theme_path = themes.get("dbx.tar.gz", "dbx.tar.gz")
        self.reload()

    def reload(self):
        if self.theme_path is None:
            return
        self.default_colors = {"bg_color": "#111111", "bg_alpha": 127,
                               "bar2_bg_color":"#111111", "bar2_bg_alpha": 127}
        try:
            tar = taropen(self.theme_path)
        except:
            logger.debug("Error opening dock theme %s" % self.theme_path)
            self.settings = {}
            self.name = "DBX"
            self.bg = {1: None, 2:None}
            self.bg_sizes = {1: -1, 2:-1}
            self.globals.set_dock_theme("dbx.tar.gz", self.default_colors)
            self.emit("dock-theme-reloaded")
            return
        # Load settings
        try:
            config = tar.extractfile("theme")
        except:
            logger.exception("Error extracting theme from %s" % \
                             self.theme_path)
            tar.close()
            self.settings = {}
            self.name = "DBX"
            self.bg = None
            self.globals.set_dock_theme("dbx.tar.gz", self.default_colors)
            self.emit("dock-theme-reloaded")
            return
        old_settings = self.settings
        self.settings = {}
        name = None
        for line in config.readlines():
            line = line.decode('utf-8')
            # Split at "=" and clean up the key and value
            if not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip().lower()
            value = value.strip().lstrip()
            # Remove comments
            if "#" in key:
                continue
            # If there is a trailing comment, remove it
            # But avoid removing # if it's in a quote
            sharp = value.find("#")
            if sharp != -1 and value.count("\"", 0, sharp) % 2 == 0 and \
               value.count("'", 0, sharp) % 2 == 0:
                   value = value.split("#", 1)[0].strip()
            # Remove quote signs
            if value[0] in ("\"", "'") and value[-1] in ("\"", "'"):
                value = value[1:-1]

            if key == "name":
                name = value
                continue
            value = value.lower()
            self.settings[key] = value
        config.close()
        if name:
            self.name = name
        else:
            # Todo: Error handling here!
            self.settings = old_settings
            tar.close()
            self.globals.set_dock_theme("dbx.tar.gz", self.default_colors)
            self.emit("dock-theme-reloaded")
            return
        # Load background
        self.bg = {1:None, 2:None}
        self.bg_sizes = {1: -1, 2: -1}
        self.resized_bg = {}
        if "background.png" in tar.getnames():
            bgf = tar.extractfile("background.png")
            self.bg[1] = cairo.ImageSurface.create_from_png(bgf)
            bgf.close()
        if "bar2_background.png" in tar.getnames():
            bgf = tar.extractfile("bar2_background.png")
            self.bg[2] = cairo.ImageSurface.create_from_png(bgf)
            bgf.close()
        tar.close()

        for key in list(self.default_colors.keys()):
            if key in self.settings:
                value = self.settings.pop(key)
                if "alpha" in key:
                    value = int(round(int(value))*2.55)
                elif value[0] != "#":
                        value = "#%s" % value
                self.default_colors[key] = value

        # Inform rest of dockbar about the reload.
        self.globals.set_dock_theme(self.theme_path.rsplit("/", 1)[-1],
                                    self.default_colors)
        self.emit("dock-theme-reloaded")

    def get_themes(self):
        # For DockbarX preference. This function makes a dict of the names and
        # file names of the themes for all themes that can be opened correctly.
        themes = {}
        app_dirs = get_app_dirs()
        dirs = [os.path.join(d, "themes", "dock") for d in app_dirs]
        for dir in dirs:
            if os.path.exists(dir) and os.path.isdir(dir):
                for f in os.listdir(dir):
                    if f[-7:] == ".tar.gz":
                        name = self.check(dir+"/"+f)
                        if name:
                            themes[name] = f
        # The default theme (if the theme doesn't set another one) is DBX,
        # whether or not the file actually exists.
        if not "DBX" in themes:
            themes["DBX"] = "dbx.tar.gz"
        return themes

    def check(self, theme_path):
        try:
            tar = taropen(theme_path)
        except:
            return None
        try:
            config = tar.extractfile("theme")
        except:
            tar.close()
            return None
        name = None
        for line in config.readlines():
            line = line.decode('utf-8')
            # Split at "=" and clean up the key and value
            if not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip().lower()
            value = value.strip().lstrip()
            # Remove comments
            if "#" in key:
                continue
            # If there is a trailing comment, remove it
            # But avoid removing # if it's in a quote
            sharp = value.find("#")
            if sharp != -1 and value.count("\"", 0, sharp) % 2 == 0 and \
               value.count("'", 0, sharp) % 2 == 0:
                   value = value.split("#", 1)[0].strip()
            # Remove quote signs
            if value[0] in ("\"", "'") and value[-1] in ("\"", "'"):
                value = value[1:-1]
            if key == "name":
                name = value
                break
        tar.close()
        return name

    def __surface2pil(self, surface):
        w = surface.get_width()
        h = surface.get_height()
        return Image.frombuffer("RGBA", (w, h), surface.get_data(),
                                "raw", "RGBA", 0,1)


    def __pil2surface(self, im):
        """Transform a PIL Image into a Cairo ImageSurface."""

        # This function is only supposed to work with little endinan
        # systems. Could that be a problem ever?
        if im.mode != 'RGBA':
            im = im.convert('RGBA')

        s = im.tobytes('raw', 'BGRA')
        a = array.array('B', s)
        dest = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                  im.size[0], im.size[1])
        ctx = cairo.Context(dest)
        non_premult_src_wo_alpha = cairo.ImageSurface.create_for_data(
            a, cairo.FORMAT_RGB24, im.size[0], im.size[1])
        non_premult_src_alpha = cairo.ImageSurface.create_for_data(
            a, cairo.FORMAT_ARGB32, im.size[0], im.size[1])
        ctx.set_source_surface(non_premult_src_wo_alpha)
        ctx.mask_surface(non_premult_src_alpha)
        return dest

    def __resize_surface(self, surface, w, h):
        im = self.__surface2pil(surface)
        try:
            algo = Image.LANCZOS
        except AttributeError:
            # removed in python-pillow 10.0.0
            algo = Image.ANTIALIAS
        im = im.resize((w, h), algo)
        return self.__pil2surface(im)
