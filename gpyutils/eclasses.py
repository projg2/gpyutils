#   vim:fileencoding=utf-8
# (c) 2017-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .util import EnumObj

from gentoopm.basepm.atom import PMAtom


class PkgType(object):
    """ Package sub-type. """

    class python(EnumObj(4)):
        eclass_r1 = 'python-r1'

    class python_single(EnumObj(3)):
        eclass_r1 = 'python-single-r1'

    class python_any(EnumObj(1)):
        eclass_r1 = 'python-any-r1'

    all_types = (python, python_single, python_any)


def guess_package_type(pkg):
    for s in PkgType.all_types:
        if s.eclass_r1 in pkg.inherits:
            return s
    return None
