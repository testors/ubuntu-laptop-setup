#!/usr/bin/bash
set -euo pipefail
if (( EUID != 0 )); then
    exec pkexec /usr/bin/bash "$0"
fi
drop_in=/etc/systemd/system/fprintd.service.d/60-egis-05b1.conf
if [[ -f "$drop_in" ]]; then
    rm -- "$drop_in"
fi
systemctl daemon-reload
systemctl restart fprintd.service
printf 'The distribution fingerprint driver is restored. Fingerprint records and password authentication were not changed.\n'
