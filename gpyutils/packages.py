# gpyutils
# (c) 2013-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import enum

from .implementations import Status, get_python_impls


class PackageClass(enum.Enum):
    non_keyworded = enum.auto()
    testing = enum.auto()
    stable = enum.auto()


def get_package_class(pkg):
    k = frozenset(pkg.keywords)
    if any(x[0] not in ("~", "-") for x in k):
        return PackageClass.stable
    elif k:
        return PackageClass.testing
    else:
        return PackageClass.non_keyworded


def group_packages(pkgs, key="key", verbose=True):
    prev_key = None
    curr = []

    for p in pkgs.sorted:
        if getattr(p, key) != prev_key:
            if curr:
                yield curr
                curr = []
            prev_key = getattr(p, key)
        curr.append(p)

    if curr:
        yield curr


def find_redundant(pkgs):
    """
    Find redundant packages in the group, i.e. those that have newer
    versions with a superset of keywords and implementations.
    """
    max_keywords = {}
    max_impls = set()
    for p in reversed(pkgs):
        redundant = True

        # live ebuilds are never redundant
        if not p.keywords:
            redundant = False

        # first, determine non-redundancy via keywords
        for k in p.keywords:
            if k.startswith("~"):
                v = 1
                k = k[1:]
            else:  # stable
                v = 2

            if max_keywords.get(k, 0) < v:
                max_keywords[k] = v
                redundant = False

        # then determine non-redundancy via impls
        impls = {i for i in get_python_impls(p) or ()
                 if i.status not in (Status.dead, Status.future)}
        if not max_impls.issuperset(impls):
            redundant = False
            max_impls.update(impls)

        if redundant:
            yield p
