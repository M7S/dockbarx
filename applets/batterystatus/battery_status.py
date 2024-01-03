#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


license = """Licensed under the GNU General Public License Version 3

Battery Status is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

Battery Status is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301, USA.
"""

name = "battery-status"
comment = "Battery Status applet for DockbarX"
copyright = "Copyright © 2010 Ivan Zorin, 2014 Matias Sars, 2020 Xu Zhen"
authors = ["Ivan Zorin <ivan.a.zorin@gmail.com>", "Matias Sars https://github.com/M7S", "Xu Zhen https://github.com/xuzhen" ]
version = "0.2.0"


import os
import sys
import time
import subprocess
import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib
gi.require_version("Pango", "1.0")
from gi.repository import Pango
import dbus
import pyudev   # >= 0.15
from xml.etree import ElementTree
from dockbarx.applets import DockXApplet, DockXAppletDialog
import dockbarx.i18n
_ = dockbarx.i18n.language.gettext

def _run(program, *args, nowait=False):
    try:

        if not nowait:
            if sys.version_info.minor >= 5:
                return subprocess.run([program, *args],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
            else:   # 3.3+
                return subprocess.call([program, *args],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([program, *args], shell=False,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, close_fds=True)
            return 0
    except:
        return -1

def _set_margin(widget, top=-1, bottom=-1, left=-1, right=-1):
    if top >= 0:
        widget.set_margin_top(top)
    if bottom >= 0:
        widget.set_margin_bottom(bottom)
    if left >= 0:
        widget.set_margin_start(left)
    if right >= 0:
        widget.set_margin_end(right)

def _split_time(time, nosec=True):
    seconds = time % 60
    time = time // 60
    minutes = time % 60
    hours = time // 60
    if nosec:
        return (hours, minutes)
    else:
        return (hours, minutes, seconds)


class CpufreqUtils():
    HELPER_SCRIPT=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               "battery_status_helper.sh")
    def get_cpus(self):
        try:
            cpus = []
            pattern = re.compile("^cpu[0-9]+$")
            files = os.listdir(path="/sys/devices/system/cpu")
            for f in files:
                if os.path.isdir("/sys/devices/system/cpu/%s" % f) and pattern.match(f):
                    cpus.append(int(f.replace("cpu", "")))
            cpus.sort()
            return cpus
        except:
            return []

    def get_governor(sel, cpu = 0):
        try:
            f = open('/sys/devices/system/cpu/cpu%d/cpufreq/scaling_governor' % cpu, 'r')
            governor = f.read().rstrip('\n')
            f.close()
            return governor
        except:
            return None

    def set_governor(self, governor):
        if not governor:
            return False
        if _run("sudo", "-n", self.HELPER_SCRIPT, governor) == 0:
            return True
        return False

    def get_all_governors(self):
        try:
            f = open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors', 'r')
            governors = f.read().rstrip('\n').split(' ')
            f.close()
            if governors[-1] == "":
                return governors[:-1]
            return governors
        except:
            return []

    def can_write(self):
        if _run("sudo", "-n", self.HELPER_SCRIPT) == 0:
            return True
        return False


class PowerSupplyUtils(GObject.GObject):
    SYSFS_MAP = {
        "type": {"": _("N/A"), "Mains": _("Line Power"), "Battery": _("Battery"), "UPS": _("UPS")},
        "tech": {"": _("N/A"), "Unknown": _("Unknown"), "Li-ion": _("Lithium Ion"), "Li-poly": _("Lithium Polymer"), "LiFe": _("Lithium Iron Phosphate"), "NiCd": _("Nickel Cadmium"), "NiMH": _("Nickel Metal Hydride")},
        "status": {"": _("N/A"), "Unknown": _("Unknown"), "Charging": _("Charging"), "Discharging": _("Discharging"), "Not charging": _("Not Charging"), "Full": _("Fully Charged") },
        "health": {"": None, "Unknown": _("Unknown"), "Good": _("Good"), "Overheat": _("Overheat"), "Dead": _("Dead"), "Over voltage": _("Over Voltage"), "Unspecified failure": _("Unspecified Failure"), "Cold": _("Cold"), "Watchdog timer expire": _("Watchdog Timer Expire"), "Safety timer expire": _("Safety Timer Expire") },
        "level": {"": None, "Unknown": _("Unknown"), "Critical": _("Critical"), "Low": _("Low"), "Normal": _("Normal"), "High": _("High"), "Full": _("Full") }
    }
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.__details = None
        self.__summary = None
        self.__poll_sid = None
        self.__update_supplay_devices(False)

        # get device changed notifications from udev
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='power_supply')
        observer = pyudev.MonitorObserver(monitor, callback=self.__on_device_changed, name='monitor-observer')
        observer.start()

    def get_summary(self, refresh=False):
        if refresh:
            self.__update_supplay_devices()
        return self.__summary

    def get_details(self, refresh=False):
        if refresh:
            self.__update_supplay_devices()
        return self.__details

    def __update_supplay_devices(self, emit_signal=True):
        if self.__poll_sid is not None:
            GLib.source_remove(self.__poll_sid)
            self.__poll_sid = None

        devices_info = []
        for device_path in os.listdir(path="/sys/class/power_supply"):
            devtype = self.__read_sysfs(device_path, "type")
            if devtype != "Mains" and devtype != "Battery":
                # Only Power line and Battery. No UPS to test, ignore too
                # Note: may also be deprecated USB_DCP, USB_CDP, USB_ACA, ...
                continue
            info = {
                "name": device_path,
                "vendor": self.__read_sysfs(device_path, "manufacturer"),
                "model": self.__read_sysfs(device_path, "model_name"),
                "serial": self.__read_sysfs(device_path, "serial_number"),
                "type": self.__map_value(devtype, self.SYSFS_MAP["type"])
            }
            if devtype == "Mains": # Line Power
                info["online"] = self.__str_to_bool(self.__read_sysfs(device_path, "online"))
                info["icon"] = "ac-adapter-symbolic"
            elif devtype == "Battery": # Battery
                status = self.__read_sysfs(device_path, "status")
                info.update({
                    "present": self.__str_to_bool(self.__read_sysfs(device_path, "present")),
                    "technology": self.__map_value(self.__read_sysfs(device_path, "technology"), self.SYSFS_MAP["tech"]),
                    "health": self.__map_value(self.__read_sysfs(device_path, "health"), self.SYSFS_MAP["health"]),
                    "temperature": self.__str_to_float(self.__read_sysfs(device_path, "temp")), # 1/10 Degrees Celsius
                    "cycle": self.__str_to_int(self.__read_sysfs(device_path, "cycle_count")),
                    "status": {
                        "charging": status == "Charging",
                        "discharging": status == "Discharging",
                        "text": self.__map_value(status, self.SYSFS_MAP["status"])
                    },
                    "capacity": {
                        "value": self.__str_to_int(self.__read_sysfs(device_path, "capacity")), # percent
                        "level": self.__map_value(self.__read_sysfs(device_path, "capacity_level"), self.SYSFS_MAP["level"])
                    },
                    "energy": { # uWh
                        "now": self.__str_to_int(self.__read_sysfs(device_path, "energy_now")),
                        "avg": self.__str_to_int(self.__read_sysfs(device_path, "energy_avg")),
                        "full": self.__str_to_int(self.__read_sysfs(device_path, "energy_full")),
                        "empty": self.__str_to_int(self.__read_sysfs(device_path, "energy_empty")),
                        "full_design": self.__str_to_int(self.__read_sysfs(device_path, "energy_full_design")),
                        "empty_design": self.__str_to_int(self.__read_sysfs(device_path, "energy_empty_design"))
                    },
                    "power": {  # uW
                        "now": self.__str_to_int(self.__read_sysfs(device_path, "power_now", "current_now")),
                        "avg": self.__str_to_int(self.__read_sysfs(device_path, "power_avg"))
                    },
                    "charge": { # percent
                        "now": self.__str_to_int(self.__read_sysfs(device_path, "charge_now")),
                        "avg": self.__str_to_int(self.__read_sysfs(device_path, "charge_avg")),
                        "full": self.__str_to_int(self.__read_sysfs(device_path, "charge_full")),
                        "empty": self.__str_to_int(self.__read_sysfs(device_path, "charge_empty")),
                        "full_design": self.__str_to_int(self.__read_sysfs(device_path, "charge_full_design")),
                        "empty_design": self.__str_to_int(self.__read_sysfs(device_path, "charge_empty_design"))
                    },
                    "voltage": { # uV
                        "now": self.__str_to_float(self.__read_sysfs(device_path, "voltage_now")),
                        "min": self.__str_to_float(self.__read_sysfs(device_path, "voltage_min_design")),
                    },
                    "time": { # second
                        "to_empty": self.__str_to_int(self.__read_sysfs(device_path, "time_to_empty_now", "time_to_empty_avg")),
                        "to_full": self.__str_to_int(self.__read_sysfs(device_path, "time_to_full_now", "time_to_full_avg"))
                    }
                })

                # convert to standard unit
                if info["temperature"] is not None:
                    info["temperature"] /= 10
                energy = info["energy"]
                for t in energy:
                    if energy[t] is not None:
                        energy[t] /= 1e6
                power = info["power"]
                for t in power:
                    if power[t] is not None:
                        power[t] /= 1e6
                voltage = info["voltage"]
                for t in voltage:
                    if voltage[t] is not None:
                        voltage[t] /= 1e6
                capacity = info["capacity"]

                # try to fix invalid values
                if capacity["value"] is None:
                    if energy["now"] is not None:
                        empty = energy["empty"] or energy["energy_empty_design"] or 0
                        full = energy["full"] or energy["energy_full_design"] or 0
                        try:
                            capacity["value"] = round(float(energy["now"]-empty)/(full-empty)*100)
                        except (TypeError, ZeroDivisionError):
                            pass
                    else:
                        capacity["value"] = charge["now"]
                    if capacity["value"] is None:
                        capacity["value"] = 0
                if energy["now"] is not None and power["now"] is not None:
                    if info["status"]["discharging"] and info["time"]["to_empty"] is None:
                        try:
                            time = round(energy["now"] / power["now"] * 3600)
                            info["time"]["to_empty"] = time
                        except ZeroDivisionError:
                            pass
                    elif info["status"]["charging"] and info["time"]["to_full"] is None and energy["full"] is not None:
                        try:
                            time = round((energy["full"] - energy["now"]) / power["now"] * 3600)
                            info["time"]["to_full"] = time
                        except ZeroDivisionError:
                            pass
            devices_info.append(info)
        self.__details = sorted(devices_info, key=lambda x:x["name"])

        if len(self.__details) == 0:
            summary = { "ac": True, "name": None, "on": True, "icon": "ac-adapter-symbolic" }
            poll_time = 0
        else:
            summary = []
            poll_time = None
            for dev in self.__details:
                if "online" in dev:
                    if dev["online"]:
                        poll_time = 120
                    summary.append({ "ac": True, "name": dev["name"], "on": dev["online"], "icon": "ac-adapter-symbolic" })
                else:
                    status = dev["status"]
                    if status["charging"]:
                        time = dev["time"]["to_full"]
                    elif status["discharging"]:
                        time = dev["time"]["to_empty"]
                    else:
                        time = None
                    if poll_time is None:
                        if dev["capacity"]["value"] < 10:
                            poll_time = 10
                        else:
                            poll_time = 30
                    summary.append({ "ac": False, "name": dev["name"], "on": dev["present"], "icon": self.__get_battery_icon(dev),
                                     "capacity": dev["capacity"]["value"], "time": time, "before_empty": dev["time"]["to_empty"],
                                     "charging": dev["status"]["charging"], "status":dev["status"]["text"] })

        if poll_time > 0:
            self.__poll_sid = GLib.timeout_add_seconds(poll_time, self.__poll)

        if self.__summary != summary:
            self.__summary = summary
            if emit_signal:
                self.emit("changed")

    def __on_device_changed(self, device):
        self.__update_supplay_devices()

    def __poll(self):
        self.__poll_sid = None
        self.__update_supplay_devices()
        return False

    def __get_battery_icon(self, info):
        if not info["present"]:
            return "battery-missing-symbolic"
        status = info["status"]
        if status == "Full":
            return "battery-full-charged-symbolic"
        energy = info["energy"]
        if energy["now"] is not None and energy["now"] <= (energy["empty"] or energy["empty_design"] or 0):
            return "battery-empty-symbolic"
        capacity = info["capacity"]
        if capacity["value"] == 0:
            return "battery-empty-symbolic"

        if status == "Charging":
            icon_charging_text = "-charging"
        else:
            icon_charging_text = ""
        if capacity["value"] < 10:
            icon_status_text = "caution"
        elif capacity["value"] < 30:
            icon_status_text = "low"
        elif capacity["value"] < 60:
            icon_status_text = "good"
        else:
            icon_status_text = "full"
        return "battery-%s%s-symbolic" % (icon_status_text, icon_charging_text)


    def __read_sysfs(self, devname, filename, fallback_filename="", fallback_value=""):
        try:
            f = open('/sys/class/power_supply/%s/%s' % (devname, filename), 'r')
            data = f.read().rstrip('\n')
            f.close()
            return data
        except:
            pass
        if fallback_filename == "":
            return fallback_value
        try:
            f = open('/sys/class/power_supply/%s/%s' % (devname, fallback_filename), 'r')
            data = f.read().rstrip('\n')
            f.close()
            return data
        except:
            return fallback_value

    def __str_to_bool(self, data):
        return self.__str_to_int(data) != 0

    def __str_to_int(self, data, fallback = None):
        try:
            return int(data)
        except ValueError:
            return fallback
    
    def __str_to_float(self, data, fallback = None):
        try:
            return float(data)
        except ValueError:
            return fallback

    def __map_value(self, key, mapping, fallback_key=""):
        try:
            return mapping[key]
        except KeyError:
            return mapping[fallback_key]


