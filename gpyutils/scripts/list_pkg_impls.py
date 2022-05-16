#!/usr/bin/env python
#   vim:fileencoding=utf-8
# (c) 2013-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from gentoopm import get_package_manager

from gpyutils.implementations import (get_python_impls,
                                      read_implementations)
from gpyutils.packages import (get_package_class, group_packages,
                               PackageClass)

import sys


def process(pkgs):
    key = 'slotted_atom'
    for pg in group_packages(pkgs.sorted, key):
        kw_impls = []
        st_impls = []
        eapi = None
        pep517 = False

        for p in reversed(pg):
            # if the newest version does not use python, stop here
            impls = get_python_impls(p)
            if impls is None:
                break

            # otherwise, try to find keywords of the newest version
            # with stable and ~arch keyword
            cl = get_package_class(p)
            if eapi is None:
                eapi = p.eapi
            if not kw_impls:
                if not cl == PackageClass.non_keyworded:
                    kw_impls = [x.short_name for x in impls]
            if not st_impls:
                if cl == PackageClass.stable:
                    st_impls = [x.short_name for x in impls]
            if not pep517:
                with open(p.path) as f:
                    for x in f:
                        if x.startswith('DISTUTILS_USE_PEP517='):
                            pep517 = True
                            break
                        if x.startswith('inherit '):
                            break
            if kw_impls and st_impls:
                break

        # if no impls found, the package is either non-python
        # or unkeyworded
        if not kw_impls and not st_impls:
            continue

        out = ['{:<40}'.format(str(getattr(p, key)))]
        out.append('EAPI:')
        out.append(eapi)

        out.append("(PEP517)" if pep517 else "        ")

        if st_impls:
            out.append(' STABLE:')
            out.extend(st_impls)

        # print only extra impls
        for impl in list(kw_impls):
            if impl in st_impls:
                kw_impls.remove(impl)

        if kw_impls:
            out.append('  ~ARCH:')
            out.extend(kw_impls)

        print(' '.join(out))


def main():
    pm = get_package_manager()
    read_implementations(pm)

    process(pm.repositories['gentoo'])
    return 0


def entry_point():
    sys.exit(main())


if __name__ == '__main__':
    sys.exit(main())
