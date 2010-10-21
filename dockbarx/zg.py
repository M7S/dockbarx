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
         result_type=None,
         days=14,
         number_of_results=5,
         mimetypes=[]):
    if iface is None:
        return
    if result_type is None:
        result_type = datamodel.ResultType.MostRecentSubjects
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
    return _get(name, datamodel.ResultType.MostRecentSubjects,
                days, number_of_results)

def get_most_used_for_app(name, days=14, number_of_results=5):
    if iface is None:
        return []
    return _get(name, datamodel.ResultType.MostPopularSubjects,
                days, number_of_results)

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

# Mimetypes to use for programs that has no/bad support for zeitgeist
workrounds = \
 {'openoffice.org-writer':
   ['application/msword',
    'application/rtf',
    'application/vnd.ms-works',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.text-master',
    'application/vnd.oasis.opendocument.text-template',
    'application/vnd.stardivision.writer',
    'application/vnd.stardivision.writer-global',
    'application/vnd.sun.xml.writer',
    'application/vnd.sun.xml.writer.global',
    'application/vnd.sun.xml.writer.template',
    'application/vnd.wordperfect',
    'application/wordperfect',
    'text/rtf',
    'application/vnd.ms-word.document.macroEnabled.12',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-word.template.macroEnabled.12',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template'],
  'openoffice.org-draw':
     ['application/vnd.oasis.opendocument.graphics',
      'application/vnd.oasis.opendocument.graphics-template',
      'application/vnd.stardivision.draw',
      'application/vnd.sun.xml.draw',
      'application/vnd.sun.xml.draw.template'],
  'openoffice.org-impress':
     ['application/mspowerpoint',
      'application/vnd.ms-powerpoint',
      'application/vnd.oasis.opendocument.presentation',
      'application/vnd.oasis.opendocument.presentation-template',
      'application/vnd.stardivision.impress',
      'application/vnd.sun.xml.impress',
      'application/vnd.sun.xml.impress.template',
      'application/vnd.ms-powerpoint.slideshow.macroEnabled.12',
      'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
      'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint.template.macroEnabled.12',
      'application/vnd.openxmlformats-officedocument.presentationml.template'],
  'openoffice.org-calc':
     ['application/msexcel',
      'application/vnd.lotus-1-2-3',
      'application/vnd.ms-excel',
      'application/vnd.oasis.opendocument.chart',
      'application/vnd.oasis.opendocument.chart-template',
      'application/vnd.oasis.opendocument.spreadsheet',
      'application/vnd.oasis.opendocument.spreadsheet-template',
      'application/vnd.stardivision.calc',
      'application/vnd.stardivision.chart',
      'application/vnd.sun.xml.calc',
      'application/vnd.sun.xml.calc.template',
      'text/spreadsheet',
      'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
      'application/vnd.ms-excel.sheet.macroEnabled.12',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel.template.macroEnabled.12',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
      'application/csv',
      'application/excel',
      'application/x-123',
      'application/x-dos_ms_excel',
      'application/x-excel',
      'application/x-ms-excel',
      'application/x-msexcel']}



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

