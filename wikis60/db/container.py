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

'Support for files which contains other files'

# usage: usage: python -c "import wikis60.db.container as c;c.test()"
from tools import pack_int64, unpack_int64
import tools

import json

MAGIC  = 'ContainerFIL'

def write(out, files):
    'files as [(name, size, fileobj)]'
    out.write(MAGIC)
    file_pos = []
    i = 0
    for name, size, fileobj in files:
        file_pos.append((name, i))
        i += size
        i += tools.INT64_LEN
    jsonpos = json.dumps(dict(file_pos))
    out.write(pack_int64(len(jsonpos)))
    out.write(jsonpos)
    for name, size, fileobj in files:
        out.write(pack_int64(size))
        # copy fileobj to out
        written = 0
        while True:
            data = fileobj.read(tools.BS)
            if not data:
                break
            written += len(data)
            out.write(data)
        if written != size:
            raise ValueError('Expected to read %d bytes from %r but read %d' % (size, name, written))

class Reader:
    def __init__(self, input):
        self.input = input
        self.current = None
        tools.check_magic(input, MAGIC)
        length = unpack_int64(input)
        self.name2pos = json.loads(self.input.read(length))
        self.realbegin = self.input.tell()
    def get(self, name):
        pos = self.name2pos[name]
        self.input.seek(self.realbegin + pos)
        len = unpack_int64(self.input)
        obj = SingleObject(self, self.input.tell(), len)
        self.current = obj
        return obj

class SingleObject:
    def __init__(self, reader, begin, length):
        self.begin = begin
        self.pos = 0
        self.length = length
        self.input = reader.input
        self.reader = reader
    def check(self):
        if self.reader.current is not self:
            raise tools.InvalidStateError('other object is currently in use')
    def read(self, i=1024**8):
        self.check()
        count = self._getreadcount(i)
        return self.input.read(count)
    def seek(self, i):
        self.check()
        count = min(self.length, i)
        self.pos = count
        self.input.seek(count + self.begin)
    def tell(self):
        self.check()
        return self.pos
    def _getreadcount(self, i):
        readto = min(self.pos + i, self.length)
        count = readto - self.pos
        self.pos += count
        return count

def test():
    from StringIO import StringIO
    def simple_write(elems):
        out = StringIO()
        write(out, [ (name, len(data), StringIO(data))
                    for name, data in elems
                    ])
        out.seek(0)
        return out
    data = {
            'Element A': 'Value A',
            'Element 2': 'Value 2'
            }.items()
    raw = simple_write(data)
    reader = Reader(raw)
    print 'Element A', repr(reader.get('Element A').read())
    print 'Element 2', repr(reader.get('Element 2').read())
    inp = reader.get('Element A')
    a = inp.read(2)
    a += inp.read(3)
    a += inp.read(5)
    print 'Element A', repr(a)

