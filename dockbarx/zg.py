#!/usr/bin/env python


# This code is based on a python snipet.
# [SNIPPET_NAME: Recently used items]
# [SNIPPET_CATEGORIES: Zeitgeist]
# [SNIPPET_DESCRIPTION: Find recently used items from Zeitgeist (synchronously)]
# [SNIPPET_AUTHOR: Siegfried-Angel Gevatter Pujals <siegfried@gevatter.com>]
# [SNIPPET_LICENSE: GPL]

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
    print "Testing with gedit.desktop"
    results = get_recent_for_app("gedit.desktop")
    for event in results:
        timestamp = int(event.timestamp) / 1000 # Zeitgeist timestamps are in msec
        print date.fromtimestamp(timestamp).strftime("%d %B %Y")
        for subject in event.get_subjects():
            print " -", subject.text, ":", subject.uri

