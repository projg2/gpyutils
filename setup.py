#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup

setup(
		name = 'gpyutils',
		version = '0.1',
		author = 'Michał Górny',
		author_email = 'mgorny@gentoo.org',
		url = 'https://bitbucket.org/mgorny/gpyutils',

		packages = ['gpyutils'],
		scripts = [
			'gpy-counts',
			'gpy-depcands',
			'gpy-depcheck',
			'gpy-showimpls',
			'gpy-upgrade-impl',
		],

		classifiers = [
			'Development Status :: 4 - Beta',
			'Environment :: Console',
			'Intended Audience :: System Administrators',
			'License :: OSI Approved :: BSD License',
			'Operating System :: POSIX',
			'Programming Language :: Python',
			'Topic :: System :: Installation/Setup'
		]
)
