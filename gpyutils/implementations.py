#	vim:fileencoding=utf-8
# (c) 2013-2017 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .ansi import ANSI
from .eclasses import guess_package_type, PkgType, PkgSubType
from .util import EnumObj

import codecs, csv, fnmatch, os.path

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

	class future(EnumObj(6)):
		color = ANSI.cyan

	mapping = {
		'dead': dead,
		'old': old,
		'supported': supported,
		'current': current,
		'experimental': experimental,
		'future': future,
	}


class PythonImpl(object):
	def __init__(self, r1_name, r0_name, status, short_name = None):
		self.r1_name = r1_name
		self.r0_name = r0_name
		self.short_name = short_name or r0_name
		if status in Status.mapping:
			self.status = Status.mapping[status]
		else:
			raise KeyError("Invalid implementation status: %s" % status)

	def supports_r0(self):
		return bool(self.r0_name)


implementations = []


def read_implementations(pkg_db):
	# check repositories for 'implementations.txt'
	# respecting PM ordering
	for r in reversed(list(pkg_db.repositories)):
		path = os.path.join(r.path, 'app-portage', 'gpyutils',
				'files', 'implementations.txt')
		if os.path.exists(path):
			with codecs.open(path, 'r', 'utf8') as f:
				listr = csv.reader(f, delimiter='\t',
						lineterminator='\n', strict=True)
				for l in listr:
					# skip comment and empty lines
					if not l or l[0].startswith('#'):
						continue
					if len(l) != 4:
						raise SystemError('Syntax error in implementations.txt')
					implementations.append(PythonImpl(*l))
				break
	else:
		raise SystemError('Unable to find implementations.txt in any of ebuild repositories')


def get_impl_by_name(name):
	for i in implementations:
		if name in (i.r1_name, i.r0_name, i.short_name):
			return i
	raise KeyError(name)

class PythonImpls(object):
	def __iter__(self):
		for i in implementations:
			if i in self:
				yield i

class PythonR1Impls(PythonImpls):
	def __init__(self, pkg, subtype):
		if subtype != PkgSubType.python_any:
			# IUSE should be much faster than env
			# len("python_targets_") == 15
			self._impls = [x[15:] for x in pkg.use
					if x.startswith('python_targets_')]
		else:
			self._impls = pkg.environ['PYTHON_COMPAT[*]'].split()

	def __contains__(self, i):
		return i.r1_name in self._impls

class PythonR0Impls(PythonImpls):
	def __init__(self, pkg):
		self._restrict = pkg.environ['RESTRICT_PYTHON_ABIS'].split()

	def __contains__(self, i):
		# the implementation is unsupported if either:
		# 1. eclass does not support it (r0_name is '')
		# 2. it is listed in RESTRICT_PYTHON_ABIS
		return i.r0_name and not any(fnmatch.fnmatch(i.r0_name, r)
				for r in self._restrict)

def get_python_impls(pkg):
	t = guess_package_type(pkg, check_deps=False)

	if isinstance(t, PkgType.python_r1):
		return PythonR1Impls(pkg, t.subtype)
	elif isinstance(t, PkgType.python_r0):
		return PythonR0Impls(pkg)
	return None
