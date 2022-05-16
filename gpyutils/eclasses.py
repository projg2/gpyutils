#   vim:fileencoding=utf-8
# (c) 2017-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

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
