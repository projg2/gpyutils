#!/usr/bin/env python
# gpyutils
# (c) 2013-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import optparse
import sys

import gentoopm.exceptions
from gentoopm import get_package_manager

from gpyutils.ansi import ANSI
from gpyutils.eclasses import guess_package_type
from gpyutils.implementations import (
    Status,
    get_impls_by_status,
    get_python_impls,
    read_implementations,
)
from gpyutils.packages import group_packages
from gpyutils.pycompat import EbuildMangler


def process(pkgs, fix=False):
    dead_impls = get_impls_by_status(Status.dead)

    total_upd = 0
    total_pkg = 0

    sys.stderr.write("%s%sWaiting for PM to start iterating...%s\r"
                     % (ANSI.clear_line, ANSI.brown, ANSI.reset))

    for pg in group_packages(pkgs):
        sys.stderr.write("%s%s%-40s%s (%s%4d%s of %s%4d%s need updating)\r"
                         % (ANSI.clear_line, ANSI.green, pg[0].key, ANSI.reset,
                            ANSI.white, total_upd, ANSI.reset,
                            ANSI.white, total_pkg, ANSI.reset))

        found_one = False
        found_upd = False

        for p in pg:
            if guess_package_type(p) is None:
                continue

            print(p)
            try:
                impls = get_python_impls(p, need_dead=True)
            except (gentoopm.exceptions.InvalidBashCodeError, OSError):
                continue
            assert impls is not None

            found_one = True

            if any(i in impls for i in dead_impls):
                found_upd = True

                if fix:
                    try:
                        with EbuildMangler(p.path) as em:
                            for i in dead_impls:
                                em.remove(i.r1_name)
                    except Exception as e:
                        sys.stderr.write("%s%s%s\n"
                                         % (ANSI.brown, str(e), ANSI.reset))

        if found_one:
            total_pkg += 1
        if found_upd:
            # in case stdout & stderr goes to the same console,
            # clean up the line before printing
            sys.stderr.write("%s\r" % ANSI.clear_line)
            print(pg[0].key)
            total_upd += 1

    sys.stderr.write("%s%sDone.%s\n"
                     % (ANSI.clear_line, ANSI.white, ANSI.reset))


def main(prog_name, *argv):
    pm = get_package_manager()
    read_implementations(pm)

    opt = optparse.OptionParser(
        prog=prog_name,
        usage="%prog [<packages>...]")
    opt.add_option("-f", "--fix", action="store_true",
                   dest="fix", default=False,
                   help="Automatically update PYTHON_COMPAT")
    opt.add_option("-r", "--repo",
                   dest="repo", default="gentoo",
                   help="Work on given repository (default: gentoo)")
    vals, argv = opt.parse_args(list(argv))

    if not argv:
        process(pm.repositories[vals.repo], fix=vals.fix)
    else:
        for pkg in argv:
            process(pm.repositories[vals.repo].filter(pkg), fix=vals.fix)

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
