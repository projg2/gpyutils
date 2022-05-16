#   vim:fileencoding=utf-8
# (c) 2013-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .ansi import ANSI
from .eclasses import guess_package_type, PkgType
from .util import EnumObj

import codecs, csv, fnmatch, os.path


class Status(object):
    class dead(EnumObj(1)):
        color = ANSI.red

    class old(EnumObj(2)):
        color = ANSI.brown

    class supported(EnumObj(3)):
        color = ANSI.green

    class current(EnumObj(4)):
        color = ANSI.bgreen

    class experimental(EnumObj(5)):
        color = ANSI.purple

    class future(EnumObj(6)):
        color = ANSI.cyan

    mapping = {
        'dead': dead,
        'old': old,
        'supported': supported,
        'current': current,
        'experimental': experimental,
        'future': future,
    }


class PythonImpl(object):
    def __init__(self, r1_name, r0_name, status, short_name = None):
        self.r1_name = r1_name
        self.short_name = short_name
        if status in Status.mapping:
            self.status = Status.mapping[status]
        else:
            raise KeyError("Invalid implementation status: %s" % status)


implementations = []


def read_implementations(pkg_db):
    # check repositories for 'implementations.txt'
    # respecting PM ordering
    for r in reversed(list(pkg_db.repositories)):
        path = os.path.join(r.path, 'app-portage', 'gpyutils',
                'files', 'implementations.txt')
        if os.path.exists(path):
            with codecs.open(path, 'r', 'utf8') as f:
                listr = csv.reader(f, delimiter='\t',
                        lineterminator='\n', strict=True)
                for l in listr:
                    # skip comment and empty lines
                    if not l or l[0].startswith('#'):
                        continue
                    if len(l) != 4:
                        raise SystemError('Syntax error in implementations.txt')
                    implementations.append(PythonImpl(*l))
                break
    else:
        raise SystemError('Unable to find implementations.txt in any of ebuild repositories')


def get_impl_by_name(name):
    for i in implementations:
        if name in (i.r1_name, i.short_name):
            return i
    raise KeyError(name)


class PythonImpls:
    def __init__(self, pkg, subtype, need_dead=False):
        if subtype != PkgType.python_any and not need_dead:
            # IUSE should be much faster than env
            if subtype == PkgType.python_single:
                # len("python_single_target_") == 21
                self._impls = [x[21:] for x in pkg.use
                        if x.startswith('python_single_target_')]
            else: # python_r1
                # len("python_targets_") == 15
                self._impls = [x[15:] for x in pkg.use
                        if x.startswith('python_targets_')]
        else:
            self._impls = pkg.environ['PYTHON_COMPAT[*]'].split()

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
