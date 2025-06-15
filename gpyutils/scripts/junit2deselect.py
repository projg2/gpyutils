#!/usr/bin/env python
# gpyutils
# (c) 2025 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import dataclasses
import os
import sys
import typing

import lxml.etree


@dataclasses.dataclass(frozen=True, order=True)
class TestCase:
    class_ref: str
    name: str
    path: str

    @classmethod
    def from_xml(cls, testcase: lxml.Element) -> typing.Self:
        classname = testcase.get("classname")
        name = testcase.get("name")
        if classname is None or name is None:
            raise RuntimeError(
                "classname or name is missing on <testcase/>, "
                "invalid junit xml file")
        path = testcase.get("file")
        if path is None:
            raise RuntimeError(
                "path is missing on <testcase/>, not an xunit1 format file")
        return cls(class_ref=classname, name=name, path=path)

    @property
    def import_name(self) -> str:
        """Convert path to import name"""
        return self.path.replace(os.sep, ".").rstrip(".pyx")

    @property
    def class_name(self) -> str | None:
        """Pure class name or None if global function"""
        stripped = self.class_ref.removeprefix(self.import_name)
        if not stripped:
            return None
        if stripped.startswith("."):
            return stripped.removeprefix(".")
        raise RuntimeError(f"{self.class_ref=} does not match {self.path=}")

    @property
    def pytest_selector(self) -> str:
        class_name = self.class_name
        if class_name is not None:
            return f"{self.path}::{class_name}::{self.name}"
        else:
            return f"{self.path}::{self.name}"


def main(prog_name: str, *argv: str) -> int:
    argp = argparse.ArgumentParser(prog=prog_name)
    argp.add_argument("xml",
                      type=lambda x: lxml.etree.parse(x),
                      metavar="file.xml",
                      help="junit xml file to process")
    args = argp.parse_args(argv)

    failing_tests = sorted(set([
        TestCase.from_xml(testcase)
        for testcase in args.xml.xpath("//testcase[failure|error]")
    ]))

    print("EPYTEST_DESELECT=(")
    for test in failing_tests:
        print(f"\t{test.pytest_selector}")
    print(")")

    return 0


def entry_point() -> None:
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
