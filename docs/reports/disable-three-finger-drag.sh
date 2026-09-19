#!/usr/bin/bash
set -euo pipefail
[[ $(id -u) == 1000 ]] || { echo 'Run as testors, without sudo.' >&2; exit 1; }
drag_dropin=/home/testors/.config/systemd/user/org.gnome.Shell@ubuntu.service.d/60-three-finger-drag.conf
if [[ -f "$drag_dropin" ]]; then
    if ! cmp -s "$drag_dropin" <(cat <<'EOF'
# Enable libinput native three-finger drag for this user's Ubuntu GNOME session.
[Service]
Environment="LD_PRELOAD=/home/testors/.local/lib/enable-3fg-drag/09e9ca7/libenable-3fg-drag.so"
Environment="LD_LIBRARY_PATH=/home/testors/.local/lib/enable-3fg-drag/libinput-1.31.1-drag-only-v1"
EOF
    ); then
        echo 'Configuration changed since installation; inspect it before removing.' >&2
        exit 1
    fi
    rm -- "$drag_dropin"
fi
systemctl --user daemon-reload
printf 'Three-finger drag will be disabled after the next logout and login.\n'
printf 'The current session was not restarted. Installed library files were retained.\n'
