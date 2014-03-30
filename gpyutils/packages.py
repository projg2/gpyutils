#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .util import EnumObj

import sys

class PackageClass(object):
	""" Package stability class. """

	class non_keyworded(EnumObj(1)):
		""" Package with empty keywords (likely live). """
		pass

	class testing(EnumObj(2)):
		""" Package with ~ keywords only. """
		pass

	class stable(EnumObj(3)):
		""" Package with at least a single stable keyword. """
		pass


def get_package_class(pkg):
	k = frozenset(pkg.keywords)
	if any([x[0] not in ('~', '-') for x in k]):
		return PackageClass.stable
	elif k:
		return PackageClass.testing
	else:
		return PackageClass.non_keyworded


def group_packages(pkgs, key='key', verbose=True):
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
