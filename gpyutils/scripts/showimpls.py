#!/usr/bin/env python
#   vim:fileencoding=utf-8
# (c) 2013-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from gentoopm import get_package_manager

from gpyutils.ansi import ANSI
from gpyutils.eclasses import guess_package_type, PkgType
from gpyutils.implementations import (implementations,
                                      get_python_impls,
                                      read_implementations,
                                      Status,
                                      )
from gpyutils.packages import (find_redundant,
                               get_package_class,
                               group_packages,
                               PackageClass,
                               )

import sys


colors = {
    Status.dead: ANSI.red,
    Status.old: ANSI.brown,
    Status.supported: ANSI.green,
    Status.current: ANSI.bgreen,
    Status.experimental: ANSI.purple,
    Status.future: ANSI.cyan,
}


def process(pkgs):
    # omit dead impls since they get ignored anyway
    my_impls = [i for i in implementations
                if i.status not in (Status.dead, Status.future)]
    keys = [i.short_name for i in my_impls]

    for pg in group_packages(pkgs.sorted, 'slotted_atom'):
        print('%s%s%s' % (ANSI.white, pg[0].slotted_atom, ANSI.reset))

        # determine which packages are safely superseded by newer versions
        redundant = set(find_redundant(pg))

        for p in pg:
            output = [' ' * len(x) for x in keys]

            pmask_tag = ' '
            version_color = ''
            try:
                if p.repo_masked:
                    pmask_tag = ANSI.red + 'M' + ANSI.reset
                    version_color = ANSI.red
            except NotImplementedError:
                pass

            pclass = get_package_class(p)
            if pclass == PackageClass.stable:
                keyw_tag = ANSI.green + 'S' + ANSI.reset
            elif pclass == PackageClass.testing:
                keyw_tag = ANSI.brown + '~' + ANSI.reset
            else:
                keyw_tag = ' '

            if p in redundant:
                unused_tag = ANSI.purple + '#' + ANSI.reset
            else:
                unused_tag = ' '

            ptype = guess_package_type(p)
            if ptype is None:
                eclass_tag = '-'
            else:
                impls = get_python_impls(p)
                for i in impls:
                    if i in my_impls:
                        output[keys.index(i.short_name)] = ''.join(
                            (colors[i.status], i.short_name, ANSI.reset))

                if ptype == PkgType.python_single:
                    eclass_tag = ANSI.cyan + 's' + ANSI.reset
                elif ptype == PkgType.python_any:
                    eclass_tag = ANSI.brown + 'a' + ANSI.reset
                else:
                    eclass_tag = ' '

            print('%s%16s%s: %s%s %s %s %s' % (
                version_color, p.version, ANSI.reset,
                keyw_tag, pmask_tag, eclass_tag, unused_tag,
                ' '.join(output).rstrip()))


def main(prog_name, *argv):
    pm = get_package_manager()
    read_implementations(pm)

    if not argv:
        sys.stderr.write('Usage: %s <atom>...\n' % prog_name)
        return 1

    for pkg in argv:
        process(pm.repositories['gentoo'].filter(pkg))

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
