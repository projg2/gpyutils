# gpyutils
# (c) 2017-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import enum


@enum.unique
class PkgType(enum.Enum):
    """Package type."""

    python = "python-r1"
    python_single = "python-single-r1"
    python_any = "python-any-r1"


def guess_package_type(pkg):
    for s in PkgType:
        if s.value in pkg.inherits:
            return s
    return None
