#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import sys

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
