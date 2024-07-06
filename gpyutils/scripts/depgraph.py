#!/usr/bin/env python
# gpyutils
# (c) 2017-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import collections
import dataclasses
import sys

from gentoopm import get_package_manager
from gentoopm.basepm.atom import PMAtom

from gpyutils.ansi import ANSI


@dataclasses.dataclass
class PkgCounters:
    deps: int = 0
    revdeps: int = 0


class DepCounter:
    def start(self):
        self.counters = {}

    def add_node(self, label, mark=False):
        self.counters[label] = PkgCounters()

    def add_edge(self, src, dest, label):
        self.counters[src].deps += 1
        self.counters[dest].revdeps += 1

    def finish(self):
        maxlen = max(len(pkg.split(" [", 1)[0]) for pkg in self.counters)
        print(f"{'# package':{maxlen}} revdeps deps [maintainer]")
        for pkg, counters in sorted(self.counters.items()):
            if " [" in pkg:
                pkg, maintainer = pkg.split(" [", 1)
                print(f"{pkg:{maxlen}} {counters.revdeps:7} {counters.deps:4} "
                      f"[{maintainer}")
            else:
                print(f"{pkg} {counters.revdeps:7} {counters.deps:4}")


class DotPrinter:
    def start(self):
        print("digraph {")
        print("\trankdir=LR;")

    def add_node(self, label, mark=False):
        if mark:
            print('\t"%s" [color="blue"];' % label)
        else:
            print('\t"%s";' % label)

    def add_edge(self, src, dst, label):
        print('\t"%s" -> "%s" [label="%s"];' % (src, dst, label))

    def finish(self):
        print("}")


class NXBase:
    def start(self):
        import networkx
        self.nx = networkx
        self.graph = networkx.DiGraph()

    def add_node(self, label, mark=False):
        # TODO: mark?
        self.graph.add_node(label, marked=mark)

    def add_edge(self, src, dst, label):
        self.graph.add_edge(src, dst, label=label)


class NXNodeDFS(NXBase):
    def finish(self):
        for n in self.nx.dfs_postorder_nodes(self.graph):
            print(n)


class NXNodeDeps(NXBase):
    def __init__(self, pkg):
        self.pkg = pkg

    def finish(self):
        for n in self.nx.nodes(self.nx.dfs_tree(self.graph, self.pkg)):
            print(n)


class PackageSource:
    """ Class providing abstraction over package metadata source. """

    def __init__(self, repo_name, usedep_only):
        self.pm = get_package_manager()
        self.repo = self.pm.repositories[repo_name]
        self.usedep_only = usedep_only
        self.match_cache = {}
        self.revmatch_cache = collections.defaultdict(set)

    def cache(self, p):
        # strip maintainer info
        pkg = p.split(" [")[0]
        matches = frozenset(self.repo.filter(pkg))
        if not matches:
            raise ValueError("%s matches no packages!" % pkg)
        self.match_cache[p] = matches
        for m in matches:
            self.revmatch_cache[m].add(p)

    def is_marked(self, p, marker):
        for m in self.match_cache[p]:
            if marker.should_mark(m):
                return True
        return False

    def get_dep_sets(self, p):
        # TODO: option to check deps for all versions?
        pkg = self.repo.select(p.split(" [")[0])

        def check_dep(dep):
            if isinstance(dep, PMAtom):
                if dep.blocking:
                    return

                # USE deps cause problems with matching, strip them
                # Note to self: this is ugly.
                matcher, _, usedep = str(dep).partition("[")
                dep = self.pm.Atom(matcher)
                if self.usedep_only:
                    for flag in usedep.rstrip("]").split(","):
                        if flag.startswith(("python_targets_",
                                            "python_single_target_")):
                            break
                    else:
                        return

                if dep not in self.match_cache:
                    self.match_cache[dep] = frozenset(self.repo.filter(dep))

                for m in self.match_cache[dep]:
                    try:
                        for matom in self.revmatch_cache[m]:
                            yield matom
                        break
                    except KeyError:
                        pass
            else:
                for dp in dep:
                    for r in check_dep(dp):
                        yield r

        yield ("r", frozenset(check_dep(pkg.run_dependencies)))
        yield ("b", frozenset(check_dep(pkg.build_dependencies)))
        yield ("p", frozenset(check_dep(pkg.post_dependencies)))
        if hasattr(pkg, "cbuild_build_dependencies"):
            yield ("B", frozenset(check_dep(pkg.cbuild_build_dependencies)))