class SystemdUtils(GObject.GObject):
    BUS_NAME = "org.freedesktop.login1"
    LOGIN_PATH = "/org/freedesktop/login1"
    LOGIN_IFNAME = "org.freedesktop.login1.Manager"
    SESSION_ROOT_PATH = "/org/freedesktop/login1/session"
    SESSION_PATH_NEW = "/org/freedesktop/login1/session/auto"
    SESSION_PATH_OLD = "/org/freedesktop/login1/session/self"
    SESSION_IFNAME = "org.freedesktop.login1.Session"
    INTROSPECTABLE_IFNAME = "org.freedesktop.DBus.Introspectable"

    __gsignals__ = {
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.__login_iface = None
        try:
            self.__bus = dbus.SystemBus()
            login_object = self.__bus.get_object(self.BUS_NAME, self.LOGIN_PATH)
            self.__login_iface = dbus.Interface(login_object, self.LOGIN_IFNAME)
        except dbus.exceptions.DBusException as exception:
            self.emit("error", exception.__str__())

        self.__session_iface = None
        try:
            if self.__bus is not None:
                use_old_path = True
                session_object = self.__bus.get_object(self.BUS_NAME, self.SESSION_ROOT_PATH)
                iface = dbus.Interface(session_object, self.INTROSPECTABLE_IFNAME)
                xml_string = iface.Introspect()
                for child in ElementTree.fromstring(xml_string):
                    if child.tag != "node":
                        continue
                    child_path = "/".join((self.SESSION_ROOT_PATH, child.attrib["name"]))
                    if child_path == self.SESSION_PATH_NEW:
                        use_old_path = False
                        break
                session_object = self.__bus.get_object(self.BUS_NAME, self.SESSION_PATH_OLD if use_old_path else self.SESSION_PATH_NEW)
                self.__session_iface = dbus.Interface(session_object, self.SESSION_IFNAME)
        except dbus.exceptions.DBusException as exception:
            self.emit("error", exception.__str__())


    def logout(self):
        if self.can_logout():
            try:
                self.__session_iface.Terminate()
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def reboot(self, interactive = True):
        if self.can_reboot():
            try:
                self.__login_iface.Reboot(interactive)
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def poweroff(self, interactive = True):
        if self.can_poweroff():
            try:
                self.__login_iface.PowerOff(interactive)
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def hybrid_sleep(self, interactive = True):
        if self.can_hybrid_sleep():
            try:
                self.__login_iface.HybridSleep(interactive)
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def hibernate(self, interactive = True):
        if self.can_hibernate():
            try:
                self.__login_iface.Hibernate(interactive)
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def suspend(self, interactive = True):
        if self.can_suspend():
            try:
                self.__login_iface.Suspend(interactive)
                return True
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def can_logout(self):
        return self.__session_iface is not None

    def can_reboot(self):
        if self.__login_iface is not None:
            try:
                return self.__login_iface.CanReboot() == "yes"
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def can_poweroff(self):
        if self.__login_iface is not None:
            try:
                return self.__login_iface.CanPowerOff() == "yes"
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def can_hybrid_sleep(self):
        if self.__login_iface is not None:
            try:
                return self.__login_iface.CanHybridSleep() == "yes"
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def can_hibernate(self):
        if self.__login_iface is not None:
            try:
                return self.__login_iface.CanHibernate() == "yes"
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False

    def can_suspend(self):
        if self.__login_iface is not None:
            try:
                return self.__login_iface.CanSuspend() == "yes"
            except dbus.exceptions.DBusException as exception:
                self.emit("error", exception.__str__())
        return False


class PowerDevicesDialog(Gtk.Dialog):
    def __init__(self, details):
        Gtk.Dialog.__init__(self)
        self.set_title(_("Power Supply Devices"))
        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)
        box = self.get_child()
        box.add(self.notebook)
        self.__setup_pages(details)

    def __setup_pages(self, details):
        for dev in details:
            label = Gtk.Label.new(dev["name"])
            table = Gtk.Grid()
            table.set_column_spacing(5)
            table.set_row_spacing(5)
            table.set_vexpand(True)
            _set_margin(table, left=5, right=5, bottom=5)
            self.notebook.append_page(table, label)
            row = 0
            
            row += self.__add_row(table,     row, _("Type:"),                 dev["type"])
            if "online" in dev:
                row += self.__add_row(table, row, _("Status:"),               self.__b2s(dev["online"], _("Online"), _("Offline")))
                continue
            present = dev["present"]
            row += self.__add_row(table,     row, _("Present:"),              self.__b2s(present, _("Yes"), _("No")))
            row += self.__add_row(table,     row, _("Vendor:"),               dev["vendor"], skip_invalid=False)
            row += self.__add_row(table,     row, _("Model:"),                dev["model"], skip_invalid=False)
            row += self.__add_row(table,     row, _("Serial:"),               dev["serial"], skip_invalid=False)

            row += self.__add_row(table,     row, _("Technology:"),           dev["technology"], skip_invalid=False)
            if not present:
                continue
            row += self.__add_row(table,     row, _("Health:"),               dev["health"])
            status = dev["status"]
            row += self.__add_row(table,     row, _("Status:"),               status["text"])
            row += self.__add_row(table,     row, _("Temperature:"),          dev["temperature"], unit="℃")
            row += self.__add_row(table,     row, _("Cycle Count:"),          dev["cycle"])
            row += self.__add_row(table,     row, _("Capacity:"),             dev["capacity"]["value"], unit="%")
            row += self.__add_row(table,     row, _("Capacity Level:"),       dev["capacity"]["level"]) 
            if status["charging"] and dev["time"]["to_full"] is not None:
                row += self.__add_row(table, row, _("Time to Fully Charged:"), self.__t2s(dev["time"]["to_full"]))
            elif status["discharging"] and dev["time"]["to_empty"] is not None:
                row += self.__add_row(table, row, _("Time To Run Out:"),      self.__t2s(dev["time"]["to_empty"]))
            energy = dev["energy"]
            if energy["now"] is not None:
                row += self.__add_row(table, row, _("Energy:"),               "", group=True)
                row += self.__add_row(table, row, _("Now:"),                  energy["now"], unit=" Wh", margin=20)
                row += self.__add_row(table, row, _("Average:"),              energy["avg"], unit=" Wh", margin=20)
                row += self.__add_row(table, row, _("Full:"),                 energy["full"], unit=" Wh", margin=20)
                row += self.__add_row(table, row, _("Empty:"),                energy["empty"], unit=" Wh", margin=20)
                row += self.__add_row(table, row, _("Design Full:"),          energy["full_design"], unit=" Wh", margin=20)
                row += self.__add_row(table, row, _("Design Empty:"),         energy["empty_design"], unit=" Wh", margin=20)
            charge = dev["charge"]
            if charge["now"] is not None:
                row += self.__add_row(table, row, _("Charge:"),               "", group=True)
                row += self.__add_row(table, row, _("Now:"),                  charge["now"], unit="%", margin=20)
                row += self.__add_row(table, row, _("Average:"),              charge["avg"], unit="%", margin=20)
                row += self.__add_row(table, row, _("Full:"),                 charge["full"], unit="%", margin=20)
                row += self.__add_row(table, row, _("Empty:"),                charge["empty"], unit="%", margin=20)
                row += self.__add_row(table, row, _("Design Full:"),          charge["full_design"], unit="%", margin=20)
                row += self.__add_row(table, row, _("Design Empty:"),         charge["empty_design"], unit="%", margin=20)
            power = dev["power"]
            if power["now"] is not None:
                row += self.__add_row(table, row, _("Power:"),                "", group=True)
                row += self.__add_row(table, row, _("Current:"),              power["now"], unit=" W", margin=20)
                row += self.__add_row(table, row, _("Average:"),              power["avg"], unit=" W", margin=20)
            voltage = dev["voltage"]
            if voltage["now"] is not None:
                row += self.__add_row(table, row, _("Voltage:"),              "", group=True)
                row += self.__add_row(table, row, _("Current:"),              voltage["now"], unit=" V", margin=20)
                row += self.__add_row(table, row, _("Design Minimum:"),       voltage["min"], unit=" V", margin=20)
        self.show_all()

    def set_page(self, pos):
        if type(pos) == int:
            self.notebook.set_current_page(pos)
        elif type(pos) == str:
            n = self.notebook.get_n_pages()
            for i in range(n):
                page = self.notebook.get_nth_page(i)
                if self.notebook.get_tab_label_text(page) == pos:
                    self.notebook.set_current_page(i)
                    return

    def update(self, details):
        n = self.notebook.get_n_pages()
        pos = self.notebook.get_current_page()
        page = self.notebook.get_nth_page(pos)
        name = self.notebook.get_tab_label_text(page);
        for i in range(n):
            self.notebook.remove_page(-1)
        self.__setup_pages(details)
        self.set_page(name)

    def __add_row(self, table, row, name, value, prec=2, unit = "", skip_invalid=True, group=False, margin=0):
        if type(value) == str:
            if group == False and value == "":
                if skip_invalid:
                    return 0
        elif type(value) == float:
            if value < 0 and skip_invalid:
                return 0
            value = str(round(value, prec))
            if unit != "":
                value = value + unit
        elif type(value) == int:
            if value < 0 and skip_invalid:
                return 0
            value = str(value)
            if unit != "":
                value = value + unit
        elif value is None:
            if skip_invalid:
                return 0
            value = _("N/A")
        label = Gtk.Label.new(name)
        label.set_halign(Gtk.Align.START)
        label.set_margin_start(margin)
        table.attach(label, 0, row, 1, 1)
        if not group:
            label = Gtk.Label.new(value)
            label.set_halign(Gtk.Align.END)
            label.set_hexpand(True)
            label.set_selectable(True)
            table.attach(label, 1, row, 1, 1)
        return 1
                
    def __b2s(self, value, str_true, str_false):
        if value:
            return str_true
        else:
            return str_false

    def __t2s(self, value):
        v = _split_time(value)
        t = ""
        if v[0] == 1:
            t = _("1 Hour ")
        elif v[0] > 1:
            t = _("%d Hours ") % v[0]
        if v[1] == 0:
            if v[0] == 0:
                t = _("Less Than 1 Minute")
        elif v[1] == 1:
            t += _("1 Minute")
        elif v[1] > 1:
            t += _("%d Minutes") % v[1]
        return t

