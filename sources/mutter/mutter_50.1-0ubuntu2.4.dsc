-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: mutter
Binary: mutter, mutter-18-tests, gir1.2-mutter-18, libmutter-18-0, libmutter-18-dev, libmutter-test-18, mutter-common, mutter-common-bin, mutter-dev-bin
Architecture: linux-any all
Version: 50.1-0ubuntu2.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Jeremy Bícha <jbicha@ubuntu.com>
Homepage: https://mutter.gnome.org/
Standards-Version: 4.7.3
Vcs-Browser: https://salsa.debian.org/gnome-team/mutter/tree/ubuntu/resolute
Vcs-Git: https://salsa.debian.org/gnome-team/mutter.git -b ubuntu/resolute
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, gnome-desktop-testing
Build-Depends: debhelper-compat (= 13), dh-exec, dh-sequence-gir, dh-sequence-gnome, at-spi2-core <!nocheck>, adwaita-icon-theme <!nocheck>, bash-completion, dbus-daemon <!nocheck>, dmz-cursor-theme <!nocheck>, gir1.2-atk-1.0-dev, gir1.2-cairo-1.0-dev, gir1.2-gdesktopenums-3.0-dev, gir1.2-gio-2.0-dev, gir1.2-gl-1.0-dev, gir1.2-gobject-2.0-dev, gir1.2-graphene-1.0-dev, gir1.2-pango-1.0-dev, gir1.2-pangocairo-1.0-dev, gir1.2-xfixes-4.0-dev, gir1.2-xlib-2.0-dev, libglycin-2-dev (>= 2.0~beta.2), gnome-control-center-data, gnome-settings-daemon-common <!nocheck>, gnome-settings-daemon-dev, gobject-introspection (>= 1.80), gsettings-desktop-schemas-dev (>= 50~alpha), gtk-doc-tools, libadwaita-1-dev, libei-dev (>= 1.3.901), libeis-dev (>= 1.3.901), libcairo2-dev, libcanberra-gtk3-dev, libcolord-dev, libdisplay-info-dev (>= 0.2), libdrm-dev (>= 2.4.118), libegl1-mesa-dev, libfribidi-dev, libgbm-dev (>= 21.3), libgl-dev, libgles-dev, libglib2.0-dev (>= 2.76), libgnome-desktop-4-dev, libgraphene-1.0-dev, libgtk-3-dev <!nocheck>, libgtk-4-dev (>= 4.22.0), libgudev-1.0-dev (>= 238), libjson-glib-dev, libice-dev, libinput-dev (>= 1.30.0), liblcms2-dev, libnvidia-egl-wayland-dev, libpam0g-dev, libpango1.0-dev, libpipewire-0.3-dev (>= 1.6.1), libpixman-1-dev (>= 0.42), libsm-dev, libsoup-3.0-dev, libstartup-notification0-dev, libsysprof-6-dev [amd64 arm64 armhf loong64 ppc64el riscv64 s390x], libsysprof-capture-4-dev (>= 3.40.1) [amd64 arm64 armhf loong64 ppc64el riscv64 s390x], libsystemd-dev, libumockdev-dev (>= 0.3.0), libwacom-dev, libwayland-dev (>= 1.24), libxau-dev, libx11-dev, libx11-xcb-dev, libxcb-res0-dev, libxcomposite-dev, libxcursor-dev, libxdamage-dev, libxext-dev, libxfixes-dev, libxi-dev, libxinerama-dev, libxkbcommon-dev, libxkbregistry-dev, libxrandr-dev, libxrender-dev, meson (>= 1.5.0), pipewire <!nocheck>, pkgconf, python3-argcomplete, python3-dbus <!nocheck>, python3-dbusmock, python3-docutils, sysprof [amd64 arm64 armhf loong64 ppc64el riscv64 s390x], systemd-dev, umockdev <!nocheck>, wayland-protocols (>= 1.47), wireplumber <!nocheck>, xauth <!nocheck>, xcvt:native, xkb-data, xwayland (>= 2:23.1.0), zenity
Package-List:
 gir1.2-mutter-18 deb introspection optional arch=linux-any
 libmutter-18-0 deb libs optional arch=linux-any
 libmutter-18-dev deb libdevel optional arch=linux-any
 libmutter-test-18 deb libs optional arch=linux-any
 mutter deb x11 optional arch=linux-any
 mutter-18-tests deb x11 optional arch=linux-any
 mutter-common deb misc optional arch=all
 mutter-common-bin deb misc optional arch=linux-any
 mutter-dev-bin deb devel optional arch=linux-any
Checksums-Sha1:
 2e2a6b96a2ffb8eeb266c23c9b9dc5137af2bfb7 8430744 mutter_50.1.orig.tar.xz
 2b566a7de08ee49acd19eb2ac8825620c106f58e 118156 mutter_50.1-0ubuntu2.4.debian.tar.xz
Checksums-Sha256:
 9344502ce473f788795f26b45f8b8ff53c0a36b867470d705a11a3ee0911021e 8430744 mutter_50.1.orig.tar.xz
 92b0027e8cf30c7ca0577c02b88b8cbd014cfddd0d513f3df3d698dc32f80e20 118156 mutter_50.1-0ubuntu2.4.debian.tar.xz
Files:
 5e4147170db223878e2845c2ae695640 8430744 mutter_50.1.orig.tar.xz
 79299430be64b2eb14cffc5c996e57fd 118156 mutter_50.1-0ubuntu2.4.debian.tar.xz
Debian-Vcs-Browser: https://salsa.debian.org/gnome-team/mutter
Debian-Vcs-Git: https://salsa.debian.org/gnome-team/mutter.git
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJSBAEBCgA8FiEEe36CAb2OUpFsR+d1yqruyKy2bB0FAmqf6X0eHGRhbmllbC52
YW4udnVndEBjYW5vbmljYWwuY29tAAoJEMqq7sistmwdFfQP/i/7DlExqTecKIUu
s5NqNHe536JQuhD+60AAHnkzzQk3cCXzPzSrSNUalByHz+1USPZpDL16z8ou7cWq
rLfW1lby3rKbC72eOmJaQcCCaeY/Wz2rwI66tL0jp2ndRWy3hYXk3arbLDtAngzM
E7YDUUx8mu0kujrJ9MEoTdvUtQpQJxOTO+dBaZxFiR9JkAmadzJbOQ+4DNMwMBu9
HTRoB1dVXaByUVunCEZAeClf+9QtWhBH6hkzQkHJ0EPr33R6gKpFTA7Q34Q6Pm+3
YWh2hpYcShQ5nKV3dTQdaXRoSvSNBglizNcFvM6NnpBBHmt95XHeCioQWqC5jigv
3CKKi6SZ7+CrqaKQVK9YQ+sxOWq/4ORDq750aSWwG6ebDLZJ3S2hdmyicXbGSF6r
4LgvTmwk705RhIj7XWDCCAsd0UhuzcYai/J2w99ZrNxlu+Lw+sipIJ0eNKORVcGD
it52VOTepNE33DnE5H56ACu2ioIGKlgRQlmc8bKVLHROyBSz1UWhavAWrtn/0CNA
SuYQlstQrbL0rlY8MBp55BdGXrQhFknrn4WaZ4qnfMt7JR7pPvWkHzgMw2eYuC9p
Q+ZnKHPIQL1T71/erHZfuGS9oFw5oWNlDYnYQJ1TYbJQlsKj/N3Gh1aFu2exOpo4
c5Am7z3KekktXnCJBhThgsamuzGJ
=WVTh
-----END PGP SIGNATURE-----
