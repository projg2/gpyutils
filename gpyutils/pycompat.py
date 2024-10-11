# gpyutils
# (c) 2013-2024 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import os.path
import re
import shutil
import tempfile


class Whitespace(str):
    def __init__(self, s):
        self.removed = False
        str.__init__(self)

    def __repr__(self):
        return "Whitespace(%s)" % str.__repr__(self)


class Value:
    def __init__(self, f_name, l_name=None):
        self.full_name = f_name
        self.local_name = l_name if l_name is not None else f_name
        self.removed = False

    def __repr__(self):
        return "Value(full_name=%s, local_name=%s, removed=%s)" % (
            self.full_name,
            self.local_name,
            self.removed,
        )

    def __str__(self):
        assert not self.removed
        return self.local_name


def get_previous_val_index(values, v):
    """
    Return index of value in list values that lexically precedes v,
    or -1 if no value precedes it.

    >>> get_previous_val_index([Value('a'), Value('b')], Value('c'))
    1
    >>> get_previous_val_index([Value('a'), Value('c')], Value('b'))
    0
    >>> get_previous_val_index([Value('c'), Value('a')], Value('b'))
    1
    >>> get_previous_val_index([Value('c'), Value('b')], Value('a'))
    -1
    >>> get_previous_val_index([Value('b'), Whitespace(' '), Value('c')],
    ...                        Value('a'))
    -1
    """
    def sort_key(x):
        if isinstance(x, Whitespace):
            # sort whitespace out to the end
            return (1,)
        elif isinstance(x, Value):
            return (0, x.local_name)
        else:
            return (0, x.local_prefix)

    sorted_values = sorted(values + [v], key=sort_key)
    idx = sorted_values.index(v)
    if idx == 0:
        return -1
    else:
        return values.index(sorted_values[idx - 1])


class Group:
    def __init__(self, f_prefix, l_prefix, values):
        self.full_prefix = f_prefix
        self.local_prefix = l_prefix
        self.values = values

    def add_sorted(self, v: str) -> bool:
        """Add value to the group and return True if it can be added"""
        self.values.insert(get_previous_val_index(self.values, v) + 1, v)
        return True

    @property
    def removed(self):
        return all(x.removed for x in self.values)

    def __iter__(self):
        for x in self.values:
            yield x

    def __repr__(self):
        return "Group(full_prefix=%s, local_prefix=%s, values=%s)" % (
            self.full_prefix,
            self.local_prefix,
            self.values,
        )

    def __str__(self):
        vals = [str(x) for x in self.values if not x.removed]

        if len(vals) > 1:
            vals = "{%s}" % ",".join(vals)
        else:
            vals = vals[0]

        return "".join((self.local_prefix, vals))


range_re = re.compile(r"^(\d+)\.\.(\d+)$")


class Range(Group):
    def __init__(self, f_prefix, l_prefix, values):
        assert len(values) == 1
        m = range_re.match(values[0].local_name)
        if m is None:
            raise ValueError("Invalid range: %s" % values[0].local_name)
        Group.__init__(self, f_prefix, l_prefix,
                       [Value("".join((f_prefix, str(x))), str(x))
                        for x in range(int(m.group(1)), int(m.group(2)) + 1)])

    def add_sorted(self, v: str) -> bool:
        try:
            int(v.local_name)
        except ValueError:
            return False
        return super().add_sorted(v)

    def __repr__(self):
        return "Range(full_prefix=%s, local_prefix=%s, values=%s)" % (
            self.full_prefix,
            self.local_prefix,
            self.values,
        )

    def __str__(self):
        # try a continuous range if we have >1 value
        vals = [x for x in self.values if not x.removed]
        if len(vals) > 1:
            minrange = int(vals[0].local_name)
            maxrange = int(vals[-1].local_name)
            # lazy way of checking
            ovalues = [x.local_name for x in vals]
            rvalues = [str(x) for x in range(minrange, maxrange + 1)]
            if ovalues == rvalues:
                return "%s{%d..%d}" % (self.local_prefix, minrange, maxrange)
        return Group.__str__(self)


