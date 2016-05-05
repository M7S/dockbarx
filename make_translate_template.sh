#!/bin/sh
# Run this to make a dockbarx.pot template file for translation of dockbarx.
xgettext --language=Python --keyword=_ --output=po/dockbarx.pot --from-code=UTF-8 `find . -name "*.py" -not -path "./build/*"` dockx dbx_preference dockbarx_factory
