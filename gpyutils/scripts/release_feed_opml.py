#!/usr/bin/env python
# gpyutils
# (c) 2023-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import locale
import os
import sys
import typing
from pathlib import Path

import lxml.etree


class FeedMetadata(typing.NamedTuple):
    feed_type: str
    text: str
    url: str
    html_url: str


class Getters:
    @staticmethod
    def github(val: str) -> FeedMetadata:
        name = val.split("/")[-1]
        return FeedMetadata(
            "atom",
            f"Release notes from {name}",
            f"https://github.com/{val}/releases.atom",
            f"https://github.com/{val}/releases")

    @staticmethod
    def pypi(val: str) -> FeedMetadata:
        return FeedMetadata(
            "rss",
            f"PyPI recent updates for {val}",
            f"https://pypi.org/rss/project/{val}/releases.xml",
            f"https://pypi.org/project/{val}/")


def remote_id_list(val: str) -> list:
    def inner() -> typing.Generator[str, None, None]:
        for x in val.split(","):
            x = x.strip()
            if x not in dir(Getters):
                raise argparse.ArgumentTypeError(
                    f"invalid remote-id type {x!r}")
            yield x
    return list(inner())


def main(prog_name: str, *argv: str) -> int:
    locale.setlocale(locale.LC_ALL, "")
    default_types = ["pypi", "github"]

    argp = argparse.ArgumentParser(prog=prog_name)
    argp.add_argument("--diff",
                      type=lambda x: lxml.etree.parse(x),
                      help="Diff against existing OPML and output only "
                           "new feeds")
    argp.add_argument("--sort-key",
                      choices=FeedMetadata._fields,
                      default="text",
                      help="Sort key (default: text)")
    argp.add_argument("--type-precedence",
                      type=remote_id_list,
                      default=default_types,
                      help="Remote-id type precedence, comma-separated "
                           f"(default: {','.join(default_types)})")
    argp.add_argument("path",
                      nargs="+",
                      type=Path,
                      help="Paths to process (recursively)")
    args = argp.parse_args(list(argv))

    feeds_set = set()
    for path in args.path:
        for dirpath, dirnames, filenames in os.walk(path):
            if "metadata.xml" not in filenames:
                continue

            xml = lxml.etree.parse(Path(dirpath) / "metadata.xml")
            for try_type in args.type_precedence:
                remotes = xml.xpath(
                    f"//upstream/remote-id[@type={try_type!r}]")
                if remotes:
                    for r in remotes:
                        feeds_set.add(getattr(Getters, try_type)(r.text))
                    break

    feeds = sorted(feeds_set,
                     key=lambda x: locale.strxfrm(getattr(x, args.sort_key)))

    if args.diff is not None:
        feeds = filter(
            lambda x: not args.diff.xpath(f"//outline[@type={x.feed_type!r} "
                                          f"and @xmlUrl={x.url!r}]"),
            feeds)

    outxml = lxml.etree.ElementTree(lxml.etree.XML("""\
<?xml version="1.0"?>
<opml version="1.0">
  <!-- generated using gpy-release-feed-opml -->
  <head>
    <title>Python Release Feeds</title>
  </head>
  <body>
    <outline title="python" type="folder">
      </outline>
  </body>
</opml>
"""))
    folder = outxml.find("//outline")
    for metadata in feeds:
        feed = lxml.etree.Element(
            "outline",
            text=metadata.text,
            type=metadata.feed_type,
            xmlUrl=metadata.url,
            htmlUrl=metadata.html_url)
        feed.tail = "\n      "
        folder.append(feed)

    feed.tail = "\n    "
    sys.stdout.buffer.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    outxml.write(sys.stdout.buffer, encoding="UTF-8")
    sys.stdout.buffer.write(b"\n")

    return 0


def entry_point() -> None:
    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
