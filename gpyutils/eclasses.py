#   vim:fileencoding=utf-8
# (c) 2017-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .util import EnumObj

from gentoopm.basepm.atom import PMAtom


class PkgSubType(object):
    """ Package sub-type. """

    class python(EnumObj(4)):
        """ python-r1 / multi-ABI python """
        eclass_r1 = 'python-r1'
        eclass_r0 = 'python'

    class python_single(EnumObj(3)):
        """ python-single-r1 / single-ABI python """
        eclass_r1 = 'python-single-r1'
        eclass_r0 = 'python'

    class python_rdep(EnumObj(2)):
        """ - / random python dep in RDEPEND/PDEPEND """
        eclass_r1 = 'python-single-r1'
        eclass_r0 = '(none)'

    class python_any(EnumObj(1)):
        """ python-any-r1 / random python dep in DEPEND """
        eclass_r1 = 'python-any-r1'
        eclass_r0 = '(none)'

    all_subtypes = (python, python_single, python_rdep, python_any)


class PkgType(object):
    """ Guess package type from inherited eclasses. """

    class non_python(EnumObj(1)):
        pass

    class python_r1(EnumObj(3)):
        def __init__(self, subtype):
            self.subtype = subtype


def guess_package_type(pkg):
    # first check for -r1
    # it's easy since every subtype can be recognized using inherit
    for s in PkgSubType.all_subtypes:
        if s.eclass_r1 in pkg.inherits:
            return PkgType.python_r1(s)

    return PkgType.non_python()
