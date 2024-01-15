#!/usr/bin/env python
# gpyutils
# (c) 2023-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import json
import re
import subprocess
import sys
import typing
from pathlib import Path

METAVAR_INSERT_RE = re.compile(r"^\s*DISTUTILS_USE.*$", re.MULTILINE)
METAVAR_INSERT2_RE = re.compile(r"^\s*PYTHON_COMPAT=.*$", re.MULTILINE)
INHERIT_RE = re.compile(r"^\s*inherit .*$", re.MULTILINE)
SRC_URI_RE = re.compile(r"^\s*SRC_URI=", re.MULTILINE)
MIRROR_PYPI_URL_PART = r"(mirror://pypi/|https://files\.pythonhosted\.org/)"
SRC_URI_LINE_RE = re.compile(
    r"\s*SRC_URI=['\"][^'\"]*" + MIRROR_PYPI_URL_PART + r"[^\n]+", re.DOTALL)
MIRROR_PYPI_RE = re.compile(
    r"\s*" + MIRROR_PYPI_URL_PART + r"[^\s'\"]+\s*", re.MULTILINE)
S_LINE_RE = re.compile(r"\n\s*S=.*")


def process_json_stream(stream: typing.IO[bytes]) -> None:
    for line in stream:
        report = json.loads(line)
        if report["__class__"] != "PythonInlinePyPIURI":
            continue
        pkg = f"{report['category']}/{report['package']}"
        if report["replacement"] is not None:
            print(f"Skipping {pkg}, custom SRC_URI required",
                  file=sys.stderr)
            continue

        path = Path(f"{pkg}/{report['package']}-{report['version']}.ebuild")
        for ebuild in Path(pkg).glob("*9999*.ebuild"):
            print(f"Live ebuild may need updating: {ebuild}",
                  file=sys.stderr)

        metavars = []
        if not report["normalize"]:
            metavars.append("\nPYPI_NO_NORMALIZE=1")
        pypi_pn = report["pypi_pn"]
        if pypi_pn is not None:
            # visual suggestions how the other way from how we like it
            pypi_pn = (pypi_pn.replace('"', "") if '"' in pypi_pn
                       else f'"{pypi_pn}"')
            metavars.append(f"\nPYPI_PN={pypi_pn}")

        with open(path) as f:
            ebuild = f.read()

        # insert metavars below ^DISTUTILS_USE, or ^PYTHON_COMPAT=
        if metavars:
            inserted = []

            def repl(match: re.Match) -> str:
                inserted.append(True)
                return match.group(0) + "".join(metavars)

            ebuild = METAVAR_INSERT_RE.sub(repl, ebuild, count=1)
            if not inserted:
                ebuild = METAVAR_INSERT2_RE.sub(repl, ebuild, count=1)
            assert inserted, ebuild

        # add pypi.eclass to inherits
        inserted = []

        def repl(match: re.Match) -> str:
            inserted.append(True)
            return match.group(0) + " pypi"

        ebuild = INHERIT_RE.sub(repl, ebuild, count=1)
        assert inserted, ebuild

        if report["append"]:
            # change SRC_URI= to SRC_URI+=
            inserted = []

            def repl(match: re.Match) -> str:
                inserted.append(True)
                return match.group(0).replace("=", "+=")

            ebuild = SRC_URI_RE.sub(repl, ebuild, count=1)
            assert inserted, ebuild

            # remove mirror://pypi
            inserted = []

            def repl(match: re.Match) -> str:
                inserted.append(True)
                return ""

            ebuild = MIRROR_PYPI_RE.sub(repl, ebuild, count=1)
            assert inserted, ebuild
        else:
            # remove SRC_URI entirely
            inserted = []

            def repl(match: re.Match) -> str:
                inserted.append(True)
                return ""

            ebuild = SRC_URI_LINE_RE.sub(repl, ebuild, count=1)
            assert inserted, ebuild

        ebuild = S_LINE_RE.sub("", ebuild, count=1)

        with open(path, "w") as f:
            f.write(ebuild)


def main(prog_name: str, *argv: str) -> int:
    argp = argparse.ArgumentParser(prog=prog_name)
    argp.add_argument("-a", "--all-versions",
                      action="store_true",
                      help="Update all package versions rather than "
                           "the latest (i.e. omit -f latest to pkgcheck)")
    argp.add_argument("data",
                      nargs="?",
                      type=argparse.FileType("rb"),
                      help="Input data (in pkgcheck JsonStream format), "
                           "the default is to run pkgcheck directly")
    args = argp.parse_args(list(argv))

    if args.data is None:
        pkgcheck_args = [
            "pkgcheck", "scan",
            "-c", "PythonFetchableCheck",
            "-k", "PythonInlinePyPIURI",
            "-R", "JsonStream",
        ]
        if not args.all_versions:
            pkgcheck_args += ["-f", "latest"]
        subp = subprocess.Popen(pkgcheck_args, stdout=subprocess.PIPE)
        args.data = subp.stdout
    process_json_stream(args.data)

    return 0


def entry_point() -> None:
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
