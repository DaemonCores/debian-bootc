#!/bin/sh
# cmdline hook, runs before dmsquash-live's own parser (priority 30).
# shellcheck source=inst-stage2-lib.sh
. /lib/debian-bootc-live/inst-stage2-lib.sh
debian_bootc_live_args
