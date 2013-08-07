#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os, os.path, re, tempfile

def add_sorted(s, new, delim=None):
	"""
	Add token 'new' to the string 's' delimited using 'delim',
	placing it before the token that sorts lexically next to it.

	>>> add_sorted('py2.7 py3.1 py3.3', 'py3.2')
	'py2.7 py3.1 py3.2 py3.3'
	>>> add_sorted('2.7,3.1,3.3', '3.2', ',')
	'2.7,3.1,3.2,3.3'
	"""
	impls = s.split(delim)

	if impls:
		impls.append(new)
		impls.sort()
		new_i = impls.index(new)
		if new_i == 0:
			return ''.join((new, delim or ' ', s))
		else:
			prev = impls[new_i-1]
			pos = s.rfind(prev)
			assert pos != -1
			pos += len(prev)
			return ''.join((s[:pos], delim or ' ', new, s[pos:]))
	else:
		return new

def add_impl(s, new):
	"""
	>>> add_impl('pypy1_9', 'python3_3')
	'pypy1_9 python3_3'
	>>> add_impl('python2_6 python2_7 python3_2 pypy1_9', 'python3_3')
	'python2_6 python2_7 python3_2 python3_3 pypy1_9'
	>>> add_impl('python2_6 python2_7 python3_4 pypy1_9', 'python3_3')
	'python2_6 python2_7 python3_3 python3_4 pypy1_9'
	>>> add_impl('python2_{6,7} python3_{1,2}', 'python3_3')
	'python2_{6,7} python3_{1,2,3}'
	>>> add_impl('python2_{6,7} python3_2', 'python3_3')
	'python2_{6,7} python3_{2,3}'
	>>> add_impl('python2_{6,7} python3_4', 'python3_3')
	'python2_{6,7} python3_{3,4}'
	>>> add_impl('python{2_6,2_7,3_2} pypy1_9', 'python3_3')
	'python{2_6,2_7,3_2,3_3} pypy1_9'
	>>> add_impl('python{2_6,2_7,3_4} pypy1_9', 'python3_3')
	'python{2_6,2_7,3_3,3_4} pypy1_9'
	>>> add_impl('python2_7 pypy{1_9,2_0}', 'python3_3')
	'python{2_7,3_3} pypy{1_9,2_0}'
	>>> add_impl('python2_7', 'python3_3')
	'python{2_7,3_3}'
	"""
	m = None

	# was anything split on _? if yes, use that syntax
	if '_{' in s:
		lhs, rhs = new.split('_')
		lhs += '_'
		# try to find pythonX_
		m1_re = re.compile(r'(?<!\S)%s{?(?P<value>.*?)}?(?!\S)'
				% re.escape(lhs))
		m = m1_re.search(s)

	if not m and (len(s.split()) == 1 or '{' in s):
		# then, python{X_Y,X_Z}
		# note: we use this also if there's just one 'pythonX_Y'
		# as a sane default
		split_re = re.compile(r'^\D+')
		m = split_re.match(new)
		lhs = m.group(0)
		rhs = new[m.end():]

		m2_re = re.compile(r'(?<!\S)%s{?(?P<value>.*?)}?(?!\S)'
				% re.escape(lhs))
		m = m2_re.search(s)

	if m:
		new_value = add_sorted(m.group('value'), rhs, ',')
		new_i = '%s{%s}' % (lhs, new_value)
		return ''.join((s[:m.start()], new_i, s[m.end():]))

	return add_sorted(s, new)

python_compat_re = re.compile(r'(?<![^\n])PYTHON_COMPAT=\((?P<value>.*)\)')

class EbuildMangler(object):
	def __init__(self, path):
		with open(path, 'rb') as f:
			data = f.read().decode('utf8')

		m = python_compat_re.search(data)
		if m:
			self._path = path
			self._data = data
			self._value = m.group('value')
			self._start = m.start()
			self._end = m.end()
		else:
			raise KeyError('Unable to find PYTHON_COMPAT in %s' % path)

	def write(self):
		data = ''.join((self._data[:self._start],
			'PYTHON_COMPAT=(', self._value, ')',
			self._data[self._end:]))

		with tempfile.NamedTemporaryFile('wb',
				dir=os.path.dirname(self._path), delete=False) as f:
			tmp_path = f.name
			f.write(data.encode('utf8'))

		os.rename(tmp_path, self._path)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type is None:
			self.write()

	def add(self, impl):
		self._value = add_impl(self._value, impl)
