#	vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

def EnumObj(num):
	def hash_eq(self, other):
		return hash(self) == hash(other)
	def hash_lt(self, other):
		return hash(self) < hash(other)

	def meta_new(mcls, cls_name, cls_par, cls_attr):
		cls_attr['__hash__'] = lambda self: num
		cls_attr['__eq__'] = hash_eq
		cls_attr['__lt__'] = hash_lt
		return type.__new__(mcls, cls_name, cls_par, cls_attr)

	return type('EnumObj', (type,), {
		'__hash__': lambda self: num,
		'__eq__': hash_eq,
		'__lt__': hash_lt,
		'__new__': meta_new,
	})
