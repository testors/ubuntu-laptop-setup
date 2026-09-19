-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libinput
Binary: libinput10, libinput-bin, libinput10-udeb, libinput-dev, libinput-tools
Architecture: any
Version: 1.31.1-1ubuntu1.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Emilio Pozuelo Monfort <pochu@debian.org>, Héctor Orón Martínez <zumbi@debian.org>, Marius Gripsgard <marius@ubports.com>
Homepage: https://www.freedesktop.org/wiki/Software/libinput/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/xorg-team/lib/libinput
Vcs-Git: https://salsa.debian.org/xorg-team/lib/libinput.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential
Build-Depends: debhelper-compat (= 13), meson, pkgconf, check, libgtk-3-dev, libmtdev-dev (>= 1.1.0), libudev-dev, libevdev-dev (>= 1.10.0), libwacom-dev (>= 0.20)
Package-List:
 libinput-bin deb libs optional arch=any
 libinput-dev deb libdevel optional arch=any
 libinput-tools deb libdevel optional arch=any
 libinput10 deb libs optional arch=any
 libinput10-udeb udeb debian-installer optional arch=any profile=!noudeb profile:v1=!noudeb
Checksums-Sha1:
 a94945b1a056e1c9b7e9ea54966cbe46a6c266f1 1175300 libinput_1.31.1.orig.tar.gz
 9b9affaac121bc2137d12228f409b86d294a43f5 13884 libinput_1.31.1-1ubuntu1.2.debian.tar.xz
Checksums-Sha256:
 72c7d62a117f89a0e611d76b0a28ba8bf08fc24083d2678060aee8de88c87953 1175300 libinput_1.31.1.orig.tar.gz
 7f92934f77f382e262962a088ee84860891368b26ca039700d2112d3fa6fee61 13884 libinput_1.31.1-1ubuntu1.2.debian.tar.xz
Files:
 b00837a654f8a318cd4b959a3172f8b1 1175300 libinput_1.31.1.orig.tar.gz
 f33f56dd194c962e86b4d030db0efe37 13884 libinput_1.31.1-1ubuntu1.2.debian.tar.xz
Original-Maintainer: Debian X Strike Force <debian-x@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEyMDHOTG0YH5UsajI8pSCVQZYHygFAmqkjZgACgkQ8pSCVQZY
HyghPQ/+MfX39s5A/OQMQku3URRH03g4FFDEgwjfxcE1BZa7bzOw5tCGH/BytiiI
OJyEBoJMmxwPZVFMXAmoCczJMJhq/Bcmf8MSTJb0/xRI5uRX3JZNKFiL6UX74Vwd
vT1f63IiDy9UJeG9p8VOQQ/XVDtRVlkKN0CQtgliHv+pdDrq8V3i3IPuY+sBe388
FfDQSnR2OMmDOfE4mUvzTMqEbui48TucKemcMsBP6MuVQe+Vg5UKttXQFI0Z/ZXG
eDLhTDgVC6MBF1Dj0dQC5d3XyzS4nAt+0kw88PGMjbWktcqa80W9ILJi6B6j7mZ9
zn6m6AQDMaV9IyNvcP7TwsR0RTj5cJmLSNPraNOZhMh6VMG7W205ulz+3suyFA6q
3gqTbgrHfM8jmxmLHxRLc1zLCdqSEWsr3Q41mB8qGhb7FbcGQNnJfSR7ZAZ8NxBA
Ii7/mZXhS5J36H1zLoYsqQvUnnnn+TRD8RzOkNOveMz5ilCkerrQf1praeURuLJB
qhJe9eDua2Dqd5HnM9GOrU6oPZZRvhW5J03Pe7sTUSzYSfrIGm22YAO4Tx7iBbsT
GBZLBT4fDoI1lONcmPbtabxNeDq6r2pNg5ckQ18cWs0ypkXX4qJqRJXe70KFpj1I
GpqSt4ZugcSg3XfHEF6unnVK7KWF1oHgvHLHeD+QFT2Zra8db7Q=
=uhW4
-----END PGP SIGNATURE-----