class PythonCompat:
    def __init__(self):
        self.nodes = []

    def append(self, n):
        self.nodes.append(n)

    def add(self, impl_name):
        # first, try adding to an existing group
        # longer groups come first, so that should be good enough
        for g in self.groups:
            if impl_name.startswith(g.full_prefix):
                value = Value(impl_name, impl_name[len(g.full_prefix):])
                if g.add_sorted(value):
                    return

        # then, try splitting something else
        for v in sorted(self, key=lambda x: len(x.full_name), reverse=True):
            cpfx = os.path.commonprefix((impl_name, v.full_name))
            # only those with common prefix
            if not cpfx:
                continue
            # only split in global scope, don't nest
            if v not in self.nodes:
                continue
            # don't split mid-version if maintainer didn't do that already
            mid_ver_groups = [x for x in self.groups
                              if x.local_prefix.endswith("_")]
            if cpfx[-1] == "_" and not any(mid_ver_groups):
                continue

            suff1 = v.full_name[len(cpfx):]
            suff2 = impl_name[len(cpfx):]
            # avoid 'empty' sections (e.g. pypy{,2_0})
            if not suff1 or not suff2:
                continue
            # don't split in middle of name (e.g. py{py,thon})
            if not suff1[0].isdigit() or not suff2[0].isdigit():
                continue

            # don't create the group if the maintainer could have created
            # one already but didn't (so he likely doesn't want that)
            # e.g. if he has 'python2_5 python2_6', don't do '{2_6,2_7}'
            group_candidates = [x for x in self.nodes
                                if isinstance(x, Value)
                                and x.full_name.startswith(cpfx)]
            if len(group_candidates) > 1:
                continue

            v1 = Value(v.full_name, suff1)
            v2 = Value(impl_name, suff2)

            i = self.nodes.index(v)
            self.nodes[i] = Group(cpfx, cpfx,
                                  sorted([v1, v2], key=lambda x: x.local_name))
            return

        # add it (sorted!)
        v = Value(impl_name, impl_name)
        i = get_previous_val_index(self.nodes, v)

        prepend_ws = (i != -1)
        if i == -1 and isinstance(self.nodes[0], Whitespace):
            i = 0

        self.nodes.insert(i + 1, v)
        self.nodes.insert(i + 1 if prepend_ws else i + 2, Whitespace(" "))

    def remove(self, impl_name):
        for i in self:
            if i.full_name == impl_name:
                i.removed = True

    @property
    def groups(self):
        def subiter(g):
            for x in g:
                if isinstance(x, Group):
                    for y in subiter(x):
                        yield y
                    yield x

        return subiter(self.nodes)

    def __iter__(self):
        def subiter(g):
            for x in g:
                if isinstance(x, Group):
                    for y in subiter(x):
                        if not y.removed:
                            yield y
                elif isinstance(x, Value):
                    if not x.removed:
                        yield x

        return subiter(self.nodes)

    def __repr__(self):
        return repr(self.nodes)

    def __str__(self):
        first = True
        for i, x in enumerate(self.nodes):
            if not isinstance(x, Whitespace):
                if x.removed:
                    if not first:
                        self.nodes[i - 1].removed = True
                    else:
                        self.nodes[i + 1].removed = True
                first = False

        return "".join([str(x) for x in self.nodes if not x.removed])


def parse_item(s):
    depth = 0
    curr = [""]
    values = [[]]
    had_text = []

    def commit_value():
        if had_text:
            values[-1].append(Value("".join(curr), curr[-1]))
            had_text.pop()

    for c in s:
        if c == "{":
            depth += 1
            curr.append("")
            values.append([])
            had_text = [True]
        elif c == "}":
            if depth == 0:
                raise ValueError("Unmatched closing brace '}'")

            commit_value()
            if values[-1]:
                # range thingie
                if len(values[-1]) == 1 and ".." in values[-1][0].local_name:
                    cls = Range
                else:
                    cls = Group
                values[-2].append(cls(
                    "".join(curr[:-1]),
                    curr[-2],
                    values[-1],
                ))

            depth -= 1
            curr.pop()
            values.pop()
        elif c == ",":
            if depth == 0:
                raise ValueError("Comma ',' outside brace")
            commit_value()
            curr[-1] = ""
            had_text = [True]
        elif not c.isalnum() and c not in ("_", "."):
            raise ValueError(f"Unexpected character {c!r} in PYTHON_COMPAT "
                             f"(token: {s!r})")
        else:
            had_text = [True]
            curr[-1] += c

    if depth != 0:
        raise ValueError("Unmatched opening brace '{'")
    commit_value()

    return values[0][0]


