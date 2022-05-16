#!/usr/bin/env python
#   vim:fileencoding=utf-8
# (c) 2017-2018 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from gentoopm import get_package_manager

from gpyutils.ansi import ANSI
from gpyutils.implementations import get_impl_by_name, read_implementations
from gpyutils.pycompat import EbuildMangler

import sys


def main(prog_name, *argv):
    pm = get_package_manager()

    if len(argv) < 2:
        print('Usage: %s <foo.ebuild> <[+|-]impl>...' % prog_name)
        return 1

    read_implementations(pm)

    to_add = set()
    to_remove = set()
    for a in argv[1:]:
        if a[0] in ('-', '%', '+'):
            impl = a[1:]
        else:
            impl = a
        impl = get_impl_by_name(impl)
        if a[0] not in ('-', '%'):
            to_add.add(impl)
        else:
            to_remove.add(impl)

    with EbuildMangler(argv[0]) as em:
        before = em.value
        for x in to_add:
            em.add(x.r1_name)
        for x in to_remove:
            em.remove(x.r1_name)
        after = em.value
        print('%s-PYTHON_COMPAT=(%s)%s' % (ANSI.red, before, ANSI.reset))
        print('%s+PYTHON_COMPAT=(%s)%s' % (ANSI.green, after, ANSI.reset))

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
