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

# (int, string)

import encoding
import pair
import tempfile
import zlib
import tools
import container
import StringIO

SLEN = 64

def write(feedfunc, out, translator):
    data_out = tempfile.TemporaryFile()
    index_out = tempfile.TemporaryFile()
    meta = StringIO.StringIO("{'slen': %r, 'version': '0'}" % SLEN)
    meta.seek(0, 2)
    write_all(feedfunc, data_out, index_out, translator, SLEN)
    flist = [('data', data_out), ('index', index_out), ('meta', meta)]
    flist = [
             (name, file.tell(), file)
             for name, file in flist
            ]
    [
        file.seek(0)
        for name, size, file in flist
    ]
    container.write(out, flist)

class DataWriter:
    def __init__(self, out, translator=lambda name, val:val):
        self.translator = translator
        self.out = out
        self.i = 0
        self.parts = []
    def feed(self, name, value):
        try:
            value = self.translator(name, value)
        except __init__.Skip:
            pass
        value = zlib.compress(value)
        self.parts.append((name, self.i))
        self.out.write(tools.pack_int64(len(value)))
        self.out.write(value)
        self.i += len(value)
        self.i += tools.INT64_LEN

def write_all(feedfunc, data, index, translator, slen):
    out = DataWriter(data, translator)
    feedfunc(out)
    out.parts.sort(key=lambda (name, i): encoding.ee(name))
    index_pair = pair.PairWriter(index, len(out.parts), slen)
    for i, name in out.parts:
        index_pair.write((name, i))
    index.flush()
    data.flush()

import __init__