ws_split_re = re.compile(r"(\s+)")


def parse(s):
    out = PythonCompat()

    data = ws_split_re.split(s)
    for i, w in enumerate(data):
        if not w:
            pass
        elif i % 2:
            # 1, 3, 5 are whitespace
            out.append(Whitespace(w))
        else:
            # 0, 2, 4 are the real deal
            out.append(parse_item(w))

    return out


def add_impl(s, new):
    """
    >>> add_impl('pypy1_9', 'python3_3')
    'pypy1_9 python3_3'
    >>> add_impl('python2_7', 'pypy2_0')
    'pypy2_0 python2_7'
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
    >>> add_impl('python{2_{5,6},3_{1,2}} pypy{1_9,2_0}', 'python3_3')
    'python{2_{5,6},3_{1,2,3}} pypy{1_9,2_0}'
    >>> add_impl('python{2_{5,6},3_{1,2}} pypy{1_9,2_0}', 'python2_7')
    'python{2_{5,6,7},3_{1,2}} pypy{1_9,2_0}'
    >>> add_impl('python{2_{5,6},3_{1,2}} pypy{1_9,2_0}', 'pypy1_8')
    'python{2_{5,6},3_{1,2}} pypy{1_8,1_9,2_0}'
    >>> add_impl('python{2_{5,6},3_{1,2}} pypy{1_9,2_0}', 'python4_0')
    'python{2_{5,6},3_{1,2},4_0} pypy{1_9,2_0}'
    >>> add_impl('python{2_6,2_7,3_2,3_3} pypy2_0', 'jython2_7')
    'jython2_7 python{2_6,2_7,3_2,3_3} pypy2_0'
    >>> add_impl('python{2_6,2_7,3_2,3_3} pypy2_0', 'pypy')
    'pypy python{2_6,2_7,3_2,3_3} pypy2_0'
    >>> add_impl(' pypy ', 'python2_6')
    ' pypy python2_6 '
    >>> add_impl(' python{2_6,2_7} ', 'pypy')
    ' pypy python{2_6,2_7} '
    >>> add_impl('python2_7 python3_{3..4}', 'python3_5')
    'python2_7 python3_{3..5}'
    >>> add_impl('python2_7 python3_{3..4}', 'python3_2')
    'python2_7 python3_{2..4}'
    >>> add_impl('python{2_{6..7},3_{3..4}}', 'python3_2')
    'python{2_{6..7},3_{2..4}}'
    >>> add_impl('python2_7 python3_{4..5}', 'python3_2')
    'python2_7 python3_{2,4,5}'
    >>> add_impl('pypy{,3}', 'python2_7')
    'pypy{,3} python2_7'
    >>> add_impl('pypy{,3}', 'pypy4')
    'pypy{,3,4}'
    >>> add_impl('pypy{3,4}', 'pypy')
    'pypy{,3,4}'
    >>> add_impl('python3_{12,13}', 'python3_13t')
    'python3_{12,13,13t}'
    >>> add_impl('python3_{12..13}', 'python3_13t')
    'python3_{12..13} python3_13t'
    >>> add_impl('python3_13', 'python3_13t')  # TODO
    'python3_13 python3_13t'
    """
    pc = parse(s)
    pc.add(new)
    return str(pc)


