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

def _get(name, result_type):
    min_days_ago = 14
    time_range = datamodel.TimeRange.from_seconds_ago(min_days_ago * 3600 * 24)
    max_amount_results = 5

    event_template = datamodel.Event()
    event_template.set_actor('application://%s'%name)

    results = iface.FindEvents(
        time_range, # (min_timestamp, max_timestamp) in milliseconds
        [event_template, ],
        datamodel.StorageState.Any,
        max_amount_results,
        result_type
    )

    # Pythonize the result
    results = [datamodel.Event(result) for result in results]
    return results

def get_recent_for_app(name):
    if iface == None:
        return []
    return _get(name, datamodel.ResultType.MostRecentSubjects)

def get_most_used_for_app(name):
    if iface == None:
        return []
    return _get(name, datamodel.ResultType.MostPopularSubjects)


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

