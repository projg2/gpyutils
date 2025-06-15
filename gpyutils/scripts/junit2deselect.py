#!/usr/bin/env python
# gpyutils
# (c) 2025 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import dataclasses
import itertools
import os
import sys
import typing

import lxml.etree


@dataclasses.dataclass(frozen=True, order=True)
class TestCase:
    class_ref: str
    name: str
    path: str
    failed: bool

    @classmethod
    def from_xml(cls, testcase: lxml.etree.Element) -> typing.Self:
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

        failed = any(child.tag in ("failure", "error") for child in testcase)
        return cls(class_ref=classname, name=name, path=path, failed=failed)

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

    @property
    def is_parametrized(self) -> bool:
        return "[" in self.name

    @property
    def base_name(self) -> str:
        """Test name without parameters"""
        return self.name.split("[", 1)[0]

    def without_parameters(self) -> typing.Self:
        return self.__class__(class_ref=self.class_ref,
                              name=self.base_name,
                              path=self.path,
                              failed=self.failed)


def combine_parameters(failing_tests: list[TestCase],
                       all_tests: set[TestCase],
                       ) -> typing.Generator[TestCase, None, None]:
    for base_test, group in itertools.groupby(
        failing_tests, key=lambda x: x.without_parameters(),
    ):
        items = list(group)
        if items[0].is_parametrized and all(
            x.failed for x in all_tests
            if x.class_ref == base_test.class_ref
            and x.base_name == base_test.base_name
        ):
            yield base_test
            continue
        yield from items


def main(prog_name: str, *argv: str) -> int:
    argp = argparse.ArgumentParser(prog=prog_name)
    argp.add_argument("xml",
                      type=lambda x: lxml.etree.parse(x),
                      metavar="file.xml",
                      help="junit xml file to process")
    argp.add_argument("--no-combine-parameters",
                      action="store_true",
                      help="Disable combining parametrizing tests if all fail")
    args = argp.parse_args(argv)

    all_tests = {TestCase.from_xml(testcase)
                 for testcase in args.xml.xpath("//testcase")}
    failing_tests = sorted(filter(lambda x: x.failed, all_tests))

    if len(all_tests) == len(failing_tests):
        print("All tests failed!", file=sys.stderr)
        return 1

    if not args.no_combine_parameters:
        failing_tests = list(combine_parameters(failing_tests, all_tests))

    print("EPYTEST_DESELECT=(")
    for test in failing_tests:
        print(f"\t{test.pytest_selector}")
    print(")")

    return 0


def entry_point() -> None:
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
