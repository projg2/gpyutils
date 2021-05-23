#   vim:fileencoding=utf-8
# (c) 2013 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

class ANSI(object):
    clear_line = '\033[2K'
    reset = '\033[0m'
    brown = '\033[33m'
    cyan = '\033[36m'
    gray = '\033[37m'
    green = '\033[32m'
    bgreen = '\033[1;32m'
    purple = '\033[35m'
    red = '\033[31m'
    white = '\033[1m'
