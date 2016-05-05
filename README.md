# DockbarX
### Version 0.92

## About DockbarX
DockBarX is a lightweight taskbar / panel replacement for Linux which works as a stand-alone dock (called DockX), as an an Avant Window Navigator applet, as a Xfce4 panel applet[^1], as a matepanel applet[^2] or as a legacy gnome2 panel applet. DockbarX is a fork of dockbar made by Aleksey Shaferov. DockbarX branch is developed by Matias Särs.

DockbarX is free software and is licensed under GPL3.

## Install in Ubuntu from ppa
To add the main DockBarX PPA and install the application in Ubuntu (and derivatives), use the following commands:

```
sudo add-apt-repository ppa:dockbar-main/ppa
sudo apt-get update
sudo apt-get install dockbarx
```

If you want to use dockbarx as a Xfce panel applet you also need this command

```
sudo apt-get install xfce4-dockbarx-plugin
```

To get more themes for DockbarX and DockX use this command

```
sudo apt-get install dockbarx-themes-extra
```

## Install in archlinux
There is an aur for DockbarX

https://aur.archlinux.org/packages/dockbarx/

And there is also one for xfce4-dockbarx-plugin

https://aur.archlinux.org/packages/xfce4-dockbarx-plugin/

## Manual Installation

1. Following dependecies needs to be installed: 
  - zeitgeist, python-wnck, python-imaging, python-keybinder and python-xlib. 
  - Install python-gnomeapplet if you want to use DockbarX as a gnome-panel applet (gnome2) you should install python-gnomeapplet. (This doesn't work in newer releases of Ubuntu.)
  - To use dockbarx as an AWN applet, you also need to copy the content of the AWN folder to ~/.config/awn/applets.
  - Some of the stand alone dock applets require dependencies:
    - Cardapio applet: Cardapio
    - Appindicators: indicator-application
  - To use DockManager helpers, you need to install dockmanager and dockmanager-daemon as well as libdesktop-agnostic-cfg-gconf and libdesktop-agnostic-vfs-gio. The last two might not need to be installed separately on distributions that aren't Debian based.
2. Extract dockbarx. Change directory to where you extracted dockbarx and run the setup.py install `$ sudo ./setup.py install`

## Usage
To start DockbarX you can
  - To run DockbarX as a stand alone dock use the command `dockx`.
  - For gnomepanel or matepanel applet, simply add DockBarX applet to the panel (kill the panel or re-login first if necessary).
  - For XFCE panel you need to [xfce-dockbarx-plugin] (https://github.com/TiZ-EX1/xfce4-dockbarx-plugin), if you haven't installed it already. Click the link for further usage information.

The preferences dialog of DockbarX can be found from your applications menu or (if you use DockX or mate-/xfce-/gnome-applet) by right clicking and choosing Preferences.

**NOTE!** To use previews with Compiz you need to activate KDE Compability in compiz settings manager and under KDE Compability check "Support Plasma Thumbnails". *You can **not** use previews with other window manager than Compiz and Kwin.*

## Contribute
DockbarX is a free and open source project I am developing in my free time. I will gladly accept any help I can get to improve DockbarX. Test out new code, **report bugs** to the issue tracker and make pull request with code you like to contribute.

You can also translate DockbarX into your language at [DockbarX launchpad translation page](https://translations.launchpad.net/dockbar). DockbarX is translated into many languages but few of the translations are complete. Even if DockbarX should be fully translated into your language at the moment, you could check in after a new release is out to see if there some new words that needs translating.

##FAQ
*Q: Why do you want to make Linux into a Microsoft Windows 7 clone?*

A: I don't. The goal of DockbarX isn't to be a clone of the Windows 7 task bar. Windows 7 task bar has a good principle, though.  When it comes to your most used programs it's more productive to do all window handling - launching, selecting, closing, etc. from the same few pixels. If I need a Firefox window I move my mouse cursor to the same spot on the screen regardless of which Firefox window I want and or if I even have not opened a Firefox window yet. This behavior is good and it would be stupid not to implement it just because "Windows had it first". Don't reduce your productivity out of stubbornness. When it comes to looks it's up to you to choose a theme that looks like windows 7 or a theme that doesn't look that way.

Here are some historical references about docks:

http://en.wikipedia.org/wiki/Dock_(computing)
http://en.wikipedia.org/wiki/Icon_bar

And another interesting link that has had quite a bit of infuence on my work with DockbarX:
http://arstechnica.com/software/news/2009/01/dock-and-windows-7-taskbar.ars

*Q: I want a button for every window instead of all windows of the same application grouped together under one button. When will DockbarX support that?*

A: Never. That would demand quite a bit of restructuring of the code and I believe it's less productive to keep the windows ungrouped. You are welcome to change the code yourself if you don't like my decision, or try the applet Talika it might suit your needs better than DockbarX does.

*Q: I added a new launcher for program X but when I click on the launcher a new groupbutton is made for the window instead of using the groupbutton of the launcher. What went wrong?*

A: Dockbarx connects group buttons and windows by using the resource class name of the application. When a launcher is added dockbarx tries to guess the resource class name of that launcher. This works in most cases but not always. Apparently it didn't work for your program X. To fix this, right click on the launcher for program X and choose "Edit Resource name" and enter the correct resource name. If the program is already running you should be able to find it's resource class name in the drop-down list.

*Q: There is no menu option to pin program X, but there is one for program Y and Z. Why?*
A: Dockbarx wasn't able to identify program X correctly then. You can "pin" the program by dragging it's icon from the gnome menu instead. Oh, and you will probably have to enter the resource name manually as well (see previous question). 

*Q: How do I get to preference dialog?*

A: Right click the handle (the dots or lines to the left of dockbarx) to get a menu where you can choose the preference option. Sometimes though, you have to double right click the handle to get the menu. Don't ask me why - just do it. You can also find the preference dialog from gnome menu (in Accessories).

*Q: None of DockbarX's compiz stuff like "compiz scale" work. Why?*

A: Make sure you enable the GLib extension in Compiz settings manager and that the compiz plugin dockbarx uses is activated as well. (eg. for group button action "compiz scale" to work you need the scale plugin activated)

*Q: Opacify doen't work?*

A: A common misunderstanding is that opacify should have something to do with transparency of dockbarx itself, it doesn't. Opacify is a way to find localize a window with dockbar. When opacify is on and you roll over a name in the window list with the mouse, all other windows will become transparent so that you easy can spot the window. 

*Q: How do I install a theme?*

A: If you find a theme on the web that you like, copy the file (should be SOMETHING.tar.gz) to ~/.dockbarx/themes or /usr/share/dockbarx/themes. You change themes in the appearance tab of preference dialog. You might need to press the reload button before your newly installed theme shows up.

*Q: How can I make an theme of my own?*

A: Read Theming HOWTO. If you need help ask me (Matias Särs alias M7S) on gnome-look or at launchpad. I'm happy to help theme developers as much as I can.

### AWN questions
*Q: When I use dockbarx in AWN, IntelliHide and Window Dodge behaviors doesn't work. Why? Can I do anything about it?*

A: For IntelliHide and Window Dodge to work, AWN Taskmanager applet has to be activated. So to get back IntelliHide or Window Dodge, simply add Taskmanager to your applet list again. If you think using Taskmanager and DockbarX at the same time looks a bit weird, you can go to the Task Manager tab of AWN preference and check the option "Display launchers only" and then remove all the launchers in the list. That will give you a completely invisible Taskmanager that will make sure IntelliHide and Window Dodge works as they should. 

[^1]: Using [xfce-dockbarx-plugin] (https://github.com/TiZ-EX1/xfce4-dockbarx-plugin)

[^2]: DockbarX doesn't work in mate 1.6 and later at the moment.




