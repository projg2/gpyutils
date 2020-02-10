#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2017 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup, Command


class TestCommand(Command):
	description = 'run tests'
	user_options = []

	def initialize_options(self):
		self.build_base = None
		self.build_lib = None

	def finalize_options(self):
		self.set_undefined_options('build',
			('build_lib', 'build_lib'))

	def run(self):
		import doctest, sys, unittest

		sys.path.insert(0, self.build_lib)

		tests = unittest.TestSuite()
		tests.addTests(doctest.DocTestSuite('gpyutils.pycompat'))

		r = unittest.TextTestRunner()
		res = r.run(tests)
		sys.exit(0 if res.wasSuccessful() else 1)


setup(
		name = 'gpyutils',
		version = '0.4.1',
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

		cmdclass = {
			'test': TestCommand
		}
)
