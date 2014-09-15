# coding: utf-8
"""
Some py2/py3 compatibility support based on a stripped down
version of six so we don't have to depend on a specific version
of it.
"""
import sys

PY2 = sys.version_info[0] == 2
PYPY = hasattr(sys, 'pypy_translation_info')
_identity = lambda x: x


if not PY2:
    unichr = chr
    range_type = range
    text_type = str
    string_types = (str,)

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    import pickle
    from io import BytesIO, StringIO
    NativeStringIO = StringIO

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    ifilter = filter
    imap = map
    izip = zip
    intern = sys.intern

    get_next = lambda x: x.__next__

    from itertools import zip_longest
else:
    unichr = unichr
    text_type = unicode
    range_type = xrange
    string_types = (str, unicode)

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    import cPickle as pickle
    from cStringIO import StringIO as BytesIO, StringIO
    NativeStringIO = BytesIO

    exec('def reraise(tp, value, tb=None):\n raise tp, value, tb')

    from itertools import imap, izip, ifilter
    intern = intern

    get_next = lambda x: x.next

    from itertools import izip_longest as zip_longest
