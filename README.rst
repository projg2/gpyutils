========
gpyutils
========


gpy-depgraph
------------

gpy-depgraph is an auxiliary tool to convert plain package lists into
dependency graphs. It can be used to ease maintenance tasks by ordering
them per-dependency.

The package list is either read from files (specified as parameters) or
from stdin. The default output format is a .dot graph (suitable for
further processing using GraphViz).

The operation is done using supplied package lists and a specified
repository (to obtain dependencies). All packages must be available
in the repository.


gpy-drop-dead-impls
-------------------

gpy-drop-dead-impls scans the tree for -r1 packages that are listing
obsolete Python implementations in ``PYTHON_COMPAT``. The script can
optionally automatically remove those implementations from ebuilds.

The output is a plain list of packages. If ``--fix`` is used, script
can also modify ebuilds.

The scan can be done per-repository or per-package.


gpy-impl
--------

gpy-impl is a simple PYTHON_COMPAT mangler. It is based on the interface
exposed by ekeyword.

It takes an ebuild path followed by one or more Python implementations,
optionally prefixed using '-', '%' or '+'. The two former prefixes cause
it to remove the specific implementation from PYTHON_COMPAT, otherwise
the implementation is added to PYTHON_COMPAT. The script outputs
a 'diff' of PYTHON_COMPAT afterwards.

The script operates on the specified file only.


gpy-showimpls
-------------

gpy-showimpls lists the implementations supported by various versions
of a package in a table. It is similar to eshowkw in that regard.

The output for each package slot consists of the package slot name
followed by a table listing supported implementations. Supported
implementations are color-coded for their importance. Unsupported are
simply not listed.

gpy-showimpls prints three extra columns that annotate the ebuild with
potentially useful extra information.

The first column explains the package keywords state. No symbol means
no keywords (live ebuild likely), '~' means no stable keywords and 'S'
means that the package has at least one stable keyword.

The second column explains the support for multiple implementations.
No symbol means that the package supports multiple implementations
(likewise python-r1), 's' denotes that only one implementation can be
chosen (likewise python-single-r1) and 'a' denotes that any of supported
implementations will be used (likewise python-any-r1).

The third column denotes the eclass suite used. No symbol means that
python-r1 eclass is used, asterisk means that the 'python.eclass' is
used. In this case, all untested implementations are listed as enabled
and some of them may not actually work.

The scan can be done per-package only.


gpy-upgrade-impl
----------------

gpy-upgrade-impl is intended to help when considering 'upgrading'
the default Python implementations. Given two implementations (the old
one and the new one), it scans the tree for packages that support
the old implementation but do not support the new one.

For example, ``gpy-upgrade-impl python{3_2,3_3}`` will list all packages
that support Python 3.2 but do not work with Python 3.3.

Optionally, it may automatically add the new implementation
to ``PYTHON_COMPAT`` (-r1 packages only). Please remember to read/test
the ebuild afterwards since the implementation may have been omitted
intentionally and the Python package may require patching.

The output is a plain list of packages. If ``--fix`` is used, script
can also modify ebuilds.

The scan can be done per-repository or per-package.


gpy-verify-deps
---------------

gpy-verify-deps scans installed packages for missing dependencies.
It compares the package's RDEPEND/PDEPEND against the requirement list
provided in package's metadata.

Note that the results need to be taken with a grain of salt, as the tool
heavily relies on upstream providing the correct metadata. Sometimes
the right solution will be to fix (or patch locally) the package's
dependencies rather than add an unnecessary dependency to the ebuild.


.. vim:tw=72:ft=rst:spell:spelllang=en