def del_impl(s, old):
    """
    >>> del_impl('python2_6 python2_7 python3_2 pypy1_9', 'python2_6')
    'python2_7 python3_2 pypy1_9'
    >>> del_impl('python2_{6,7} python3_{1,2}', 'python2_6')
    'python2_7 python3_{1,2}'
    >>> del_impl('python2_{6,7} python3_{1,2,3}', 'python3_1')
    'python2_{6,7} python3_{2,3}'
    >>> del_impl('python{2_6,2_7,3_2} pypy1_9', 'python2_6')
    'python{2_7,3_2} pypy1_9'
    >>> del_impl('python{2_6,2_7} pypy1_9', 'python2_6')
    'python2_7 pypy1_9'
    >>> del_impl(' python2_6 python2_7 ', 'python2_6')
    ' python2_7 '
    >>> del_impl(' python2_6 python2_7 ', 'python2_7')
    ' python2_6 '
    >>> del_impl(' python2_6 python2_7 python3_2 ', 'python2_7')
    ' python2_6 python3_2 '
    >>> del_impl(' python{2_{5,6,7},3_{1,2,3}} pypy{1_{8,9},2_0} ',
    ...          'python2_5')
    ' python{2_{6,7},3_{1,2,3}} pypy{1_{8,9},2_0} '
    >>> del_impl(' python{2_{5,6,7},3_{1,2,3}} pypy{1_{8,9},2_0} ', 'pypy1_8')
    ' python{2_{5,6,7},3_{1,2,3}} pypy{1_9,2_0} '
    >>> del_impl('python2_{6..7}', 'python2_6')
    'python2_7'
    >>> del_impl('python3_{1..5}', 'python3_1')
    'python3_{2..5}'
    >>> del_impl('python3_{1..5}', 'python3_5')
    'python3_{1..4}'
    >>> del_impl('python3_{1..5}', 'python3_3')
    'python3_{1,2,4,5}'
    >>> del_impl('python{2_{6..7},3_{3..5}}', 'python2_6')
    'python{2_7,3_{3..5}}'
    >>> del_impl('pypy{,3} python2_7', 'python2_7')
    'pypy{,3}'
    >>> del_impl('pypy{,3}', 'pypy3')
    'pypy'
    >>> del_impl('pypy{,3}', 'pypy')
    'pypy3'
    >>> del_impl('pypy{3,} python2_7', 'python2_7')
    'pypy{3,}'
    >>> del_impl('pypy{3,}', 'pypy3')
    'pypy'
    >>> del_impl('pypy{3,}', 'pypy')
    'pypy3'
    >>> del_impl('python3_{10..13} python3_13t', 'python3_13t')
    'python3_{10..13}'
    >>> del_impl('python3_{10..13} python3_13t', 'python3_10')
    'python3_{11..13} python3_13t'
    >>> del_impl('python3_{10..13} python3_13t', 'python3_13')
    'python3_{10..12} python3_13t'
    >>> del_impl('python3_{10..13} python3_13t', 'python3_12')
    'python3_{10,11,13} python3_13t'
    >>> del_impl('python3_{13,13t}', 'python3_13t')
    'python3_13'
    >>> del_impl('python3_{13,13t}', 'python3_13')
    'python3_13t'
    """
    pc = parse(s)
    pc.remove(old)
    return str(pc)


python_compat_re = re.compile(r"(?<![^\n])PYTHON_COMPAT=\((?P<value>.*)\)")


class EbuildMangler:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read().decode("utf8")

        m = python_compat_re.search(data)
        if m:
            self._path = path
            self._data = data
            self._value = parse(m.group("value"))
            self._start = m.start()
            self._end = m.end()
        else:
            raise KeyError("Unable to find PYTHON_COMPAT in %s" % path)

    def write(self):
        data = "".join((self._data[:self._start],
                        "PYTHON_COMPAT=(", str(self._value), ")",
                        self._data[self._end:]))

        with tempfile.NamedTemporaryFile(
                "wb", dir=os.path.dirname(self._path), delete=False) as f:
            tmp_path = f.name
            f.write(data.encode("utf8"))

        shutil.copymode(self._path, tmp_path)
        os.rename(tmp_path, self._path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.write()

    def add(self, impl):
        self._value.add(impl)

    def remove(self, impl):
        self._value.remove(impl)

    @property
    def value(self):
        return str(self._value)
