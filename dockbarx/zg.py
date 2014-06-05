#!/usr/bin/env python2

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

# This code is based on a python snipet.
# SNIPPET_NAME: Recently used items
# SNIPPET_CATEGORIES: Zeitgeist
# SNIPPET_DESCRIPTION: Find recently used items from Zeitgeist (synchronously)
# SNIPPET_AUTHOR: Siegfried-Angel Gevatter Pujals <siegfried@gevatter.com>
# SNIPPET_LICENSE: GPL

from datetime import date
try:
    from zeitgeist import client, datamodel
except:
    iface = None
else:
    try:
        iface = client.ZeitgeistDBusInterface()
        zgclient = client.ZeitgeistClient()
    except RuntimeError:
        print "Error: Could not connect to Zeitgeist."
        iface = None

def pythonify_zg_events(events):
    return_list = []
    for event in events:
        for subject in event.subjects:
            return_list.append((str(subject.text), str(subject.uri)))
    return return_list

def err_handler(*args):
    print "Zeitgeist error:", args

def _get(name=None,
         result_type=None,
         days=14,
         number_of_results=5,
         mimetypes=[],
         handler=None):
    if iface is None:
        return
    if result_type is None:
        result_type = datamodel.ResultType.MostRecentSubjects
    time_range = datamodel.TimeRange.from_seconds_ago(days * 3600 * 24)

    if not mimetypes:
        event_template = datamodel.Event()
        if name:
            event_template.set_actor("application://%s"%name)
        event_templates = [event_template]
    else:
        event_templates = []
        for mimetype in mimetypes:
            event_template = datamodel.Event()
            if name:
                event_template.set_actor("application://%s"%name)
            event_template.append_subject(
                        datamodel.Subject.new_for_values(mimetype=mimetype))
            event_templates.append(event_template)

    #~ results = iface.FindEvents(time_range,
                               #~ event_templates,
                               #~ datamodel.StorageState.Any,
                               #~ number_of_results,
                               #~ result_type)
    #print "results", results
    zgclient.find_events_for_templates(event_templates,
                                    handler,
                                    timerange=time_range,
                                    storage_state=datamodel.StorageState.Any,
                                    num_events=number_of_results,
                                    result_type=result_type,
                                    error_handler=err_handler)

    #~ # Pythonize the result
    #~ return_list = []
    #~ for result in results:
        #~ for subject in datamodel.Event(result).get_subjects():
            #~ return_list.append((str(subject.text), str(subject.uri)))
    #~ return return_list


def get_recent_for_app(name, days=14, number_of_results=5, handler=None):
    if iface is None:
        return []
    return _get(name, datamodel.ResultType.MostRecentSubjects,
                days, number_of_results, handler=handler)

def get_most_used_for_app(name, days=14, number_of_results=5, handler=None):
    if iface is None:
        return []
    return _get(name, datamodel.ResultType.MostPopularSubjects,
                days, number_of_results, handler=handler)

def get_most_used_for_mimetypes(mimetypes, days=1, \
                                number_of_results=5, handler=None):
    if iface is None:
        return []
    return _get(mimetypes=mimetypes,
                result_type=datamodel.ResultType.MostPopularSubjects,
                days=days,
                number_of_results=number_of_results,
                handler=handler)

def get_recent_for_mimetypes(mimetypes, days=1, number_of_results=5, \
                             handler=None):
    if iface is None:
        return []
    return _get(mimetypes=mimetypes,
                result_type=datamodel.ResultType.MostRecentSubjects,
                days=days,
                number_of_results=number_of_results,
                handler=handler)
    

