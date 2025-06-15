#!/usr/bin/env python
# gpyutils
# (c) 2025 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import os
import sys

import lxml.etree


def testcase_to_selector(testcase: lxml.Element) -> str:
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

    classname_from_path = path.replace(os.sep, ".").rstrip(".py")
    # global test function
    if classname_from_path == classname:
        return f"{path}::{name}"

    # test in class
    actual_classname = classname.removeprefix(f"{classname_from_path}.")
    if actual_classname == classname:
        raise RuntimeError(f"{classname=} does not match {path=}")
    return f"{path}::{actual_classname}::{name}"


def main(prog_name: str, *argv: str) -> int:
    argp = argparse.ArgumentParser(prog=prog_name)
    argp.add_argument("xml",
                      type=lambda x: lxml.etree.parse(x),
                      metavar="file.xml",
                      help="junit xml file to process")
    args = argp.parse_args(argv)

    print("EPYTEST_DESELECT=(")
    for testcase in args.xml.xpath("//testcase[failure|error]"):
        print(f"\t{testcase_to_selector(testcase)}")
    print(")")

    return 0


def entry_point() -> None:
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