class WarningDialog(Gtk.MessageDialog):
    def __init__(self, countdown = 0):
        Gtk.MessageDialog.__init__(self, None, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE,
                _("Please connect your computer to AC power.\nOtherwise all unsaved data will be lost."))

        self.__countdown = countdown
        self.set_keep_above(True)
        self.connect("response", self.__on_response)
        self.__update_countdown()
        self.add_button(_("_Ignore"), 0)
        self.add_button(_("_Sleep Now"), 1)
        self.set_default_response(0)

        GLib.timeout_add_seconds(countdown, self.response, 0)
        GLib.timeout_add_seconds(1, self.__count)

    def __count(self):
        if self.__countdown > 1:
            self.__countdown -= 1
            self.__update_countdown()
            return True
        elif self.__countdown == 0:
            self.response(0)
        return False

    def __update_countdown(self):
        if self.__countdown > 1:
            self.format_secondary_text("Battery will run out in %d seconds." % self.__countdown)
        else:
            self.format_secondary_text("Battery will run out in %d second." % self.__countdown)

    def __on_response(self, *args):
        self.__countdown = -1
        GLib.idle_add(self.destroy)

    def recount(self, count):
        self.__countdown = count
        self.__update_countdown()

class DockXBatteryApplet(DockXApplet):
    """Battery Status applet - shows battery status and battery life/charge time"""

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)
        """Create applet"""
        self.init_settings()
        self.init_utils()
        self.init_widgets()
        self.init_main_menu()
        self.init_extra_menu()
        self.show()
        if self.get_setting("restore_cpu_mode"):
            self.__cpufreq.set_governor(self.get_setting("last_cpu_mode"))
        GLib.idle_add(self.update_status)

    def init_settings(self):
        self.__options = {}
        self.__status_options = [ "label_visibility", "icon_visibility", "use_symbolic_icon", "low_power_action", "low_capacity", "low_time" ]
        self.__font_options = [ "font", "color" ]
        for opt in self.__status_options:
            self.__options[opt] = self.get_setting(opt)
        for opt in self.__font_options:
            self.__options[opt] = self.get_setting(opt)

    def init_utils(self):
        self.__cpufreq = CpufreqUtils()
        self.__powersupply = PowerSupplyUtils()
        self.__powersupply.connect("changed", self.__on_power_supply_changed)
        self.__system = SystemdUtils()
        self.__system.connect("error", self.__on_systemd_error)

    def init_widgets(self):
        """Create widgets for applet"""
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon_theme.connect("changed", self.__on_icon_theme_changed)
        self.icon_pixbufs = {}
        self.menu_icon_pixbufs = {}
        self.icon = Gtk.Image()
        self.label = Gtk.Label(label="")
        self.label.set_use_markup(True)
        self.margin = 3
        if self.get_position() in ("left", "right"):
            self.set_label_rotation(self.get_setting("rotation"))
            self.box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 3)
            _set_margin(self.icon, left=self.margin, right=self.margin)
        else:
            self.box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 3)
            _set_margin(self.icon, top=self.margin, bottom=self.margin)
        self.box.pack_start(self.icon, True, True, 0)
        self.box.pack_start(self.label, False, False, 0)
        self.add(self.box)
        self.connect("clicked", self.__on_self_clicked)
        self.__details_dialog = None
        self.__warning_dialog = None
        self.__warning_ignored = False
        self.update_font()
        self.box.show_all()

    def init_main_menu(self):
        """Create main menu"""
        self.main_menu = Gtk.Menu()

        ### menu items: Device Brief Info
        self.main_menu_item_devices = []

        ### menu item: CPU Modes >
        self.main_menu_item_cpumodes_sep = Gtk.SeparatorMenuItem()
        self.main_menu_item_cpumodes = Gtk.MenuItem.new_with_mnemonic(_("_CPU Modes"))
        submenu = Gtk.Menu()
        self.main_menu_item_cpumodes.set_submenu(submenu)
        self.main_menu.append(self.main_menu_item_cpumodes_sep)
        self.main_menu.append(self.main_menu_item_cpumodes)

        ### menu item: Sleep Actions
        self.main_menu_item_sleep_sep = Gtk.SeparatorMenuItem()
        self.main_menu_item_sleep_suspend = self.__create_text_menuitem(_("_Suspend"), self.__on_main_menuitem_system_action, "suspend")
        self.main_menu_item_sleep_hybrid = self.__create_text_menuitem(_("Hy_brid Sleep"), self.__on_main_menuitem_system_action, "hybrid_sleep")
        self.main_menu_item_sleep_hibernate = self.__create_text_menuitem(_("_Hibernate"), self.__on_main_menuitem_system_action, "hibernate")
        self.main_menu.append(self.main_menu_item_sleep_sep)
        self.main_menu.append(self.main_menu_item_sleep_suspend)
        self.main_menu.append(self.main_menu_item_sleep_hybrid)
        self.main_menu.append(self.main_menu_item_sleep_hibernate)

        ### menu item: Session Actions
        self.main_menu_item_session_sep = Gtk.SeparatorMenuItem()
        self.main_menu_item_session_logout = self.__create_text_menuitem(_("_Log Out"), self.__on_main_menuitem_system_action, "logout")
        self.main_menu_item_session_poweroff = self.__create_text_menuitem(_("Shut _Down"), self.__on_main_menuitem_system_action, "poweroff")
        self.main_menu_item_session_reboot = self.__create_text_menuitem(_("_Reboot"), self.__on_main_menuitem_system_action, "reboot")
        self.main_menu.append(self.main_menu_item_session_sep)
        self.main_menu.append(self.main_menu_item_session_logout)
        self.main_menu.append(self.main_menu_item_session_poweroff)
        self.main_menu.append(self.main_menu_item_session_reboot)

        self.main_menu.show_all()


    def init_extra_menu(self):
        """Create right click menu"""
        self.extra_menu = Gtk.Menu()
        extra_menuitem_prefs = Gtk.MenuItem.new_with_mnemonic(_("_Preferences"))
        extra_menuitem_prefs.connect("activate", self.__on_extra_menuitem_prefs)
        self.extra_menu.append(extra_menuitem_prefs)
        extra_menuitem_about = Gtk.MenuItem.new_with_mnemonic(_("_About"))
        extra_menuitem_about.connect("activate", self.__on_extra_menuitem_about)
        self.extra_menu.append(extra_menuitem_about)
        self.extra_menu.show_all()

    def show_main_menu(self, event):
        """Create main menu"""
        summary = self.__powersupply.get_summary()
        self.update_status(summary)

        # Device Info
        self.__create_device_menuitems(summary)

        # CPU Modes
        if self.get_setting("show_cpu_modes"):
            power_mode = self.__cpufreq.get_governor()
            governors = self.__cpufreq.get_all_governors()
            writeable = self.__cpufreq.can_write()
            submenu = self.main_menu_item_cpumodes.get_submenu()
            for menuitem in submenu.get_children():
                menuitem.destroy()
            group = None
            for g in governors:
                menuitem = self.__create_raido_menuitem(group, g[0].upper() + g[1:], self.__on_main_menuitem_cpu_mode, g)
                menuitem.show()
                if power_mode == menuitem.tag:
                    menuitem.set_active(True)
                if group is None:
                    group = menuitem
                menuitem.set_sensitive(writeable)
                submenu.append(menuitem)
            if len(governors) > 0:
                self.main_menu_item_cpumodes_sep.show()
                self.main_menu_item_cpumodes.show()
            else:
                self.main_menu_item_cpumodes_sep.hide()
                self.main_menu_item_cpumodes.hide()
        else:
            self.main_menu_item_cpumodes_sep.hide()
            self.main_menu_item_cpumodes.hide()

        # Sleep Actions
        if self.get_setting("show_sleep_actions"):
            self.main_menu_item_sleep_sep.show()
            self.main_menu_item_sleep_suspend.show()
            self.main_menu_item_sleep_hybrid.show()
            self.main_menu_item_sleep_hibernate.show()
            self.main_menu_item_sleep_suspend.set_sensitive(self.__system.can_suspend())
            self.main_menu_item_sleep_hybrid.set_visible(self.__system.can_hibernate())
            self.main_menu_item_sleep_hibernate.set_sensitive(self.__system.can_hibernate())
        else:
            self.main_menu_item_sleep_sep.hide()
            self.main_menu_item_sleep_suspend.hide()
            self.main_menu_item_sleep_hybrid.hide()
            self.main_menu_item_sleep_hibernate.hide()

        # Session Actions
        if self.get_setting("show_session_actions"):
            self.main_menu_item_session_sep.show()
            self.main_menu_item_session_logout.show()
            self.main_menu_item_session_reboot.show()
            self.main_menu_item_session_poweroff.show()
            self.main_menu_item_session_logout.set_sensitive(self.__system.can_logout())
            self.main_menu_item_session_reboot.set_sensitive(self.__system.can_reboot())
            self.main_menu_item_session_poweroff.set_sensitive(self.__system.can_poweroff())
        else:
            self.main_menu_item_session_sep.hide()
            self.main_menu_item_session_logout.hide()
            self.main_menu_item_session_reboot.hide()
            self.main_menu_item_session_poweroff.hide()

        self.main_menu.popup_at_pointer(event)
        return

    def show_extra_menu(self, event):
        """Show popup menu"""
        self.extra_menu.popup_at_pointer(event)

    def set_label_rotation(self, rotation):
        angle = { "no": 0, "clockwise": 270, "anticlockwise": 90 }
        self.label.set_angle(angle[rotation])

    def update_font(self):
        color = self.__options["color"]
        font = self.__options["font"]
        if hasattr(Pango, "attr_font_desc_new") and hasattr(Pango, "attr_foreground_new"):
            font_desc = Pango.FontDescription(font)
            #font_desc.set_absolute_size(self.get_size() * Pango.SCALE)
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_font_desc_new(font_desc))
            attrs.insert(Pango.attr_foreground_new(color[0]*65535, color[1]*65535, color[2]*65535))
            attrs.insert(Pango.attr_foreground_alpha_new(color[3]*65535))
            #attrs.insert(Pango.attr_background_new(0, 0, 0))
            self.label.set_attributes(attrs)
        else:
            hex_color = "#%02x%02x%02x" % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            text = GLib.markup_escape_text(self.label.get_text(), -1)
            markup = '<span foreground="%s" font_desc="%s">%s</span>' % (hex_color, font, text)
            self.label.set_markup(markup)

    def update_status(self, devices = None):
        if devices is None:
            devices = self.__powersupply.get_summary()

        not_available = _("N/A")

        if type(devices) == dict:
            icon = devices["icon"]
            tooltip = self.__generate_device_text(devices)
            time = not_available
            charging = False
            capacity = not_available
            self.power_line = True
        else:
            tooltip = ""
            charging = False
            ac_icon = None
            battery_icon = None
            no_battery_icon = None
            time = None
            capacity = -1
            for dev in devices:
                tooltip += self.__generate_device_text(dev) + '\n'
                if dev["ac"]:
                    if dev["on"]:
                        ac_icon = dev["icon"]
                else:
                    if dev["on"]:
                        if dev["capacity"] > capacity:
                            battery_icon = dev["icon"]
                            time = dev["before_empty"]
                            capacity = dev["capacity"]
                        if dev["charging"]:
                            charging = True
                    else:
                        no_battery_icon = dev["icon"]
            if not charging and ac_icon is not None:
                icon = ac_icon
                if battery_icon is None:
                    time = not_available
                    capacity = not_available
            else:
                if battery_icon is None:
                    icon = no_battery_icon
                    time = not_available
                    capacity = not_available
                else:
                    icon = battery_icon
            self.power_line = charging or ac_icon is not None
        tooltip = tooltip.rstrip('\n')

        # set icon
        if self.__options["icon_visibility"] == "always" or \
               (self.__options["icon_visibility"] == "low" and (time != not_available or capacity != not_available) and (capacity == not_available or capacity <= self.__options["low_capacity"]) and (time == not_available or time <= self.__options["low_time"] * 60)) or \
               (self.__options["icon_visibility"] == "charging" and charging):
            if icon not in self.icon_pixbufs:
                self.icon_pixbufs[icon] = self.__load_theme_icon(icon, self.get_size() - self.margin * 2)
            self.icon.set_from_pixbuf(self.icon_pixbufs[icon])
            self.icon.show()
            self.icon.set_tooltip_text(tooltip)
        else:
            self.icon.hide()
        # set label
        if self.__options["label_visibility"] != "never":
            if self.__options["label_visibility"] == "time":
                if time is None:
                    label = _("N/A")
                elif type(time) == str:
                    label = time
                else:
                    label = "%02d:%02d" % _split_time(time)
            else:
                if type(capacity) == str:
                    label = capacity
                else:
                    label = "%d%%" % capacity
            self.label.set_text(label)
            self.label.show()
            self.label.set_tooltip_text(tooltip)
        else:
            self.label.hide()

        if self.power_line:
            if self.__warning_dialog is not None:
                self.__warning_dialog.response(0)
            self.__warning_ignored = False
        elif self.__options["low_power_action"] != "nothing" and \
                not self.power_line and  \
                ((time is not None and time != not_available) or capacity != not_available) and \
                (time is None or time == not_available or time <= self.__options["low_time"] * 60) and \
                (capacity == not_available or capacity <= self.__options["low_capacity"]):
            if self.__options["low_power_action"] == "sleep":
                self.sleep()
            else:
                if time == not_available:
                    time = 0
                if not self.__warning_ignored:
                    GLib.idle_add(self.show_low_power_warning_dialog, time)
        elif self.__warning_dialog is not None:
            self.__warning_dialog.response(0)


    def show_device_details(self, menuitem, index, name):
        """Device information dialog"""
        details = self.__powersupply.get_details()
        if self.__details_dialog is None:
            self.__details_dialog = PowerDevicesDialog(details)
            self.__details_dialog.connect("response", self.__on_dialog_close)
            self.__details_dialog.set_page(index)
            self.__details_dialog.show()
        else:
            self.__details_dialog.update(details)
            self.__details_dialog.set_page(name)
        return

    def sleep(self):
        if self.__system.hybrid_sleep():
            return
        if self.__system.hibernate():
            return
        if self.__system.suspend():
            return
        dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, _("Failed to sleep"))
        dialog.connect("response", lambda dlg, resp: dlg.destroy());
        dialog.run()

    def show_low_power_warning_dialog(self, time):
        if self.__warning_dialog is not None:
            self.__warning_dialog.recount(time)
            return
        self.__warning_dialog = WarningDialog(time)
        ret = self.__warning_dialog.run()
        if ret == 1:
            GLib.idle_add(self.sleep)
        else:
            self.__warning_ignored = True
        self.__warning_dialog = None

    def __on_power_supply_changed(self, source):
        details = self.__powersupply.get_details()
        summary = self.__powersupply.get_summary()
        self.update_status(summary)
        if self.__details_dialog is not None:
            if len(details) == 0:
                self.__details_dialog.response(0)
                self.__details_dialog.destroy()
                self.__details_dialog = None
            else:
                GLib.idle_add(self.__details_dialog.update, details)

    def __on_systemd_error(self, error):
        self.debug(error)

    def __on_dialog_close(self, *args):
        self.__details_dialog.destroy()
        self.__details_dialog = None

    def __on_icon_theme_changed(self, *args):
        self.icon_pixbufs = {}
        self.menu_icon_pixbufs = {}
        self.update_status()

    def __on_self_clicked(self, applet, event):
        button = event.get_button().button
        if button == 1:
            self.show_main_menu(event)
        elif button == 3:
            self.show_extra_menu(event)

    def __on_main_menuitem_cpu_mode(self, item, mode):
        if item.get_active() == False:
            return
        self.set_setting("last_cpu_mode", mode)
        old_mode = self.__cpufreq.get_governor()
        if mode == old_mode:
            return
        if self.__cpufreq.set_governor(mode):
            return
        for menuitem in self.main_menu_item_cpumodes.get_submenu().get_children():
            if old_mode == menuitem.tag:
                menuitem.set_active(True)
                break;

    def __on_main_menuitem_system_action(self, menuitem, action):
        confirm = False
        sleep_actions = ("suspend", "hybrid_sleep", "hibernate")
        if action in sleep_actions:
            if self.get_setting("confirm_sleep"):
                confirm = True
        else:
            if self.get_setting("confirm_session"):
                confirm = True
        if confirm:
            dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                                           Gtk.ButtonsType.YES_NO,
                                           _("Ready to %s?") % menuitem.get_label().replace("_", ""))
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                return
        getattr(self.__system, action)()

    def __on_extra_menuitem_about(self, event):
        """Show information about applet on choosing 'About' in popup menu"""
        About = Gtk.AboutDialog()
        About.set_version(version)
        About.set_name(name)
        About.set_license(license)
        About.set_authors(authors)
        About.set_comments(comment)
        About.set_copyright(copyright)
        About.set_logo_icon_name("dockbarx")
        About.run()
        About.destroy()

    def __on_extra_menuitem_prefs(self, event):
        """Show preferences dialog on choosing 'Preferences' in popup menu"""
        dialog = DockXBatteryPreferences(self.get_id())
        dialog.run()
        dialog.destroy()


    def __load_theme_icon(self, name, size, flags = Gtk.IconLookupFlags.FORCE_SIZE, fallback = "error"):
        if self.__options["use_symbolic_icon"]:
            flags = flags | Gtk.IconLookupFlags.FORCE_SYMBOLIC
            flags = flags & (~Gtk.IconLookupFlags.FORCE_REGULAR)
        else:
            flags = flags | Gtk.IconLookupFlags.FORCE_REGULAR
            flags = flags & (~Gtk.IconLookupFlags.FORCE_SYMBOLIC)
        try:
            pixbuf = self.icon_theme.load_icon(name, size, Gtk.IconLookupFlags(flags))
        except:
            pixbuf = self.icon_theme.load_icon(fallback, size, Gtk.IconLookupFlags(flags))
        if flags & Gtk.IconLookupFlags.FORCE_SIZE:
            pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf

    def __create_raido_menuitem(self, group, text, func, data):
        menuitem = Gtk.RadioMenuItem.new_with_label_from_widget(group, text)
        menuitem.set_use_underline(True)
        menuitem.connect("toggled", func, data)
        menuitem.tag = data
        return menuitem

    def __create_text_menuitem(self, text, func, *args):
        menuitem = Gtk.MenuItem.new_with_mnemonic(text)
        menuitem.connect("activate", func, *args)
        return menuitem

    def __create_device_menuitem(self, device_info, index = 0):
        text = self.__generate_device_text(device_info)
        icon = device_info["icon"]
        if icon not in self.menu_icon_pixbufs:
            self.menu_icon_pixbufs[icon] = self.__load_theme_icon(icon, 24)
        menuitem = Gtk.MenuItem()
        hbox = Gtk.HBox()
        if index >= 0:
            image = Gtk.Image()
            image.set_from_pixbuf(self.menu_icon_pixbufs[icon])
            hbox.pack_start(image, False, False, 0)
        label = Gtk.Label.new(text)
        label.set_xalign(0)
        _set_margin(label, left=3)
        label.set_hexpand(True)
        hbox.pack_start(label, True, True, 0)
        if index >= 0:
            menuitem.connect("activate", self.show_device_details, index, device_info["name"])
        menuitem.add(hbox)
        return menuitem

    def __create_device_menuitems(self, devices_summary):
        while len(self.main_menu_item_devices) > 0:
            self.main_menu_item_devices.pop().destroy()

        if type(devices_summary) == dict:
            menuitem = self.__create_device_menuitem(devices_summary, -1)
            menuitem.set_sensitive(False)
            menuitem.show_all()
            self.main_menu.prepend(menuitem)
            self.main_menu_item_devices.append(menuitem)
        else:
            pos = 0
            for device in devices_summary:
                menuitem = self.__create_device_menuitem(device, pos)
                menuitem.show_all()
                self.main_menu.insert(menuitem, pos)
                self.main_menu_item_devices.append(menuitem)
                pos += 1

    def __generate_device_text(self, device):
        if device["name"] is None:
            return "No Power Supply Devices"
        else:
            if device["ac"]:
                if device["on"]:
                    online_status = "Online"
                else:
                    online_status = "Offline"
                text = "%s: %s" % (device["name"], online_status)
            else:
                if device["on"]:
                    if device["time"] is not None:
                        time = _split_time(device["time"])
                        if device["charging"]:
                            text = _("%s: %s (%d%%, %02d:%02d to full)") % (device["name"], device["status"], device["capacity"], time[0], time[1])
                        else:
                            text = _("%s: %s (%d%%, %02d:%02d to empty)") % (device["name"], device["status"], device["capacity"], time[0], time[1])
                    else:
                        text = _("%s: %s (%d%%)") % (device["name"], device["status"], device["capacity"])
                else:
                    text = _("%s: Not Available") % device["name"]
            return text

    def on_setting_changed(self, key, value):
        if key in self.__status_options or key in self.__font_options:
            self.__options[key] = value

        if key == "use_symbolic_icon":
            self.icon_pixbufs = {}
            self.menu_icon_pixbufs = {}
        elif key == "rotation":
            if self.get_position() in ("left", "right"):
                self.set_label_rotation(value)
        elif key in ("low_power_action", "low_capacity", "low_time"):
            self.__warning_ignored = False

        if key in self.__status_options:
            self.update_status()
        elif key in self.__font_options:
            self.update_font()

    def update(self):
        self.update_font()
        self.__on_icon_theme_changed()


