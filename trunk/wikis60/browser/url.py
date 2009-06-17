#!/usr/bin/env python
# Copyright (c) 2009, Michal Marek Zielinski
# 
# All rights reserved.
#
# *   Redistribution and use in source and binary forms, with or without modification,
#     are permitted provided that the following conditions are met:
#     
# *   Redistributions of source code must retain the above copyright notice, this list
#     of conditions and the following disclaimer.
#     
# *   Redistributions in binary form must reproduce the above copyright notice, this
#     list of conditions and the following disclaimer in the documentation and/or
#     other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import string
import binascii

alphnum = string.ascii_letters + string.digits + '.'

def rsplit(string, by):
    ret = string.split(by)
    if len(ret) == 1:
        return ret
    return by.join(ret[:-1]), ret[-1]

def enumerate(ls):
    ret = []
    i = 0
    for item in ls:
        ret.append((i, item))
        i += 1
    return ret

def _defsplit(string, by, default='', add=''):
    tpl = rsplit(string, by)
    if len(tpl) == 1:
        return tpl + [default, ]
    else:
        return tpl[0], add + tpl[1]

def _deflsplit(string, by, default='', add=''):
    tpl = string.split(by, 1)
    if len(tpl) == 1:
        return tpl + [default, ]
    else:
        return tpl[0], add + tpl[1]


def _split_hash(url):
    return _defsplit(
        url, '#', None
    )

def _split_query(url):
    return _defsplit(
        url, '?', None
    )

def _get_query(url):
    query = []
    while True:
        url, nq = _split_query(url)
        if nq is None:
            break
        query.append(nq)
    if not query:
        return url, None
    return url, '&'.join(query)

def _parse_query(query):
    result = []
    parts = query.split('&')
    for part in parts:
        if not part:
            continue
        result.append(map(unquote, _deflsplit(part, '=', None)))
    return result

def _join_path(parts):
    return '/' + '/'.join(
        map(quote, parts)
    )

def _split_path(path):
    parts = path.split('/')
    if parts[0]:
        raise ValueError('path is not absolute')
    return map(unquote, parts[1:])

def _norm_path(parts):
    stack = []
    for part in parts:
        if part == '.' or not part:
            pass
        elif part == '..':
            stack.pop()
        else:
            stack.append(part)
    return stack

def _unparse_query(query):
    return '&'.join(
        [
            quote(key) + '=' + quote(value)
            for key, value in query.items()
        ]
    )

def unquote(string):
    out = []
    skip = 0
    for i, ch in enumerate(string):
        if skip:
            skip -= 1
            continue
        if ch == '+':
            out.append(' ')
        elif ch == '%':
            if len(string) - 2 <= i:
                out.append('%')
            else:
                hexnum = string[i + 1: i + 3]
                skip = 2
                try:
                    num = int(hexnum, 16)
                except ValueError:
                    out.append('%' + hexnum)
                else:
                    out.append(chr(num))
        else:
            out.append(ch)
    return ''.join(out)

def quote(string):
    return ''.join([
        (ch not in alphnum) and ('%' + binascii.hexlify(ch)) or ch
        for ch in string
    ])

def _test_quote():
    import os
    data = os.urandom(1024)
    assert unquote(quote(data)) == data

class Path:
    def __init__(self, path):
        rest, self.hash = _split_hash(path)
        self.raw_path, self.query = _get_query(rest)
        if self.query is not None:
            self.vars = dict(_parse_query(self.query))
            self.bquery = '?' + self.query
        else:
            self.vars = {}
            self.bquery = ''
        self.raw_spath = _split_path(self.raw_path)
        self.spath = _norm_path(self.raw_spath)
        self.path = _join_path(self.spath)
        if self.hash is not None:
            self.bhash = '#' + self.hash
        else:
            self.bhash = ''
        self.whole = self.path + self.bquery + self.bhash
    def __repr__(self):
        return self.whole
    def dump(self):
        return _asrepr(makerepr(self))

# dump

def _makerepr(self, name=None):
    if name is None:
        name = self.__class__.__name__
    d = dir(self)
    keys = [ k for k in d if (not k.startswith('_') and (not  callable(getattr(self,k ))) ) ]
    return funccallrepr(name, dict(map(lambda k: (k, getattr(self, k)), keys)))

def _funccallrepr(name, kwargs):
    return '%s(%s)' % (name, ', '.join(map(lambda (k, v): '%s=%r' % (k, v), kwargs.items())))

class _asrepr:
    def __init__(self, str):
        self.str = str
    def __repr__(self):
        return self.str