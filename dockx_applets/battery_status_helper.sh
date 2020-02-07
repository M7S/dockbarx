#!/bin/bash -e
case "$#" in
	'0') exit 0;;
	'1') ;;
	*) exit 1;;
esac
for file in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
	echo "$1" > "$file"
done
exit 0
