#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2017-2022 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup


setup(
		name = 'gpyutils',
		version = '0.6.2',
		author = 'Michał Górny',
		author_email = 'mgorny@gentoo.org',
		url = 'https://github.com/mgorny/gpyutils',

		packages = ['gpyutils'],
		scripts = [
			'gpy-cands',
			'gpy-depcheck',
			'gpy-depgraph',
			'gpy-drop-dead-impls',
			'gpy-impl',
			'gpy-list-pkg-impls',
			'gpy-py2',
			'gpy-showimpls',
			'gpy-upgrade-impl',
			'gpy-verify-installed-reqs',
		],

		classifiers = [
			'Development Status :: 4 - Beta',
			'Environment :: Console',
			'Intended Audience :: System Administrators',
			'License :: OSI Approved :: BSD License',
			'Operating System :: POSIX',
			'Programming Language :: Python',
			'Topic :: System :: Installation/Setup'
		],
)
