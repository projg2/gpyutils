#!/usr/bin/env python
# gpyutils
# (c) 2017-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

from gentoopm import get_package_manager

from gpyutils.ansi import ANSI
from gpyutils.implementations import get_impl_by_name, read_implementations
from gpyutils.pycompat import EbuildMangler

import sys


def main(prog_name, *argv):
    pm = get_package_manager()

    ebuilds = []
    ops = []
    for arg in argv:
        if arg.endswith(".ebuild"):
            ebuilds.append(arg)
        else:
            ops.append(arg)

    if not ebuilds or not ops:
        print(f"Usage: {prog_name} <foo.ebuild>... <[+|-]impl>...")
        return 1

    read_implementations(pm)

    to_add = set()
    to_remove = set()
    for a in ops:
        if a[0] in ('-', '%', '+'):
            impl = a[1:]
        else:
            impl = a
        impl = get_impl_by_name(impl)
        if a[0] not in ('-', '%'):
            to_add.add(impl)
        else:
            to_remove.add(impl)

    for ebuild in ebuilds:
        with EbuildMangler(ebuild) as em:
            before = em.value
            for x in to_add:
                em.add(x.r1_name)
            for x in to_remove:
                em.remove(x.r1_name)
            after = em.value
            print(f"{ebuild}:")
            print(f"{ANSI.red}-PYTHON_COMPAT=({before}){ANSI.reset}")
            print(f"{ANSI.green}+PYTHON_COMPAT=({after}){ANSI.reset}")

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
