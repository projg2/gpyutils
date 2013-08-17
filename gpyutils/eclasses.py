#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .util import EnumObj

from gentoopm.basepm.atom import PMAtom

def has_python_in_deptree(dep):
	""" Check whether dev-lang/python is in dependency tree. """

	for d in dep:
		if isinstance(d, PMAtom):
			if d.key == 'dev-lang/python':
				return True
		else:
			if has_python_in_deptree(d):
				return True

	return False

class PkgSubType(object):
	""" Package sub-type. """

	class distutils(EnumObj(4)):
		""" distutils-r1 / distutils """
		eclass_r1 = 'distutils-r1'

	class python(EnumObj(3)):
		""" python-r1 / multi-ABI python """
		eclass_r1 = 'python-r1'

	class python_single(EnumObj(2)):
		""" python-single-r1 / single-ABI python """
		eclass_r1 = 'python-single-r1'

	class python_any(EnumObj(1)):
		""" python-any-r1 / any random python dep """
		eclass_r1 = 'python-any-r1'

	all_subtypes = (distutils, python, python_single, python_any)

class PkgType(object):
	""" Guess package type from inherited eclasses. """

	class non_python(EnumObj(1)):
		pass

	class python_r0(EnumObj(2)):
		def __init__(self, subtype_or_pkg, lazy=False):
			if not lazy:
				self._subtype = subtype_or_pkg()
			else:
				self._subtype = None
				self._pkg = subtype_or_pkg

		@property
		def subtype(self):
			if self._subtype is None:
				# lazy check for multi/single-ABI
				if self._pkg.environ['SUPPORT_PYTHON_ABIS']:
					self._subtype = PkgSubType.python
				else:
					self._subtype = PkgSubType.python_single
				# dereference
				self._pkg = None

			return self._subtype

	class python_r1(EnumObj(3)):
		def __init__(self, subtype):
			self.subtype = subtype

def guess_package_type(pkg, check_deps=True):
	# first check for -r1
	# it's easy since every subtype can be recognized using inherit
	for s in PkgSubType.all_subtypes:
		if s.eclass_r1 in pkg.inherits:
			return PkgType.python_r1(s)

	if 'python' in pkg.inherits:
		if 'distutils' in pkg.inherits:
			return PkgType.python_r0(PkgSubType.distutils)
		else:
			# subtype check involves running bash
			# so better keep it lazy
			return PkgType.python_r0(pkg, lazy=True)
	elif check_deps and (has_python_in_deptree(pkg.run_dependencies)
			or has_python_in_deptree(pkg.post_dependencies)
			or has_python_in_deptree(pkg.build_dependencies)):
		return PkgType.python_r0(PkgSubType.python_any)
	else:
		return PkgType.non_python()
