#!/bin/sh
# Run this to make a dockbarx.pot template file for translation of dockbarx.
xgettext --language=Python --keyword=_ --output="$(dirname "$0")/../data/po/dockbarx.pot" --from-code=UTF-8 `find "$(dirname "$0")/.." -name "*.py" -not -path "./build/*"` "$(dirname "$0")"/../utils/* 
