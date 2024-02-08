#!/usr/bin/env python
# gpyutils
# (c) 2022-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import collections
import importlib.metadata
import itertools
import json
import os.path
import subprocess
import sys

from gentoopm import get_package_manager
from gentoopm.basepm.atom import PMAtom
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from gpyutils.ansi import ANSI

PYTHON_QUERY_SCRIPT = b"""
import json
import os
import platform
import sys

from epython import EPYTHON

# see packaging/markers.py: default_environment()
output = {
    "EPYTHON": EPYTHON,
    "implementation_name": sys.implementation.name,
    # NB this doesn't account for beta versions but should be good enough
    "implementation_version": "{}.{}.{}".format(*sys.version_info[:3]),
    "os_name": os.name,
    "platform_machine": platform.machine(),
    "platform_release": platform.release(),
    "platform_system": platform.system(),
    "platform_version": platform.version(),
    "python_full_version": platform.python_version(),
    "platform_python_implementation": platform.python_implementation(),
    "python_version": ".".join(platform.python_version_tuple()[:2]),
    "sys_platform": sys.platform,
}
json.dump(output, sys.stdout)
"""


def process(pkgs):
    sys.stderr.write(f"{ANSI.cyan}Populating package cache...{ANSI.reset}\n")

    dist_info_map = {}
    for i, p in enumerate(pkgs):
        sys.stderr.write(
            f"{ANSI.clear_line}{ANSI.green}{p!s:56}{ANSI.reset} "
            f"({ANSI.white}{len(dist_info_map):4}{ANSI.reset} dist-infos in "
            f"{ANSI.white}{i:4}{ANSI.reset} packages)\r")

        for f in p.contents:
            if not f.endswith((".dist-info/METADATA", ".egg-info/PKG-INFO")):
                continue
            spl_path = f.rsplit(os.path.sep, 3)
            if (spl_path[-3] != "site-packages"
                    and not spl_path[-3].startswith("pypy3")):
                continue
            dist_info_map[f] = p

    sys.stderr.write(
        f"{ANSI.clear_line}"
        f"{ANSI.cyan}Populating dist-info cache...{ANSI.reset}\n")

    dist_name_map = collections.defaultdict(dict)
    python_versions = set()
    for i, (distinfo, pkg) in enumerate(dist_info_map.items()):
        spl_path = distinfo.rsplit(os.path.sep, 4)
        pyver = spl_path[-3]
        if pyver == "site-packages":
            pyver = spl_path[-4]
        dist_name = spl_path[-2]
        python_versions.add(pyver)

        sys.stderr.write(
            f"{ANSI.clear_line}"
            f"{ANSI.brown}{pyver:10}{ANSI.reset}: "
            f"{ANSI.green}{dist_name:40}{ANSI.reset} "
            f"({ANSI.white}{i:4}{ANSI.reset} of "
            f"{ANSI.white}{len(dist_info_map):4}{ANSI.reset})\r")

        dist = importlib.metadata.Distribution.at(distinfo)
        names = [dist.name]
        names.extend(dist.metadata.get_all("Provides", []))
        names.extend(dist.metadata.get_all("Provides-Dist", []))
        for dist_name in names:
            dist_name = canonicalize_name(dist_name)
            pkg_in_map = dist_name_map[dist_name].setdefault(pyver, pkg)
            assert pkg_in_map == pkg, (
                f"{dist_name} ({pyver}) belongs to two packages: "
                f"{pkg_in_map} and {pkg}")

    sys.stderr.write(
        f"{ANSI.clear_line}"
        f"{ANSI.cyan}Querying Python interpreter metadata...{ANSI.reset}\n")

    python_envs = {}
    epythons = {}
    for p in python_versions:
        subp = subprocess.Popen([p, "-"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        stdout, _ = subp.communicate(PYTHON_QUERY_SCRIPT)
        assert subp.returncode == 0
        env = json.loads(stdout)
        env["extra"] = ""
        epythons[p] = env.pop("EPYTHON")
        python_envs[p] = env

    sys.stderr.write(
        f"{ANSI.clear_line}"
        f"{ANSI.cyan}Verifying dependencies...{ANSI.reset}\n")

    missing_dists = collections.defaultdict(
        lambda: collections.defaultdict(set))
    missing_deps = collections.defaultdict(
        lambda: collections.defaultdict(set))
    missing_usedeps = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for i, (distinfo, pkg) in enumerate(dist_info_map.items()):
        spl_path = distinfo.rsplit(os.path.sep, 4)
        pyver = spl_path[-3]
        if pyver == "site-packages":
            pyver = spl_path[-4]
        pyflag = epythons[pyver].replace(".", "_")
        dist_name = spl_path[-2]

        sys.stderr.write(
            f"{ANSI.clear_line}"
            f"{ANSI.brown}{pyver:10}{ANSI.reset}: "
            f"{ANSI.green}{dist_name:40}{ANSI.reset} "
            f"({ANSI.white}{i:4}{ANSI.reset} of "
            f"{ANSI.white}{len(dist_info_map):4}{ANSI.reset})\r")

        dist = importlib.metadata.Distribution.at(distinfo)
        expected_deps = set()
        for r in dist.requires or ():
            parsed_req = Requirement(r)
            if parsed_req.marker is not None:
                if not parsed_req.marker.evaluate(python_envs[pyver]):
                    continue
            dep_name = canonicalize_name(parsed_req.name)
            matched_pkg = dist_name_map[dep_name].get(pyver, None)
            if matched_pkg is None:
                missing_dists[dist.name][dep_name].add(pyver)
                continue
            matched_dep = str(matched_pkg.key)
            # map dev-python/pypy3_* subpackages into the common
            # dev-python/pypy3 dependency
            if matched_dep.startswith("dev-python/pypy3_"):
                matched_dep = "dev-python/pypy3"
            expected_deps.add(matched_dep)

        expected_usedeps = set(expected_deps)

        def process_deps(dep):
            if not isinstance(dep, PMAtom):
                for x in dep:
                    process_deps(x)
            else:
                _, _, usedep = str(dep).partition("[")
                flags = usedep.rstrip("]").split(",")
                for f in flags:
                    if not f.startswith(("python_targets_",
                                         "python_single_target_")):
                        continue
                    if f.rstrip("()+-?").endswith(pyflag):
                        expected_usedeps.discard(str(dep.key))
                        break
                expected_deps.discard(str(dep.key))

        process_deps((pkg.run_dependencies, pkg.post_dependencies))
        for dep in expected_deps:
            missing_deps[dist.name][dep].add(pyver)
            # report each dep only once
            expected_usedeps.discard(dep)
        # special case: dev-python/pypy3 provides (cffi, hpy)
        if pyflag == "pypy3":
            expected_usedeps.discard("dev-python/pypy3")
        for dep in expected_usedeps:
            missing_usedeps[dist.name][dep].add(pyver)

    sys.stderr.write(
        f"{ANSI.clear_line}{ANSI.white}Done.{ANSI.reset}\n")

    for dist_name, data in sorted(missing_dists.items()):
        for dep, allpyvers in data.items():
            for pkg, pyvers in itertools.groupby(
                    allpyvers, lambda x: dist_name_map[dist_name].get(x)):
                if pkg is None:
                    continue
                pyvers = set(pyvers)
                if pyvers == set(dist_name_map[dist_name]):
                    pyvers = ["*"]
                print(f"{pkg}: missing package providing distribution: {dep} "
                      f"[{' '.join(sorted(pyvers))}]")

    for dist_name, data in sorted(missing_deps.items()):
        for dep, allpyvers in data.items():
            for pkg, pyvers in itertools.groupby(
                    allpyvers, lambda x: dist_name_map[dist_name].get(x)):
                if pkg is None:
                    continue
                pyvers = set(pyvers)
                if pyvers == set(dist_name_map[dist_name]):
                    pyvers = ["*"]
                print(f"{pkg}: missing dependency: {dep} "
                      f"[{' '.join(sorted(pyvers))}]")

    for dist_name, data in sorted(missing_usedeps.items()):
        for dep, allpyvers in data.items():
            for pkg, pyvers in itertools.groupby(
                    allpyvers, lambda x: dist_name_map[dist_name].get(x)):
                if pkg is None:
                    continue
                pyvers = set(pyvers)
                if pyvers == set(dist_name_map[dist_name]):
                    pyvers = ["*"]
                print(f"{pkg}: missing PYTHON_USEDEP on: {dep} "
                      f"[{' '.join(sorted(pyvers))}]")


def main(prog_name, *argv):
    pm = get_package_manager()
    process(pm.installed)
    return 0


def entry_point():
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
