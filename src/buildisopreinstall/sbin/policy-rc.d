#!/bin/sh
#
# policy-rc.d - deny all daemon start/restart actions during the image build.
# dpkg/apt invoke this hook before (re)starting a service on package install;
# returning 101 tells the invoke-rc.d helper "forbidden", so no daemon runs
# inside the build container (there is no init there and services must start
# only on the real first boot).
exit 101
