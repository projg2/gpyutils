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
		entry_points = {
			'console_scripts': [
				'gpy-depgraph = gpyutils.scripts.depgraph:entry_point',
				'gpy-drop-dead-impls = gpyutils.scripts.drop_dead_impls:entry_point',
				'gpy-impl = gpyutils.scripts.impl:entry_point',
				'gpy-list-pkg-impls = gpyutils.scripts.list_pkg_impls:entry_point',
				'gpy-showimpls = gpyutils.scripts.showimpls:entry_point',
				'gpy-upgrade-impl = gpyutils.scripts.upgrade_impl:entry_point',
			],
		},

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