class DockXBatteryPreferences(DockXAppletDialog):
    Title = "Battery Status Applet Preference"
    
    def __init__(self, applet_id):
        DockXAppletDialog.__init__(self, applet_id, title=self.Title)

        frame = Gtk.Frame.new(_("Appearance"))
        frame.set_valign(Gtk.Align.START)
        frame.set_vexpand(False)
        _set_margin(frame, left=5, right=5)
        self.vbox.pack_start(frame, False, False, 5)

        table = Gtk.Grid()
        table.set_column_spacing(5)
        table.set_row_spacing(5)
        _set_margin(table, left=5, right=5, bottom=5)
        frame.add(table)
        row = 0

        icon_visibility = self.get_setting("icon_visibility")

        label = Gtk.Label(_("Show Icon"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.icon_combox = Gtk.ComboBoxText()
        self.icon_combox.append("always", _("Always"))
        self.icon_combox.append("low", _("When Low Power"))
        self.icon_combox.append("charging", _("While Charging"))
        self.icon_combox.append("never", _("Never"))
        self.icon_combox.set_hexpand(True)
        self.icon_combox.set_size_request(220, -1)
        self.icon_combox.set_active_id(icon_visibility)
        self.icon_combox.connect("changed", self.__on_combox_item_changed, "icon_visibility")
        table.attach(self.icon_combox, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Icon Style"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.icon_style_combox = Gtk.ComboBoxText()
        self.icon_style_combox.append("True", _("Symbolic"))
        self.icon_style_combox.append("False", _("Normal"))
        self.icon_style_combox.set_hexpand(True)
        self.icon_style_combox.set_size_request(220, -1)
        self.icon_style_combox.set_active_id(str(self.get_setting("use_symbolic_icon")))
        self.icon_style_combox.set_sensitive(icon_visibility != "never")
        self.icon_style_combox.connect("changed", self.__on_combox_item_changed, "use_symbolic_icon")
        table.attach(self.icon_style_combox, 1, row, 1, 1)
        row += 1

        
        label_visibility = self.get_setting("label_visibility")
        
        label = Gtk.Label(_("Show Label"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.label_combox = Gtk.ComboBoxText()
        self.label_combox.append("never", _("Never"))
        self.label_combox.append("time", _("Time To Run Out"))
        self.label_combox.append("percent", _("Capacity Percentage"))
        self.label_combox.set_hexpand(True)
        self.label_combox.set_size_request(220, -1)
        self.label_combox.set_active_id(label_visibility)
        self.label_combox.connect("changed", self.__on_combox_item_changed, "label_visibility")
        table.attach(self.label_combox, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Font"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.font_button = Gtk.FontButton()
        self.font_button.set_use_font(True)
        self.font_button.set_use_size(False)
        self.font_button.set_show_size(True)
        self.font_button.set_show_style(True)
        self.font_button.set_hexpand(True)
        self.font_button.set_size_request(220, -1)
        Gtk.FontChooser.set_font(self.font_button, self.get_setting("font"))
        self.font_button.set_sensitive(label_visibility != "never")
        self.font_button.connect("font-set", self.__on_font_changed, "font")
        table.attach(self.font_button, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Text Color"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.color_button = Gtk.ColorButton()
        self.color_button.set_hexpand(True)
        self.color_button.set_size_request(220, -1)
        Gtk.ColorChooser.set_use_alpha(self.color_button, hasattr(Pango, "attr_foreground_alpha_new"))
        Gtk.ColorChooser.set_rgba(self.color_button, self.__rgba_convert(self.get_setting("color")))
        self.color_button.set_sensitive(label_visibility != "never")
        self.color_button.connect("color-set", self.__on_color_changed, "color")
        table.attach(self.color_button, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Text Direction"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 0, row, 1, 1)
        self.rotation_combox = Gtk.ComboBoxText()
        self.rotation_combox.append("no", _("always left-right"))
        self.rotation_combox.append("anticlockwise", _("top-down on left/right side"))
        self.rotation_combox.append("clockwise", _("bottom-up on left/right side"))
        self.rotation_combox.set_hexpand(True)
        self.rotation_combox.set_size_request(220, -1)
        self.rotation_combox.set_active_id(self.get_setting("rotation"))
        self.rotation_combox.set_sensitive(label_visibility != "never")
        self.rotation_combox.connect("changed", self.__on_combox_item_changed, "rotation")
        table.attach(self.rotation_combox, 1, row, 1, 1)
        row += 1

        frame = Gtk.Frame.new(_("Left Click Popup Menu"))
        frame.set_valign(Gtk.Align.START)
        frame.set_vexpand(False)
        _set_margin(frame, left=5, right=5)
        self.vbox.pack_start(frame, False, False, 5)

        table = Gtk.Grid()
        table.set_column_spacing(5)
        table.set_row_spacing(5)
        _set_margin(table, left=5, right=5, bottom=5)
        frame.add(table)
        row = 0

        label = Gtk.Label(_("Show CPU Modes"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.cpumodes_swt = Gtk.Switch()
        self.cpumodes_swt.set_active(self.get_setting("show_cpu_modes"))
        self.cpumodes_swt.set_halign(Gtk.Align.END)
        self.cpumodes_swt.set_hexpand(True)
        self.cpumodes_swt.connect("state-set", self.__on_switch_changed, "show_cpu_modes")
        table.attach(self.cpumodes_swt, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Show Sleep Actions"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.sleep_swt = Gtk.Switch()
        self.sleep_swt.set_active(self.get_setting("show_sleep_actions"))
        self.sleep_swt.set_halign(Gtk.Align.END)
        self.sleep_swt.set_hexpand(True)
        self.sleep_swt.connect("state-set", self.__on_switch_changed, "show_sleep_actions")
        table.attach(self.sleep_swt, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Show Session Actions"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.session_swt = Gtk.Switch()
        self.session_swt.set_active(self.get_setting("show_session_actions"))
        self.session_swt.set_halign(Gtk.Align.END)
        self.session_swt.set_hexpand(True)
        self.session_swt.connect("state-set", self.__on_switch_changed, "show_session_actions")
        table.attach(self.session_swt, 1, row, 1, 1)
        row += 1

        frame = Gtk.Frame.new(_("Low Power Protection"))
        frame.set_valign(Gtk.Align.START)
        frame.set_vexpand(False)
        _set_margin(frame, left=5, right=5)
        self.vbox.pack_start(frame, False, False, 5)

        table = Gtk.Grid()
        table.set_column_spacing(5)
        table.set_row_spacing(5)
        _set_margin(table, left=5, right=5, bottom=5)
        frame.add(table)
        row = 0

        label = Gtk.Label(_("When Low Power"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.action_combox = Gtk.ComboBoxText()
        self.action_combox.append("warning", _("Show Warning"))
        self.action_combox.append("sleep", _("Sleep"))
        self.action_combox.append("nothing", _("Do Nothing"))
        self.action_combox.set_hexpand(True)
        self.action_combox.set_size_request(260, -1)
        self.action_combox.set_active_id(self.get_setting("low_power_action"))
        self.action_combox.connect("changed", self.__on_combox_item_changed, "low_power_action")
        table.attach(self.action_combox, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Remaining Percentage"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.capacity_spin = Gtk.SpinButton()
        self.capacity_spin.set_range(1, 99)
        self.capacity_spin.set_digits(0)
        self.capacity_spin.set_increments(1, 5)
        self.capacity_spin.set_numeric(True)
        self.capacity_spin.set_hexpand(True)
        self.capacity_spin.set_size_request(260, -1)
        self.capacity_spin.set_value(self.get_setting("low_capacity"))
        self.capacity_spin.connect("value-changed", self.__on_spin_changed, "low_capacity")
        table.attach(self.capacity_spin, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Remaining Minutes"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.time_spin = Gtk.SpinButton()
        self.time_spin.set_range(1, 60)
        self.time_spin.set_digits(0)
        self.time_spin.set_increments(5, 10)
        self.time_spin.set_numeric(True)
        self.time_spin.set_hexpand(True)
        self.time_spin.set_size_request(260, -1)
        self.time_spin.set_value(self.get_setting("low_time"))
        self.time_spin.connect("value-changed", self.__on_spin_changed, "low_time")
        table.attach(self.time_spin, 1, row, 1, 1)
        row += 1

        frame = Gtk.Frame.new(_("Misc"))
        frame.set_valign(Gtk.Align.START)
        frame.set_vexpand(False)
        _set_margin(frame, left=5, right=5)
        self.vbox.pack_start(frame, False, False, 5)

        table = Gtk.Grid()
        table.set_column_spacing(5)
        table.set_row_spacing(5)
        _set_margin(table, left=5, right=5, bottom=5)
        frame.add(table)
        row = 0

        label = Gtk.Label(_("Restore Last CPU Mode On Startup"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.restore_swt = Gtk.Switch()
        self.restore_swt.set_active(self.get_setting("restore_cpu_mode"))
        self.restore_swt.set_halign(Gtk.Align.END)
        self.restore_swt.set_hexpand(True)
        self.restore_swt.set_sensitive(CpufreqUtils().can_write())
        self.restore_swt.connect("state-set", self.__on_switch_changed, "restore_cpu_mode")
        table.attach(self.restore_swt, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Confirm Before Sleep Actions"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.sleepconfirm_swt = Gtk.Switch()
        self.sleepconfirm_swt.set_active(self.get_setting("confirm_sleep"))
        self.sleepconfirm_swt.set_halign(Gtk.Align.END)
        self.sleepconfirm_swt.set_hexpand(True)
        self.sleepconfirm_swt.connect("state-set", self.__on_switch_changed, "confirm_sleep")
        table.attach(self.sleepconfirm_swt, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(_("Confirm Before Session Actions"))
        label.set_halign(Gtk.Align.START)
        _set_margin(label, left=5)
        table.attach(label, 0, row, 1, 1)
        self.sessionconfirm_swt = Gtk.Switch()
        self.sessionconfirm_swt.set_active(self.get_setting("confirm_session"))
        self.sessionconfirm_swt.set_halign(Gtk.Align.END)
        self.sessionconfirm_swt.set_hexpand(True)
        self.sessionconfirm_swt.connect("state-set", self.__on_switch_changed, "confirm_session")
        table.attach(self.sessionconfirm_swt, 1, row, 1, 1)
        row += 1

        self.vbox.show_all()
        return

    def __on_combox_item_changed(self, combox, key):
        value = combox.get_active_id()
        if key == "icon_visibility":
            self.icon_style_combox.set_sensitive(value != "never")
        elif key == "label_visibility":
            self.font_button.set_sensitive(value != "never")
            self.color_button.set_sensitive(value != "never")
            self.rotation_combox.set_sensitive(value != "never")
        elif key == "use_symbolic_icon":
            value = value == "True"
            self.icon_pixbufs = {}
        self.set_setting(key, value)

    def __on_switch_changed(self, switch, state, option):
        self.set_setting(option, state)

    def __on_font_changed(self, button, option):
        font = Gtk.FontChooser.get_font(button);
        self.set_setting(option, font)

    def __on_color_changed(self, button, option):
        rgba = Gtk.ColorChooser.get_rgba(button);
        self.set_setting(option, self.__rgba_convert(rgba))

    def __on_spin_changed(self, spin, option):
        self.set_setting(option, spin.get_value_as_int())

    def __rgba_convert(self, data):
        if type(data) == list:
            while len(data) < 4:
                data.append(1.0)
            rgba = Gdk.RGBA()
            rgba.red = data[0]
            rgba.green = data[1]
            rgba.blue = data[2]
            rgba.alpha = data[3]
            return rgba
        else:
            return [ data.red, data.green, data.blue, data.alpha ]

    def on_setting_changed(self, key, value):
        if key == "label_visibility":
            self.label_combox.set_active_id(value)
        elif key == "icon_visibility":
            self.icon_combox.set_active_id(value)
        elif key == "use_symbolic_icon":
            self.icon_style_combox.set_active_id(str(value))
        elif key == "font":
            Gtk.FontChooser.set_font(self.font_button, value);
        elif key == "color":
            Gtk.ColorChooser.set_rgba(self.color_button, self.__rgba_convert(value))
        elif key == "rotation":
            self.rotation_combox.set_active_id(value)
        elif key == "show_cpu_modes":
            self.cpumodes_swt.set_active(value)
        elif key == "show_sleep_actions":
            self.sleep_swt.set_active(value)
        elif key == "show_session_actions":
            self.session_swt.set_active(value)
        elif key == "low_power_action":
            self.action_combox.set_active_id(value)
        elif key == "low_capacity":
            self.capacity_spin.set_value(value)
        elif key == "low_time":
            self.time_spin.set_value(value)
        elif key == "restore_cpu_mode":
            self.restore_swt.set_active(value)
        elif key == "confirm_sleep":
            self.sleepconfirm_swt.set_active(value)
        elif key == "confirm_session":
            self.sessionconfirm_swt.set_active(value)

def get_dbx_applet(dbx_dict):
    return DockXBatteryApplet(dbx_dict)

def run_applet_dialog(applet_id):
    dialog = DockXBatteryPreferences(applet_id)
    dialog.run()
    dialog.destroy()

