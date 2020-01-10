#!/usr/bin/env python3

#   zg.py
#	Copyright 2010 Siegfried-Angel Gevatter Pujals and Matias Sars
#
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

# This code was based on a python snipet.
# SNIPPET_NAME: Recently used items
# SNIPPET_CATEGORIES: Zeitgeist
# SNIPPET_DESCRIPTION: Find recently used items from Zeitgeist (synchronously)
# SNIPPET_AUTHOR: Siegfried-Angel Gevatter Pujals <siegfried@gevatter.com>
# SNIPPET_LICENSE: GPL

from datetime import date
from time import time
        
import gi
try:
    gi.require_version('Zeitgeist', '2.0')
    from gi.repository import Zeitgeist
except:
    Zeitgeist = None
else:
    zlog = Zeitgeist.Log.new()
    
    
def pythonify_zg_events(source, result):
    # Finish the event search
    try:
        result_set = source.find_events_finish(result)
    except GLib.GError as e:
        logger.warning("Zeitgest error: %s" % e.message)
        return None
    # Return the search result as a list of (name, uri)-tuples
    return_list = []
    while result_set.has_next():
        event = result_set.next_value()
        for subject in event.get_subjects():
            return_list.append((str(subject.get_text()), str(subject.get_uri())))
    return return_list


def _get(name=None,
         result_type=None,
         days=14,
         number_of_results=5,
         mimetypes=[],
         handler=None):
    # ~ if iface is None:
        # ~ return
    if result_type is None:
        result_type = Zeitgeist.ResultType.MOST_RECENT_SUBJECTS
    # Start and end times in time since epoch inmilliseconds.
    end = round(time()*1000)
    start = end - days * 24 * 3600 * 1000
    time_range = Zeitgeist.TimeRange.new(start, end)

    if not mimetypes:
        event_template = Zeitgeist.Event.new()
        if name:
            event_template.set_actor("application://%s"%name)
        event_templates = [event_template]
    else:
        event_templates = []
        for mimetype in mimetypes:
            event_template = Zeitgeist.Event.new()
            if name:
                event_template.set_actor("application://%s"%name)
            subject = Zeitgeist.Subject.new()
            subject.set_mimetype(mimetype)
            event_template.add_subject(subject)
            event_templates.append(event_template)

    zlog.find_events(time_range, event_templates,
                     Zeitgeist.StorageState.ANY, number_of_results,
                     result_type, None, handler)


def get_recent_for_app(name, days=14, number_of_results=5, handler=None):
    _get(name, Zeitgeist.ResultType.MOST_RECENT_SUBJECTS,
        days, number_of_results, handler=handler)


def get_most_used_for_app(name, days=14, number_of_results=5, handler=None):
    _get(name, Zeitgeist.ResultType.MOST_POPULAR_SUBJECTS,
        days, number_of_results, handler=handler)


def get_most_used_for_mimetypes(mimetypes, days=1, number_of_results=5, handler=None):
    _get(mimetypes=mimetypes,
        result_type=Zeitgeist.ResultType.MOST_POPULAR_SUBJECTS,
        days=days,
        number_of_results=number_of_results,
        handler=handler)


def get_recent_for_mimetypes(mimetypes, days=1, number_of_results=5, handler=None):
    _get(mimetypes=mimetypes,
        result_type=Zeitgeist.ResultType.MOST_RECENT_SUBJECTS,
        days=days,
        number_of_results=number_of_results,
        handler=handler)
    

