# gpyutils
# (c) 2013-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import codecs
import csv
import enum
import os.path

from .eclasses import PkgType, guess_package_type


class Status(enum.Enum):
    dead = enum.auto()
    old = enum.auto()
    supported = enum.auto()
    current = enum.auto()
    experimental = enum.auto()
    future = enum.auto()


class PythonImpl:
    def __init__(self, r1_name, r0_name, status, short_name=None):
        self.r1_name = r1_name
        self.short_name = short_name
        self.status = Status[status]


implementations = []


def read_implementations(pkg_db):
    # check repositories for 'implementations.txt'
    # respecting PM ordering
    for r in reversed(list(pkg_db.repositories)):
        path = os.path.join(r.path, "app-portage", "gpyutils",
                            "files", "implementations.txt")
        if os.path.exists(path):
            with codecs.open(path, "r", "utf8") as f:
                listr = csv.reader(f, delimiter="\t",
                                   lineterminator="\n", strict=True)
                for x in listr:
                    # skip comment and empty lines
                    if not x or x[0].startswith("#"):
                        continue
                    if len(x) != 4:
                        raise SystemError(
                            "Syntax error in implementations.txt")
                    implementations.append(PythonImpl(*x))
                break
    else:
        raise SystemError(
            "Unable to find implementations.txt in any of ebuild repositories")


def get_impl_by_name(name):
    for i in implementations:
        if name in (i.r1_name, i.short_name):
            return i
    raise KeyError(name)


def get_impls_by_status(status: Status) -> list[PythonImpl]:
    return [i for i in implementations if i.status == status]


class PythonImpls:
    def __init__(self, pkg, subtype, need_dead=False):
        if subtype != PkgType.python_any and not need_dead:
            # IUSE should be much faster than env
            if subtype == PkgType.python_single:
                # len("python_single_target_") == 21
                self._impls = [x[21:] for x in pkg.use
                               if x.startswith("python_single_target_")]
            else:  # python_r1
                # len("python_targets_") == 15
                self._impls = [x[15:] for x in pkg.use
                               if x.startswith("python_targets_")]
        else:
            self._impls = pkg.environ["PYTHON_COMPAT[*]"].split()

    def __iter__(self):
        for i in implementations:
            if i in self:
                yield i

    def __contains__(self, i):
        return i.r1_name in self._impls


def get_python_impls(pkg, need_dead=False):
    t = guess_package_type(pkg)

    if t is not None:
        return PythonImpls(pkg, t, need_dead=need_dead)
    return None
