#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .ansi import ANSI
from .eclasses import guess_package_type, PkgType
from .util import EnumObj

import fnmatch

class Status(object):
	class dead(EnumObj(1)):
		color = ANSI.red

	class old(EnumObj(2)):
		color = ANSI.brown

	class supported(EnumObj(3)):
		color = ANSI.green

	class current(EnumObj(4)):
		color = ANSI.bgreen

	class experimental(EnumObj(5)):
		color = ANSI.purple

class PythonImpl(object):
	def __init__(self, r1_name, r0_name, status, short_name = None):
		self.r1_name = r1_name
		self.r0_name = r0_name
		self.status = status
		self.short_name = short_name or r0_name

implementations = (
	PythonImpl('python2_4', '2.4', Status.dead),
	PythonImpl('python2_5', '2.5', Status.old),
	PythonImpl('python2_6', '2.6', Status.supported),
	PythonImpl('python2_7', '2.7', Status.current),
	PythonImpl('python3_0', '3.0', Status.dead),
	PythonImpl('python3_1', '3.1', Status.old),
	PythonImpl('python3_2', '3.2', Status.current),
	PythonImpl('python3_3', '3.3', Status.supported),
	PythonImpl('python3_4', '3.4', Status.experimental),

	PythonImpl('pypy1_8', '2.7-pypy-1.8', Status.dead, 'p1.8'),
	PythonImpl('pypy1_9', '2.7-pypy-1.8', Status.old, 'p1.9'),
	PythonImpl('pypy2_0', '2.7-pypy-1.8', Status.supported, 'p2.0'),
	PythonImpl('pypy2_1', '2.7-pypy-1.8', Status.experimental, 'p2.1'),

	PythonImpl('jython2_5', '2.5-jython', Status.dead, 'j2.5'),
	PythonImpl('jython2_7', '2.7-jython', Status.experimental, 'j2.7'),
)

def get_impl_by_name(name):
	for i in implementations:
		if i.r1_name == name or i.r0_name == name:
			return i
	raise KeyError(name)

class PythonImpls(object):
	def __iter__(self):
		for i in implementations:
			if i in self:
				yield i

class PythonR1Impls(PythonImpls):
	def __init__(self, pkg):
		self._impls = pkg.environ['PYTHON_COMPAT[*]'].split()

	def __contains__(self, i):
		return i.r1_name in self._impls

class PythonR0Impls(PythonImpls):
	def __init__(self, pkg):
		self._restrict = pkg.environ['RESTRICT_PYTHON_ABIS'].split()

	def __contains__(self, i):
		return not any(fnmatch.fnmatch(i.r0_name, r)
				for r in self._restrict)

def get_python_impls(pkg):
	t = guess_package_type(pkg, check_deps=False)

	if isinstance(t, PkgType.python_r1):
		return PythonR1Impls(pkg)
	elif isinstance(t, PkgType.python_r0):
		return PythonR0Impls(pkg)
	return None
