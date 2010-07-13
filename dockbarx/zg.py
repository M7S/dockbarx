#!/usr/bin/env python

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
    except RuntimeError:
        print "Error: Could not connect to Zeitgeist."
        iface = None

def _get(name=None,
         result_type=datamodel.ResultType.MostRecentSubjects,
         days=14,
         number_of_results=5,
         mimetypes=[]):
    time_range = datamodel.TimeRange.from_seconds_ago(days * 3600 * 24)

    event_template = datamodel.Event()
    if name:
        event_template.set_actor('application://%s'%name)

    for mimetype in mimetypes:
        event_template.append_subject(
                        datamodel.Subject.new_for_values(mimetype=mimetype))

    results = iface.FindEvents(time_range,
                               [event_template, ],
                               datamodel.StorageState.Any,
                               number_of_results,
                               result_type)

    # Pythonize the result
    return_list = []
    for result in results:
        for subject in datamodel.Event(result).get_subjects():
            return_list.append((str(subject.text), str(subject.uri)))
    return return_list


def get_recent_for_app(name, days=14, number_of_results=5):
    if iface is None:
        return []
    return _get(name, datamodel.ResultType.MostRecentSubjects, days)

def get_most_used_for_app(name, days=14, number_of_results=5):
    if iface is None:
        return []
    return _get(name, datamodel.ResultType.MostPopularSubjects,days)

def get_most_used_for_mimetypes(mimetypes, days=1, number_of_results=5):
    if iface is None:
        return []
    return _get(mimetypes=mimetypes,
                result_type=datamodel.ResultType.MostPopularSubjects,
                days=days,
                number_of_results=number_of_results)

def get_recent_for_mimetypes(mimetypes, days=1, number_of_results=5):
    if iface is None:
        return []
    return _get(mimetypes=mimetypes,
                result_type=datamodel.ResultType.MostRecentSubjects,
                days=days,
                number_of_results=number_of_results)




if __name__ == "__main__":
    app = "gedit.desktop"
    print "Testing with %s"%app
    results = get_recent_for_app(app)
    for event in results:
        # Zeitgeist timestamps are in msec
        timestamp = int(event.timestamp) / 1000
        print date.fromtimestamp(timestamp).strftime("%d %B %Y")
        for subject in event.get_subjects():
            print " -", subject.text, ":", subject.uri