class MaintainerMarker:
    """ Class providing node marking based on maintainer. """

    def __init__(self, maintainers):
        self.maintainers = frozenset(maintainers)

    def should_mark(self, p):
        for maint in p.maintainers:
            if maint.email in self.maintainers:
                return True
        return False


def process(pkgsrc, pkgs, processor, marker):
    sys.stderr.write("%sPopulating match cache...%s\n"
                     % (ANSI.cyan, ANSI.reset))

    for i, p in enumerate(pkgs):
        sys.stderr.write("%s%s%-56s%s (%s%4d%s/%s%4d%s done)\r"
                         % (ANSI.clear_line, ANSI.green, p, ANSI.reset,
                            ANSI.white, i, ANSI.reset,
                            ANSI.white, len(pkgs), ANSI.reset))

        pkgsrc.cache(p)

    sys.stderr.write("%s%sGenerating the graph...%s\n"
                     % (ANSI.clear_line, ANSI.cyan, ANSI.reset))
    processor.start()

    # list all packages first, so we do not skip packages with no deps
    for p in pkgs:
        processor.add_node(p, pkgsrc.is_marked(p, marker))

    for i, p in enumerate(pkgs):
        sys.stderr.write("%s%s%-56s%s (%s%4d%s/%s%4d%s done)\r"
                         % (ANSI.clear_line, ANSI.green, p, ANSI.reset,
                            ANSI.white, i, ANSI.reset,
                            ANSI.white, len(pkgs), ANSI.reset))
        dep_sets = tuple(pkgsrc.get_dep_sets(p))

        combined = set()
        for t, dep_pkgs in dep_sets:
            combined |= dep_pkgs

        sys.stderr.write("%s\r" % ANSI.clear_line)
        for dep in combined:
            dep_types = []
            for t, dep_pkgs in dep_sets:
                if dep in dep_pkgs:
                    dep_types.append(t)
            assert dep_types

            dep_type = "+".join(dep_types) + "dep"
            processor.add_edge(p, dep, dep_type)

    sys.stderr.write("%s%sDone.%s\n"
                     % (ANSI.clear_line, ANSI.white, ANSI.reset))
    processor.finish()


def main(prog_name, *argv):
    opt = argparse.ArgumentParser(prog=prog_name)
    action = opt.add_mutually_exclusive_group()
    action.add_argument("-c", "--counts",
                        dest="proc_cls", action="store_const",
                        const=DepCounter(),
                        help="Print a package list along with dep and revdep "
                             "counts")
    action.add_argument("-d", "--dot-print",
                        dest="proc_cls", action="store_const",
                        const=DotPrinter(),
                        help="Output a .dot graph (default)")
    action.add_argument("-D", "--dependencies", metavar="PACKAGE",
                        help="Print list of all dependencies of given PACKAGE "
                             "(uses networkx)")
    action.add_argument("-n", "--node-dfs",
                        dest="proc_cls", action="store_const",
                        const=NXNodeDFS(),
                        help="Produce list of nodes in depth-first-search "
                             "(uses networkx)")
    opt.add_argument("-m", "--mark-maintainer",
                     dest="mark_maint", action="append", default=[],
                     help="Highlight packages maintained by specified "
                          "person/project (by e-mail)")
    opt.add_argument("-r", "--repo",
                     dest="repo", default="gentoo",
                     help="Work on given repository (default: gentoo)")
    opt.add_argument("-U", "--usedep-only",
                     action="store_true",
                     help="Ignore dependency relations without USE "
                          "dependendencies referencing PYTHON_* flags")
    opt.add_argument("file", nargs="*")
    opt.set_defaults(proc_cls=DotPrinter())
    vals = opt.parse_args(list(argv))

    if vals.dependencies:
        vals.proc_cls = NXNodeDeps(vals.dependencies)

    all_packages = set()

    if vals.file:
        for fn in vals.file:
            with open(fn) as f:
                for x in f:
                    all_packages.add(x.strip())
    else:
        sys.stderr.write("[reading package dependency spec list from stdin]")
        for x in sys.stdin:
            all_packages.add(x.strip())

    pkgsrc = PackageSource(vals.repo, vals.usedep_only)
    process(pkgsrc, all_packages, vals.proc_cls,
            MaintainerMarker(vals.mark_maint))

    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
