#!/usr/bin/env python
# gpyutils
# (c) 2013-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import sys

from gentoopm import get_package_manager

from gpyutils.packages import group_packages


def process(pkgs):
    for pg in group_packages(pkgs.sorted, "unversioned_atom"):
        for p in reversed(pg):
            positive_keywords = frozenset(x for x in p.keywords
                                          if not x.startswith("-"))
            # skip unkeyworded (live)
            if not positive_keywords:
                continue
            # if the newest version has at least one stable keywords,
            # print it
            if any(not x.startswith("~") for x in positive_keywords):
                print(p.unversioned_atom)
            break


def main(prog_name, *argv):
    pm = get_package_manager()

    process(pm.repositories["gentoo"])

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
